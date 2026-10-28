"""Independent streaming oracle for the Stage 02 Retraction Data Engine (RDE).

Derived only from docs/verification/stage-02/SPECIFICATION.md sections 5, 6 and 10.3; it shares no code with
src/citerift/retraction. It reads the Retraction Watch CSV once and writes, for every valid DOI and PMID key,
the 1-based ordinals of accepted records that hold the key in the original role and in the notice role (a notice
occurrence equal to the same record's original key of that scheme is not listed as a notice, spec 10.3 step 2).
It also writes record accounting, quarantined ordinals, invalid identifier counts and a list of keys verified to
be absent from both roles, which a lookup must answer with ``no_record``.

Run: python simulations/stage02/oracle_stream.py --csv data/raw/rw/retraction_watch.csv --out OUT.json

Standard library only. Exit code 0 on success, 2 on a fatal import failure (spec 5.1; no output is written).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

# Trimmed outer whitespace: whitespace that is not a control, plus tab, LF and CR (spec 16, C-18).
OUTER_SPACE = "".join(
    chr(i) for i in range(0x110000) if chr(i).isspace() and (unicodedata.category(chr(i)) != "Cc" or chr(i) in "\t\n\r")
)
ORACLE_VERSION = "citerift-rde-oracle-stream/1.0.0"

FIELD_LIMIT = 1 << 20  # 1 MiB (spec 5.1 FIELD_TOO_LARGE)
ROW_LIMIT = 2_000_000  # spec 5.1 ROW_LIMIT_EXCEEDED
DOI_MAX_LENGTH = 512

NATURES = frozenset({"Retraction", "Expression of concern", "Correction", "Reinstatement"})
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
# (scheme, role, column)
ID_FIELDS = (
    ("doi", "original", "OriginalPaperDOI"),
    ("doi", "notice", "RetractionDOI"),
    ("pmid", "original", "OriginalPaperPubMedID"),
    ("pmid", "notice", "RetractionPubMedID"),
)

DOI_SENTINELS = frozenset({"unavailable", "Unavailable"})
FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zs", "Zl", "Zp"})
DOI_SYNTAX = re.compile(r"10\.[0-9]{4,9}(?:\.[0-9]+)*/.+", re.DOTALL)
DOI_HOSTS = frozenset({"doi.org", "dx.doi.org"})
HEX = frozenset("0123456789abcdefABCDEF")
ASCII_DIGITS = frozenset("0123456789")
_ASCII_FOLD = {code: code + 32 for code in range(ord("A"), ord("Z") + 1)}

# Status values returned by the normalizers.
VALID = "valid"
MISSING = "missing"
INVALID = "invalid"


class FatalImportError(Exception):
    """A spec 5.1 failure: no artifact is published."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def ascii_lower(text: str) -> str:
    """Map ASCII A-Z to a-z and nothing else (spec 6.1 step 5)."""
    return text.translate(_ASCII_FOLD)


def _percent_decode_strict(path: str) -> str | None:
    """Decode %XX escapes exactly once as strict UTF-8; None when an escape or the byte sequence is invalid."""
    out = bytearray()
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == "%":
            pair = path[i + 1 : i + 3]
            if len(pair) != 2 or pair[0] not in HEX or pair[1] not in HEX:
                return None
            out.append(int(pair, 16))
            i += 3
        else:
            out.extend(ch.encode("utf-8", "surrogatepass"))
            i += 1
    try:
        return out.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None


def _validate_doi(candidate: str) -> tuple[str | None, str, str]:
    if len(candidate) > DOI_MAX_LENGTH:
        return None, INVALID, "DOI_TOO_LONG"
    for ch in candidate:
        category = unicodedata.category(ch)
        if category in FORBIDDEN_CATEGORIES:
            reason = {"Cc": "DOI_CONTAINS_CONTROL", "Cf": "DOI_CONTAINS_FORMAT_CHARACTER"}.get(
                category, "DOI_CONTAINS_WHITESPACE" if category[0] == "Z" else "DOI_CONTAINS_SURROGATE"
            )
            return None, INVALID, reason
    if not DOI_SYNTAX.fullmatch(candidate):
        return None, INVALID, "DOI_SYNTAX_INVALID"
    return ascii_lower(candidate), VALID, ""


