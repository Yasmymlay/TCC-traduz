"""Model de idiomas suportados pela plataforma."""

SUPPORTED_LANGS = {'pt', 'en', 'es'}
LANGUAGE_NAMES = {'pt': 'Português', 'en': 'Inglês', 'es': 'Espanhol'}
OCR_LANGUAGES = {'pt': 'por', 'en': 'eng', 'es': 'spa'}

_ALIASES = {
    'pt': 'pt',
    'pt-br': 'pt',
    'en': 'en',
    'en-us': 'en',
    'es': 'es',
    'es-es': 'es',
}


def normalize_lang(code: str) -> str:
    """Converte códigos como 'pt-BR' ou 'en_US' para 'pt', 'en' ou 'es'."""
    if not code:
        return 'pt'
    normalized = code.strip().lower().replace('_', '-')
    return _ALIASES.get(normalized, normalized)


def validated_language_pair(source_lang, target_lang):
    """Retorna (origem, destino) normalizados ou lança ValueError."""
    source = normalize_lang(source_lang or '')
    target = normalize_lang(target_lang or '')
    if source not in SUPPORTED_LANGS or target not in SUPPORTED_LANGS or source == target:
        raise ValueError('Selecione dois idiomas diferentes entre português, inglês e espanhol.')
    return source, target
