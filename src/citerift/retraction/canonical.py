"""Canonical JSON and digests (SPECIFICATION.md section 10.4)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any


def canonical(value: Any) -> str:
    """UTF-8 JSON with sorted keys, compact separators and no NaN or infinity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest(value: Any) -> str:
    return sha256_text(canonical(value))


def digest_lines(lines: Iterable[str]) -> str:
    """SHA-256 over newline-terminated lines, in the order given."""
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()
