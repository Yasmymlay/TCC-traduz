import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from docx import Document

import app


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

    @patch('app.translate_blocks', side_effect=lambda blocks, source, target: blocks)
    def test_preserves_page_and_blank_slide_separation(self, _translate):
        pages = [
            {'page_title': 'Página 1', 'blocks': [{'type': 'paragraph', 'text': 'First page'}]},
            {'page_title': 'Página 2', 'blocks': []},
            {'page_title': 'Página 3', 'blocks': [{'type': 'paragraph', 'text': 'Third page'}]},
        ]
        result = app.translate_document_pages('unused.pdf', '.pdf', 'pt', 'en', pages=pages)
        self.assertEqual([page['page_title'] for page in result], ['Página 1', 'Página 2', 'Página 3'])
        self.assertEqual(result[1]['blocks'], [])

    @patch('app.translate_chunk', side_effect=lambda text, source, target: f'{target}: {text}')
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

    @patch('app.requests.post')
    def test_never_returns_original_text_when_translation_is_empty(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {'translatedText': ''}
        with self.assertRaisesRegex(RuntimeError, 'resposta vazia'):
            app.translate_chunk('texto original', 'pt', 'en')

    @patch('app.requests.post', side_effect=requests.ConnectionError('offline'))
    def test_reports_translation_service_unavailable(self, _post):
        with self.assertRaisesRegex(RuntimeError, 'serviço de tradução'):
            app.translate_chunk('texto original', 'pt', 'en')


if __name__ == '__main__':
    unittest.main()
