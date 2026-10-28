"""Pinned source receipts and lossless reading of the Retraction Watch CSV (SPECIFICATION.md sections 3, 5)."""

from __future__ import annotations

import codecs
import csv
import hashlib
import io
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from citerift.contracts.formats import loads_strict
from citerift.retraction.canonical import canonical

PARSER_VERSION = "citerift-rw-csv/1.0.0"
FIELD_LIMIT = 1024 * 1024
ROW_LIMIT = 2_000_000
CRITICAL_COLUMNS = (
    "Record ID",
    "RetractionNature",
    "RetractionDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDate",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
)
DEFAULT_RECEIPT = "rw-a987928.json"
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_RECEIPT_KEYS = {
    "receipt_version": str,
    "source_id": str,
    "repository": str,
    "commit": str,
    "path": str,
    "url": str,
    "expected_bytes": int,
    "expected_sha256": str,
    "git_blob_sha1": str,
    "readme_generated_on": str,
    "acquired_at": str,
    "attribution": str,
}


class ImportFailure(Exception):
    """A fatal import failure: no artifact is published (SPECIFICATION.md 5.1)."""

    def __init__(self, code: str, message: str, position: str | None = None):
        super().__init__(f"{code}: {message}" + (f" at {position}" if position else ""))
        self.code = code
        self.message = message
        self.position = position

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "position": self.position}


@dataclass(frozen=True)
class Receipt:
    receipt_version: str
    source_id: str
    repository: str
    commit: str
    path: str
    url: str
    expected_bytes: int
    expected_sha256: str
    git_blob_sha1: str
    readme_generated_on: str
    acquired_at: str
    attribution: str

    @property
    def locator_base(self) -> str:
        return f"{self.repository}/-/blob/{self.commit}/{self.path}"

    def to_json(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in _RECEIPT_KEYS}


def parse_receipt(data: Any) -> Receipt:
    if not isinstance(data, dict) or set(data) != set(_RECEIPT_KEYS):
        raise ImportFailure("RECEIPT_INVALID", f"receipt must have exactly the keys {sorted(_RECEIPT_KEYS)}")
    for key, typ in _RECEIPT_KEYS.items():
        if not isinstance(data[key], typ) or isinstance(data[key], bool):
            raise ImportFailure("RECEIPT_INVALID", f"receipt field {key} must be {typ.__name__}")
    if not _HEX40.fullmatch(data["commit"]) or not _HEX40.fullmatch(data["git_blob_sha1"]):
        raise ImportFailure("RECEIPT_INVALID", "commit and git_blob_sha1 must be 40 lowercase hex digits")
    if not _HEX64.fullmatch(data["expected_sha256"]) or data["expected_bytes"] < 0:
        raise ImportFailure("RECEIPT_INVALID", "expected_sha256 must be 64 lowercase hex digits")
    if not data["url"].startswith("https://") or not data["repository"].startswith("https://"):
        raise ImportFailure("RECEIPT_INVALID", "url and repository must be https URLs")
    return Receipt(**data)


def load_receipt(path: Path | None = None) -> Receipt:
    """Load a receipt file; the default is the pinned snapshot receipt shipped with the package."""
    try:
        if path is None:
            text = resources.files("citerift.retraction").joinpath("receipts", DEFAULT_RECEIPT).read_text("utf-8")
        else:
            text = path.read_text(encoding="utf-8")
        data = loads_strict(text)
    except (OSError, ValueError) as exc:
        raise ImportFailure("RECEIPT_INVALID", str(exc)) from None
    return parse_receipt(data)


@dataclass(frozen=True)
class ByteCheck:
    size: int
    sha256: str
    git_blob_sha1: str
    physical_lines: int


