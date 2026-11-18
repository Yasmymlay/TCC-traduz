"""Geração dos arquivos para download (seção 7.6 da documentação).

Cada exportador recebe as páginas já validadas por
models.document.validate_export_pages e devolve os bytes do arquivo.
"""
import io
import logging
from dataclasses import dataclass
from xml.sax.saxutils import escape

from docx import Document
from pptx import Presentation
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

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportedFile:
    content: bytes
    mimetype: str
    extension: str


def export_text(pages):
    sections = []
    for page in pages:
        parts = [
            page['page_title'],
            page['title'],
            page['subtitle'],
            *(block['text'] for block in page['blocks']),
        ]
        sections.append('\n\n'.join(part for part in parts if part))
    return '\n\n--------------------\n\n'.join(sections)


def export_docx(pages):
    document = Document()
    document.core_properties.title = 'Material traduzido'
    for page_index, page in enumerate(pages):
        if page_index:
            document.add_page_break()
        if page['page_title']:
            document.add_heading(page['page_title'], level=1)
        if page['title']:
            document.add_heading(page['title'], level=2)
        if page['subtitle']:
            document.add_paragraph(page['subtitle'], style='Subtitle')

        for kind, item in group_blocks(page['blocks']):
            if kind == 'table':
                column_count = max(len(row) for row in item)
                table = document.add_table(rows=len(item), cols=column_count)
                try:
                    table.style = 'Light Shading Accent 1'
                except KeyError:
                    LOGGER.info('The requested DOCX table style is not available.')
                for row_index, row in enumerate(item):
                    for column_index in range(column_count):
                        table.cell(row_index, column_index).text = (
                            row[column_index] if column_index < len(row) else ''
                        )
                continue

            if not item['text']:
                continue
            if item['type'] == 'heading':
                document.add_heading(item['text'], level=2)
            elif item['type'] == 'list-item':
                document.add_paragraph(item['text'], style='List Bullet')
            else:
                document.add_paragraph(item['text'])

    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def export_pptx(pages):
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Inches, Pt

    presentation = Presentation()
    blank_layout = presentation.slide_layouts[6]
    content_width = presentation.slide_width - Inches(1.4)
    max_cursor = 7.1

    def create_slide(page_title, continuation=False):
        slide = presentation.slides.add_slide(blank_layout)
        title_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(0.35), content_width, Inches(0.75)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        title_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.text = (
            f'{page_title} (continuação)' if continuation else page_title
        ) or 'Material traduzido'
        title_paragraph.font.size = Pt(24)
        title_paragraph.font.bold = True
        return slide

    for page in pages:
        page_title = page['page_title'] or page['title'] or 'Material traduzido'
        slide = create_slide(page_title)
        cursor = 1.35

        if page['title'] and page['title'] != page_title:
            title = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(0.55)
            ).text_frame.paragraphs[0]
            title.text = page['title']
            title.font.size = Pt(20)
            title.font.bold = True
            cursor += 0.6

        if page['subtitle']:
            subtitle = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(0.45)
            ).text_frame.paragraphs[0]
            subtitle.text = page['subtitle']
            subtitle.font.size = Pt(14)
            subtitle.font.italic = True
            cursor += 0.5

        for kind, item in group_blocks(page['blocks']):
            if kind == 'table':
                column_count = max(len(row) for row in item)
                for first_row in range(0, len(item), 8):
                    row_batch = item[first_row:first_row + 8]
                    table_height = max(0.4, 0.38 * len(row_batch))
                    if cursor + table_height > max_cursor:
                        slide = create_slide(page_title, continuation=True)
                        cursor = 1.2
                    table = slide.shapes.add_table(
                        len(row_batch),
                        column_count,
                        Inches(0.8),
                        Inches(cursor),
                        content_width,
                        Inches(table_height),
                    ).table
                    for row_index, row in enumerate(row_batch):
                        for column_index in range(column_count):
                            table.cell(row_index, column_index).text = (
                                row[column_index] if column_index < len(row) else ''
                            )
                    cursor += table_height + 0.15
                continue

            text = item['text']
            if not text:
                continue
            line_count = max(1, (len(text) + 99) // 100)
            height = min(2.4, max(0.36, 0.28 * line_count + 0.12))
            if cursor + height > max_cursor:
                slide = create_slide(page_title, continuation=True)
                cursor = 1.2
            text_frame = slide.shapes.add_textbox(
                Inches(0.8), Inches(cursor), content_width, Inches(height)
            ).text_frame
            text_frame.word_wrap = True
            text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            paragraph = text_frame.paragraphs[0]
            paragraph.text = f'• {text}' if item['type'] == 'list-item' else text
            paragraph.font.size = Pt(18 if item['type'] == 'heading' else 14)
            paragraph.font.bold = item['type'] == 'heading'
            cursor += height + 0.1

    output = io.BytesIO()
    presentation.save(output)
    return output.getvalue()


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
    if format_name == 'txt':
        return ExportedFile(
            ('﻿' + export_text(pages)).encode('utf-8'),
            'text/plain; charset=utf-8',
            'txt',
        )
    if format_name == 'docx':
        return ExportedFile(
            export_docx(pages),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'docx',
        )
    if format_name == 'pptx':
        return ExportedFile(
            export_pptx(pages),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'pptx',
        )
    if format_name == 'pdf':
        return ExportedFile(export_pdf(pages), 'application/pdf', 'pdf')
    raise ValueError('Formato de download inválido.')
