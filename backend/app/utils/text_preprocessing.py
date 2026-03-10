"""
Laris - Text Preprocessing for TTS
Strips references, noise strings, and enforces punctuation pauses for TTS.
"""

import re


# === 1. TRUNCATE AT REFERENCES ===

# Standalone section headers (case-insensitive, must be on their own line)
_REFERENCES_HEADERS = [
    r"refer[eê]ncias",
    r"references",
    r"bibliography",
    r"bibliografia",
    r"works\s+cited",
    r"literatura\s+citada",
]
# Standalone line OR followed by citation-like content on the same line
_REFERENCES_HEADER_RE = re.compile(
    r"^\s*(?:" + "|".join(_REFERENCES_HEADERS) + r")\s*(?:$|\s*\[)",
    re.IGNORECASE | re.MULTILINE,
)

# Numbered citation lines: [1], (1), 1. followed by author-like text
_NUMBERED_CITATION_RE = re.compile(
    r"^(?:\[\d+\]|\(\d+\)|\d+\.)\s+[A-ZÀ-Ý][a-zà-ÿ]+",
    re.MULTILINE,
)


def truncate_at_references(text: str) -> str:
    """Remove everything from the references/bibliography section onward."""
    # Try explicit header first
    match = _REFERENCES_HEADER_RE.search(text)
    if match:
        return text[: match.start()].rstrip()

    # Heuristic: block of 3+ consecutive numbered citation lines
    citations = list(_NUMBERED_CITATION_RE.finditer(text))
    if len(citations) >= 3:
        # Check if at least 3 are within ~2000 chars of each other (a citation block)
        for i in range(len(citations) - 2):
            span = citations[i + 2].start() - citations[i].start()
            if span < 3000:
                return text[: citations[i].start()].rstrip()

    return text


# === 2. STRIP NOISE ===

_NOISE_LITERALS = [
    "Tradução do Google",
    "Ver original",
    "Mostrar original",
    "Show original",
]

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_DOI_RE = re.compile(r"(?:doi(?:\.org)?[:/]\s*)\S+", re.IGNORECASE)

_FIGURE_TABLE_RE = re.compile(
    r"^\s*(?:Figure|Figura|Fig\.|Table|Tabela|FIGURE|TABLE)\s*.+$",
    re.MULTILINE,
)

# Footnote markers: *, †, ‡ and superscript digit clusters (¹²³⁴⁵⁶⁷⁸⁹⁰)
_FOOTNOTE_MARKERS_RE = re.compile(r"[*†‡¹²³⁴⁵⁶⁷⁸⁹⁰]+")


def strip_noise(text: str) -> str:
    """Remove noise strings, URLs, DOIs, figure captions, footnote markers."""
    # Literal noise phrases — consume trailing period/whitespace but keep leading sentence end
    # e.g. "avaliados. Ver original." → "avaliados. "
    # e.g. "Tradução do Google. Os dados" → " Os dados"
    for phrase in _NOISE_LITERALS:
        text = re.sub(
            r"\s*" + re.escape(phrase) + r"\.?\s*",
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # URLs and DOIs
    text = _URL_RE.sub("", text)
    text = _DOI_RE.sub("", text)

    # Figure/table caption lines
    text = _FIGURE_TABLE_RE.sub("", text)

    # Footnote markers (only standalone clusters, not digits inside words)
    text = _FOOTNOTE_MARKERS_RE.sub("", text)

    # Clean up orphaned/doubled punctuation from removals
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\.\s*\.", ".", text)

    # Clean up leftover whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# === 3. PUNCTUATION PAUSE ENFORCEMENT ===
#
# Edge-tts neural voices respect punctuation naturally. We ensure proper
# formatting so the engine produces audible pauses:
# - Proper spacing after commas, periods, semicolons, etc.
# - Paragraph breaks get an ellipsis to trigger a longer ~900ms pause.
# - Em/en dashes surrounded by spaces for a natural pause.


def enforce_punctuation_pauses(text: str) -> str:
    """
    Ensure punctuation is properly formatted so TTS produces audible pauses.
    Must be called on plain text BEFORE sending to edge-tts.
    """
    # Ensure space after punctuation (comma, period, semicolon, colon, !, ?)
    # but not inside numbers like 0.05 or abbreviations like et al.
    text = re.sub(r"([,;:!?])([^\s\d])", r"\1 \2", text)

    # Ensure em/en dashes have spaces around them for a clear pause
    text = re.sub(r"(\w)([—–])(\w)", r"\1 \2 \3", text)

    # Paragraph breaks → add "..." for a longer pause from the neural voice
    text = re.sub(r"\n\n+", "\n\n...\n\n", text)

    # Clean up any double spaces
    text = re.sub(r" {2,}", " ", text)

    return text


# === MAIN ENTRY POINT ===

def preprocess_for_tts(text: str) -> str:
    """
    Full preprocessing pipeline: truncate references, strip noise,
    enforce punctuation pauses for natural TTS narration.
    """
    text = truncate_at_references(text)
    text = strip_noise(text)
    text = enforce_punctuation_pauses(text)
    return text
