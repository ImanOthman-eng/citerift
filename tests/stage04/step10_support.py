"""Shared setup of the Step 10 tests: real investigations run through the production operations, the command line
driven in process, and journal forgeries that recompute the hash chain (and, where Memory allows it, the verified
content digest), as an adversary with write access to the memory root could.

Bundles and indexes are those of the Step 8 and Step 9 tests (previously exposed design cases, SPEC S-7.4; owner
decision D-5): no Stage 04 holdout and no live capture. Stage 03 challenge, reserve and holdout bundles (some with
locked Stage 03 labels) are reused here as design-exposed Stage 04 development data and are listed in the Stage 04
exposure manifest (Step 12, E-11). Every socket is refused while an
investigation runs (``step8_support.NoNetwork``).
"""

from __future__ import annotations

import copy
import io
import json
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
from test_step9_real import AR_BCAS3, AR_COCHRANE, EN_CONCERN, _build_step9_index

from citerift.investigation import cli, ids, workflow
from citerift.investigation import operations as ops
from citerift.investigation.canonical import canon, loads_record, sha256_hex
from citerift.investigation.errors import CorruptInvestigation
from citerift.investigation.memory import InvestigationMemory

__all__ = ["AR_BCAS3", "AR_COCHRANE", "EN_CONCERN", "build_index9"]

build_index9 = _build_step9_index


@contextmanager
def offline() -> Iterator[S8.NoNetwork]:
    with pytest.MonkeyPatch.context() as mp:
        guard = S8.NoNetwork(mp)
        yield guard
        assert guard.attempts == [], guard.attempts


class Inv:
    """One investigation of a retained bundle, run to its end by ``operations.run`` (the production integration)."""

    def __init__(self, tmp: Path, bundle: Path, index: Path, *, budget: int | None = None) -> None:
        self.tmp = tmp
        self.root = S8.memory_root(tmp)
        self.request = ops.retained_request(bundle, index, self.root, budget=budget)
        with offline():
            self.out, self.code = ops.run(self.request)
        self.key: str = self.out["investigation_key"]

    def copy(self, dest: Path) -> Inv:
        """An independent copy of the memory root (for a test that changes it)."""
        clone = copy.copy(self)
        shutil.copytree(self.root, dest / "memory", symlinks=True)
        clone.root = dest / "memory"
        clone.request = {**self.request, "memory_root": str(clone.root)}
        return clone

    @property
    def dir(self) -> Path:
        return self.root / self.key

    def journal_bytes(self) -> bytes:
        return (self.dir / "journal.jsonl").read_bytes()

    def records(self) -> list[dict[str, Any]]:
        return journal(self.root, self.key)

    def blob(self, digest: str) -> Any:
        return json.loads((self.dir / "blobs" / digest).read_bytes())

    def report_record(self) -> dict[str, Any]:
        return next(r for r in self.records() if r["kind"] == "report_recorded")["payload"]


def journal(root: Path, key: str) -> list[dict[str, Any]]:
    data = (root / key / "journal.jsonl").read_bytes()
    return [loads_record(line) for line in data.split(b"\n") if line]


def rewrite(root: Path, key: str, records: list[dict[str, Any]]) -> None:
    """Write ``records`` as the journal, with ``prev`` and ``digest`` recomputed from the genesis value."""
    out, prev = [], ids.genesis(key)
    for original in records:
        r = copy.deepcopy(original)
        r["prev"] = prev
        r["digest"] = ids.record_digest(r)
        prev = r["digest"]
        out.append(canon(r) + b"\n")
    path = root / key / "journal.jsonl"
    path.chmod(0o600)
    path.write_bytes(b"".join(out))


def put(root: Path, key: str, value: Any) -> str:
    """Publish ``value`` as a blob of the investigation (as Memory names blobs: SHA-256 of the canonical bytes)."""
    data = canon(value)
    d = sha256_hex(data)
    p = root / key / "blobs" / d
    if not p.exists():
        p.write_bytes(data)
        p.chmod(0o444)
    return d


def flip(path: Path) -> None:
    """Change one byte in the middle of a file."""
    path.chmod(0o644)
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))


