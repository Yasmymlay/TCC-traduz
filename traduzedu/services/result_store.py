"""Guarda por um tempo os PDFs traduzidos, para o professor baixar depois."""
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

DEFAULT_TTL_SECONDS = 60 * 60
DEFAULT_MAX_ITEMS = 20


@dataclass
class StoredFile:
    content: bytes
    filename: str
    expires_at: float


class TranslatedFileStore:
    def __init__(self, ttl_seconds=DEFAULT_TTL_SECONDS, max_items=DEFAULT_MAX_ITEMS):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._items = OrderedDict()
        self._lock = Lock()

    def _discard_expired(self, now):
        for key in [key for key, item in self._items.items() if item.expires_at <= now]:
            del self._items[key]

    def save(self, content, filename):
        now = time.monotonic()
        file_id = uuid.uuid4().hex
        with self._lock:
            self._discard_expired(now)
            self._items[file_id] = StoredFile(content, filename, now + self.ttl_seconds)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
        return file_id

    def get(self, file_id):
        with self._lock:
            self._discard_expired(time.monotonic())
            return self._items.get(file_id)


TRANSLATED_FILES = TranslatedFileStore()
