"""
Utilities for document cleanup and speech-only normalization.

The pipeline keeps two versions of the text:
- display_text: cleaned article text used by the UI and translation flow
- speech_text: voice-specific text normalized for TTS
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any

try:
    from app.utils.english_terms import ENGLISH_TERMS_RE, ENGLISH_ACRONYMS_RE
except Exception:  # pragma: no cover - optional helper file
    ENGLISH_TERMS_RE = re.compile(r"$^")
    ENGLISH_ACRONYMS_RE = re.compile(r"$^")


REFERENCE_HEADINGS = [
    r"references",
    r"referencias",
    r"bibliography",
    r"bibliografia",
    r"works cited",
    r"literatura citada",
    r"referencias bibliograficas",
]

REFERENCE_HEADER_RE = re.compile(
    r"^\s*(?:" + "|".join(REFERENCE_HEADINGS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

NUMBERED_REFERENCE_LINE_RE = re.compile(
    r"^\s*(?:\[\d+\]|\d+\.)\s+[A-Z0-9]",
    re.MULTILINE,
)

LINE_NOISE_PATTERNS: dict[str, re.Pattern[str]] = {
    "machine_translated": re.compile(
        r"translated by google|traducao do google|traduzido pelo google|"
        r"traduc..o do google|"
        r"\bver original\b|\bshow original\b|\bmostrar original\b|\bview original\b|"
        r"\bmachine translated\b",
        re.IGNORECASE,
    ),
    "isolated_page_number": re.compile(r"^\s*(?:page\s+)?\d{1,4}\s*$", re.IGNORECASE),
}

# Lines that are entirely a bare URL (nothing else on the line)
BARE_URL_LINE_RE = re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE)

# Lines that are entirely a DOI reference
BARE_DOI_LINE_RE = re.compile(r"^\s*(?:https?://)?doi\.org/\S+\s*$", re.IGNORECASE)

# --- Inline noise (removed from text, surrounding text kept) ---

# Author citations: (Author et al., 2022), (Author, 2022), (Author & Other, 2022)
INLINE_AUTHOR_CITATION_RE = re.compile(
    r"\s*\([A-Z][a-z\u00e0-\u00fc]+(?:\s+(?:et\s+al\.?|&\s+[A-Z][a-z\u00e0-\u00fc]+))*,?\s*\d{4}[a-z]?\)",
)

# Bracketed number citations: [1], [2,3], [1-3], [1, 2, 3]
INLINE_BRACKET_CITATION_RE = re.compile(
    r"\s*\[\d+(?:\s*[,\-\u2013]\s*\d+)*\]",
)

# Superscript footnote markers
SUPERSCRIPT_MARKERS_RE = re.compile(r"[\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2070]+")

# Standalone footnote symbols after a word
FOOTNOTE_SYMBOL_RE = re.compile(r"(?<=\S)[*\u2020\u2021\u00a7\u00b6\u2016]+")

# Inline DOI strings: doi:10.1234/something
INLINE_DOI_RE = re.compile(r"\s*\bdoi:\s*10\.\d+/\S+", re.IGNORECASE)

FIGURE_CAPTION_RE = re.compile(
    r"^\s*(?:figure|fig\.|figura|table|tabela)\s+\d+[a-z]?\b",
    re.IGNORECASE,
)

HEADING_LIKE_RE = re.compile(
    r"^(?:"
    r"(?:abstract|resumo|summary|introducao|introduction|methods?|metodos?|results?|resultados?|discussion|discussao|conclusion|conclusao|keywords?|palavras-chave)"
    r"|(?:[0-9]+(?:\.[0-9]+)*\s+.+)"
    r"|(?:[ivxlcdm]+\.\s+.+)"
    r")$",
    re.IGNORECASE,
)

LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)]|[a-z][.)])\s+")

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
DOI_TOKEN_RE = re.compile(r"\b(?:https?://doi\.org/|doi[:\s])\S+", re.IGNORECASE)

COMMON_SINGLE_LETTER_WORDS = {"a", "e", "o"}
ACRONYMS_TO_SPELL = {
    "PTSD",
    "ESC",
    "ECG",
    "EEG",
    "SSRI",
    "IL",
    "TNF",
    "NF",
    "MRI",
    "RCT",
    "RCTS",
    "DSM",
    "ICD",
    "DNA",
    "RNA",
}

SCIENTIFIC_TERM_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bIL-?6\b", re.IGNORECASE), "interleucina 6"),
    (re.compile(r"\bTNF-?(?:alpha|alfa|α)\b", re.IGNORECASE), "TNF alfa"),
    (re.compile(r"\bNF-?(?:kB|kb)\b", re.IGNORECASE), "NF capa B"),
    (re.compile(r"\bPTSD\b"), "P T S D"),
    (re.compile(r"\bESC\b"), "E S C"),
    (re.compile(r"\bECG\b"), "E C G"),
    (re.compile(r"\bEEG\b"), "E E G"),
    (re.compile(r"\bSSRI\b"), "S S R I"),
    (re.compile(r"\bMRI\b"), "M R I"),
    (re.compile(r"\bfMRI\b"), "f M R I"),
    (re.compile(r"\bmeta-analysis\b", re.IGNORECASE), "meta analysis"),
    (re.compile(r"\brandomized trial\b", re.IGNORECASE), "randomized trial"),
    (re.compile(r"\bguideline(?:s)?\b", re.IGNORECASE), "guideline"),
]

SYMBOL_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"α|(?<=\w)-alpha\b|(?<=\w)\s+alpha\b", re.IGNORECASE), " alfa"),
    (re.compile(r"β|(?<=\w)-beta\b|(?<=\w)\s+beta\b", re.IGNORECASE), " beta"),
    (re.compile(r"γ|(?<=\w)-gamma\b|(?<=\w)\s+gamma\b", re.IGNORECASE), " gama"),
    (re.compile(r"δ|(?<=\w)-delta\b|(?<=\w)\s+delta\b", re.IGNORECASE), " delta"),
    (re.compile(r"κ|(?<=\w)-kappa\b|(?<=\w)\s+kappa\b", re.IGNORECASE), " capa"),
    (re.compile(r"±"), " mais ou menos "),
    (re.compile(r"%"), " por cento"),
    (re.compile(r"\bmmHg\b", re.IGNORECASE), " milimetros de mercurio"),
    (re.compile(r"\bmg/dL\b", re.IGNORECASE), " miligramas por decilitro"),
    (re.compile(r"\bkg/m2\b", re.IGNORECASE), " quilogramas por metro quadrado"),
    (re.compile(r"\bkg/m\^?2\b", re.IGNORECASE), " quilogramas por metro quadrado"),
    (re.compile(r"&"), " e "),
]


def normalize_unicode(text: str) -> str:
    """Normalize unicode and whitespace while preserving line breaks."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    text = text.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_line(line: str) -> str:
    """Normalize line-level spacing and OCR-like single-letter splits."""
    line = normalize_unicode(line)
    if not line:
        return ""

    tokens = line.split(" ")
    repaired: list[str] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else ""

        if (
            len(token) == 1
            and token.isalpha()
            and token.isascii()
            and token.islower()
            and token.lower() not in COMMON_SINGLE_LETTER_WORDS
            and next_token.isalpha()
            and len(next_token) >= 2
            and next_token[0].islower()
        ):
            repaired.append(token + next_token)
            idx += 2
            continue

        repaired.append(token)
        idx += 1

    line = " ".join(repaired)
    line = re.sub(r"\s+([,.;:!?])", r"\1", line)
    line = re.sub(r"([([{])\s+", r"\1", line)
    line = re.sub(r"\s+([)\]}])", r"\1", line)
    return line.strip()


