import io
import hashlib
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from flask import Flask, jsonify, request, send_file, send_from_directory
from docx.table import Table
from docx.text.paragraph import Paragraph
from pptx import Presentation
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph as PDFParagraph,
    SimpleDocTemplate,
    Spacer,
    Table as PDFTable,
    TableStyle,
)
from werkzeug.utils import secure_filename

from translation_engine import (
    TranslationError,
    UnsupportedLanguagePair,
    argos_model_status,
    configured_endpoints,
    configured_provider_names,
    install_argos_model,
    provider_status,
    refresh_argos_catalog,
    translate_text,
    translate_texts,
)

LOGGER = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
try:
    MAX_TRANSLATION_SECONDS = int(os.getenv('TRANSLATION_TOTAL_TIMEOUT_SECONDS', '300'))
except ValueError:
    LOGGER.warning('Invalid TRANSLATION_TOTAL_TIMEOUT_SECONDS; using 300 seconds.')
    MAX_TRANSLATION_SECONDS = 300
MAX_TRANSLATION_SECONDS = min(max(MAX_TRANSLATION_SECONDS, 30), 900)
app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES + 64 * 1024
ACTIVE_TRANSLATIONS = set()
ACTIVE_TRANSLATIONS_LOCK = Lock()
SUPPORTED_LANGS = {'pt', 'en', 'es'}
OCR_LANGUAGES = {'pt': 'por', 'en': 'eng', 'es': 'spa'}
EXPORT_FORMATS = {'txt', 'docx', 'pptx', 'pdf'}
EXPORT_BLOCK_TYPES = {'heading', 'list-item', 'paragraph', 'table-row'}
MAX_EXPORT_PAGES = 300
MAX_EXPORT_BLOCKS = 5000
MAX_EXPORT_TEXT_BYTES = MAX_UPLOAD_BYTES
MAX_OCR_PAGES = 100
MAX_OCR_SECONDS = 120
MAX_TRANSLATION_BATCH_SIZE = 20
DEMO_RESULTS_PATH = Path(__file__).with_name('demo_results.json')
DEMO_FORMATS = {'pdf', 'docx', 'pptx'}


class OCRProcessingError(ValueError):
    pass


def normalize_lang(code: str) -> str:
    if not code:
        return 'pt'
    normalized = code.strip().lower().replace('_', '-')
    mapping = {
        'pt': 'pt',
        'pt-br': 'pt',
        'pt-BR': 'pt',
        'en': 'en',
        'en-us': 'en',
        'en-US': 'en',
        'es': 'es',
        'es-es': 'es',
        'es-ES': 'es',
    }
    return mapping.get(normalized, normalized)


def clean_text(text: str) -> str:
    if text is None:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def split_text_chunks(text: str, max_chars: int = 1400):
    cleaned = clean_text(text)
    if not cleaned:
        return []

    def split_oversized(value):
        pieces = []
        while len(value) > max_chars:
            boundary = value.rfind(' ', 0, max_chars + 1)
            if boundary <= 0:
                boundary = max_chars
            pieces.append(value[:boundary].strip())
            value = value[boundary:].strip()
        if value:
            pieces.append(value)
        return pieces

    paragraphs = [item.strip() for item in re.split(r'\n\s*\n+', cleaned) if item.strip()]
    chunks = []
    current = ''

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            if current:
                current += '\n\n'
            current += paragraph
        else:
            if current:
                chunks.append(current)
            current = ''
            if len(paragraph) <= max_chars:
                current = paragraph
            else:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    for piece in split_oversized(sentence):
                        if len(piece) > max_chars:
                            raise ValueError('Não foi possível limitar o tamanho do trecho de tradução.')
                        if current and len(current) + len(piece) + 1 <= max_chars:
                            current += ' ' + piece
                        else:
                            if current:
                                chunks.append(current)
                            current = piece
                if current:
                    chunks.append(current)
                current = ''

    if current:
        chunks.append(current)

    return chunks if chunks else [cleaned[:max_chars]]


