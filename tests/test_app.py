import hashlib
import io
import re
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

from traduzedu import config, create_app
from traduzedu.models.document import group_blocks, validate_export_pages
from traduzedu.models.text import clean_text, split_text_chunks
from traduzedu.services import export, extraction, ocr, translation
from traduzedu.services.translation_engine import ArgosProvider, TranslationEngine


FIXTURES = Path(__file__).parent / 'fixtures'
EXAMPLE_PDF = config.EXAMPLES_DIR / 'sample.pdf'


class TranslationApiTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

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
        for path in ('/static/css/style.css', '/static/js/model.js', '/static/js/view.js',
                     '/static/js/controller.js', '/static/exemplos/sample.pdf'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.addCleanup(response.close)
                self.assertEqual(response.status_code, 200)

        for path in (
            '/app.py',
            '/README.md',
            '/requirements.txt',
            '/.git/config',
            '/static/../config.py',
            '/static/../services/translation_engine.py',
            '/static/../../app.py',
            '/script.js',
            '/static/exemplos/sample.docx',
            '/static/exemplos/sample.pptx',
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_upload_form_advertises_pdf_only(self):
        response = self.client.get('/')
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        file_inputs = [
            line for line in html.splitlines()
            if '<input type="file"' in line
        ]
        self.assertEqual(len(file_inputs), 1)
        self.assertIn('accept=".pdf,application/pdf"', file_inputs[0])
        self.assertNotIn('.docx', file_inputs[0].lower())
        self.assertNotIn('.pptx', file_inputs[0].lower())
        self.assertIn('Somente PDF', html)

    def test_text_pdf_download_keeps_translated_content(self):
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
        payload = {'filename': 'sample.pdf', 'pages': pages}

        pdf_response = self.client.post('/api/download/pdf', json=payload)
        self.assertEqual(pdf_response.status_code, 200, pdf_response.get_json())
        pdf = PdfReader(io.BytesIO(pdf_response.data))
        self.assertGreaterEqual(len(pdf.pages), 2)
        pdf_text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        self.assertIn('Important terms', pdf_text)
        self.assertIn('Second page content.', pdf_text)
        self.assertIn('tradução', pdf_text)


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
            docx_pages = extraction.extract_document_pages(str(docx_path), '.docx')
            self.assertEqual(docx_pages[0]['blocks'][0]['text'], accented_text)

            pptx_path = Path(directory) / 'accents.pptx'
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            textbox = slide.shapes.add_textbox(
                Inches(1), Inches(1), Inches(8), Inches(1)
            )
            textbox.text = accented_text
            presentation.save(pptx_path)
            pptx_pages = extraction.extract_document_pages(str(pptx_path), '.pptx')
            self.assertEqual(pptx_pages[0]['blocks'][0]['text'], accented_text)

            pdf_path = Path(directory) / 'accents.pdf'
            pdf_path.write_bytes(export.export_pdf(pages))
            pdf_pages = extraction.extract_document_pages(str(pdf_path), '.pdf')
            extracted_pdf_text = '\n'.join(
                block['text']
                for page in pdf_pages
                for block in page['blocks']
            )
            self.assertIn(accented_text, extracted_pdf_text)

        response = self.client.post(
            '/api/download/pdf',
            json={'filename': 'accents.pdf', 'pages': pages},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        exported_text = '\n'.join(
            page.extract_text() or ''
            for page in PdfReader(io.BytesIO(response.data)).pages
        )
        self.assertIn(accented_text, exported_text)

    def test_download_rejects_malformed_content_and_unknown_format(self):
        response = self.client.post('/api/download/pdf', json={'pages': [{'blocks': 'bad'}]})
        self.assertEqual(response.status_code, 400)
        for format_name in ('rtf', 'txt', 'docx', 'pptx'):
            with self.subTest(format=format_name):
                response = self.client.post(f'/api/download/{format_name}', json={'pages': []})
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
        text_pdf = export.export_pdf([{
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

    @patch('traduzedu.services.ocr.check_ocr_ready')
    @patch('traduzedu.services.ocr.recognize_pdf_page', return_value='Recognized study content.')
    @patch(
        'traduzedu.services.translation.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_ocr_text_is_sent_through_translation(self, _translate, _recognize, _check):
        response = self.upload('scan.pdf', self.make_scanned_pdf(), 'en', 'pt')
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['pages'][0]['blocks'][0]['text'], 'pt: Recognized study content.')

    @patch('traduzedu.services.ocr.ocr_status', return_value={
        'available': False,
        'languages': [],
        'error': 'Instale o Tesseract OCR para reconhecer este PDF.',
    })
    def test_scanned_pdf_reports_missing_ocr_engine(self, _status):
        response = self.upload('scan.pdf', self.make_scanned_pdf(), 'pt', 'en')
        self.assertEqual(response.status_code, 422)
        self.assertIn('Tesseract OCR', response.get_json()['error'])

    @patch('traduzedu.services.ocr.ocr_status', return_value={
        'available': False,
        'languages': [],
        'error': 'Instale o Tesseract OCR para reconhecer este PDF.',
    })
    @patch(
        'traduzedu.services.translation.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_pages_without_text_are_skipped_when_ocr_is_unavailable(self, _translate, _status):
        text_pdf = export.export_pdf([{
            'page_title': '', 'title': '', 'subtitle': '',
            'blocks': [{'type': 'paragraph', 'text': 'Texto da primeira página.'}],
        }])
        document = pymupdf.open(stream=text_pdf, filetype='pdf')
        document.new_page()
        content = document.tobytes()
        document.close()

        response = self.upload('misto.pdf', content, 'pt', 'es')

        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(len(payload['pages']), 2)
        self.assertIn('Texto da primeira', payload['pages'][0]['blocks'][-1]['text'])
        self.assertEqual(payload['pages'][1]['blocks'], [])
        self.assertTrue(any('2' in warning for warning in payload['warnings']))

    def test_real_ocr_recognizes_scanned_pdf_when_tesseract_language_is_installed(self):
        status = ocr.ocr_status('en')
        if not status['available'] or status.get('missing_languages'):
            self.skipTest(status.get('error', 'Tesseract OCR or English data is unavailable'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scan.pdf'
            path.write_bytes(self.make_scanned_pdf())
            pages = extraction.extract_document_pages(str(path), '.pdf', source_lang='en')
        self.assertIn('OCR', ' '.join(block['text'] for block in pages[0]['blocks']).upper())

    def test_real_ocr_recognizes_portuguese_accents_in_scanned_pdf(self):
        status = ocr.ocr_status('pt')
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
            pages = extraction.extract_document_pages(str(path), '.pdf', source_lang='pt')

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

    def test_extracts_sample_documents_and_keeps_pages(self):
        for path in (EXAMPLE_PDF, FIXTURES / 'sample.docx', FIXTURES / 'sample.pptx'):
            name = path.name
            with self.subTest(name=name):
                pages = extraction.extract_document_pages(str(path), path.suffix)
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
            blocks = extraction.extract_word_document(str(path))[0]['blocks']
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
            blocks = extraction.extract_powerpoint_document(str(path))[0]['blocks']

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
            blocks = extraction.extract_powerpoint_document(str(path))[0]['blocks']
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
            pages = extraction.extract_powerpoint_document(str(path))
        self.assertEqual([page['page_title'] for page in pages], ['Slide 1', 'Slide 2'])
        self.assertEqual(
            [page['blocks'][0]['text'] for page in pages],
            ['First slide', 'Second slide'],
        )

    @patch(
        'traduzedu.services.translation.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_translated_pdf_keeps_layout_images_and_replaces_only_the_text(self, _translate):
        source = pymupdf.open()
        page = source.new_page(width=960, height=540)
        image = Image.new('RGB', (40, 40), (230, 100, 20))
        png = io.BytesIO()
        image.save(png, format='PNG')
        page.insert_image(pymupdf.Rect(0, 0, 960, 40), stream=png.getvalue())
        page.insert_text((80, 120), 'Leitura de minicontos', fontsize=24, color=(0.5, 0.2, 0.5))
        page.insert_text((80, 200), 'Colocação pronominal', fontsize=24)
        content = source.tobytes()
        source.close()

        response = self.upload('aula.pdf', content, 'pt', 'es')
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(
            [block['text'] for block in payload['pages'][0]['blocks']],
            ['es: Leitura de minicontos', 'es: Colocação pronominal'],
        )

        download = self.client.get(payload['translated_pdf_url'])
        self.addCleanup(download.close)
        self.assertEqual(download.status_code, 200)
        self.assertIn('aula-traduzido.pdf', download.headers['Content-Disposition'])
        translated = pymupdf.open(stream=download.data, filetype='pdf')
        try:
            translated_page = translated[0]
            self.assertEqual(translated_page.rect, pymupdf.Rect(0, 0, 960, 540))
            self.assertEqual(len(translated_page.get_images()), 1)
            words = translated_page.get_text('words')
            text = ' '.join(word[4] for word in words)
            self.assertIn('es: Leitura de minicontos', text)
            self.assertEqual(text.count('Leitura'), 1)
            first_word = next(word for word in words if word[4] == 'es:')
            self.assertAlmostEqual(first_word[0], 80, delta=2)
            self.assertAlmostEqual(first_word[3], 120, delta=8)
        finally:
            translated.close()

    @patch(
        'traduzedu.services.translation.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            'Foco en el contenido de la clase' for _text in texts
        ],
    )
    def test_single_line_text_stays_on_one_line_when_translation_is_longer(self, _translate):
        source = pymupdf.open()
        page = source.new_page(width=960, height=540)
        page.insert_text((40, 40), 'Foco no conteúdo', fontsize=20)
        page.insert_text((40, 300), 'Outro bloco mais abaixo', fontsize=20)
        content = source.tobytes()
        source.close()

        response = self.upload('faixa.pdf', content, 'pt', 'es')
        self.assertEqual(response.status_code, 200, response.get_json())
        download = self.client.get(response.get_json()['translated_pdf_url'])
        self.addCleanup(download.close)
        translated = pymupdf.open(stream=download.data, filetype='pdf')
        try:
            words = [w for w in translated[0].get_text('words') if w[1] < 150]
        finally:
            translated.close()
        self.assertEqual(' '.join(w[4] for w in words), 'Foco en el contenido de la clase')
        self.assertEqual(len({round(w[3]) for w in words}), 1)

    def test_translated_pdf_download_reports_expired_file(self):
        response = self.client.get('/api/download/translated/naoexiste')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Traduza o arquivo novamente', response.get_json()['error'])

    @patch(
        'traduzedu.services.translation.translate_texts',
        side_effect=lambda texts, source, target, deadline=None: [
            f'{target}: {text}' for text in texts
        ],
    )
    def test_translates_upload_using_selected_languages(self, _translate):
        response = self.upload('sample.pdf', EXAMPLE_PDF.read_bytes(), 'pt', 'es')
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['target_lang'], 'es')
        self.assertTrue(payload['pages'][0]['blocks'])
        self.assertTrue(all(block['text'].startswith('es: ') for block in payload['pages'][0]['blocks']))

    def test_rejects_empty_file(self):
        response = self.upload('empty.pdf', b'')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vazio', response.get_json()['error'])

    def test_rejects_non_pdf_uploads(self):
        unsupported_files = (
            ('notes.txt', b'content'),
            ('sample.docx', (FIXTURES / 'sample.docx').read_bytes()),
            ('sample.pptx', (FIXTURES / 'sample.pptx').read_bytes()),
        )
        for name, content in unsupported_files:
            with self.subTest(name=name):
                response = self.upload(name, content)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Envie somente um arquivo PDF', response.get_json()['error'])

    def test_rejects_non_pdf_content_with_pdf_extension(self):
        content = (FIXTURES / 'sample.docx').read_bytes()
        response = self.upload('renamed.pdf', content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('PDF válido', response.get_json()['error'])

    def test_rejects_document_without_extractable_text(self):
        document = pymupdf.open()
        document.new_page()
        content = document.tobytes()
        document.close()
        with patch('traduzedu.services.ocr.check_ocr_ready'), patch('traduzedu.services.ocr.recognize_pdf_page', return_value=''):
            response = self.upload('empty.pdf', content)
        self.assertEqual(response.status_code, 422)
        self.assertIn('Nenhum texto', response.get_json()['error'])

    def test_reports_translation_service_failure(self):
        with patch(
            'traduzedu.services.translation.translate_layout_document',
            side_effect=RuntimeError('Não foi possível conectar ao serviço de tradução.'),
        ):
            response = self.upload(
                'sample.pdf', EXAMPLE_PDF.read_bytes()
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn('serviço de tradução', response.get_json()['error'])

    def test_rejects_same_source_and_target_language(self):
        response = self.upload('sample.pdf', EXAMPLE_PDF.read_bytes(), 'en', 'en')
        self.assertEqual(response.status_code, 400)
        self.assertIn('idiomas diferentes', response.get_json()['error'])

    def test_rejects_upload_over_ten_megabytes(self):
        response = self.upload('large.pdf', b'x' * (config.MAX_UPLOAD_BYTES + 1))
        self.assertEqual(response.status_code, 413)

    @patch('traduzedu.services.translation.translate_texts', side_effect=AssertionError('demo must not translate'))
    def test_demo_results_are_available_without_calling_translation(self, _translate):
        for format_name in ('pdf',):
            with self.subTest(format=format_name):
                response = self.client.get(f'/api/demo/{format_name}')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['demo'])
                self.assertTrue(response.get_json()['pages'])

    def test_demo_rejects_unknown_format(self):
        for format_name in ('rtf', 'docx', 'pptx'):
            with self.subTest(format=format_name):
                response = self.client.get(f'/api/demo/{format_name}')
                self.assertEqual(response.status_code, 404)

    def test_page_offers_only_the_pdf_demo(self):
        response = self.client.get('/')
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        self.assertNotIn('id="demoFormato"', html)
        self.assertIn('exemplos/sample.pdf', html)

    def test_download_offers_only_the_translated_pdf(self):
        response = self.client.get('/')
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        select = html.split('id="formatoDownload"', 1)[1].split('</select>', 1)[0]
        options = re.findall(r'<option value="([^"]+)"[^>]*>([^<]+)</option>', select)
        self.assertEqual(options, [('pdf-layout', 'PDF traduzido')])

    @patch(
        'traduzedu.services.translation_engine.provider_status',
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

    @patch('traduzedu.services.translation_engine.argos_model_status', return_value={
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
        self.assertEqual(clean_text('First paragraph.\n\nSecond paragraph.'), 'First paragraph.\n\nSecond paragraph.')

    def test_long_unbroken_text_is_split_within_provider_limit(self):
        text = 'x' * 3100
        chunks = split_text_chunks(text, max_chars=1400)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(0 < len(chunk) <= 1400 for chunk in chunks))

    def test_translate_texts_in_order_batches_long_texts_and_keeps_one_result_per_text(self):
        texts = ['A title', 'x' * 1500, 'A list item', *[f'Paragraph {index}' for index in range(20)]]
        with patch(
            'traduzedu.services.translation.translate_texts',
            side_effect=lambda texts, source, target, deadline=None: [
                f'{target}: {text}' for text in texts
            ],
        ) as translate_batch:
            translated = translation.translate_texts_in_order(texts, 'pt', 'en')

        self.assertEqual(translate_batch.call_count, 2)
        self.assertEqual(len(translated), len(texts))
        self.assertEqual(translated[0], 'en: A title')
        self.assertEqual(translated[1], f"en: {'x' * 1400} en: {'x' * 100}")
        self.assertEqual(translated[-1], 'en: Paragraph 19')

    def test_translated_file_store_expires_old_files(self):
        from traduzedu.services.result_store import TranslatedFileStore

        store = TranslatedFileStore(ttl_seconds=0)
        self.assertIsNone(store.get(store.save(b'%PDF', 'a.pdf')))
        store = TranslatedFileStore(max_items=1)
        first = store.save(b'1', 'a.pdf')
        second = store.save(b'2', 'b.pdf')
        self.assertIsNone(store.get(first))
        self.assertEqual(store.get(second).content, b'2')

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
            blocks = extraction.extract_word_document(str(path))[0]['blocks']
        self.assertEqual(
            [(block['type'], block['text']) for block in blocks],
            [
                ('paragraph', 'Before table'),
                ('table-row', 'Cell A | Cell B'),
                ('paragraph', 'After table'),
            ],
        )

    def test_reports_duplicate_document_request(self):
        content = EXAMPLE_PDF.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        key = f'pt:en:{digest}'
        self.assertTrue(translation.ACTIVE_TRANSLATIONS.try_acquire(key))
        try:
            response = self.upload('sample.pdf', content)
        finally:
            translation.ACTIVE_TRANSLATIONS.release(key)
        self.assertEqual(response.status_code, 409)

    def test_real_local_argos_fallback_translates_pdf_upload(self):
        argos = ArgosProvider()
        if not argos.supports('pt', 'en'):
            self.skipTest('pt->en Argos model is not installed')
        with patch('traduzedu.services.translation_engine.ENGINE', TranslationEngine([argos])):
            response = self.upload(
                'sample.pdf',
                EXAMPLE_PDF.read_bytes(),
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
        from traduzedu.services.translation_engine import LibreTranslateProvider

        engine = TranslationEngine([
            LibreTranslateProvider(['http://127.0.0.1:59999'], 0.1, 0.1, 1),
            argos,
        ])
        with patch('traduzedu.services.translation_engine.ENGINE', engine):
            response = self.upload(
                'sample.pdf',
                EXAMPLE_PDF.read_bytes(),
                'pt',
                'en',
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        translated = ' '.join(
            block['text']
            for page in response.get_json()['pages']
            for block in page['blocks']
        )
        source_pages = extraction.extract_document_pages(str(EXAMPLE_PDF), '.pdf')
        source_text = ' '.join(
            block['text']
            for page in source_pages
            for block in page['blocks']
        )
        self.assertTrue(translated.strip())
        self.assertNotEqual(translated.strip(), source_text.strip())


class ServerStartupTests(unittest.TestCase):
    def test_detects_port_already_taken_by_another_server(self):
        import socket
        from traduzedu.server import port_in_use

        with socket.socket() as existing:
            existing.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            existing.bind(('127.0.0.1', 0))
            existing.listen()
            port = existing.getsockname()[1]
            self.assertTrue(port_in_use('127.0.0.1', port))
        self.assertFalse(port_in_use('127.0.0.1', port))


class DocumentModelTests(unittest.TestCase):
    def test_group_blocks_joins_consecutive_table_rows(self):
        blocks = [
            {'type': 'paragraph', 'text': 'Intro'},
            {'type': 'table-row', 'text': 'A | B'},
            {'type': 'table-row', 'text': 'C | D'},
            {'type': 'list-item', 'text': 'Item'},
        ]
        self.assertEqual(list(group_blocks(blocks)), [
            ('block', blocks[0]),
            ('table', [['A', 'B'], ['C', 'D']]),
            ('block', blocks[3]),
        ])

    def test_validate_export_pages_rejects_unknown_block_type(self):
        with self.assertRaises(ValueError):
            validate_export_pages([{'blocks': [{'type': 'image', 'text': 'x'}]}])

    def test_validate_export_pages_fills_missing_titles(self):
        pages = validate_export_pages([{'blocks': [{'type': 'paragraph', 'text': ' Olá '}]}])
        self.assertEqual(pages, [{
            'page_title': '', 'title': '', 'subtitle': '',
            'blocks': [{'type': 'paragraph', 'text': 'Olá'}],
        }])


if __name__ == '__main__':
    unittest.main()


class PdfLayoutUnitTests(unittest.TestCase):
    @staticmethod
    def span(text, bbox, font='Arial', size=10.0):
        return {'text': text, 'bbox': bbox, 'font': font, 'size': size, 'color': 0, 'flags': 0}

    def block(self, *spans):
        return {'type': 0, 'lines': [{'dir': (1.0, 0.0), 'spans': list(spans)}]}

    def test_symbol_font_bullet_is_kept_out_of_the_text_to_translate(self):
        from traduzedu.services import pdf_layout
        unit = pdf_layout._unit_from_block(self.block(
            self.span('', (156.6, 177.3, 162.2, 184.8), font='Wingdings', size=7.6),
            self.span('Custo/desempenho', (170.2, 175.5, 256.7, 185.5)),
        ))
        self.assertTrue(unit.bullet)
        self.assertEqual(unit.text, 'Custo/desempenho')
        self.assertAlmostEqual(unit.rect[0], 170.2)

    def test_text_drawn_twice_in_the_same_place_is_translated_once(self):
        from traduzedu.services import pdf_layout
        unit = pdf_layout._unit_from_block(self.block(
            self.span('Modularidade', (170.2, 206.7, 230.3, 216.7)),
            self.span('Modularidade', (170.2, 206.7, 230.3, 216.7)),
        ))
        self.assertEqual(unit.text, 'Modularidade')

    def test_private_use_symbols_inside_text_are_not_sent_for_translation(self):
        from traduzedu.services import pdf_layout
        unit = pdf_layout._unit_from_block(self.block(
            self.span(' Hosts: coleção de máquinas', (10, 10, 200, 20)),
        ))
        self.assertEqual(unit.text, 'Hosts: coleção de máquinas')

    def test_text_repeated_as_a_second_line_in_the_same_place_is_translated_once(self):
        from traduzedu.services import pdf_layout
        first = self.span('Desenvolvimento do software', (170.2, 533.0, 437.1, 542.9))
        second = self.span('caro.', (170.2, 545.0, 192.4, 554.9))
        block = {'type': 0, 'lines': [
            {'dir': (1.0, 0.0), 'spans': [first]},
            {'dir': (1.0, 0.0), 'spans': [dict(first)]},
            {'dir': (1.0, 0.0), 'spans': [second]},
            {'dir': (1.0, 0.0), 'spans': [dict(second)]},
        ]}
        unit = pdf_layout._unit_from_block(block)
        self.assertEqual(unit.text, 'Desenvolvimento do software caro.')
        self.assertEqual(unit.line_count, 2)