def normalize_doi(raw: str) -> tuple[str | None, str, str]:
    """Return (key or None, status, reason) for a source DOI field (spec 6.1)."""
    text = raw.strip(OUTER_SPACE)
    if text == "":
        return None, MISSING, "DOI_EMPTY"
    if text in DOI_SENTINELS:
        return None, MISSING, "DOI_SENTINEL_UNAVAILABLE"
    folded_head = ascii_lower(text[:8])
    if folded_head.startswith("doi:"):
        rest = text[4:]
        if not rest.startswith("10."):
            return None, INVALID, "DOI_PREFIX_INVALID"
        return _validate_doi(rest)
    for scheme in ("https://", "http://"):
        if folded_head.startswith(scheme):
            rest = text[len(scheme) :]
            cut = len(rest)
            for sep in "/?#":
                pos = rest.find(sep)
                if pos != -1:
                    cut = min(cut, pos)
            authority, remainder = rest[:cut], rest[cut:]
            if "@" in authority or ":" in authority:
                return None, INVALID, "DOI_URL_SHAPE_INVALID"
            if ascii_lower(authority) not in DOI_HOSTS:
                return None, INVALID, "DOI_URL_HOST_INVALID"
            if not remainder.startswith("/") or "?" in remainder or "#" in remainder:
                return None, INVALID, "DOI_URL_SHAPE_INVALID"
            decoded = _percent_decode_strict(remainder[1:])
            if decoded is None:
                return None, INVALID, "DOI_PERCENT_ENCODING_INVALID"
            return _validate_doi(decoded)
    return _validate_doi(text)


def _classify_pmid_digits(text: str) -> tuple[str | None, str, str]:
    if text == "":
        return None, MISSING, "PMID_EMPTY"
    if all(ch in ASCII_DIGITS for ch in text):
        if set(text) == {"0"}:
            return None, MISSING, "PMID_ZERO_SENTINEL"
        if text[0] == "0":
            return None, INVALID, "PMID_LEADING_ZERO"
        if len(text) > 9:
            return None, INVALID, "PMID_TOO_LONG"
        return text, VALID, ""
    if all(unicodedata.decimal(ch, None) is not None for ch in text):
        return None, INVALID, "PMID_NON_ASCII_DIGIT"
    return None, INVALID, "PMID_NOT_INTEGER"


def normalize_pmid(raw: str) -> tuple[str | None, str, str]:
    """Return (key or None, status, reason) for a source PMID field (spec 6.2)."""
    text = raw.strip(OUTER_SPACE)
    folded_head = ascii_lower(text[:8])
    for scheme in ("https://", "http://"):
        if folded_head.startswith(scheme):
            rest = text[len(scheme) :]
            slash = rest.find("/")
            if slash == -1:
                return None, INVALID, "PMID_URL_INVALID"
            host, path = ascii_lower(rest[:slash]), rest[slash:]
            digits: str | None = None
            if host == "pubmed.ncbi.nlm.nih.gov":
                body = path[1:]
                if body.endswith("/"):
                    body = body[:-1]
                digits = body
            elif host == "www.ncbi.nlm.nih.gov" and path.startswith("/pubmed/"):
                digits = path[len("/pubmed/") :]
            if not digits or not all(ch in ASCII_DIGITS for ch in digits):
                return None, INVALID, "PMID_URL_INVALID"
            key, status, reason = _classify_pmid_digits(digits)
            if status == MISSING:  # a URL naming PMID 0 is not the README's blank-or-0 sentinel
                return None, INVALID, "PMID_URL_INVALID"
            return key, status, reason
    return _classify_pmid_digits(text)


class _HashingReader(io.RawIOBase):
    """Binary pass-through that hashes and counts bytes and refuses NUL, so the file is read exactly once."""

    def __init__(self, raw: io.BufferedReader) -> None:
        self._raw = raw
        self.sha256 = hashlib.sha256()
        self.size = 0
        self._last = b""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        view = memoryview(buffer)
        data = self._raw.read(len(view))
        if not data:
            if self._last == b"\r":
                raise FatalImportError("CSV_STRUCTURE_INVALID", "bare CR at end of file")
            return 0
        if b"\x00" in data:
            raise FatalImportError("NUL_BYTE", f"near byte {self.size + data.index(b'\x00')}")
        joined = self._last + data
        if b"\r" in joined.replace(b"\r\n", b""):
            cr = joined.replace(b"\r\n", b"  ").index(b"\r")
            if cr != len(joined) - 1:  # a CR at the very end of a chunk is judged with the next chunk
                raise FatalImportError("CSV_STRUCTURE_INVALID", f"bare CR near byte {self.size - len(self._last) + cr}")
        self._last = data[-1:]
        self.sha256.update(data)
        self.size += len(data)
        view[: len(data)] = data
        return len(data)


def _new_roles() -> dict[str, list[int]]:
    return {"original": [], "notice": []}


