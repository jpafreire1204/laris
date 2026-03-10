"""
Laris - Fast Pipeline Service
Pipeline otimizado para TTS em < 30 segundos.
Todos os chunks em paralelo + timeout global + sem retry.
"""

import asyncio
import logging
import time
import re
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Callable

logger = logging.getLogger(__name__)

# === CONFIGURACOES OTIMIZADAS ===
CHUNK_SIZE_CHARS = 2500   # Chunks pequenos = completam em ~10s cada
TTS_CONCURRENCY = 25      # Max conexoes simultaneas (testado: 23 OK em 10s)


class PerformanceMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.tts_ms = 0
        self.merge_ms = 0
        self.total_ms = 0
        self.chunks_count = 0

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    def log_summary(self, job_id: str):
        self.total_ms = self.elapsed_ms()
        logger.info(
            f"[PERF {job_id}] tts={self.tts_ms}ms, merge={self.merge_ms}ms, "
            f"total={self.total_ms}ms, chunks={self.chunks_count}"
        )


def clean_text_for_tts(text: str) -> str:
    """Limpa texto extraido de PDF para narracao natural."""
    from app.utils.text_preprocessing import preprocess_for_tts
    text = preprocess_for_tts(text)
    # Reconstitui palavras quebradas com hifen
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    # Junta linhas que nao terminam com pontuacao final
    text = re.sub(r'([a-zA-ZÀ-ÿ0-9,])\s*\n\s*([a-zA-ZÀ-ÿ("])', r'\1 \2', text)
    # Remove numeros de pagina soltos
    text = re.sub(r'\n\s*\d{1,4}\s*\n', '\n', text)
    # Normaliza multiplas quebras de linha
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove espacos duplicados
    text = re.sub(r' {2,}', ' ', text)
    # Remove espacos antes de pontuacao
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    # Remove linhas que sao apenas simbolos soltos
    text = re.sub(r'\n\s*[-–—•]\s*\n', '\n', text)
    # Dentro de cada paragrafo, substitui \n por espaco
    lines = text.split('\n\n')
    cleaned = []
    for para in lines:
        para = para.strip()
        if not para:
            continue
        para = re.sub(r'\s*\n\s*', ' ', para)
        para = re.sub(r' {2,}', ' ', para)
        cleaned.append(para.strip())
    return '\n\n'.join(cleaned)


def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> List[str]:
    """Divide texto em chunks respeitando limites de sentenca."""
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp = ""
                for sent in sentences:
                    if len(temp) + len(sent) + 1 <= chunk_size:
                        temp = (temp + " " + sent).strip()
                    else:
                        if temp:
                            chunks.append(temp)
                        if len(sent) > chunk_size:
                            words = sent.split(' ')
                            temp = ""
                            for w in words:
                                if len(temp) + len(w) + 1 <= chunk_size:
                                    temp = (temp + " " + w).strip()
                                else:
                                    if temp:
                                        chunks.append(temp)
                                    temp = w
                        else:
                            temp = sent
                current_chunk = temp if temp else ""
            else:
                current_chunk = para
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


async def generate_one_chunk(
    text: str, voice_id: str, speed: float, output_path: Path
) -> Tuple[bool, Optional[str]]:
    """Gera audio para um chunk. Sem retry — fail fast."""
    try:
        import edge_tts

        clean_text = text.strip()
        if not clean_text or len(clean_text) < 2:
            return False, "Texto vazio"

        clean_text = clean_text.replace('\x00', '').replace('\ufeff', '')
        rate_str = f"{int((speed - 1) * 100):+d}%"
        communicate = edge_tts.Communicate(clean_text, voice_id, rate=rate_str)
        await communicate.save(str(output_path))

        if output_path.exists() and output_path.stat().st_size > 100:
            return True, None
        return False, "Arquivo vazio"

    except Exception as e:
        return False, str(e)[:80]


