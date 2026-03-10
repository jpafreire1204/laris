"""
Laris - PDF Translator Service
Traduz PDFs mantendo o layout original usando PyMuPDF.
Abordagem: cobre texto original com retângulo branco + insere tradução.
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Representa um bloco de texto extraído."""
    text: str
    bbox: tuple  # (x0, y0, x1, y1)
    font_size: float
    font_name: str
    is_bold: bool
    is_italic: bool
    color: tuple  # (r, g, b) normalizado 0-1


def get_base_font(original_font: str, is_bold: bool, is_italic: bool) -> str:
    """Mapeia fonte original para fonte PDF base."""
    font_lower = original_font.lower()

    # Detecta família de fonte
    if any(x in font_lower for x in ["arial", "helvetica", "calibri", "verdana", "sans"]):
        base = "helv"
    elif any(x in font_lower for x in ["times", "georgia", "cambria", "serif", "roman"]):
        base = "tiro"
    elif any(x in font_lower for x in ["courier", "consolas", "mono", "code"]):
        base = "cour"
    else:
        base = "helv"  # default sans-serif

    # Adiciona estilo
    styles = {
        "helv": {"bi": "hebi", "b": "hebo", "i": "heit", "": "helv"},
        "tiro": {"bi": "tibi", "b": "tibo", "i": "tiit", "": "tiro"},
        "cour": {"bi": "cobi", "b": "cobo", "i": "coit", "": "cour"},
    }

    style_key = ""
    if is_bold:
        style_key += "b"
    if is_italic:
        style_key += "i"

    return styles.get(base, styles["helv"]).get(style_key, base)


def extract_text_blocks(page) -> List[TextBlock]:
    """Extrai blocos de texto de uma página, agrupando por linhas."""
    import fitz

    blocks = []
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # Só texto
            continue

        for line in block.get("lines", []):
            # Agrupa spans de uma linha
            line_text = ""
            line_bbox = None
            main_font_size = 0
            main_font_name = "Helvetica"
            is_bold = False
            is_italic = False
            color = (0, 0, 0)

            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if not span_text:
                    continue

                line_text += span_text

                # Usa bbox combinado da linha
                span_bbox = span.get("bbox")
                if line_bbox is None:
                    line_bbox = list(span_bbox)
                else:
                    line_bbox[0] = min(line_bbox[0], span_bbox[0])  # x0
                    line_bbox[1] = min(line_bbox[1], span_bbox[1])  # y0
                    line_bbox[2] = max(line_bbox[2], span_bbox[2])  # x1
                    line_bbox[3] = max(line_bbox[3], span_bbox[3])  # y1

                # Usa o maior tamanho de fonte da linha
                span_size = span.get("size", 11)
                if span_size > main_font_size:
                    main_font_size = span_size
                    main_font_name = span.get("font", "Helvetica")

                    # Extrai flags
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 16)
                    is_italic = bool(flags & 2)

                    # Cor
                    c = span.get("color", 0)
                    if isinstance(c, int):
                        color = (
                            ((c >> 16) & 255) / 255,
                            ((c >> 8) & 255) / 255,
                            (c & 255) / 255
                        )

            if line_text.strip() and line_bbox:
                blocks.append(TextBlock(
                    text=line_text.strip(),
                    bbox=tuple(line_bbox),
                    font_size=main_font_size or 11,
                    font_name=main_font_name,
                    is_bold=is_bold,
                    is_italic=is_italic,
                    color=color
                ))

    return blocks


def should_translate(text: str) -> bool:
    """Verifica se o texto deve ser traduzido."""
    text = text.strip()

    # Muito curto
    if len(text) < 3:
        return False

    # Só números, pontuação ou símbolos
    if re.match(r'^[\d\s\.\,\-\(\)\[\]\{\}\/\\\:\;\!\?\@\#\$\%\^\&\*\+\=\<\>\~\`\'\"]+$', text):
        return False

    # URLs ou emails
    if re.match(r'^(https?://|www\.|[\w\.-]+@)', text, re.I):
        return False

    # Referências bibliográficas curtas (ex: "[1]", "(2023)")
    if re.match(r'^\[?\d+\]?$', text) or re.match(r'^\(\d{4}\)$', text):
        return False

    return True


