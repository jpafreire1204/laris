from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from app.services.extraction import extract_document_from_file
from app.services.fast_pipeline import run_fast_pipeline
from app.utils.chunking import semantic_chunk_text
from app.utils.mp3_utils import estimate_mp3_duration, merge_mp3_files
from app.utils.text_preprocessing import prepare_tts_text
from tests.pdf_factory import create_pdf


def build_fake_mp3(frame_count: int = 12) -> bytes:
    # MPEG1 Layer III, 128 kbps, 44.1 kHz, stereo.
    header = bytes([0xFF, 0xFB, 0x90, 0x64])
    frame_size = 417
    frame = header + bytes(frame_size - 4)
    id3v2 = b"ID3\x04\x00\x00\x00\x00\x00\x00"
    id3v1 = b"TAG" + bytes(125)
    return id3v2 + (frame * frame_count) + id3v1


@pytest.fixture
def workspace_tmp_dir() -> Path:
    path = Path("backend_test_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_short_pdf_keeps_title_and_last_sentence(workspace_tmp_dir: Path):
    pdf_path = create_pdf(
        workspace_tmp_dir / "short.pdf",
        pages=[
            {
                "title": "Short Clinical Report",
                "headings": ["Abstract"],
                "paragraphs": [
                    "This is a short article used to validate the extraction flow.",
                    "The final sentence of the last page must be preserved exactly in the output.",
                ],
                "page_number": 1,
            }
        ],
    )

    result = extract_document_from_file(pdf_path.read_bytes(), pdf_path.name)

    assert result.error == ""
    assert "Short Clinical Report" in result.text
    assert "The final sentence of the last page must be preserved exactly in the output." in result.text


def test_google_translated_pdf_removes_machine_translated_noise(workspace_tmp_dir: Path):
    pdf_path = create_pdf(
        workspace_tmp_dir / "google_translated.pdf",
        pages=[
            {
                "title": "Exercise and the Gut Microbiome",
                "headings": ["Abstract"],
                "paragraphs": [
                    "Physical activity improves gut diversity and supports gastrointestinal health.",
                ],
                "page_number": 1,
            },
            {
                "headings": ["Results"],
                "paragraphs": [
                    "The final sentence on the last page must remain available after cleanup.",
                ],
                "page_number": 2,
            },
        ],
        header="Machine Translated by Google",
        footer="Downloaded from https://journal.example.org/article.pdf",
    )

    result = extract_document_from_file(pdf_path.read_bytes(), pdf_path.name)

    assert "Machine Translated by Google" not in result.text
    assert "Downloaded from" not in result.text
    assert result.diagnostics["removed_patterns"]["machine_translated"] >= 1
    assert result.diagnostics["removed_patterns"]["download_notice"] >= 1
    assert "The final sentence on the last page must remain available after cleanup." in result.text


def test_repeated_headers_and_footers_are_removed_without_losing_body(workspace_tmp_dir: Path):
    pages = []
    for page_number in range(1, 5):
        pages.append(
            {
                "title": "Inflammation Biomarkers" if page_number == 1 else None,
                "headings": [f"Section {page_number}"],
                "paragraphs": [
                    f"Page {page_number} discusses IL-6, TNF-alpha and ECG findings in patients.",
                    f"Body paragraph {page_number} should stay even when repeated editorial headers are dropped.",
                ],
                "page_number": page_number,
            }
        )

    pdf_path = create_pdf(
        workspace_tmp_dir / "headers.pdf",
        pages=pages,
        header="Journal of Local Cardiology | Vol 2 | 2026",
        footer="journal.example.org | DOI 10.1000/test-header",
    )

    result = extract_document_from_file(pdf_path.read_bytes(), pdf_path.name)

    assert "Journal of Local Cardiology" not in result.text
    assert "10.1000/test-header" not in result.text
    assert "Body paragraph 4 should stay even when repeated editorial headers are dropped." in result.text
    assert len(result.diagnostics["discarded_pages"]) == 0


def test_many_page_pdf_reaches_the_last_page(workspace_tmp_dir: Path):
    pages = []
    for page_number in range(1, 13):
        pages.append(
            {
                "title": "Long Guideline" if page_number == 1 else None,
                "headings": [f"Chapter {page_number}"],
                "paragraphs": [
                    f"This paragraph belongs to page {page_number} and keeps the reading order stable.",
                    (
                        "This is the true final sentence on the last page."
                        if page_number == 12
                        else f"Supporting sentence {page_number}."
                    ),
                ],
                "page_number": page_number,
            }
        )

    pdf_path = create_pdf(workspace_tmp_dir / "many_pages.pdf", pages=pages, header="Long Guideline Header")
    result = extract_document_from_file(pdf_path.read_bytes(), pdf_path.name)

    assert result.diagnostics["page_count"] == 12
    assert result.diagnostics["pages_extracted"] == 12
    assert "This is the true final sentence on the last page." in result.text


def test_prepare_tts_text_skips_references_by_default_and_normalizes_terms():
    text = (
        "Clinical Inflammation Review\n\n"
        "Results\n\n"
        "IL-6, TNF-alpha, NF-kB, PTSD, ESC, ECG and SSRI were reported.\n\n"
        "References\n\n"
        "[1] Example reference.\n"
    )

    prepared = prepare_tts_text(text, voice_id="pt-BR-FranciscaNeural", include_references=False)

    assert "Clinical Inflammation Review" in prepared["display_text"]
    assert "References" not in prepared["speech_text"]
    assert "interleucina 6" in prepared["speech_text"]
    assert "T N F alfa" in prepared["speech_text"]
    assert "N F capa B" in prepared["speech_text"]
    assert "P T S D" in prepared["speech_text"]
    assert "E C G" in prepared["speech_text"]


def test_semantic_chunking_keeps_sentence_boundaries():
    text = (
        "Title\n\n"
        "Methods\n\n"
        + "This is a sentence. " * 120
        + "\n\nResults\n\n"
        + "Another paragraph closes the article cleanly."
    )

    chunks, diagnostics = semantic_chunk_text(text, max_chars=500, hard_max_chars=700)

    assert len(chunks) > 1
    assert diagnostics["forced_splits"] == 0
    for chunk in chunks[:-1]:
        assert chunk.strip().endswith((".", "!", "?"))


def test_merge_mp3_files_creates_valid_duration(workspace_tmp_dir: Path):
    chunk_a = workspace_tmp_dir / "a.mp3"
    chunk_b = workspace_tmp_dir / "b.mp3"
    output = workspace_tmp_dir / "merged.mp3"

    chunk_a.write_bytes(build_fake_mp3(frame_count=10))
    chunk_b.write_bytes(build_fake_mp3(frame_count=8))

    merged, error = merge_mp3_files([chunk_a, chunk_b], output)

    assert merged is True, error
    assert output.exists()
    assert estimate_mp3_duration(output) > 0.4


@pytest.mark.asyncio
async def test_run_fast_pipeline_end_to_end_with_fake_tts(monkeypatch, workspace_tmp_dir: Path):
    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str):
            self.text = text
            self.voice = voice
            self.rate = rate

        async def save(self, path: str) -> None:
            Path(path).write_bytes(build_fake_mp3(frame_count=6))

    class FakeEdgeTTSModule:
        Communicate = FakeCommunicate

    monkeypatch.setitem(__import__("sys").modules, "edge_tts", FakeEdgeTTSModule())

    output_path = workspace_tmp_dir / "pipeline.mp3"
    success, error, metrics, prepared_text = await run_fast_pipeline(
        text=(
            "Scientific Title\n\n"
            "Abstract\n\n"
            + "Sentence one. Sentence two. " * 220
            + "\n\nConclusion\n\n"
            "The final sentence of the article is here."
        ),
        voice_id="pt-BR-FranciscaNeural",
        speed=1.0,
        output_path=output_path,
        job_id="pytest",
        include_references=False,
    )

    assert success is True, error
    assert prepared_text is not None
    assert output_path.exists()
    assert metrics.chunks_count >= 2
    assert metrics.completed_chunks == metrics.chunks_count
    assert metrics.report["truncated"] is False
    assert metrics.report["audio"]["duration_seconds"] > 0
