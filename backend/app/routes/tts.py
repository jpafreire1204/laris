"""
Laris - TTS route.
"""

import logging
import re
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.models.schemas import AudioMode, JobStatus, JobStatusResponse, TTSRequest, TTSResponse
from app.services.fast_pipeline import PerformanceMetrics, run_fast_pipeline
from app.services.tts_service import get_system_status
from app.utils.file_utils import (
    OUTPUTS_DIR,
    ensure_debug_dir,
    ensure_outputs_dir,
    load_job_metadata,
    save_debug_json,
    save_debug_text,
    save_job_metadata,
)

router = APIRouter()
logger = logging.getLogger(__name__)

jobs: Dict[str, Dict[str, Any]] = {}
PIPELINE_SIGNATURE = "tts-route-debug-v2-2026-03-22"


def detect_language(text: str) -> str:
    """Detecta o idioma do texto de forma leve."""
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        return detect(text[:5000])
    except Exception:
        return "unknown"


def update_job_progress(
    job_id: str,
    progress: int,
    message: str,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Atualiza progresso, etapa e detalhes do job."""
    if job_id not in jobs:
        return

    jobs[job_id]["progress"] = progress
    jobs[job_id]["message"] = message
    if status:
        jobs[job_id]["status"] = status
    if stage:
        jobs[job_id]["stage"] = stage
    if details is not None:
        jobs[job_id]["details"] = details


async def process_tts_job(
    job_id: str,
    text: str,
    voice_id: str,
    speed: float,
    file_id: str | None = None,
    skip_translation: bool = True,
    include_references: bool = False,
) -> None:
    """Processa um job de TTS local com diagnosticos auditaveis."""
    job_start = time.time()
    logger.info("[JOB %s] Iniciando TTS local (%s chars)", job_id, len(text))
    logger.info("[JOB %s] Arquivo=%s voz=%s velocidade=%s", job_id, jobs[job_id].get("filename", ""), voice_id, speed)

    try:
        detected_lang = detect_language(text)
        jobs[job_id]["detected_language"] = detected_lang

        ensure_outputs_dir()
        output_path = OUTPUTS_DIR / f"{job_id}_final.mp3"

        def progress_callback(progress: int, message: str, details: Optional[dict[str, Any]] = None) -> None:
            update_job_progress(
                job_id,
                progress,
                message,
                status=JobStatus.GENERATING_AUDIO,
                stage=(details or {}).get("stage"),
                details=details or {},
            )

        success, error, metrics, prepared_bundle = await run_fast_pipeline(
            text=text,
            voice_id=voice_id,
            speed=speed,
            output_path=output_path,
            job_id=job_id,
            detected_lang=detected_lang,
            progress_callback=progress_callback,
            skip_translation=skip_translation,
            include_references=include_references,
        )

        tts_debug_dir = ensure_debug_dir("tts", job_id)
        if prepared_bundle:
            display_text = prepared_bundle.get("display_text", "")
            speech_text = prepared_bundle.get("speech_text", "")
            chunks = prepared_bundle.get("chunks", [])
            display_path = save_debug_text("tts", job_id, "display_text", display_text)
            speech_path = save_debug_text("tts", job_id, "speech_text", speech_text)
            chunk_manifest_path = save_debug_json(
                "tts",
                job_id,
                "chunk_manifest",
                {
                    "job_id": job_id,
                    "pipeline_signature": PIPELINE_SIGNATURE,
                    "chunk_count": len(chunks),
                    "chunks": prepared_bundle.get("chunk_debug", []),
                },
            )
            jobs[job_id]["debug_paths"] = {
                "debug_dir": str(tts_debug_dir),
                "display_text_path": str(display_path),
                "speech_text_path": str(speech_path),
                "chunk_manifest_path": str(chunk_manifest_path),
            }
            logger.info("[JOB %s] Speech preview (inicio): %s", job_id, speech_text[:500])
            logger.info("[JOB %s] Speech preview (fim): %s", job_id, speech_text[-500:])
            logger.info(
                "[JOB %s] Last chunk present in speech text: %s",
                job_id,
                bool(chunks and chunks[-1] in speech_text),
            )

        if not success:
            jobs[job_id]["status"] = JobStatus.ERROR
            jobs[job_id]["message"] = "Falha no processamento"
            jobs[job_id]["error"] = error
            jobs[job_id]["completed_at"] = time.time()
            jobs[job_id]["diagnostics"] = metrics.report
            jobs[job_id]["warnings"] = metrics.report.get("warnings", [])
            jobs[job_id]["pipeline_signature"] = PIPELINE_SIGNATURE
            save_debug_json(
                "tts",
                job_id,
                "summary",
                {
                    "job_id": job_id,
                    "pipeline_signature": PIPELINE_SIGNATURE,
                    "filename": jobs[job_id].get("filename", ""),
                    "voice_id": voice_id,
                    "speed": speed,
                    "input_text_length": len(text),
                    "status": "error",
                    "error": error,
                    "diagnostics": metrics.report,
                    "debug_paths": jobs[job_id].get("debug_paths", {}),
                },
            )
            save_job_metadata(job_id, jobs[job_id])
            logger.error("[JOB %s] Falhou: %s", job_id, error)
            return

        elapsed = time.time() - job_start
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Pronto para ouvir"
        jobs[job_id]["stage"] = "ready"
        jobs[job_id]["audio_mode"] = "single"
        jobs[job_id]["audio_path"] = str(output_path)
        jobs[job_id]["audio_url"] = f"/api/download/audio/{job_id}"
        jobs[job_id]["completed_at"] = time.time()
        jobs[job_id]["diagnostics"] = metrics.report
        jobs[job_id]["warnings"] = metrics.report.get("warnings", [])
        jobs[job_id]["pipeline_signature"] = PIPELINE_SIGNATURE
        jobs[job_id]["details"] = {
            "stage": "ready",
            "chunks_total": metrics.chunks_count,
            "chunks_completed": metrics.completed_chunks,
            "estimated_duration_seconds": metrics.estimated_duration_seconds,
            "actual_duration_seconds": metrics.actual_duration_seconds,
        }
        jobs[job_id]["metrics"] = {
            "tts_ms": metrics.tts_ms,
            "merge_ms": metrics.merge_ms,
            "total_ms": metrics.total_ms,
            "chunks": metrics.chunks_count,
        }

        save_debug_json(
            "tts",
            job_id,
            "summary",
            {
                "job_id": job_id,
                "pipeline_signature": PIPELINE_SIGNATURE,
                "filename": jobs[job_id].get("filename", ""),
                "voice_id": voice_id,
                "speed": speed,
                "input_text_length": len(text),
                "diagnostics": metrics.report,
                "details": jobs[job_id]["details"],
                "audio_url": jobs[job_id]["audio_url"],
                "audio_path": jobs[job_id]["audio_path"],
                "debug_paths": jobs[job_id].get("debug_paths", {}),
            },
        )
        save_job_metadata(job_id, jobs[job_id])
        logger.info("[JOB %s] Concluido em %.1fs", job_id, elapsed)
    except Exception as exc:
        logger.error("[JOB %s] Erro inesperado: %s\n%s", job_id, exc, traceback.format_exc())
        jobs[job_id]["status"] = JobStatus.ERROR
        jobs[job_id]["message"] = "Erro inesperado"
        jobs[job_id]["error"] = str(exc)
        jobs[job_id]["completed_at"] = time.time()
        save_job_metadata(job_id, jobs[job_id])


@router.get("/health")
async def health_check():
    """Endpoint de saude da fila de TTS."""
    status = get_system_status()
    active_jobs = sum(
        1 for job in jobs.values() if job.get("status") not in [JobStatus.COMPLETED, JobStatus.ERROR]
    )

    return JSONResponse(
        {
            "ok": True,
        "service": "laris-tts",
        "active_jobs": active_jobs,
        "system": status,
        "pipeline_signature": PIPELINE_SIGNATURE,
    }
)


@router.post("/tts", response_model=TTSResponse)
async def create_tts(request: TTSRequest, background_tasks: BackgroundTasks):
    """Cria um job de TTS."""
    if not request.text or not request.text.strip():
        return TTSResponse(success=False, error="Texto vazio.")

    status = get_system_status()
    if not status["edge_tts_available"]:
        return TTSResponse(success=False, error="Servico de voz indisponivel.")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "progress": 0,
        "message": "Upload recebido",
        "stage": "queued",
        "details": {},
        "diagnostics": {},
        "warnings": [],
        "voice_id": request.voice_id,
        "speed": request.speed,
        "detected_language": None,
        "audio_path": None,
        "audio_url": None,
        "audio_mode": "single",
        "error": None,
        "created_at": time.time(),
        "filename": request.filename or "",
        "include_references": request.include_references,
        "pipeline_signature": PIPELINE_SIGNATURE,
    }

    background_tasks.add_task(
        process_tts_job,
        job_id,
        request.text,
        request.voice_id,
        request.speed,
        request.file_id,
        request.skip_translation,
        request.include_references,
    )

    return TTSResponse(success=True, job_id=job_id, status=JobStatus.PENDING)


@router.get("/tts/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Retorna o status do job."""
    if job_id not in jobs:
        metadata = load_job_metadata(job_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Job nao encontrado")

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
            stage=metadata.get("stage"),
            details=metadata.get("details", {}),
            diagnostics=metadata.get("diagnostics", {}),
            warnings=metadata.get("warnings", []),
            detected_language=metadata.get("detected_language"),
            language_name=metadata.get("language_name"),
            translation_skipped=metadata.get("translation_skipped"),
        )

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
        stage=job.get("stage"),
        details=job.get("details", {}),
        diagnostics=job.get("diagnostics", {}),
        warnings=job.get("warnings", []),
        detected_language=job.get("detected_language"),
        language_name=job.get("language_name"),
        translation_skipped=job.get("translation_skipped"),
    )


