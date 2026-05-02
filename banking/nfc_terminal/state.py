"""Thread-safe selected PC/SC reader index."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_selected_reader_index = 0


def get_reader_index() -> int:
    with _lock:
        return _selected_reader_index


def set_reader_index(idx: int) -> None:
    global _selected_reader_index
    with _lock:
        _selected_reader_index = idx