def translate_pdf_preserve_layout(
    input_path: Path,
    output_path: Path,
    source_lang: str = 'en',
    target_lang: str = 'pt'
) -> Tuple[bool, Optional[str]]:
    """
    Traduz um PDF mantendo o layout original.

    Abordagem:
    1. Extrai texto linha por linha
    2. Traduz linhas inteiras (melhor contexto)
    3. Cobre texto original com retângulo branco
    4. Insere texto traduzido na mesma posição
    """
    try:
        import fitz
        from deep_translator import GoogleTranslator

        logger.info(f"[PDF] Traduzindo {input_path} -> {output_path}")

        # Abre o PDF
        doc = fitz.open(str(input_path))
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        total_pages = len(doc)
        translated_count = 0

        for page_num in range(total_pages):
            page = doc[page_num]
            logger.info(f"[PDF] Página {page_num + 1}/{total_pages}")

            # Extrai blocos de texto
            blocks = extract_text_blocks(page)

            # Processa cada bloco
            for block in blocks:
                if not should_translate(block.text):
                    continue

                try:
                    # Traduz o texto
                    translated = translator.translate(block.text)

                    if not translated or translated == block.text:
                        continue

                    # Coordenadas do bloco
                    x0, y0, x1, y1 = block.bbox
                    rect = fitz.Rect(x0, y0, x1, y1)

                    # Expande um pouco o retângulo para garantir cobertura
                    rect_expanded = fitz.Rect(
                        x0 - 1, y0 - 1,
                        x1 + 1, y1 + 1
                    )

                    # Desenha retângulo branco sobre o texto original
                    shape = page.new_shape()
                    shape.draw_rect(rect_expanded)
                    shape.finish(color=None, fill=(1, 1, 1))  # Branco
                    shape.commit()

                    # Calcula tamanho da fonte ajustado
                    font_size = block.font_size

                    # Se texto traduzido for muito maior, reduz fonte
                    len_ratio = len(translated) / max(len(block.text), 1)
                    if len_ratio > 1.4:
                        font_size *= 0.75
                    elif len_ratio > 1.2:
                        font_size *= 0.85

                    # Limita tamanho mínimo
                    font_size = max(font_size, 6)

                    # Obtém fonte apropriada
                    pdf_font = get_base_font(block.font_name, block.is_bold, block.is_italic)

                    # Insere texto traduzido
                    # Usa insert_textbox para quebra automática de linha
                    text_rect = fitz.Rect(x0, y0, x1 + 50, y1 + 20)  # Expande para caber

                    rc = page.insert_textbox(
                        text_rect,
                        translated,
                        fontsize=font_size,
                        fontname=pdf_font,
                        color=block.color,
                        align=0  # Esquerda
                    )

                    # Se não coube, tenta com fonte menor
                    if rc < 0:
                        page.insert_textbox(
                            text_rect,
                            translated,
                            fontsize=font_size * 0.8,
                            fontname=pdf_font,
                            color=block.color,
                            align=0
                        )

                    translated_count += 1

                except Exception as e:
                    logger.debug(f"Erro traduzindo bloco: {e}")
                    continue

        # Salva PDF
        doc.save(str(output_path), garbage=4, deflate=True)
        doc.close()

        logger.info(f"[PDF] Traduzido: {translated_count} blocos em {total_pages} páginas")
        return True, None

    except ImportError:
        return False, "PyMuPDF não instalado. Execute: pip install pymupdf"
    except Exception as e:
        logger.error(f"[PDF] Erro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, str(e)


def translate_pdf_simple(
    input_path: Path,
    output_path: Path,
    translated_text: str,
    title: str = "Artigo Traduzido"
) -> Tuple[bool, Optional[str]]:
    """
    Cria um PDF limpo com o texto traduzido.
    Não preserva layout, mas tem formatação profissional.
    """
    try:
        import fitz

        doc = fitz.open()

        # A4
        page_width = 595
        page_height = 842
        margin = 50
        font_size = 11
        line_height = font_size * 1.4

        paragraphs = translated_text.split('\n\n')

        current_page = doc.new_page(width=page_width, height=page_height)
        y = margin

        # Título
        current_page.insert_text(
            (margin, y + 20),
            title,
            fontsize=18,
            fontname="hebo",  # Helvetica Bold
            color=(0, 0, 0)
        )
        y += 50

        usable_width = page_width - 2 * margin

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Verifica se precisa nova página
            if y > page_height - margin - 50:
                current_page = doc.new_page(width=page_width, height=page_height)
                y = margin

            # Usa textbox para quebra automática
            text_rect = fitz.Rect(margin, y, page_width - margin, page_height - margin)

            rc = current_page.insert_textbox(
                text_rect,
                para,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
                align=0  # Justify
            )

            # Estima altura usada
            lines_needed = len(para) / (usable_width / (font_size * 0.5))
            height_used = max(lines_needed * line_height, line_height * 2)
            y += height_used + 10

        doc.save(str(output_path), garbage=4, deflate=True)
        doc.close()

        return True, None

    except Exception as e:
        logger.error(f"[PDF] Erro ao criar PDF: {e}")
        return False, str(e)
