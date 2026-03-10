"""
Laris - TTS Route
Endpoints para geração de áudio (Text-to-Speech).
Pipeline otimizado: < 5 minutos para textos longos.
SEMPRE gera UM único arquivo MP3.
"""

import asyncio
import logging
import re
import uuid
import time
import traceback
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from app.models.schemas import (
    TTSRequest,
    TTSResponse,
    JobStatusResponse,
    JobStatus,
    AudioMode
)
from app.services.fast_pipeline import run_fast_pipeline, PerformanceMetrics
from app.services.tts_service import get_system_status
from app.utils.file_utils import ensure_outputs_dir, save_job_metadata, load_job_metadata, OUTPUTS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)

# Armazenamento em memória dos jobs
jobs: Dict[str, Dict[str, Any]] = {}


def detect_language(text: str) -> str:
    """Detecta o idioma do texto. Retorna código."""
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        return detect(text[:5000])
    except Exception:
        return 'unknown'


def update_job_progress(job_id: str, progress: int, message: str, status: str = None):
    """Atualiza progresso do job."""
    if job_id in jobs:
        jobs[job_id]["progress"] = progress
        jobs[job_id]["message"] = message
        if status:
            jobs[job_id]["status"] = status


async def process_tts_job(job_id: str, text: str, voice_id: str, speed: float, file_id: str = None, skip_translation: bool = True):
    """
    Processa um job de TTS usando pipeline otimizado.
    Fluxo: detectar idioma → (traduzir se não skip) → TTS → concatenar → 1 MP3
    Se file_id for fornecido, tenta criar PDF com layout preservado.
    """
    job_start = time.time()
    logger.info(f"[JOB {job_id}] Iniciando pipeline - {len(text)} chars, file_id={file_id}")

    try:
        # Detecta idioma silenciosamente
        detected_lang = detect_language(text)
        jobs[job_id]["detected_language"] = detected_lang

        # Prepara output
        ensure_outputs_dir()
        output_path = OUTPUTS_DIR / f"{job_id}_final.mp3"

        # Callback de progresso
        def progress_callback(pct: int, msg: str):
            update_job_progress(job_id, pct, msg, JobStatus.GENERATING_AUDIO)

        # Executa pipeline otimizado
        success, error, metrics, translated_text = await run_fast_pipeline(
            text=text,
            voice_id=voice_id,
            speed=speed,
            output_path=output_path,
            job_id=job_id,
            detected_lang=detected_lang,
            progress_callback=progress_callback,
            skip_translation=skip_translation
        )

        if not success:
            jobs[job_id]["status"] = JobStatus.ERROR
            jobs[job_id]["error"] = error
            jobs[job_id]["message"] = "Erro no processamento"
            jobs[job_id]["completed_at"] = time.time()
            save_job_metadata(job_id, jobs[job_id])
            logger.error(f"[JOB {job_id}] Falhou: {error}")
            return

        # Finaliza
        elapsed = time.time() - job_start
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Pronto!"
        jobs[job_id]["audio_mode"] = "single"
        jobs[job_id]["audio_path"] = str(output_path)
        jobs[job_id]["audio_url"] = f"/api/download/audio/{job_id}"
        jobs[job_id]["completed_at"] = time.time()
        jobs[job_id]["metrics"] = {
            "tts_ms": metrics.tts_ms,
            "merge_ms": metrics.merge_ms,
            "total_ms": metrics.total_ms,
            "chunks": metrics.chunks_count,
        }

        save_job_metadata(job_id, jobs[job_id])
        logger.info(f"[JOB {job_id}] Concluído em {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - job_start
        logger.error(f"[JOB {job_id}] Erro após {elapsed:.1f}s: {e}\n{traceback.format_exc()}")
        jobs[job_id]["status"] = JobStatus.ERROR
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = "Erro inesperado"
        jobs[job_id]["completed_at"] = time.time()
        save_job_metadata(job_id, jobs[job_id])


@router.get("/health")
async def health_check():
    """Endpoint de saúde."""
    status = get_system_status()
    active = sum(1 for j in jobs.values() if j.get("status") not in [JobStatus.COMPLETED, JobStatus.ERROR])

    return JSONResponse({
        "ok": True,
        "service": "laris-tts",
        "active_jobs": active,
        "system": status
    })


@router.post("/tts", response_model=TTSResponse)
async def create_tts(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Inicia geração de áudio.
    Retorna job_id para acompanhar progresso.
    """
    logger.info(f"[API] POST /tts - {len(request.text)} chars")

    if not request.text or not request.text.strip():
        return TTSResponse(success=False, error="Texto vazio.")

    status = get_system_status()
    if not status["edge_tts_available"]:
        return TTSResponse(success=False, error="Serviço de voz indisponível.")

    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "progress": 0,
        "message": "Iniciando...",
        "voice_id": request.voice_id,
        "speed": request.speed,
        "detected_language": None,
        "audio_path": None,
        "audio_url": None,
        "audio_mode": "single",
        "error": None,
        "created_at": time.time()
    }

    jobs[job_id]["filename"] = request.filename or ""

    background_tasks.add_task(
        process_tts_job, job_id, request.text, request.voice_id, request.speed, request.file_id, request.skip_translation
    )

    return TTSResponse(success=True, job_id=job_id, status=JobStatus.PENDING)


@router.get("/tts/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Retorna status do job."""
    if job_id not in jobs:
        metadata = load_job_metadata(job_id)
        if metadata:
            return JobStatusResponse(
                job_id=job_id,
                status=JobStatus(metadata.get("status", "completed")),
                progress=metadata.get("progress", 100),
                message=metadata.get("message", ""),
                audio_url=metadata.get("audio_url"),
                audio_mode=AudioMode(metadata.get("audio_mode", "single")),
                text_url=metadata.get("text_url"),
                pdf_url=metadata.get("pdf_url"),
                error=metadata.get("error"),
            )
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = jobs[job_id]

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        audio_url=job.get("audio_url"),
        audio_mode=AudioMode(job.get("audio_mode", "single")),
        text_url=job.get("text_url"),
        pdf_url=job.get("pdf_url"),
        error=job.get("error"),
    )


@router.get("/download/audio/{job_id}")
async def download_audio(job_id: str):
    """Baixa o MP3 final."""
    audio_path = None

    if job_id in jobs and jobs[job_id].get("audio_path"):
        audio_path = Path(jobs[job_id]["audio_path"])
    else:
        ensure_outputs_dir()
        for suffix in ["_final.mp3", "_ptbr.mp3"]:
            p = OUTPUTS_DIR / f"{job_id}{suffix}"
            if p.exists():
                audio_path = p
                break

    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Usa nome do arquivo original se disponivel
    original_name = ""
    if job_id in jobs:
        original_name = jobs[job_id].get("filename", "")
    if original_name:
        safe_name = re.sub(r'[^\w\s\-.]', '', original_name).strip()
        download_name = f"{safe_name}.mp3"
    else:
        download_name = f"audio_{job_id}.mp3"

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=download_name
    )


@router.get("/test/performance")
async def test_performance():
    """Endpoint de teste de performance."""
    test_text = "This is a test. " * 100  # ~1600 chars

    from app.services.fast_pipeline import run_fast_pipeline
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        output = Path(f.name)

    try:
        success, error, metrics = await run_fast_pipeline(
            text=test_text,
            voice_id="pt-BR-FranciscaNeural",
            speed=1.0,
            output_path=output,
            job_id="test",
            detected_lang="en"
        )

        result = {
            "success": success,
            "error": error,
            "metrics": {
                "tts_ms": metrics.tts_ms,
                "merge_ms": metrics.merge_ms,
                "total_ms": metrics.total_ms,
                "chunks": metrics.chunks_count
            }
        }

        if output.exists():
            result["file_size"] = output.stat().st_size
            output.unlink()

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}
