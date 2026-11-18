"""Configurações centrais da aplicação TraduzEdu.

Todos os limites e valores lidos do ambiente ficam aqui, para que models,
services e controllers usem a mesma fonte de verdade.
"""
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
VIEWS_DIR = PACKAGE_DIR / 'views'
TEMPLATES_DIR = VIEWS_DIR / 'templates'
STATIC_DIR = VIEWS_DIR / 'static'
EXAMPLES_DIR = STATIC_DIR / 'exemplos'
DATA_DIR = PACKAGE_DIR / 'data'
DEMO_RESULTS_PATH = DATA_DIR / 'demo_results.json'
DEMO_TRANSLATED_PDF_STATIC = 'exemplos/sample-traduzido.pdf'
DEMO_TRANSLATED_PDF_PATH = STATIC_DIR / DEMO_TRANSLATED_PDF_STATIC


def _translation_total_timeout():
    try:
        value = int(os.getenv('TRANSLATION_TOTAL_TIMEOUT_SECONDS', '300'))
    except ValueError:
        LOGGER.warning('Invalid TRANSLATION_TOTAL_TIMEOUT_SECONDS; using 300 seconds.')
        value = 300
    return min(max(value, 30), 900)


# Envio de arquivos
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Tradução
MAX_TRANSLATION_SECONDS = _translation_total_timeout()
MAX_TRANSLATION_BATCH_SIZE = 20
MAX_CHUNK_CHARS = 1400

# OCR
MAX_OCR_PAGES = 100
MAX_OCR_SECONDS = 120

# Exportação (download)
EXPORT_FORMATS = {'txt', 'docx', 'pptx', 'pdf'}
MAX_EXPORT_PAGES = 300
MAX_EXPORT_BLOCKS = 5000
MAX_EXPORT_TEXT_BYTES = MAX_UPLOAD_BYTES

# Demonstração offline
DEMO_FORMATS = {'pdf'}


class Config:
    """Configuração carregada pelo Flask em create_app()."""

    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 64 * 1024
    JSON_AS_ASCII = False
