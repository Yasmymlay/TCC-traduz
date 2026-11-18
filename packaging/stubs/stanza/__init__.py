"""Substituto mínimo do stanza para a versão instalável.

O argostranslate importa o stanza ao carregar, e o stanza traz o PyTorch
(mais de 1 GB). O Tradutor de Aulas não usa o stanza: quando ele falha, as
frases são separadas pela pontuação (translation_engine._OfflineStanzaSentencizer).
Este módulo permite o import e falha ao ser usado, o que ativa essa alternativa.
"""


class DownloadMethod:
    NONE = None
    REUSE_RESOURCES = None


class Pipeline:
    def __init__(self, *args, **kwargs):
        raise RuntimeError('stanza não está incluído na versão instalável.')