def line_signature(line: str) -> str:
    """Build a normalized signature for repeated header/footer detection."""
    signature = normalize_line(line).lower()
    signature = URL_RE.sub("<url>", signature)
    signature = DOI_TOKEN_RE.sub("<doi>", signature)
    signature = re.sub(r"\d+", "#", signature)
    signature = re.sub(r"[^a-z0-9<> ]+", " ", signature)
    signature = re.sub(r"\s+", " ", signature).strip()
    return signature


def should_drop_line(line: str, repeated_margin_signatures: set[str] | None = None) -> tuple[bool, str | None]:
    """Return whether a line is editorial noise and the reason."""
    normalized = normalize_line(line)
    if not normalized:
        return True, "empty"

    signature = line_signature(normalized)
    if repeated_margin_signatures and signature in repeated_margin_signatures:
        return True, "repeated_margin"

    # Machine-translated / "ver original" noise (search anywhere in line)
    if LINE_NOISE_PATTERNS["machine_translated"].search(normalized):
        return True, "machine_translated"

    # Isolated page numbers (must match entire line)
    if LINE_NOISE_PATTERNS["isolated_page_number"].match(normalized):
        return True, "isolated_page_number"

    # Bare URL lines (entire line is just a URL)
    if BARE_URL_LINE_RE.match(normalized):
        return True, "bare_url"

    # Bare DOI lines (entire line is just a DOI)
    if BARE_DOI_LINE_RE.match(normalized):
        return True, "bare_doi"

    # Figure/table captions
    if FIGURE_CAPTION_RE.match(normalized):
        return True, "figure_caption"

    return False, None


