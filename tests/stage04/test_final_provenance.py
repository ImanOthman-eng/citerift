"""Final corrective cycle (owner decision D-083, item 6; reviewer finding D-03): every committed final-cycle result
was computed by committed code that still decides as the code under test.

For every JSON result under ``docs/verification/stage-04/final-cycle`` (all but the inputs listed in ``INPUTS``):

- it records the provenance of ``fc_provenance`` with an empty ``uncommitted`` list;
- the recorded tool SHA-256 is the SHA-256 of that tool at the recorded ``code_commit``;
- the engine and the inputs a result depends on (``SAME_AS_HEAD``) are identical at ``code_commit`` and at HEAD, so the
  result still describes the code under test (a change there needs a rerun);
- the results computed from a Stage 02 index all name one index.

The fail-first inputs are a pure function of the corpus and the bib-1 code and are recomputed here. The history is
required, never skipped (CI checks out the full history).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
S04 = "docs/verification/stage-04"
FC = REPO / S04 / "final-cycle"

# Inputs, not results: each is checked elsewhere.
INPUTS = {
    "corpus/BIB_CORPUS.json": "the adversarial corpus; every case is decided by test_final_bib.py",
    "fail-first/detector_inputs.json": "recomputed from the corpus by test_fail_first_inputs_are_recomputed",
    "simulation/decision_space_dt3_summary.json": "the dt-3 oracle summary (oracle pinned by test_final_oracle.py)",
}
# What a final-cycle result depends on besides its own tool: the engine, the schemas, the reference models, the pinned
# dependencies, the test support modules the tools import, and the input trees (campaign bundles, the dt-2 regression,
# the step 7 generators).
SAME_AS_HEAD = (
    "src",
    "schemas",
    "simulations/stage04",
    "pyproject.toml",
    "uv.lock",
    "tests/stage04/*_support.py",
    f"{S04}/evaluation",
    f"{S04}/evaluation-campaign",
    f"{S04}/evaluation-p2-campaign",
    f"{S04}/corrective/regression",
    f"{S04}/review/step7",
)
DT2_ENGINE_COMMIT = "6663314"

pytestmark = pytest.mark.unit


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def _results() -> list[str]:
    return sorted(
        str(p.relative_to(FC))
        for p in FC.rglob("*.json")
        if "__pycache__" not in p.parts and p.parts[len(FC.parts)] != "review"
    )


def _load(rel: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FC / rel).read_text(encoding="utf-8"))
    return data


def test_every_json_file_is_a_result_or_a_listed_input() -> None:
    names = _results()
    assert set(INPUTS) <= set(names), sorted(set(INPUTS) - set(names))
    assert len(names) > len(INPUTS)


@pytest.mark.parametrize("rel", [r for r in _results() if r not in INPUTS])
def test_a_result_was_computed_by_committed_code_that_still_decides_as_head(rel: str) -> None:
    prov = _load(rel).get("provenance")
    assert isinstance(prov, dict), f"{rel} records no provenance"
    assert prov["uncommitted"] == [], (rel, prov["uncommitted"])
    commit = prov["code_commit"]
    found = subprocess.run(["git", "cat-file", "-e", commit], cwd=REPO, check=False)
    assert found.returncode == 0, f"{rel}: commit {commit} is needed (a full git checkout)"
    tool = subprocess.run(["git", "show", f"{commit}:{prov['tool']}"], cwd=REPO, capture_output=True, check=True).stdout
    assert hashlib.sha256(tool).hexdigest() == prov["tool_sha256"], rel
    changed = _git("diff", "--name-only", commit, "HEAD", "--", *SAME_AS_HEAD)
    assert changed == "", f"{rel} was computed at {commit[:12]}; changed since: {changed.split()[:10]}"


def test_results_computed_from_a_stage02_index_name_one_index() -> None:
    indexes = {
        rel: json.dumps(_load(rel)["provenance"]["index"], sort_keys=True)
        for rel in _results()
        if rel not in INPUTS and "index" in _load(rel).get("provenance", {})
    }
    assert indexes and len(set(indexes.values())) == 1, indexes


def test_the_fail_first_runs_name_their_engine_commits() -> None:
    dt2 = _load("fail-first/decided_by_dt2_engine_6663314.json")
    assert dt2["engine_source"]["commit"].startswith(DT2_ENGINE_COMMIT) and dt2["table_version"] == "dt-2"
    dt3 = _load("fail-first/decided_by_dt3_engine.json")
    assert dt3["engine_source"] == {"commit": dt3["provenance"]["code_commit"], "path_in_repository": "src/"}
    assert dt3["table_version"] == "dt-3"
    view = _load("identity/LOGICAL_VIEW_DIFF.json")
    assert view["old_root_head"].startswith(DT2_ENGINE_COMMIT)


def test_fail_first_inputs_are_recomputed() -> None:
    spec = importlib.util.spec_from_file_location("fc_detector_inputs", FC / "fail-first" / "detector_inputs.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert (FC / "fail-first" / "detector_inputs.json").read_text(encoding="utf-8") == mod.render()
    corpus = json.loads((FC / "corpus" / "BIB_CORPUS.json").read_text(encoding="utf-8"))["cases"]
    assert [c["id"] for c in mod.inputs()] == [c["id"] for c in corpus]


def _fc_provenance() -> Any:
    spec = importlib.util.spec_from_file_location("fc_provenance_under_test", FC / "fc_provenance.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_tool_refuses_a_dirty_tree_and_a_tree_that_changes_while_it_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    fp = _fc_provenance()
    real = fp._git
    status = {"out": ""}

    def fake(*args: str) -> str:
        return status["out"] if args[0] == "status" else real(*args)

    monkeypatch.setattr(fp, "_git", fake)
    tool = FC / "fc_provenance.py"
    begun = fp.start(tool)
    assert begun["uncommitted"] == [] and begun["excluded_paths"] == [f"{S04}/final-cycle/review"]
    fp.finish(begun, tool)
    status["out"] = " M src/citerift/investigation/dt1.py\n"
    with pytest.raises(SystemExit, match="changed while the tool ran"):
        fp.finish(begun, tool)
    with pytest.raises(SystemExit, match="uncommitted changes"):
        fp.start(tool)
