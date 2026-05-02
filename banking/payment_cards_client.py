"""
HTTP client for the external payment-system cards API (server-side only).
"""
from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

# Cloudflare may block urllib's default User-Agent; use a neutral server client string.
_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; Team7BankingApp/1.0; +https://example.invalid; "
    "payment-cards integration)"
)

# Some payment-system paths (e.g. GET /api/transactions) return CF 1010 without a browser-like UA.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Team7BankingApp/1.0"
)


class PaymentCardsAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {
        "Accept": "application/json",
        "User-Agent": getattr(
            settings,
            "PAYMENT_CARDS_HTTP_USER_AGENT",
            _DEFAULT_UA,
        ),
    }
    if extra:
        h.update(extra)
    return h


def _read_json_response(req: Request, timeout: float) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode()
    except HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        raise PaymentCardsAPIError(
            detail or f"HTTP {e.code}",
            status_code=e.code,
        ) from e
    except URLError as e:
        raise PaymentCardsAPIError(str(e.reason or e)) from e

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise PaymentCardsAPIError("Invalid JSON from payment cards API") from e

    if not isinstance(data, dict):
        raise PaymentCardsAPIError("Unexpected response shape from payment cards API")
    return data


def _read_json_array_response(req: Request, timeout: float) -> list[dict[str, Any]]:
    ctx = ssl.create_default_context()
    try:
        try:
            import certifi

            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode()
    except HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        raise PaymentCardsAPIError(
            detail or f"HTTP {e.code}",
            status_code=e.code,
        ) from e
    except URLError as e:
        raise PaymentCardsAPIError(str(e.reason or e)) from e

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise PaymentCardsAPIError("Invalid JSON from payment cards API") from e

    if not isinstance(data, list):
        raise PaymentCardsAPIError("Unexpected response shape from payment cards API (expected list)")
    out: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            out.append(item)
    return out


def fetch_cards_me(timeout: float = 15.0) -> dict[str, Any]:
    """
    GET /api/cards/me — bank budget summary and all cards (requires X-API-Key).
    """
    base = str(getattr(settings, "PAYMENT_CARDS_API_BASE", "")).rstrip("/")
    api_key = getattr(settings, "PAYMENT_CARDS_API_KEY", "") or ""
    if not base or not api_key:
        raise PaymentCardsAPIError("Payment cards API is not configured", status_code=None)

    url = f"{base}/cards/me"
    req = Request(url, headers=_request_headers({"X-API-Key": api_key}))
    return _read_json_response(req, timeout)


def fetch_card_public(bank_id: str, card_number: str, timeout: float = 15.0) -> dict[str, Any]:
    """
    GET /api/cards/<bank_id>/<card_number> — single card (no API key).
    """
    base = str(getattr(settings, "PAYMENT_CARDS_API_BASE", "")).rstrip("/")
    if not base:
        raise PaymentCardsAPIError("Payment cards API is not configured", status_code=None)

    bank_id = bank_id.strip()
    card_number = card_number.strip()
    if not bank_id or not card_number:
        raise PaymentCardsAPIError("bank_id and card_number are required", status_code=None)

    url = f"{base}/cards/{bank_id}/{card_number}"
    req = Request(url, headers=_request_headers())
    return _read_json_response(req, timeout)


def fetch_bank_transactions(timeout: float = 25.0) -> list[dict[str, Any]]:
    """
    GET /api/transactions — all authorization events for the bank (requires X-API-Key).
    Uses a browser-like User-Agent (Cloudflare may block otherwise).
    """
    base = str(getattr(settings, "PAYMENT_CARDS_API_BASE", "")).rstrip("/")
    api_key = getattr(settings, "PAYMENT_CARDS_API_KEY", "") or ""
    if not base or not api_key:
        raise PaymentCardsAPIError("Payment cards API is not configured", status_code=None)

    url = f"{base}/transactions"
    headers = _request_headers({"X-API-Key": api_key})
    headers["User-Agent"] = getattr(settings, "PAYMENT_CARDS_HTTP_USER_AGENT", _BROWSER_UA)
    req = Request(url, headers=headers)
    return _read_json_array_response(req, timeout)
