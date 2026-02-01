"""
Laris - TTS Route
Endpoints para geração de áudio (Text-to-Speech).
Com timeouts robustos e tratamento de erros.
"""

import asyncio
import logging
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
from app.services.tts_service import (
    generate_audio,
    save_translated_text,
    save_translated_pdf,
    get_system_status,
    TOTAL_JOB_TIMEOUT_SECONDS
)
from app.utils.file_utils import ensure_outputs_dir, save_job_metadata, load_job_metadata, OUTPUTS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)

# Armazenamento em memória dos jobs
jobs: Dict[str, Dict[str, Any]] = {}


def update_job_progress(job_id: str, progress: int, message: str):
    """Atualiza progresso do job."""
    if job_id in jobs:
        jobs[job_id]["progress"] = progress
        jobs[job_id]["message"] = message


async def process_tts_job(job_id: str, text: str, voice_id: str, speed: float):
    """
    Processa um job de TTS em background com timeout total.
    """
    job_start_time = time.time()
    logger.info(f"[JOB {job_id}] ===== PROCESSO BACKGROUND INICIADO =====")

    try:
        # Atualiza status
        jobs[job_id]["status"] = JobStatus.GENERATING_AUDIO
        jobs[job_id]["message"] = "Gerando áudio... Isso pode levar alguns segundos."
        jobs[job_id]["progress"] = 10
        jobs[job_id]["started_at"] = job_start_time

        # Callback para atualizar progresso
        def progress_callback(progress: int, message: str):
            update_job_progress(job_id, progress, message)

        # Gera áudio com timeout total
        try:
            audio_path, error, audio_mode = await asyncio.wait_for(
                generate_audio(
                    text=text,
                    voice_id=voice_id,
                    speed=speed,
                    job_id=job_id,
                    progress_callback=progress_callback
                ),
                timeout=TOTAL_JOB_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - job_start_time
            error = f"Tempo limite excedido ({TOTAL_JOB_TIMEOUT_SECONDS}s). O texto pode ser muito longo."
            audio_path = None
            audio_mode = "single"
            logger.error(f"[JOB {job_id}] Timeout total após {elapsed:.1f}s")

        if error:
            jobs[job_id]["status"] = JobStatus.ERROR
            jobs[job_id]["error"] = error
            jobs[job_id]["message"] = f"Erro: {error}"
            jobs[job_id]["completed_at"] = time.time()
            logger.error(f"[JOB {job_id}] Falhou: {error}")
            save_job_metadata(job_id, jobs[job_id])
            return

        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Salvando arquivos de texto..."

        # Salva texto TXT
        text_path, text_error = save_translated_text(text, job_id=job_id)
        if text_error:
            logger.warning(f"[JOB {job_id}] Erro ao salvar TXT: {text_error}")

        jobs[job_id]["progress"] = 90
        jobs[job_id]["message"] = "Gerando PDF..."

        # Salva texto PDF
        pdf_path, pdf_error = save_translated_pdf(text, title="Artigo Traduzido", job_id=job_id)
        if pdf_error:
            logger.warning(f"[JOB {job_id}] Erro ao salvar PDF: {pdf_error}")

        # Finaliza com sucesso
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["progress"] = 100
        jobs[job_id]["audio_mode"] = audio_mode
        jobs[job_id]["audio_path"] = str(audio_path) if audio_path else None
        jobs[job_id]["text_path"] = str(text_path) if text_path else None
        jobs[job_id]["pdf_path"] = str(pdf_path) if pdf_path else None
        jobs[job_id]["completed_at"] = time.time()

        if audio_mode == "parts":
            jobs[job_id]["message"] = "Áudio gerado em partes! Baixe o ZIP para ouvir."
            jobs[job_id]["audio_url"] = f"/api/download/audio-parts/{job_id}"
        else:
            jobs[job_id]["message"] = "Áudio gerado com sucesso!"
            jobs[job_id]["audio_url"] = f"/api/download/audio/{job_id}"

        jobs[job_id]["text_url"] = f"/api/download/text/{job_id}"
        jobs[job_id]["pdf_url"] = f"/api/download/pdf/{job_id}"

        # Salva metadados
        save_job_metadata(job_id, jobs[job_id])

        elapsed = time.time() - job_start_time
        logger.info(f"[JOB {job_id}] ===== PROCESSO BACKGROUND CONCLUÍDO em {elapsed:.1f}s (mode={audio_mode}) =====")

    except Exception as e:
        elapsed = time.time() - job_start_time
        error_msg = str(e)
        logger.error(f"[JOB {job_id}] Erro inesperado após {elapsed:.1f}s: {error_msg}\n{traceback.format_exc()}")

        jobs[job_id]["status"] = JobStatus.ERROR
        jobs[job_id]["error"] = error_msg
        jobs[job_id]["message"] = f"Erro inesperado: {error_msg}"
        jobs[job_id]["completed_at"] = time.time()
        save_job_metadata(job_id, jobs[job_id])


@router.get("/health")
async def health_check():
    """
    Endpoint de saúde para diagnóstico.
    Retorna status do sistema e disponibilidade dos serviços.
    """
    status = get_system_status()

    # Conta jobs ativos
    active_jobs = sum(1 for j in jobs.values() if j.get("status") not in [JobStatus.COMPLETED, JobStatus.ERROR])

    return JSONResponse({
        "ok": True,
        "service": "laris-tts",
        "timestamp": time.time(),
        "active_jobs": active_jobs,
        "total_jobs_in_memory": len(jobs),
        "system": status,
        "timeouts": {
            "chunk_timeout_seconds": 60,
            "total_job_timeout_seconds": TOTAL_JOB_TIMEOUT_SECONDS
        }
    })


@router.post("/tts", response_model=TTSResponse)
async def create_tts(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Inicia a geração de áudio a partir de texto.
    Retorna um job_id para acompanhar o progresso.
    """
    logger.info(f"[API] POST /tts - texto: {len(request.text)} chars, voz: {request.voice_id}")

    if not request.text or not request.text.strip():
        logger.warning("[API] Texto vazio recebido")
        return TTSResponse(
            success=False,
            error="Texto vazio para gerar áudio."
        )

    # Verifica sistema
    status = get_system_status()
    if not status["edge_tts_available"]:
        logger.error("[API] edge-tts não disponível")
        return TTSResponse(
            success=False,
            error="Serviço de voz não está disponível. Verifique a instalação."
        )

    # Cria job
    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "progress": 0,
        "message": "Iniciando geração de áudio...",
        "text": request.text,
        "voice_id": request.voice_id,
        "speed": request.speed,
        "audio_path": None,
        "text_path": None,
        "audio_url": None,
        "text_url": None,
        "pdf_url": None,
        "audio_mode": "single",
        "error": None,
        "created_at": time.time()
    }

    logger.info(f"[API] Job {job_id} criado, iniciando background task...")

    # Inicia processamento em background
    background_tasks.add_task(
        process_tts_job,
        job_id,
        request.text,
        request.voice_id,
        request.speed
    )

    return TTSResponse(
        success=True,
        job_id=job_id,
        status=JobStatus.PENDING
    )


@router.get("/tts/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Retorna o status de um job de TTS.
    """
    if job_id not in jobs:
        # Tenta carregar de metadados salvos
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
                error=metadata.get("error")
            )

        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = jobs[job_id]

    # Verifica se job está travado (muito tempo sem atualização)
    if job.get("status") == JobStatus.GENERATING_AUDIO:
        started_at = job.get("started_at", job.get("created_at", 0))
        elapsed = time.time() - started_at
        if elapsed > TOTAL_JOB_TIMEOUT_SECONDS + 30:  # 30s de margem
            # Job travou, marca como erro
            logger.warning(f"[API] Job {job_id} detectado como travado após {elapsed:.1f}s")
            job["status"] = JobStatus.ERROR
            job["error"] = "O processamento demorou muito e foi cancelado."
            job["message"] = "Erro: O processamento demorou muito e foi cancelado."
            save_job_metadata(job_id, job)

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        audio_url=job.get("audio_url"),
        audio_mode=AudioMode(job.get("audio_mode", "single")),
        text_url=job.get("text_url"),
        pdf_url=job.get("pdf_url"),
        error=job.get("error")
    )


