"""Step 6: strict JSON and canonical serialization (MM 2; review finding SR-12; owner Step 6 items 3 and 4)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from citerift.investigation import ids
from citerift.investigation.canonical import H, canon, loads_blob, loads_record, sha256_hex, uuid_from_key
from citerift.investigation.errors import CanonError

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_canonical_bytes_are_sorted_compact_utf8() -> None:
    value = {"b": [1, {"y": None, "x": True}], "a": "عربي é"}
    assert canon(value) == '{"a":"عربي é","b":[1,{"x":true,"y":null}]}'.encode()
    assert loads_record(canon(value)) == value


@pytest.mark.negative
@pytest.mark.parametrize(
    "text",
    [
        b'{"seq":1.0}',
        b'{"seq":1e0}',
        b'{"seq":1E2}',
        b'{"seq":-0.0}',
        b'{"seq":NaN}',
        b'{"seq":Infinity}',
        b'{"seq":-Infinity}',
        b'{"seq":1e400}',
    ],
)
def test_record_reader_refuses_non_integer_number_tokens(text: bytes) -> None:
    """SR-12: an integer field encoded as 1.0 is refused, never coerced; NaN and Infinity are refused."""
    with pytest.raises(CanonError) as exc:
        loads_record(text)
    assert exc.value.code == "JSON_INVALID"


@pytest.mark.negative
@pytest.mark.parametrize(
    "text",
    [
        b'{"a":1,"a":1}',  # duplicate key, equal values
        b'{"a":1,"b":{"c":1,"c":2}}',  # nested duplicate
        b'{"a":"\xff"}',  # invalid UTF-8
        b'{"a":"\xed\xa0\x80"}',  # UTF-8-encoded surrogate
        b'{"a":"\\ud800"}',  # lone surrogate escape
        b'\xef\xbb\xbf{"a":1}',  # byte-order mark
        b'{"a": 1}',  # not canonical: space
        b'{"b":1,"a":2}',  # not canonical: key order
        b'{"a":"\\u00e9"}',  # not canonical: escape for a character kept as is
        b'{"a":-0}',  # not canonical: -0 is written 0
        b'{"a":1}\n',  # not canonical: trailing newline inside the record
        b"[" * 100 + b"]" * 100,  # nesting deeper than the bound
        b'{"a":1',  # truncated
        b"",
    ],
)
def test_strict_reader_refusals(text: bytes) -> None:
    for loads in (loads_record, loads_blob):
        with pytest.raises(CanonError):
            loads(text)


@pytest.mark.unit
def test_blob_reader_allows_finite_floats_only() -> None:
    assert loads_blob(b'{"r":0.5}') == {"r": 0.5}
    for text in (b'{"r":NaN}', b'{"r":1e400}', b'{"r":0.50}'):
        with pytest.raises(CanonError):
            loads_blob(text)
    with pytest.raises(CanonError):
        loads_record(b'{"r":0.5}')


@pytest.mark.negative
@pytest.mark.parametrize(
    "value",
    [
        {"a": 1.0},
        {"a": float("nan")},
        {1: "int key"},
        {"a": {1, 2}},
        {"a": b"bytes"},
        {"a": "\ud800"},
        {"a": object()},
    ],
)
def test_canon_refuses_values_outside_the_model(value: object) -> None:
    with pytest.raises(CanonError) as exc:
        canon(value)
    assert exc.value.code == "CANON_INVALID"


@pytest.mark.unit
def test_tagged_hash_and_uuid() -> None:
    assert H("t", 1, "x") == sha256_hex(b'["t",1,"x"]')
    assert H("a", "b") != H("b", "a")
    u = uuid_from_key("0" * 64)
    assert len(u) == 36 and u[14] == "8" and u[19] in "89ab" and u == u.lower()
    with pytest.raises(CanonError):
        H("")


_SCRIPT = """
import json, sys
from citerift.investigation.canonical import H, canon
from citerift.investigation import ids
value = json.loads(sys.stdin.read())
sys.stdout.write(json.dumps([canon(value).hex(), H("citerift-test/1", value), ids.record_digest(value)]))
"""


@pytest.mark.reproducibility
def test_canonical_output_is_identical_across_processes_hash_seeds_and_locales() -> None:
    """Owner Step 6 item 4: deterministic bytes, independent of hash seed, locale and process."""
    value = {"z": [3, 2, 1], "ع": {"é": "ß", "a": None}, "n": -12345678901234, "t": True, "s": "x y"}
    outputs = set()
    for seed, locale in (("0", "C"), ("1", "C.UTF-8"), ("12345", "POSIX"), ("random", "C")):
        env = {**os.environ, "PYTHONHASHSEED": seed, "LC_ALL": locale, "LANG": locale}
        out = subprocess.run(
            [sys.executable, "-c", _SCRIPT],
            input=json.dumps(value),
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.add(out.stdout)
    assert len(outputs) == 1
    here = json.loads(outputs.pop())
    assert here == [canon(value).hex(), H("citerift-test/1", value), ids.record_digest(value)]


@pytest.mark.unit
def test_nesting_bound_is_exactly_max_depth_levels() -> None:
    from citerift.investigation.canonical import MAX_DEPTH

    ok = b"[" * MAX_DEPTH + b"]" * MAX_DEPTH
    assert loads_record(ok) is not None
    with pytest.raises(CanonError):
        loads_record(b"[" + ok + b"]")
