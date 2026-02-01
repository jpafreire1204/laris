"""
Laris - Text-to-Speech Service
Geração de áudio usando edge-tts (Microsoft Edge Neural Voices).
Com timeouts robustos e tratamento de erros.
"""

import asyncio
import logging
import tempfile
import zipfile
import shutil
import time
import traceback
from pathlib import Path
from typing import List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)

# Configurações de timeout
CHUNK_TIMEOUT_SECONDS = 120  # Timeout por chunk (2 min)
TOTAL_JOB_TIMEOUT_SECONDS = 900  # Timeout total do job (15 min)


def check_pydub_available() -> bool:
    """Verifica se pydub e ffmpeg estão disponíveis."""
    try:
        from pydub import AudioSegment
        AudioSegment.empty()
        return True
    except Exception:
        return False


def check_ffmpeg_available() -> bool:
    """Verifica se ffmpeg está disponível no PATH."""
    import shutil
    return shutil.which("ffmpeg") is not None


def check_edge_tts_available() -> bool:
    """Verifica se edge-tts está disponível."""
    try:
        import edge_tts
        return True
    except ImportError:
        return False


# Cache dos resultados
_pydub_available: Optional[bool] = None
_ffmpeg_available: Optional[bool] = None
_edge_tts_available: Optional[bool] = None


def is_pydub_available() -> bool:
    global _pydub_available
    if _pydub_available is None:
        _pydub_available = check_pydub_available()
    return _pydub_available


def is_ffmpeg_available() -> bool:
    global _ffmpeg_available
    if _ffmpeg_available is None:
        _ffmpeg_available = check_ffmpeg_available()
    return _ffmpeg_available


def is_edge_tts_available() -> bool:
    global _edge_tts_available
    if _edge_tts_available is None:
        _edge_tts_available = check_edge_tts_available()
    return _edge_tts_available


def get_system_status() -> dict:
    """Retorna status do sistema para diagnóstico."""
    import sys
    return {
        "python_version": sys.version,
        "edge_tts_available": is_edge_tts_available(),
        "pydub_available": is_pydub_available(),
        "ffmpeg_available": is_ffmpeg_available(),
    }


# Vozes PT-BR disponíveis no edge-tts
PT_BR_VOICES = [
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "Feminino", "locale": "pt-BR"},
    {"id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "Masculino", "locale": "pt-BR"},
    {"id": "pt-BR-ThalitaNeural", "name": "Thalita", "gender": "Feminino", "locale": "pt-BR"},
    {"id": "pt-BR-BrendaNeural", "name": "Brenda", "gender": "Feminino", "locale": "pt-BR"},
    {"id": "pt-BR-DonatoNeural", "name": "Donato", "gender": "Masculino", "locale": "pt-BR"},
    {"id": "pt-BR-ElzaNeural", "name": "Elza", "gender": "Feminino", "locale": "pt-BR"},
]


def get_available_voices() -> List[dict]:
    """Retorna lista de vozes PT-BR disponíveis."""
    return PT_BR_VOICES


def speed_to_rate(speed: float) -> str:
    """Converte velocidade (0.5-2.0) para rate string do edge-tts."""
    percentage = int((speed - 1.0) * 100)
    if percentage >= 0:
        return f"+{percentage}%"
    else:
        return f"{percentage}%"


async def generate_audio_chunk_internal(
    text: str,
    voice_id: str,
    rate: str,
    output_path: Path
) -> Tuple[bool, str]:
    """Gera áudio para um chunk de texto (sem timeout)."""
    try:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate
        )

        await communicate.save(str(output_path))

        # Verifica se arquivo foi criado e tem tamanho > 0
        if not output_path.exists():
            return False, "Arquivo de áudio não foi criado"
        if output_path.stat().st_size == 0:
            return False, "Arquivo de áudio está vazio"

        return True, ""

    except Exception as e:
        error_msg = f"Erro edge-tts: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return False, error_msg


