"""Motor de tradução com fallback entre provedores (seção 6.3 da documentação).

A ordem padrão é LibreTranslate (API local), Argos Translate (modelos offline)
e DeepL (API externa opcional). O primeiro provedor que suportar o par de
idiomas e responder corretamente é usado.
"""
import logging
import os
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import requests

from ..models.language import SUPPORTED_LANGS as LANGUAGES

LOGGER = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class UnsupportedLanguagePair(TranslationError):
    pass


class _OfflineStanzaSentencizer:
    def __init__(self, model_package):
        self.pkg = model_package
        self.stanza_lang_code = {'zt': 'zh-hant', 'pb': 'pt'}.get(
            model_package.from_code,
            model_package.from_code,
        )
        self.stanza_pipeline = None

    def lazy_pipeline(self):
        if self.stanza_pipeline is None:
            import stanza

            self.stanza_pipeline = stanza.Pipeline(
                lang=self.stanza_lang_code,
                dir=str(self.pkg.package_path / 'stanza'),
                processors='tokenize',
                use_gpu=False,
                logging_level='WARNING',
                download_method=stanza.DownloadMethod.NONE,
            )
        return self.stanza_pipeline

    def split_sentences(self, text):
        document = self.lazy_pipeline()(text)
        return [sentence.text for sentence in document.sentences]


def _positive_float(name, default, minimum=0.1, maximum=300.0):
    try:
        value = float(os.getenv(name, default))
    except (TypeError, ValueError):
        LOGGER.warning('Invalid %s value; using default %s.', name, default)
        return float(default)
    return min(max(value, minimum), maximum)


def _positive_int(name, default, minimum=1, maximum=5):
    try:
        value = int(os.getenv(name, default))
    except (TypeError, ValueError):
        LOGGER.warning('Invalid %s value; using default %s.', name, default)
        return int(default)
    return min(max(value, minimum), maximum)


