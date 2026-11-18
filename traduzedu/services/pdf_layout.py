"""Tradução do PDF mantendo o layout original.

O texto de cada bloco do PDF é localizado com a posição, o tamanho, a cor e o
peso da fonte. Depois da tradução, o texto original é apagado da página (as
imagens, os fundos e os desenhos ficam intactos) e a tradução é escrita no
mesmo lugar, com a mesma aparência. Se a tradução for mais longa, ela pode
ocupar o espaço livre logo abaixo e, se ainda assim não couber, a fonte
diminui o necessário.
"""
import html
import re
from dataclasses import dataclass, field

import pymupdf

from . import extraction

BULLET_CHARS = set('●•▪■◆◦○·–-➢➤►✓✔')
HAS_LETTER = re.compile(r'[^\W\d_]')
SERIF_FONT_HINTS = ('times', 'serif', 'georgia', 'garamond', 'cambria', 'book')
HORIZONTAL = (1.0, 0.0)


class InvalidPdfError(ValueError):
    pass


class NoTextFoundError(ValueError):
    pass


@dataclass
class TextUnit:
    """Um trecho de texto do PDF que será traduzido e reescrito no mesmo lugar."""

    rect: tuple
    text: str
    size: float
    color: int
    bold: bool = False
    italic: bool = False
    serif: bool = False
    bullet: bool = False
    line_height: float = 1.15
    line_count: int = 1


@dataclass
class PageLayout:
    units: list = field(default_factory=list)
    fallback_blocks: list = field(default_factory=list)
    ocr_error: str = None


@dataclass
class LayoutDocument:
    path: str
    pages: list


def _is_bullet(span):
    text = span['text'].strip()
    return len(text) == 1 and text in BULLET_CHARS


def _unit_from_block(block):
    lines = [line for line in block['lines'] if tuple(line['dir']) == HORIZONTAL]
    spans = [span for line in lines for span in line['spans'] if span['text'].strip()]
    if not spans:
        return None

    bullet = _is_bullet(spans[0])
    body = spans[1:] if bullet else spans
    if not body:
        return None

    text_lines = []
    for line in lines:
        parts = [span['text'] for span in line['spans'] if not (bullet and span is spans[0])]
        line_text = ''.join(parts).strip()
        if line_text:
            text_lines.append(line_text)
    text = ' '.join(' '.join(text_lines).split())
    if not HAS_LETTER.search(text):
        return None

    rect = pymupdf.Rect()
    for span in body:
        rect |= span['bbox']

    main = max(body, key=lambda span: len(span['text']))
    font_name = main['font'].lower()
    line_count = max(1, len(text_lines))
    line_height = 1.15
    if line_count > 1 and main['size']:
        line_height = min(max(rect.height / line_count / main['size'], 1.0), 1.6)

    return TextUnit(
        rect=tuple(rect),
        text=text,
        size=round(main['size'], 1),
        color=main['color'],
        bold=bool(main['flags'] & 16) or 'bold' in font_name,
        italic=bool(main['flags'] & 2) or 'italic' in font_name,
        serif=any(hint in font_name for hint in SERIF_FONT_HINTS),
        bullet=bullet,
        line_height=line_height,
        line_count=line_count,
    )


def extract_page_units(page):
    units = []
    for block in page.get_text('dict')['blocks']:
        if block['type'] != 0:
            continue
        unit = _unit_from_block(block)
        if unit is not None:
            units.append(unit)
    return units


