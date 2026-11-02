import os
import re
import tempfile
import zipfile
from pathlib import Path

import requests
from docx import Document
from flask import Flask, jsonify, request, send_from_directory
from pptx import Presentation
from pypdf import PdfReader
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES + 64 * 1024
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
            translated = data.get('translatedText')
            if not translated and isinstance(data.get('translations'), list):
                translated = next(
                    (
                        item.get('translatedText')
                        for item in data['translations']
                        if isinstance(item, dict) and item.get('translatedText')
                    ),
                    None,
                )
            if not isinstance(translated, str) or not translated.strip():
                raise RuntimeError('O serviço de tradução retornou uma resposta vazia.')
            return translated.strip()
        except RuntimeError:
            raise
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise RuntimeError(f'Não foi possível conectar ao serviço de tradução. Verifique se o LibreTranslate está em execução. Detalhe: {last_error}')
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
            style_name = (paragraph.style.name or '').lower()
            if style_name.startswith(('heading', 'title', 'subtitle')):
                block_type = 'heading'
            elif 'list' in style_name:
                block_type = 'list-item'
            else:
                block_type = 'paragraph'
            blocks.append({'type': block_type, 'text': text})
    for table in document.tables:
        for row in table.rows:
            row_text = ' | '.join(clean_text(cell.text) for cell in row.cells if clean_text(cell.text))
            if row_text:
                blocks.append({'type': 'list-item', 'text': row_text})

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
        for shape in slide.shapes:
            if not hasattr(shape, 'has_text_frame') or not shape.has_text_frame:
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


def extract_document_pages(file_path: str, extension: str):
    ext = extension.lower()
    if ext == '.pdf':
        return extract_pdf_document(file_path)
    if ext == '.docx':
        return extract_word_document(file_path)
    if ext == '.pptx':
        return extract_powerpoint_document(file_path)
    raise ValueError('Formato não suportado.')


def translate_document_pages(file_path: str, extension: str, source_lang: str, target_lang: str, pages=None):
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

    for page in pages:
        translated = translate_blocks(page.get('blocks', []), source_lang, target_lang)
        translated_pages.append({
            'page_title': page.get('page_title', 'Página 1'),
            'title': '',
            'subtitle': '',
            'blocks': translated,
        })

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


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({
        'error': 'O arquivo excede o limite de 10 MB. Escolha um arquivo menor.'
    }), 413


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
    base_dir = tempfile.mkdtemp(prefix='tradutor-')
    file_path = os.path.join(base_dir, original_name)
    uploaded_file.save(file_path)

    try:
        if file_ext in {'.docx', '.pptx'} and not zipfile.is_zipfile(file_path):
            return jsonify({'error': 'O arquivo não é um documento válido para o formato selecionado.'}), 400
        try:
            pages = extract_document_pages(file_path, file_ext)
        except Exception as exc:
            app.logger.exception('Could not read uploaded %s file', file_ext)
            return jsonify({'error': 'Não foi possível ler o arquivo. Verifique se está íntegro e não protegido por senha.'}), 400
        if not any(
            clean_text(block.get('text', ''))
            for page in pages
            for block in page.get('blocks', [])
        ):
            return jsonify({'error': 'Nenhum texto foi encontrado no documento. PDFs digitalizados como imagem não podem ser lidos.'}), 422
        try:
            translated_pages = translate_document_pages(
                file_path, file_ext, source_lang, target_lang, pages=pages
            )
        except Exception as exc:
            app.logger.exception('Could not translate uploaded %s file', file_ext)
            if isinstance(exc, ValueError):
                return jsonify({'error': str(exc)}), 422
            return jsonify({'error': str(exc)}), 503
    finally:
        uploaded_file.close()
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
        'pages': translated_pages,
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
