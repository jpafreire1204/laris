from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def create_pdf(
    path: Path,
    pages: Iterable[dict],
    header: str | None = None,
    footer: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    for page in pages:
        y = height - 50

        if header:
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, height - 25, header)

        title = page.get("title")
        if title:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(50, y, title)
            y -= 28

        for heading in page.get("headings", []):
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, heading)
            y -= 20

        pdf.setFont("Helvetica", 11)
        for paragraph in page.get("paragraphs", []):
            for line in _wrap_text(paragraph, width=92):
                pdf.drawString(50, y, line)
                y -= 15
            y -= 12

        for bullet in page.get("bullets", []):
            for line in _wrap_text(f"- {bullet}", width=88):
                pdf.drawString(65, y, line)
                y -= 15
            y -= 6

        if footer:
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, 20, footer)

        page_number = page.get("page_number")
        if page_number is not None:
            pdf.setFont("Helvetica", 9)
            pdf.drawRightString(width - 40, 20, str(page_number))

        pdf.showPage()

    pdf.save()
    return path


def _wrap_text(text: str, width: int = 90) -> list[str]:
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
