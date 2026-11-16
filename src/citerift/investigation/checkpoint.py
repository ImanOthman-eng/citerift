"""External journal checkpoints (owner decision D-052; design ``review/step7/closure/STEP7_D052_CHECKPOINT_DESIGN.md``).

A checkpoint is one canonical JSON object with exactly the fields ``format``, ``format_version``,
``investigation_key``, ``seq`` (the last journal record it covers) and ``journal_digest`` (that record's ``digest``,
which commits to the whole prefix through ``prev``). It holds no time, path, host, user or content excerpt.

It is written to standard output or to a file the user names outside the memory root (``outputs.write_file``), never
into the journal, the investigation directory, the report or any blob. ``compare`` checks a supplied checkpoint
against an opened journal and answers exactly one of ``CHECKPOINT_MATCH``, ``CHECKPOINT_PREFIX_REWRITTEN``,
``CHECKPOINT_TRUNCATED`` or ``CHECKPOINT_KEY_MISMATCH``; ``read`` refuses a malformed checkpoint
(``CHECKPOINT_INVALID``). A journal that fails to open is reported by the open itself, before any comparison.

``STATEMENT`` is the only claim made for it, word for word. No cryptographic dependency is used: SHA-256 from the
standard library and the Stage 04 canonical encoder.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from citerift.investigation.canonical import canon, loads_record
from citerift.investigation.errors import CanonError
from citerift.investigation.fsutil import is_hex64
from citerift.investigation.outputs import OperationError, target, write_file

FORMAT = "citerift-investigation-checkpoint"
FORMAT_VERSION = "1"
FIELDS = ("format", "format_version", "investigation_key", "journal_digest", "seq")
MAX_BYTES = 4096
STATEMENT = (
    "A checkpoint retained outside Investigation Memory can detect rewriting or truncation of the journal prefix it "
    "covers."
)


def make(key: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    last = records[-1]
    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "investigation_key": key,
        "seq": last["seq"],
        "journal_digest": last["digest"],
    }


def encode(value: Mapping[str, Any]) -> bytes:
    return canon(dict(value)) + b"\n"


def _invalid(detail: str) -> OperationError:
    return OperationError("invalid", "CHECKPOINT_INVALID", detail)


def parse(data: bytes) -> dict[str, Any]:
    """A checkpoint from its bytes: the canonical object, optionally followed by one newline."""
    if len(data) > MAX_BYTES:
        raise _invalid(f"larger than {MAX_BYTES} bytes")
    body = data[:-1] if data.endswith(b"\n") else data
    try:
        value = loads_record(body)
    except CanonError as exc:
        raise _invalid(f"not canonical JSON: {exc}") from exc
    if not isinstance(value, dict) or tuple(sorted(value)) != FIELDS:
        raise _invalid(f"the fields must be exactly {', '.join(FIELDS)}")
    if value["format"] != FORMAT or value["format_version"] != FORMAT_VERSION:
        raise _invalid("unknown format or format_version")
    seq = value["seq"]
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        raise _invalid("seq is not a non-negative integer")
    if not is_hex64(value["investigation_key"]) or not is_hex64(value["journal_digest"]):
        raise _invalid("investigation_key and journal_digest must be 64 lowercase hex digits")
    return value


def read(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_BYTES + 1)
    except OSError as exc:
        raise _invalid(f"{path}: {exc.strerror}") from exc
    return parse(data)


def compare(value: Mapping[str, Any], key: str, records: Sequence[Mapping[str, Any]]) -> str:
    """D-052 section 4: the result of comparing a parsed checkpoint with the journal of investigation ``key``."""
    if value["investigation_key"] != key:
        return "CHECKPOINT_KEY_MISMATCH"
    seq = value["seq"]
    if seq >= len(records):
        return "CHECKPOINT_TRUNCATED"
    if records[seq]["digest"] != value["journal_digest"]:
        return "CHECKPOINT_PREFIX_REWRITTEN"
    return "CHECKPOINT_MATCH"


def check_target(out: Path, memory_root: Path, *, overwrite: bool = False) -> None:
    target(out, memory_root, overwrite=overwrite)


def write(out: Path, data: bytes, memory_root: Path, *, overwrite: bool = False) -> None:
    write_file(out, data, memory_root, overwrite=overwrite)
