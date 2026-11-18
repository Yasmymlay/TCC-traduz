"""Regras de limpeza e divisão de texto usadas antes da tradução."""
import re

from ..config import MAX_CHUNK_CHARS


def clean_text(text: str) -> str:
    """Normaliza quebras de linha e espaços, preservando parágrafos."""
    if text is None:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _split_oversized(value, max_chars):
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


def split_text_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS):
    """Divide o texto em trechos que respeitam o limite do serviço de tradução.

    A divisão tenta, nesta ordem: parágrafos, frases e, por último, espaços.
    """
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
            continue

        if current:
            chunks.append(current)
        current = ''
        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        for sentence in re.split(r'(?<=[.!?])\s+', paragraph):
            for piece in _split_oversized(sentence, max_chars):
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
