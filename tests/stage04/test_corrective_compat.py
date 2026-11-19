"""Corrective cycle (owner decision D-071; reviewer finding C-02): an investigation made by the frozen engine (0.2.0,
table dt-1) is refused when read by engine 0.3.0, never folded as a dt-2 investigation.

The journal of the superseded freeze's vertical slice (``freeze/vertical-slice/VS-6a``, engine 0.2.0, kept unchanged)
is folded record by record: its first record names ``table_version`` dt-1 and schema 3.0.0, which the dt-2 schemas
refuse (``RECORD_INVALID``), so a Memory root created by the frozen engine is corrupt for this engine by design and an
investigation must be run again under a new key (the engine identity is part of the key). The same case from the
freeze-2 vertical slice (engine 0.3.0) folds without a problem, as the control.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from citerift.investigation.errors import InvariantViolation
from citerift.investigation.fold import Folder
from citerift.investigation.journal import parse_journal

pytestmark = pytest.mark.unit

S04 = Path(__file__).resolve().parents[2] / "docs" / "verification" / "stage-04"
FROZEN = S04 / "freeze" / "vertical-slice" / "VS-6a" / "journal.jsonl"
CURRENT = S04 / "freeze-2" / "vertical-slice" / "VS-6a" / "journal.jsonl"


def test_a_frozen_engine_journal_is_refused_not_read_as_dt2() -> None:
    records = parse_journal(FROZEN.read_bytes()).records
    stage04 = records[0]["payload"]["stage04"]
    assert (stage04["table_version"], stage04["schema_version"]) == ("dt-1", "3.0.0")
    folder = Folder(None)
    with pytest.raises(InvariantViolation) as exc:
        for rec in records:
            folder.apply(rec)
    assert exc.value.code == "RECORD_INVALID"
    assert exc.value.seq == 0
    assert "dt-2" in exc.value.reason and "4.0.0" in exc.value.reason


def test_the_same_case_from_the_current_engine_folds() -> None:
    records = parse_journal(CURRENT.read_bytes()).records
    assert records[0]["payload"]["stage04"]["table_version"] == "dt-2"
    folder = Folder(None)
    for rec in records:
        folder.apply(rec)
    assert len(folder.records) == len(records)
