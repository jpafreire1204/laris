from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


OUTPUT = Path(__file__).resolve().parents[2] / "outputs" / "sample_scientific_case.pdf"


PAGES = [
    {
        "title": "Inflammation, Cardiology and the Gut Axis",
        "headings": ["Abstract"],
        "paragraphs": [
            "This sample article exists to validate long PDF extraction, cleanup and TTS chunking in Laris.",
            "It includes repeated editorial noise that must not be spoken by the Francisca voice.",
        ],
    },
    {
        "headings": ["Introduction"],
        "paragraphs": [
            "IL-6, TNF-alpha, NF-kB, PTSD, ESC and ECG are deliberately present to validate scientific term normalization.",
            "The article body must preserve paragraph order and natural pauses across the full document.",
        ],
    },
    {
        "headings": ["Methods"],
        "paragraphs": [
            "This page simulates a translated scientific PDF with noisy headers and footers.",
            "Downloaded notices, page numbers and repeated URLs should be removed without deleting the body text.",
        ],
    },
    {
        "headings": ["Results"],
        "paragraphs": [
            "The semantic chunker must avoid splitting sentences in the middle and keep headings attached to the next paragraph.",
            "The final MP3 should merge all chunks in order and remain valid on localhost.",
        ],
    },
    {
        "headings": ["Conclusion"],
        "paragraphs": [
            "The title should be read first.",
            "This is the final sentence on the last page and it must be present in the generated audio.",
        ],
    },
]


def wrap_text(text: str, width: int = 92) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def build_pdf(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    for page_number, page in enumerate(PAGES, start=1):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(48, height - 24, "Machine Translated by Google")

        y = height - 56
        if page.get("title"):
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(48, y, page["title"])
            y -= 28

        for heading in page.get("headings", []):
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(48, y, heading)
            y -= 20

        pdf.setFont("Helvetica", 11)
        for paragraph in page.get("paragraphs", []):
            for line in wrap_text(paragraph):
                pdf.drawString(48, y, line)
                y -= 15
            y -= 12

        pdf.setFont("Helvetica", 9)
        pdf.drawString(48, 20, "Downloaded from https://journal.example.org/sample-case")
        pdf.drawRightString(width - 40, 20, str(page_number))
        pdf.showPage()

    pdf.save()
    return output_path


if __name__ == "__main__":
    created = build_pdf(OUTPUT)
    print(created)
