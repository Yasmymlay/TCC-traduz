"""Controller dos recursos auxiliares: OCR e modelos locais do Argos."""
from flask import Blueprint, current_app, jsonify, request

from ..models.language import SUPPORTED_LANGS, normalize_lang, validated_language_pair
from ..services import ocr, translation_engine

resources_bp = Blueprint('resources', __name__, url_prefix='/api')


def _pair_from(values):
    return validated_language_pair(values.get('source'), values.get('target'))


@resources_bp.route('/ocr/status')
def ocr_status_api():
    source_lang = normalize_lang(request.args.get('source_lang', 'pt'))
    if source_lang not in SUPPORTED_LANGS:
        return jsonify({'error': 'Idioma de OCR inválido. Use pt, en ou es.'}), 400
    return jsonify(ocr.ocr_status(source_lang))


@resources_bp.route('/argos/models')
def argos_models():
    try:
        source, target = _pair_from(request.args)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(translation_engine.argos_model_status(source, target))
    except Exception as exc:
        current_app.logger.exception('Could not inspect Argos language models.')
        return jsonify({'error': f'Não foi possível verificar os modelos Argos: {exc}'}), 503


@resources_bp.route('/argos/catalog', methods=['POST'])
def check_argos_catalog():
    try:
        source, target = _pair_from(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(translation_engine.refresh_argos_catalog(source, target))
    except Exception as exc:
        current_app.logger.exception('Could not update the Argos model catalog.')
        return jsonify({
            'error': (
                'Não foi possível consultar o catálogo Argos. Verifique a conexão '
                f'com a internet. Detalhe: {exc}'
            )
        }), 503


@resources_bp.route('/argos/models/install', methods=['POST'])
def install_argos_model():
    try:
        source, target = _pair_from(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        return jsonify(translation_engine.install_argos_model(source, target))
    except LookupError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception('Could not install requested Argos model.')
        return jsonify({'error': f'Não foi possível instalar o modelo Argos: {exc}'}), 503