def remove_inline_noise(text: str) -> str:
    """Remove inline citation markers, superscripts, and DOI strings while keeping surrounding text."""
    text = INLINE_AUTHOR_CITATION_RE.sub("", text)
    text = INLINE_BRACKET_CITATION_RE.sub("", text)
    text = SUPERSCRIPT_MARKERS_RE.sub("", text)
    text = FOOTNOTE_SYMBOL_RE.sub("", text)
    text = INLINE_DOI_RE.sub("", text)
    text = re.sub(r"  +", " ", text)
    return text


def looks_like_heading(block: str, first_block: bool = False) -> bool:
    """Heuristic heading detector used for paragraph preservation and pauses."""
    normalized = normalize_line(block)
    if not normalized:
        return False

    words = normalized.split()
    if first_block and len(words) <= 25:
        return True

    if HEADING_LIKE_RE.match(normalized):
        return True

    if len(words) > 18 or len(normalized) > 160:
        return False

    if normalized.endswith((".", "!", "?")):
        return False

    uppercase_ratio = sum(1 for ch in normalized if ch.isupper()) / max(
        sum(1 for ch in normalized if ch.isalpha()),
        1,
    )
    title_case_ratio = sum(1 for word in words if word[:1].isupper()) / max(len(words), 1)
    return uppercase_ratio >= 0.45 or title_case_ratio >= 0.55