def translate_chunk(text: str, source_lang: str, target_lang: str, deadline=None) -> str:
    if not text or not text.strip():
        return ''
    return translate_text(text, source_lang, target_lang, deadline=deadline)


def translate_blocks(blocks, source_lang, target_lang, deadline=None):
    pending = []
    for block in blocks:
        text = clean_text(block.get('text', ''))
        if not text:
            continue
        for chunk in split_text_chunks(text):
            pending.append((block.get('type', 'paragraph'), chunk))

    translated = []
    for batch_start in range(0, len(pending), MAX_TRANSLATION_BATCH_SIZE):
        if deadline is not None and time.monotonic() >= deadline:
            raise TranslationError('O tempo máximo desta tradução foi excedido.')
        batch = pending[batch_start:batch_start + MAX_TRANSLATION_BATCH_SIZE]
        translated_texts = translate_texts(
            [text for _block_type, text in batch],
            source_lang,
            target_lang,
            deadline=deadline,
        )
        if len(translated_texts) != len(batch):
            raise TranslationError('O mecanismo retornou uma quantidade inválida de traduções.')
        translated.extend(
            {'type': block_type, 'text': translated_text}
            for (block_type, _text), translated_text in zip(batch, translated_texts)
        )
    return translated


def ocr_status(source_lang=None):
    try:
        import pytesseract
    except ImportError:
        return {
            'available': False,
            'languages': [],
            'error': 'O OCR requer as dependências Python pytesseract e Pillow.',
        }

    tesseract_cmd = os.getenv('TESSERACT_CMD')
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        configured_tesseract = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if configured_tesseract.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(configured_tesseract)

    try:
        version = str(pytesseract.get_tesseract_version())
        languages = sorted(set(pytesseract.get_languages(config='')))
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, OSError):
        return {
            'available': False,
            'languages': [],
            'error': (
                'O mecanismo Tesseract OCR não foi encontrado. Instale o Tesseract '
                'e reinicie o aplicativo; consulte as instruções no README.'
            ),
        }

    result = {
        'available': True,
        'version': version,
        'languages': languages,
        'missing_languages': [],
    }
    if source_lang in OCR_LANGUAGES:
        required = OCR_LANGUAGES[source_lang]
        if required not in languages:
            result['missing_languages'] = [required]
            result['error'] = (
                f'O Tesseract está instalado, mas falta o pacote de idioma {required}. '
                'Adicione esse idioma aos dados do Tesseract e tente novamente.'
            )
    return result


def _check_ocr_ready(source_lang):
    status = ocr_status(source_lang)
    if not status['available'] or status.get('missing_languages'):
        raise OCRProcessingError(status.get('error', 'O OCR não está disponível.'))


def _recognize_pdf_page(pdf_page, source_lang):
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OCRProcessingError(
            'O OCR requer PyMuPDF, pytesseract e Pillow. Instale as dependências do projeto.'
        ) from exc

    scale = 2
    page_width, page_height = pdf_page.rect.width, pdf_page.rect.height
    if page_width * page_height * scale * scale > 25_000_000:
        raise OCRProcessingError(
            'Uma página deste PDF é grande demais para o reconhecimento OCR.'
        )
    try:
        pixmap = pdf_page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale),
            alpha=False,
        )
        image = Image.open(io.BytesIO(pixmap.tobytes('png')))
        return clean_text(pytesseract.image_to_string(
            image,
            lang=OCR_LANGUAGES[source_lang],
            timeout=30,
        ))
    except (pytesseract.TesseractError, RuntimeError, OSError, ValueError) as exc:
        raise OCRProcessingError(
            'Não foi possível reconhecer o texto deste PDF. Verifique a qualidade '
            'da imagem e os dados de idioma do Tesseract.'
        ) from exc


