"""Extração de texto dos materiais enviados (PDF, Word e PowerPoint).

Corresponde à etapa 4.4 da documentação ("Processamento dos arquivos"): o
conteúdo textual é extraído e separado em blocos que preservam a organização
original (títulos, parágrafos, listas e tabelas).
"""
import re
import time

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pptx import Presentation
from pypdf import PdfReader

from ..config import MAX_OCR_PAGES, MAX_OCR_SECONDS
from ..models.document import TABLE_CELL_SEPARATOR, make_block
from ..models.text import clean_text
from . import ocr

LIST_ITEM_PATTERN = re.compile(r'^(?:[a-zA-Z]|\d+)[\).]')


def _paragraph_blocks(text):
    blocks = [
        make_block('paragraph', clean_text(part))
        for part in re.split(r'\n\s*\n+', text)
        if clean_text(part)
    ]
    if not blocks and text:
        blocks = [make_block('paragraph', text)]
    return blocks


def _ocr_page_text(file_path, page_number, total_pages, source_lang, state):
    if total_pages > MAX_OCR_PAGES:
        raise ocr.OCRProcessingError(
            f'O OCR está limitado a {MAX_OCR_PAGES} páginas por arquivo.'
        )
    if state['deadline'] is None:
        state['deadline'] = time.monotonic() + MAX_OCR_SECONDS
    elif time.monotonic() >= state['deadline']:
        raise ocr.OCRProcessingError(
            f'O reconhecimento OCR excedeu o limite de tempo de {MAX_OCR_SECONDS} segundos.'
        )
    ocr.check_ocr_ready(source_lang)
    try:
        import pymupdf
        if state['rendered_pdf'] is None:
            state['rendered_pdf'] = pymupdf.open(file_path)
        return ocr.recognize_pdf_page(
            state['rendered_pdf'].load_page(page_number - 1),
            source_lang,
        )
    except ocr.OCRProcessingError:
        raise
    except Exception as exc:
        raise ocr.OCRProcessingError(
            'Não foi possível abrir o PDF para reconhecimento OCR.'
        ) from exc


def extract_pdf_document(file_path: str, source_lang='pt'):
    pages = []
    state = {'rendered_pdf': None, 'deadline': None}
    try:
        with open(file_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            total_pages = len(reader.pages)
            for page_number, page in enumerate(reader.pages, start=1):
                text = clean_text(page.extract_text() or '')
                if not text:
                    text = _ocr_page_text(file_path, page_number, total_pages, source_lang, state)
                pages.append({
                    'page_title': f'Página {page_number}',
                    'blocks': _paragraph_blocks(text),
                })
    finally:
        if state['rendered_pdf'] is not None:
            state['rendered_pdf'].close()
    return pages


def _word_paragraph_type(paragraph):
    style_name = (paragraph.style.name or '').lower()
    if style_name.startswith(('heading', 'title', 'subtitle')):
        return 'heading'
    if 'list' in style_name:
        return 'list-item'
    return 'paragraph'


def extract_word_document(file_path: str):
    document = Document(file_path)
    blocks = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, document)
            text = clean_text(paragraph.text)
            if text:
                blocks.append(make_block(_word_paragraph_type(paragraph), text))
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            for row in table.rows:
                cells = [clean_text(cell.text) for cell in row.cells]
                row_text = TABLE_CELL_SEPARATOR.join(text for text in cells if text)
                if row_text:
                    blocks.append(make_block('table-row', row_text))

    return [{'page_title': 'Página 1', 'blocks': blocks}]


def extract_powerpoint_document(file_path: str):
    presentation = Presentation(file_path)
    pages = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        blocks = []
        text_shapes = sorted(
            (
                shape for shape in slide.shapes
                if getattr(shape, 'has_text_frame', False) or getattr(shape, 'has_table', False)
            ),
            key=lambda shape: (shape.top, shape.left),
        )
        for shape in text_shapes:
            if getattr(shape, 'has_table', False):
                for row in shape.table.rows:
                    row_text = TABLE_CELL_SEPARATOR.join(
                        clean_text(cell.text) for cell in row.cells if clean_text(cell.text)
                    )
                    if row_text:
                        blocks.append(make_block('table-row', row_text))
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = clean_text(paragraph.text)
                if text:
                    block_type = 'list-item' if LIST_ITEM_PATTERN.match(text) else 'paragraph'
                    blocks.append(make_block(block_type, text))
        pages.append({'page_title': f'Slide {slide_number}', 'blocks': blocks})
    return pages


def extract_document_pages(file_path: str, extension: str, source_lang='pt'):
    """Escolhe o extrator pela extensão do arquivo."""
    ext = extension.lower()
    if ext == '.pdf':
        return extract_pdf_document(file_path, source_lang=source_lang)
    if ext == '.docx':
        return extract_word_document(file_path)
    if ext == '.pptx':
        return extract_powerpoint_document(file_path)
    raise ValueError('Formato não suportado.')
