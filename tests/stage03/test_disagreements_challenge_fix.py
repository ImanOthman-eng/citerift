"""Disagreement listing on a ``challenge`` split (defect found 2026-11-03, after the confirmation prediction run).

SYNTHETIC: one synthetic bundle; no request is made. The frozen ``disagreements_v2.items`` recurses without end on a
``challenge`` split; ``disagreements_challenge_fix.items`` lists it with the challenge window and leaves the frozen
modules unchanged.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, extract

SCRIPTS = Path(__file__).resolve().parents[2] / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts"
sys.path.insert(0, str(SCRIPTS))
wc = importlib.import_module("warning_challenge")
dv2 = importlib.import_module("disagreements_v2")
fix = importlib.import_module("disagreements_challenge_fix")

TEXT = "Intro.\n" + "x" * 9000 + "\nA.<ref>{{Retracted|doi=10.1/r}}{{cite journal|doi=10.1/a}}</ref>\n"


def _spec(tmp_path: Path, split: str) -> tuple[dict[str, Any], Any]:
    path = bundle(tmp_path, TEXT)
    (tmp_path / "x.json").write_text(json.dumps(extract(path)))
    art = wc.load(path)
    ann = {"article": {"window": list(art.window)}, "definitions": [], "uses": [], "identifiers": []}
    (tmp_path / "a.json").write_text(json.dumps(ann))
    entry = {"bundle": str(path), "extraction": str(tmp_path / "x.json"), "locked": str(tmp_path / "a.json")}
    return {"splits": {split: [entry]}}, art


@pytest.mark.unit
def test_frozen_disagreements_v2_recurses_on_a_challenge_split(tmp_path: Path) -> None:
    spec, _ = _spec(tmp_path, "challenge")
    with pytest.raises(RecursionError):
        dv2.items(spec)
    assert dv2.d1.ev.load_bundle is fix._ORIGINAL_LOAD_BUNDLE  # the frozen code restored its patch


@pytest.mark.unit
def test_wrapper_lists_the_challenge_split_with_the_challenge_window(tmp_path: Path) -> None:
    spec, art = _spec(tmp_path, "challenge")
    assert art.window[0] > 0  # the challenge window starts at the marker line, not at 0
    got = fix.items(spec)["challenge"][0]
    assert got["window"] == list(art.window)
    assert any(i["kind"] == "definition_extra" for i in got["items"])
    assert wc.load is not fix._challenge_load  # restored


@pytest.mark.unit
def test_wrapper_gives_the_frozen_result_on_a_gate_split(tmp_path: Path) -> None:
    spec, _ = _spec(tmp_path, "gate")
    assert fix.items(spec) == dv2.items(spec)
