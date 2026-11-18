"""Model do documento traduzido.

Um documento é uma lista de páginas (ou slides). Cada página tem:

    {
        'page_title': 'Página 1',   # ou 'Slide 1'
        'title': '',
        'subtitle': '',
        'blocks': [{'type': 'paragraph', 'text': '...'}, ...],
    }

Os tipos de bloco preservam a organização do arquivo original (títulos,
parágrafos, listas e linhas de tabela), como pede a seção 3.3 da documentação.
"""
from ..config import MAX_EXPORT_BLOCKS, MAX_EXPORT_PAGES, MAX_EXPORT_TEXT_BYTES
from .text import clean_text

BLOCK_TYPES = {'heading', 'list-item', 'paragraph', 'table-row'}
TABLE_CELL_SEPARATOR = ' | '


def make_block(block_type, text):
    return {'type': block_type, 'text': text}


def make_page(page_title, blocks, title='', subtitle=''):
    return {
        'page_title': page_title,
        'title': title,
        'subtitle': subtitle,
        'blocks': blocks,
    }


def has_text(pages):
    """Indica se alguma página tem texto a traduzir."""
    return any(
        clean_text(block.get('text', ''))
        for page in pages
        for block in page.get('blocks', [])
    )


def group_blocks(blocks):
    """Agrupa linhas de tabela consecutivas.

    Gera tuplas ('table', [[célula, ...], ...]) ou ('block', bloco). Usado pelos
    exportadores para montar tabelas reais nos arquivos baixados.
    """
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block['type'] == 'table-row':
            rows = []
            while index < len(blocks) and blocks[index]['type'] == 'table-row':
                rows.append(blocks[index]['text'].split(TABLE_CELL_SEPARATOR))
                index += 1
            yield 'table', rows
            continue
        yield 'block', block
        index += 1


def validate_export_pages(raw_pages):
    """Valida e normaliza as páginas recebidas do navegador para download."""
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ValueError('Nenhuma página traduzida foi informada para o download.')
    if len(raw_pages) > MAX_EXPORT_PAGES:
        raise ValueError(f'O documento excede o limite de {MAX_EXPORT_PAGES} páginas.')

    pages = []
    total_bytes = 0
    block_count = 0
    for page_number, page in enumerate(raw_pages, start=1):
        if not isinstance(page, dict) or not isinstance(page.get('blocks'), list):
            raise ValueError(f'A estrutura da página {page_number} é inválida.')
        normalized_page = {}
        for field in ('page_title', 'title', 'subtitle'):
            value = page.get(field, '')
            if not isinstance(value, str):
                raise ValueError(f'O campo {field} da página {page_number} é inválido.')
            normalized_page[field] = clean_text(value)
            total_bytes += len(normalized_page[field].encode('utf-8'))

        normalized_page['blocks'] = []
        block_count += len(page['blocks'])
        if block_count > MAX_EXPORT_BLOCKS:
            raise ValueError('O documento contém blocos de texto demais para exportar.')
        for block in page['blocks']:
            if not isinstance(block, dict):
                raise ValueError(f'Um bloco da página {page_number} é inválido.')
            block_type = block.get('type', 'paragraph')
            text = block.get('text', '')
            if (
                not isinstance(block_type, str)
                or block_type not in BLOCK_TYPES
                or not isinstance(text, str)
            ):
                raise ValueError(f'Um bloco da página {page_number} é inválido.')
            text = clean_text(text)
            total_bytes += len(text.encode('utf-8'))
            normalized_page['blocks'].append(make_block(block_type, text))

        pages.append(normalized_page)

    if total_bytes > MAX_EXPORT_TEXT_BYTES:
        raise ValueError('O conteúdo traduzido excede o limite de 10 MB para exportação.')
    if not any(block['text'] for page in pages for block in page['blocks']):
        raise ValueError('Não há conteúdo traduzido para baixar.')
    return pages