@router.get("/debug/tts/{job_id}")
async def get_tts_debug(job_id: str):
    """Retorna os artefatos detalhados do job de TTS local."""
    debug_dir = ensure_outputs_dir() / "debug" / "tts" / job_id
    summary_path = debug_dir / "summary.json"
    display_text_path = debug_dir / "display_text.txt"
    speech_text_path = debug_dir / "speech_text.txt"
    chunk_manifest_path = debug_dir / "chunk_manifest.json"

    if not summary_path.exists() and job_id in jobs:
        return JSONResponse(
            {
                "job_id": job_id,
                "pipeline_signature": jobs[job_id].get("pipeline_signature"),
                "status": jobs[job_id].get("status"),
                "message": "Debug ainda nao persistido para este job.",
            }
        )

    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Debug de TTS nao encontrado")

    def _read_json(path: Path) -> dict[str, Any]:
        import json

        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    return JSONResponse(
        {
            "summary": _read_json(summary_path),
            "chunk_manifest": _read_json(chunk_manifest_path),
            "display_text": _read_text(display_text_path),
            "speech_text": _read_text(speech_text_path),
        }
    )


@router.get("/download/audio/{job_id}")
async def download_audio(job_id: str):
    """Baixa o MP3 final."""
    audio_path: Optional[Path] = None

    if job_id in jobs and jobs[job_id].get("audio_path"):
        audio_path = Path(jobs[job_id]["audio_path"])
    else:
        ensure_outputs_dir()
        for suffix in ("_final.mp3", "_ptbr.mp3"):
            candidate = OUTPUTS_DIR / f"{job_id}{suffix}"
            if candidate.exists():
                audio_path = candidate
                break

    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    original_name = jobs.get(job_id, {}).get("filename", "")
    if original_name:
        safe_name = re.sub(r"[^\w\s\-.]", "", original_name).strip()
        download_name = f"{safe_name}.mp3"
    else:
        download_name = f"audio_{job_id}.mp3"

    return FileResponse(path=audio_path, media_type="audio/mpeg", filename=download_name)


@router.get("/test/performance")
async def test_performance():
    """Smoke test pequeno para o pipeline local."""
    sample_text = (
        "Titulo do artigo.\n\n"
        "Introducao.\n\n"
        "IL-6, TNF-alpha e PTSD aparecem neste paragrafo para validar a normalizacao."
    )

    output_path = OUTPUTS_DIR / "performance_smoke.mp3"
    success, error, metrics, _ = await run_fast_pipeline(
        text=sample_text,
        voice_id="pt-BR-FranciscaNeural",
        speed=1.0,
        output_path=output_path,
        job_id="perf",
        detected_lang="pt",
        include_references=False,
    )

    return {
        "success": success,
        "error": error,
        "metrics": {
            "tts_ms": metrics.tts_ms,
            "merge_ms": metrics.merge_ms,
            "total_ms": metrics.total_ms,
            "chunks": metrics.chunks_count,
            "estimated_duration_seconds": metrics.estimated_duration_seconds,
            "actual_duration_seconds": metrics.actual_duration_seconds,
        },
        "diagnostics": metrics.report,
    }