def read_document(file_path, source_lang='pt'):
    """Lê o PDF e separa o texto de cada página em unidades com posição.

    Páginas sem texto selecionável passam pela extração com OCR; o texto
    reconhecido aparece na visualização, mas a página fica como imagem no PDF.
    """
    try:
        document = pymupdf.open(file_path)
    except Exception as exc:
        raise InvalidPdfError('O arquivo não é um PDF válido.') from exc
    try:
        if not document.is_pdf:
            raise InvalidPdfError('O arquivo não é um PDF válido.')
        if document.needs_pass:
            raise InvalidPdfError('O PDF está protegido por senha.')
        pages = [PageLayout(units=extract_page_units(page)) for page in document]
    finally:
        document.close()

    if any(not page.units for page in pages):
        extracted = extraction.extract_pdf_document(file_path, source_lang=source_lang)
        for page, fallback in zip(pages, extracted):
            if not page.units:
                page.fallback_blocks = fallback.get('blocks', [])
                page.ocr_error = fallback.get('ocr_error')

    if not any(page.units or any(block['text'] for block in page.fallback_blocks) for page in pages):
        raise NoTextFoundError(
            'Nenhum texto legível foi encontrado. Em PDFs digitalizados, '
            'verifique se o Tesseract OCR e o pacote do idioma original estão instalados.'
        )
    return LayoutDocument(path=file_path, pages=pages)


def _available_rect(unit, others, page_rect):
    """Área em que a tradução pode ser escrita.

    Texto de uma linha (títulos, faixas, rótulos) continua numa linha só: se a
    tradução for mais longa, a fonte diminui. Texto de várias linhas pode usar
    também o espaço livre logo abaixo antes de diminuir a fonte.
    """
    x0, y0, x1, y1 = unit.rect
    if unit.line_count == 1:
        return pymupdf.Rect(x0, y0, x1, y0 + max(y1 - y0, unit.size * unit.line_height * 1.15))
    limit = min(page_rect.y1 - 2, y1 + 3 * unit.size)
    for other in others:
        if other is unit:
            continue
        ox0, oy0, ox1, _oy1 = other.rect
        overlaps_horizontally = ox0 < x1 and ox1 > x0
        if overlaps_horizontally and oy0 >= y1 - 1:
            limit = min(limit, oy0 - 2)
    return pymupdf.Rect(x0, y0, x1, max(limit, y1 + unit.size * 0.3))


def _css(unit):
    family = 'serif' if unit.serif else 'sans-serif'
    return (
        '* {'
        f'font-family: {family}; font-size: {unit.size:.1f}px; color: #{unit.color:06x};'
        f'font-weight: {"bold" if unit.bold else "normal"};'
        f'font-style: {"italic" if unit.italic else "normal"};'
        f'line-height: {unit.line_height:.2f}; margin: 0; padding: 0;'
        f'{"white-space: nowrap;" if unit.line_count == 1 else ""}'
        '}'
    )


def render_translated_pdf(layout, translations):
    """Gera o PDF traduzido.

    translations[i][j] é a tradução da unidade j da página i.
    """
    document = pymupdf.open(layout.path)
    try:
        for page, page_layout, page_translations in zip(document, layout.pages, translations):
            if not page_layout.units:
                continue
            for unit in page_layout.units:
                page.add_redact_annot(unit.rect, fill=False)
            page.apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_NONE,
                graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
            )
            for unit, translated in zip(page_layout.units, page_translations):
                page.insert_htmlbox(
                    _available_rect(unit, page_layout.units, page.rect),
                    html.escape(translated or unit.text),
                    css=_css(unit),
                    scale_low=0,
                )
        # Sem isso a fonte inteira é embutida em cada página e o PDF fica
        # várias vezes maior que o original.
        document.subset_fonts()
        return document.tobytes(garbage=3, deflate=True)
    finally:
        document.close()


def preview_blocks(units, translations):
    """Blocos para a visualização na tela (título, item de lista ou parágrafo)."""
    sizes = sorted(unit.size for unit in units)
    median = sizes[len(sizes) // 2] if sizes else 0
    blocks = []
    for unit, translated in zip(units, translations):
        if unit.bullet:
            block_type = 'list-item'
        elif median and (unit.size >= median * 1.3 or (unit.bold and unit.size >= median)):
            block_type = 'heading'
        else:
            block_type = 'paragraph'
        blocks.append({'type': block_type, 'text': translated})
    return blocks
