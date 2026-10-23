import os
import re
import tempfile
from pathlib import Path

import requests
from docx import Document
from flask import Flask, jsonify, request, send_from_directory
from pptx import Presentation
from pypdf import PdfReader
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.', static_url_path='')

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx'}
DEFAULT_LIBRETRANSLATE_URLS = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
]
RAW_LIBRETRANSLATE_URLS = os.getenv('LIBRETRANSLATE_URL', '')
TRANSLATE_URLS = []
if RAW_LIBRETRANSLATE_URLS:
    TRANSLATE_URLS = [
        item.strip()
        for item in RAW_LIBRETRANSLATE_URLS.split(',')
        if item and item.strip()
    ]
if not TRANSLATE_URLS:
    TRANSLATE_URLS = DEFAULT_LIBRETRANSLATE_URLS
LIBRETRANSLATE_URL = TRANSLATE_URLS[0]
SUPPORTED_LANGS = {'pt', 'en', 'es'}


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
    text = text.replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\s+\n\s+', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def split_text_chunks(text: str, max_chars: int = 1400):
    cleaned = clean_text(text)
    if not cleaned:
        return []

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
            if len(paragraph) <= max_chars:
                current = paragraph
            else:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp = ''
                for sentence in sentences:
                    if len(temp) + len(sentence) + 1 <= max_chars:
                        if temp:
                            temp += ' '
                        temp += sentence
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = sentence
                if temp:
                    chunks.append(temp)
                current = ''

    if current:
        chunks.append(current)

    return chunks if chunks else [cleaned[:max_chars]]


def translate_chunk(text: str, source_lang: str, target_lang: str) -> str:
    if not text or not text.strip():
        return ''
    if source_lang == target_lang:
        return text

    payload = {
        'q': text,
        'source': source_lang,
        'target': target_lang,
        'format': 'text',
    }
    last_error = None

    for base_url in TRANSLATE_URLS:
        url = f'{base_url.rstrip("/")}/translate'
        try:
            response = requests.post(url, json=payload, timeout=90)
            if response.status_code != 200:
                last_error = RuntimeError(f'Erro no LibreTranslate ({url}): {response.text[:300]}')
                continue
            data = response.json()
            translated = data.get('translatedText') or data.get('translations', [{}])[0].get('translatedText')
            if translated:
                return translated.strip()
            return text
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise RuntimeError(f'Não foi possível conectar ao LibreTranslate. Verifique LIBRETRANSLATE_URL e o serviço em execução. Detalhe: {last_error}')
    raise RuntimeError('Nenhum endpoint de LibreTranslate disponível para tradução.')


def translate_blocks(blocks, source_lang, target_lang):
    translated = []
    for block in blocks:
        text = clean_text(block.get('text', ''))
        if not text:
            continue
        for chunk in split_text_chunks(text):
            translated_text = translate_chunk(chunk, source_lang, target_lang)
            if translated_text:
                translated.append({
                    'type': block.get('type', 'paragraph'),
                    'text': translated_text,
                })
    return translated


def decorate_page(page):
    blocks = page.get('blocks', [])
    title = ''
    subtitle = ''
    remaining = []

    if blocks:
        first = clean_text(blocks[0].get('text', ''))
        if len(first) < 100 and not re.match(r'^(?:[a-zA-Z]|\d+)[\).]', first):
            title = first
            blocks = blocks[1:]

    if blocks:
        second = clean_text(blocks[0].get('text', ''))
        if len(second) < 180 and not re.match(r'^(?:[a-zA-Z]|\d+)[\).]', second):
            subtitle = second
            blocks = blocks[1:]

    remaining = blocks
    page['title'] = title
    page['subtitle'] = subtitle
    page['blocks'] = remaining
    return page


def extract_pdf_document(file_path: str):
    pages = []
    reader = PdfReader(file_path)
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        blocks = [
            {'type': 'paragraph', 'text': clean_text(part)}
            for part in re.split(r'\n\s*\n+', clean_text(text))
            if clean_text(part)
        ]
        if not blocks:
            blocks = [{'type': 'paragraph', 'text': clean_text(text)}] if clean_text(text) else []
        pages.append({
            'page_title': f'Página {page_number}',
            'blocks': blocks,
        })
    return pages


