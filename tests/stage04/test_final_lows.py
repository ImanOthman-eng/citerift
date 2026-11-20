"""Final corrective cycle (owner decision D-083, item 6): the open LOW findings of the corrective review, each closed
with a test that fails on the code before its fix (the fail-first runs are recorded in
``docs/verification/stage-04/final-cycle/lows/``).

- D-05: the role-collision fixture manifest names the full identity of the index its keys were selected from.
- E-05: the command line never prints the absolute memory root (errors included); with the final-cycle review's
  E-03 (the root of ``run --request``, and ancestors named by the memory-root checks) and E-04 (only whole absolute
  spellings are replaced, so digests and identifiers are never rewritten).
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The pinned Stage 02 index (rw-2f116e9ffed718e6): its identity as freeze-2's D-062 record states it.
INDEX_IDENTITY = {
    "source_sha256": "2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655",
    "artifact_digest": "adcf7b6547e09fc72b6379b3f616608eca8225d66e688d2b2d5a0271b0b016d9",
    "semantic_digest": "7b2a2344a7f9546d2c684dfef84aa01db9e010fd9c9bf7f9343c93b5b88a5f88",
    "snapshot_id": "rw-2f116e9ffed718e6",
}


def test_d05_the_fixture_manifest_names_the_selection_index_identity() -> None:
    manifest = json.loads((FIXTURES / "corrective" / "rw_role_collision.json").read_text(encoding="utf-8"))
    selection = manifest["selection_index"]
    assert {k: selection.get(k) for k in INDEX_IDENTITY} == INDEX_IDENTITY
    d062 = (REPO / "docs/verification/stage-04/freeze-2/d062/two_build_equivalence.json").read_text(encoding="utf-8")
    assert INDEX_IDENTITY["artifact_digest"] in d062 and INDEX_IDENTITY["semantic_digest"] in d062
    assert manifest["source"]["sha256"] == INDEX_IDENTITY["source_sha256"]
    assert set(manifest["source"]) == {"bytes", "commit", "path", "repository", "sha256", "url"}


def _cli(*argv: str | Path) -> tuple[int, str]:
    from citerift.investigation import cli

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main([str(a) for a in argv])
    return code, out.getvalue() + err.getvalue()


@pytest.mark.parametrize("damage", ["world_writable", "missing_key"])
def test_e05_the_command_line_never_prints_the_memory_root(tmp_path: Path, damage: str) -> None:
    root = tmp_path / "account-name-here" / "memory"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o777 if damage == "world_writable" else 0o700)
    for fmt in ("json", "text"):
        code, printed = _cli("show", "--memory-root", root, "--key", "a" * 64, "--format", fmt)
        assert code in (3, 4)
        assert "account-name-here" not in printed and str(tmp_path) not in printed, printed
        assert "<memory-root>" in printed or damage == "missing_key"


def test_e03_run_with_a_request_file_never_prints_the_memory_root(tmp_path: Path) -> None:
    from citerift.investigation import operations as ops

    root = tmp_path / "account-name-here" / "memory"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o777)
    request = tmp_path / "request.json"
    req = ops.live_request("en", 1, tmp_path / "index.sqlite", root)  # refused at the memory root: nothing is fetched
    request.write_text(json.dumps(req), encoding="utf-8")
    for fmt in ("json", "text"):
        code, printed = _cli("run", "--request", request, "--format", fmt)
        assert code == 3, printed
        assert "account-name-here" not in printed and "<memory-root>" in printed, printed


def test_e03_the_memory_root_checks_never_print_an_ancestor(tmp_path: Path) -> None:
    root = tmp_path / "account-name-here" / "project" / "memory"
    root.mkdir(parents=True, mode=0o700)
    (tmp_path / "account-name-here" / "project" / ".git").mkdir()
    for fmt in ("json", "text"):
        code, printed = _cli("show", "--memory-root", root, "--key", "a" * 64, "--format", fmt)
        assert code == 3, printed
        assert "account-name-here" not in printed and "repository working tree" in printed, printed


def test_e04_redaction_replaces_only_whole_absolute_spellings(tmp_path: Path) -> None:
    import argparse

    from citerift.investigation import cli

    digest = "00ab12ab" * 8
    relative = cli._redactor(argparse.Namespace(memory_root=Path("ab")))
    absolute_ab = str(Path("ab").absolute())
    assert relative({"claim_id": digest, "text": "under the ab root"}) == {
        "claim_id": digest,
        "text": "under the ab root",
    }
    assert relative(f"{absolute_ab}/journal") == "<memory-root>/journal"
    root = tmp_path / "db"
    redact = cli._redactor(argparse.Namespace(memory_root=root))
    assert redact(f"{root}/journal is torn") == "<memory-root>/journal is torn"
    assert redact(f"'{root}': not a directory.") == "'<memory-root>': not a directory."
    assert redact(f"{root}x and {root}-2") == f"{root}x and {root}-2"  # other paths, not the root
    assert redact(f"x{root}") == f"x{root}"
    assert redact({"journal_digest": "db" * 32, "n": 3}) == {"journal_digest": "db" * 32, "n": 3}