class LibreTranslateProvider:
    name = 'libretranslate'

    def __init__(self, urls, connect_timeout, read_timeout, attempts):
        self.urls = [url.rstrip('/') for url in urls if url.strip()]
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.attempts = attempts
        self._languages = None
        self._languages_expires_at = 0
        self._languages_error = None
        self._languages_lock = Lock()

    @staticmethod
    def _remaining_timeout(deadline, connect_timeout, read_timeout):
        if deadline is None:
            return connect_timeout, read_timeout
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TranslationError('O tempo máximo desta tradução foi excedido.')
        return min(connect_timeout, remaining), min(read_timeout, remaining)

    def _load_languages(self, refresh=False):
        with self._languages_lock:
            now = time.monotonic()
            if not refresh and now < self._languages_expires_at:
                if self._languages is not None:
                    return self._languages
                if self._languages_error:
                    raise TranslationError(self._languages_error)

            last_error = None
            for base_url in self.urls:
                try:
                    response = requests.get(
                        f'{base_url}/languages',
                        timeout=(min(self.connect_timeout, 2), min(self.read_timeout, 3)),
                    )
                    if response.status_code != 200:
                        last_error = f'HTTP {response.status_code}'
                        continue
                    payload = response.json()
                    if not isinstance(payload, list):
                        last_error = 'Resposta de idiomas inválida'
                        continue
                    languages = {
                        item.get('code'): {
                            target for target in item.get('targets', [])
                            if isinstance(target, str)
                        }
                        for item in payload
                        if isinstance(item, dict)
                        and isinstance(item.get('code'), str)
                        and isinstance(item.get('targets'), list)
                    }
                    self._languages = languages
                    self._languages_error = None
                    self._languages_expires_at = time.monotonic() + 30
                    return languages
                except (requests.RequestException, ValueError) as exc:
                    last_error = str(exc)
            self._languages = None
            self._languages_error = (
                f'LibreTranslate indisponível: {last_error or "nenhum endpoint configurado"}.'
            )
            self._languages_expires_at = time.monotonic() + 10
            raise TranslationError(self._languages_error)

    def supports(self, source, target):
        languages = self._load_languages()
        return source in languages and target in languages[source]

    def translate(self, text, source, target, deadline=None):
        return self.translate_many([text], source, target, deadline=deadline)[0]

    def translate_many(self, texts, source, target, deadline=None):
        if not texts:
            return []
        if not self.urls:
            raise TranslationError('Nenhum endereço do LibreTranslate foi configurado.')
        if not self.supports(source, target):
            raise UnsupportedLanguagePair(
                f'LibreTranslate não disponibiliza o par {source} → {target}.'
            )

        payload = {
            'q': texts[0] if len(texts) == 1 else texts,
            'source': source,
            'target': target,
            'format': 'text',
        }
        last_error = None
        for base_url in self.urls:
            for attempt in range(self.attempts):
                timeout = self._remaining_timeout(deadline, self.connect_timeout, self.read_timeout)
                try:
                    response = requests.post(
                        f'{base_url}/translate',
                        json=payload,
                        timeout=timeout,
                    )
                    if response.status_code != 200:
                        detail = f'HTTP {response.status_code}'
                        if response.status_code < 500 and response.status_code != 429:
                            raise TranslationError(f'LibreTranslate rejeitou a solicitação ({detail}).')
                        last_error = detail
                        if attempt + 1 < self.attempts:
                            retry_after = response.headers.get('Retry-After', '')
                            try:
                                delay = min(max(float(retry_after), 0), 2)
                            except ValueError:
                                delay = 0.4 * (attempt + 1)
                            time.sleep(delay)
                        continue

                    data = response.json()
                    translated = data.get('translatedText')
                    if translated is None and isinstance(data.get('translations'), list):
                        translated = [
                            item.get('translatedText')
                            for item in data['translations']
                            if isinstance(item, dict)
                        ]
                    if isinstance(translated, str) and len(texts) == 1:
                        translated = [translated]
                    if (
                        not isinstance(translated, list)
                        or len(translated) != len(texts)
                        or any(not isinstance(item, str) or not item.strip() for item in translated)
                    ):
                        raise TranslationError('LibreTranslate retornou uma tradução vazia.')
                    return [item.strip() for item in translated]
                except (requests.Timeout, requests.ConnectionError) as exc:
                    last_error = str(exc)
                    if attempt + 1 < self.attempts:
                        time.sleep(0.4 * (attempt + 1))
                except requests.RequestException as exc:
                    last_error = str(exc)
                except ValueError as exc:
                    last_error = f'Resposta JSON inválida: {exc}'
                    break

        raise TranslationError(f'LibreTranslate falhou: {last_error or "erro de comunicação"}.')

    def status(self):
        try:
            languages = self._load_languages(refresh=True)
            return {
                'name': self.name,
                'status': 'available',
                'pairs': sorted(
                    f'{source}->{target}'
                    for source, targets in languages.items()
                    for target in targets
                ),
            }
        except TranslationError as exc:
            return {'name': self.name, 'status': 'unavailable', 'error': str(exc)}


