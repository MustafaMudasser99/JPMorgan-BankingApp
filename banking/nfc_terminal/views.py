"""Django views mirroring local-terminal.py HTTP API (+ session auth + CSRF)."""

from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from banking.models import Account, Business, Transaction

from . import nfc_ops, network_client, state
from .config_store import config_path_display, current_acquirer_api_key, load_config, save_config


def _json_body(request) -> dict[str, Any] | None:
    try:
        raw = json.loads(request.body.decode() or "{}")
        return raw if isinstance(raw, dict) else None
    except json.JSONDecodeError:
        return None


def _effective_acquirer_key() -> str:
    return (current_acquirer_api_key() or getattr(settings, "PAYMENT_CARDS_API_KEY", "") or "").strip()


@login_required
@require_GET
def terminal_page(request):
    accounts = Account.objects.filter(user=request.user).order_by("name")
    if not nfc_ops.PYSCARD_AVAILABLE:
        return render(request, "banking/nfc/pyscard_missing.html")
    return render(request, "banking/nfc/terminal.html", {"accounts": accounts})


@login_required
@require_GET
def program_page(request):
    if not nfc_ops.PYSCARD_AVAILABLE:
        return render(request, "banking/nfc/pyscard_missing.html")
    return render(request, "banking/nfc/program.html")


@login_required
@require_GET
def config_page(request):
    return render(
        request,
        "banking/nfc/config.html",
        {"initial_acquirer_api_key": _effective_acquirer_key()},
    )


@login_required
@require_GET
def readers_list(request):
    rs = [str(r) for r in nfc_ops.list_readers_safe()]
    idx = state.get_reader_index()
    return JsonResponse({"readers": rs, "selected": idx})


@login_required
@require_http_methods(["POST"])
def select_reader(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=400)
    idx = body.get("index")
    rs = nfc_ops.list_readers_safe()
    if not isinstance(idx, int) or idx < 0 or idx >= len(rs):
        return JsonResponse(
            {"error": "index out of range", "available": [str(r) for r in rs]},
            status=400,
        )
    state.set_reader_index(idx)
    return JsonResponse({"selected": idx, "name": str(rs[idx])})


@login_required
@require_http_methods(["POST"])
def charge(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=400)
    amount = body.get("amount")
    merchant_id = body.get("merchant_id") or "TestTeam"
    from_account_raw = body.get("from_account") or body.get("from_account_id")
    if not isinstance(amount, (int, float)) or amount <= 0:
        return JsonResponse({"error": "amount must be a positive number"}, status=400)
    if not from_account_raw:
        return JsonResponse(
            {"error": "from_account is required (UUID of the account to debit in this app)"},
            status=400,
        )
    try:
        aid = UUID(str(from_account_raw))
    except ValueError:
        return JsonResponse({"error": "from_account must be a valid UUID"}, status=400)
    try:
        account = Account.objects.get(id=aid, user=request.user)
    except Account.DoesNotExist:
        return JsonResponse({"error": "Account not found"}, status=404)

    amt_dec = Decimal(str(amount))
    if account.get_balance() < amt_dec:
        return JsonResponse({"error": "Insufficient funds in the selected account"}, status=400)

    if not nfc_ops.PYSCARD_AVAILABLE:
        return JsonResponse({"error": "pyscard not installed"}, status=503)

    payload, err = nfc_ops.wait_for_tap(nfc_ops.tap_timeout())
    if err:
        return JsonResponse({"error": err}, status=400)
    status, result = network_client.post_charge(float(amount), str(merchant_id), payload)
    resp_body: dict[str, Any] = {"card": payload, "result": result}
    if status >= 400:
        err = result.get("error") if isinstance(result, dict) else None
        if err:
            resp_body["error"] = err
        return JsonResponse(resp_body, status=status)

    auth_status = result.get("status") if isinstance(result, dict) else None
    if auth_status == "authorized":
        mid = str(merchant_id)[:50]
        with db_transaction.atomic():
            business, _ = Business.objects.get_or_create(
                id=mid,
                defaults={"name": str(merchant_id), "category": "nfc_pos"},
            )
            tx = Transaction.objects.create(
                transaction_type="payment",
                amount=amt_dec,
                from_account=account,
                to_account=None,
                business=business,
                status="completed",
            )
        resp_body["local_transaction_id"] = str(tx.id)
    return JsonResponse(resp_body, status=status)


