"""Regressions for the confirmed findings of the focused follow-up review R7 (candidate 0dfef1c;
review/round-7/REVIEW.md) on the campaign tools. The tokenizer findings RF7-1 and RF7-2 are covered in
test_wiki_mf1_tokenizer.py. SYNTHETIC: no request is made."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts"))
cc = importlib.import_module("campaign_capture")
sel = importlib.import_module("select_confirmation")


class Killed(BaseException):
    pass


@pytest.mark.regression
@pytest.mark.parametrize("char", ["\u0085", " ", " "])
def test_a_unicode_line_separator_inside_a_journal_string_is_not_a_line_end(tmp_path: Path, char: str) -> None:
    """RF7-4."""
    cc._append(tmp_path / "captures.jsonl", {"event": "end", "key": "k", "run": 1, "stderr": f"a{char}b"})
    assert cc._journal(tmp_path)[0]["stderr"] == f"a{char}b"


@pytest.mark.regression
def test_a_whole_final_line_missing_only_its_line_end_is_completed_not_dropped(tmp_path: Path) -> None:
    """RF7-5 (a): a deferral's end line keeps its not_before."""
    end = {"event": "end", "key": "holdout/en-1", "run": 1, "stdout": {"status": "deferred"}}
    (tmp_path / "captures.jsonl").write_text(json.dumps({"event": "start"}) + "\n" + json.dumps(end))
    assert cc.repair_journal(tmp_path) == "completed the final line"
    assert cc._journal(tmp_path)[-1] == end and not list(tmp_path.glob("*.torn-at-*"))


@pytest.mark.regression
def test_two_tears_at_the_same_offset_are_both_kept(tmp_path: Path) -> None:
    """RF7-5 (b)."""
    log = tmp_path / "captures.jsonl"
    head = json.dumps({"event": "start"}) + "\n"
    for fragment in ('{"event": "end", "ke', '{"event": "end", "key": "other'):
        log.write_text(head + fragment)
        cc.repair_journal(tmp_path)
    kept = sorted(p.read_text() for p in tmp_path.glob("captures.jsonl.torn-at-*"))
    assert kept == sorted(['{"event": "end", "ke', '{"event": "end", "key": "other'])
    assert log.read_text() == head


@pytest.mark.regression
def test_only_the_attempt_that_ended_a_failed_operation_makes_a_retry_after_problem_final() -> None:
    """RF7-6: an odd header on an accepted source response does not end retries of an unrelated render failure."""
    source_ok = {"operation": "source", "code": None, "retry_after_problem": "RETRY_AFTER_UNREADABLE"}
    render_failed = {"operation": "render", "code": "ATTEMPTS_EXHAUSTED", "retry_after_problem": None}
    stdout = {
        "status": "partial",
        "capture": {
            "attempts": [source_ok, render_failed],
            "issues": [{"code": "ATTEMPTS_EXHAUSTED"}],
            "render": {"code": "ATTEMPTS_EXHAUSTED"},
        },
    }
    run = {"run": 1, **cc.summarize(6, stdout)}
    assert run["retry_after_problems"] == []
    assert cc.next_step({"runs": [run]}, 0.0) == ("run", None)
    render_429 = {"operation": "render", "code": "HTTP_RATE_LIMITED", "retry_after_problem": "RETRY_AFTER_UNREADABLE"}
    stdout["capture"]["attempts"] = [source_ok, render_429]
    assert cc.summarize(6, stdout)["retry_after_problems"] == ["RETRY_AFTER_UNREADABLE"]


@pytest.mark.regression
def test_a_kill_while_selection_is_written_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF7-8."""
    exposure = tmp_path / "exposure.json"
    exposure.write_text(json.dumps({"page_ids": [], "titles": []}))

    class NoGet:
        def __init__(self, campaign: Path) -> None:
            (campaign / "selection").mkdir(parents=True)
            self.earlier: list[str] = []
            self.requests: list[dict[str, Any]] = []

    def replace(*_: Any) -> None:
        raise Killed

    monkeypatch.setattr(sel, "LiveGet", NoGet)
    monkeypatch.setattr(sel, "select", lambda get, exp: {"frame": {}, "challenge": {}})
    monkeypatch.setattr(cc.os, "replace", replace)
    monkeypatch.setattr(sys, "argv", ["select_confirmation.py", str(exposure), str(tmp_path / "campaign")])
    with pytest.raises(Killed):
        sel.main()
    assert not (tmp_path / "campaign" / "selection" / "SELECTION.json").exists()
