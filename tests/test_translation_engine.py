import time
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from traduzedu.services.translation_engine import (
    ArgosProvider,
    DeepLProvider,
    LibreTranslateProvider,
    TranslationEngine,
    TranslationError,
)


class StubProvider:
    name = 'stub'

    def __init__(self, result=None, error=None, supported=True):
        self.result = result
        self.error = error
        self.supported = supported
        self.calls = 0

    def supports(self, source, target):
        return self.supported

    def translate(self, text, source, target, deadline=None):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    def status(self):
        return {'name': self.name, 'status': 'available', 'pairs': ['pt->en']}


def libre_response(status, payload=None):
    response = Mock()
    response.status_code = status
    response.headers = {}
    response.json.return_value = payload or {'translatedText': 'Good morning'}
    return response


class TranslationEngineTests(unittest.TestCase):
    def test_falls_back_to_local_argos_after_primary_provider_failure(self):
        argos = ArgosProvider()
        if not argos.supports('pt', 'en'):
            self.skipTest('pt->en Argos model is not installed')
        primary = StubProvider(error=TranslationError('LibreTranslate offline'))

        result = TranslationEngine([primary, argos]).translate('Bom dia', 'pt', 'en')

        self.assertTrue(result.strip())
        self.assertNotEqual(result.strip(), 'Bom dia')
        self.assertEqual(primary.calls, 1)

    def test_falls_back_when_primary_provider_does_not_support_pair(self):
        unsupported = StubProvider(supported=False)
        fallback = StubProvider(result='Good morning')

        result = TranslationEngine([unsupported, fallback]).translate('Bom dia', 'pt', 'en')

        self.assertEqual(result, 'Good morning')
        self.assertEqual(unsupported.calls, 0)

    def test_fails_explicitly_when_every_provider_is_unavailable(self):
        engine = TranslationEngine([
            StubProvider(error=TranslationError('offline')),
            StubProvider(supported=False),
        ])

        with self.assertRaisesRegex(TranslationError, 'A tradução não foi concluída'):
            engine.translate('Bom dia', 'pt', 'en')

    def test_retries_transient_libretranslate_statuses(self):
        languages = libre_response(200, [
            {'code': 'pt', 'targets': ['en']},
            {'code': 'en', 'targets': ['pt']},
        ])
        for status in (429, 500, 502):
            with self.subTest(status=status):
                provider = LibreTranslateProvider(['http://localhost:5000'], 1, 1, 2)
                post_responses = [libre_response(status), libre_response(200)]
                with patch('traduzedu.services.translation_engine.requests.get', return_value=languages), \
                        patch('traduzedu.services.translation_engine.requests.post', side_effect=post_responses) as post, \
                        patch('traduzedu.services.translation_engine.time.sleep'):
                    self.assertEqual(
                        provider.translate('Bom dia', 'pt', 'en'),
                        'Good morning',
                    )
                self.assertEqual(post.call_count, 2)

    def test_libretranslate_400_falls_back_without_retrying_bad_request(self):
        languages = libre_response(200, [
            {'code': 'pt', 'targets': ['en']},
            {'code': 'en', 'targets': ['pt']},
        ])
        fallback = StubProvider(result='Good morning')
        with patch('traduzedu.services.translation_engine.requests.get', return_value=languages), \
                patch('traduzedu.services.translation_engine.requests.post', return_value=libre_response(400)) as post:
            result = TranslationEngine([
                LibreTranslateProvider(['http://localhost:5000'], 1, 1, 3),
                fallback,
            ]).translate('Bom dia', 'pt', 'en')
        self.assertEqual(result, 'Good morning')
        self.assertEqual(post.call_count, 1)

    def test_libretranslate_connection_error_falls_back(self):
        fallback = StubProvider(result='Good morning')
        with patch(
            'traduzedu.services.translation_engine.requests.get',
            side_effect=ConnectionError('offline'),
        ):
            result = TranslationEngine([
                LibreTranslateProvider(['http://localhost:5000'], 0.1, 0.1, 1),
                fallback,
            ]).translate('Bom dia', 'pt', 'en')
        self.assertEqual(result, 'Good morning')

    def test_libretranslate_caches_short_lived_outage_detection(self):
        provider = LibreTranslateProvider(['http://localhost:5000'], 0.1, 0.1, 1)
        with patch(
            'traduzedu.services.translation_engine.requests.get',
            side_effect=requests.ConnectionError('offline'),
        ) as get:
            for _ in range(2):
                with self.assertRaisesRegex(TranslationError, 'indisponível'):
                    provider.supports('pt', 'en')
            self.assertEqual(get.call_count, 1)

    def test_expired_deadline_stops_before_a_provider_call(self):
        provider = StubProvider(result='Good morning')
        with self.assertRaisesRegex(TranslationError, 'tempo máximo'):
            TranslationEngine([provider]).translate(
                'Bom dia',
                'pt',
                'en',
                deadline=time.monotonic() - 1,
            )
        self.assertEqual(provider.calls, 0)

    def test_deepl_uses_environment_secret_as_authorization_header(self):
        provider = DeepLProvider(
            'test-secret',
            'https://api-free.deepl.com/v2/translate',
            1,
            1,
            1,
        )
        response = Mock(status_code=200)
        response.json.return_value = {'translations': [{'text': 'Good morning'}]}
        with patch('traduzedu.services.translation_engine.requests.post', return_value=response) as post:
            self.assertEqual(provider.translate('Bom dia', 'pt', 'en'), 'Good morning')
        self.assertEqual(
            post.call_args.kwargs['headers']['Authorization'],
            'DeepL-Auth-Key test-secret',
        )
        self.assertFalse(post.call_args.kwargs['allow_redirects'])

    def test_deepl_rejects_non_https_remote_url(self):
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            DeepLProvider('test-secret', 'http://example.test/translate', 1, 1, 1)

    def test_environment_provider_order_is_configurable(self):
        with patch.dict(
            'os.environ',
            {
                'TRANSLATION_PROVIDERS': 'argos,libretranslate',
                'LIBRETRANSLATE_URL': 'http://localhost:5000',
            },
            clear=False,
        ):
            engine = TranslationEngine.from_environment()
        self.assertEqual(
            [provider.name for provider in engine.providers],
            ['argos', 'libretranslate'],
        )

    def test_argos_model_install_requires_an_explicit_catalog_check(self):
        provider = ArgosProvider()
        with patch.object(provider, '_argos_package') as argos_package:
            with self.assertRaisesRegex(RuntimeError, 'Consulte o catálogo'):
                provider.install_model('pt', 'en')
            argos_package.update_package_index.assert_not_called()

    def test_argos_catalog_check_reports_model_without_downloading_it(self):
        provider = ArgosProvider()
        provider._installed_languages = Mock(return_value=[])
        package = Mock(
            from_code='pt',
            to_code='en',
            package_version='1.9',
            links=['https://models.example/model.argosmodel'],
        )
        with patch.object(provider, '_argos_package') as argos_package:
            argos_package.get_available_packages.return_value = [package]
            result = provider.refresh_catalog('pt', 'en')
        argos_package.update_package_index.assert_called_once_with()
        package.download.assert_not_called()
        self.assertTrue(result['package_available'])
        self.assertFalse(result['installed'])
        self.assertEqual(result['download_host'], 'models.example')

    def test_argos_install_refuses_a_pair_missing_from_the_verified_catalog(self):
        provider = ArgosProvider()
        provider._catalog_checked = True
        provider.supports = Mock(return_value=False)
        provider._available_model = Mock(return_value=None)
        with patch.object(provider, '_argos_package') as argos_package:
            with self.assertRaisesRegex(LookupError, 'Nenhum modelo foi baixado'):
                provider.install_model('fr', 'en')
            argos_package.install_from_path.assert_not_called()

    def test_argos_install_downloads_only_the_verified_requested_model(self):
        provider = ArgosProvider()
        provider._catalog_checked = True
        provider.supports = Mock(side_effect=[False, True, True])
        package = Mock(package_version='1.9', links=['https://models.example/model.argosmodel'])
        package.download.return_value = 'model.argosmodel'
        provider._available_model = Mock(return_value=package)
        with patch.object(provider, '_argos_package') as argos_package:
            result = provider.install_model('pt', 'en')
        package.download.assert_called_once_with()
        argos_package.install_from_path.assert_called_once_with('model.argosmodel')
        self.assertTrue(result['installed'])

    def test_argos_does_not_advertise_models_missing_local_tokenizer_resources(self):
        provider = ArgosProvider()
        with tempfile.TemporaryDirectory() as directory:
            package_path = Path(directory)
            stanza_path = package_path / 'stanza'
            (package_path / 'model').mkdir()
            (stanza_path / 'pt' / 'tokenize').mkdir(parents=True)
            (package_path / 'model' / 'model.bin').write_bytes(b'model')
            (package_path / 'sentencepiece.model').write_bytes(b'tokenizer')
            (stanza_path / 'resources.json').write_text('{}', encoding='utf-8')
            tokenizer = stanza_path / 'pt' / 'tokenize' / 'bosque.pt'
            tokenizer.write_bytes(b'tokenizer')

            model_package = SimpleNamespace(
                package_path=package_path,
                packaged_sbd_path=stanza_path,
            )
            translation = SimpleNamespace(pkg=model_package)
            source = SimpleNamespace(code='pt', get_translation=lambda _target: translation)
            target = SimpleNamespace(code='en', get_translation=lambda _target: None)
            provider._installed_languages = Mock(return_value=[source, target])

            self.assertTrue(provider.supports('pt', 'en'))
            tokenizer.unlink()
            self.assertFalse(provider.supports('pt', 'en'))
            self.assertEqual(provider.status()['pairs'], [])

    def test_installed_argos_models_translate_all_pairs_without_network(self):
        provider = ArgosProvider()
        pairs = [
            ('pt', 'en', 'Bom dia.'),
            ('pt', 'es', 'Bom dia.'),
            ('en', 'pt', 'Good morning.'),
            ('en', 'es', 'Good morning.'),
            ('es', 'pt', 'Buenos días.'),
            ('es', 'en', 'Buenos días.'),
        ]
        missing_pairs = [
            f'{source}->{target}'
            for source, target, _text in pairs
            if not provider.supports(source, target)
        ]
        if missing_pairs:
            self.skipTest(f'Argos models not installed for: {", ".join(missing_pairs)}')

        with patch(
            'requests.sessions.Session.request',
            side_effect=AssertionError('Argos attempted external HTTP while offline'),
        ):
            for source, target, text in pairs:
                with self.subTest(source=source, target=target):
                    translated = provider.translate(text, source, target)
                    self.assertTrue(translated.strip())
                    self.assertLessEqual(len(translated), 500)
                    self.assertNotEqual(translated, text)

    def test_unknown_provider_configuration_fails_clearly(self):
        with patch.dict('os.environ', {'TRANSLATION_PROVIDERS': 'not-a-provider'}):
            with self.assertRaisesRegex(ValueError, 'desconhecidos'):
                TranslationEngine.from_environment()


if __name__ == '__main__':
    unittest.main()