@login_required
@require_GET
def config_state(request):
    cfg = load_config()
    cfg_key = (cfg.get("acquirer_api_key") or "").strip() if isinstance(cfg.get("acquirer_api_key"), str) else ""
    env_key = os.environ.get("ACQUIRER_API_KEY") or ""
    django_key = (getattr(settings, "PAYMENT_CARDS_API_KEY", "") or "").strip()
    effective = _effective_acquirer_key()
    if cfg_key:
        source = "config"
    elif env_key.strip():
        source = "env"
    elif django_key:
        source = "django_settings"
    else:
        source = "unset"
    return JsonResponse(
        {
            "acquirer_api_key": effective,
            "source": source,
            "payment_network_url": network_client.payment_network_url(),
            "authorize_url": network_client.authorize_url(),
            "register_card_url": network_client.register_card_url(),
            "config_path": config_path_display(),
        }
    )


@login_required
@require_http_methods(["POST"])
def config_save(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=400)
    key = (body.get("acquirer_api_key") or "").strip()
    cfg = load_config()
    if key:
        cfg["acquirer_api_key"] = key
    else:
        cfg.pop("acquirer_api_key", None)
    try:
        save_config(cfg)
    except OSError as e:
        return JsonResponse({"error": f"could not save config: {e}"}, status=500)
    return JsonResponse({"status": "ok", "acquirer_api_key": key})


@login_required
@require_GET
def program_state(request):
    cfg = load_config()
    return JsonResponse(
        {
            "last_bank_id": cfg.get("last_bank_id", ""),
            "default_amount": cfg.get("default_amount", 10),
            "issuer_api_keys": cfg.get("issuer_api_keys", {}),
        }
    )


@login_required
@require_http_methods(["POST"])
def program_card(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=400)
    if not nfc_ops.PYSCARD_AVAILABLE:
        return JsonResponse({"error": "pyscard not installed", "stage": "validation"}, status=503)

    bank_id = (body.get("bank_id") or "").strip()
    account_number = (body.get("account_number") or "").strip()
    issuer_api_key = (body.get("issuer_api_key") or "").strip()
    amount = body.get("amount")

    if not re.match(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        bank_id,
    ):
        return JsonResponse({"error": "bank_id must be a UUID", "stage": "validation"}, status=400)
    if not re.match(r"^\d{1,16}$", account_number):
        return JsonResponse(
            {"error": "account_number must be up to 16 digits", "stage": "validation"},
            status=400,
        )
    if not issuer_api_key:
        return JsonResponse({"error": "issuer_api_key is required", "stage": "validation"}, status=400)
    if not isinstance(amount, (int, float)) or amount <= 0 or amount > 10:
        return JsonResponse({"error": "amount must be £0.01–£10", "stage": "validation"}, status=400)

    account_number = account_number.zfill(16)
    payload = f"{bank_id}|{account_number}"

    who_status, who_body = network_client.whoami_on_network(issuer_api_key)
    if who_status != 200:
        return JsonResponse(
            {
                "error": who_body.get("error")
                or f"could not verify issuer api_key (HTTP {who_status})",
                "stage": "verify_issuer",
                "whoami_status": who_status,
            },
            status=401,
        )
    actual_bank_id = who_body.get("id")
    if actual_bank_id != bank_id:
        return JsonResponse(
            {
                "error": (
                    f"issuer_api_key belongs to bank {actual_bank_id} "
                    f"({who_body.get('name')!r}), not the pasted bank {bank_id}. "
                    "Paste the matching bank, or supply the correct bank's api_key."
                ),
                "stage": "verify_issuer",
                "expected_bank_id": bank_id,
                "actual_bank_id": actual_bank_id,
                "actual_bank_name": who_body.get("name"),
            },
            status=400,
        )

    reg_status, reg_body = network_client.register_card_on_network(
        issuer_api_key, account_number, float(amount)
    )
    already = False
    if reg_status == 201:
        pass
    elif reg_status == 409:
        already = True
    else:
        code = reg_status if 400 <= reg_status < 600 else 502
        return JsonResponse(
            {
                "error": reg_body.get("error") or f"register failed (HTTP {reg_status})",
                "stage": "register",
                "register_status": reg_status,
                "register_body": reg_body,
            },
            status=code,
        )

    verified, err = nfc_ops.wait_for_program(payload, nfc_ops.tap_timeout())
    if err:
        return JsonResponse(
            {
                "error": err,
                "stage": "tag_write",
                "registration": {"already": already, "status": reg_status, "body": reg_body},
            },
            status=400,
        )

    cfg = load_config()
    cfg["last_bank_id"] = bank_id
    cfg["default_amount"] = float(amount)
    keys = cfg.get("issuer_api_keys")
    if not isinstance(keys, dict):
        keys = {}
    keys[bank_id] = issuer_api_key
    cfg["issuer_api_keys"] = keys
    try:
        save_config(cfg)
    except OSError:
        pass

    return JsonResponse(
        {
            "verified": verified,
            "payload": payload,
            "registration": {"already": already, "status": reg_status, "body": reg_body},
        }
    )
