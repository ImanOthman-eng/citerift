"""Throwaway git repositories with the real governance layout, for scenario tests."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import REGISTRY_PATH, Orchestrator, TransitionResult

REPO = Path(__file__).resolve().parents[2]
OWNER_REF = "cmsg_TESTOWNERREF0001"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Sandbox",
    "GIT_AUTHOR_EMAIL": "sandbox@example.invalid",
    "GIT_COMMITTER_NAME": "Sandbox",
    "GIT_COMMITTER_EMAIL": "sandbox@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}

DECISIONS = """# Decisions

## D-001 — Sandbox decision
- Status: accepted
- Topic: sandbox
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Sandbox body.
"""

RISKS = """# Risks

## R-001 — Sandbox risk
- Status: open
- Severity: low
- Kind: limitation
- Stage: 00

Sandbox body.
"""

FILLER = (
    "This synthetic evidence document exists only inside a test sandbox. It is padded so that it "
    "exceeds the minimum evidence size and therefore exercises the hash and content checks rather "
    "than the trivial-file check. It records no real result."
)


def git(root: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env=env, check=True)
    return out.stdout.strip()


def fresh_registry() -> dict[str, Any]:
    reg = json.loads((REPO / REGISTRY_PATH).read_text(encoding="utf-8"))
    reg = copy.deepcopy(reg)
    for s in reg["stages"]:
        s.update(
            status="NOT_STARTED",
            authorization=None,
            implementation=None,
            verification=None,
            acceptance=None,
            blockers=[],
            amendments=[],
        )
    reg["history"] = []
    return reg


class Sandbox:
    def __init__(self, root: Path):
        self.root = root
        self.clock = 0
        self.refs = 0
        root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / "schemas", root / "schemas")
        (root / "governance").mkdir()
        self.write("DECISIONS.md", DECISIONS)
        self.write("RISKS.md", RISKS)
        Orchestrator(root, fresh_registry()).write()
        git(root, "init", "-q", "-b", "main")
        self.commit("sandbox init")

    # ------------------------------------------------------------ utilities

    def tick(self) -> str:
        self.clock += 1
        return f"2026-01-01T00:{self.clock // 60:02d}:{self.clock % 60:02d}Z"

    def new_ref(self) -> str:
        """A new owner reference: an amendment records its own owner decision, so it cannot reuse one (X-13)."""
        self.refs += 1
        return f"cmsg_TESTAMENDMENT{self.refs:04d}"

    def orc(self) -> Orchestrator:
        return Orchestrator(self.root)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.root, "rev-parse", "HEAD")

    def head(self) -> str:
        return git(self.root, "rev-parse", "HEAD")

    def registry(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((self.root / REGISTRY_PATH).read_text(encoding="utf-8"))
        return data

    def save_registry(self, reg: dict[str, Any]) -> None:
        (self.root / REGISTRY_PATH).write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")

    def codes(self, findings: list[Any], severity: str = "error") -> set[str]:
        return {f.code for f in findings if f.severity == severity}

    # ------------------------------------------------------------- evidence

    def write_evidence(
        self,
        stage_id: str,
        revision: str,
        *,
        omit: tuple[str, ...] = (),
        handoff_sections: list[str] | None = None,
        handoff_revision: str | None = None,
        report: dict[str, Any] | None = None,
        report_overrides: dict[str, Any] | None = None,
    ) -> None:
        orc = self.orc()
        stage = orc.stage(stage_id)
        policy = orc.registry["policy"]
        vdir = stage["verification_dir"]
        sections = policy["handoff_required_sections"] if handoff_sections is None else handoff_sections
        for name in stage.get("required_artifacts", policy["required_artifacts"]):
            if name in omit:
                continue
            body = f"# {name}\n\n{FILLER}\n\n{FILLER}\n"
            if name == policy["handoff_file"]:
                body += "".join(f"\n## {s}\n\n{FILLER}\n" for s in sections)
                body += f"\nVerified revision: {handoff_revision or revision}\n"
            self.write(f"{vdir}/{name}", body)
        if stage["required_test_suites"] and policy["test_report_file"] not in omit:
            data = report or {
                "format": "citerift.test-report/1",
                "revision": revision,
                "dirty": False,
                "exit_status": 0,
                "totals": {"passed": 10 * len(stage["required_test_suites"])},
                "selection": {"args": ["tests"], "deselected": 0, "complete": True},
                "suites": {s: {"passed": 10} for s in stage["required_test_suites"]},
            }
            data.update(report_overrides or {})
            self.write(f"{vdir}/{policy['test_report_file']}", json.dumps(data, indent=2))

    def gates(self, stage_id: str, result: str = "pass") -> dict[str, Any]:
        stage = self.orc().stage(stage_id)
        ev = f"{stage['verification_dir']}/HANDOFF.md"
        return {g["id"]: {"result": result, "evidence": [ev]} for g in stage["acceptance_gates"]}

    def ci(self, revision: str, conclusion: str = "success") -> dict[str, Any]:
        return {
            "run_url": "https://github.com/example/repo/actions/runs/1",
            "head_sha": revision,
            "conclusion": conclusion,
        }

    # ---------------------------------------------------------- transitions

    def go(self, stage_id: str, target: Status, *, apply: bool = True, **kwargs: Any) -> TransitionResult:
        kwargs.setdefault("reason", f"sandbox {target}")
        kwargs.setdefault("at", self.tick())
        if "actor" not in kwargs:
            owner_edges = {Status.AUTHORIZED, Status.ACCEPTED_CLOSED}
            executor = self.orc().stage(stage_id)["executor"]
            kwargs["actor"] = Actor.OWNER if target in owner_edges else Actor(executor)
        if kwargs["actor"] == Actor.OWNER:
            # An acceptance must cite an owner statement made after the verification, so each
            # sandbox acceptance gets its own reference.
            default_ref = f"cmsg_TESTACCEPTREF{self.clock:04d}" if target == Status.ACCEPTED_CLOSED else OWNER_REF
            kwargs.setdefault("owner_ref", default_ref)
        orc = self.orc()
        result = orc.propose(stage_id, target, **kwargs)
        if apply and result.allowed:
            orc.apply(result)
        return result

    def drive_to_verified(self, stage_id: str) -> str:
        """Authorize, implement and verify a stage with complete evidence. Returns the verified revision."""
        for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
            assert self.go(stage_id, target).allowed
        self.write(f"impl/{stage_id}.txt", f"implementation of stage {stage_id}\n")
        rev = self.commit(f"implement stage {stage_id}")
        assert self.go(stage_id, Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
        self.write_evidence(stage_id, rev)
        stage = self.orc().stage(stage_id)
        ci = self.ci(rev) if stage["executor"] == "engineering-agent" else None
        result = self.go(stage_id, Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=self.gates(stage_id), ci=ci)
        assert result.allowed, [str(f) for f in result.findings]
        self.commit(f"verify stage {stage_id}")
        return rev

    def drive_to_accepted(self, stage_id: str) -> str:
        rev = self.drive_to_verified(stage_id)
        result = self.go(stage_id, Status.ACCEPTED_CLOSED)
        assert result.allowed, [str(f) for f in result.findings]
        self.commit(f"accept stage {stage_id}")
        return rev
