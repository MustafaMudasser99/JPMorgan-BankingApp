"""PC/SC NFC read/write (NTAG NDEF text). Requires pyscard on the host."""

from __future__ import annotations

import time
from typing import Optional, Tuple

from django.conf import settings

from . import state

try:
    from smartcard.CardConnection import CardConnection
    from smartcard.Exceptions import CardConnectionException, NoCardException
    from smartcard.System import readers
    from smartcard.util import toHexString

    PYSCARD_AVAILABLE = True
except ImportError:
    PYSCARD_AVAILABLE = False
    readers = None  # type: ignore[misc, assignment]


def tap_timeout() -> float:
    return float(getattr(settings, "NFC_TERMINAL_TAP_TIMEOUT", 30.0))


def _read_block(connection, block: int) -> bytes:
    data, sw1, sw2 = connection.transmit([0xFF, 0xB0, 0x00, block, 0x04])
    if (sw1, sw2) != (0x90, 0x00):
        raise OSError(f"block {block}: status {sw1:02X}{sw2:02X}")
    return bytes(data)


def _write_block(connection, block: int, data: bytes) -> None:
    if len(data) != 4:
        raise ValueError("NTAG block write must be exactly 4 bytes")
    cmd = [0xFF, 0xD6, 0x00, block, 0x04] + list(data)
    _, sw1, sw2 = connection.transmit(cmd)
    if (sw1, sw2) != (0x90, 0x00):
        raise OSError(f"block {block}: status {sw1:02X}{sw2:02X}")


def _build_ndef_text_payload(text: str) -> bytes:
    body = text.encode("utf-8")
    lang = b"en"
    payload = bytes([len(lang) & 0x3F]) + lang + body
    type_field = b"T"
    if len(payload) > 255:
        raise ValueError("payload too large for short record")
    record = bytes([0xD1, len(type_field), len(payload)]) + type_field + payload
    if len(record) < 0xFF:
        tlv = bytes([0x03, len(record)]) + record + bytes([0xFE])
    else:
        tlv = (
            bytes([0x03, 0xFF, (len(record) >> 8) & 0xFF, len(record) & 0xFF])
            + record
            + bytes([0xFE])
        )
    pad = (-len(tlv)) % 4
    return tlv + b"\x00" * pad


def _walk_ndef_text(raw: bytes) -> Optional[str]:
    i = 0
    while i < len(raw):
        t = raw[i]
        if t == 0x00:
            i += 1
            continue
        if t == 0xFE:
            return None
        if t == 0x03:
            i += 1
            if i >= len(raw):
                return None
            if raw[i] == 0xFF and i + 2 < len(raw):
                length = (raw[i + 1] << 8) | raw[i + 2]
                i += 3
            else:
                length = raw[i]
                i += 1
            msg = raw[i : i + length]
            for j in range(len(msg) - 2):
                if msg[j] == 0x54:
                    lang_len = msg[j + 1] & 0x3F
                    blob = msg[j + 2 + lang_len :]
                    blob = blob.split(b"\xFE", 1)[0].rstrip(b"\x00")
                    return blob.decode("utf-8", "replace")
            return None
        i += 2
    return None


def list_readers_safe() -> list:
    if not PYSCARD_AVAILABLE or readers is None:
        return []
    try:
        return readers()
    except Exception:
        return []


def wait_for_tap(timeout: float) -> Tuple[Optional[str], Optional[str]]:
    rs = list_readers_safe()
    if not rs:
        return None, "no PC/SC reader connected (install pyscard and plug in reader)"
    idx = state.get_reader_index()
    if not (0 <= idx < len(rs)):
        idx = 0
    r = rs[idx]
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = r.createConnection()
            c.connect(CardConnection.T1_protocol)
            try:
                atr = c.getATR()
                raw = bytearray()
                for blk in range(4, 40):
                    try:
                        raw.extend(_read_block(c, blk))
                    except OSError:
                        break
                text = _walk_ndef_text(bytes(raw))
            finally:
                c.disconnect()
            if text:
                return text, None
            return None, f"no NDEF text record on tag {toHexString(atr)}"
        except (NoCardException, CardConnectionException):
            time.sleep(0.4)
    return None, "no card tapped within timeout"


def wait_for_program(text: str, timeout: float) -> Tuple[Optional[str], Optional[str]]:
    rs = list_readers_safe()
    if not rs:
        return None, "no PC/SC reader connected (install pyscard and plug in reader)"
    idx = state.get_reader_index()
    if not (0 <= idx < len(rs)):
        idx = 0
    r = rs[idx]
    try:
        ndef = _build_ndef_text_payload(text)
    except ValueError as e:
        return None, f"payload error: {e}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = r.createConnection()
            c.connect(CardConnection.T1_protocol)
            try:
                atr = c.getATR()
                for i in range(0, len(ndef), 4):
                    _write_block(c, 4 + i // 4, ndef[i : i + 4])
                raw = bytearray()
                for blk in range(4, 4 + (len(ndef) // 4) + 4):
                    try:
                        raw.extend(_read_block(c, blk))
                    except OSError:
                        break
                verified = _walk_ndef_text(bytes(raw))
            finally:
                c.disconnect()
            if verified is None:
                return None, f"wrote tag {toHexString(atr)} but could not verify NDEF read-back"
            return verified, None
        except (NoCardException, CardConnectionException):
            time.sleep(0.4)
        except OSError as e:
            return None, f"write failed: {e}"
    return None, "no card tapped within timeout"
