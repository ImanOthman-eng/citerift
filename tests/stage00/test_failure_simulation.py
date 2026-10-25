"""Failure simulations: interrupted writes, corrupted records and recovery.

The orchestrator writes the registry and PROJECT_STATUS.md through a temporary
file and ``os.replace``. These tests interrupt that sequence at each point,
including a hard process exit, and check that the registry is never left
half-written and that the documented recovery restores a consistent state.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sandbox_repo import GIT_ENV, OWNER_REF, Sandbox, git

from citerift.governance import orchestrator
from citerift.governance.cli import main
from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import Orchestrator, errors

pytestmark = [pytest.mark.simulation, pytest.mark.negative]

REGISTRY = "governance/stage_registry.json"


def _leftover_temp_files(root: Path) -> list[Path]:
    return sorted(root.glob("governance/.stage_registry.json.*.tmp")) + sorted(root.glob(".PROJECT_STATUS.md.*.tmp"))


@pytest.mark.parametrize("fail_at", ["write", "replace"])
def test_interrupted_registry_write_leaves_the_old_registry(
    sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch, fail_at: str
) -> None:
    before = (sandbox.root / REGISTRY).read_bytes()
    if fail_at == "replace":
        monkeypatch.setattr(orchestrator.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    else:
        real_fdopen = os.fdopen

        class FailingFile:
            def __init__(self, fh: object) -> None:
                self.fh = fh

            def __enter__(self) -> FailingFile:
                return self

            def __exit__(self, *exc: object) -> None:
                self.fh.close()  # type: ignore[attr-defined]

            def write(self, text: str) -> None:
                self.fh.write(text[: len(text) // 2])  # type: ignore[attr-defined]
                raise OSError("interrupted")

        monkeypatch.setattr(orchestrator.os, "fdopen", lambda *a, **k: FailingFile(real_fdopen(*a, **k)))
    with pytest.raises(OSError):
        sandbox.go("00", Status.AUTHORIZED)
    assert (sandbox.root / REGISTRY).read_bytes() == before
    assert _leftover_temp_files(sandbox.root) == []
    monkeypatch.undo()
    assert not errors(sandbox.orc().check())


def test_crash_between_registry_and_status_document_is_detected_and_recovered(
    sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = orchestrator._atomic_write
    calls: list[Path] = []

    def second_write_fails(path: Path, text: str) -> None:
        calls.append(path)
        if path.name == "PROJECT_STATUS.md":
            raise OSError("killed")
        real(path, text)

    monkeypatch.setattr(orchestrator, "_atomic_write", second_write_fails)
    with pytest.raises(OSError):
        sandbox.go("00", Status.AUTHORIZED)
    monkeypatch.undo()
    assert [p.name for p in calls] == ["stage_registry.json", "PROJECT_STATUS.md"]
    assert sandbox.registry()["stages"][0]["status"] == "AUTHORIZED"
    assert sandbox.codes(sandbox.orc().check()) == {"STATUS_DOC_OUT_OF_DATE"}
    assert main(["--root", str(sandbox.root), "render-status", "--write"]) == 0
    capsys.readouterr()
    assert not errors(sandbox.orc().check())


def test_hard_exit_during_write_keeps_a_valid_registry(sandbox: Sandbox) -> None:
    """A real process killed (os._exit, no cleanup) just before the rename."""
    before = (sandbox.root / REGISTRY).read_bytes()
    script = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "from citerift.governance import orchestrator\n"
        "from citerift.governance.model import Actor, Status\n"
        "orchestrator.os.replace = lambda *a: os._exit(9)\n"
        "orc = orchestrator.Orchestrator(Path(sys.argv[1]))\n"
        "r = orc.propose('00', Status.AUTHORIZED, actor=Actor.OWNER, owner_ref=sys.argv[2], reason='x')\n"
        "orc.apply(r)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script, str(sandbox.root), OWNER_REF], capture_output=True, text=True, check=False
    )
    assert out.returncode == 9, out.stderr
    assert (sandbox.root / REGISTRY).read_bytes() == before
    leftovers = _leftover_temp_files(sandbox.root)
    assert len(leftovers) == 1, "the killed process leaves its temporary file"
    findings = sandbox.orc().check()
    assert not errors(findings)
    for p in leftovers:
        p.unlink()
    assert sandbox.go("00", Status.AUTHORIZED).allowed


@pytest.mark.parametrize(
    "damage",
    [
        lambda t: t[: len(t) // 2],
        lambda t: "",
        lambda t: t.replace('"status": "ACCEPTED_CLOSED"', '"status": "ACCEPTED_CLOSE"', 1),
        lambda t: t.replace('"history": [', '"history": "not a list", "x": [', 1),
        lambda t: "\ufeff" + t,
    ],
    ids=["truncated", "empty", "bad_enum", "wrong_type", "byte_order_mark"],
)
def test_corrupted_registry_fails_closed_and_git_restores_it(sandbox: Sandbox, damage: object) -> None:
    sandbox.drive_to_accepted("00")
    sandbox.commit("accepted")
    path = sandbox.root / REGISTRY
    good = path.read_text(encoding="utf-8")
    path.write_text(damage(good), encoding="utf-8")  # type: ignore[operator]
    env = {**os.environ, **GIT_ENV}
    out = subprocess.run(
        [sys.executable, "-m", "citerift.governance.cli", "--root", str(sandbox.root), "check"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert out.returncode == 1
    assert "Traceback" not in out.stderr
    git(sandbox.root, "checkout", "--", REGISTRY)
    assert path.read_text(encoding="utf-8") == good
    assert not errors(Orchestrator(sandbox.root).check())


def test_recovery_after_a_lost_commit_is_explicit(sandbox: Sandbox) -> None:
    """A transition applied but never committed: a fresh clone shows the last committed state."""
    sandbox.drive_to_verified("00")
    sandbox.commit("verified")
    assert sandbox.go("00", Status.ACCEPTED_CLOSED).allowed  # applied, not committed
    clone = sandbox.root.parent / "clone"
    subprocess.run(["git", "clone", "-q", str(sandbox.root), str(clone)], check=True, capture_output=True)
    data = Orchestrator(clone).recover()
    assert data["verified_awaiting_owner_acceptance"] == ["00"]
    assert data["consistency"]["errors"] == []
    local = Orchestrator(sandbox.root).recover()
    assert local["completed_and_accepted"] == ["00"]
    assert REGISTRY in (local["uncommitted_changes"] or [])


def test_reopen_and_reverify_after_simulated_session_loss(sandbox: Sandbox) -> None:
    """The correction cycle survives a session restart at every step (fresh object from disk each time)."""
    sandbox.drive_to_accepted("00")
    aid = Orchestrator(sandbox.root).add_amendment(
        "00",
        kind="correction",
        reason="defect found by an independent review",
        evidence_refs=["RISKS.md"],
        owner_ref="cmsg_TESTREOPENREF01",
        at=sandbox.tick(),
    )
    sandbox.commit("amendment")
    assert sandbox.go(
        "00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_TESTREOPENREF01"
    ).allowed
    sandbox.commit("reopened")
    sandbox.write("impl/00.txt", "corrected\n")
    rev = sandbox.commit("correction")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.commit("implemented")
    sandbox.write_evidence("00", rev)
    assert sandbox.go(
        "00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("00"), ci=sandbox.ci(rev)
    ).allowed
    sandbox.commit("verified again")
    data = Orchestrator(sandbox.root).recover()
    assert data["verified_awaiting_owner_acceptance"] == ["00"]
    assert data["authoritative_revisions"]["00"]["verified"] == rev
    assert data["consistency"]["errors"] == []


def test_shallow_clone_fails_closed_without_a_false_staleness_report(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    sandbox.write("notes.txt", "later work\n")
    sandbox.commit("later work")
    clone = sandbox.root.parent / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{sandbox.root}", str(clone)], check=True, capture_output=True
    )
    findings = Orchestrator(clone).check()
    codes = {f.code for f in errors(findings)}
    assert "REVISION_NOT_FOUND" in codes
    assert "VERIFICATION_STALE" not in codes
    assert any("shallow" in f.message for f in findings)