def forge_report(
    root: Path,
    key: str,
    *,
    manifest: Callable[[dict[str, Any], Callable[[Any], str]], None] | None = None,
    payload: Callable[[dict[str, Any], Callable[[Any], str]], None] | None = None,
) -> bool:
    """Replace the committed report by a forged one: ``manifest(m, put)`` changes the manifest, ``payload(p, put)`` the
    ``report_recorded`` payload; every later reference to the old manifest digest follows, the hash chain is
    recomputed and, when Memory still opens the forged prefix, the verified content digest is re-sealed to ``C(J)``.
    Returns whether it could re-seal (False: Memory already refuses the forged report on open)."""
    recs = journal(root, key)
    at = next(i for i, r in enumerate(recs) if r["kind"] == "report_recorded")
    old = recs[at]["payload"]["report"]
    value = json.loads((root / key / "blobs" / old).read_bytes())

    def publish(v: Any) -> str:
        return put(root, key, v)

    if manifest is not None:
        manifest(value, publish)
    new = publish(value)
    p = copy.deepcopy(recs[at]["payload"])
    p["report"] = new
    if payload is not None:
        payload(p, publish)
    recs[at]["payload"] = p
    for r in recs[at + 1 :]:
        if r["kind"] == "step_succeeded" and old in r["payload"].get("outputs", []):
            r["payload"]["outputs"] = [new if o == old else o for o in r["payload"]["outputs"]]
    verify_at = next((i for i, r in enumerate(recs) if r["kind"] == "step_started" and r["step"] == "VERIFY"), None)
    if verify_at is None:
        rewrite(root, key, recs)
        return False
    rewrite(root, key, recs[:verify_at])
    try:
        with InvestigationMemory.open(root, key, writable=False) as mem:
            digest = mem.view.content_digest()
            f = mem.view
            # VERIFY's step key reads ASSEMBLE's outputs: re-derive it and its manifest, so the forged journal is
            # consistent everywhere a forger can make it so (Step 12, B-07: every command checks every committed
            # step manifest) and only the re-derivation of the report can refuse it.
            ends = [r for r in recs[verify_at:] if r["kind"] == "step_succeeded" and r["step"] == "VERIFY"]
            old_manifest = json.loads((root / key / "blobs" / ends[-1]["payload"]["outputs"][-1]).read_bytes())
            step_key = workflow.step_key(f, "VERIFY", old_manifest["identities"])
            new_manifest = publish(workflow.manifest(f, "VERIFY", step_key, old_manifest["identities"]))
    except CorruptInvestigation:
        rewrite(root, key, recs)
        return False
    for r in recs[verify_at:]:
        if r["kind"] == "verification_recorded":
            r["payload"]["content_digest"] = digest
        if r.get("step") == "VERIFY" and "step_key" in r["payload"]:
            r["payload"]["step_key"] = step_key
        if r["kind"] == "step_succeeded" and r["step"] == "VERIFY":
            r["payload"]["outputs"] = [*r["payload"]["outputs"][:-1], new_manifest]
    rewrite(root, key, recs)
    return True


# The command line, in process ----------------------------------------------------------------------------------------


def run_cli(*argv: str | Path) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def run_json(*argv: str | Path) -> tuple[int, dict[str, Any]]:
    code, out, _ = run_cli(*argv, "--format", "json")
    value = json.loads(out)
    assert set(value) in ({"command", "status", "exit_code", "result"}, {"command", "status", "exit_code", "error"})
    assert value["exit_code"] == code
    assert ops.EXIT[value["status"]] == code
    return code, value


# Projection inputs of a committed investigation ----------------------------------------------------------------------


def projection_inputs(inv: Inv) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    """The report claim entries, the deciding lookup observation of each positive claim (by claim id) and the other
    ``projections.build_bodies`` arguments, all read from the committed investigation."""
    from citerift.investigation import explanations, report
    from citerift.investigation.adapters.acquire import committed_manifest
    from citerift.investigation.adapters.assemble import deciding_query
    from citerift.investigation.adapters.detect import committed_plan
    from citerift.investigation.adapters.lookup import committed_inputs

    with ops.opened(inv.root, inv.key) as mem:
        req = ops.readonly_request(mem, "ASSEMBLE")
        rep = ops.report_of(mem)
        assert rep is not None
        manifest = rep[1]
        entries = list(ops.claim_entries(mem, manifest))
        _, inputs = committed_inputs(req)
        plan = committed_plan(req)
        candidates = {c["cand_ref"]: c for c in inputs["candidates"]}
        lookups = {canon(e["query"]): e["observation"] for e in plan["lookups"]}
        deciding = {}
        for e in entries:
            claim = e["claim"]
            if claim["class"] in report.POSITIVE:
                q = deciding_query(candidates[claim["cand_ref"]])
                deciding[claim["claim_id"]] = req.read_blob(lookups[canon(q)])
        bundle = committed_manifest(req)
        assert req.root is not None
        context = {
            "investigation_id": manifest["investigation_id"],
            "root": copy.deepcopy(dict(req.root)),
            "capture": json.loads(req.read_bytes(bundle["capture"]["blob"])),
            "source_artifact": bundle["source"]["artifact"],
            "outcome": manifest["outcome"],
            "limitations": explanations.limitations(manifest, [e["claim"] for e in entries]),
        }
    return entries, deciding, context


def stored_bodies(inv: Inv) -> list[dict[str, Any]]:
    rec = inv.report_record()
    return [inv.blob(d) for d in inv.blob(rec["projection_set"])["projections"]]