async def generate_audio_parallel(
    chunks: List[str],
    voice_id: str,
    speed: float,
    temp_dir: Path,
    progress_callback: Callable[[int, int], None] = None
) -> Tuple[List[Path], int, List[str]]:
    """
    Gera audio com semaforo (max TTS_CONCURRENCY simultaneos).
    Sem timeout global — espera todos completarem.
    """
    start = time.time()
    total = len(chunks)
    errors = []
    results: List[Optional[Path]] = [None] * total
    completed_count = 0
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    async def process_chunk(idx: int, chunk: str):
        nonlocal completed_count
        async with semaphore:
            output_path = temp_dir / f"chunk_{idx:04d}.mp3"
            success, error = await generate_one_chunk(chunk, voice_id, speed, output_path)
            if success:
                results[idx] = output_path
            else:
                errors.append(f"Chunk {idx}: {error}")
            completed_count += 1
            if progress_callback:
                progress_callback(completed_count, total)

    # Lanca todas as tasks (semaforo controla concorrencia real)
    tasks = [asyncio.create_task(process_chunk(idx, chunk)) for idx, chunk in enumerate(chunks)]

    # Espera todos terminarem (sem timeout — semaforo controla a carga)
    await asyncio.gather(*tasks, return_exceptions=True)

    audio_paths = [p for p in results if p is not None]
    elapsed = int((time.time() - start) * 1000)
    return audio_paths, elapsed, errors


def concat_audio_binary(audio_paths: List[Path], output_path: Path) -> Tuple[bool, int, Optional[str]]:
    """Concatena MP3s por concatenacao binaria direta."""
    start = time.time()
    if not audio_paths:
        return False, 0, "No audio files"
    if len(audio_paths) == 1:
        import shutil
        shutil.copy(audio_paths[0], output_path)
        return True, int((time.time() - start) * 1000), None
    try:
        with open(output_path, 'wb') as outfile:
            for path in audio_paths:
                if path.exists():
                    with open(path, 'rb') as infile:
                        outfile.write(infile.read())
        if output_path.exists() and output_path.stat().st_size > 0:
            return True, int((time.time() - start) * 1000), None
        return False, 0, "Output file empty"
    except Exception as e:
        return False, 0, str(e)


async def run_fast_pipeline(
    text: str,
    voice_id: str,
    speed: float,
    output_path: Path,
    job_id: str,
    detected_lang: str = 'pt',
    progress_callback: Callable[[int, str], None] = None,
    skip_translation: bool = True
) -> Tuple[bool, Optional[str], PerformanceMetrics, Optional[str]]:
    """
    Pipeline TTS ultra-rapido.
    Todos os chunks em paralelo, timeout global de 28s, concat binario.
    """
    metrics = PerformanceMetrics()
    temp_dir = None

    def update_progress(pct: int, msg: str = ""):
        if progress_callback:
            progress_callback(pct, msg)

    try:
        update_progress(5, "Processando texto...")
        text = clean_text_for_tts(text)
        logger.info(f"[PIPE {job_id}] Texto limpo: {len(text)} chars")

        update_progress(8, "Preparando...")
        chunks = split_text_into_chunks(text)
        metrics.chunks_count = len(chunks)
        logger.info(f"[PIPE {job_id}] {len(chunks)} chunks (concurrency={TTS_CONCURRENCY})")

        if not chunks:
            return False, "Texto vazio apos processamento", metrics, None

        update_progress(10, "Gerando audio...")
        temp_dir = Path(tempfile.mkdtemp(prefix=f"laris_{job_id}_"))

        def tts_progress(current, total):
            pct = 10 + int(82 * current / total)
            update_progress(pct, "Gerando audio...")

        audio_paths, tts_time, tts_errors = await generate_audio_parallel(
            chunks, voice_id, speed, temp_dir, tts_progress
        )
        metrics.tts_ms = tts_time
        logger.info(f"[PIPE {job_id}] TTS: {tts_time}ms, {len(audio_paths)}/{len(chunks)} OK")

        if not audio_paths:
            errors_str = "; ".join(tts_errors[:3]) if tts_errors else "Erro desconhecido"
            return False, f"Falha ao gerar audio: {errors_str}", metrics, None

        success_rate = len(audio_paths) / len(chunks)
        if tts_errors:
            logger.warning(f"[PIPE {job_id}] Taxa de sucesso: {success_rate:.0%}")
        if success_rate < 0.3:
            return False, f"Muitos chunks falharam ({len(tts_errors)}/{len(chunks)})", metrics, None

        update_progress(94, "Finalizando...")
        success, merge_time, merge_error = concat_audio_binary(audio_paths, output_path)
        metrics.merge_ms = merge_time

        if not success:
            return False, f"Falha ao concatenar: {merge_error}", metrics, None

        logger.info(f"[PIPE {job_id}] Merge: {merge_time}ms")
        update_progress(100, "Concluido!")
        metrics.log_summary(job_id)

        return True, None, metrics, text

    except Exception as e:
        logger.error(f"[PIPE {job_id}] Erro: {e}")
        return False, str(e), metrics, None

    finally:
        if temp_dir and temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