def extract_pdf_document(file_path: str, source_lang='pt'):
    pages = []
    rendered_pdf = None
    ocr_deadline = None
    try:
        with open(file_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            for page_number, page in enumerate(reader.pages, start=1):
                text = clean_text(page.extract_text() or '')
                if not text:
                    if len(reader.pages) > MAX_OCR_PAGES:
                        raise OCRProcessingError(
                            f'O OCR está limitado a {MAX_OCR_PAGES} páginas por arquivo.'
                        )
                    if ocr_deadline is None:
                        ocr_deadline = time.monotonic() + MAX_OCR_SECONDS
                    elif time.monotonic() >= ocr_deadline:
                        raise OCRProcessingError(
                            'O reconhecimento OCR excedeu o limite de tempo de 120 segundos.'
                        )
                    _check_ocr_ready(source_lang)
                    try:
                        import pymupdf
                        if rendered_pdf is None:
                            rendered_pdf = pymupdf.open(file_path)
                        text = _recognize_pdf_page(
                            rendered_pdf.load_page(page_number - 1),
                            source_lang,
                        )
                    except OCRProcessingError:
                        raise
                    except Exception as exc:
                        raise OCRProcessingError(
                            'Não foi possível abrir o PDF para reconhecimento OCR.'
                        ) from exc

                blocks = [
                    {'type': 'paragraph', 'text': clean_text(part)}
                    for part in re.split(r'\n\s*\n+', text)
                    if clean_text(part)
                ]
                if not blocks and text:
                    blocks = [{'type': 'paragraph', 'text': text}]
                pages.append({
                    'page_title': f'Página {page_number}',
                    'blocks': blocks,
                })
    finally:
        if rendered_pdf is not None:
            rendered_pdf.close()
    return pages


def extract_word_document(file_path: str):
    document = Document(file_path)
    blocks = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, document)
            text = clean_text(paragraph.text)
            if text:
                style_name = (paragraph.style.name or '').lower()
                if style_name.startswith(('heading', 'title', 'subtitle')):
                    block_type = 'heading'
                elif 'list' in style_name:
                    block_type = 'list-item'
                else:
                    block_type = 'paragraph'
                blocks.append({'type': block_type, 'text': text})
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            for row in table.rows:
                cells = [clean_text(cell.text) for cell in row.cells]
                row_text = ' | '.join(text for text in cells if text)
                if row_text:
                    blocks.append({'type': 'table-row', 'text': row_text})

    page = {
        'page_title': 'Página 1',
        'blocks': blocks,
    }
    return [page]


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
                    row_text = ' | '.join(
                        clean_text(cell.text) for cell in row.cells if clean_text(cell.text)
                    )
                    if row_text:
                        blocks.append({'type': 'table-row', 'text': row_text})
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = clean_text(paragraph.text)
                if text:
                    block_type = 'list-item' if re.match(r'^(?:[a-zA-Z]|\d+)[\).]', text) else 'paragraph'
                    blocks.append({'type': block_type, 'text': text})
        pages.append({
            'page_title': f'Slide {slide_number}',
            'blocks': blocks,
        })
    return pages


def extract_document_pages(file_path: str, extension: str, source_lang='pt'):
    ext = extension.lower()
    if ext == '.pdf':
        return extract_pdf_document(file_path, source_lang=source_lang)
    if ext == '.docx':
        return extract_word_document(file_path)
    if ext == '.pptx':
        return extract_powerpoint_document(file_path)
    raise ValueError('Formato não suportado.')


def translate_document_pages(
    file_path: str,
    extension: str,
    source_lang: str,
    target_lang: str,
    pages=None,
    deadline=None,
):
    if pages is None:
        pages = extract_document_pages(file_path, extension)
    translated_pages = []
    has_text = any(
        clean_text(block.get('text', ''))
        for page in pages
        for block in page.get('blocks', [])
    )
    if not has_text:
        raise ValueError('Nenhum texto foi encontrado no documento para traduzir.')

    deadline = deadline or (time.monotonic() + MAX_TRANSLATION_SECONDS)
    for page in pages:
        translated = translate_blocks(
            page.get('blocks', []), source_lang, target_lang, deadline=deadline
        )
        translated_pages.append({
            'page_title': page.get('page_title', 'Página 1'),
            'title': '',
            'subtitle': '',
            'blocks': translated,
        })

    return translated_pages