class ArgosProvider:
    name = 'argos'

    def __init__(self):
        self._catalog_checked = False
        self._model_lock = Lock()
        self._invalid_pairs = set()
        self._invalid_pairs_lock = Lock()
        try:
            from argostranslate import translate as argos_translate
            from argostranslate import package as argos_package
        except ImportError:
            argos_translate = None
            argos_package = None
        self._argos_translate = argos_translate
        self._argos_package = argos_package

    def _installed_languages(self):
        if self._argos_translate is None:
            return []
        return self._argos_translate.get_installed_languages()

    @staticmethod
    def _model_package(translation):
        while translation is not None:
            model_package = getattr(translation, 'pkg', None)
            if model_package is not None:
                return model_package
            translation = getattr(translation, 'underlying', None)
        return None

    @staticmethod
    def _package_translation(translation):
        while translation is not None and getattr(translation, 'underlying', None) is not None:
            translation = translation.underlying
        return translation

    @classmethod
    def _has_local_model_resources(cls, translation, source):
        model_package = cls._model_package(translation)
        if model_package is None or not model_package.package_path:
            return False

        package_path = Path(model_package.package_path)
        stanza_path = Path(model_package.packaged_sbd_path) if model_package.packaged_sbd_path else None
        if stanza_path is None:
            return False
        return (
            (package_path / 'model' / 'model.bin').is_file()
            and any(
                (package_path / name).is_file()
                for name in ('sentencepiece.model', 'bpe.model')
            )
            and (stanza_path / 'resources.json').is_file()
            and any((stanza_path / source / 'tokenize').glob('*.pt'))
        )

    @staticmethod
    def _is_pathological_output(source_text, translated_text):
        translated_text = translated_text.strip()
        if not translated_text:
            return True
        if len(translated_text) > max(500, len(source_text) * 20):
            return True

        prefix = translated_text[:256]
        for width in range(2, min(32, len(prefix) // 8) + 1):
            repeated = translated_text[:width]
            if translated_text.startswith(repeated * 8):
                return True
        return False

    @classmethod
    def _prepare_offline_translation(cls, translation):
        package_translation = cls._package_translation(translation)
        sentencizer = getattr(package_translation, 'sentencizer', None)
        if sentencizer is not None and type(sentencizer).__name__ == 'StanzaSentencizer':
            package_translation.sentencizer = _OfflineStanzaSentencizer(package_translation.pkg)
        return translation

    def _translation_path(self, languages, source, target):
        source_language = next((language for language in languages if language.code == source), None)
        target_language = next((language for language in languages if language.code == target), None)
        if source_language is None or target_language is None:
            return []

        with self._invalid_pairs_lock:
            direct_is_invalid = (source, target) in self._invalid_pairs
        direct = None if direct_is_invalid else source_language.get_translation(target_language)
        paths = (
            [[direct]]
            if direct is not None and self._has_local_model_resources(direct, source)
            else []
        )

        for intermediate in LANGUAGES - {source, target}:
            intermediate_language = next(
                (language for language in languages if language.code == intermediate),
                None,
            )
            if intermediate_language is None:
                continue
            first = source_language.get_translation(intermediate_language)
            second = intermediate_language.get_translation(target_language)
            if (
                first is not None
                and second is not None
                and self._has_local_model_resources(first, source)
                and self._has_local_model_resources(second, intermediate)
            ):
                paths.append([first, second])
        return paths

    def supports(self, source, target):
        languages = self._installed_languages()
        return bool(self._translation_path(languages, source, target))

    def translate(self, text, source, target, deadline=None):
        if deadline is not None and time.monotonic() >= deadline:
            raise TranslationError('O tempo máximo desta tradução foi excedido.')
        languages = self._installed_languages()
        paths = self._translation_path(languages, source, target)
        if not paths:
            raise UnsupportedLanguagePair(f'Argos não tem o par {source} → {target} instalado.')

        failures = []
        for path in paths:
            translated = text
            try:
                for translation in path:
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TranslationError('O tempo máximo desta tradução foi excedido.')
                    self._prepare_offline_translation(translation)
                    translated = translation.translate(translated)
                    if (
                        not isinstance(translated, str)
                        or self._is_pathological_output(text, translated)
                    ):
                        if len(path) == 1 and path[0] is not None:
                            with self._invalid_pairs_lock:
                                self._invalid_pairs.add((source, target))
                            LOGGER.warning(
                                'Argos direct model %s->%s produced invalid output; '
                                'trying an installed local translation path.',
                                source,
                                target,
                            )
                        raise TranslationError('Argos retornou uma saída de tradução inválida.')
                return translated.strip()
            except TranslationError as exc:
                failures.append(str(exc))
        raise TranslationError(
            'Nenhum caminho de tradução Argos produziu um resultado válido. '
            + ' | '.join(failures)
        )

    def status(self):
        try:
            languages = self._installed_languages()
            pairs = []
            for source in languages:
                for target in languages:
                    if (
                        source.code != target.code
                        and self._translation_path(languages, source.code, target.code)
                    ):
                        pairs.append(f'{source.code}->{target.code}')
            return {
                'name': self.name,
                'status': 'available' if pairs else 'unavailable',
                'pairs': sorted(pairs),
            }
        except Exception as exc:
            LOGGER.exception('Could not inspect local Argos packages.')
            return {'name': self.name, 'status': 'unavailable', 'error': str(exc)}

    def model_status(self, source, target):
        languages = self._installed_languages()
        installed_pairs = sorted(
            f'{origin.code}->{destination.code}'
            for origin in languages
            for destination in languages
            if origin.code != destination.code
            and self._translation_path(languages, origin.code, destination.code)
        )
        result = {
            'source': source,
            'target': target,
            'installed_pairs': installed_pairs,
            'installed': self.supports(source, target),
            'catalog_checked': self._catalog_checked,
            'package_available': False,
            'package_version': None,
            'download_host': None,
        }
        if self._catalog_checked and self._argos_package is not None:
            package = self._available_model(source, target)
            if package is not None:
                result.update({
                    'package_available': True,
                    'package_version': package.package_version,
                    'download_host': (
                        urlparse(package.links[0]).hostname
                        if package.links else None
                    ),
                })
        return result

    def _available_model(self, source, target):
        if self._argos_package is None:
            return None
        return next(
            (
                package for package in self._argos_package.get_available_packages()
                if package.from_code == source and package.to_code == target
            ),
            None,
        )

    def refresh_catalog(self, source, target):
        if self._argos_package is None:
            raise RuntimeError('O pacote Argos Translate não está instalado.')
        with self._model_lock:
            self._argos_package.update_package_index()
            self._catalog_checked = True
        return self.model_status(source, target)

    def install_model(self, source, target):
        if self._argos_package is None:
            raise RuntimeError('O pacote Argos Translate não está instalado.')
        if not self._catalog_checked:
            raise RuntimeError(
                'Consulte o catálogo Argos antes de solicitar a instalação do modelo.'
            )
        with self._model_lock:
            if self.supports(source, target):
                return self.model_status(source, target)
            package = self._available_model(source, target)
            if package is None:
                raise LookupError(
                    f'O catálogo Argos não oferece o modelo {source} → {target}. '
                    'Nenhum modelo foi baixado.'
                )
            package_path = package.download()
            self._argos_package.install_from_path(package_path)
            if not self.supports(source, target):
                raise RuntimeError(
                    f'O modelo {source} → {target} foi instalado, mas o par ainda '
                    'não aparece como disponível no Argos.'
                )
        return self.model_status(source, target)


class DeepLProvider:
    name = 'deepl'
    source_codes = {'pt': 'PT', 'en': 'EN', 'es': 'ES'}
    target_codes = {'pt': 'PT-BR', 'en': 'EN-US', 'es': 'ES'}

    def __init__(self, auth_key, api_url, connect_timeout, read_timeout, attempts):
        parsed_url = urlparse(api_url)
        if parsed_url.scheme != 'https' and parsed_url.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('DEEPL_API_URL deve usar HTTPS, exceto para um serviço local.')
        self.auth_key = auth_key
        self.api_url = api_url
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.attempts = attempts

    def supports(self, source, target):
        return bool(self.auth_key) and source in self.source_codes and target in self.target_codes

    def translate(self, text, source, target, deadline=None):
        if not self.auth_key:
            raise TranslationError('DeepL não foi configurado.')
        last_error = None
        payload = {
            'text': [text],
            'source_lang': self.source_codes[source],
            'target_lang': self.target_codes[target],
        }
        for attempt in range(self.attempts):
            timeout = LibreTranslateProvider._remaining_timeout(
                deadline, self.connect_timeout, self.read_timeout
            )
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers={'Authorization': f'DeepL-Auth-Key {self.auth_key}'},
                    timeout=timeout,
                    allow_redirects=False,
                )
                if response.status_code != 200:
                    last_error = f'HTTP {response.status_code}'
                    if response.status_code < 500 and response.status_code != 429:
                        raise TranslationError(f'DeepL rejeitou a solicitação ({last_error}).')
                    if attempt + 1 < self.attempts:
                        time.sleep(0.4 * (attempt + 1))
                    continue
                data = response.json()
                translations = data.get('translations')
                translated = translations[0].get('text') if translations else None
                if not isinstance(translated, str) or not translated.strip():
                    raise TranslationError('DeepL retornou uma tradução vazia.')
                return translated.strip()
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = str(exc)
                if attempt + 1 < self.attempts:
                    time.sleep(0.4 * (attempt + 1))
            except requests.RequestException as exc:
                last_error = str(exc)
            except ValueError as exc:
                last_error = f'Resposta JSON inválida: {exc}'
                break
        raise TranslationError(f'DeepL falhou: {last_error or "erro de comunicação"}.')

    def status(self):
        if not self.auth_key:
            return {'name': self.name, 'status': 'not_configured', 'pairs': []}
        return {
            'name': self.name,
            'status': 'configured',
            'pairs': sorted(
                f'{source}->{target}'
                for source in self.source_codes
                for target in self.target_codes
                if source != target
            ),
        }


class TranslationEngine:
    def __init__(self, providers):
        self.providers = providers

    @classmethod
    def from_environment(cls):
        timeout = _positive_float('TRANSLATION_TIMEOUT_SECONDS', '25', maximum=120)
        attempts = _positive_int('TRANSLATION_RETRIES', '2', maximum=3)
        raw_urls = os.getenv('LIBRETRANSLATE_URL', 'http://localhost:5000,http://127.0.0.1:5000')
        urls = [url.strip() for url in raw_urls.split(',') if url.strip()][:3]
        configured_names = [
            name.strip().lower()
            for name in os.getenv('TRANSLATION_PROVIDERS', 'libretranslate,argos,deepl').split(',')
            if name.strip()
        ]
        constructors = {
            'libretranslate': lambda: LibreTranslateProvider(urls, 3, timeout, attempts),
            'argos': ArgosProvider,
            'deepl': lambda: DeepLProvider(
                os.getenv('DEEPL_AUTH_KEY', ''),
                os.getenv('DEEPL_API_URL', 'https://api-free.deepl.com/v2/translate'),
                3,
                timeout,
                attempts,
            ),
        }
        unknown = set(configured_names) - set(constructors)
        if unknown:
            raise ValueError(f'Provedores de tradução desconhecidos: {", ".join(sorted(unknown))}.')
        return cls([constructors[name]() for name in dict.fromkeys(configured_names)])

    def translate(self, text, source, target, deadline=None):
        return self.translate_many([text], source, target, deadline=deadline)[0]

    def translate_many(self, texts, source, target, deadline=None):
        if not texts:
            return []
        failures = []
        pair_supported = False
        support_check_failed = False
        for provider in self.providers:
            if deadline is not None and time.monotonic() >= deadline:
                raise TranslationError('O tempo máximo desta tradução foi excedido.')
            started_at = time.monotonic()
            try:
                supported = provider.supports(source, target)
                if not supported:
                    failures.append(f'{provider.name}: par de idiomas indisponível')
                    continue
                pair_supported = True
                translate_many = getattr(provider, 'translate_many', None)
                if callable(translate_many):
                    translated = translate_many(
                        texts,
                        source,
                        target,
                        deadline=deadline,
                    )
                else:
                    translated = [
                        provider.translate(text, source, target, deadline=deadline)
                        for text in texts
                    ]
                if (
                    not isinstance(translated, list)
                    or len(translated) != len(texts)
                    or any(not isinstance(item, str) or not item.strip() for item in translated)
                ):
                    raise TranslationError(
                        f'{provider.name} retornou uma quantidade inválida de traduções.'
                    )
                LOGGER.info(
                    'Translation batch completed with provider=%s chunks=%s duration_seconds=%.2f',
                    provider.name,
                    len(texts),
                    time.monotonic() - started_at,
                )
                return translated
            except UnsupportedLanguagePair as exc:
                failures.append(f'{provider.name}: {exc}')
            except Exception as exc:
                if not pair_supported:
                    support_check_failed = True
                LOGGER.warning('Translation provider %s failed: %s', provider.name, exc)
                failures.append(f'{provider.name}: {exc}')

        if not self.providers:
            raise TranslationError('Nenhum mecanismo de tradução está configurado.')
        if not pair_supported and not support_check_failed:
            raise UnsupportedLanguagePair(
                f'Nenhum mecanismo configurado possui o par de idiomas {source} → {target}.'
            )
        raise TranslationError(
            'A tradução não foi concluída. Todos os mecanismos configurados falharam. '
            + ' | '.join(failures)
        )

    def status(self):
        return [provider.status() for provider in self.providers]


ENGINE = TranslationEngine.from_environment()
ARGOS_MODEL_MANAGER = ArgosProvider()


def translate_text(text, source, target, deadline=None):
    return ENGINE.translate(text, source, target, deadline=deadline)


def translate_texts(texts, source, target, deadline=None):
    return ENGINE.translate_many(texts, source, target, deadline=deadline)


def provider_status():
    return ENGINE.status()


def argos_model_status(source, target):
    return ARGOS_MODEL_MANAGER.model_status(source, target)


def refresh_argos_catalog(source, target):
    return ARGOS_MODEL_MANAGER.refresh_catalog(source, target)


def install_argos_model(source, target):
    return ARGOS_MODEL_MANAGER.install_model(source, target)


def configured_endpoints():
    return next(
        (provider.urls for provider in ENGINE.providers if provider.name == 'libretranslate'),
        [],
    )


def configured_provider_names():
    return [provider.name for provider in ENGINE.providers]
