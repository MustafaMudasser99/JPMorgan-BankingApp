"""v2 payment network HTTP (authorize, register, banks/me)."""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Any, Tuple

from django.conf import settings

from .config_store import current_acquirer_api_key

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 team7-nfc-terminal/1.0"
)


def _ssl_context() -> ssl.SSLContext:
    """Explicit TLS context (matches payment_cards_client); certifi helps some Windows installs."""
    ctx = ssl.create_default_context()
    try:
        import certifi

        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    return ctx


def _urlopen_json(
    req: urllib.request.Request,
    timeout: float,
) -> Tuple[int, dict[str, Any]]:
    ctx = _ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read() or b"{}"
            try:
                data = json.loads(raw.decode())
            except json.JSONDecodeError:
                return resp.status, {
                    "error": "invalid JSON from payment network",
                    "body_preview": raw.decode("utf-8", errors="replace")[:300],
                }
            if not isinstance(data, dict):
                return resp.status, {"error": "unexpected JSON shape from payment network"}
            return resp.status, data
    except urllib.error.HTTPError as e:
        raw = e.read() or b""
        try:
            parsed = json.loads(raw.decode() or "{}")
            if isinstance(parsed, dict):
                return e.code, parsed
        except json.JSONDecodeError:
            pass
        return e.code, {
            "error": str(e),
            "body": raw.decode("utf-8", errors="replace")[:300],
        }
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        msg = f"{type(e).__name__}: {reason}"
        logger.warning("payment network URLError: %s", msg)
        return 502, {"error": msg, "hint": "Check internet, firewall, and TLS (try: pip install certifi)."}
    except Exception as e:
        logger.exception("payment network request failed")
        return 502, {"error": f"network error: {e}"}


def payment_network_url() -> str:
    return getattr(settings, "PAYMENT_NETWORK_URL", "https://paymentsystem-cards-cf.pages.dev").rstrip(
        "/"
    )


def authorize_url() -> str:
    return payment_network_url() + "/api/authorize"


def register_card_url() -> str:
    return payment_network_url() + "/api/cards/register"


def post_charge(amount: float, merchant_id: str, payload: str) -> Tuple[int, dict]:
    parts = payload.split("|")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return 400, {"error": f"invalid card payload: {payload[:80]}"}
    issuing_bank_id, card_number = parts[0], parts[1]

    body = json.dumps(
        {
            "amount": amount,
            "card_number": card_number,
            "merchant_id": merchant_id,
            "issuing_bank_id": issuing_bank_id,
        }
    ).encode()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    api_key = (current_acquirer_api_key() or getattr(settings, "PAYMENT_CARDS_API_KEY", "") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(authorize_url(), data=body, headers=headers, method="POST")
    status, result = _urlopen_json(req, 20.0)
    if not api_key and status in (401, 403):
        result = {
            **result,
            "hint": "Set acquirer X-API-Key in NFC Settings or PAYMENT_CARDS_API_KEY / ACQUIRER_API_KEY.",
        }
    return status, result


def whoami_on_network(api_key: str) -> Tuple[int, dict]:
    headers = {"X-API-Key": api_key, "User-Agent": UA}
    req = urllib.request.Request(
        payment_network_url() + "/api/banks/me", headers=headers, method="GET"
    )
    return _urlopen_json(req, 10.0)


def register_card_on_network(issuer_api_key: str, card_number: str, amount: float) -> Tuple[int, dict]:
    body = json.dumps({"card_number": card_number, "amount": amount}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": issuer_api_key,
        "User-Agent": UA,
    }
    req = urllib.request.Request(register_card_url(), data=body, headers=headers, method="POST")
    return _urlopen_json(req, 15.0)
