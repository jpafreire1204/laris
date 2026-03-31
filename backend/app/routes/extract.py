"""
Laris - Extract route.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.models.schemas import ExtractResponse
from app.services.extraction import extract_document_from_file, get_text_preview
from app.services.language_detection import detect_language, get_language_name, is_portuguese
from app.utils.file_utils import ensure_outputs_dir, is_valid_upload, save_debug_json, save_debug_text

router = APIRouter()
logger = logging.getLogger(__name__)

# Referencias aos arquivos originais para outras rotas locais.
original_files: dict[str, str] = {}
extraction_debug_registry: dict[str, dict[str, str]] = {}

MAX_FILE_SIZE_MB = 150
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/extract", response_model=ExtractResponse)
async def extract_text(file: UploadFile = File(...)):
    """Extrai texto e diagnosticos de PDF, DOCX ou TXT."""
    is_valid, error_msg = is_valid_upload(file.filename)
    if not is_valid:
        return ExtractResponse(success=False, error=error_msg)

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Erro ao ler arquivo: %s", exc)
        return ExtractResponse(success=False, error="Erro ao ler o arquivo. Tente novamente.")

    if len(content) > MAX_FILE_SIZE:
        return ExtractResponse(
            success=False,
            error=f"Arquivo muito grande. Maximo permitido: {MAX_FILE_SIZE_MB} MB",
        )

    extraction = extract_document_from_file(content, file.filename)
    if not extraction.text:
        return ExtractResponse(
            success=False,
            error=extraction.error or "Nao foi possivel extrair texto do arquivo.",
        )

    file_id = str(uuid.uuid4())[:8]
    if file.filename.lower().endswith(".pdf"):
        try:
            output_dir = ensure_outputs_dir()
            original_path = output_dir / f"{file_id}_original.pdf"
            with open(original_path, "wb") as handle:
                handle.write(content)
            original_files[file_id] = str(original_path)
        except Exception as exc:
            logger.warning("Erro ao salvar PDF original: %s", exc)

    text = extraction.text
    detected_lang = detect_language(text)
    lang_name = get_language_name(detected_lang) if detected_lang else "Nao detectado"
    is_pt = is_portuguese(detected_lang) if detected_lang else False
    preview = get_text_preview(text)

    diagnostics = extraction.diagnostics or {}
    warnings = diagnostics.get("warnings", [])
    page_metrics = diagnostics.get("page_metrics", [])
    page_characters = [
        {
            "page_number": page.get("page_number"),
            "final_chars": page.get("final_chars"),
        }
        for page in page_metrics
    ]

    debug_identifier = file_id or str(uuid.uuid4())[:8]
    raw_text = extraction.debug_data.get("raw_extracted_text", extraction.text)
    ordered_text = extraction.debug_data.get("cleaned_ordered_text", extraction.text)
    final_text = extraction.debug_data.get("final_text", extraction.text)
    raw_path = save_debug_text("extract", debug_identifier, "raw_extracted_text", raw_text)
    ordered_path = save_debug_text("extract", debug_identifier, "cleaned_ordered_text", ordered_text)
    final_path = save_debug_text("extract", debug_identifier, "final_text", final_text)
    debug_json_path = save_debug_json(
        "extract",
        debug_identifier,
        "summary",
        {
            "debug_id": debug_identifier,
            "filename": file.filename,
            "bytes_received": len(content),
            "page_count": diagnostics.get("page_count"),
            "pages_extracted": diagnostics.get("pages_extracted"),
            "page_characters": page_characters,
            "removed_patterns": diagnostics.get("removed_patterns", {}),
            "total_chars_before_cleaning": diagnostics.get("total_chars_before_cleaning"),
            "total_chars_after_cleaning": diagnostics.get("total_chars_after_cleaning"),
            "warnings": warnings,
            "raw_text_path": str(raw_path),
            "ordered_text_path": str(ordered_path),
            "final_text_path": str(final_path),
        },
    )
    extraction_debug_registry[debug_identifier] = {
        "summary_path": str(debug_json_path),
        "raw_text_path": str(raw_path),
        "ordered_text_path": str(ordered_path),
        "final_text_path": str(final_path),
        "filename": file.filename,
    }
    diagnostics["debug_id"] = debug_identifier
    diagnostics["debug_paths"] = extraction_debug_registry[debug_identifier]

    logger.info(
        "Extracao concluida: arquivo=%s chars=%s idioma=%s paginas=%s",
        file.filename,
        len(text),
        detected_lang,
        diagnostics.get("page_count"),
    )
    logger.info("Extracao page metrics: %s", page_characters)
    logger.info("Extracao final preview (inicio): %s", text[:500])
    logger.info("Extracao final preview (fim): %s", text[-500:])

    return ExtractResponse(
        success=True,
        text=text,
        preview=preview,
        detected_language=detected_lang or "",
        language_name=lang_name,
        is_portuguese=is_pt,
        char_count=len(text),
        file_id=file_id,
        diagnostics=diagnostics,
        warnings=warnings,
    )


@router.get("/debug/extract/{debug_id}")
async def get_extract_debug(debug_id: str):
    """Retorna artefatos de debug da extracao local."""
    record = extraction_debug_registry.get(debug_id)
    if not record:
        debug_dir = ensure_outputs_dir() / "debug" / "extract" / debug_id
        if not debug_dir.exists():
            return JSONResponse({"error": "Debug de extracao nao encontrado."}, status_code=404)
        record = {
            "summary_path": str(debug_dir / "summary.json"),
            "raw_text_path": str(debug_dir / "raw_extracted_text.txt"),
            "ordered_text_path": str(debug_dir / "cleaned_ordered_text.txt"),
            "final_text_path": str(debug_dir / "final_text.txt"),
        }

    def _read_text(path_value: str) -> str:
        path = Path(path_value)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    return JSONResponse(
        {
            "debug_id": debug_id,
            "summary_path": record.get("summary_path"),
            "raw_text_path": record.get("raw_text_path"),
            "ordered_text_path": record.get("ordered_text_path"),
            "final_text_path": record.get("final_text_path"),
            "raw_extracted_text": _read_text(record.get("raw_text_path", "")),
            "cleaned_ordered_text": _read_text(record.get("ordered_text_path", "")),
            "final_text": _read_text(record.get("final_text_path", "")),
        }
    )
