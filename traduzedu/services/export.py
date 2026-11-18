"""PDF simples com o texto traduzido (seção 7.6 da documentação).

O download principal é o PDF com o mesmo layout (services/pdf_layout.py).
Este exportador recebe as páginas já validadas por
models.document.validate_export_pages e devolve os bytes do PDF.
"""
import io
from dataclasses import dataclass
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph as PDFParagraph,
    SimpleDocTemplate,
    Spacer,
    Table as PDFTable,
    TableStyle,
)

from ..models.document import group_blocks


@dataclass(frozen=True)
class ExportedFile:
    content: bytes
    mimetype: str
    extension: str


def _pdf_paragraph(text, style):
    return PDFParagraph(escape(text).replace('\n', '<br/>'), style)


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TranslatedPageTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#263452'),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='TranslatedHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#34415b'),
        spaceBefore=8,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name='TranslatedBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=8,
        splitLongWords=True,
    ))
    return styles


def export_pdf(pages):
    styles = _pdf_styles()
    story = []
    for page_index, page in enumerate(pages):
        if page_index:
            story.append(PageBreak())
        if page['page_title']:
            story.append(_pdf_paragraph(page['page_title'], styles['TranslatedPageTitle']))
        if page['title']:
            story.append(_pdf_paragraph(page['title'], styles['TranslatedHeading']))
        if page['subtitle']:
            story.append(_pdf_paragraph(page['subtitle'], styles['Italic']))

        for kind, item in group_blocks(page['blocks']):
            if kind == 'table':
                rows = [
                    [_pdf_paragraph(cell, styles['TranslatedBody']) for cell in row]
                    for row in item
                ]
                column_count = max(len(row) for row in rows)
                table = PDFTable(
                    [row + [''] * (column_count - len(row)) for row in rows],
                    colWidths=None,
                    repeatRows=0,
                )
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dce2ed')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.extend((table, Spacer(1, 8)))
                continue

            if not item['text']:
                continue
            if item['type'] == 'heading':
                story.append(_pdf_paragraph(item['text'], styles['TranslatedHeading']))
            elif item['type'] == 'list-item':
                story.append(_pdf_paragraph(f'• {item["text"]}', styles['TranslatedBody']))
            else:
                story.append(_pdf_paragraph(item['text'], styles['TranslatedBody']))

    output = io.BytesIO()
    SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title='Material traduzido',
        author='Tradutor de Aulas',
    ).build(story)
    return output.getvalue()


def export_document(pages, format_name):
    """Ponto de entrada usado pelo controller de download."""
    if format_name == 'pdf':
        return ExportedFile(export_pdf(pages), 'application/pdf', 'pdf')
    raise ValueError('Formato de download inválido.')