async def generate_audio_chunk(
    text: str,
    voice_id: str,
    rate: str,
    output_path: Path,
    chunk_index: int = 0,
    total_chunks: int = 1
) -> Tuple[bool, str]:
    """
    Gera áudio para um chunk de texto COM TIMEOUT.
    """
    logger.info(f"[CHUNK {chunk_index + 1}/{total_chunks}] Iniciando geração...")
    start_time = time.time()

    try:
        # Aplica timeout por chunk
        success, error = await asyncio.wait_for(
            generate_audio_chunk_internal(text, voice_id, rate, output_path),
            timeout=CHUNK_TIMEOUT_SECONDS
        )

        elapsed = time.time() - start_time
        if success:
            logger.info(f"[CHUNK {chunk_index + 1}/{total_chunks}] Concluído em {elapsed:.1f}s")
        else:
            logger.error(f"[CHUNK {chunk_index + 1}/{total_chunks}] Falhou após {elapsed:.1f}s: {error}")

        return success, error

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        error_msg = f"Timeout após {elapsed:.1f}s (limite: {CHUNK_TIMEOUT_SECONDS}s)"
        logger.error(f"[CHUNK {chunk_index + 1}/{total_chunks}] {error_msg}")
        return False, error_msg

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"Erro inesperado após {elapsed:.1f}s: {str(e)}"
        logger.error(f"[CHUNK {chunk_index + 1}/{total_chunks}] {error_msg}\n{traceback.format_exc()}")
        return False, error_msg