def _validate_export_pages(raw_pages):
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ValueError('Nenhuma página traduzida foi informada para o download.')
    if len(raw_pages) > MAX_EXPORT_PAGES:
        raise ValueError(f'O documento excede o limite de {MAX_EXPORT_PAGES} páginas.')

    pages = []
    total_bytes = 0
    block_count = 0
    for page_number, page in enumerate(raw_pages, start=1):
        if not isinstance(page, dict) or not isinstance(page.get('blocks'), list):
            raise ValueError(f'A estrutura da página {page_number} é inválida.')
        normalized_page = {}
        for field in ('page_title', 'title', 'subtitle'):
            value = page.get(field, '')
            if not isinstance(value, str):
                raise ValueError(f'O campo {field} da página {page_number} é inválido.')
            normalized_page[field] = clean_text(value)
            total_bytes += len(normalized_page[field].encode('utf-8'))

        normalized_page['blocks'] = []
        block_count += len(page['blocks'])
        if block_count > MAX_EXPORT_BLOCKS:
            raise ValueError('O documento contém blocos de texto demais para exportar.')
        for block in page['blocks']:
            if not isinstance(block, dict):
                raise ValueError(f'Um bloco da página {page_number} é inválido.')
            block_type = block.get('type', 'paragraph')
            text = block.get('text', '')
            if (
                not isinstance(block_type, str)
                or block_type not in EXPORT_BLOCK_TYPES
                or not isinstance(text, str)
            ):
                raise ValueError(f'Um bloco da página {page_number} é inválido.')
            text = clean_text(text)
            total_bytes += len(text.encode('utf-8'))
            normalized_page['blocks'].append({'type': block_type, 'text': text})

        pages.append(normalized_page)

    if total_bytes > MAX_EXPORT_TEXT_BYTES:
        raise ValueError('O conteúdo traduzido excede o limite de 10 MB para exportação.')
    if not any(block['text'] for page in pages for block in page['blocks']):
        raise ValueError('Não há conteúdo traduzido para baixar.')
    return pages


def _export_text(pages):
    sections = []
    for page in pages:
        parts = [
            page['page_title'],
            page['title'],
            page['subtitle'],
            *(block['text'] for block in page['blocks']),
        ]
        sections.append('\n\n'.join(part for part in parts if part))
    return '\n\n--------------------\n\n'.join(sections)


