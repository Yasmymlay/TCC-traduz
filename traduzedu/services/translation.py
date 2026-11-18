"""Tradução do documento extraído (etapa 4.5 da documentação).

Cada trecho de texto do PDF é traduzido mantendo a ordem. O resultado serve a
duas coisas: a visualização na tela e o PDF traduzido com o layout original.
"""
import time
from dataclasses import dataclass
from threading import Lock

from ..config import MAX_TRANSLATION_BATCH_SIZE, MAX_TRANSLATION_SECONDS
from ..models.document import make_page
from ..models.text import clean_text, split_text_chunks
from . import pdf_layout
from .extraction import skipped_pages_warning
from .translation_engine import TranslationError, translate_texts


@dataclass
class TranslatedDocument:
    pages: list
    pdf_bytes: bytes
    warnings: list


def translate_texts_in_order(texts, source_lang, target_lang, deadline=None):
    """Traduz uma lista de textos e devolve uma tradução para cada um, na mesma ordem.

    Textos longos são divididos em trechos aceitos pelo serviço de tradução e
    juntados de novo; os trechos são enviados em lotes.
    """
    pieces = []
    owners = []
    for index, text in enumerate(texts):
        for chunk in split_text_chunks(clean_text(text)):
            pieces.append(chunk)
            owners.append(index)

    translated_pieces = []
    for batch_start in range(0, len(pieces), MAX_TRANSLATION_BATCH_SIZE):
        if deadline is not None and time.monotonic() >= deadline:
            raise TranslationError('O tempo máximo desta tradução foi excedido.')
        batch = pieces[batch_start:batch_start + MAX_TRANSLATION_BATCH_SIZE]
        result = translate_texts(batch, source_lang, target_lang, deadline=deadline)
        if len(result) != len(batch):
            raise TranslationError('O mecanismo retornou uma quantidade inválida de traduções.')
        translated_pieces.extend(result)

    joined = [[] for _ in texts]
    for owner, piece in zip(owners, translated_pieces):
        joined[owner].append(piece)
    return [' '.join(parts) for parts in joined]


def translate_layout_document(layout, source_lang, target_lang, deadline=None):
    """Traduz o PDF lido por pdf_layout.read_document.

    Devolve as páginas para a visualização, o PDF traduzido com o layout
    original e os avisos (por exemplo, páginas que ficaram sem tradução).
    """
    deadline = deadline or (time.monotonic() + MAX_TRANSLATION_SECONDS)

    texts = []
    for page in layout.pages:
        texts.extend(unit.text for unit in page.units)
        texts.extend(block['text'] for block in page.fallback_blocks)
    translated = iter(translate_texts_in_order(texts, source_lang, target_lang, deadline))

    preview_pages = []
    unit_translations = []
    skipped = []
    for number, page in enumerate(layout.pages, start=1):
        page_units = [next(translated) for _ in page.units]
        page_fallback = [
            {'type': block['type'], 'text': next(translated)}
            for block in page.fallback_blocks
        ]
        unit_translations.append(page_units)
        blocks = pdf_layout.preview_blocks(page.units, page_units) + page_fallback
        preview_pages.append(make_page(f'Página {number}', [b for b in blocks if b['text']]))
        if page.ocr_error:
            skipped.append({'page_title': f'Página {number}', 'ocr_error': page.ocr_error})

    warning = skipped_pages_warning(skipped)
    return TranslatedDocument(
        pages=preview_pages,
        pdf_bytes=pdf_layout.render_translated_pdf(layout, unit_translations),
        warnings=[warning] if warning else [],
    )


class ActiveTranslations:
    """Impede que o mesmo documento seja traduzido duas vezes ao mesmo tempo."""

    def __init__(self):
        self._keys = set()
        self._lock = Lock()

    def try_acquire(self, key):
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            return True

    def release(self, key):
        with self._lock:
            self._keys.discard(key)


ACTIVE_TRANSLATIONS = ActiveTranslations()
