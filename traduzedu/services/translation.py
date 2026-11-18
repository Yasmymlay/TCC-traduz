"""Tradução do documento extraído (etapa 4.5 da documentação).

Os blocos são divididos em trechos, enviados em lotes ao motor de tradução e
remontados na mesma ordem e com o mesmo tipo, preservando a estrutura.
"""
import time
from threading import Lock

from ..config import MAX_TRANSLATION_BATCH_SIZE, MAX_TRANSLATION_SECONDS
from ..models.document import has_text, make_page
from ..models.text import clean_text, split_text_chunks
from .translation_engine import TranslationError, translate_texts


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


def translate_document_pages(pages, source_lang, target_lang, deadline=None):
    """Traduz todas as páginas mantendo a separação por página/slide."""
    if not has_text(pages):
        raise ValueError('Nenhum texto foi encontrado no documento para traduzir.')

    deadline = deadline or (time.monotonic() + MAX_TRANSLATION_SECONDS)
    return [
        make_page(
            page.get('page_title', 'Página 1'),
            translate_blocks(page.get('blocks', []), source_lang, target_lang, deadline=deadline),
        )
        for page in pages
    ]


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