def _export_docx(pages):
    document = Document()
    document.core_properties.title = 'Material traduzido'
    for page_index, page in enumerate(pages):
        if page_index:
            document.add_page_break()
        if page['page_title']:
            document.add_heading(page['page_title'], level=1)
        if page['title']:
            document.add_heading(page['title'], level=2)
        if page['subtitle']:
            document.add_paragraph(page['subtitle'], style='Subtitle')

        blocks = page['blocks']
        block_index = 0
        while block_index < len(blocks):
            block = blocks[block_index]
            if block['type'] == 'table-row':
                rows = []
                while block_index < len(blocks) and blocks[block_index]['type'] == 'table-row':
                    rows.append(blocks[block_index]['text'].split(' | '))
                    block_index += 1
                column_count = max(len(row) for row in rows)
                table = document.add_table(rows=len(rows), cols=column_count)
                try:
                    table.style = 'Light Shading Accent 1'
                except KeyError:
                    LOGGER.info('The requested DOCX table style is not available.')
                for row_index, row in enumerate(rows):
                    for column_index in range(column_count):
                        table.cell(row_index, column_index).text = (
                            row[column_index] if column_index < len(row) else ''
                        )
                continue

            if block['text']:
                if block['type'] == 'heading':
                    document.add_heading(block['text'], level=2)
                elif block['type'] == 'list-item':
                    document.add_paragraph(block['text'], style='List Bullet')
                else:
                    document.add_paragraph(block['text'])
            block_index += 1

    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _export_pptx(pages):
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Inches, Pt

    presentation = Presentation()
    blank_layout = presentation.slide_layouts[6]
    page_width = presentation.slide_width
    content_width = page_width - Inches(1.4)

    def create_slide(page_title, continuation=False):
        slide = presentation.slides.add_slide(blank_layout)
        title_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(0.35), content_width, Inches(0.75)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        title_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.text = (
            f'{page_title} (continuação)' if continuation else page_title
        ) or 'Material traduzido'
        title_paragraph.font.size = Pt(24)
        title_paragraph.font.bold = True
        return slide

    for page in pages:
        page_title = page['page_title'] or page['title'] or 'Material traduzido'
        slide = create_slide(page_title)
        cursor = 1.35

        if page['title'] and page['title'] != page_title:
            title_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(0.55)
            )
            title = title_box.text_frame.paragraphs[0]
            title.text = page['title']
            title.font.size = Pt(20)
            title.font.bold = True
            cursor += 0.6

        if page['subtitle']:
            subtitle_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(0.45)
            )
            subtitle = subtitle_box.text_frame.paragraphs[0]
            subtitle.text = page['subtitle']
            subtitle.font.size = Pt(14)
            subtitle.font.italic = True
            cursor += 0.5

        blocks = page['blocks']
        block_index = 0
        while block_index < len(blocks):
            block = blocks[block_index]
            if block['type'] == 'table-row':
                rows = []
                while block_index < len(blocks) and blocks[block_index]['type'] == 'table-row':
                    rows.append(blocks[block_index]['text'].split(' | '))
                    block_index += 1
                column_count = max(len(row) for row in rows)
                for first_row in range(0, len(rows), 8):
                    row_batch = rows[first_row:first_row + 8]
                    table_height = max(0.4, 0.38 * len(row_batch))
                    if cursor + table_height > 7.1:
                        slide = create_slide(page_title, continuation=True)
                        cursor = 1.2
                    table = slide.shapes.add_table(
                        len(row_batch),
                        column_count,
                        Inches(0.8),
                        Inches(cursor),
                        content_width,
                        Inches(table_height),
                    ).table
                    for row_index, row in enumerate(row_batch):
                        for column_index in range(column_count):
                            table.cell(row_index, column_index).text = (
                                row[column_index] if column_index < len(row) else ''
                            )
                    cursor += table_height + 0.15
                continue

            text = block['text']
            if not text:
                block_index += 1
                continue
            line_count = max(1, (len(text) + 99) // 100)
            height = min(2.4, max(0.36, 0.28 * line_count + 0.12))
            if cursor + height > 7.1:
                slide = create_slide(page_title, continuation=True)
                cursor = 1.2
            text_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(height)
            )
            text_frame = text_box.text_frame
            text_frame.word_wrap = True
            text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            paragraph = text_frame.paragraphs[0]
            paragraph.text = f'• {text}' if block['type'] == 'list-item' else text
            paragraph.font.size = Pt(18 if block['type'] == 'heading' else 14)
            paragraph.font.bold = block['type'] == 'heading'
            cursor += height + 0.1
            block_index += 1

    output = io.BytesIO()
    presentation.save(output)
    return output.getvalue()


def _pdf_paragraph(text, style):
    return PDFParagraph(escape(text).replace('\n', '<br/>'), style)


