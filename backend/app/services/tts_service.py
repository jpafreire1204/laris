"""
Laris - Text-to-Speech Service
Geração de áudio usando edge-tts (Microsoft Edge Neural Voices).
SEMPRE gera UM único arquivo MP3 final usando ffmpeg concat demuxer.
"""

import asyncio
import logging
import subprocess
import tempfile
import shutil
import time
import traceback
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import uuid

logger = logging.getLogger(__name__)

# Configurações
MAX_RETRIES_PER_CHUNK = 1  # Retry 1x se falhar
RETRY_DELAY_SECONDS = 2   # Espera entre retries


def check_ffmpeg_available() -> bool:
    """Verifica se ffmpeg está disponível no PATH."""
    return shutil.which("ffmpeg") is not None


def check_edge_tts_available() -> bool:
    """Verifica se edge-tts está disponível."""
    try:
        import edge_tts
        return True
    except ImportError:
        return False


def check_google_translate_available() -> Tuple[bool, List[str]]:
    """
    Verifica se Google Translate (via deep-translator) está disponível.

    Returns:
        Tupla (disponível, idiomas_suportados)
    """
    try:
        from deep_translator import GoogleTranslator

        # Testa uma tradução simples
        translator = GoogleTranslator(source='en', target='pt')
        result = translator.translate("test")

        if result:
            # Google Translate suporta muitos idiomas
            supported = ['en->pt', 'es->pt', 'fr->pt', 'de->pt', 'it->pt', 'auto->pt']
            return True, supported
        return False, []

    except ImportError:
        return False, []
    except Exception as e:
        logger.warning(f"Erro ao verificar Google Translate: {e}")
        return False, []