def stream(csv_path: Path) -> dict[str, Any]:
    """Read the CSV once and return the oracle result (without absent keys)."""
    csv.field_size_limit(FIELD_LIMIT)
    try:
        binary = open(csv_path, "rb")  # noqa: SIM115 - closed via the text wrapper below
    except OSError as exc:
        raise FatalImportError("SOURCE_UNREADABLE", str(exc)) from exc
    hashing = _HashingReader(binary)
    text = io.TextIOWrapper(io.BufferedReader(hashing), encoding="utf-8-sig", errors="strict", newline="")
    roles: dict[str, dict[str, dict[str, list[int]]]] = {"doi": {}, "pmid": {}}
    invalid_counts = {column: 0 for _, _, column in ID_FIELDS}
    invalid_reasons: dict[str, dict[str, int]] = {column: {} for _, _, column in ID_FIELDS}
    notice_equals_original = {"doi": 0, "pmid": 0}
    quarantined: list[int] = []
    quarantine_reasons: dict[str, int] = {}
    nature_counts: dict[str, int] = {}
    records = accepted = blank_lines = header_lines = span_total = 0
    header: list[str] | None = None
    try:
        with text:
            reader = csv.reader(text, strict=True)
            index: dict[str, int] = {}
            before = 0
            for row in reader:
                span = reader.line_num - before
                before = reader.line_num
                if not row:
                    blank_lines += span
                    continue
                for field in row:
                    if len(field) > FIELD_LIMIT // 4 and len(field.encode("utf-8")) > FIELD_LIMIT:
                        raise FatalImportError("FIELD_TOO_LARGE", f"line {reader.line_num}")
                if header is None:
                    header = row
                    header_lines = span
                    if len(set(header)) != len(header):
                        raise FatalImportError("HEADER_DUPLICATE")
                    missing = [name for name in CRITICAL_COLUMNS if name not in header]
                    if missing:
                        raise FatalImportError("HEADER_CRITICAL_MISSING", ", ".join(missing))
                    index = {name: i for i, name in enumerate(header)}
                    continue
                records += 1
                span_total += span
                if records > ROW_LIMIT:
                    raise FatalImportError("ROW_LIMIT_EXCEEDED")
                ordinal = records
                if len(row) != len(header):
                    quarantined.append(ordinal)
                    quarantine_reasons["FIELD_COUNT_MISMATCH"] = quarantine_reasons.get("FIELD_COUNT_MISMATCH", 0) + 1
                    continue
                nature = row[index["RetractionNature"]]
                if nature not in NATURES:
                    reason = "EVENT_TYPE_MISSING" if nature == "" else "EVENT_TYPE_UNKNOWN"
                    quarantined.append(ordinal)
                    quarantine_reasons[reason] = quarantine_reasons.get(reason, 0) + 1
                    continue
                accepted += 1
                nature_counts[nature] = nature_counts.get(nature, 0) + 1
                keys: dict[tuple[str, str], str] = {}
                for scheme, role, column in ID_FIELDS:
                    normalizer = normalize_doi if scheme == "doi" else normalize_pmid
                    key, status, reason = normalizer(row[index[column]])
                    if status == INVALID:
                        invalid_counts[column] += 1
                        invalid_reasons[column][reason] = invalid_reasons[column].get(reason, 0) + 1
                    elif key is not None:
                        keys[(scheme, role)] = key
                for scheme in ("doi", "pmid"):
                    original = keys.get((scheme, "original"))
                    notice = keys.get((scheme, "notice"))
                    table = roles[scheme]
                    if original is not None:
                        table.setdefault(original, _new_roles())["original"].append(ordinal)
                    if notice is not None:
                        if notice == original:
                            notice_equals_original[scheme] += 1
                        else:
                            table.setdefault(notice, _new_roles())["notice"].append(ordinal)
            physical_lines = reader.line_num
    except UnicodeDecodeError as exc:
        raise FatalImportError("ENCODING_INVALID", str(exc)) from exc
    except csv.Error as exc:
        message = str(exc)
        code = "FIELD_TOO_LARGE" if "field larger than field limit" in message else "CSV_STRUCTURE_INVALID"
        raise FatalImportError(code, message) from exc
    if header is None:
        raise FatalImportError("HEADER_MISSING")
    if records != accepted + len(quarantined) or physical_lines != header_lines + span_total + blank_lines:
        raise FatalImportError("ACCOUNTING_MISMATCH")
    for table in roles.values():
        for entry in table.values():
            entry["original"].sort()
            entry["notice"].sort()
    return {
        "oracle_version": ORACLE_VERSION,
        "source": {"bytes": hashing.size, "sha256": hashing.sha256.hexdigest()},
        "records": records,
        "accepted": accepted,
        "quarantined": quarantined,
        "quarantine_reasons": quarantine_reasons,
        "nature_counts": nature_counts,
        "physical_lines": physical_lines,
        "blank_lines": blank_lines,
        "invalid_identifiers": invalid_counts,
        "invalid_identifier_reasons": invalid_reasons,
        "notice_equals_original": notice_equals_original,
        "doi": roles["doi"],
        "pmid": roles["pmid"],
    }


