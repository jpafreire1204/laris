"""
Reliable local TTS pipeline for long scientific documents.

The previous implementation optimized for speed and tolerated missing chunks.
This version optimizes for completeness, deterministic ordering and auditable
diagnostics.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Optional

from app.utils.chunking import estimate_audio_duration, semantic_chunk_text
from app.utils.mp3_utils import describe_mp3, merge_mp3_files
from app.utils.text_preprocessing import prepare_tts_text

logger = logging.getLogger(__name__)

CHUNK_SOFT_LIMIT = 2200
CHUNK_HARD_LIMIT = 3200
TTS_CONCURRENCY = 3
MAX_RETRIES_PER_CHUNK = 2
RETRY_DELAY_SECONDS = 2
RECOVERY_RETRIES_PER_CHUNK = 4
RECOVERY_RETRY_DELAY_SECONDS = 8
CHUNK_TIMEOUT_SECONDS = 180


class PerformanceMetrics:
    def __init__(self) -> None:
        self.start_time = time.time()
        self.tts_ms = 0
        self.merge_ms = 0
        self.total_ms = 0
        self.chunks_count = 0
        self.completed_chunks = 0
        self.estimated_duration_seconds = 0.0
        self.actual_duration_seconds = 0.0
        self.report: dict[str, Any] = {}

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    def log_summary(self, job_id: str) -> None:
        self.total_ms = self.elapsed_ms()
        logger.info(
            "[PERF %s] tts=%sms merge=%sms total=%sms chunks=%s estimated=%.1fs actual=%.1fs",
            job_id,
            self.tts_ms,
            self.merge_ms,
            self.total_ms,
            self.chunks_count,
            self.estimated_duration_seconds,
            self.actual_duration_seconds,
        )


def _rate_string(speed: float) -> str:
    percentage = int((speed - 1.0) * 100)
    return f"{percentage:+d}%"


async def _generate_chunk_once(
    text: str,
    voice_id: str,
    speed: float,
    output_path: Path,
) -> tuple[bool, str]:
    try:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=_rate_string(speed),
        )
        await asyncio.wait_for(communicate.save(str(output_path)), timeout=CHUNK_TIMEOUT_SECONDS)

        if not output_path.exists() or output_path.stat().st_size == 0:
            return False, "O arquivo do chunk ficou vazio."

        return True, ""
    except Exception as exc:
        return False, str(exc)


async def _generate_chunk_with_retry(
    text: str,
    voice_id: str,
    speed: float,
    output_path: Path,
    chunk_index: int,
    total_chunks: int,
) -> tuple[bool, str]:
    last_error = ""
    for attempt in range(MAX_RETRIES_PER_CHUNK + 1):
        success, error = await _generate_chunk_once(text, voice_id, speed, output_path)
        if success:
            return True, ""
        last_error = error
        logger.warning(
            "[TTS] Chunk %s/%s falhou na tentativa %s: %s",
            chunk_index + 1,
            total_chunks,
            attempt + 1,
            error,
        )
        if attempt < MAX_RETRIES_PER_CHUNK:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
    return False, last_error


async def _generate_chunks(
    chunks: list[str],
    voice_id: str,
    speed: float,
    temp_dir: Path,
    progress_callback: Optional[Callable[[int, str, Optional[dict[str, Any]]], None]] = None,
) -> tuple[list[Path], list[dict[str, Any]]]:
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)
    total_chunks = len(chunks)
    audio_paths: list[Optional[Path]] = [None] * total_chunks
    error_records: list[dict[str, Any]] = []
    completed = 0

    async def process_chunk(index: int, chunk_text: str) -> None:
        nonlocal completed
        async with semaphore:
            chunk_path = temp_dir / f"chunk_{index:04d}.mp3"
            success, error = await _generate_chunk_with_retry(
                chunk_text,
                voice_id,
                speed,
                chunk_path,
                index,
                total_chunks,
            )
            if success:
                audio_paths[index] = chunk_path
            else:
                error_records.append(
                    {
                        "index": index,
                        "chunk_number": index + 1,
                        "error": error,
                    }
                )

            completed += 1
            if progress_callback:
                progress = 20 + int(64 * (completed / total_chunks))
                progress_callback(
                    progress,
                    f"Gerando audio {completed}/{total_chunks}",
                    {
                        "stage": "generating_audio",
                        "chunks_total": total_chunks,
                        "chunks_completed": completed,
                    },
                )

    tasks = [asyncio.create_task(process_chunk(index, chunk)) for index, chunk in enumerate(chunks)]
    await asyncio.gather(*tasks)

    valid_paths = [path for path in audio_paths if path is not None]
    return valid_paths, error_records


async def _recover_failed_chunks(
    chunks: list[str],
    voice_id: str,
    speed: float,
    temp_dir: Path,
    failed_records: list[dict[str, Any]],
) -> tuple[list[Path], list[dict[str, Any]]]:
    recovered_paths: list[Path] = []
    remaining_failures: list[dict[str, Any]] = []

    for failed in failed_records:
        index = failed["index"]
        chunk_text = chunks[index]
        chunk_path = temp_dir / f"chunk_{index:04d}.mp3"
        last_error = failed["error"]

        for attempt in range(RECOVERY_RETRIES_PER_CHUNK):
            logger.warning(
                "[TTS] Recuperacao sequencial do chunk %s/%s tentativa %s",
                index + 1,
                len(chunks),
                attempt + 1,
            )
            success, error = await _generate_chunk_once(chunk_text, voice_id, speed, chunk_path)
            if success:
                recovered_paths.append(chunk_path)
                last_error = ""
                break
            last_error = error
            await asyncio.sleep(RECOVERY_RETRY_DELAY_SECONDS)

        if last_error:
            remaining_failures.append(
                {
                    "index": index,
                    "chunk_number": index + 1,
                    "error": last_error,
                }
            )

    return recovered_paths, remaining_failures


async def run_fast_pipeline(
    text: str,
    voice_id: str,
    speed: float,
    output_path: Path,
    job_id: str,
    detected_lang: str = "pt",
    progress_callback: Optional[Callable[[int, str, Optional[dict[str, Any]]], None]] = None,
    skip_translation: bool = True,
    include_references: bool = False,
) -> tuple[bool, Optional[str], PerformanceMetrics, Optional[dict[str, Any]]]:
    """
    Robust local TTS pipeline. Returns:
      success, error, metrics, prepared_display_text
    """
    metrics = PerformanceMetrics()
    temp_dir: Optional[Path] = None

    def update_progress(
        progress: int,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        if progress_callback:
            progress_callback(progress, message, details)

    try:
        update_progress(5, "Limpando texto", {"stage": "cleaning"})
        prepared = prepare_tts_text(
            text,
            voice_id=voice_id,
            include_references=include_references,
        )
        display_text = prepared["display_text"]
        speech_text = prepared["speech_text"]
        speech_text_start = speech_text[:500]
        speech_text_end = speech_text[-500:]

        if not speech_text.strip():
            return False, "O texto ficou vazio depois da limpeza.", metrics, None

        update_progress(
            12,
            "Segmentando o documento",
            {
                "stage": "segmenting",
                "estimated_duration_seconds": estimate_audio_duration(speech_text, speed=speed),
            },
        )

        chunks, chunk_diagnostics = semantic_chunk_text(
            speech_text,
            max_chars=CHUNK_SOFT_LIMIT,
            hard_max_chars=CHUNK_HARD_LIMIT,
        )
        metrics.chunks_count = len(chunks)
        metrics.estimated_duration_seconds = estimate_audio_duration(speech_text, speed=speed)
        chunk_debug = [
            {
                "index": index,
                "chars": len(chunk),
                "preview_start": chunk[:160],
                "preview_end": chunk[-160:],
            }
            for index, chunk in enumerate(chunks)
        ]

        if not chunks:
            return False, "Nao foi possivel gerar chunks de audio.", metrics, None

        temp_dir = output_path.parent / f"{job_id}_chunks"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        tts_start = time.time()

        update_progress(
            18,
            f"Gerando audio 0/{len(chunks)}",
            {
                "stage": "generating_audio",
                "chunks_total": len(chunks),
                "chunks_completed": 0,
                "estimated_duration_seconds": metrics.estimated_duration_seconds,
            },
        )

        audio_paths, errors = await _generate_chunks(
            chunks,
            voice_id,
            speed,
            temp_dir,
            progress_callback=update_progress,
        )

        if errors:
            logger.warning("[PIPE %s] Iniciando recuperacao de %s chunks com falha", job_id, len(errors))
            recovered_paths, remaining_failures = await _recover_failed_chunks(
                chunks,
                voice_id,
                speed,
                temp_dir,
                errors,
            )
            for recovered_path in recovered_paths:
                if recovered_path not in audio_paths:
                    audio_paths.append(recovered_path)
            audio_paths = sorted(audio_paths, key=lambda path: path.name)
            errors = remaining_failures

        metrics.tts_ms = int((time.time() - tts_start) * 1000)
        metrics.completed_chunks = len(audio_paths)

        if errors:
            logger.error(
                "[PIPE %s] Falhas de TTS: %s",
                job_id,
                "; ".join(
                    f"Chunk {item['chunk_number']}/{len(chunks)}: {item['error']}"
                    for item in errors[:5]
                ),
            )

        if len(audio_paths) != len(chunks):
            metrics.report = {
                "pipeline_signature": "local-debug-v2-2026-03-22",
                "input_text_length": len(text),
                "display_text_length": len(display_text),
                "speech_text_length": len(speech_text),
                "speech_text_sha1": hashlib.sha1(speech_text.encode("utf-8")).hexdigest(),
                "speech_text_preview_start": speech_text_start,
                "speech_text_preview_end": speech_text_end,
                "chunks_total": len(chunks),
                "chunks_completed": len(audio_paths),
                "chunks_failed": len(errors),
                "failed_chunks": errors,
                "chunk_text_lengths": [len(chunk) for chunk in chunks],
                "chunk_debug": chunk_debug,
                "chunk_audio_files": [str(path) for path in sorted(audio_paths, key=lambda path: path.name)],
                "estimated_duration_seconds": metrics.estimated_duration_seconds,
                "actual_duration_seconds": 0.0,
                "removed_patterns": prepared["removed_patterns"],
                "removed_characters": prepared["removed_characters"],
                "references_removed": prepared["references_removed"],
                "warnings": prepared["warnings"],
                "chunk_diagnostics": chunk_diagnostics,
                "audio": {},
                "final_mp3_path": str(output_path),
                "final_mp3_size_bytes": 0,
                "last_chunk_present_in_speech_text": bool(chunks and chunks[-1] in speech_text),
                "last_chunk_preview": chunks[-1][-500:] if chunks else "",
                "detected_language": detected_lang,
                "truncated": True,
            }
            return (
                False,
                (
                    "A geracao de audio nao terminou todos os chunks. "
                    f"Foram concluidos {len(audio_paths)} de {len(chunks)}."
                ),
                metrics,
                {
                    "display_text": display_text,
                    "speech_text": speech_text,
                    "speech_text_preview_start": speech_text_start,
                    "speech_text_preview_end": speech_text_end,
                    "chunks": chunks,
                    "chunk_debug": chunk_debug,
                },
            )

        update_progress(
            88,
            "Juntando os chunks",
            {
                "stage": "merging_audio",
                "chunks_total": len(chunks),
                "chunks_completed": len(audio_paths),
            },
        )

        merge_start = time.time()
        merged, merge_error = merge_mp3_files(audio_paths, output_path)
        metrics.merge_ms = int((time.time() - merge_start) * 1000)

        if not merged:
            return False, f"Falha ao montar o MP3 final: {merge_error}", metrics, {
                "display_text": display_text,
                "speech_text": speech_text,
                "speech_text_preview_start": speech_text_start,
                "speech_text_preview_end": speech_text_end,
                "chunks": chunks,
                "chunk_debug": chunk_debug,
            }

        final_audio = describe_mp3(output_path)
        metrics.actual_duration_seconds = float(final_audio["duration_seconds"])

        if metrics.actual_duration_seconds <= 0:
            return False, "O MP3 final ficou invalido.", metrics, {
                "display_text": display_text,
                "speech_text": speech_text,
                "speech_text_preview_start": speech_text_start,
                "speech_text_preview_end": speech_text_end,
                "chunks": chunks,
                "chunk_debug": chunk_debug,
            }

        update_progress(
            100,
            "Pronto para ouvir",
            {
                "stage": "ready",
                "chunks_total": len(chunks),
                "chunks_completed": len(chunks),
                "estimated_duration_seconds": metrics.estimated_duration_seconds,
                "actual_duration_seconds": metrics.actual_duration_seconds,
            },
        )

        metrics.report = {
            "pipeline_signature": "local-debug-v2-2026-03-22",
            "input_text_length": len(text),
            "display_text_length": len(display_text),
            "speech_text_length": len(speech_text),
            "speech_text_sha1": hashlib.sha1(speech_text.encode("utf-8")).hexdigest(),
            "speech_text_preview_start": speech_text_start,
            "speech_text_preview_end": speech_text_end,
            "chunks_total": len(chunks),
            "chunks_completed": len(chunks),
            "chunks_failed": len(errors),
            "failed_chunks": errors,
            "chunk_text_lengths": [len(chunk) for chunk in chunks],
            "chunk_debug": chunk_debug,
            "chunk_audio_files": [str(path) for path in sorted(audio_paths, key=lambda path: path.name)],
            "estimated_duration_seconds": metrics.estimated_duration_seconds,
            "actual_duration_seconds": metrics.actual_duration_seconds,
            "removed_patterns": prepared["removed_patterns"],
            "removed_characters": prepared["removed_characters"],
            "references_removed": prepared["references_removed"],
            "warnings": prepared["warnings"],
            "chunk_diagnostics": chunk_diagnostics,
            "audio": final_audio,
            "final_mp3_path": str(output_path),
            "final_mp3_size_bytes": final_audio["size_bytes"],
            "last_chunk_present_in_speech_text": bool(chunks and chunks[-1] in speech_text),
            "last_chunk_preview": chunks[-1][-500:] if chunks else "",
            "detected_language": detected_lang,
            "truncated": False,
        }

        metrics.log_summary(job_id)
        return True, None, metrics, {
            "display_text": display_text,
            "speech_text": speech_text,
            "speech_text_preview_start": speech_text_start,
            "speech_text_preview_end": speech_text_end,
            "chunks": chunks,
            "chunk_debug": chunk_debug,
        }
    except Exception as exc:
        logger.exception("[PIPE %s] Erro inesperado: %s", job_id, exc)
        return False, str(exc), metrics, None
    finally:
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