def check_bytes(path: Path, receipt: Receipt) -> ByteCheck:
    """Verify size and hash against the receipt, then strict UTF-8, NUL and CR rules, in one read."""
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise ImportFailure("SOURCE_UNREADABLE", str(exc)) from None
    sha = hashlib.sha256()
    size = 0
    newlines = 0
    last = b""
    nul_at = cr_at = None
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    bad_utf8_at = None
    with handle:
        while chunk := handle.read(1 << 20):
            sha.update(chunk)
            if nul_at is None and (i := chunk.find(b"\x00")) >= 0:
                nul_at = size + i
            if cr_at is None and (i := chunk.find(b"\r")) >= 0:
                cr_at = size + i
            if bad_utf8_at is None:
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError as exc:
                    bad_utf8_at = size + exc.start
            newlines += chunk.count(b"\n")
            size += len(chunk)
            last = chunk[-1:]
    if bad_utf8_at is None:
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            bad_utf8_at = size
    if size != receipt.expected_bytes:
        raise ImportFailure(
            "SOURCE_SIZE_MISMATCH", f"{size} bytes, receipt expects {receipt.expected_bytes}", f"byte {size}"
        )
    if sha.hexdigest() != receipt.expected_sha256:
        raise ImportFailure("SOURCE_HASH_MISMATCH", f"sha256 {sha.hexdigest()}, receipt {receipt.expected_sha256}")
    if bad_utf8_at is not None:
        raise ImportFailure("ENCODING_INVALID", "bytes are not strict UTF-8", f"byte {bad_utf8_at}")
    if nul_at is not None:
        raise ImportFailure("NUL_BYTE", "the file contains a NUL byte", f"byte {nul_at}")
    if cr_at is not None:
        raise ImportFailure("CR_UNSUPPORTED", "the file contains a CR byte", f"byte {cr_at}")
    blob = hashlib.sha1(f"blob {size}\0".encode(), usedforsecurity=False)
    with path.open("rb") as handle2:
        while chunk := handle2.read(1 << 20):
            blob.update(chunk)
    if blob.hexdigest() != receipt.git_blob_sha1:
        raise ImportFailure(
            "SOURCE_HASH_MISMATCH", f"git blob sha1 {blob.hexdigest()}, receipt {receipt.git_blob_sha1}"
        )
    physical = newlines + (1 if size and last != b"\n" else 0)
    return ByteCheck(size, sha.hexdigest(), blob.hexdigest(), physical)


@dataclass(frozen=True)
class RawRecord:
    ordinal: int
    line_start: int
    line_end: int
    fields: tuple[str, ...]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(canonical(list(self.fields)).encode("utf-8")).hexdigest()


@dataclass
class ReadStats:
    header_lines: int = 0
    blank_lines: int = 0
    record_lines: int = 0
    records: int = 0
    physical_lines_seen: int = 0


def read_header(text_stream: io.TextIOBase) -> tuple[list[str], Any, ReadStats]:
    reader = csv.reader(text_stream, strict=True)
    stats = ReadStats()
    try:
        header = next(reader)
    except StopIteration:
        raise ImportFailure("HEADER_MISSING", "the file has no header record") from None
    except csv.Error as exc:
        raise ImportFailure("CSV_STRUCTURE_INVALID", str(exc), "line 1") from None
    stats.header_lines = reader.line_num
    if not header or header == [""]:
        raise ImportFailure("HEADER_MISSING", "the first record is empty", "line 1")
    seen: set[str] = set()
    for name in header:
        if name in seen:
            raise ImportFailure("HEADER_DUPLICATE", f"column {name!r} repeats", "line 1")
        seen.add(name)
    missing = [c for c in CRITICAL_COLUMNS if c not in seen]
    if missing:
        raise ImportFailure("HEADER_CRITICAL_MISSING", f"missing critical columns {missing}", "line 1")
    return header, reader, stats


def iter_records(path: Path) -> tuple[list[str], Iterator[RawRecord], ReadStats]:
    """Open a verified file and return (header, records, stats). Stats are complete once records is exhausted."""
    handle = path.open("r", encoding="utf-8-sig", errors="strict", newline="")
    previous_limit = csv.field_size_limit(FIELD_LIMIT)
    try:
        header, reader, stats = read_header(handle)
    except BaseException:
        csv.field_size_limit(previous_limit)
        handle.close()
        raise

    def generate() -> Iterator[RawRecord]:
        last_line = stats.header_lines
        try:
            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                except csv.Error as exc:
                    code = "FIELD_TOO_LARGE" if "field larger" in str(exc) else "CSV_STRUCTURE_INVALID"
                    raise ImportFailure(code, str(exc), f"line {reader.line_num}") from None
                start, end = last_line + 1, reader.line_num
                last_line = end
                if not row:
                    stats.blank_lines += end - start + 1
                    continue
                stats.records += 1
                stats.record_lines += end - start + 1
                if stats.records > ROW_LIMIT:
                    raise ImportFailure("ROW_LIMIT_EXCEEDED", f"more than {ROW_LIMIT} records", f"line {end}")
                yield RawRecord(stats.records, start, end, tuple(row))
            stats.physical_lines_seen = last_line
        finally:
            csv.field_size_limit(previous_limit)
            handle.close()

    return header, generate(), stats


def receipt_digest(receipt: Receipt) -> str:
    return hashlib.sha256(json.dumps(receipt.to_json(), sort_keys=True).encode("utf-8")).hexdigest()
