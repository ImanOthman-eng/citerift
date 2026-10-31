"""Canonical JSON, digests and strict JSON reading for Stage 03 records (SPECIFICATION.md 9).

Canonical form: UTF-8, keys sorted, no insignificant whitespace, non-ASCII kept as is, no NaN or infinity.
A digest is the SHA-256 of the canonical form of an object that does not contain the digest itself.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class StrictJSONError(ValueError):
    """A JSON text that CITERIFT refuses: duplicate keys, NaN or infinity, or unreadable."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictJSONError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def _no_constant(name: str) -> Any:
    raise StrictJSONError(f"non-finite number {name} is not allowed")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise StrictJSONError(f"number {text[:40]} is not finite")
    return value


def _encodable(value: Any) -> None:
    """Strings must be encodable as UTF-8: a JSON escape can write a lone surrogate (\\ud800)."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            try:
                item.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise StrictJSONError("a string holds a lone surrogate") from exc
        elif isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def loads_strict(data: bytes | str) -> Any:
    """Parse JSON, rejecting duplicate keys, NaN/Infinity (also as overflowing numbers such as 1e400), lone
    surrogates and invalid UTF-8."""
    try:
        text = data.decode("utf-8", "strict") if isinstance(data, bytes) else data
        value = json.loads(
            text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant, parse_float=_finite_float
        )
    except StrictJSONError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise StrictJSONError(f"unreadable JSON: {type(exc).__name__}") from exc
    _encodable(value)
    return value


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    return sha256_hex(canonical_bytes(obj))


def pretty_bytes(obj: Any) -> bytes:
    """Readable, deterministic serialization for files people inspect (same content as the canonical form)."""
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")