async def generate_audio(
    text: str,
    voice_id: str = "pt-BR-FranciscaNeural",
    speed: float = 1.0,
    output_dir: Path = None,
    job_id: str = None,
    progress_callback=None
) -> Tuple[Optional[Path], str, str]:
    """
    Gera áudio MP3 a partir de texto.

    Returns:
        Tupla (caminho_do_arquivo, mensagem_erro, modo)
        modo: "single" (MP3 único) ou "parts" (ZIP com partes)
    """
    job_start_time = time.time()
    logger.info(f"[JOB {job_id}] ===== INICIANDO GERAÇÃO DE ÁUDIO =====")
    logger.info(f"[JOB {job_id}] Texto: {len(text)} caracteres, voz: {voice_id}, velocidade: {speed}")

    if not text or not text.strip():
        logger.error(f"[JOB {job_id}] Texto vazio")
        return None, "Texto vazio para gerar áudio.", "single"

    # Verifica se edge-tts está disponível
    if not is_edge_tts_available():
        logger.error(f"[JOB {job_id}] edge-tts não está instalado")
        return None, "Serviço de voz não está disponível. Verifique a instalação.", "single"

    from app.utils.chunking import split_text_into_chunks
    from app.utils.file_utils import ensure_outputs_dir

    if output_dir is None:
        output_dir = ensure_outputs_dir()

    if job_id is None:
        job_id = str(uuid.uuid4())[:8]

    rate = speed_to_rate(speed)

    # Divide texto em chunks
    logger.info(f"[JOB {job_id}] Dividindo texto em chunks...")
    chunks = split_text_into_chunks(text, max_chars=3000)
    total_chunks = len(chunks)
    logger.info(f"[JOB {job_id}] Texto dividido em {total_chunks} chunks")

    if total_chunks == 1:
        # Texto pequeno, gera diretamente
        output_path = output_dir / f"{job_id}_ptbr.mp3"
        logger.info(f"[JOB {job_id}] Gerando áudio único...")

        success, error = await generate_audio_chunk(
            text, voice_id, rate, output_path,
            chunk_index=0, total_chunks=1
        )

        elapsed = time.time() - job_start_time
        if success:
            logger.info(f"[JOB {job_id}] ===== CONCLUÍDO em {elapsed:.1f}s (single) =====")
            return output_path, "", "single"
        else:
            logger.error(f"[JOB {job_id}] ===== FALHOU após {elapsed:.1f}s =====")
            return None, error, "single"

    else:
        # Texto longo - verifica se pydub está disponível
        can_concat = is_pydub_available()
        logger.info(f"[JOB {job_id}] pydub disponível: {can_concat}")

        chunk_files = []
        temp_dir = Path(tempfile.mkdtemp())
        logger.info(f"[JOB {job_id}] Diretório temporário: {temp_dir}")

        try:
            # Gera cada chunk com verificação de timeout total
            for i, chunk in enumerate(chunks):
                # Verifica timeout total do job
                elapsed_total = time.time() - job_start_time
                if elapsed_total > TOTAL_JOB_TIMEOUT_SECONDS:
                    error_msg = f"Timeout total do job ({TOTAL_JOB_TIMEOUT_SECONDS}s) excedido"
                    logger.error(f"[JOB {job_id}] {error_msg}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None, error_msg, "single"

                chunk_path = temp_dir / f"parte_{i + 1:02d}.mp3"

                success, error = await generate_audio_chunk(
                    chunk, voice_id, rate, chunk_path,
                    chunk_index=i, total_chunks=total_chunks
                )

                if not success:
                    # Limpa e retorna erro
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None, f"Falha na parte {i + 1}: {error}", "single"

                chunk_files.append(chunk_path)

                # Callback de progresso
                if progress_callback:
                    progress = 20 + int(60 * (i + 1) / total_chunks)
                    progress_callback(progress, f"Gerando parte {i + 1}/{total_chunks}...")

            logger.info(f"[JOB {job_id}] Todos os {total_chunks} chunks gerados com sucesso")

            if can_concat:
                # Tenta concatenar com pydub
                logger.info(f"[JOB {job_id}] [CONCAT] Iniciando concatenação com pydub...")
                concat_start = time.time()

                try:
                    from pydub import AudioSegment

                    combined = AudioSegment.empty()

                    for idx, chunk_path in enumerate(chunk_files):
                        logger.info(f"[JOB {job_id}] [CONCAT] Adicionando parte {idx + 1}/{len(chunk_files)}...")
                        audio = AudioSegment.from_mp3(chunk_path)
                        combined += audio
                        combined += AudioSegment.silent(duration=300)

                    output_path = output_dir / f"{job_id}_ptbr.mp3"
                    logger.info(f"[JOB {job_id}] [CONCAT] Exportando MP3 final...")
                    combined.export(output_path, format="mp3")

                    shutil.rmtree(temp_dir, ignore_errors=True)

                    concat_elapsed = time.time() - concat_start
                    total_elapsed = time.time() - job_start_time
                    logger.info(f"[JOB {job_id}] [CONCAT] Concatenação concluída em {concat_elapsed:.1f}s")
                    logger.info(f"[JOB {job_id}] ===== CONCLUÍDO em {total_elapsed:.1f}s (single) =====")
                    return output_path, "", "single"

                except Exception as e:
                    logger.warning(f"[JOB {job_id}] [CONCAT] Falha: {e}, usando fallback ZIP")
                    can_concat = False

            if not can_concat:
                # Cria ZIP com as partes
                logger.info(f"[JOB {job_id}] [ZIP] Criando ZIP com {len(chunk_files)} partes...")
                zip_start = time.time()

                zip_path = output_dir / f"{job_id}_ptbr_partes.zip"

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    instrucoes = (
                        "COMO OUVIR OS ÁUDIOS\n"
                        "====================\n\n"
                        f"Este ZIP contém {len(chunk_files)} partes do seu artigo.\n\n"
                        "Para ouvir na ordem correta:\n"
                        "1. Extraia todos os arquivos\n"
                        "2. Reproduza em ordem: parte_01.mp3, parte_02.mp3, etc.\n\n"
                        "Dica: A maioria dos players de áudio toca os arquivos\n"
                        "em ordem alfabética automaticamente.\n"
                    )
                    zf.writestr("LEIA-ME.txt", instrucoes)

                    for chunk_path in chunk_files:
                        zf.write(chunk_path, chunk_path.name)

                shutil.rmtree(temp_dir, ignore_errors=True)

                zip_elapsed = time.time() - zip_start
                total_elapsed = time.time() - job_start_time
                logger.info(f"[JOB {job_id}] [ZIP] ZIP criado em {zip_elapsed:.1f}s")
                logger.info(f"[JOB {job_id}] ===== CONCLUÍDO em {total_elapsed:.1f}s (parts) =====")
                return zip_path, "", "parts"

        except Exception as e:
            error_msg = f"Erro inesperado: {str(e)}"
            logger.error(f"[JOB {job_id}] {error_msg}\n{traceback.format_exc()}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, error_msg, "single"


def save_translated_text(
    text: str,
    output_dir: Path = None,
    job_id: str = None
) -> Tuple[Optional[Path], str]:
    """Salva o texto traduzido em arquivo TXT."""
    from app.utils.file_utils import ensure_outputs_dir

    if output_dir is None:
        output_dir = ensure_outputs_dir()

    if job_id is None:
        job_id = str(uuid.uuid4())[:8]

    try:
        output_path = output_dir / f"{job_id}_ptbr.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

        return output_path, ""

    except Exception as e:
        error_msg = f"Erro ao salvar texto: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def save_translated_pdf(
    text: str,
    title: str = "Artigo Traduzido",
    output_dir: Path = None,
    job_id: str = None
) -> Tuple[Optional[Path], str]:
    """Salva o texto traduzido em arquivo PDF."""
    from app.utils.file_utils import ensure_outputs_dir

    if output_dir is None:
        output_dir = ensure_outputs_dir()

    if job_id is None:
        job_id = str(uuid.uuid4())[:8]

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_JUSTIFY

        output_path = output_dir / f"{job_id}_ptbr.pdf"

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )

        story = []
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))

        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_para, body_style))

        doc.build(story)

        logger.info(f"PDF gerado: {output_path}")
        return output_path, ""

    except ImportError:
        return None, "reportlab não está instalado"

    except Exception as e:
        error_msg = f"Erro ao gerar PDF: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
