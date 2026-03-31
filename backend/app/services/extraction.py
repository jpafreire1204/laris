"""
Document extraction helpers with page-level PDF diagnostics.
"""

from __future__ import annotations

import io
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.utils.text_preprocessing import (
    clean_document_text,
    line_signature,
    normalize_line,
    should_drop_line,
)

logger = logging.getLogger(__name__)

HEADER_FOOTER_LINE_COUNT = 3


@dataclass
class PageExtractionDiagnostics:
    page_number: int
    final_chars: int = 0
    empty: bool = False
    discarded: bool = False
    removed_lines: int = 0
    removed_patterns: dict[str, int] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    text: Optional[str]
    error: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    debug_data: dict[str, Any] = field(default_factory=dict)


def _find_repeated_margin_signatures(page_texts: list[str]) -> set[str]:
    header_counter: Counter[str] = Counter()
    footer_counter: Counter[str] = Counter()
    total_pages = len(page_texts)
    threshold = max(3, total_pages // 4)

    for page_text in page_texts:
        lines = [normalize_line(line) for line in page_text.splitlines() if normalize_line(line)]
        header_lines = lines[:HEADER_FOOTER_LINE_COUNT]
        footer_lines = lines[-HEADER_FOOTER_LINE_COUNT:]
        for line in header_lines:
            signature = line_signature(line)
            if len(signature) >= 10 and len(line.split()) <= 12 and not line.endswith((".", "!", "?")):
                header_counter[signature] += 1
        for line in footer_lines:
            signature = line_signature(line)
            if len(signature) >= 10 and len(line.split()) <= 12 and not line.endswith((".", "!", "?")):
                footer_counter[signature] += 1

    repeated = {
        signature
        for signature, count in header_counter.items()
        if count >= threshold
    }
    repeated.update(
        signature
        for signature, count in footer_counter.items()
        if count >= threshold
    )
    return repeated


def _clean_page_text(
    page_text: str,
    repeated_margin_signatures: set[str],
) -> tuple[str, Counter[str], int]:
    removed_patterns: Counter[str] = Counter()
    removed_lines = 0
    kept_lines: list[str] = []

    for line in page_text.splitlines():
        drop, reason = should_drop_line(line, repeated_margin_signatures=repeated_margin_signatures)
        if drop:
            removed_lines += 1
            if reason and reason != "empty":
                removed_patterns[reason] += 1
            continue
        kept_lines.append(line)

    page_cleaned = "\n".join(kept_lines).strip()
    return page_cleaned, removed_patterns, removed_lines


def _extract_pdf_document(file_content: bytes) -> ExtractionResult:
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - dependency issue
        logger.error("Erro ao carregar PyMuPDF: %s", exc)
        return ExtractionResult(
            text=None,
            error="A biblioteca de leitura de PDF (PyMuPDF) nao esta disponivel.",
        )

    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
    except Exception as exc:
        logger.error("Erro ao abrir PDF: %s", exc)
        return ExtractionResult(
            text=None,
            error=(
                "Nao consegui abrir esse PDF. O arquivo pode estar protegido, "
                "corrompido ou sem camada de texto selecionavel."
            ),
        )

    pages: list[str] = []
    page_diagnostics: list[PageExtractionDiagnostics] = []

    for index, page in enumerate(doc):
        try:
            text = page.get_text("text").strip()
        except Exception as exc:
            logger.warning("Erro ao extrair texto da pagina %s: %s", index + 1, exc)
            text = ""

        page_diag = PageExtractionDiagnostics(
            page_number=index + 1,
            final_chars=len(text),
            empty=not bool(text),
        )
        pages.append(text)
        page_diagnostics.append(page_diag)

    repeated_margin_signatures = _find_repeated_margin_signatures(pages)
    cleaned_pages: list[str] = []
    removed_patterns_total: Counter[str] = Counter()

    for idx, page_text in enumerate(pages):
        page_cleaned, page_removed_patterns, removed_lines = _clean_page_text(
            page_text,
            repeated_margin_signatures=repeated_margin_signatures,
        )
        page_diagnostics[idx].removed_patterns = dict(sorted(page_removed_patterns.items()))
        page_diagnostics[idx].removed_lines = removed_lines
        page_diagnostics[idx].discarded = not bool(page_cleaned.strip())
        page_diagnostics[idx].final_chars = len(page_cleaned)
        removed_patterns_total.update(page_removed_patterns)
        if page_cleaned.strip():
            cleaned_pages.append(page_cleaned.strip())

    joined_text = "\n\n".join(cleaned_pages).strip()
    document_cleanup = clean_document_text(joined_text, include_references=True)
    final_text = document_cleanup["text"]
    removed_patterns_total.update(document_cleanup["removed_patterns"])

    diagnostics = {
        "page_count": len(page_diagnostics),
        "pages_extracted": sum(1 for page in page_diagnostics if not page.discarded),
        "empty_pages": [page.page_number for page in page_diagnostics if page.empty],
        "skipped_pages": [page.page_number for page in page_diagnostics if page.discarded],
        "total_chars_before_cleaning": sum(len(page_text) for page_text in pages),
        "total_chars_after_cleaning": len(final_text),
        "removed_characters": document_cleanup["removed_characters"],
        "removed_patterns": dict(sorted(removed_patterns_total.items())),
        "page_metrics": [asdict(page) for page in page_diagnostics],
        "warnings": list(document_cleanup["warnings"]),
        "truncated": False,
    }

    logger.info(
        "PDF extraido: %s paginas, %s paginas com texto, %s chars finais",
        diagnostics["page_count"],
        diagnostics["pages_extracted"],
        diagnostics["total_chars_after_cleaning"],
    )

    return ExtractionResult(
        text=final_text if final_text else None,
        error="" if final_text else "Nao foi possivel extrair texto desse PDF.",
        diagnostics=diagnostics,
        debug_data={
            "raw_extracted_text": "\n\n".join(page_text.strip() for page_text in pages if page_text.strip()),
            "cleaned_ordered_text": joined_text,
            "final_text": final_text,
        },
    )


def extract_text_from_pdf_pypdf(file_content: bytes) -> Optional[str]:
    """Compatibility helper used by older imports/tests."""
    return _extract_pdf_document(file_content).text


def extract_text_from_pdf_pdfplumber(file_content: bytes) -> Optional[str]:
    """Compatibility helper used by older imports/tests."""
    return _extract_pdf_document(file_content).text


def extract_text_from_docx(file_content: bytes) -> Optional[str]:
    """Extract text from DOCX files."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_content))
        paragraphs = [normalize_line(paragraph.text) for paragraph in doc.paragraphs if normalize_line(paragraph.text)]
        text = "\n\n".join(paragraphs).strip()
        return text or None
    except Exception as exc:
        logger.error("Erro docx: %s", exc)
        return None


def extract_text_from_txt(file_content: bytes) -> Optional[str]:
    """Extract text from plain-text files with encoding fallback."""
    for encoding in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            text = file_content.decode(encoding)
            text = clean_document_text(text, include_references=True)["text"]
            return text or None
        except UnicodeDecodeError:
            continue

    logger.error("Nao foi possivel decodificar o arquivo de texto")
    return None


def extract_document_from_file(file_content: bytes, filename: str) -> ExtractionResult:
    """Extract text and diagnostics from PDF, DOCX or TXT files."""
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return _extract_pdf_document(file_content)

    if extension == ".docx":
        text = extract_text_from_docx(file_content)
        return ExtractionResult(
            text=text,
            error="" if text else "Nao consegui ler esse arquivo DOCX.",
            diagnostics={
                "page_count": None,
                "pages_extracted": None,
                "removed_patterns": {},
                "warnings": [],
            },
            debug_data={
                "raw_extracted_text": text or "",
                "cleaned_ordered_text": text or "",
                "final_text": text or "",
            },
        )

    if extension == ".txt":
        text = extract_text_from_txt(file_content)
        return ExtractionResult(
            text=text,
            error="" if text else "Nao consegui ler esse arquivo TXT.",
            diagnostics={
                "page_count": None,
                "pages_extracted": None,
                "removed_patterns": {},
                "warnings": [],
            },
            debug_data={
                "raw_extracted_text": text or "",
                "cleaned_ordered_text": text or "",
                "final_text": text or "",
            },
        )

    return ExtractionResult(
        text=None,
        error=f"Tipo de arquivo nao suportado: {extension}. Use PDF, DOCX ou TXT.",
    )


def extract_text_from_file(file_content: bytes, filename: str) -> tuple[Optional[str], str]:
    """Backwards-compatible wrapper returning only text and error."""
    result = extract_document_from_file(file_content, filename)
    return result.text, result.error


def get_text_preview(text: str, max_chars: int = 1500) -> str:
    """Return a natural preview of the extracted text."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text

    preview = text[:max_chars]
    cut_candidates = [preview.rfind(marker) for marker in (". ", "\n\n", "\n")]
    cut_point = max(cut_candidates)
    if cut_point > max_chars // 2:
        preview = preview[: cut_point + 1].strip()

    return preview.rstrip() + "\n\n[...]"
