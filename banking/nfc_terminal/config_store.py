"""Persist acquirer key, issuer keys, and program defaults (same shape as local-terminal)."""

from __future__ import annotations

import json
import os
from typing import Any

from django.conf import settings


def config_path() -> str:
    return getattr(
        settings,
        "NFC_TERMINAL_CONFIG_PATH",
        os.path.expanduser("~/.team7-banking-terminal/config.json"),
    )


def load_config() -> dict[str, Any]:
    path = config_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(cfg: dict[str, Any]) -> None:
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, path)


def current_acquirer_api_key() -> str:
    """Settings file takes precedence; ACQUIRER_API_KEY env seeds default."""
    val = load_config().get("acquirer_api_key")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return os.environ.get("ACQUIRER_API_KEY") or ""
