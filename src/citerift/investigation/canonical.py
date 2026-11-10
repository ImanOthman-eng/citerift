"""Canonical JSON, the tagged hash ``H`` and the derived UUID (MATHEMATICAL_MODEL.md section 2).

``canon(x)`` is ``json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`` encoded
as UTF-8: the encoding Stages 02 and 03 already use, so engine outputs and Stage 04 records share one encoding. The
Stage 03 strict-reading rules are reimplemented here without importing private names (MM 2.1).

Two strict readers (review finding SR-12 of Step 5, owner Step 6 item 3):

- ``loads_record``: a journal record. Every number must be an integer token: ``1.0``, ``1e0``, ``NaN`` and
  ``Infinity`` are refused, never coerced. The bytes must equal the canonical encoding of the parsed value, so a
  different spelling of the same value (spaces, key order, ``\\u00e9`` escapes, ``-0``) is refused too.
- ``loads_blob``: a blob (an engine output). Finite floats are allowed, as MM 2.1 allows them in engine outputs; the
  bytes must still be canonical.

Both refuse duplicate keys, invalid UTF-8, lone surrogates, a byte-order mark and nesting deeper than the bound.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from citerift.investigation.errors import CanonError

MAX_DEPTH = 64


class _Refused(ValueError):
    pass


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _Refused(f"duplicate JSON key {key[:80]!r}")
        out[key] = value
    return out


def _no_constant(name: str) -> Any:
    raise _Refused(f"non-finite number {name} is not allowed")


def _no_float(text: str) -> Any:
    raise _Refused(f"number {text[:40]} is not an integer token")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _Refused(f"number {text[:40]} is not finite")
    return value


def check_value(value: Any, *, allow_float: bool) -> None:
    """Raise CanonError unless ``value`` is in the canonical data model: objects with string keys, arrays, strings
    encodable as UTF-8, integers (and finite floats when allowed), booleans and null, at most MAX_DEPTH levels deep.
    Every value counts as a level, leaves (scalars and object keys) included: the top-level value is level 1."""
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth >= MAX_DEPTH:  # the top-level value is depth 0: at most MAX_DEPTH levels
            raise CanonError("CANON_INVALID", f"nesting deeper than {MAX_DEPTH} levels")
        if item is None or isinstance(item, bool | int):
            continue
        if isinstance(item, float):
            if not allow_float:
                raise CanonError("CANON_INVALID", f"float {item!r} where only integers are allowed")
            if not math.isfinite(item):
                raise CanonError("CANON_INVALID", "NaN or infinity")
            continue
        if isinstance(item, str):
            try:
                item.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise CanonError("CANON_INVALID", "a string holds a lone surrogate") from exc
            continue
        if isinstance(item, dict):
            for key, sub in item.items():
                if not isinstance(key, str):
                    raise CanonError("CANON_INVALID", f"object key {key!r} is not a string")
                stack.append((key, depth + 1))
                stack.append((sub, depth + 1))
            continue
        if isinstance(item, list | tuple):
            stack.extend((sub, depth + 1) for sub in item)
            continue
        raise CanonError("CANON_INVALID", f"type {type(item).__name__} is not JSON")


def canon(value: Any, *, allow_float: bool = False) -> bytes:
    """The canonical bytes of ``value``. Floats are refused unless ``allow_float`` (engine outputs only)."""
    check_value(value, allow_float=allow_float)
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CanonError("CANON_INVALID", str(exc)[:200]) from exc
    return text.encode("utf-8")


def _loads(data: bytes, *, allow_float: bool) -> Any:
    if not isinstance(data, bytes | bytearray | memoryview):
        raise CanonError("JSON_INVALID", "input is not bytes")
    raw = bytes(data)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CanonError("JSON_INVALID", "byte-order mark")
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_constant=_no_constant,
            parse_float=_finite_float if allow_float else _no_float,
        )
    except _Refused as exc:
        raise CanonError("JSON_INVALID", str(exc)) from exc
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise CanonError("JSON_INVALID", f"unreadable JSON: {type(exc).__name__}") from exc
    try:
        again = canon(value, allow_float=allow_float)
    except CanonError as exc:
        raise CanonError("JSON_INVALID", exc.detail) from exc
    if again != raw:
        raise CanonError("JSON_INVALID", "bytes are not the canonical encoding of their value")
    return value


def loads_record(data: bytes) -> Any:
    """Parse one journal record: integer tokens only, canonical bytes only."""
    return _loads(data, allow_float=False)


def loads_blob(data: bytes) -> Any:
    """Parse one blob: finite floats allowed, canonical bytes only."""
    return _loads(data, allow_float=True)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def H(tag: str, *values: Any) -> str:
    """``H(tag, x1, …, xn) = hex(SHA-256(canon([tag, x1, …, xn])))`` (MM 2.2). Stage 04 hashes hold no floats."""
    if not isinstance(tag, str) or not tag:
        raise CanonError("CANON_INVALID", "a hash tag must be a non-empty string")
    return sha256_hex(canon([tag, *values]))


def uuid_from_key(key: str) -> str:
    """The v1 ``investigation_id`` derived from an investigation key (MM 2.3, UUIDv8)."""
    b = bytearray(hashlib.sha256(canon(["citerift-investigation-uuid/1", key])).digest()[:16])
    b[6] = (b[6] & 0x0F) | 0x80
    b[8] = (b[8] & 0x3F) | 0x80
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