def _export_pdf(pages):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TranslatedPageTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#263452'),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='TranslatedHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#34415b'),
        spaceBefore=8,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name='TranslatedBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=8,
        splitLongWords=True,
    ))
    story = []
    for page_index, page in enumerate(pages):
        if page_index:
            story.append(PageBreak())
        if page['page_title']:
            story.append(_pdf_paragraph(page['page_title'], styles['TranslatedPageTitle']))
        if page['title']:
            story.append(_pdf_paragraph(page['title'], styles['TranslatedHeading']))
        if page['subtitle']:
            story.append(_pdf_paragraph(page['subtitle'], styles['Italic']))

        blocks = page['blocks']
        block_index = 0
        while block_index < len(blocks):
            block = blocks[block_index]
            if block['type'] == 'table-row':
                rows = []
                while block_index < len(blocks) and blocks[block_index]['type'] == 'table-row':
                    rows.append([
                        _pdf_paragraph(cell, styles['TranslatedBody'])
                        for cell in blocks[block_index]['text'].split(' | ')
                    ])
                    block_index += 1
                column_count = max(len(row) for row in rows)
                table_data = [
                    row + [''] * (column_count - len(row))
                    for row in rows
                ]
                table = PDFTable(table_data, colWidths=None, repeatRows=0)
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dce2ed')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.extend((table, Spacer(1, 8)))
                continue

            if block['text']:
                if block['type'] == 'heading':
                    style = styles['TranslatedHeading']
                    text = block['text']
                elif block['type'] == 'list-item':
                    style = styles['TranslatedBody']
                    text = f'• {block["text"]}'
                else:
                    style = styles['TranslatedBody']
                    text = block['text']
                story.append(_pdf_paragraph(text, style))
            block_index += 1

    output = io.BytesIO()
    SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title='Material traduzido',
        author='Tradutor de Aulas',
    ).build(story)
    return output.getvalue()


@app.route('/')
def index():
    return send_from_directory(Path(__file__).parent, 'index.html')


@app.route('/style.css')
def stylesheet():
    return send_from_directory(Path(__file__).parent, 'style.css')


@app.route('/script.js')
def javascript():
    return send_from_directory(Path(__file__).parent, 'script.js')


@app.route('/tmp-docs/<path:filename>')
def demo_file(filename):
    if filename not in {'sample.pdf', 'sample.docx', 'sample.pptx'}:
        return jsonify({'error': 'Arquivo de demonstração não encontrado.'}), 404
    return send_from_directory(Path(__file__).parent / 'tmp-docs', filename)


@app.route('/api/health')
def health():
    endpoints = configured_endpoints()
    return jsonify({
        'status': 'ok',
        'libretranslate_url': endpoints[0] if endpoints else None,
        'configured_endpoints': endpoints,
        'translation_providers': configured_provider_names(),
    })


@app.route('/api/translation/status')
def translation_status():
    statuses = provider_status()
    available_pairs = sorted({
        pair
        for provider in statuses
        if provider['status'] == 'available'
        for pair in provider.get('pairs', [])
        if pair.split('->', 1)[0] != pair.split('->', 1)[-1]
    })
    return jsonify({
        'providers': statuses,
        'available_pairs': available_pairs,
        'demo_available': DEMO_RESULTS_PATH.is_file(),
        'max_translation_seconds': MAX_TRANSLATION_SECONDS,
    })


def _validated_language_pair(source_lang, target_lang):
    source = normalize_lang(source_lang or '')
    target = normalize_lang(target_lang or '')
    if source not in SUPPORTED_LANGS or target not in SUPPORTED_LANGS or source == target:
        raise ValueError('Selecione dois idiomas diferentes entre português, inglês e espanhol.')
    return source, target


@app.route('/api/ocr/status')
def ocr_status_api():
    source_lang = normalize_lang(request.args.get('source_lang', 'pt'))
    if source_lang not in SUPPORTED_LANGS:
        return jsonify({'error': 'Idioma de OCR inválido. Use pt, en ou es.'}), 400
    status = ocr_status(source_lang)
    return jsonify(status)


