"""Shared setup of the Step 8 integration tests: real Stage 03 bundles, the attributed Retraction Watch subset index,
real requests, and one SYNTHETIC test detector.

The bundles are the previously exposed design cases of SPECIFICATION.md S-7.4 / VS-1..VS-3 (never a Stage 03
evaluation or holdout bundle). The index is built by Stage 02 ``build`` from ``fixtures/step8/rw_subset.csv``, which
``docs/verification/stage-04/scripts/step8_rw_subset.py`` selected from the pinned snapshot (6 real records,
attributed; no synthetic row).

``synthetic_detector`` is NOT dt-1, has no coherence function and decides nothing scientific: it is a fixed test
mapping (labeled SYNTHETIC in its identity) that lets the Step 8 boundary, ASSEMBLE and VERIFY run end to end before
Step 9 supplies the detector. On an untainted keyed candidate's deciding lookup: ``matched``/``exact``/``retracted``
gives ``RETRACTED_WORK_CITED``; a single key's ``no_record`` gives ``NOT_FOUND_IN_CHECKED_SOURCES``; an
``unavailable`` lookup (single key or pair) gives ``LOOKUP_UNAVAILABLE``; a pair's ``ambiguous_identity`` gives
``IDENTITY_CONFLICT``. Every other candidate gets no claim. The coherence values it writes are test values, not kappa.
"""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from citerift.investigation import ids, sets
from citerift.investigation.adapters.detect import DetectInput, Detection
from citerift.investigation.adapters.plan import STAGE04_IDENTITY, Integration
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.controller import RunResult, open_controller, run_investigation
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.investigation.memory import InvestigationMemory, created_payload
from citerift.retraction.source import load_receipt, parse_receipt
from citerift.retraction.store import build
from citerift.wiki.bundle import open_bundle

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "step8"
RW_MANIFEST = json.loads((FIXTURES / "rw_subset.json").read_text(encoding="utf-8"))
RW_DATA = (FIXTURES / "rw_subset.csv").read_bytes()

AR_OBOKATA = REPO / "tests/stage03/fixtures/observed/ar-76190003"  # VS-2
EN_OBOKATA = REPO / "tests/stage03/fixtures/observed/en-1372543632"  # VS-3
EN_MMR = REPO / "docs/verification/stage-03/demonstrations/bundles/en-1381772671"  # VS-1 (Wakefield)
SUBJECT = "wikipedia_article_revision"
DETECTOR_IDENTITY = "SYNTHETIC-test-detector/1 (not dt-1)"


def build_index(tmp: Path) -> Path:
    """The Stage 02 index of the attributed subset (the receipt is the pinned one, re-pointed at the subset)."""
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / RW_MANIFEST["fixture"]
    path.write_bytes(RW_DATA)
    fields = load_receipt().to_json()
    fields.update(
        path=RW_MANIFEST["fixture"],
        expected_bytes=len(RW_DATA),
        expected_sha256=hashlib.sha256(RW_DATA).hexdigest(),
        git_blob_sha1=hashlib.sha1(f"blob {len(RW_DATA)}\0".encode() + RW_DATA, usedforsecurity=False).hexdigest(),
        attribution=RW_MANIFEST["attribution"],
    )
    return build(path, parse_receipt(fields), tmp / "index").index_path


def memory_root(tmp: Path) -> Path:
    root = tmp / "memory"
    root.mkdir(mode=0o700, parents=True)
    root.chmod(0o700)
    return root


def request(
    bundle: Path, index: Path, root: Path, *, budget: int = DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
) -> dict[str, Any]:
    return {
        "schema": "urn:citerift:schema:investigation:v1:request",
        "schema_version": "2.0.0",
        "mode": "retained_bundle",
        "subject": {"type": SUBJECT, "bundle_path": str(bundle)},
        "index_path": str(index),
        "memory_root": str(root),
        "config": {
            "plan_version": "plan-1",
            "budgets": {"a_max": 3, "f_max": 6},
            "fetch_policy_sha256": None,
            "live_acquire_bound": None,
            "lookup_evidence_budget_bytes": budget,
        },
    }


def create(root: Path, req: dict[str, Any]) -> dict[str, Any]:
    """Create the investigation of a retained-bundle request; return its ``investigation_created`` payload."""
    capture = open_bundle(Path(req["subject"]["bundle_path"])).capture_sha256
    payload = created_payload(req, dict(STAGE04_IDENTITY), bundle_capture_sha256=capture)
    InvestigationMemory.create(root, payload).close()
    return payload


def run(root: Path, payload: Mapping[str, Any], integration: Integration) -> RunResult:
    return run_investigation(
        root, payload["investigation_key"], integration.adapters(), integration.environment(payload)
    )


