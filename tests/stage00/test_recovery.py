"""Controlled recovery test: a fresh session with no conversational memory reconstructs project state.

The state is built in one repository, then cloned into a new directory and
inspected by a separate Python process with a minimal environment, so nothing
from the building process can leak into the reconstruction.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sandbox_repo import GIT_ENV, OWNER_REF, Sandbox, git

from citerift.governance.model import Status

pytestmark = [pytest.mark.reproducibility]


def run_recover(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": str(root.parent), "LANG": "C.UTF-8", **GIT_ENV}
    return subprocess.run(
        [sys.executable, "-I", "-m", "citerift.governance.cli", "--root", str(root), *extra],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_fresh_clone_reconstructs_state(sandbox: Sandbox, tmp_path: Path) -> None:
    sandbox.drive_to_accepted("01")
    verified = sandbox.drive_to_verified("00")
    risks = (sandbox.root / "RISKS.md").read_text(encoding="utf-8")
    sandbox.write(
        "RISKS.md",
        risks + "\n## R-002 — Known limitation\n- Status: open\n- Severity: medium\n- Kind: limitation\n- Stage: 00\n",
    )
    decisions = (sandbox.root / "DECISIONS.md").read_text(encoding="utf-8")
    sandbox.write("DECISIONS.md", decisions + "\n## D-002 — License\n- Status: pending-owner\n- Topic: license\n")
    authoritative = sandbox.commit("record memory")

    clone = tmp_path / "fresh-session"
    git(tmp_path, "clone", "-q", str(sandbox.root), str(clone))
    out = run_recover(clone, "--json", "recover")
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)

    assert data["head"] == authoritative  # 6. which revision is authoritative
    assert data["uncommitted_changes"] == []
    assert data["completed_and_accepted"] == ["01"]  # 1. what is completed
    assert data["verified_awaiting_owner_acceptance"] == ["00"]  # 2. independently verified
    assert data["authoritative_revisions"]["00"] == {"verified": verified, "accepted": None}
    assert data["not_started"] == ["02", "03", "04", "05", "06", "07", "08", "09"]  # 3. what remains open
    assert {r["id"] for r in data["open_risks_and_limitations"]} == {"R-001", "R-002"}  # 4. limitations
    assert data["pending_decisions"] == [{"id": "D-002", "title": "License"}]
    assert data["recent_changes"][-1]["to"] == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE  # 5. what changed
    next_actions = " ".join(data["next_actions"])  # 7. what is authorized next
    assert "Stage 00 (Engineering Foundation): owner acceptance decision required" in next_actions
    assert "Stage 02" not in next_actions  # 02 needs 00 accepted first; nothing is falsely authorized
    assert data["consistency"]["errors"] == []

    text = run_recover(clone, "recover")
    assert text.returncode == 0
    assert "Verified, awaiting owner acceptance: 00" in text.stdout


def test_recovery_reports_inconsistency_instead_of_guessing(sandbox: Sandbox, tmp_path: Path) -> None:
    sandbox.go("00", Status.AUTHORIZED)
    reg = sandbox.registry()
    reg["stages"][0]["status"] = "ACCEPTED_CLOSED"
    sandbox.save_registry(reg)
    sandbox.commit("corrupt registry")
    clone = tmp_path / "fresh-session"
    git(tmp_path, "clone", "-q", str(sandbox.root), str(clone))
    data = json.loads(run_recover(clone, "--json", "recover").stdout)
    codes = {e["code"] for e in data["consistency"]["errors"]}
    assert "STATUS_HISTORY_CONFLICT" in codes
    assert run_recover(clone, "check").returncode == 1


def test_owner_reference_survives_in_history(sandbox: Sandbox) -> None:
    sandbox.go("00", Status.AUTHORIZED)
    sandbox.commit("authorize")
    data = json.loads(run_recover(sandbox.root, "--json", "recover").stdout)
    assert data["recent_changes"][0]["owner_ref"] == OWNER_REF
