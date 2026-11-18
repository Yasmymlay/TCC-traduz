"""Controller do fluxo principal: envio do material e tradução.

Fluxo (seções 7.2 a 7.5 da documentação):
envio do arquivo -> seleção dos idiomas -> extração -> tradução -> resultado.
"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .. import config
from ..models.document import has_text
from ..models.language import SUPPORTED_LANGS, normalize_lang
from ..services import extraction, translation, translation_engine
from ..services.ocr import OCRProcessingError

translation_bp = Blueprint('translation', __name__, url_prefix='/api')


@translation_bp.route('/health')
def health():
    endpoints = translation_engine.configured_endpoints()
    return jsonify({
        'status': 'ok',
        'libretranslate_url': endpoints[0] if endpoints else None,
        'configured_endpoints': endpoints,
        'translation_providers': translation_engine.configured_provider_names(),
    })


@translation_bp.route('/translation/status')
def translation_status():
    statuses = translation_engine.provider_status()
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
        'demo_available': config.DEMO_RESULTS_PATH.is_file(),
        'max_translation_seconds': config.MAX_TRANSLATION_SECONDS,
    })


@translation_bp.route('/demo/<format_name>')
def demo_result(format_name):
    format_name = format_name.lower()
    if format_name not in config.DEMO_FORMATS:
        return jsonify({'error': 'Formato de demonstração inválido.'}), 404
    try:
        with config.DEMO_RESULTS_PATH.open(encoding='utf-8') as demo_file:
            results = json.load(demo_file)
    except (OSError, json.JSONDecodeError):
        current_app.logger.exception('Could not load prepared translation demonstration.')
        return jsonify({'error': 'A demonstração não está disponível.'}), 503
    if format_name not in results:
        return jsonify({'error': 'Demonstração não encontrada para este formato.'}), 404
    return jsonify({'demo': True, **results[format_name]})


def _uploaded_file_size(uploaded_file):
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    return size


def _file_digest(uploaded_file):
    digest = hashlib.sha256()
    while True:
        chunk = uploaded_file.stream.read(64 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    uploaded_file.stream.seek(0)
    return digest.hexdigest()


def _validate_upload():
    """Valida o pedido e devolve (arquivo, extensão, origem, destino) ou uma resposta de erro."""
    if 'file' not in request.files:
        return None, (jsonify({'error': 'Arquivo não enviado.'}), 400)

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return None, (jsonify({'error': 'Selecione um arquivo antes de traduzir.'}), 400)

    file_ext = Path(uploaded_file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_UPLOAD_EXTENSIONS:
        return None, (jsonify({'error': 'Formato não permitido. Envie somente um arquivo PDF.'}), 400)

    file_size = _uploaded_file_size(uploaded_file)
    if file_size == 0:
        return None, (jsonify({'error': 'O arquivo está vazio. Selecione um documento com conteúdo.'}), 400)
    if file_size > config.MAX_UPLOAD_BYTES:
        return None, (jsonify({'error': 'O arquivo excede o limite de 10 MB. Escolha um arquivo menor.'}), 413)

    source_lang = normalize_lang(request.form.get('source_lang', 'pt'))
    target_lang = normalize_lang(request.form.get('target_lang', 'en'))
    if source_lang not in SUPPORTED_LANGS or target_lang not in SUPPORTED_LANGS:
        return None, (jsonify({'error': 'Idioma inválido. Use pt, en ou es.'}), 400)
    if source_lang == target_lang:
        return None, (jsonify({'error': 'Selecione idiomas diferentes para a tradução.'}), 400)

    return (uploaded_file, file_ext, source_lang, target_lang), None


def _extract_and_translate(file_path, file_ext, source_lang, target_lang):
    """Executa extração e tradução, convertendo erros em respostas HTTP."""
    logger = current_app.logger
    try:
        pages = extraction.extract_document_pages(file_path, file_ext, source_lang=source_lang)
    except OCRProcessingError as exc:
        logger.info('OCR could not read uploaded PDF: %s', exc)
        return None, (jsonify({'error': str(exc)}), 422)
    except Exception:
        logger.exception('Could not read uploaded %s file', file_ext)
        return None, (jsonify({
            'error': (
                'Não foi possível ler o PDF. Verifique se o arquivo está íntegro, '
                'não protegido por senha e se é um PDF válido.'
            )
        }), 400)

    if not has_text(pages):
        return None, (jsonify({
            'error': (
                'Nenhum texto legível foi encontrado. Em PDFs digitalizados, '
                'verifique se o Tesseract OCR e o pacote do idioma original estão instalados.'
            )
        }), 422)

    try:
        translated_pages = translation.translate_document_pages(
            pages,
            source_lang,
            target_lang,
            deadline=time.monotonic() + config.MAX_TRANSLATION_SECONDS,
        )
    except translation_engine.UnsupportedLanguagePair as exc:
        logger.info('No configured provider supports requested pair: %s', exc)
        return None, (jsonify({'error': str(exc)}), 422)
    except translation_engine.TranslationError as exc:
        logger.exception('Translation failed for uploaded %s file', file_ext)
        status_code = 504 if 'tempo máximo' in str(exc).lower() else 503
        return None, (jsonify({'error': str(exc)}), status_code)
    except ValueError as exc:
        logger.exception('Could not translate uploaded %s file', file_ext)
        return None, (jsonify({'error': str(exc)}), 422)
    except Exception as exc:
        logger.exception('Could not translate uploaded %s file', file_ext)
        return None, (jsonify({'error': str(exc)}), 503)

    warning = extraction.skipped_pages_warning(pages)
    return (translated_pages, [warning] if warning else []), None


@translation_bp.route('/translate', methods=['POST'])
def translate_document():
    upload, error = _validate_upload()
    if error:
        return error
    uploaded_file, file_ext, source_lang, target_lang = upload

    original_name = secure_filename(uploaded_file.filename)
    if not original_name:
        return jsonify({'error': 'O nome do arquivo é inválido.'}), 400

    translation_key = f'{source_lang}:{target_lang}:{_file_digest(uploaded_file)}'
    if not translation.ACTIVE_TRANSLATIONS.try_acquire(translation_key):
        uploaded_file.close()
        return jsonify({
            'error': 'Este mesmo documento já está sendo traduzido. Aguarde a tentativa atual terminar.'
        }), 409

    try:
        with tempfile.TemporaryDirectory(prefix='tradutor-') as base_dir:
            file_path = os.path.join(base_dir, original_name)
            uploaded_file.save(file_path)
            result, error = _extract_and_translate(
                file_path, file_ext, source_lang, target_lang
            )
    finally:
        uploaded_file.close()
        translation.ACTIVE_TRANSLATIONS.release(translation_key)

    if error:
        return error
    translated_pages, warnings = result
    return jsonify({
        'filename': original_name,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'pages': translated_pages,
        'warnings': warnings,
    })
