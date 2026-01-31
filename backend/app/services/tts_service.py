"""
Laris - Text-to-Speech Service
Geração de áudio usando edge-tts (Microsoft Edge Neural Voices).
"""

import asyncio
import logging
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


def check_pydub_available() -> bool:
    """
    Verifica se pydub e ffmpeg estão disponíveis.

    Returns:
        True se pydub pode concatenar áudios, False caso contrário
    """
    try:
        from pydub import AudioSegment
        # Tenta criar um segmento vazio para verificar se ffmpeg está disponível
        AudioSegment.empty()
        return True
    except Exception:
        return False


# Cache do resultado para não verificar toda vez
_pydub_available: Optional[bool] = None


def is_pydub_available() -> bool:
    """
    Retorna se pydub está disponível (com cache).
    """
    global _pydub_available
    if _pydub_available is None:
        _pydub_available = check_pydub_available()
    return _pydub_available

# Vozes PT-BR disponíveis no edge-tts
PT_BR_VOICES = [
    {
        "id": "pt-BR-FranciscaNeural",
        "name": "Francisca",
        "gender": "Feminino",
        "locale": "pt-BR"
    },
    {
        "id": "pt-BR-AntonioNeural",
        "name": "Antonio",
        "gender": "Masculino",
        "locale": "pt-BR"
    },
    {
        "id": "pt-BR-ThalitaNeural",
        "name": "Thalita",
        "gender": "Feminino",
        "locale": "pt-BR"
    },
    {
        "id": "pt-BR-BrendaNeural",
        "name": "Brenda",
        "gender": "Feminino",
        "locale": "pt-BR"
    },
    {
        "id": "pt-BR-DonatoNeural",
        "name": "Donato",
        "gender": "Masculino",
        "locale": "pt-BR"
    },
    {
        "id": "pt-BR-ElzaNeural",
        "name": "Elza",
        "gender": "Feminino",
        "locale": "pt-BR"
    },
]


def get_available_voices() -> List[dict]:
    """
    Retorna lista de vozes PT-BR disponíveis.

    Returns:
        Lista de dicionários com informações das vozes
    """
    return PT_BR_VOICES


def speed_to_rate(speed: float) -> str:
    """
    Converte velocidade (0.5-2.0) para rate string do edge-tts.

    Args:
        speed: Velocidade (1.0 = normal)

    Returns:
        String de rate (ex: "+0%", "-25%", "+50%")
    """
    # Converte speed para porcentagem
    # 1.0 = 0%, 0.5 = -50%, 2.0 = +100%
    percentage = int((speed - 1.0) * 100)

    if percentage >= 0:
        return f"+{percentage}%"
    else:
        return f"{percentage}%"


