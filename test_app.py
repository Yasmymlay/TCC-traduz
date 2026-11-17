import io
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfReader
import pymupdf

import app
from translation_engine import ArgosProvider, TranslationEngine


FIXTURES = Path(__file__).parent / 'tmp-docs'


class TranslationApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def upload(self, name, content, source='pt', target='en'):
        response = self.client.post(
            '/api/translate',
            data={
                'file': (io.BytesIO(content), name),
                'source_lang': source,
                'target_lang': target,
            },
            content_type='multipart/form-data',
        )
        self.addCleanup(response.close)
        return response

    def test_only_public_site_assets_and_demo_files_are_served(self):
        for path in ('/style.css', '/script.js', '/tmp-docs/sample.pdf',
                     '/tmp-docs/sample.docx', '/tmp-docs/sample.pptx'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.addCleanup(response.close)
                self.assertEqual(response.status_code, 200)

        for path in (
            '/app.py',
            '/README.md',
            '/translation_engine.py',
            '/requirements.txt',
            '/.git/config',
            '/tmp-docs/../app.py',
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_downloads_open_and_preserve_translated_document_structure(self):
        pages = [
            {
                'page_title': 'Página 1',
                'title': 'Introduction',
                'subtitle': 'Study material',
                'blocks': [
                    {'type': 'heading', 'text': 'Important terms'},
                    {'type': 'paragraph', 'text': 'A paragraph with accented text: tradução.'},
                    {'type': 'list-item', 'text': 'First item'},
                    {'type': 'table-row', 'text': 'Term | Meaning'},
                    {'type': 'table-row', 'text': 'Cell | Basic unit'},
                ],
            },
            {
                'page_title': 'Página 2',
                'title': 'Conclusion',
                'subtitle': '',
                'blocks': [{'type': 'paragraph', 'text': 'Second page content.'}],
            },
        ]
        payload = {'filename': 'sample.docx', 'pages': pages}

        docx_response = self.client.post('/api/download/docx', json=payload)
        self.assertEqual(docx_response.status_code, 200, docx_response.get_json())
        self.assertIn('sample-traduzido.docx', docx_response.headers['Content-Disposition'])
        document = Document(io.BytesIO(docx_response.data))
        paragraph_text = '\n'.join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn('Important terms', paragraph_text)
        self.assertIn('First item', paragraph_text)
        self.assertIn('Conclusion', paragraph_text)
        self.assertEqual(
            [[cell.text for cell in row.cells] for row in document.tables[0].rows],
            [['Term', 'Meaning'], ['Cell', 'Basic unit']],
        )

        pptx_response = self.client.post('/api/download/pptx', json=payload)
        self.assertEqual(pptx_response.status_code, 200, pptx_response.get_json())
        presentation = Presentation(io.BytesIO(pptx_response.data))
        self.assertEqual(len(presentation.slides), 2)
        first_slide = presentation.slides[0]
        self.assertTrue(any(
            shape.has_text_frame and shape.text == 'Introduction'
            for shape in first_slide.shapes
        ))
        self.assertTrue(any(shape.has_table for shape in first_slide.shapes))
        self.assertIn('First item', '\n'.join(
            shape.text for shape in first_slide.shapes if shape.has_text_frame
        ))

        pdf_response = self.client.post('/api/download/pdf', json=payload)
        self.assertEqual(pdf_response.status_code, 200, pdf_response.get_json())
        pdf = PdfReader(io.BytesIO(pdf_response.data))
        self.assertGreaterEqual(len(pdf.pages), 2)
        pdf_text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        self.assertIn('Important terms', pdf_text)
        self.assertIn('Second page content.', pdf_text)
        self.assertIn('tradução', pdf_text)

        txt_response = self.client.post('/api/download/txt', json=payload)
        self.assertEqual(txt_response.status_code, 200)
        self.assertIn('First item', txt_response.data.decode('utf-8-sig'))
        self.assertIn('Second page content.', txt_response.data.decode('utf-8-sig'))

    def test_extracts_and_exports_unicode_accents_without_replacing_characters(self):
        accented_text = (
            'A\u00e7\u00e3o, ma\u00e7\u00e3, p\u00e3o, av\u00f3, b\u00ean\u00e7\u00e3o, '
            'cora\u00e7\u00e3o; Portugu\u00eas: \u00e3 \u00f5 \u00e7 \u00e9 \u00e1 '
            '\u00ed \u00f3 \u00fa \u00e2 \u00ea \u00f4 \u00c0 \u00c9 \u00d5 \u00c7.'
        )
        pages = [{
            'page_title': 'P\u00e1gina 1',
            'title': '',
            'subtitle': '',
            'blocks': [{'type': 'paragraph', 'text': accented_text}],
        }]

        with tempfile.TemporaryDirectory() as directory:
            docx_path = Path(directory) / 'accents.docx'
            document = Document()
            document.add_paragraph(accented_text)
            document.save(docx_path)
            docx_pages = app.extract_document_pages(str(docx_path), '.docx')
            self.assertEqual(docx_pages[0]['blocks'][0]['text'], accented_text)

            pptx_path = Path(directory) / 'accents.pptx'
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            textbox = slide.shapes.add_textbox(
                Inches(1), Inches(1), Inches(8), Inches(1)
            )
            textbox.text = accented_text
            presentation.save(pptx_path)
            pptx_pages = app.extract_document_pages(str(pptx_path), '.pptx')
            self.assertEqual(pptx_pages[0]['blocks'][0]['text'], accented_text)

            pdf_path = Path(directory) / 'accents.pdf'
            pdf_path.write_bytes(app._export_pdf(pages))
            pdf_pages = app.extract_document_pages(str(pdf_path), '.pdf')
            extracted_pdf_text = '\n'.join(
                block['text']
                for page in pdf_pages
                for block in page['blocks']
            )
            self.assertIn(accented_text, extracted_pdf_text)

        payload = {'filename': 'accents.docx', 'pages': pages}
        for format_name in ('txt', 'docx', 'pptx', 'pdf'):
            with self.subTest(format=format_name):
                response = self.client.post(
                    f'/api/download/{format_name}',
                    json=payload,
                )
                self.assertEqual(response.status_code, 200, response.get_json())
                if format_name == 'txt':
                    exported_text = response.data.decode('utf-8-sig')
                elif format_name == 'docx':
                    exported_text = '\n'.join(
                        paragraph.text for paragraph in Document(io.BytesIO(response.data)).paragraphs
                    )
                elif format_name == 'pptx':
                    exported_text = '\n'.join(
                        shape.text
                        for slide in Presentation(io.BytesIO(response.data)).slides
                        for shape in slide.shapes
                        if shape.has_text_frame
                    )
                else:
                    exported_text = '\n'.join(
                        page.extract_text() or ''
                        for page in PdfReader(io.BytesIO(response.data)).pages
                    )
                self.assertIn(accented_text, exported_text)

    def test_download_rejects_malformed_content_and_unknown_format(self):
        response = self.client.post('/api/download/docx', json={'pages': [{'blocks': 'bad'}]})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/download/rtf', json={'pages': []})
        self.assertEqual(response.status_code, 404)

    @staticmethod
    def make_scanned_pdf():
        image = Image.new('RGB', (1600, 500), 'white')
        draw = ImageDraw.Draw(image)
        draw.text(
            (60, 170),
            'OCR STUDY MATERIAL 1234',
            fill='black',
            font=ImageFont.load_default(size=72),
        )
        png = io.BytesIO()
        image.save(png, format='PNG')
        document = pymupdf.open()
        page = document.new_page(width=800, height=250)
        page.insert_image(page.rect, stream=png.getvalue())
        content = document.tobytes()
        document.close()
        return content

    @staticmethod
    def make_portuguese_scanned_pdf():
        expected_text = 'Ação, coração, português, maçã e educação.'
        text_pdf = app._export_pdf([{
            'page_title': '',
            'title': '',
            'subtitle': '',
            'blocks': [{'type': 'paragraph', 'text': expected_text}],
        }])
        source_document = pymupdf.open(stream=text_pdf, filetype='pdf')
        scanned_document = pymupdf.open()
        try:
            source_page = source_document[0]
            pixmap = source_page.get_pixmap(
                matrix=pymupdf.Matrix(3, 3),
                alpha=False,
            )
            scanned_page = scanned_document.new_page(
                width=source_page.rect.width,
                height=source_page.rect.height,
            )
            scanned_page.insert_image(scanned_page.rect, stream=pixmap.tobytes('png'))
            return expected_text, scanned_document.tobytes()
        finally:
            scanned_document.close()
            source_document.close()

    @patch('app._check_ocr_ready')
    @patch('app._recognize_pdf_page', return_value='Recognized study content.')
    @patch(
        'app.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_ocr_text_is_sent_through_translation(self, _translate, _recognize, _check):
        response = self.upload('scan.pdf', self.make_scanned_pdf(), 'en', 'pt')
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['pages'][0]['blocks'][0]['text'], 'pt: Recognized study content.')

    @patch('app.ocr_status', return_value={
        'available': False,
        'languages': [],
        'error': 'Instale o Tesseract OCR para reconhecer este PDF.',
    })
    def test_scanned_pdf_reports_missing_ocr_engine(self, _status):
        response = self.upload('scan.pdf', self.make_scanned_pdf(), 'pt', 'en')
        self.assertEqual(response.status_code, 422)
        self.assertIn('Tesseract OCR', response.get_json()['error'])

    def test_real_ocr_recognizes_scanned_pdf_when_tesseract_language_is_installed(self):
        status = app.ocr_status('en')
        if not status['available'] or status.get('missing_languages'):
            self.skipTest(status.get('error', 'Tesseract OCR or English data is unavailable'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scan.pdf'
            path.write_bytes(self.make_scanned_pdf())
            pages = app.extract_document_pages(str(path), '.pdf', source_lang='en')
        self.assertIn('OCR', ' '.join(block['text'] for block in pages[0]['blocks']).upper())

    def test_real_ocr_recognizes_portuguese_accents_in_scanned_pdf(self):
        status = app.ocr_status('pt')
        if not status['available'] or status.get('missing_languages'):
            self.skipTest(status.get('error', 'Tesseract OCR or Portuguese data is unavailable'))

        self.assertIn('por', status['languages'])
        expected_text, scanned_pdf = self.make_portuguese_scanned_pdf()
        self.assertFalse(any(
            (page.extract_text() or '').strip()
            for page in PdfReader(io.BytesIO(scanned_pdf)).pages
        ))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'portuguese-scan.pdf'
            path.write_bytes(scanned_pdf)
            pages = app.extract_document_pages(str(path), '.pdf', source_lang='pt')

        recognized_text = ' '.join(
            block['text']
            for page in pages
            for block in page['blocks']
        )
        for word in expected_text.replace(',', '').replace('.', '').split():
            with self.subTest(word=word):
                self.assertIn(word, recognized_text)

    def test_ocr_status_describes_engine_and_language_requirements(self):
        response = self.client.get('/api/ocr/status?source_lang=en')
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn('available', payload)
        if not payload['available'] or payload.get('missing_languages'):
            self.assertTrue(payload.get('error'))

    def test_extracts_each_supported_file_and_keeps_pages(self):
        for name in ('sample.pdf', 'sample.docx', 'sample.pptx'):
            with self.subTest(name=name):
                pages = app.extract_document_pages(str(FIXTURES / name), Path(name).suffix)
                self.assertTrue(pages)
                if name.endswith('.pdf'):
                    self.assertTrue(all(page['page_title'].startswith('Página ') for page in pages))
                if name.endswith('.pptx'):
                    self.assertTrue(all(page['page_title'].startswith('Slide ') for page in pages))

    def test_preserves_word_heading_and_list_styles(self):
        document = Document()
        document.add_heading('Chapter title', level=1)
        document.add_paragraph('First item', style='List Bullet')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.docx'
            document.save(path)
            blocks = app.extract_word_document(str(path))[0]['blocks']
        self.assertEqual([block['type'] for block in blocks], ['heading', 'list-item'])

    def test_extracts_powerpoint_text_in_visual_reading_order(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(0.5), Inches(3.5), Inches(4), Inches(0.5)).text = 'Bottom'
        slide.shapes.add_textbox(Inches(5), Inches(1), Inches(4), Inches(0.5)).text = 'Top right'
        slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(4), Inches(0.5)).text = 'Top left'

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reading-order.pptx'
            presentation.save(path)
            blocks = app.extract_powerpoint_document(str(path))[0]['blocks']

        self.assertEqual(
            [block['text'] for block in blocks],
            ['Top left', 'Top right', 'Bottom'],
        )

    def test_extracts_powerpoint_table_rows(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        table = slide.shapes.add_table(
            rows=2,
            cols=2,
            left=Inches(1),
            top=Inches(1),
            width=Inches(6),
            height=Inches(2),
        ).table
        table.cell(0, 0).text = 'Term'
        table.cell(0, 1).text = 'Meaning'
        table.cell(1, 0).text = 'Cell'
        table.cell(1, 1).text = 'Basic unit of life'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'table.pptx'
            presentation.save(path)
            blocks = app.extract_powerpoint_document(str(path))[0]['blocks']
        self.assertEqual(
            [block['text'] for block in blocks],
            ['Term | Meaning', 'Cell | Basic unit of life'],
        )

    def test_keeps_powerpoint_slides_separate_and_in_sequence(self):
        presentation = Presentation()
        for content in ('First slide', 'Second slide'):
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            textbox = slide.shapes.add_textbox(
                Inches(1),
                Inches(1),
                Inches(5),
                Inches(1),
            )
            textbox.text = content
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'multiple-slides.pptx'
            presentation.save(path)
            pages = app.extract_powerpoint_document(str(path))
        self.assertEqual([page['page_title'] for page in pages], ['Slide 1', 'Slide 2'])
        self.assertEqual(
            [page['blocks'][0]['text'] for page in pages],
            ['First slide', 'Second slide'],
        )

    @patch('app.translate_blocks', side_effect=lambda blocks, source, target, deadline=None: blocks)
    def test_preserves_page_and_blank_slide_separation(self, _translate):
        pages = [
            {'page_title': 'Página 1', 'blocks': [{'type': 'paragraph', 'text': 'First page'}]},
            {'page_title': 'Página 2', 'blocks': []},
            {'page_title': 'Página 3', 'blocks': [{'type': 'paragraph', 'text': 'Third page'}]},
        ]
        result = app.translate_document_pages('unused.pdf', '.pdf', 'pt', 'en', pages=pages)
        self.assertEqual([page['page_title'] for page in result], ['Página 1', 'Página 2', 'Página 3'])
        self.assertEqual(result[1]['blocks'], [])

    @patch(
        'app.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_translates_upload_using_selected_languages(self, _translate):
        response = self.upload('sample.docx', (FIXTURES / 'sample.docx').read_bytes(), 'pt', 'es')
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['target_lang'], 'es')
        self.assertTrue(payload['pages'][0]['blocks'])
        self.assertTrue(all(block['text'].startswith('es: ') for block in payload['pages'][0]['blocks']))

    def test_rejects_empty_file(self):
        response = self.upload('empty.pdf', b'')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vazio', response.get_json()['error'])

    def test_rejects_unsupported_format(self):
        response = self.upload('notes.txt', b'content')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Formato não permitido', response.get_json()['error'])

    def test_rejects_corrupt_word_document(self):
        response = self.upload('broken.docx', b'not a zip archive')
        self.assertEqual(response.status_code, 400)
        self.assertIn('documento válido', response.get_json()['error'])

    def test_rejects_document_without_extractable_text(self):
        document = Document()
        content = io.BytesIO()
        document.save(content)
        response = self.upload('empty.docx', content.getvalue())
        self.assertEqual(response.status_code, 422)
        self.assertIn('Nenhum texto', response.get_json()['error'])

    def test_reports_translation_service_failure(self):
        with patch(
            'app.translate_document_pages',
            side_effect=RuntimeError('Não foi possível conectar ao serviço de tradução.'),
        ):
            response = self.upload(
                'sample.docx', (FIXTURES / 'sample.docx').read_bytes()
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn('serviço de tradução', response.get_json()['error'])

    def test_rejects_same_source_and_target_language(self):
        response = self.upload('sample.docx', (FIXTURES / 'sample.docx').read_bytes(), 'en', 'en')
        self.assertEqual(response.status_code, 400)
        self.assertIn('idiomas diferentes', response.get_json()['error'])

    def test_rejects_upload_over_ten_megabytes(self):
        response = self.upload('large.pdf', b'x' * (app.MAX_UPLOAD_BYTES + 1))
        self.assertEqual(response.status_code, 413)

    @patch('app.translate_text', side_effect=AssertionError('demo must not translate'))
    def test_demo_results_are_available_without_calling_translation(self, _translate):
        for format_name in ('pdf', 'docx', 'pptx'):
            with self.subTest(format=format_name):
                response = self.client.get(f'/api/demo/{format_name}')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['demo'])
                self.assertTrue(response.get_json()['pages'])

    def test_demo_rejects_unknown_format(self):
        response = self.client.get('/api/demo/rtf')
        self.assertEqual(response.status_code, 404)

    @patch(
        'app.provider_status',
        return_value=[
            {'name': 'libretranslate', 'status': 'unavailable', 'error': 'offline'},
            {'name': 'argos', 'status': 'available', 'pairs': ['pt->en', 'en->pt']},
        ],
    )
    def test_translation_status_reports_provider_pairs(self, _status):
        response = self.client.get('/api/translation/status')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['available_pairs'], ['en->pt', 'pt->en'])
        self.assertTrue(payload['demo_available'])

    @patch('app.argos_model_status', return_value={
        'source': 'pt',
        'target': 'en',
        'installed': True,
        'installed_pairs': ['pt->en'],
        'catalog_checked': False,
        'package_available': False,
        'package_version': None,
        'download_host': None,
    })
    def test_argos_model_status_does_not_refresh_catalog_implicitly(self, status):
        response = self.client.get('/api/argos/models?source=pt&target=en')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['installed'])
        self.assertFalse(response.get_json()['catalog_checked'])
        status.assert_called_once_with('pt', 'en')

    def test_argos_model_routes_reject_invalid_language_pairs(self):
        response = self.client.get('/api/argos/models?source=pt&target=pt')
        self.assertEqual(response.status_code, 400)

    def test_clean_text_preserves_paragraph_breaks(self):
        self.assertEqual(app.clean_text('First paragraph.\n\nSecond paragraph.'), 'First paragraph.\n\nSecond paragraph.')

    def test_long_unbroken_text_is_split_within_provider_limit(self):
        text = 'x' * 3100
        chunks = app.split_text_chunks(text, max_chars=1400)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(0 < len(chunk) <= 1400 for chunk in chunks))

    def test_translate_blocks_batches_chunks_without_changing_their_order_or_type(self):
        blocks = [
            {'type': 'heading', 'text': 'A title'},
            {'type': 'paragraph', 'text': 'x' * 1500},
            {'type': 'list-item', 'text': 'A list item'},
            *[{'type': 'paragraph', 'text': f'Paragraph {index}'} for index in range(20)],
        ]
        with patch(
            'app.translate_texts',
            side_effect=lambda texts, source, target, deadline=None: [
                f'{target}: {text}' for text in texts
            ],
        ) as translate_batch:
            translated = app.translate_blocks(blocks, 'pt', 'en')

        self.assertEqual(translate_batch.call_count, 2)
        self.assertEqual(
            [block['type'] for block in translated],
            ['heading', 'paragraph', 'paragraph', 'list-item'] + ['paragraph'] * 20,
        )
        self.assertEqual(translated[0]['text'], 'en: A title')
        self.assertEqual(translated[1]['text'], f"en: {'x' * 1400}")
        self.assertEqual(translated[2]['text'], f"en: {'x' * 100}")
        self.assertEqual(translated[-1]['text'], 'en: Paragraph 19')

    def test_preserves_word_table_position_in_body_order(self):
        document = Document()
        document.add_paragraph('Before table')
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = 'Cell A'
        table.cell(0, 1).text = 'Cell B'
        document.add_paragraph('After table')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ordered.docx'
            document.save(path)
            blocks = app.extract_word_document(str(path))[0]['blocks']
        self.assertEqual(
            [(block['type'], block['text']) for block in blocks],
            [
                ('paragraph', 'Before table'),
                ('table-row', 'Cell A | Cell B'),
                ('paragraph', 'After table'),
            ],
        )

    def test_reports_duplicate_document_request(self):
        content = (FIXTURES / 'sample.docx').read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        key = f'pt:en:{digest}'
        with app.ACTIVE_TRANSLATIONS_LOCK:
            app.ACTIVE_TRANSLATIONS.add(key)
        try:
            response = self.upload('sample.docx', content)
        finally:
            with app.ACTIVE_TRANSLATIONS_LOCK:
                app.ACTIVE_TRANSLATIONS.discard(key)
        self.assertEqual(response.status_code, 409)

    def test_real_local_argos_fallback_translates_each_document_format(self):
        argos = ArgosProvider()
        if not argos.supports('pt', 'en'):
            self.skipTest('pt->en Argos model is not installed')
        with patch('translation_engine.ENGINE', TranslationEngine([argos])):
            for name in ('sample.pdf', 'sample.docx', 'sample.pptx'):
                with self.subTest(name=name):
                    response = self.upload(
                        name,
                        (FIXTURES / name).read_bytes(),
                        'pt',
                        'en',
                    )
                    self.assertEqual(response.status_code, 200, response.get_json())
                    pages = response.get_json()['pages']
                    self.assertTrue(pages)
                    self.assertTrue(any(
                        block['text'].strip()
                        for page in pages
                        for block in page['blocks']
                    ))

    def test_real_libretranslate_connection_failure_falls_back_to_argos(self):
        argos = ArgosProvider()
        if not argos.supports('pt', 'en'):
            self.skipTest('pt->en Argos model is not installed')
        from translation_engine import LibreTranslateProvider

        engine = TranslationEngine([
            LibreTranslateProvider(['http://127.0.0.1:59999'], 0.1, 0.1, 1),
            argos,
        ])
        with patch('translation_engine.ENGINE', engine):
            response = self.upload(
                'sample.docx',
                (FIXTURES / 'sample.docx').read_bytes(),
                'pt',
                'en',
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        translated = ' '.join(
            block['text']
            for page in response.get_json()['pages']
            for block in page['blocks']
        )
        self.assertIn('Study Plan', translated)
        self.assertNotIn('Plano de Estudos', translated)


if __name__ == '__main__':
    unittest.main()