# Cache dos resultados
_ffmpeg_available: Optional[bool] = None
_edge_tts_available: Optional[bool] = None


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

    google_available, supported_pairs = check_google_translate_available()

    return {
        "python_version": sys.version,
        "edge_tts_available": is_edge_tts_available(),
        "ffmpeg_available": is_ffmpeg_available(),
        "google_translate_available": google_available,
        "translation_pairs": supported_pairs,
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
    percentage = int(round((speed - 1.0) * 100))
    if percentage >= 0:
        return f"+{percentage}%"
    else:
        return f"{percentage}%"


def concat_mp3_ffmpeg(parts: List[Path], output: Path) -> Tuple[bool, str]:
    """
    Concatena múltiplos arquivos MP3 em um único usando ffmpeg concat demuxer.

    Args:
        parts: Lista de Paths dos arquivos MP3 a concatenar
        output: Path do arquivo de saída

    Returns:
        Tupla (sucesso, mensagem_erro)
    """
    if not parts:
        return False, "Nenhum arquivo para concatenar"

    if not is_ffmpeg_available():
        return False, (
            "ffmpeg não está instalado ou não está no PATH.\n"
            "Instale o ffmpeg:\n"
            "  - Windows: baixe de https://ffmpeg.org/download.html e adicione ao PATH\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Linux: sudo apt install ffmpeg"
        )

    # Cria arquivo de lista para o concat demuxer
    list_file = parts[0].parent / "concat_list.txt"

    try:
        # Escreve arquivo de lista com paths absolutos
        with open(list_file, 'w', encoding='utf-8') as f:
            for part in parts:
                # Escapa aspas simples no path
                safe_path = str(part.absolute()).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        logger.info(f"[FFMPEG] Arquivo de lista criado: {list_file}")
        logger.info(f"[FFMPEG] Concatenando {len(parts)} arquivos...")

        # Executa ffmpeg
        cmd = [
            "ffmpeg",
            "-y",                    # Sobrescreve sem perguntar
            "-f", "concat",          # Formato concat
            "-safe", "0",            # Permite paths absolutos
            "-i", str(list_file),    # Arquivo de lista
            "-c", "copy",            # Copia sem recodificar (rápido!)
            str(output)
        ]

        logger.info(f"[FFMPEG] Comando: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos max
        )

        if result.returncode != 0:
            error_msg = f"ffmpeg falhou (código {result.returncode}): {result.stderr}"
            logger.error(f"[FFMPEG] {error_msg}")
            return False, error_msg

        # Verifica se arquivo foi criado
        if not output.exists() or output.stat().st_size == 0:
            return False, "ffmpeg não gerou arquivo de saída válido"

        logger.info(f"[FFMPEG] Concatenação concluída: {output} ({output.stat().st_size} bytes)")
        return True, ""

    except subprocess.TimeoutExpired:
        return False, "ffmpeg demorou muito (timeout de 5 minutos)"
    except Exception as e:
        error_msg = f"Erro ao executar ffmpeg: {str(e)}"
        logger.error(f"[FFMPEG] {error_msg}\n{traceback.format_exc()}")
        return False, error_msg
    finally:
        # Remove arquivo de lista
        if list_file.exists():
            list_file.unlink()


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
    Gera áudio para um chunk de texto SEM TIMEOUT.
    Inclui retry automático em caso de falha.
    """
    logger.info(f"[CHUNK {chunk_index + 1}/{total_chunks}] Iniciando geração...")
    start_time = time.time()
    last_error = ""

    for attempt in range(MAX_RETRIES_PER_CHUNK + 1):
        try:
            if attempt > 0:
                logger.info(f"[CHUNK {chunk_index + 1}/{total_chunks}] Tentativa {attempt + 1}/{MAX_RETRIES_PER_CHUNK + 1}...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

            success, error = await generate_audio_chunk_internal(text, voice_id, rate, output_path)

            elapsed = time.time() - start_time
            if success:
                logger.info(f"[CHUNK {chunk_index + 1}/{total_chunks}] Concluído em {elapsed:.1f}s")
                return True, ""
            else:
                last_error = error
                logger.warning(f"[CHUNK {chunk_index + 1}/{total_chunks}] Tentativa {attempt + 1} falhou: {error}")

        except Exception as e:
            elapsed = time.time() - start_time
            last_error = f"Erro: {str(e)}"
            logger.warning(f"[CHUNK {chunk_index + 1}/{total_chunks}] Tentativa {attempt + 1} erro: {last_error}")

    elapsed = time.time() - start_time
    final_error = f"Falha após {MAX_RETRIES_PER_CHUNK + 1} tentativas ({elapsed:.1f}s): {last_error}"
    logger.error(f"[CHUNK {chunk_index + 1}/{total_chunks}] {final_error}")
    return False, final_error


async def generate_audio(
    text: str,
    voice_id: str = "pt-BR-FranciscaNeural",
    speed: float = 1.0,
    output_dir: Path = None,
    job_id: str = None,
    progress_callback: Callable[[int, str], None] = None
) -> Tuple[Optional[Path], str, str]:
    """
    Gera áudio MP3 a partir de texto.
    SEMPRE retorna UM único arquivo MP3 (concatenado com ffmpeg).

    Returns:
        Tupla (caminho_do_arquivo, mensagem_erro, modo)
        modo: sempre "single" (MP3 único)
    """
    job_start_time = time.time()
    logger.info(f"[JOB {job_id}] ===== INICIANDO GERAÇÃO DE ÁUDIO =====")
    logger.info(f"[JOB {job_id}] Texto: {len(text)} caracteres, voz: {voice_id}, velocidade: {speed}")

    if not text or not text.strip():
        logger.error(f"[JOB {job_id}] Texto vazio")
        return None, "Texto vazio para gerar áudio.", "single"

    # Preprocess: strip references and noise
    from app.utils.text_preprocessing import preprocess_for_tts
    text = preprocess_for_tts(text)
    logger.info(f"[JOB {job_id}] Texto após pré-processamento: {len(text)} caracteres")

    if not text or not text.strip():
        logger.error(f"[JOB {job_id}] Texto vazio após pré-processamento")
        return None, "Texto ficou vazio após remover referências e ruído.", "single"

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

    output_path = output_dir / f"{job_id}_final.mp3"

    if total_chunks == 1:
        # Texto pequeno, gera diretamente
        logger.info(f"[JOB {job_id}] Gerando áudio único...")

        if progress_callback:
            progress_callback(20, "Gerando áudio...")

        success, error = await generate_audio_chunk(
            text, voice_id, rate, output_path,
            chunk_index=0, total_chunks=1
        )

        elapsed = time.time() - job_start_time
        if success:
            logger.info(f"[JOB {job_id}] ===== CONCLUÍDO em {elapsed:.1f}s =====")
            return output_path, "", "single"
        else:
            logger.error(f"[JOB {job_id}] ===== FALHOU após {elapsed:.1f}s =====")
            return None, error, "single"

    else:
        # Texto longo - verifica se ffmpeg está disponível ANTES de começar
        if not is_ffmpeg_available():
            error_msg = (
                "ffmpeg não está instalado. Necessário para processar textos longos.\n"
                "Instale o ffmpeg:\n"
                "  - Windows: baixe de https://ffmpeg.org/download.html e adicione ao PATH\n"
                "  - macOS: brew install ffmpeg\n"
                "  - Linux: sudo apt install ffmpeg"
            )
            logger.error(f"[JOB {job_id}] {error_msg}")
            return None, error_msg, "single"

        chunk_files = []
        temp_dir = Path(tempfile.mkdtemp())
        logger.info(f"[JOB {job_id}] Diretório temporário: {temp_dir}")

        try:
            # Gera cada chunk
            for i, chunk in enumerate(chunks):
                chunk_path = temp_dir / f"parte_{i + 1:02d}.mp3"

                if progress_callback:
                    progress = 10 + int(60 * i / total_chunks)
                    progress_callback(progress, f"Gerando parte {i + 1}/{total_chunks}...")

                logger.info(f"[JOB {job_id}] Processando chunk {i + 1}/{total_chunks} ({len(chunk)} chars)...")

                success, error = await generate_audio_chunk(
                    chunk, voice_id, rate, chunk_path,
                    chunk_index=i, total_chunks=total_chunks
                )

                if not success:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None, f"Falha na parte {i + 1}/{total_chunks}: {error}", "single"

                chunk_files.append(chunk_path)

            logger.info(f"[JOB {job_id}] Todos os {total_chunks} chunks gerados")

            # Concatena com ffmpeg
            if progress_callback:
                progress_callback(75, "Juntando partes em 1 MP3...")

            logger.info(f"[JOB {job_id}] [CONCAT] Concatenando {len(chunk_files)} partes com ffmpeg...")
            concat_start = time.time()

            success, error = concat_mp3_ffmpeg(chunk_files, output_path)

            if not success:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None, f"Erro ao concatenar áudio: {error}", "single"

            concat_elapsed = time.time() - concat_start
            total_elapsed = time.time() - job_start_time

            logger.info(f"[JOB {job_id}] [CONCAT] Concatenação concluída em {concat_elapsed:.1f}s")
            logger.info(f"[JOB {job_id}] ===== CONCLUÍDO em {total_elapsed:.1f}s =====")

            # Limpa arquivos temporários
            shutil.rmtree(temp_dir, ignore_errors=True)

            return output_path, "", "single"

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
        output_path = output_dir / f"{job_id}_texto.txt"

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

        output_path = output_dir / f"{job_id}_artigo.pdf"

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
