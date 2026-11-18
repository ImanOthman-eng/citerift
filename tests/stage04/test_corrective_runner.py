"""Corrective cycle (owner decision D-071 section 9): the prediction-run tool, not the engine.

Fail-first: the historical tool (``evaluation/tools/s13_run.py``, unchanged, part of the accepted pre-registration P)
loses the first article's export when ``run/exports`` is absent and puts the Investigation Memory where a repository
working tree makes the engine refuse it. The corrected tool (``corrective/runner/s13_run_v2.py``) prepares both before
the first article: the first article exports, and an unsafe memory root is refused before anything runs. The memory
root is an operational locator only. Bundle: VS-1 (enwiki 1381772671, MMR vaccine), a previously exposed design case;
index: the attributed Step 8 subset.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import step8_support as S8

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
OLD = REPO / "docs/verification/stage-04/evaluation/tools/s13_run.py"
NEW = REPO / "docs/verification/stage-04/corrective/runner/s13_run_v2.py"
NAME = "en-1381772671"


def _load(path: Path, name: str) -> ModuleType:
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


def campaign(base: Path) -> Path:
    c = base / "campaign"
    shutil.copytree(S8.EN_MMR, c / "bundles" / NAME)
    return c


def scientific(rec: dict[str, Any]) -> dict[str, Any]:
    keep = ("article", "wiki", "investigation_key", "lifecycle", "claims_by_class", "verify_passed")
    return {k: rec.get(k) for k in keep} | {"exported": rec.get("export") is not None}


def test_historical_tool_loses_the_first_export(tmp_path: Path, index: Path) -> None:
    """Deviation 2 of the failed campaign, reproduced: no ``run/exports`` → the engine refuses the export."""
    old = _load(OLD, "s13_run_historical")
    c = campaign(tmp_path)
    (c / "run" / "memory").mkdir(mode=0o700, parents=True)  # as the historical main() does
    rec = old.run_article(NAME, "en", c, index)
    assert rec["verify_passed"] is True
    assert rec["export"] is None
    assert rec["export_error"]["error"]["code"] == "OUTPUT_PATH_UNSAFE"


def test_historical_tool_memory_under_a_working_tree_is_refused(tmp_path: Path, index: Path) -> None:
    """Deviation 1 reproduced: the campaign lies in a repository working tree, so the memory under it is refused."""
    old = _load(OLD, "s13_run_historical")
    work = tmp_path / "checkout"
    (work / ".git").mkdir(parents=True)
    c = campaign(work)
    (c / "run" / "memory").mkdir(mode=0o700, parents=True)
    rec = old.run_article(NAME, "en", c, index)
    assert rec["investigation_key"] is None
    assert rec["error"]["error"]["code"] == "MEMORY_ROOT_UNSAFE"


def test_corrected_tool_prepares_the_export_parent_and_the_first_article_exports(tmp_path: Path, index: Path) -> None:
    new = _load(NEW, "s13_run_v2")
    c = campaign(tmp_path)
    assert not (c / "run" / "exports").exists()
    op = new.prepare(c, tmp_path / "memory-outside")
    assert (c / "run" / "exports").is_dir()
    assert Path(op["memory_root"]).stat().st_mode & 0o777 == 0o700
    rec = new.run_article(NAME, "en", c, index, Path(op["memory_root"]))
    assert rec["verify_passed"] is True
    assert rec["export"] == f"run/exports/{NAME}" and (c / rec["export"] / "export.json").is_file()
    assert "memory_root" not in rec


@pytest.mark.parametrize("where", ["working_tree", "repository", "relative"])
def test_corrected_tool_refuses_an_unsafe_memory_root_before_any_article(tmp_path: Path, where: str) -> None:
    new = _load(NEW, "s13_run_v2")
    c = campaign(tmp_path)
    if where == "working_tree":
        (tmp_path / "checkout" / ".git").mkdir(parents=True)
        root = tmp_path / "checkout" / "memory"
    elif where == "repository":
        root = REPO / "docs" / "never-created-memory-root"
    else:
        root = Path("relative-memory")
    with pytest.raises(new.RunnerRefused):
        new.prepare(c, root)
    assert not (REPO / "docs" / "never-created-memory-root").exists()
    assert not Path("relative-memory").exists()


def test_the_memory_root_is_an_operational_locator_only(tmp_path: Path, index: Path) -> None:
    """Two runs of one article with two memory roots give the same scientific record."""
    new = _load(NEW, "s13_run_v2")
    recs = []
    for k in ("a", "b"):
        c = campaign(tmp_path / k)
        op = new.prepare(c, tmp_path / f"memory-{k}")
        recs.append(new.run_article(NAME, "en", c, index, Path(op["memory_root"])))
    assert scientific(recs[0]) == scientific(recs[1])
    assert recs[0]["investigation_key"] is not None


def test_the_historical_guard_refuses_the_corrected_engine() -> None:
    """The historical tool's guard (``s13_run.frozen_check``, part of P) pins the frozen engine b5bf8ed: it refuses
    this tree, so the historical tool can never run the corrected engine under P (owner decision D-071)."""
    import subprocess

    old = _load(OLD, "s13_run_historical")
    params = old.read_json(REPO / "docs/verification/stage-04/evaluation/PARAMETERS.json")
    commit = params["frozen_engine"]["content_commit"]
    if subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO, check=False).returncode:
        pytest.skip("the frozen commit is not in this clone (shallow checkout)")
    with pytest.raises(SystemExit, match="the engine is not the frozen one"):
        old.frozen_check(params)