@app.route('/api/argos/models')
def argos_models():
    try:
        source, target = _validated_language_pair(
            request.args.get('source'),
            request.args.get('target'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(argos_model_status(source, target))
    except Exception as exc:
        app.logger.exception('Could not inspect Argos language models.')
        return jsonify({'error': f'Não foi possível verificar os modelos Argos: {exc}'}), 503


@app.route('/api/argos/catalog', methods=['POST'])
def check_argos_catalog():
    payload = request.get_json(silent=True) or {}
    try:
        source, target = _validated_language_pair(
            payload.get('source'),
            payload.get('target'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(refresh_argos_catalog(source, target))
    except Exception as exc:
        app.logger.exception('Could not update the Argos model catalog.')
        return jsonify({
            'error': (
                'Não foi possível consultar o catálogo Argos. Verifique a conexão '
                f'com a internet. Detalhe: {exc}'
            )
        }), 503


@app.route('/api/argos/models/install', methods=['POST'])
def install_argos_model_route():
    payload = request.get_json(silent=True) or {}
    try:
        source, target = _validated_language_pair(
            payload.get('source'),
            payload.get('target'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(install_argos_model(source, target))
    except LookupError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        app.logger.exception('Could not install requested Argos model.')
        return jsonify({'error': f'Não foi possível instalar o modelo Argos: {exc}'}), 503


@app.route('/api/demo/<format_name>')
def demo_result(format_name):
    format_name = format_name.lower()
    if format_name not in DEMO_FORMATS:
        return jsonify({'error': 'Formato de demonstração inválido.'}), 404
    try:
        with DEMO_RESULTS_PATH.open(encoding='utf-8') as demo_file:
            results = json.load(demo_file)
    except (OSError, json.JSONDecodeError):
        LOGGER.exception('Could not load prepared translation demonstration.')
        return jsonify({'error': 'A demonstração não está disponível.'}), 503
    if format_name not in results:
        return jsonify({'error': 'Demonstração não encontrada para este formato.'}), 404
    return jsonify({'demo': True, **results[format_name]})


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({
        'error': 'O arquivo ou conteúdo enviado excede o limite de 10 MB.'
    }), 413


@app.route('/api/download/<format_name>', methods=['POST'])
def download_translation(format_name):
    format_name = format_name.lower()
    if format_name not in EXPORT_FORMATS:
        return jsonify({'error': 'Formato de download inválido.'}), 404
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Os dados da tradução estão ausentes ou inválidos.'}), 400
    try:
        pages = _validate_export_pages(payload.get('pages'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    original_name = payload.get('filename', 'material')
    if not isinstance(original_name, str):
        return jsonify({'error': 'O nome do documento é inválido.'}), 400
    base_name = secure_filename(Path(original_name).stem)[:100] or 'material'

    try:
        if format_name == 'txt':
            content = ('\ufeff' + _export_text(pages)).encode('utf-8')
            content_type = 'text/plain; charset=utf-8'
        elif format_name == 'docx':
            content = _export_docx(pages)
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif format_name == 'pptx':
            content = _export_pptx(pages)
            content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        else:
            content = _export_pdf(pages)
            content_type = 'application/pdf'
    except Exception as exc:
        app.logger.exception('Could not create %s translation download.', format_name)
        return jsonify({
            'error': f'Não foi possível gerar o arquivo {format_name.upper()}: {exc}'
        }), 500

    return send_file(
        io.BytesIO(content),
        mimetype=content_type,
        as_attachment=True,
        download_name=f'{base_name}-traduzido.{format_name}',
    )


@app.route('/api/translate', methods=['POST'])
def translate_document():
    if 'file' not in request.files:
        return jsonify({'error': 'Arquivo não enviado.'}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'error': 'Selecione um arquivo antes de traduzir.'}), 400

    file_ext = Path(uploaded_file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Formato não permitido. Envie somente um arquivo PDF.'}), 400
    uploaded_file.seek(0, os.SEEK_END)
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)
    if file_size == 0:
        return jsonify({'error': 'O arquivo está vazio. Selecione um documento com conteúdo.'}), 400
    if file_size > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'O arquivo excede o limite de 10 MB. Escolha um arquivo menor.'}), 413

    source_lang = normalize_lang(request.form.get('source_lang', 'pt'))
    target_lang = normalize_lang(request.form.get('target_lang', 'en'))

    if source_lang not in SUPPORTED_LANGS or target_lang not in SUPPORTED_LANGS:
        return jsonify({'error': 'Idioma inválido. Use pt, en ou es.'}), 400

    if source_lang == target_lang:
        return jsonify({'error': 'Selecione idiomas diferentes para a tradução.'}), 400

    original_name = secure_filename(uploaded_file.filename)
    if not original_name:
        return jsonify({'error': 'O nome do arquivo é inválido.'}), 400
    digest = hashlib.sha256()
    while True:
        chunk = uploaded_file.stream.read(64 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    uploaded_file.stream.seek(0)
    translation_key = f'{source_lang}:{target_lang}:{digest.hexdigest()}'
    with ACTIVE_TRANSLATIONS_LOCK:
        if translation_key in ACTIVE_TRANSLATIONS:
            uploaded_file.close()
            return jsonify({
                'error': 'Este mesmo documento já está sendo traduzido. Aguarde a tentativa atual terminar.'
            }), 409
        ACTIVE_TRANSLATIONS.add(translation_key)

    base_dir = None
    file_path = None
    try:
        base_dir = tempfile.mkdtemp(prefix='tradutor-')
        file_path = os.path.join(base_dir, original_name)
        uploaded_file.save(file_path)
        try:
            pages = extract_document_pages(
                file_path,
                file_ext,
                source_lang=source_lang,
            )
        except OCRProcessingError as exc:
            app.logger.info('OCR could not read uploaded PDF: %s', exc)
            return jsonify({'error': str(exc)}), 422
        except Exception as exc:
            app.logger.exception('Could not read uploaded %s file', file_ext)
            return jsonify({
                'error': (
                    'Não foi possível ler o PDF. Verifique se o arquivo está íntegro, '
                    'não protegido por senha e se é um PDF válido.'
                )
            }), 400
        if not any(
            clean_text(block.get('text', ''))
            for page in pages
            for block in page.get('blocks', [])
        ):
            return jsonify({
                'error': (
                    'Nenhum texto legível foi encontrado. Em PDFs digitalizados, '
                    'verifique se o Tesseract OCR e o pacote do idioma original estão instalados.'
                )
            }), 422
        try:
            translated_pages = translate_document_pages(
                file_path,
                file_ext,
                source_lang,
                target_lang,
                pages=pages,
                deadline=time.monotonic() + MAX_TRANSLATION_SECONDS,
            )
        except UnsupportedLanguagePair as exc:
            app.logger.info('No configured provider supports requested pair: %s', exc)
            return jsonify({'error': str(exc)}), 422
        except TranslationError as exc:
            app.logger.exception('Translation failed for uploaded %s file', file_ext)
            status_code = 504 if 'tempo máximo' in str(exc).lower() else 503
            return jsonify({'error': str(exc)}), status_code
        except Exception as exc:
            app.logger.exception('Could not translate uploaded %s file', file_ext)
            if isinstance(exc, ValueError):
                return jsonify({'error': str(exc)}), 422
            return jsonify({'error': str(exc)}), 503
    finally:
        uploaded_file.close()
        if file_path:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        if base_dir:
            try:
                os.rmdir(base_dir)
            except OSError:
                pass
        with ACTIVE_TRANSLATIONS_LOCK:
            ACTIVE_TRANSLATIONS.discard(translation_key)

    return jsonify({
        'filename': original_name,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'pages': translated_pages,
    })


if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5001'))
    app.run(host=host, port=port, debug=False)
