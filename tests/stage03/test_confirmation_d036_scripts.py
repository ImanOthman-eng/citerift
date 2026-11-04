"""The D-036 campaign scripts are copies of the frozen 2026-11 scripts (through the D-035 copies), changed only as
AMENDMENT_2026-11-04_D036_CONFIRMATION.md section 2 lists: the docstrings, and in ``select_confirmation.py`` the
salt, the unused challenge salt and the campaign name. ``make_packets_partial.py`` is the D-035 wrapper with one
docstring paragraph added."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "docs/verification/stage-03/evaluation"
OLD = EVAL / "confirmation-2026-11/scripts"
D035 = EVAL / "confirmation-d035/scripts"
NEW = EVAL / "confirmation-d036/scripts"
SAME = [
    "disagreements_v2.py",
    "exposure_set.py",
    "intervals.py",
    "reserve_step.py",
    "run_confirmation.py",
    "warning_challenge.py",
]
CHANGED_NAMES = frozenset({"SALT", "CHALLENGE_SALT", "STRATA"})


def _body(path: Path, drop: frozenset[str] = frozenset()) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) else tree.body
    kept = []
    for node in body:
        targets = (
            [t.id for t in node.targets if isinstance(t, ast.Name)]
            if isinstance(node, ast.Assign)
            else [node.target.id]
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            else []
        )
        if not set(targets) & drop:
            kept.append(node)
    text = ast.dump(ast.Module(body=kept, type_ignores=[]))
    for name in ("confirmation-2026-11", "confirmation-d035", "confirmation-d036"):
        text = text.replace(name, "CAMPAIGN")
    return text


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"d036_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.regression
@pytest.mark.parametrize("name", SAME)
def test_d036_copied_script_code_is_unchanged(name: str) -> None:
    assert _body(NEW / name) == _body(OLD / name) == _body(D035 / name)


@pytest.mark.regression
def test_d036_make_packets_partial_code_is_the_d035_wrapper() -> None:
    assert _body(NEW / "make_packets_partial.py") == _body(D035 / "make_packets_partial.py")


@pytest.mark.regression
def test_d036_select_differs_only_in_salt_strata_and_campaign_name() -> None:
    assert _body(NEW / "select_confirmation.py", CHANGED_NAMES) == _body(OLD / "select_confirmation.py", CHANGED_NAMES)
    new = _load(NEW / "select_confirmation.py")
    old = _load(OLD / "select_confirmation.py")
    d035 = _load(D035 / "select_confirmation.py")
    assert new.SALT == "citerift-stage03-confirmation-d036-2026-11-04-v1"
    assert new.SALT not in (old.SALT, d035.SALT)
    assert new.STRATA == {"ar": [], "en": []}
    assert (new.INITIAL, new.MAXIMUM, new.BLOCK, new.MAX_BATCHES) == (
        old.INITIAL,
        old.MAXIMUM,
        old.BLOCK,
        old.MAX_BATCHES,
    )


@pytest.mark.regression
def test_d036_select_makes_no_challenge_request_and_plans_no_challenge() -> None:
    new = _load(NEW / "select_confirmation.py")
    calls: list[str] = []

    def get(url: str) -> dict[str, object]:
        calls.append(url)
        raise AssertionError("no request expected")

    assert new.challenge(get, "en", set(), set()) == {}
    assert new.challenge(get, "ar", set(), set()) == {}
    assert calls == []
    selection = {
        "frame": {w: {"initial": [{"page_id": 1}], "reserve_blocks": [[{"page_id": 2}]]} for w in ("ar", "en")},
        "challenge": {"ar": {}, "en": {}},
    }
    plan = new.plan(selection, {"en": 1}, with_challenge=False)
    assert plan["campaign"] == "confirmation-d036"
    assert [a["split"] for a in plan["articles"]] == ["holdout", "holdout", "reserve1"]


@pytest.mark.security
def test_d036_secret_gate_withholds_a_matching_file_and_records_no_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _load(NEW / "secret_gate.py")
    key_id = "AK" + "IA" + "Q" * 16  # built at run time: no tracked file holds the pattern
    (tmp_path / "capture").mkdir()
    planted = tmp_path / "capture" / "render.html"
    planted.write_text(f"<a href='https://example.invalid/x?AWSAccessKeyId={key_id}'>x</a>", encoding="utf-8")
    clean = tmp_path / "capture" / "source.wikitext"
    clean.write_text("no secret here", encoding="utf-8")
    monkeypatch.setattr(gate, "untracked", lambda campaign: [planted, clean])
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 3
    ledger = (tmp_path / "WITHHELD_FILES.json").read_text(encoding="utf-8")
    assert key_id not in ledger
    assert json.loads(ledger)["files"][0]["path"] == "capture/render.html"
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines() == ["/capture/render.html"]
    assert planted.read_text(encoding="utf-8").count(key_id) == 1  # kept on disk unchanged
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 0  # already withheld: nothing new
    monkeypatch.setattr(gate, "untracked", lambda campaign: [clean])
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 0


@pytest.mark.security
def test_d036_secret_gate_uses_the_stage00_patterns() -> None:
    gate = _load(NEW / "secret_gate.py")
    stage00 = _load(ROOT / "tests/stage00/test_repository.py")
    assert [p.pattern for p in gate.patterns()] == [p.pattern for p in stage00.SECRET_PATTERNS]
