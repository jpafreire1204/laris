"""
Laris - Extract Route
Endpoint para extração de texto de arquivos.
"""

import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import ExtractResponse
from app.services.extraction import extract_text_from_file, get_text_preview
from app.services.language_detection import detect_language, get_language_name, is_portuguese
from app.utils.file_utils import is_valid_upload, ensure_outputs_dir

router = APIRouter()
logger = logging.getLogger(__name__)

# Armazena referências aos arquivos originais
original_files: dict = {}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/extract", response_model=ExtractResponse)
async def extract_text(file: UploadFile = File(...)):
    """
    Extrai texto de um arquivo PDF, DOCX ou TXT.

    Retorna o texto extraído, prévia, e idioma detectado.
    """
    # Valida tipo de arquivo
    is_valid, error_msg = is_valid_upload(file.filename)
    if not is_valid:
        return ExtractResponse(
            success=False,
            error=error_msg
        )

    # Lê conteúdo do arquivo
    try:
        content = await file.read()

        # Verifica tamanho
        if len(content) > MAX_FILE_SIZE:
            return ExtractResponse(
                success=False,
                error=f"Arquivo muito grande. Máximo permitido: 50 MB"
            )

    except Exception as e:
        logger.error(f"Erro ao ler arquivo: {e}")
        return ExtractResponse(
            success=False,
            error="Erro ao ler o arquivo. Tente novamente."
        )

    # Extrai texto
    text, error = extract_text_from_file(content, file.filename)

    if not text:
        return ExtractResponse(
            success=False,
            error=error or "Não foi possível extrair texto do arquivo."
        )

    # Salva arquivo original se for PDF (para tradução com layout)
    file_id = None
    if file.filename.lower().endswith('.pdf'):
        try:
            file_id = str(uuid.uuid4())[:8]
            output_dir = ensure_outputs_dir()
            original_path = output_dir / f"{file_id}_original.pdf"
            with open(original_path, 'wb') as f:
                f.write(content)
            original_files[file_id] = str(original_path)
            logger.info(f"PDF original salvo: {original_path}")
        except Exception as e:
            logger.warning(f"Erro ao salvar PDF original: {e}")

    # Detecta idioma
    detected_lang = detect_language(text)
    lang_name = get_language_name(detected_lang) if detected_lang else "Não detectado"
    is_pt = is_portuguese(detected_lang) if detected_lang else False

    # Gera prévia
    preview = get_text_preview(text)

    logger.info(f"Texto extraído: {len(text)} caracteres, idioma: {detected_lang}")

    return ExtractResponse(
        success=True,
        text=text,
        preview=preview,
        detected_language=detected_lang or "",
        language_name=lang_name,
        is_portuguese=is_pt,
        char_count=len(text),
        file_id=file_id
    )