def committed(root: Path, payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The committed logical records and, by digest, every blob they reference, parsed when it is JSON; its exact
    bytes are under ``"bytes:" + digest`` (read-only)."""
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        recs = [copy.deepcopy(r) for r in mem.view.logical]
        blobs: dict[str, Any] = {}
        for d in mem.view.referenced_blobs():
            data = mem.blobs.get(d)
            try:
                blobs[d] = json.loads(data)
            except ValueError:
                blobs[d] = data
            blobs["bytes:" + d] = data
    return recs, blobs


# The SYNTHETIC test detector ---------------------------------------------------------------------------------------


def _lookup_evidence(obs: str, pointer: str) -> dict[str, Any]:
    return {
        "evidence_id": ids.evidence_id(obs, pointer, "lookup_result"),
        "observation": obs,
        "pointer": pointer,
        "kind": "lookup_result",
        "refs": [],
        "value": None,
    }


def _query(keys: list[dict[str, str]]) -> dict[str, str | None]:
    q: dict[str, str | None] = {"doi": None, "pmid": None}
    for k in keys:
        q[k["scheme"]] = k["normalized"]
    return q


def synthetic_detector(inp: DetectInput) -> Detection:
    lookups = {canon(e["query"]): e["observation"] for e in inp.lookup_plan["lookups"]}
    evidence: dict[str, dict[str, Any]] = {}
    claims = []

    def ev(obs: str, pointer: str) -> str:
        item = _lookup_evidence(obs, pointer)
        evidence[item["evidence_id"]] = item
        return str(item["evidence_id"])

    for cand in inp.candidate_inputs["candidates"]:
        if cand["shape"] == "NONE" or cand["taint"]:
            continue
        obs = lookups[canon(_query(cand["keys"]))]
        result = inp.read_blob(obs)["result"]
        state, identity = result["lookup_state"], result["identity"]["status"]
        status = ((result.get("projection") or {}).get("retraction_status") or {}).get("value")
        pair = cand["shape"] == "PAIR"
        coherence = None
        alternatives: list[dict[str, Any]] = []
        alt_sets: list[list[str]] = []
        if state == "matched" and identity == "exact" and status == "retracted":
            cls, rule, st, value, reasons = "RETRACTED_WORK_CITED", "D-14", "verified_fact", "retracted", []
            supporting = [ev(obs, "/result/projection/retraction_status")]
            coherence = "COHERENT" if pair else None
        elif state == "no_record" and not pair:
            cls, rule, st, value = "NOT_FOUND_IN_CHECKED_SOURCES", "D-16", "uncertain", "not_found_in_checked_sources"
            reasons, supporting = ["NOT_FOUND_IN_CHECKED_SOURCES"], [ev(obs, "/result/lookup_state")]
        elif state == "unavailable":
            cls, rule, st, value, reasons = "LOOKUP_UNAVAILABLE", "D-13", "unavailable", None, ["LOOKUP_QUERY_FAILED"]
            if any(i.get("code") == "LOOKUP_EVIDENCE_LIMIT_EXCEEDED" for i in result["issues"]):
                reasons.append("LOOKUP_EVIDENCE_LIMIT_EXCEEDED")  # S-6.10a
            supporting, coherence = [ev(obs, "/result/lookup_state")], "NOT_DETERMINED" if pair else None
        elif state == "ambiguous_identity" and pair:
            cls, rule, st, value = "IDENTITY_CONFLICT", "D-6", "conflicting", None
            reasons, coherence = ["IDENTITY_WITNESSED", "KEY_RESULTS_DIFFER"], "INCOMPATIBLE"
            supporting = [ev(obs, "/result/identity")]
            for key in cand["keys"]:
                one = lookups[canon(_query([key]))]
                events = inp.read_blob(one)["events"]
                work = {"doi": None, "pmid": None, key["scheme"]: key["normalized"]}
                if events:
                    work = {"doi": events[0]["original_doi"], "pmid": events[0]["original_pmid"]}
                alternatives.append({"value": {"reached_by": dict(key), "work": work}, "supporting_count": 1})
                alt_sets.append([ev(one, "/result/identity")])
        else:
            continue
        value_set = sets.evidence_set(supporting, [], alt_sets)
        es = sha256_hex(canon(value_set))
        claim = {
            "cand_ref": cand["cand_ref"],
            "candidate": {"shape": cand["shape"], "keys": copy.deepcopy(cand["keys"]), "coherence": coherence},
            "class": cls,
            "rule": rule,
            "table_version": "dt-1",
            "status": st,
            "value": value,
            "alternatives": alternatives,
            "reasons": reasons,
            "upstream_reasons": [],
            "evidence_set": es,
            "supporting_count": len(value_set["supporting"]),
            "contradicting_count": 0,
        }
        claim["claim_id"] = ids.claim_id(cand["cand_ref"], cls, rule, "dt-1", es)
        claims.append((claim, value_set))
    return Detection(evidence=tuple(evidence.values()), claims=tuple(claims), identity=DETECTOR_IDENTITY)


TEST_INTEGRATION = Integration(detector=synthetic_detector)


def run_until(root: Path, payload: Mapping[str, Any], integration: Integration, step: str) -> None:
    """Run the investigation one action at a time until ``step`` has committed, then close it (a partial run)."""
    mem, ctl = open_controller(
        root, payload["investigation_key"], integration.adapters(), integration.environment(payload)
    )
    with mem:
        ctl.recover()
        for _ in range(64):
            if ctl.view.step_state(step) == "succeeded":
                return
            ctl.step()
    raise AssertionError(f"{step} did not commit")


class NoNetwork:
    """Refuse every socket connection and name lookup in this process, and count the attempts."""

    def __init__(self, monkeypatch: Any) -> None:
        self.attempts: list[str] = []

        def refuse(name: str) -> Any:
            def _refuse(*args: Any, **kwargs: Any) -> Any:
                self.attempts.append(name)
                raise OSError(f"network refused in this test ({name})")

            return _refuse

        monkeypatch.setattr(socket.socket, "connect", refuse("connect"))
        monkeypatch.setattr(socket.socket, "connect_ex", refuse("connect_ex"))
        monkeypatch.setattr(socket, "create_connection", refuse("create_connection"))
        monkeypatch.setattr(socket, "getaddrinfo", refuse("getaddrinfo"))


def open_bundle_capture(bundle: Path) -> str:
    return open_bundle(bundle).capture_sha256
