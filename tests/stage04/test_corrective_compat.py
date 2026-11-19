"""Engine compatibility across table versions (owner decisions D-071 and D-083; reviewer finding C-02).

An investigation made by an earlier engine is refused when read by this engine (0.4.0, table dt-3, schema 5.0.0), never
folded as a dt-3 investigation:

- the journal of the superseded freeze's vertical slice (``freeze/vertical-slice/VS-6a``, engine 0.2.0, dt-1, schema
  3.0.0, kept unchanged);
- the journal of the freeze-2 vertical slice (``freeze-2/vertical-slice/VS-6a``, engine 0.3.0, dt-2, schema 4.0.0,
  kept unchanged).

Each one's first record names its table and schema version, which this engine refuses before any other check
(``ENGINE_IDENTITY_DIFFERS``, reviewer finding E-07; the dt-3 schemas would refuse it too). The investigation key does
not include the engine identity, so the same request in a reused memory root meets the earlier engine's journal: it is
reported as STALE with that code (exit 11), not as CORRUPT, and nothing is read or written. An investigation must be
run again with a fresh memory root. A journal written by this engine folds (the control is the Memory and controller
suite, which writes and folds dt-3 journals throughout).

The freeze-2 identity is proved from git at its frozen commit, not from the working tree, which now holds dt-3.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from citerift.investigation.errors import InvariantViolation
from citerift.investigation.fold import Folder
from citerift.investigation.journal import parse_journal

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
S04 = REPO / "docs" / "verification" / "stage-04"
FREEZE2_COMMIT = "28ba6467c7005eec7bf51869974719a402059ca7"


def _refused(path: Path, table: str, schema: str) -> None:
    records = parse_journal(path.read_bytes()).records
    stage04 = records[0]["payload"]["stage04"]
    assert (stage04["table_version"], stage04["schema_version"]) == (table, schema)
    folder = Folder(None)
    with pytest.raises(InvariantViolation) as exc:
        for rec in records:
            folder.apply(rec)
    assert exc.value.code == "ENGINE_IDENTITY_DIFFERS"  # E-07; before D-083: RECORD_INVALID
    assert exc.value.seq == 0
    assert table in exc.value.reason and schema in exc.value.reason
    rec = json.loads(json.dumps(records[0]))
    rec["payload"]["stage04"].update(table_version="dt-3", schema_version="5.0.0")
    with pytest.raises(InvariantViolation) as exc:
        Folder(None).apply(rec)  # the same record claiming this engine's identity is still refused (digest, schema)
    assert exc.value.code in ("RECORD_INVALID", "CHAIN_BROKEN")


def test_the_superseded_frozen_engine_journal_is_refused() -> None:
    _refused(S04 / "freeze" / "vertical-slice" / "VS-6a" / "journal.jsonl", "dt-1", "3.0.0")


def test_the_freeze2_engine_journal_is_refused_not_read_as_dt3() -> None:
    _refused(S04 / "freeze-2" / "vertical-slice" / "VS-6a" / "journal.jsonl", "dt-2", "4.0.0")


def _git(*args: str, text: bool = True) -> Any:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True, text=text).stdout


def test_freeze2_identity_is_proved_from_its_frozen_commit() -> None:
    """D-076: freeze-2 records engine 0.3.0, dt-2, schema 4.0.0, detector 3; every source and schema file it
    lists hashes, at the frozen commit, to its recorded SHA-256. The running engine is dt-3 and differs (D-083)."""
    from citerift.investigation import __version__, dt1
    from citerift.investigation.adapters.detector import DETECTOR_IDENTITY

    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{FREEZE2_COMMIT}^{{commit}}"], cwd=REPO, capture_output=True, check=False
    )
    if probe.returncode != 0:
        pytest.fail(f"commit {FREEZE2_COMMIT} is missing: this proof needs the full history (no shallow clone)")
    manifest = json.loads((S04 / "freeze-2" / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    ident = manifest["stage04_identity"]
    assert (ident["engine_version"], ident["table_version"], ident["schema_version"]) == ("0.3.0", "dt-2", "4.0.0")
    assert ident["detector_identity"] == "citerift-dt1-detector/3 (dt-2)"
    assert manifest["supersedes"]["frozen_commit"] == "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0"
    for group in ("source_files", "schemas"):
        assert manifest[group]
        for path, sha in manifest[group].items():
            blob = _git("show", f"{FREEZE2_COMMIT}:{path}", text=False)
            assert hashlib.sha256(blob).hexdigest() == sha, path
    assert (__version__, dt1.TABLE_VERSION, DETECTOR_IDENTITY) == ("0.4.0", "dt-3", "citerift-dt1-detector/4 (dt-3)")
    assert ident["package_version"] != __version__ and manifest["decision_table_version"] != dt1.TABLE_VERSION


def test_e07_another_engines_journal_has_its_own_code_before_schema_validation() -> None:
    """E-07 (owner decision D-083): the refusal names the engine identity, not a schema defect."""
    from citerift.investigation.fold import ENGINE_IDENTITY_DIFFERS

    for rel, table in (("freeze", "dt-1"), ("freeze-2", "dt-2")):
        records = parse_journal((S04 / rel / "vertical-slice" / "VS-6a" / "journal.jsonl").read_bytes()).records
        with pytest.raises(InvariantViolation) as exc:
            Folder(None).apply(records[0])
        assert exc.value.code == ENGINE_IDENTITY_DIFFERS and exc.value.invariant == "E-07"
        assert table in exc.value.reason


def test_e07_a_tampered_identity_value_is_still_invalid() -> None:
    """Only string table and schema versions of another engine get the identity code; a non-string is a schema
    defect."""
    records = parse_journal((S04 / "freeze-2" / "vertical-slice" / "VS-6a" / "journal.jsonl").read_bytes()).records
    rec = json.loads(json.dumps(records[0]))
    rec["payload"]["stage04"]["table_version"] = 3
    with pytest.raises(InvariantViolation) as exc:
        Folder(None).apply(rec)
    assert exc.value.code == "RECORD_INVALID"


def test_e07_a_reused_memory_root_reports_engine_identity_differs(tmp_path: Path) -> None:
    """A memory root holding an investigation of the freeze-2 engine: opening it (every command opens it so) reports
    STALE / ENGINE_IDENTITY_DIFFERS (exit 11), not CORRUPT, and changes nothing."""
    import os

    from citerift.investigation import operations as ops

    src = S04 / "freeze-2" / "vertical-slice" / "VS-6a" / "journal.jsonl"
    key = parse_journal(src.read_bytes()).records[0]["payload"]["investigation_key"]
    root = tmp_path / "memory"
    inv = root / key
    for d in (root, inv, inv / "blobs"):
        d.mkdir(mode=0o700)
        os.chmod(d, 0o700)
    (inv / "journal.jsonl").write_bytes(src.read_bytes())
    (inv / "lock").write_bytes(b"")
    before = sorted((p.relative_to(root), p.read_bytes() if p.is_file() else None) for p in root.rglob("*"))
    with pytest.raises(ops.OperationError) as exc, ops.opened(root, key):
        pass
    assert (exc.value.status, exc.value.code) == ("stale", "ENGINE_IDENTITY_DIFFERS")
    assert ops.EXIT[exc.value.status] == 11
    result, code = ops.verify(root, key)
    assert (result["result"], result["code"], code) == ("stale", "ENGINE_IDENTITY_DIFFERS", 11)
    after = sorted((p.relative_to(root), p.read_bytes() if p.is_file() else None) for p in root.rglob("*"))
    assert after == before
