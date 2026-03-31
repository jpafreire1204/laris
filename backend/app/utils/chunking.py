"""
Semantic chunking helpers for long-form TTS generation.
"""

from __future__ import annotations

import re
from typing import Any, List, Tuple

from app.utils.text_preprocessing import LIST_ITEM_RE, looks_like_heading, normalize_line


SOFT_MAX_CHARS = 2200
HARD_MAX_CHARS = 3200

ABBREVIATION_PLACEHOLDERS = {
    "Dr.": "Dr<dot>",
    "Dra.": "Dra<dot>",
    "Sr.": "Sr<dot>",
    "Sra.": "Sra<dot>",
    "Prof.": "Prof<dot>",
    "Fig.": "Fig<dot>",
    "Eq.": "Eq<dot>",
    "et al.": "et al<dot>",
    "etc.": "etc<dot>",
}


def _protect_abbreviations(text: str) -> str:
    for source, replacement in ABBREVIATION_PLACEHOLDERS.items():
        text = text.replace(source, replacement)
    return text


def _restore_abbreviations(text: str) -> str:
    for source, replacement in ABBREVIATION_PLACEHOLDERS.items():
        text = text.replace(replacement, source)
    return text


def _split_into_sentences(text: str) -> List[str]:
    protected = _protect_abbreviations(text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])", protected)
    sentences = [_restore_abbreviations(part).strip() for part in parts if part.strip()]
    return sentences or ([text.strip()] if text.strip() else [])


def _is_list_item(block: str) -> bool:
    return bool(LIST_ITEM_RE.match(block))


def _chunk_is_heading_only(chunk: str) -> bool:
    blocks = [block for block in chunk.split("\n\n") if block.strip()]
    return bool(blocks) and all(looks_like_heading(block, first_block=(index == 0)) for index, block in enumerate(blocks))


def _split_block(block: str, hard_max_chars: int) -> Tuple[List[str], int]:
    """
    Split an oversized block on sentence boundaries. If a single sentence
    exceeds the hard limit, it is split at clause/space boundaries.
    """
    forced_splits = 0
    sentences = _split_into_sentences(block)
    if not sentences:
        return [], forced_splits

    parts: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            parts.append(current.strip())
            current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= hard_max_chars:
            current = candidate
            continue

        if current:
            flush()

        if len(sentence) <= hard_max_chars:
            current = sentence
            continue

        # Last-resort clause split for pathological sentences.
        chunks = re.split(r"(?<=[,;:])\s+", sentence)
        buffer = ""
        for piece in chunks:
            candidate_piece = f"{buffer} {piece}".strip() if buffer else piece
            if len(candidate_piece) <= hard_max_chars:
                buffer = candidate_piece
                continue

            if buffer:
                parts.append(buffer.strip())
                forced_splits += 1
                buffer = ""

            if len(piece) <= hard_max_chars:
                buffer = piece
                continue

            words = piece.split()
            running = ""
            for word in words:
                candidate_word = f"{running} {word}".strip() if running else word
                if len(candidate_word) <= hard_max_chars:
                    running = candidate_word
                    continue

                if running:
                    parts.append(running.strip())
                    forced_splits += 1
                running = word

            if running:
                buffer = running

        if buffer:
            current = buffer

    flush()
    return parts, forced_splits


def semantic_chunk_text(
    text: str,
    max_chars: int = SOFT_MAX_CHARS,
    hard_max_chars: int = HARD_MAX_CHARS,
) -> tuple[List[str], dict[str, Any]]:
    """Chunk text on headings, paragraphs, lists and sentences."""
    blocks = [normalize_line(block) for block in text.split("\n\n")]
    blocks = [block for block in blocks if block]

    chunks: list[str] = []
    current = ""
    forced_splits = 0

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
            current = ""

    for idx, block in enumerate(blocks):
        is_heading = looks_like_heading(block, first_block=(idx == 0))
        is_list_item = _is_list_item(block)

        if len(block) > hard_max_chars:
            if current and _chunk_is_heading_only(current):
                available = max(120, hard_max_chars - len(current) - 2)
                split_parts, split_count = _split_block(block, hard_max_chars=available)
                forced_splits += split_count
                if split_parts:
                    first_part = split_parts[0]
                    combined = f"{current}\n\n{first_part}".strip()
                    chunks.append(combined)
                    for part in split_parts[1:-1]:
                        chunks.append(part)
                    current = split_parts[-1] if len(split_parts) > 1 else ""
                    continue

            flush()
            split_parts, split_count = _split_block(block, hard_max_chars=hard_max_chars)
            forced_splits += split_count
            chunks.extend(split_parts)
            continue

        separator = "\n\n" if current else ""
        candidate = f"{current}{separator}{block}" if current else block

        if len(candidate) <= max_chars:
            current = candidate
            continue

        # Keep headings with the next paragraph instead of leaving them alone.
        if is_heading:
            flush()
            current = block
            continue

        # Prefer keeping list items as standalone blocks.
        if is_list_item and current:
            flush()
            current = block
            continue

        if current and _chunk_is_heading_only(current):
            available = max(120, hard_max_chars - len(current) - 2)
            split_parts, split_count = _split_block(block, hard_max_chars=available)
            forced_splits += split_count
            if split_parts:
                first_part = split_parts[0]
                combined = f"{current}\n\n{first_part}".strip()
                if len(combined) <= hard_max_chars:
                    chunks.append(combined)
                    remaining_parts = split_parts[1:]
                    for part in remaining_parts[:-1]:
                        chunks.append(part)
                    current = remaining_parts[-1] if remaining_parts else ""
                    continue

        flush()

        if len(block) <= max_chars:
            current = block
            continue

        split_parts, split_count = _split_block(block, hard_max_chars=hard_max_chars)
        forced_splits += split_count
        for part in split_parts:
            if len(part) <= max_chars:
                if current:
                    flush()
                current = part
            else:
                flush()
                chunks.append(part)

    flush()

    diagnostics = {
        "chunks": len(chunks),
        "max_chars": max_chars,
        "hard_max_chars": hard_max_chars,
        "chunk_char_counts": [len(chunk) for chunk in chunks],
        "forced_splits": forced_splits,
    }
    return chunks, diagnostics


def split_text_into_chunks(text: str, max_chars: int = SOFT_MAX_CHARS) -> List[str]:
    """Backwards-compatible wrapper used by the rest of the app/tests."""
    hard_limit = max(max_chars + 100, max_chars)
    chunks, _ = semantic_chunk_text(text, max_chars=max_chars, hard_max_chars=hard_limit)
    return chunks


def estimate_audio_duration(text: str, speed: float = 1.0) -> float:
    """Estimate audio duration in seconds using a conservative PT-BR speech rate."""
    if not text or not text.strip():
        return 0
    words = len(text.split())
    base_wpm = 145
    adjusted_wpm = max(base_wpm * max(speed, 0.1), 1)
    duration_minutes = words / adjusted_wpm
    return duration_minutes * 60


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split()) if text.strip() else 0


def count_paragraphs(text: str) -> int:
    """Count paragraphs separated by blank lines."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return len(paragraphs)
