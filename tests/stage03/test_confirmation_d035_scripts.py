"""The D-035 campaign scripts are copies of the frozen 2026-11 scripts, changed only as
AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 2 lists: the docstrings, and in ``select_confirmation.py`` the
salt, empty challenge strata and the campaign name."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts"
NEW = ROOT / "docs/verification/stage-03/evaluation/confirmation-d035/scripts"
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
    return text.replace("confirmation-2026-11", "CAMPAIGN").replace("confirmation-d035", "CAMPAIGN")


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"d035_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.regression
@pytest.mark.parametrize("name", SAME)
def test_copied_script_code_is_unchanged(name: str) -> None:
    assert _body(NEW / name) == _body(OLD / name)


@pytest.mark.regression
def test_select_differs_only_in_salt_strata_and_campaign_name() -> None:
    assert _body(NEW / "select_confirmation.py", CHANGED_NAMES) == _body(OLD / "select_confirmation.py", CHANGED_NAMES)
    new = _load(NEW / "select_confirmation.py")
    old = _load(OLD / "select_confirmation.py")
    assert new.SALT == "citerift-stage03-confirmation-d035-2026-11-03-v1" != old.SALT
    assert new.STRATA == {"ar": [], "en": []}
    assert (new.INITIAL, new.MAXIMUM, new.BLOCK, new.MAX_BATCHES) == (
        old.INITIAL,
        old.MAXIMUM,
        old.BLOCK,
        old.MAX_BATCHES,
    )


@pytest.mark.regression
def test_select_makes_no_challenge_request_and_plans_no_challenge() -> None:
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
    assert plan["campaign"] == "confirmation-d035"
    assert [a["split"] for a in plan["articles"]] == ["holdout", "holdout", "reserve1"]