def _is_fresh_doi(candidate: str, present: dict[str, Any], chosen: dict[str, None]) -> bool:
    key, status, _ = normalize_doi(candidate)
    return status == VALID and key == candidate and candidate not in present and candidate not in chosen


def _is_fresh_pmid(candidate: str, present: dict[str, Any], chosen: dict[str, None]) -> bool:
    key, status, _ = normalize_pmid(candidate)
    return status == VALID and key == candidate and candidate not in present and candidate not in chosen


def absent_keys(result: dict[str, Any]) -> dict[str, list[str]]:
    """Deterministic DOI and PMID keys that are valid, idempotent and absent from both roles of this file."""
    dois: dict[str, Any] = result["doi"]
    pmids: dict[str, Any] = result["pmid"]
    absent_doi: dict[str, None] = {}
    for i in range(1, 1001):
        candidate = f"10.5555/oracle-absent-{i:06d}"
        if _is_fresh_doi(candidate, dois, absent_doi):
            absent_doi[candidate] = None
    real = sorted(dois)
    if real:
        step = max(1, len(real) // 100)
        picks = real[::step][:100]
        for key in picks:
            last = key[-1]
            for candidate in (key + "x", key + "0", key[:-1] + ("z" if last != "z" else "y"), key + "/1"):
                if len(absent_doi) >= 1300:
                    break
                if _is_fresh_doi(candidate, dois, absent_doi):
                    absent_doi[candidate] = None
    i = 0
    while len(absent_doi) < 1300:
        i += 1
        candidate = f"10.5555/oracle-absent-extra-{i:06d}"
        if _is_fresh_doi(candidate, dois, absent_doi):
            absent_doi[candidate] = None
    absent_pmid: dict[str, None] = {}
    for i in range(150):
        candidate = str(990_000_000 + 7_919 * i)
        if _is_fresh_pmid(candidate, pmids, absent_pmid):
            absent_pmid[candidate] = None
    real_pmids = sorted(pmids, key=int)
    if real_pmids:
        step = max(1, len(real_pmids) // 150)
        for key in real_pmids[::step]:
            if len(absent_pmid) >= 300:
                break
            for delta in range(1, 50):
                candidate = str(int(key) + delta)
                if _is_fresh_pmid(candidate, pmids, absent_pmid):
                    absent_pmid[candidate] = None
                    break
    i = 0
    while len(absent_pmid) < 300:
        i += 1
        candidate = str(980_000_000 + i)
        if _is_fresh_pmid(candidate, pmids, absent_pmid):
            absent_pmid[candidate] = None
    return {"doi": list(absent_doi), "pmid": list(absent_pmid)}


def self_check(result: dict[str, Any]) -> None:
    """Invariants the oracle must satisfy about itself; raises AssertionError (a defect in the oracle)."""
    for key in result["doi"]:
        if normalize_doi(key)[0] != key:
            raise AssertionError(f"DOI key not idempotent: {key!r}")
    for key in result["pmid"]:
        if normalize_pmid(key)[0] != key:
            raise AssertionError(f"PMID key not idempotent: {key!r}")
    quarantined = set(result["quarantined"])
    for scheme in ("doi", "pmid"):
        for key in result["absent_keys"][scheme]:
            if key in result[scheme]:
                raise AssertionError(f"absent {scheme} key is present: {key!r}")
        for entry in result[scheme].values():
            if quarantined.intersection(entry["original"]) or quarantined.intersection(entry["notice"]):
                raise AssertionError("a quarantined record has a role entry")
            if set(entry["original"]) & set(entry["notice"]):
                raise AssertionError("a record is both original and notice for one key")


def run(csv_path: Path) -> dict[str, Any]:
    result = stream(csv_path)
    result["absent_keys"] = absent_keys(result)
    self_check(result)
    return result


def summary_line(result: dict[str, Any], seconds: float) -> str:
    invalid = ",".join(f"{column}={count}" for column, count in result["invalid_identifiers"].items())
    return (
        f"oracle {ORACLE_VERSION}: records={result['records']} accepted={result['accepted']} "
        f"quarantined={len(result['quarantined'])} blank_lines={result['blank_lines']} "
        f"doi_keys={len(result['doi'])} pmid_keys={len(result['pmid'])} "
        f"absent_doi={len(result['absent_keys']['doi'])} absent_pmid={len(result['absent_keys']['pmid'])} "
        f"invalid[{invalid}] sha256={result['source']['sha256']} seconds={seconds:.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        result = run(args.csv)
    except FatalImportError as exc:
        print(f"oracle fatal: {exc}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(result, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")
    print(summary_line(result, time.perf_counter() - started))
    return 0


if __name__ == "__main__":
    sys.exit(main())