def join_wrapped_lines(lines: list[str]) -> str:
    """Rebuild paragraphs from hard-wrapped PDF lines."""
    clean_lines = [normalize_line(line) for line in lines]
    clean_lines = [line for line in clean_lines if line]
    if not clean_lines:
        return ""

    line_lengths = [len(line) for line in clean_lines]
    median_len = sorted(line_lengths)[len(line_lengths) // 2] if line_lengths else 80

    blocks: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        paragraph = paragraph_lines[0]
        for part in paragraph_lines[1:]:
            if paragraph.endswith("-"):
                paragraph = paragraph[:-1] + part
            else:
                paragraph = f"{paragraph} {part}"
        paragraph = re.sub(r"\s+([,.;:!?])", r"\1", paragraph).strip()
        blocks.append(paragraph)
        paragraph_lines.clear()

    for idx, line in enumerate(clean_lines):
        first_block = len(blocks) == 0 and not paragraph_lines
        next_line = clean_lines[idx + 1] if idx + 1 < len(clean_lines) else ""

        if looks_like_heading(line, first_block=first_block):
            flush_paragraph()
            blocks.append(line)
            continue

        if LIST_ITEM_RE.match(line):
            flush_paragraph()
            blocks.append(line)
            continue

        if paragraph_lines:
            previous = paragraph_lines[-1]
            previous_short = len(previous) < median_len * 0.82
            if previous.endswith((".", "!", "?")) and previous_short and next_line[:1].isupper():
                flush_paragraph()

        paragraph_lines.append(line)

    flush_paragraph()
    return "\n\n".join(blocks).strip()


def trim_references_section(text: str) -> tuple[str, bool]:
    """Optionally remove the references section from the TTS version."""
    match = REFERENCE_HEADER_RE.search(text)
    if match:
        return text[: match.start()].rstrip(), True

    citations = list(NUMBERED_REFERENCE_LINE_RE.finditer(text))
    for idx in range(len(citations) - 2):
        if citations[idx + 2].start() - citations[idx].start() < 2500:
            return text[: citations[idx].start()].rstrip(), True

    return text, False


def clean_document_text(text: str, include_references: bool = True) -> dict[str, Any]:
    """
    Clean article text for display/translation while preserving document structure.
    """
    removed_patterns: Counter[str] = Counter()
    warnings: list[str] = []

    text = normalize_unicode(text)
    raw_chars = len(text)

    lines = text.splitlines()
    kept_lines: list[str] = []
    for line in lines:
        drop, reason = should_drop_line(line)
        if drop:
            if reason and reason != "empty":
                removed_patterns[reason] += 1
            continue
        kept_lines.append(line)

    cleaned = join_wrapped_lines(kept_lines)
    cleaned = remove_inline_noise(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    references_removed = False
    if not include_references:
        cleaned, references_removed = trim_references_section(cleaned)
        if references_removed:
            removed_patterns["references"] += 1

    if not cleaned:
        warnings.append("O texto ficou vazio depois da limpeza.")

    return {
        "text": cleaned,
        "removed_patterns": dict(sorted(removed_patterns.items())),
        "removed_characters": max(raw_chars - len(cleaned), 0),
        "references_removed": references_removed,
        "warnings": warnings,
        "raw_characters": raw_chars,
    }


def _spell_acronym(token: str) -> str:
    token = token.strip()
    if not token:
        return token
    if token.upper() in ACRONYMS_TO_SPELL or ENGLISH_ACRONYMS_RE.fullmatch(token):
        return " ".join(token)
    return token


def _normalize_english_terms(text: str) -> str:
    def replace_term(match: re.Match[str]) -> str:
        return match.group(0).replace("-", " ")

    text = ENGLISH_TERMS_RE.sub(replace_term, text)
    return re.sub(r"\b[A-Z]{2,6}\b", lambda match: _spell_acronym(match.group(0)), text)


def normalize_for_speech(text: str, voice_id: str = "pt-BR-FranciscaNeural") -> dict[str, Any]:
    """
    Normalize the text specifically for speech synthesis.
    """
    removed_patterns: Counter[str] = Counter()
    text = normalize_unicode(text)

    # Strip URLs, DOI strings and residual editorial clutter before speech.
    if URL_RE.search(text):
        removed_patterns["editorial_url"] += len(URL_RE.findall(text))
        text = URL_RE.sub("", text)

    if DOI_TOKEN_RE.search(text):
        removed_patterns["doi"] += len(DOI_TOKEN_RE.findall(text))
        text = DOI_TOKEN_RE.sub("", text)

    blocks = []
    for raw_block in text.split("\n\n"):
        block = normalize_line(raw_block)
        if not block:
            continue
        if FIGURE_CAPTION_RE.match(block):
            removed_patterns["figure_caption"] += 1
            continue
        if looks_like_heading(block):
            if not block.endswith((".", "!", "?")):
                block = f"{block}."
            blocks.append(block)
            continue
        if LIST_ITEM_RE.match(block):
            block = LIST_ITEM_RE.sub("Item ", block, count=1)
            if not block.endswith((".", "!", "?")):
                block = f"{block}."
        blocks.append(block)

    text = "\n\n".join(blocks)

    for pattern, replacement in SCIENTIFIC_TERM_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    for pattern, replacement in SYMBOL_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    text = _normalize_english_terms(text)

    # Encourage clearer pauses without injecting visible garbage into the UI text.
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r"\s*:\s*", ": ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*([.!?])\s*", r"\1 ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\n +", "\n", text).strip()

    warnings: list[str] = []
    if voice_id == "pt-BR-FranciscaNeural" and ENGLISH_TERMS_RE.search(text):
        warnings.append(
            "A voz Francisca recebeu normalizacao para termos em ingles, mas ainda pode haver limite de pronuncia sem SSML."
        )

    return {
        "text": text,
        "removed_patterns": dict(sorted(removed_patterns.items())),
        "warnings": warnings,
    }


def prepare_tts_text(
    text: str,
    voice_id: str = "pt-BR-FranciscaNeural",
    include_references: bool = False,
) -> dict[str, Any]:
    """Return both the cleaned display text and the speech-only text."""
    cleaned = clean_document_text(text, include_references=include_references)
    speech = normalize_for_speech(cleaned["text"], voice_id=voice_id)

    removed_patterns = Counter(cleaned["removed_patterns"])
    removed_patterns.update(speech["removed_patterns"])

    warnings = list(cleaned["warnings"])
    warnings.extend(speech["warnings"])

    return {
        "display_text": cleaned["text"],
        "speech_text": speech["text"],
        "removed_patterns": dict(sorted(removed_patterns.items())),
        "removed_characters": cleaned["removed_characters"],
        "references_removed": cleaned["references_removed"],
        "warnings": warnings,
        "raw_characters": cleaned["raw_characters"],
    }


def preprocess_for_tts(
    text: str,
    voice_id: str = "pt-BR-FranciscaNeural",
    include_references: bool = False,
) -> str:
    """
    Backwards-compatible wrapper used by older code paths.
    """
    return prepare_tts_text(
        text,
        voice_id=voice_id,
        include_references=include_references,
    )["speech_text"]