def extract_word_document(file_path: str):
    document = Document(file_path)
    blocks = []
    for paragraph in document.paragraphs:
        text = clean_text(paragraph.text)
        if text:
            blocks.append({'type': 'paragraph', 'text': text})
    for table in document.tables:
        for row in table.rows:
            row_text = ' | '.join(clean_text(cell.text) for cell in row.cells if clean_text(cell.text))
            if row_text:
                blocks.append({'type': 'list-item', 'text': row_text})

    page = {
        'page_title': 'Página 1',
        'blocks': blocks or [{'type': 'paragraph', 'text': 'Documento Word sem conteúdo textual.'}],
    }
    return [page]


def extract_powerpoint_document(file_path: str):
    presentation = Presentation(file_path)
    pages = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        blocks = []
        for shape in slide.shapes:
            if not hasattr(shape, 'has_text_frame') or not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = clean_text(paragraph.text)
                if text:
                    block_type = 'list-item' if re.match(r'^(?:[a-zA-Z]|\d+)[\).]', text) else 'paragraph'
                    blocks.append({'type': block_type, 'text': text})
        if not blocks:
            blocks = [{'type': 'paragraph', 'text': 'Slide sem conteúdo textual.'}]
        pages.append({
            'page_title': f'Slide {slide_number}',
            'blocks': blocks,
        })
    return pages


def extract_document_pages(file_path: str, extension: str):
    ext = extension.lower()
    if ext == '.pdf':
        return extract_pdf_document(file_path)
    if ext == '.docx':
        return extract_word_document(file_path)
    if ext == '.pptx':
        return extract_powerpoint_document(file_path)
    raise ValueError('Formato não suportado.')


def translate_document_pages(file_path: str, extension: str, source_lang: str, target_lang: str):
    pages = extract_document_pages(file_path, extension)
    translated_pages = []

    for page in pages:
        translated = translate_blocks(page.get('blocks', []), source_lang, target_lang)
        if not translated:
            continue
        page['blocks'] = translated
        decorated = decorate_page(page)
        translated_pages.append({
            'page_title': decorated.get('page_title', page.get('page_title', 'Página 1')),
            'title': decorated.get('title', ''),
            'subtitle': decorated.get('subtitle', ''),
            'blocks': decorated.get('blocks', []),
        })

    if not translated_pages:
        raise ValueError('Nenhum conteúdo foi encontrado para tradução.')

    return translated_pages


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'libretranslate_url': LIBRETRANSLATE_URL,
        'configured_endpoints': TRANSLATE_URLS,
    })


@app.route('/api/translate', methods=['POST'])
def translate_document():
    if 'file' not in request.files:
        return jsonify({'error': 'Arquivo não enviado.'}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'error': 'Selecione um arquivo antes de traduzir.'}), 400

    file_ext = Path(uploaded_file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Formato não permitido. Use PDF, DOCX ou PPTX.'}), 400

    source_lang = normalize_lang(request.form.get('source_lang', 'pt'))
    target_lang = normalize_lang(request.form.get('target_lang', 'en'))

    if source_lang not in SUPPORTED_LANGS or target_lang not in SUPPORTED_LANGS:
        return jsonify({'error': 'Idioma inválido. Use pt, en ou es.'}), 400

    if source_lang == target_lang:
        return jsonify({'error': 'Selecione idiomas diferentes para a tradução.'}), 400

    original_name = secure_filename(uploaded_file.filename)
    base_dir = tempfile.mkdtemp(prefix='tradutor-')
    file_path = os.path.join(base_dir, original_name)
    uploaded_file.save(file_path)

    try:
        pages = translate_document_pages(file_path, file_ext, source_lang, target_lang)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    finally:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        try:
            os.rmdir(base_dir)
        except OSError:
            pass

    return jsonify({
        'filename': original_name,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'pages': pages,
    })


@app.route('/<path:filename>')
def serve_static(filename):
    if filename.endswith('/'):
        filename = filename[:-1]
    return send_from_directory('.', filename)


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5001'))
    app.run(host=host, port=port, debug=False)