async def generate_audio_chunk(
    text: str,
    voice_id: str,
    rate: str,
    output_path: Path
) -> Tuple[bool, str]:
    """
    Gera áudio para um chunk de texto.

    Args:
        text: Texto para narrar
        voice_id: ID da voz
        rate: Taxa de velocidade (ex: "+0%")
        output_path: Caminho do arquivo de saída

    Returns:
        Tupla (sucesso, mensagem_erro)
    """
    try:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate
        )

        await communicate.save(str(output_path))
        return True, ""

    except Exception as e:
        error_msg = f"Erro ao gerar áudio: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def generate_audio(
    text: str,
    voice_id: str = "pt-BR-FranciscaNeural",
    speed: float = 1.0,
    output_dir: Path = None,
    job_id: str = None
) -> Tuple[Optional[Path], str, str]:
    """
    Gera áudio MP3 a partir de texto.

    Para textos longos, divide em chunks e concatena (se pydub disponível)
    ou retorna ZIP com as partes (se pydub não disponível).

    Args:
        text: Texto para narrar
        voice_id: ID da voz
        speed: Velocidade (0.5-2.0)
        output_dir: Diretório de saída
        job_id: ID do job (para nomear arquivo)

    Returns:
        Tupla (caminho_do_arquivo, mensagem_erro, modo)
        modo: "single" (MP3 único) ou "parts" (ZIP com partes)
    """
    if not text or not text.strip():
        return None, "Texto vazio para gerar áudio.", "single"

    from app.utils.chunking import split_text_into_chunks
    from app.utils.file_utils import OUTPUTS_DIR, ensure_outputs_dir

    # Usa diretório padrão se não especificado
    if output_dir is None:
        output_dir = ensure_outputs_dir()

    # Gera ID se não fornecido
    if job_id is None:
        job_id = str(uuid.uuid4())[:8]

    rate = speed_to_rate(speed)
    logger.info(f"Gerando áudio: voice={voice_id}, rate={rate}")

    # Divide texto em chunks
    chunks = split_text_into_chunks(text, max_chars=3000)
    logger.info(f"Texto dividido em {len(chunks)} chunks")

    if len(chunks) == 1:
        # Texto pequeno, gera diretamente
        output_path = output_dir / f"{job_id}_ptbr.mp3"
        success, error = await generate_audio_chunk(text, voice_id, rate, output_path)

        if success:
            return output_path, "", "single"
        else:
            return None, error, "single"

    else:
        # Texto longo - verifica se pydub está disponível
        can_concat = is_pydub_available()

        # Gera chunks de áudio
        chunk_files = []
        temp_dir = Path(tempfile.mkdtemp())

        try:
            for i, chunk in enumerate(chunks):
                chunk_path = temp_dir / f"parte_{i + 1:02d}.mp3"
                logger.info(f"Gerando chunk {i + 1}/{len(chunks)}...")

                success, error = await generate_audio_chunk(chunk, voice_id, rate, chunk_path)

                if not success:
                    # Limpa arquivos temporários
                    for f in chunk_files:
                        f.unlink(missing_ok=True)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None, f"Erro na parte {i + 1}: {error}", "single"

                chunk_files.append(chunk_path)

            if can_concat:
                # pydub disponível - concatena em MP3 único
                logger.info("Concatenando chunks de áudio com pydub...")
                try:
                    from pydub import AudioSegment

                    combined = AudioSegment.empty()

                    for chunk_path in chunk_files:
                        audio = AudioSegment.from_mp3(chunk_path)
                        combined += audio
                        # Adiciona pequena pausa entre chunks
                        combined += AudioSegment.silent(duration=300)

                    # Salva arquivo final
                    output_path = output_dir / f"{job_id}_ptbr.mp3"
                    combined.export(output_path, format="mp3")

                    # Limpa arquivos temporários
                    shutil.rmtree(temp_dir, ignore_errors=True)

                    logger.info(f"Áudio único gerado: {output_path}")
                    return output_path, "", "single"

                except Exception as e:
                    logger.warning(f"Falha ao concatenar, usando fallback ZIP: {e}")
                    # Se falhar, usa fallback ZIP
                    can_concat = False

            if not can_concat:
                # pydub não disponível ou falhou - cria ZIP com as partes
                logger.info("Criando ZIP com partes de áudio (pydub não disponível)...")

                zip_path = output_dir / f"{job_id}_ptbr_partes.zip"

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Adiciona instrução de uso
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

                    # Adiciona cada parte
                    for chunk_path in chunk_files:
                        zf.write(chunk_path, chunk_path.name)

                # Limpa arquivos temporários
                shutil.rmtree(temp_dir, ignore_errors=True)

                logger.info(f"ZIP com partes gerado: {zip_path}")
                return zip_path, "", "parts"

        except Exception as e:
            error_msg = f"Erro ao gerar áudio: {str(e)}"
            logger.error(error_msg)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, error_msg, "single"


def save_translated_text(
    text: str,
    output_dir: Path = None,
    job_id: str = None
) -> Tuple[Optional[Path], str]:
    """
    Salva o texto traduzido em arquivo TXT.

    Args:
        text: Texto para salvar
        output_dir: Diretório de saída
        job_id: ID do job

    Returns:
        Tupla (caminho_do_arquivo, mensagem_erro)
    """
    from app.utils.file_utils import OUTPUTS_DIR, ensure_outputs_dir

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
    """
    Salva o texto traduzido em arquivo PDF.

    Args:
        text: Texto para salvar
        title: Título do documento
        output_dir: Diretório de saída
        job_id: ID do job

    Returns:
        Tupla (caminho_do_arquivo, mensagem_erro)
    """
    from app.utils.file_utils import OUTPUTS_DIR, ensure_outputs_dir

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

        # Configura documento
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )

        # Conteúdo
        story = []

        # Título
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))

        # Texto em parágrafos
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Limpa e escapa caracteres especiais
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_para, body_style))

        # Gera PDF
        doc.build(story)

        logger.info(f"PDF gerado: {output_path}")
        return output_path, ""

    except ImportError:
        return None, "reportlab não está instalado. Instale: pip install reportlab"

    except Exception as e:
        error_msg = f"Erro ao gerar PDF: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
