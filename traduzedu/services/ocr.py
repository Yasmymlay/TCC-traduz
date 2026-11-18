"""Reconhecimento de texto (OCR) em PDFs digitalizados, via Tesseract."""
import io
import os
from pathlib import Path

from ..models.language import OCR_LANGUAGES
from ..models.text import clean_text

DEFAULT_WINDOWS_TESSERACT = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
MAX_RENDER_PIXELS = 25_000_000
RENDER_SCALE = 2


class OCRProcessingError(ValueError):
    pass


def ocr_status(source_lang=None):
    """Informa se o Tesseract e o pacote do idioma de origem estão instalados."""
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
    elif DEFAULT_WINDOWS_TESSERACT.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(DEFAULT_WINDOWS_TESSERACT)

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


def check_ocr_ready(source_lang):
    status = ocr_status(source_lang)
    if not status['available'] or status.get('missing_languages'):
        raise OCRProcessingError(status.get('error', 'O OCR não está disponível.'))


def recognize_pdf_page(pdf_page, source_lang):
    """Renderiza uma página PyMuPDF como imagem e extrai o texto com OCR."""
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OCRProcessingError(
            'O OCR requer PyMuPDF, pytesseract e Pillow. Instale as dependências do projeto.'
        ) from exc

    page_width, page_height = pdf_page.rect.width, pdf_page.rect.height
    if page_width * page_height * RENDER_SCALE * RENDER_SCALE > MAX_RENDER_PIXELS:
        raise OCRProcessingError(
            'Uma página deste PDF é grande demais para o reconhecimento OCR.'
        )
    try:
        pixmap = pdf_page.get_pixmap(
            matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
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
