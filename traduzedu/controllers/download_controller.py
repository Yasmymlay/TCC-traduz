"""Controller de download do material traduzido (seção 7.6 da documentação)."""
import io
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..config import EXPORT_FORMATS
from ..models.document import validate_export_pages
from ..services.export import export_document
from ..services.result_store import TRANSLATED_FILES

download_bp = Blueprint('download', __name__, url_prefix='/api')


@download_bp.route('/download/<format_name>', methods=['POST'])
def download_translation(format_name):
    format_name = format_name.lower()
    if format_name not in EXPORT_FORMATS:
        return jsonify({'error': 'Formato de download inválido.'}), 404
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Os dados da tradução estão ausentes ou inválidos.'}), 400
    try:
        pages = validate_export_pages(payload.get('pages'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    original_name = payload.get('filename', 'material')
    if not isinstance(original_name, str):
        return jsonify({'error': 'O nome do documento é inválido.'}), 400
    base_name = secure_filename(Path(original_name).stem)[:100] or 'material'

    try:
        exported = export_document(pages, format_name)
    except Exception as exc:
        current_app.logger.exception('Could not create %s translation download.', format_name)
        return jsonify({
            'error': f'Não foi possível gerar o arquivo {format_name.upper()}: {exc}'
        }), 500

    return send_file(
        io.BytesIO(exported.content),
        mimetype=exported.mimetype,
        as_attachment=True,
        download_name=f'{base_name}-traduzido.{exported.extension}',
    )


@download_bp.route('/download/translated/<file_id>')
def download_translated_pdf(file_id):
    """Baixa o PDF traduzido com o mesmo layout do original."""
    stored = TRANSLATED_FILES.get(file_id)
    if stored is None:
        return jsonify({
            'error': 'O PDF traduzido não está mais disponível. Traduza o arquivo novamente.'
        }), 404
    return send_file(
        io.BytesIO(stored.content),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=stored.filename,
    )
