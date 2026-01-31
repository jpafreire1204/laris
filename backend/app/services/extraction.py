"""
Laris - Text Extraction Service
Extrai texto de PDFs, DOCX e arquivos de texto.
"""

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf_pypdf(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de PDF usando pypdf.

    Args:
        file_content: Conteúdo do arquivo PDF em bytes

    Returns:
        Texto extraído ou None em caso de erro
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []

        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Erro ao extrair página {page_num}: {e}")

        text = '\n\n'.join(text_parts)
        return text.strip() if text.strip() else None

    except Exception as e:
        logger.error(f"Erro pypdf: {e}")
        return None


def extract_text_from_pdf_pdfplumber(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de PDF usando pdfplumber (fallback).

    Args:
        file_content: Conteúdo do arquivo PDF em bytes

    Returns:
        Texto extraído ou None em caso de erro
    """
    try:
        import pdfplumber

        text_parts = []

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Erro ao extrair página {page_num}: {e}")

        text = '\n\n'.join(text_parts)
        return text.strip() if text.strip() else None

    except Exception as e:
        logger.error(f"Erro pdfplumber: {e}")
        return None


def extract_text_from_docx(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de arquivo DOCX.

    Args:
        file_content: Conteúdo do arquivo DOCX em bytes

    Returns:
        Texto extraído ou None em caso de erro
    """
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = '\n\n'.join(paragraphs)
        return text.strip() if text.strip() else None

    except Exception as e:
        logger.error(f"Erro docx: {e}")
        return None


def extract_text_from_txt(file_content: bytes) -> Optional[str]:
    """
    Extrai texto de arquivo TXT.

    Args:
        file_content: Conteúdo do arquivo TXT em bytes

    Returns:
        Texto extraído ou None em caso de erro
    """
    # Tenta diferentes encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            text = file_content.decode(encoding)
            return text.strip() if text.strip() else None
        except UnicodeDecodeError:
            continue

    logger.error("Não foi possível decodificar o arquivo de texto")
    return None


def extract_text_from_file(file_content: bytes, filename: str) -> tuple[Optional[str], str]:
    """
    Extrai texto de um arquivo baseado na extensão.

    Args:
        file_content: Conteúdo do arquivo em bytes
        filename: Nome do arquivo (para identificar extensão)

    Returns:
        Tupla (texto_extraído, mensagem_de_erro)
    """
    ext = Path(filename).suffix.lower()
    text = None
    error_msg = ""

    if ext == '.pdf':
        # Tenta pypdf primeiro
        text = extract_text_from_pdf_pypdf(file_content)

        if not text or len(text) < 50:
            logger.info("pypdf falhou ou retornou pouco texto, tentando pdfplumber...")
            text = extract_text_from_pdf_pdfplumber(file_content)

        if not text:
            error_msg = (
                "Não consegui ler esse PDF. O arquivo pode estar protegido, "
                "ser uma imagem escaneada, ou estar corrompido. "
                "Tente salvar o conteúdo como texto (.txt) ou usar outro PDF."
            )

    elif ext == '.docx':
        text = extract_text_from_docx(file_content)
        if not text:
            error_msg = (
                "Não consegui ler esse documento Word. "
                "O arquivo pode estar corrompido. Tente salvar como .txt."
            )

    elif ext == '.txt':
        text = extract_text_from_txt(file_content)
        if not text:
            error_msg = (
                "Não consegui ler esse arquivo de texto. "
                "Verifique se o arquivo não está vazio."
            )

    else:
        error_msg = f"Tipo de arquivo não suportado: {ext}. Use PDF, DOCX ou TXT."

    # Limpa o texto extraído
    if text:
        # Remove espaços excessivos
        import re
        text = re.sub(r' +', ' ', text)
        # Remove linhas em branco excessivas
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

    return text, error_msg


def get_text_preview(text: str, max_chars: int = 1500) -> str:
    """
    Retorna uma prévia do texto.

    Args:
        text: Texto completo
        max_chars: Número máximo de caracteres

    Returns:
        Prévia do texto
    """
    if len(text) <= max_chars:
        return text

    # Tenta cortar em um ponto natural
    preview = text[:max_chars]
    last_period = preview.rfind('.')
    last_newline = preview.rfind('\n')

    cut_point = max(last_period, last_newline)
    if cut_point > max_chars // 2:
        preview = preview[:cut_point + 1]

    return preview + "\n\n[...]"