@router.get("/download/audio/{job_id}")
async def download_audio(job_id: str):
    """Baixa o arquivo de áudio gerado."""
    audio_path = None

    if job_id in jobs and jobs[job_id].get("audio_path"):
        audio_path = Path(jobs[job_id]["audio_path"])
    else:
        ensure_outputs_dir()
        potential_path = OUTPUTS_DIR / f"{job_id}_ptbr.mp3"
        if potential_path.exists():
            audio_path = potential_path

    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=audio_path.name,
        headers={"Content-Disposition": f'attachment; filename="{audio_path.name}"'}
    )


@router.get("/download/text/{job_id}")
async def download_text(job_id: str):
    """Baixa o arquivo de texto traduzido."""
    text_path = None

    if job_id in jobs and jobs[job_id].get("text_path"):
        text_path = Path(jobs[job_id]["text_path"])
    else:
        ensure_outputs_dir()
        potential_path = OUTPUTS_DIR / f"{job_id}_ptbr.txt"
        if potential_path.exists():
            text_path = potential_path

    if not text_path or not text_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de texto não encontrado")

    return FileResponse(
        path=text_path,
        media_type="text/plain; charset=utf-8",
        filename=text_path.name,
        headers={"Content-Disposition": f'attachment; filename="{text_path.name}"'}
    )


@router.get("/download/pdf/{job_id}")
async def download_pdf(job_id: str):
    """Baixa o arquivo PDF do texto traduzido."""
    pdf_path = None

    if job_id in jobs and jobs[job_id].get("pdf_path"):
        pdf_path = Path(jobs[job_id]["pdf_path"])
    else:
        ensure_outputs_dir()
        potential_path = OUTPUTS_DIR / f"{job_id}_ptbr.pdf"
        if potential_path.exists():
            pdf_path = potential_path

    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f'attachment; filename="{pdf_path.name}"'}
    )


@router.get("/download/audio-parts/{job_id}")
async def download_audio_parts(job_id: str):
    """Baixa o arquivo ZIP com as partes do áudio."""
    zip_path = None

    if job_id in jobs and jobs[job_id].get("audio_path"):
        zip_path = Path(jobs[job_id]["audio_path"])
    else:
        ensure_outputs_dir()
        potential_path = OUTPUTS_DIR / f"{job_id}_ptbr_partes.zip"
        if potential_path.exists():
            zip_path = potential_path

    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo ZIP não encontrado")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
        headers={"Content-Disposition": f'attachment; filename="{zip_path.name}"'}
    )
