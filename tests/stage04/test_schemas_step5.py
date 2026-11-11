"""Stage 04 Step 5: contract tests of the investigation schemas (schemas/investigation/v1).

Each test builds a valid record, checks that it validates, then breaks one property and checks that validation
fails. The schemas are loaded with the accepted contracts, wiki and retraction schemas into one registry, exactly as
the Stage 02 and Stage 03 loaders do; no Stage 04 production code exists or is imported. Properties that relate
several records (hash chain, sequence gaps, commit discipline, evidence resolution) are not schema properties: they
are listed in docs/verification/stage-04/review/step5/STEP5_SCHEMA_REVIEW.md as deferred to Investigation Memory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from citerift.contracts.formats import FORMAT_CHECKER
from citerift.contracts.validate import ContractSet, load_contracts
from citerift.investigation import report as report_mod

pytestmark = pytest.mark.contracts

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
SIM = ROOT / "simulations" / "stage04"
P = "urn:citerift:schema:investigation:v1:"
REQUEST, RECORD, CLAIM, REPORT, COMMON = P + "request", P + "journal-record", P + "claim", P + "report", P + "common"
EVIDENCE_SET, PROJECTION_SET = P + "evidence-set", P + "projection-set"
EVIDENCE_BATCH, REPORT_CHUNK = P + "evidence-batch", P + "report-chunk"

# Digest of each accepted upstream schema directory; Step 5 must not change them (owner exit criterion 8).
ACCEPTED_DIRS = ("contracts", "wiki", "retraction")


@cache
def contracts() -> ContractSet:
    schemas: dict[str, dict[str, Any]] = {}
    for d in (*ACCEPTED_DIRS, "investigation"):
        schemas.update(load_contracts(SCHEMAS / d).schemas)
    return ContractSet(schemas)


@cache
def _validator(schema_id: str) -> Draft202012Validator:
    cs = contracts()
    return Draft202012Validator(cs.schemas[schema_id], registry=cs.registry, format_checker=FORMAT_CHECKER)


def errors(instance: Any, schema_id: str) -> list[str]:
    if schema_id == REPORT and isinstance(instance, dict) and "components" not in instance:
        return report_errors(instance)
    return sorted(f"{list(e.absolute_path)}: {e.message[:200]}" for e in _validator(schema_id).iter_errors(instance))


def split(logical: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """The D-054 manifest graph of a logical report (the version 2 shape the cases below are written in): the claims,
    observations and positive works in chunks in the order given (not re-sorted, so an order defect stays), the
    evidence in one batch, every other field copied. Returns the manifest and the blobs by digest."""
    blobs: dict[str, Any] = {}

    def publish(value: Any) -> str:
        d = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        blobs[d.hexdigest()] = value
        return d.hexdigest()

    rest = {k: v for k, v in logical.items() if k not in ("claims", "observations", "evidence", "article_summary")}
    summary = {k: v for k, v in logical.get("article_summary", {}).items() if k != "positive_works"}
    claims = logical.get("claims", [])
    summary["open_questions"] = sum(1 for e in claims if isinstance(e, dict) and e.get("question") is not None)
    collections = {
        "claims": claims,
        "observations": logical.get("observations", []),
        "positive_works": logical.get("article_summary", {}).get("positive_works", []),
    }
    components: dict[str, Any] = {}
    for part, items in collections.items():
        listed = [{"chunk": publish(c), "count": len(c["items"])} for c in report_mod.chunks(part, items)]
        components[part] = {"order": report_mod.ORDERS[part], "count": len(items), "chunks": listed}
    ev = logical.get("evidence", [])
    batch = [{"batch": publish(evidence_batch(ev)), "count": len(ev)}] if ev else []
    components["evidence"] = {"order": report_mod.EVIDENCE_ORDER, "count": len(ev), "batches": batch}
    manifest = {**rest, "article_summary": summary, "components": components}
    return manifest, blobs


def report_errors(logical: dict[str, Any]) -> list[str]:
    """A logical report is valid when its manifest graph is: the manifest schema, every chunk and the evidence batch
    schema, and every graph check of ``report.graph_problem``."""
    manifest, blobs = split(logical)
    found = errors(manifest, REPORT)
    for b in manifest["components"]["evidence"]["batches"]:
        found += errors(blobs[b["batch"]], EVIDENCE_BATCH)
    if found:
        return found

    def read(digest: str) -> Any:
        if digest not in blobs:
            raise ValueError(f"blob {digest} is missing")
        return blobs[digest]

    problem = report_mod.graph_problem(manifest, read)
    return [problem] if problem else []


def ok(instance: Any, schema_id: str) -> None:
    assert errors(instance, schema_id) == []


def bad(instance: Any, schema_id: str) -> None:
    assert errors(instance, schema_id), "expected a validation failure"


def h(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()


# ----- builders of valid records ------------------------------------------------------------------------------------

LIVE_BOUND = {"deadline_ms": 180_000, "op_timeout_ms": 30_000, "safety_allowance_ms": 30_000, "t_acq_ms": 240_000}


def live_config() -> dict[str, Any]:
    return {
        "plan_version": "plan-1",
        "budgets": {"a_max": 3, "f_max": 6},
        "fetch_policy_sha256": h("fetch-policy"),
        "live_acquire_bound": dict(LIVE_BOUND),
        "lookup_evidence_budget_bytes": 16 * 1024 * 1024,
    }


def bundle_config() -> dict[str, Any]:
    return {
        "plan_version": "plan-1",
        "budgets": {"a_max": 3, "f_max": 6},
        "fetch_policy_sha256": None,
        "live_acquire_bound": None,
        "lookup_evidence_budget_bytes": 16 * 1024 * 1024,
    }


def live_request() -> dict[str, Any]:
    return {
        "schema": REQUEST,
        "schema_version": "2.0.0",
        "mode": "live_capture",
        "subject": {"type": "wikipedia_article_revision", "wiki": "ar", "revision_id": 76190003},
        "index_path": "/data/rw/index.sqlite",
        "memory_root": "/var/citerift/memory",
        "config": live_config(),
    }


def bundle_request() -> dict[str, Any]:
    return {
        "schema": REQUEST,
        "schema_version": "2.0.0",
        "mode": "retained_bundle",
        "subject": {"type": "wikipedia_article_revision", "bundle_path": "/data/bundles/ar-76190003"},
        "index_path": "/data/rw/index.sqlite",
        "memory_root": "/var/citerift/memory",
        "config": bundle_config(),
    }


def root() -> dict[str, Any]:
    return {
        "root_id": h("root"),
        "subject": {
            "type": "wikipedia_article_revision",
            "identity": {"wiki": "ar", "page_id": 1234567, "revision_id": 76190003, "capture_sha256": h("capture")},
            "display": {"title": "هاروكو أوبوكاتا", "revision_sha1": "0" * 40},
        },
    }


DOI = {"scheme": "doi", "normalized": "10.1038/nature12969"}
PMID = {"scheme": "pmid", "normalized": "24476881"}


def claim(cls: str = "RETRACTED_WORK_CITED") -> dict[str, Any]:
    """A valid claim of each class (the shapes the reference model produces)."""
    base: dict[str, Any] = {
        "claim_id": h("claim-" + cls),
        "cand_ref": h("cand"),
        "candidate": {"shape": "DOI", "keys": [dict(DOI)], "coherence": None},
        "class": cls,
        "rule": "D-14",
        "table_version": "dt-1",
        "status": "verified_fact",
        "value": "retracted",
        "alternatives": [],
        "reasons": [],
        "upstream_reasons": [],
        "evidence_set": h("set-" + cls),
        "supporting_count": 1,
        "contradicting_count": 0,
    }
    pos = {
        "RETRACTED_WORK_CITED": "retracted",
        "CONCERN_CITED": "expression_of_concern",
        "CORRECTION_CITED": "correction",
        "REINSTATED_WORK_CITED": "reinstated",
    }
    if cls in pos:
        base["value"] = pos[cls]
        return base
    base["value"] = None
    base["status"] = "uncertain"
    if cls == "NOT_FOUND_IN_CHECKED_SOURCES":
        base.update(rule="D-16", value="not_found_in_checked_sources", reasons=["NOT_FOUND_IN_CHECKED_SOURCES"])
    elif cls == "NOTICE_CITED":
        base.update(rule="D-15", reasons=["CITED_IDENTIFIER_IS_NOTICE"])
    elif cls == "IDENTITY_CONFLICT":
        base.update(
            rule="D-6",
            status="conflicting",
            candidate={"shape": "PAIR", "keys": [dict(DOI), dict(PMID)], "coherence": "INCOMPATIBLE"},
            reasons=["IDENTITY_WITNESSED", "KEY_RESULTS_DIFFER"],
            alternatives=[
                {
                    "value": {"reached_by": dict(DOI), "work": {"doi": "10.1038/nature12969", "pmid": "24476891"}},
                    "supporting_count": 1,
                },
                {
                    "value": {"reached_by": dict(PMID), "work": {"doi": "10.1000/other", "pmid": "24476881"}},
                    "supporting_count": 1,
                },
            ],
            supporting_count=2,
        )
    elif cls == "CONTRADICTION_IN_SOURCES":
        base.update(
            rule="D-7",
            status="conflicting",
            reasons=["RETRACTION_EVENT_TYPE_CONFLICT"],
            alternatives=[
                {"value": "retracted", "supporting_count": 1},
                {"value": "correction", "supporting_count": 1},
            ],
        )
    elif cls == "UNRESOLVED_IDENTITY":
        base.update(
            rule="D-9",
            candidate={"shape": "PMID", "keys": [dict(PMID)], "coherence": None},
            reasons=["KEY_NAMES_SEVERAL_WORKS"],
        )
    elif cls == "UNRESOLVED_IDENTIFIER":
        base.update(rule="D-8", reasons=["IDENTIFIER_UNCONFIRMED"])
    elif cls == "UNRESOLVED_STATUS":
        base.update(
            rule="D-11",
            reasons=["CURRENT_EFFECT_NOT_ESTABLISHED"],
            upstream_reasons=[
                {"source": "stage02_projection_basis", "code": "MIXED_CURRENT_EFFECT", "evidence": h("ev-lookup")}
            ],
        )
    elif cls == "LOOKUP_UNAVAILABLE":
        base.update(rule="D-13", status="unavailable", reasons=["LOOKUP_QUERY_FAILED"])
    elif cls == "UNUSED_DEFINITION":
        base.update(rule="D-1", status=None, reasons=["LIST_DEFINED_UNUSED"])
    elif cls == "UNRESOLVED_USE":
        base.update(rule="D-2", status=None, reasons=["NO_BOUND_USE"])
    elif cls == "NO_IDENTIFIER":
        base.update(
            rule="D-3", status=None, candidate={"shape": "NONE", "keys": [], "coherence": None}, supporting_count=0
        )
    return base


CLASSES = [
    "RETRACTED_WORK_CITED",
    "CONCERN_CITED",
    "CORRECTION_CITED",
    "REINSTATED_WORK_CITED",
    "NOT_FOUND_IN_CHECKED_SOURCES",
    "NOTICE_CITED",
    "IDENTITY_CONFLICT",
    "CONTRADICTION_IN_SOURCES",
    "UNRESOLVED_IDENTITY",
    "UNRESOLVED_IDENTIFIER",
    "UNRESOLVED_STATUS",
    "LOOKUP_UNAVAILABLE",
    "UNUSED_DEFINITION",
    "UNRESOLVED_USE",
    "NO_IDENTIFIER",
]
DISPOSITION = {
    **dict.fromkeys(CLASSES[:4], "REPORT_FINDING"),
    "NOT_FOUND_IN_CHECKED_SOURCES": "REPORT_NOT_FOUND",
    "IDENTITY_CONFLICT": "ROUTE_NEEDS_RESOLUTION",
    "CONTRADICTION_IN_SOURCES": "ROUTE_NEEDS_RESOLUTION",
    **dict.fromkeys(["UNRESOLVED_IDENTITY", "UNRESOLVED_IDENTIFIER", "UNRESOLVED_STATUS", "NOTICE_CITED"], "ABSTAIN"),
    "LOOKUP_UNAVAILABLE": "ABSTAIN_UNAVAILABLE",
    **dict.fromkeys(["UNUSED_DEFINITION", "UNRESOLVED_USE", "NO_IDENTIFIER"], "OUT_OF_SCOPE"),
}
CHECKED = [{"source_id": "retraction-watch", "locator": "rw-0123456789abcdef", "retrieved_at": "2026-10-27T00:00:00Z"}]


def entry(cls: str, offset: int = 0) -> dict[str, Any]:
    c = claim(cls)
    question = None
    if cls == "IDENTITY_CONFLICT":
        question = {"question_id": h("q-" + cls), "kind": "identity_conflict"}
    elif cls == "CONTRADICTION_IN_SOURCES":
        question = {"question_id": h("q-" + cls), "kind": "source_conflict"}
    return {
        "claim": c,
        "decision": {"decision_id": h("d-" + cls), "disposition": DISPOSITION[cls]},
        "question": question,
        "unit": {"unit_id": "un-00013", "byte_start": offset, "byte_end": offset + 100, "unit_span_sha256": h("span")},
        "checked_sources": copy.deepcopy(CHECKED) if cls == "NOT_FOUND_IN_CHECKED_SOURCES" else [],
    }


def identities(live: bool = False, extraction_status: str = "complete") -> dict[str, Any]:
    return {
        "request_key": ({"wiki": "ar", "revision_id": 76190003} if live else {"capture_sha256": h("capture")}),
        "extraction": {
            "extractor": {
                "name": "citerift-wiki",
                "version": "0.3.0",
                "profile": {"version": "1", "digest": h("profile")},
                "parsers": {"wikitext": "mwparserfromhell 0.6.6", "html": "html5lib"},
                "normalizer": "citerift-rde-normalizer/1",
            },
            "config_digest": h("x-config"),
            "extraction_digest": h("extraction"),
            "status": extraction_status,
        },
        "index": {
            "snapshot_id": "rw-0123456789abcdef",
            "policy_version": "citerift-rde-policy/1.2.0",
            "lookup_schema_version": "1.0.0",
            "index_sha256": h("index"),
        },
        "stage04": {
            "engine_version": "0.1.0",
            "table_version": "dt-1",
            "plan_version": "plan-1",
            "schema_version": "2.0.0",
        },
        "config": live_config() if live else bundle_config(),
        "config_digest": h("config"),
    }


def report(classes: list[str], live: bool = False, extraction_status: str = "complete") -> dict[str, Any]:
    entries = [entry(c, 200 * i) for i, c in enumerate(classes)]
    routed = any(e["question"] for e in entries)
    unavailable = "LOOKUP_UNAVAILABLE" in classes
    partial = routed or unavailable or extraction_status == "partial"
    limitations = ["CHECKED_SOURCES_ONLY"]
    if routed:
        limitations.append("OPEN_QUESTIONS")
    if unavailable:
        limitations.append("LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES")
    if extraction_status == "partial":
        limitations.append("EXTRACTION_PARTIAL")
    counts: dict[str, int] = {}
    for c in classes:
        counts[c] = counts.get(c, 0) + 1
    positives = [e["claim"]["claim_id"] for e in entries if e["claim"]["class"] in CLASSES[:4]]
    return {
        "schema": REPORT,
        "schema_version": "3.0.0",  # the logical shape of the version 3 report; split() makes its manifest (D-054)
        "investigation_key": h("key"),
        "investigation_id": "0b1e2c3d-4e5f-8a6b-9c7d-0e1f2a3b4c5d",
        "root": root(),
        "terminal_state": "NEEDS_RESOLUTION" if routed else "COMPLETED",
        "outcome": "partial" if partial else "completed",
        "claims": entries,
        "observations": [{"blob": h("obs-lookup"), "obs_kind": "lookup"}],
        "evidence": [
            {
                "evidence_id": h("ev-lookup"),
                "observation": h("obs-lookup"),
                "pointer": "/events/0",
                "kind": "lookup_event",
                "refs": [],
                "value": None,
            }
        ],
        "article_summary": {
            "claims_by_class": counts,
            "positive_works": (
                [
                    {
                        "work": {"doi": "10.1038/nature12968"},
                        "classes": sorted({c for c in classes if c in CLASSES[:4]}),
                        "claim_ids": sorted(positives),
                    }
                ]
                if positives
                else []
            ),
            "snapshot_id": "rw-0123456789abcdef",
        },
        "limitations": limitations,
        "identities": identities(live, extraction_status),
    }


def evidence_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    """A D-053 evidence batch (SPEC 8.8) of ``items``."""
    return {"schema": EVIDENCE_BATCH, "schema_version": "1.0.0", "order": "dependency-topological/evidence-id/1",
            "items": items}  # fmt: skip


def record(kind: str, payload: dict[str, Any], *, step: str | None, attempt: int | None, root_id: str | None,
           seq: int = 5) -> dict[str, Any]:  # fmt: skip
    return {
        "v": 3,
        "seq": 0 if kind == "investigation_created" else seq,
        "prev": h("prev"),
        "kind": kind,
        "step": step,
        "attempt": attempt,
        "at": "2026-11-10T12:00:00Z",
        "root_id": root_id,
        "payload": payload,
        "digest": h("digest"),
    }


def created() -> dict[str, Any]:
    return record(
        "investigation_created",
        {
            "request": live_request(),
            "request_key": {"wiki": "ar", "revision_id": 76190003},
            "investigation_key": h("key"),
            "investigation_id": "0b1e2c3d-4e5f-8a6b-9c7d-0e1f2a3b4c5d",
            "config_digest": h("config"),
            "stage04": {
                "engine_version": "0.1.0",
                "table_version": "dt-1",
                "plan_version": "plan-1",
                "schema_version": "2.0.0",
            },
            "migrated_from": None,
        },
        step=None,
        attempt=None,
        root_id=None,
    )


def acquire_succeeded() -> dict[str, Any]:
    r = root()
    payload = {"step_key": h("k-acquire"), "outputs": [h("bundle")], "root": r}
    return record("step_succeeded", payload, step="ACQUIRE", attempt=1, root_id=r["root_id"])


def acquire_failed(code: str = "ACQUIRE_WALL_CLOCK_EXCEEDED", retryable: bool = True) -> dict[str, Any]:
    payload = {
        "step_key": h("k-acquire"),
        "code": code,
        "retryable": retryable,
        "reason": None,
        "detail": None,
        "not_before": None,
        "wall_clock": {"t_acq_ms": 240_000, "elapsed_ms": 240_001} if code == "ACQUIRE_WALL_CLOCK_EXCEEDED" else None,
    }
    return record("step_failed", payload, step="ACQUIRE", attempt=1, root_id=None)


def claim_record(cls: str = "RETRACTED_WORK_CITED", root_id: str | None = None) -> dict[str, Any]:
    return record("claim_recorded", claim(cls), step="DETECT", attempt=1, root_id=root_id or h("root"))


RECORD_KINDS = [
    "investigation_created",
    "step_started",
    "step_succeeded",
    "step_failed",
    "step_deferred",
    "step_interrupted",
    "stale_detected",
    "observation_recorded",
    "evidence_batch_recorded",
    "claim_recorded",
    "decision_recorded",
    "question_opened",
    "question_closed",
    "report_recorded",
    "claim_superseded",
    "verification_recorded",
]


# ----- schema set -----------------------------------------------------------------------------------------------------


def test_schemas_are_valid_2020_12_and_versioned() -> None:
    cs = contracts()
    mine = {sid: s for sid, s in cs.schemas.items() if sid.startswith(P)}
    assert set(mine) == {COMMON, REQUEST, RECORD, CLAIM, REPORT, EVIDENCE_SET, PROJECTION_SET, EVIDENCE_BATCH,
                         REPORT_CHUNK}  # fmt: skip
    assert [p for p in cs.meta_problems() if p.path.startswith(P)] == []
    for sid, s in mine.items():
        assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema", sid
        # Step 7 closure (D-047, D-048, D-051): the Step 5 schemas are version 2 and the two sets are new; D-053 makes
        # the journal record format 3 and adds the evidence batch.
        expected = {RECORD: "3.0.0", REPORT: "3.0.0", EVIDENCE_SET: "1.0.0", PROJECTION_SET: "1.0.0",
                    EVIDENCE_BATCH: "1.0.0", REPORT_CHUNK: "1.0.0"}  # fmt: skip
        assert s["x-citerift-version"] == expected.get(sid, "2.0.0"), sid
        assert (SCHEMAS / "investigation" / "v1" / f"{sid.removeprefix(P)}.schema.json").is_file()


def test_every_reference_resolves() -> None:
    """Walk each schema and resolve every $ref through the registry (a dangling URN would only fail when reached)."""
    cs = contracts()
    resolver = cs.registry.resolver()

    def walk(node: Any, base: str) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                target = ref if not ref.startswith("#") else base + ref
                resolver.lookup(target)
            for v in node.values():
                walk(v, base)
        elif isinstance(node, list):
            for v in node:
                walk(v, base)

    for sid, s in cs.schemas.items():
        if sid.startswith(P):
            walk(s, sid)


def test_accepted_schemas_untouched() -> None:
    """Step 5 references schemas/contracts, wiki and retraction and changes none of them (git shows no diff)."""
    import subprocess

    out = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "fb39ede", "--", *(f"schemas/{d}" for d in ACCEPTED_DIRS)],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        pytest.skip("git history unavailable: " + out.stderr.strip()[:200])
    assert out.stdout.strip() == ""


# ----- request --------------------------------------------------------------------------------------------------------


def test_valid_retained_bundle_request() -> None:
    ok(bundle_request(), REQUEST)


def test_valid_pinned_live_request() -> None:
    ok(live_request(), REQUEST)


@pytest.mark.negative
def test_title_only_request_rejected() -> None:
    r = live_request()
    r["subject"] = {"type": "wikipedia_article_revision", "wiki": "ar", "title": "هاروكو أوبوكاتا"}
    bad(r, REQUEST)


@pytest.mark.negative
def test_page_id_only_request_rejected() -> None:
    r = live_request()
    r["subject"] = {"type": "wikipedia_article_revision", "wiki": "ar", "page_id": 1234567}
    bad(r, REQUEST)


@pytest.mark.negative
def test_title_beside_revision_rejected() -> None:
    """A title is never part of the request identity, not even next to a pinned revision."""
    r = live_request()
    r["subject"]["title"] = "Haruko Obokata"
    bad(r, REQUEST)


@pytest.mark.negative
@pytest.mark.parametrize("wiki", ["fr", "EN", "", None])
def test_unsupported_wiki_rejected(wiki: Any) -> None:
    r = live_request()
    r["subject"]["wiki"] = wiki
    bad(r, REQUEST)


@pytest.mark.negative
@pytest.mark.parametrize("rev", [0, -1, "76190003", 1.5, None])
def test_revision_must_be_positive_integer(rev: Any) -> None:
    r = live_request()
    r["subject"]["revision_id"] = rev
    bad(r, REQUEST)


@pytest.mark.negative
def test_unknown_subject_type_rejected() -> None:
    for make in (live_request, bundle_request):
        r = make()
        r["subject"]["type"] = "scholarly_work"
        bad(r, REQUEST)
    rt = root()
    rt["subject"]["type"] = "scholarly_work"
    rep = report(["RETRACTED_WORK_CITED"])
    rep["root"] = rt
    bad(rep, REPORT)


@pytest.mark.negative
@pytest.mark.parametrize("schema_id", [REQUEST, REPORT])
def test_unknown_schema_version_rejected(schema_id: str) -> None:
    doc = live_request() if schema_id == REQUEST else report(["RETRACTED_WORK_CITED"])
    current = "3.0.0" if schema_id == REPORT else "2.0.0"  # D-054 made the report version 3
    for version in ("1.0.0", "2.0.0", "2.0.1", "3.0.0", "3.0.1", "2.0", 2):
        if version == current:
            continue
        d = copy.deepcopy(doc)
        d["schema_version"] = version
        bad(d, schema_id)
    d = copy.deepcopy(doc)
    d["schema"] = "urn:citerift:schema:investigation:v2:" + schema_id.rsplit(":", 1)[1]
    bad(d, schema_id)


@pytest.mark.negative
def test_unknown_journal_format_rejected() -> None:
    for v in (0, 1, 2, 4, "3"):
        r = created()
        r["v"] = v
        bad(r, RECORD)


@pytest.mark.negative
def test_live_request_needs_d042_bound_and_bundle_has_none() -> None:
    r = live_request()
    r["config"]["live_acquire_bound"] = None
    bad(r, REQUEST)
    r = live_request()
    r["config"]["fetch_policy_sha256"] = None
    bad(r, REQUEST)
    r = bundle_request()
    r["config"] = live_config()
    bad(r, REQUEST)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("safety_allowance_ms", 0),
        ("safety_allowance_ms", 60_000),
        ("deadline_ms", 0),
        ("deadline_ms", 180.0 + 0.5),
        ("t_acq_ms", None),
    ],
)
def test_live_bound_form(field: str, value: Any) -> None:
    r = live_request()
    r["config"]["live_acquire_bound"][field] = value
    bad(r, REQUEST)


@pytest.mark.negative
@pytest.mark.parametrize(("field", "value"), [("a_max", 4), ("f_max", 7), ("a_max", 2)])
def test_budgets_are_fixed_by_plan_1(field: str, value: int) -> None:
    r = live_request()
    r["config"]["budgets"][field] = value
    bad(r, REQUEST)
    r = live_request()
    r["config"]["plan_version"] = "plan-2"
    bad(r, REQUEST)


@pytest.mark.negative
@pytest.mark.parametrize("path", ["relative/index", "/a\nb", "", "/" + "x" * 5000])
def test_paths_must_be_absolute_and_clean(path: str) -> None:
    r = bundle_request()
    r["index_path"] = path
    bad(r, REQUEST)


@pytest.mark.negative
def test_request_rejects_extra_fields() -> None:
    r = bundle_request()
    r["detection_threshold"] = 0.5
    bad(r, REQUEST)


@pytest.mark.negative
def test_request_key_has_exactly_the_specified_form() -> None:
    """S-4.7: {wiki, revision_id} or {capture_sha256}; never both, never a title, and the form follows the mode."""
    ok(created(), RECORD)
    for key in (
        {"wiki": "ar", "revision_id": 76190003, "capture_sha256": h("capture")},
        {"wiki": "ar"},
        {"title": "Example"},
        {"wiki": "ar", "revision_id": 76190003, "title": "Example"},
        {"capture_sha256": h("capture")},
        {},
    ):
        r = created()
        r["payload"]["request_key"] = key
        bad(r, RECORD)


# ----- journal records and root binding ---------------------------------------------------------------------------


def test_valid_records() -> None:
    ok(created(), RECORD)
    ok(acquire_succeeded(), RECORD)
    ok(acquire_failed(), RECORD)
    for cls in CLASSES:
        ok(claim_record(cls), RECORD)
    ok(record("step_started", {"step_key": h("k")}, step="VALIDATE", attempt=1, root_id=None), RECORD)
    ok(record("step_started", {"step_key": h("k")}, step="ACQUIRE", attempt=9, root_id=None), RECORD)
    ok(
        record(
            "step_deferred",
            {"step_key": h("k"), "code": "DEFERRED_RETRY_AFTER", "not_before": "2026-11-10T13:00:00Z"},
            step="ACQUIRE",
            attempt=2,
            root_id=None,
        ),
        RECORD,
    )
    ok(
        record(
            "observation_recorded",
            {
                "obs_kind": "bundle",
                "blob": h("b"),
                "source_ref": {"engine": "citerift.wiki", "operation": "capture_revision", "locator": None},
            },
            step="ACQUIRE",
            attempt=1,
            root_id=None,
        ),
        RECORD,
    )
    ok(
        record(
            "stale_detected",
            {"changed": ["config"], "recorded": {"config": h("c1")}, "current": {"config": h("c2")}},
            step=None,
            attempt=None,
            root_id=None,
        ),
        RECORD,
    )
    ok(
        record(
            "verification_recorded",
            {"result": "passed", "checks": [{"check": "M_INVARIANTS", "passed": True}], "content_digest": h("C")},
            step="VERIFY",
            attempt=1,
            root_id=h("root"),
        ),
        RECORD,
    )


def test_one_valid_record_of_every_kind() -> None:
    """Every journal kind of SPEC 8.3 has a valid form, so the schema rejects no specified kind outright."""
    kinds = RECORD_KINDS
    rid = h("root")
    examples = {
        "investigation_created": created(),
        "step_started": record("step_started", {"step_key": h("k")}, step="EXTRACT", attempt=1, root_id=rid),
        "step_succeeded": acquire_succeeded(),
        "step_failed": acquire_failed(),
        "step_deferred": record(
            "step_deferred",
            {"step_key": h("k"), "code": "DEFERRED_RETRY_AFTER", "not_before": "2026-11-10T13:00:00Z"},
            step="ACQUIRE",
            attempt=2,
            root_id=None,
        ),
        "step_interrupted": record("step_interrupted", {"step_key": h("k")}, step="LOOKUP", attempt=1, root_id=rid),
        "stale_detected": record(
            "stale_detected",
            {"changed": ["index"], "recorded": {"index": h("i1")}, "current": {"index": h("i2")}},
            step=None,
            attempt=None,
            root_id=rid,
        ),
        "observation_recorded": record(
            "observation_recorded",
            {
                "obs_kind": "extraction",
                "blob": h("x"),
                "source_ref": {"engine": "citerift.wiki", "operation": "extract_bundle", "locator": None},
            },
            step="EXTRACT",
            attempt=1,
            root_id=rid,
        ),
        "evidence_batch_recorded": record(
            "evidence_batch_recorded",
            {"batch": h("b"), "batch_index": 0, "batch_total": 1, "evidence_count": 1},
            step="NORMALIZE",
            attempt=1,
            root_id=rid,
        ),
        "claim_recorded": claim_record(),
        "decision_recorded": record(
            "decision_recorded",
            {"decision_id": h("d"), "claim_id": h("c"), "disposition": "ROUTE_NEEDS_RESOLUTION"},
            step="DETECT",
            attempt=1,
            root_id=rid,
        ),
        "question_opened": record(
            "question_opened",
            {"question_id": h("q"), "claim_id": h("c"), "kind": "source_conflict"},
            step="DETECT",
            attempt=1,
            root_id=rid,
        ),
        "question_closed": record(
            "question_closed",
            {"question_id": h("q"), "claim_id": h("c"), "kind": "identity_conflict", "evidence": [h("e2")]},
            step="DETECT",
            attempt=1,
            root_id=rid,
        ),
        "report_recorded": record(
            "report_recorded",
            {"report": h("r"), "projection_set": h("p"), "projection_count": 1},
            step="ASSEMBLE",
            attempt=1,
            root_id=rid,
        ),
        "claim_superseded": record(
            "claim_superseded",
            {"old_claim_id": h("c1"), "new_claim_id": h("c2"), "reason": "NEW_EVIDENCE", "new_evidence": [h("e3")]},
            step="DETECT",
            attempt=1,
            root_id=rid,
        ),
        "verification_recorded": record(
            "verification_recorded",
            {"result": "failed", "checks": [{"check": "M_INVARIANTS", "passed": False}], "content_digest": None},
            step="VERIFY",
            attempt=1,
            root_id=rid,
        ),
    }
    assert set(examples) == set(kinds) == set(contracts().schemas[RECORD]["properties"]["kind"]["enum"])
    for kind, rec in examples.items():
        assert rec["kind"] == kind
        ok(rec, RECORD)


@pytest.mark.negative
def test_unbound_root_allowed_only_before_acquire_commit() -> None:
    # Pre-bind records: genesis, VALIDATE, ACQUIRE attempts that did not succeed, and ACQUIRE's bundle observation.
    r = created()
    r["root_id"] = h("root")
    bad(r, RECORD)
    r = record("step_started", {"step_key": h("k")}, step="VALIDATE", attempt=1, root_id=h("root"))
    bad(r, RECORD)
    r = acquire_failed()
    r["root_id"] = h("root")
    bad(r, RECORD)
    # The committing record binds the root and carries it.
    r = acquire_succeeded()
    r["root_id"] = None
    bad(r, RECORD)
    r = acquire_succeeded()
    r["payload"]["root"] = None
    bad(r, RECORD)
    # After the bind every step's records carry the root.
    for step in ("EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY"):
        bad(record("step_started", {"step_key": h("k")}, step=step, attempt=1, root_id=None), RECORD)


@pytest.mark.negative
@pytest.mark.parametrize(
    "kind",
    [
        "claim_recorded",
        "evidence_batch_recorded",
        "decision_recorded",
        "question_opened",
        "report_recorded",
        "verification_recorded",
    ],
)
def test_scientific_content_without_bound_root_rejected(kind: str) -> None:
    payloads: dict[str, tuple[str, dict[str, Any]]] = {
        "claim_recorded": ("DETECT", claim()),
        "evidence_batch_recorded": (
            "NORMALIZE",
            {"batch": h("b"), "batch_index": 0, "batch_total": 1, "evidence_count": 1},
        ),
        "decision_recorded": ("DETECT", {"decision_id": h("d"), "claim_id": h("c"), "disposition": "REPORT_FINDING"}),
        "question_opened": ("DETECT", {"question_id": h("q"), "claim_id": h("c"), "kind": "identity_conflict"}),
        "report_recorded": ("ASSEMBLE", {"report": h("r"), "projection_set": h("p"), "projection_count": 0}),
        "verification_recorded": (
            "VERIFY",
            {"result": "passed", "checks": [{"check": "M_INVARIANTS", "passed": True}], "content_digest": h("C")},
        ),
    }
    step, payload = payloads[kind]
    ok(record(kind, payload, step=step, attempt=1, root_id=h("root")), RECORD)
    bad(record(kind, payload, step=step, attempt=1, root_id=None), RECORD)
    # Before the bind, no step may write them: ACQUIRE and VALIDATE records are unbound by construction.
    bad(record(kind, payload, step="ACQUIRE", attempt=1, root_id=None), RECORD)
    bad(record(kind, payload, step="VALIDATE", attempt=1, root_id=None), RECORD)


@pytest.mark.negative
@pytest.mark.parametrize("field", ["prev", "digest", "root_id"])
@pytest.mark.parametrize("value", ["", "abc", "A" * 64, "g" * 64, "0" * 63, "0" * 65, "0" * 64 + "\n"])
def test_malformed_digest_rejected(field: str, value: str) -> None:
    r = acquire_succeeded()
    r[field] = value
    bad(r, RECORD)


@pytest.mark.negative
def test_malformed_digest_inside_payloads_rejected() -> None:
    r = acquire_succeeded()
    r["payload"]["root"]["subject"]["identity"]["capture_sha256"] = "XYZ"
    bad(r, RECORD)
    r = claim_record()
    r["payload"]["evidence_set"] = "not-a-digest"
    bad(r, RECORD)
    r = bundle_request()
    r["config"] = live_config()
    r["mode"] = "live_capture"
    r["subject"] = {"type": "wikipedia_article_revision", "wiki": "en", "revision_id": 1}
    r["config"]["fetch_policy_sha256"] = "0" * 63
    bad(r, REQUEST)


@pytest.mark.negative
def test_journal_sequencing_shape() -> None:
    r = created()
    r["seq"] = 1
    bad(r, RECORD)
    for seq in (0, -1, 1.5, "5", None, True):
        r = acquire_failed()
        r["seq"] = seq
        bad(r, RECORD)
    # Draft 2020-12 counts 1.0 as an integer, so the schema cannot tell 1.0 from 1.
    # Investigation Memory's strict reader refuses the float token (SR-12 in the schema review, MM 2.1).
    r = acquire_failed()
    r["seq"] = 1.0
    ok(r, RECORD)
    r = acquire_failed()
    r["attempt"] = 10
    bad(r, RECORD)
    r = record("step_started", {"step_key": h("k")}, step="EXTRACT", attempt=4, root_id=h("root"))
    bad(r, RECORD)
    r = record("step_started", {"step_key": h("k")}, step="EXTRACT", attempt=None, root_id=h("root"))
    bad(r, RECORD)
    r = created()
    r["step"] = "VALIDATE"
    bad(r, RECORD)
    r = acquire_failed()
    r["kind"] = "step_crashed"
    bad(r, RECORD)
    r = created()
    del r["prev"]
    bad(r, RECORD)


@pytest.mark.negative
def test_content_records_belong_to_their_step() -> None:
    bad(record("claim_recorded", claim(), step="LOOKUP", attempt=1, root_id=h("root")), RECORD)
    obs = {
        "obs_kind": "lookup",
        "blob": h("b"),
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": None},
    }
    ok(record("observation_recorded", obs, step="LOOKUP", attempt=1, root_id=h("root")), RECORD)
    bad(record("observation_recorded", obs, step="EXTRACT", attempt=1, root_id=h("root")), RECORD)
    obs2 = copy.deepcopy(obs)
    obs2["source_ref"]["engine"] = "citerift.wiki"
    bad(record("observation_recorded", obs2, step="LOOKUP", attempt=1, root_id=h("root")), RECORD)
    deferred = {"step_key": h("k"), "code": "DEFERRED_RETRY_AFTER", "not_before": "2026-11-10T13:00:00Z"}
    bad(record("step_deferred", deferred, step="EXTRACT", attempt=1, root_id=h("root")), RECORD)


@pytest.mark.negative
def test_payload_must_match_kind() -> None:
    r = acquire_failed()
    r["kind"] = "step_succeeded"
    bad(r, RECORD)
    r = claim_record()
    r["payload"] = {"anything": True}
    bad(r, RECORD)
    r = claim_record()
    r["payload"]["extra"] = 1
    bad(r, RECORD)


# ----- D-042 representation -----------------------------------------------------------------------------------------


def test_wall_clock_failure_form() -> None:
    ok(acquire_failed("ACQUIRE_WALL_CLOCK_EXCEEDED", retryable=True), RECORD)
    # Retryability is not fixed by the schema (D-042: terminal when Retry-After safety cannot be proven).
    ok(acquire_failed("ACQUIRE_WALL_CLOCK_EXCEEDED", retryable=False), RECORD)
    r = acquire_failed()
    r["payload"]["not_before"] = "2026-11-10T13:00:00Z"
    ok(r, RECORD)


@pytest.mark.negative
def test_wall_clock_failure_constraints() -> None:
    r = acquire_failed()
    r["payload"]["wall_clock"] = None
    bad(r, RECORD)
    r = acquire_failed()
    del r["payload"]["not_before"]
    bad(r, RECORD)
    r = acquire_failed("HTTP_TIMEOUT")
    r["payload"]["wall_clock"] = {"t_acq_ms": 240_000, "elapsed_ms": 240_001}
    bad(r, RECORD)
    for step in ("VALIDATE", "EXTRACT", "LOOKUP", "VERIFY"):
        r = acquire_failed()
        r["step"] = step
        r["root_id"] = None if step == "VALIDATE" else h("root")
        del r["payload"]["not_before"]
        bad(r, RECORD)
    # A killed attempt never commits: the code never appears on step_succeeded.
    r = acquire_succeeded()
    r["payload"]["code"] = "ACQUIRE_WALL_CLOCK_EXCEEDED"
    bad(r, RECORD)


@pytest.mark.negative
def test_retryability_by_step() -> None:
    r = record(
        "step_failed",
        {
            "step_key": h("k"),
            "code": "ADAPTER_INCONSISTENT",
            "retryable": True,
            "reason": None,
            "detail": None,
            "wall_clock": None,
        },
        step="DETECT",
        attempt=1,
        root_id=h("root"),
    )
    bad(r, RECORD)
    r["payload"]["retryable"] = False
    ok(r, RECORD)
    r["payload"]["code"] = "HTTP_TIMEOUT"
    bad(r, RECORD)
    r = acquire_failed("RETRY_BUDGET_EXHAUSTED", retryable=True)
    bad(r, RECORD)
    r = acquire_failed("REVISION_NOT_FOUND", retryable=True)
    bad(r, RECORD)
    ok(acquire_failed("REVISION_NOT_FOUND", retryable=False), RECORD)
    r = record(
        "step_failed",
        {
            "step_key": h("k"),
            "code": "INPUT_INVALID",
            "retryable": False,
            "reason": "TITLE_ONLY",
            "detail": None,
            "wall_clock": None,
        },
        step="VALIDATE",
        attempt=1,
        root_id=None,
    )
    bad(r, RECORD)
    r["payload"]["reason"] = "REVISION_NOT_PINNED"
    ok(r, RECORD)


def test_config_identity_carries_the_bound() -> None:
    rep = report(["RETRACTED_WORK_CITED"], live=True)
    ok(rep, REPORT)
    assert rep["identities"]["config"]["live_acquire_bound"]["t_acq_ms"] == 240_000
    rep["identities"]["config"]["live_acquire_bound"] = None
    rep["identities"]["config"]["fetch_policy_sha256"] = None
    bad(rep, REPORT)
    rep = report(["RETRACTED_WORK_CITED"], live=False)
    rep["identities"]["config"] = live_config()
    bad(rep, REPORT)


@pytest.mark.negative
def test_stale_and_config_identity_fields_retained() -> None:
    rep = report(["RETRACTED_WORK_CITED"])
    for field in ("request_key", "extraction", "index", "stage04", "config", "config_digest"):
        r = copy.deepcopy(rep)
        del r["identities"][field]
        bad(r, REPORT)
    for field in ("extractor", "config_digest", "extraction_digest", "status"):
        r = copy.deepcopy(rep)
        del r["identities"]["extraction"][field]
        bad(r, REPORT)
    for field in ("snapshot_id", "policy_version", "lookup_schema_version", "index_sha256"):
        r = copy.deepcopy(rep)
        del r["identities"]["index"][field]
        bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["identities"]["stage04"]["table_version"] = "dt-2"
    bad(r, REPORT)
    stale = record(
        "stale_detected", {"changed": [], "recorded": {}, "current": {}}, step=None, attempt=None, root_id=None
    )
    bad(stale, RECORD)
    stale["payload"] = {"changed": ["title"], "recorded": {}, "current": {}}
    bad(stale, RECORD)


# ----- claims ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cls", CLASSES)
def test_valid_claim_per_class(cls: str) -> None:
    ok(claim(cls), CLAIM)


@pytest.mark.negative
@pytest.mark.parametrize("cls", ["NOT_RETRACTED", "CLEAN", "NO_RETRACTION", "", "retracted_work_cited"])
def test_invalid_claim_class_rejected(cls: str) -> None:
    c = claim()
    c["class"] = cls
    bad(c, CLAIM)


@pytest.mark.negative
@pytest.mark.parametrize("value", ["retracted", "not_found_in_checked_sources", "not_retracted", True, False])
def test_identity_conflict_carries_no_scientific_value(value: Any) -> None:
    c = claim("IDENTITY_CONFLICT")
    c["value"] = value
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["alternatives"][0]["value"] = "retracted"
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["status"] = "verified_fact"
    bad(c, CLAIM)


@pytest.mark.negative
def test_identity_conflict_shape() -> None:
    c = claim("IDENTITY_CONFLICT")
    c["candidate"]["coherence"] = "COHERENT"
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["alternatives"] = c["alternatives"][:1]
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["alternatives"][1]["supporting_count"] = 0
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["reasons"] = ["KEY_RESULTS_DIFFER"]
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["candidate"] = {"shape": "DOI", "keys": [dict(DOI)], "coherence": None}
    bad(c, CLAIM)
    c = claim("IDENTITY_CONFLICT")
    c["alternatives"].reverse()
    bad(c, CLAIM)


@pytest.mark.negative
def test_no_global_negative_is_representable() -> None:
    for value in ("not_retracted", "clean", "safe", False):
        c = claim()
        c["value"] = value
        bad(c, CLAIM)
    c = claim()
    c["not_retracted"] = True
    bad(c, CLAIM)
    rep = report(["NOT_FOUND_IN_CHECKED_SOURCES"])
    ok(rep, REPORT)
    for field, value in (("clean", True), ("no_retracted_citations", True), ("summary", "No retracted citations.")):
        r = copy.deepcopy(rep)
        r[field] = value
        bad(r, REPORT)
        r = copy.deepcopy(rep)
        r["article_summary"][field] = value
        bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["limitations"].append("NO_RETRACTED_CITATIONS")
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["article_summary"]["claims_by_class"]["CLEAN"] = 1
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["outcome"] = "clean"
    bad(r, REPORT)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("cls", "field", "value"),
    [
        ("RETRACTED_WORK_CITED", "value", "correction"),
        ("RETRACTED_WORK_CITED", "status", "uncertain"),
        ("RETRACTED_WORK_CITED", "rule", "D-16"),
        ("RETRACTED_WORK_CITED", "supporting_count", 0),
        ("NOT_FOUND_IN_CHECKED_SOURCES", "status", "verified_fact"),
        ("NOT_FOUND_IN_CHECKED_SOURCES", "reasons", ["NOT_FOUND_IN_CHECKED_SOURCES", "IDENTIFIER_UNCONFIRMED"]),
        ("NOT_FOUND_IN_CHECKED_SOURCES", "reasons", ["NOT_FOUND_IN_CHECKED_SOURCES", "LOOKUP_PARTIAL"]),
        ("NOTICE_CITED", "value", "retracted"),
        ("LOOKUP_UNAVAILABLE", "value", "not_found_in_checked_sources"),
        ("LOOKUP_UNAVAILABLE", "status", "uncertain"),
        ("UNRESOLVED_STATUS", "reasons", ["STAGE02_BASIS_REASONS"]),
        ("UNRESOLVED_USE", "reasons", ["USE_NOT_ESTABLISHED"]),
        ("UNUSED_DEFINITION", "reasons", ["DEFINITION_UNUSED"]),
        ("LOOKUP_UNAVAILABLE", "reasons", ["LOOKUP_UNAVAILABLE"]),
        ("UNRESOLVED_IDENTITY", "candidate", {"shape": "DOI", "keys": [DOI], "coherence": None}),
        ("CONTRADICTION_IN_SOURCES", "alternatives", []),
        ("UNUSED_DEFINITION", "status", "uncertain"),
        ("NO_IDENTIFIER", "candidate", {"shape": "DOI", "keys": [DOI], "coherence": None}),
        ("UNRESOLVED_STATUS", "rule", "D-17"),
        ("UNRESOLVED_STATUS", "rule", "D-5"),
    ],
)
def test_claim_class_functions_enforced(cls: str, field: str, value: Any) -> None:
    c = claim(cls)
    c[field] = value
    bad(c, CLAIM)


@pytest.mark.negative
def test_simulation_placeholders_are_not_reason_codes() -> None:
    """The four Step 4 placeholders are not production reason codes (STEP5_PLACEHOLDER_MAPPING.md)."""
    common = contracts().schemas[COMMON]["$defs"]["reason"]["enum"]
    for placeholder in ("DEFINITION_UNUSED", "USE_NOT_ESTABLISHED", "STAGE02_BASIS_REASONS", "LOOKUP_UNAVAILABLE"):
        assert placeholder not in common
    c = claim("UNRESOLVED_STATUS")
    c["upstream_reasons"][0]["source"] = "stage04"
    bad(c, CLAIM)


@pytest.mark.negative
def test_d043_reason_vocabulary() -> None:
    """D-043: the v1 names are RETRACTION_EVENT_TYPE_CONFLICT (D-7) and CURRENT_EFFECT_NOT_ESTABLISHED (D-11); the
    Step 5 names are not v1 reason codes. SOURCE_TYPE_CONFLICT stays a valid Stage 02 basis code in upstream_reasons."""
    common = contracts().schemas[COMMON]["$defs"]["reason"]["enum"]
    for new_name in ("RETRACTION_EVENT_TYPE_CONFLICT", "CURRENT_EFFECT_NOT_ESTABLISHED", "LOOKUP_QUERY_FAILED"):
        assert new_name in common
    for old_name in ("SOURCE_TYPE_CONFLICT", "STATUS_NOT_ESTABLISHED"):
        assert old_name not in common
    for cls, old_name in (
        ("CONTRADICTION_IN_SOURCES", "SOURCE_TYPE_CONFLICT"),
        ("UNRESOLVED_STATUS", "STATUS_NOT_ESTABLISHED"),
    ):
        c = claim(cls)
        c["reasons"] = [old_name]
        bad(c, CLAIM)
    c = claim("UNRESOLVED_STATUS")
    c["upstream_reasons"][0]["code"] = "SOURCE_TYPE_CONFLICT"
    ok(c, CLAIM)


@pytest.mark.negative
def test_d048_lookup_evidence_limit_reason_belongs_to_lookup_unavailable_only() -> None:
    """D-048: an over-budget lookup makes the candidate LOOKUP_UNAVAILABLE with the reason
    LOOKUP_EVIDENCE_LIMIT_EXCEEDED (besides LOOKUP_QUERY_FAILED); no other class carries that reason."""
    assert "LOOKUP_EVIDENCE_LIMIT_EXCEEDED" in contracts().schemas[COMMON]["$defs"]["reason"]["enum"]
    c = claim("LOOKUP_UNAVAILABLE")
    c["reasons"] = ["LOOKUP_QUERY_FAILED", "LOOKUP_EVIDENCE_LIMIT_EXCEEDED"]
    ok(c, CLAIM)
    c["reasons"] = ["LOOKUP_EVIDENCE_LIMIT_EXCEEDED"]
    bad(c, CLAIM)  # LOOKUP_QUERY_FAILED stays required (STEP5_PLACEHOLDER_MAPPING.md)
    for cls in ("UNRESOLVED_STATUS", "NOT_FOUND_IN_CHECKED_SOURCES", "RETRACTED_WORK_CITED"):
        c = claim(cls)
        c["reasons"] = [*c["reasons"], "LOOKUP_EVIDENCE_LIMIT_EXCEEDED"]
        bad(c, CLAIM)


@pytest.mark.negative
def test_d043_unit_evidence_carries_the_stage04_span_hash() -> None:
    """D-043 (SR-03): unit evidence holds the Stage-04-derived span hash and the source artifact it was derived from."""
    payload = {
        "evidence_id": h("e"),
        "observation": h("o"),
        "pointer": "/units/0",
        "kind": "unit",
        "refs": [],
        "value": {"source_artifact": h("src"), "unit_span_sha256": h("span")},
    }
    ok(evidence_batch([payload]), EVIDENCE_BATCH)
    for value in (None, {"unit_span_sha256": h("span")}, {"source_artifact": h("src")},
                  {"source_artifact": h("src"), "unit_span_sha256": "0" * 63},
                  {"source_artifact": h("src"), "unit_span_sha256": h("span"), "raw_sha256": h("span")}):  # fmt: skip
        bad(evidence_batch([{**payload, "value": value}]), EVIDENCE_BATCH)
    rep = report(["RETRACTED_WORK_CITED"])
    ok(rep, REPORT)
    r = copy.deepcopy(rep)
    r["claims"][0]["unit"]["raw_sha256"] = r["claims"][0]["unit"].pop("unit_span_sha256")
    bad(r, REPORT)


# ----- reports and NEEDS_RESOLUTION ---------------------------------------------------------------------------------


def test_valid_reports() -> None:
    ok(report(["RETRACTED_WORK_CITED", "NOTICE_CITED", "NOT_FOUND_IN_CHECKED_SOURCES", "UNUSED_DEFINITION"]), REPORT)
    ok(report(["RETRACTED_WORK_CITED", "IDENTITY_CONFLICT"]), REPORT)
    ok(report(["CONTRADICTION_IN_SOURCES"]), REPORT)
    ok(report(["LOOKUP_UNAVAILABLE"]), REPORT)
    ok(report(["RETRACTED_WORK_CITED"], extraction_status="partial"), REPORT)
    ok(report(CLASSES, live=True), REPORT)


@pytest.mark.negative
def test_needs_resolution_represented_as_completed_rejected() -> None:
    rep = report(["RETRACTED_WORK_CITED", "IDENTITY_CONFLICT"])
    assert rep["terminal_state"] == "NEEDS_RESOLUTION"
    r = copy.deepcopy(rep)
    r["terminal_state"] = "COMPLETED"
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["outcome"] = "completed"
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["claims"][1]["question"] = None
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["claims"][1]["decision"]["disposition"] = "ABSTAIN"
    bad(r, REPORT)
    clean = report(["RETRACTED_WORK_CITED"])
    clean["terminal_state"] = "NEEDS_RESOLUTION"
    bad(clean, REPORT)
    for state in ("FAILED", "STALE", "CORRUPT", "RUNNING", "BLOCKED", "CREATED"):
        r = copy.deepcopy(rep)
        r["terminal_state"] = state
        bad(r, REPORT)


@pytest.mark.negative
def test_outcome_partial_conditions() -> None:
    r = report(["LOOKUP_UNAVAILABLE"])
    r["outcome"] = "completed"
    bad(r, REPORT)
    r = report(["RETRACTED_WORK_CITED"], extraction_status="partial")
    r["outcome"] = "completed"
    bad(r, REPORT)
    r = report(["RETRACTED_WORK_CITED"])
    r["outcome"] = "partial"
    bad(r, REPORT)
    for code in ("OPEN_QUESTIONS", "LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES", "EXTRACTION_PARTIAL"):
        r = report(["RETRACTED_WORK_CITED"])
        r["limitations"].append(code)
        bad(r, REPORT)


@pytest.mark.negative
def test_disposition_and_question_follow_class() -> None:
    for cls in CLASSES:
        rep = report([cls])
        ok(rep, REPORT)
        for disp in {"REPORT_FINDING", "REPORT_NOT_FOUND", "ABSTAIN", "OUT_OF_SCOPE"} - {DISPOSITION[cls]}:
            r = copy.deepcopy(rep)
            r["claims"][0]["decision"]["disposition"] = disp
            bad(r, REPORT)
        if DISPOSITION[cls] != "ROUTE_NEEDS_RESOLUTION":
            r = copy.deepcopy(rep)
            r["claims"][0]["question"] = {"question_id": h("q"), "kind": "identity_conflict"}
            bad(r, REPORT)


@pytest.mark.negative
def test_not_found_names_the_checked_sources() -> None:
    rep = report(["NOT_FOUND_IN_CHECKED_SOURCES"])
    r = copy.deepcopy(rep)
    r["claims"][0]["checked_sources"] = []
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    del r["article_summary"]["snapshot_id"]
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["limitations"] = []
    bad(r, REPORT)


@pytest.mark.negative
def test_report_requires_bound_root() -> None:
    r = report(["RETRACTED_WORK_CITED"])
    r["root"] = None
    bad(r, REPORT)
    r = report(["RETRACTED_WORK_CITED"])
    r["root"]["subject"]["identity"]["title"] = "x"
    bad(r, REPORT)
    r = report(["RETRACTED_WORK_CITED"])
    del r["root"]["subject"]["identity"]["capture_sha256"]
    bad(r, REPORT)


@pytest.mark.negative
def test_evidence_provenance_cannot_be_omitted() -> None:
    rep = report(["RETRACTED_WORK_CITED"])
    for field in ("observation", "pointer", "kind", "refs"):
        r = copy.deepcopy(rep)
        del r["evidence"][0][field]
        bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["evidence"][0]["pointer"] = "events/0"
    bad(r, REPORT)
    r = copy.deepcopy(rep)
    r["evidence"][0]["value"] = "retracted"
    bad(r, REPORT)
    for field in ("evidence_set", "supporting_count", "contradicting_count"):
        c = claim()
        del c[field]
        bad(c, CLAIM)


# ----- the schemas agree with the frozen Step 4 reference model -----------------------------------------------------

PLACEHOLDER = {
    "DEFINITION_UNUSED": ["LIST_DEFINED_UNUSED"],
    "USE_NOT_ESTABLISHED": ["NO_BOUND_USE"],
    "STAGE02_BASIS_REASONS": ["CURRENT_EFFECT_NOT_ESTABLISHED"],
    "LOOKUP_UNAVAILABLE": ["LOOKUP_QUERY_FAILED"],
    # Not a placeholder: the frozen Step 4 model's D-7 reason, renamed for v1 by owner decision D-043.
    "SOURCE_TYPE_CONFLICT": ["RETRACTION_EVENT_TYPE_CONFLICT"],
}


def _model() -> tuple[Any, Any, Any, Any]:
    sys.path.insert(0, str(SIM))
    try:
        import decision_space as S
        import dt1_reference as R
        import stage02_abstraction as A
    finally:
        sys.path.remove(str(SIM))
    return R, A, S, None


def _claim_of(case: Any, dec: dict[str, Any], R: Any) -> dict[str, Any]:
    keys = {"NONE": [], "DOI": [dict(DOI)], "PMID": [dict(PMID)], "PAIR": [dict(DOI), dict(PMID)]}[case.shape]
    reasons: list[str] = []
    for r in dec["reasons"]:
        reasons += PLACEHOLDER.get(r, [r])
    c = claim()
    c.update(
        candidate={"shape": case.shape, "keys": keys, "coherence": R.coherence(case)},
        **{"class": dec["class"]},
        rule=dec["rule"],
        status=dec["status"],
        value=dec["value"],
        reasons=sorted(set(reasons)),
        supporting_count=1 if case.shape != "NONE" else 0,
        alternatives=[],
    )
    if dec["rule"] == "D-11":
        c["upstream_reasons"] = [
            {"source": "stage02_projection_basis", "code": "MIXED_CURRENT_EFFECT", "evidence": h("ev")}
        ]
    if dec["class"] == "IDENTITY_CONFLICT":
        c["alternatives"] = claim("IDENTITY_CONFLICT")["alternatives"]
    if dec["class"] == "CONTRADICTION_IN_SOURCES":
        c["alternatives"] = claim("CONTRADICTION_IN_SOURCES")["alternatives"]
    return c


@pytest.mark.simulation
def test_every_valid_reference_decision_is_a_valid_claim() -> None:
    """Every decision the Step 4 reference model makes on the valid domain (244,884 cases) maps, with the placeholder
    mapping and nothing else, to a claim that validates; and the distinct decisions are all covered. This checks that
    the schemas do not reject a state the specification allows (review question 'valid states that cannot validate')."""
    R, A, S, _ = _model()
    seen: dict[str, Any] = {}
    n_valid = 0

    def visit(case: Any) -> None:
        nonlocal n_valid
        if not A.valid(case):
            return
        n_valid += 1
        dec = R.decide(case)
        assert dec["kind"] != "failure", case
        sig = json.dumps([case.shape, R.coherence(case), dec["rule"], dec["class"], sorted(dec["reasons"])])
        seen.setdefault(sig, (case, dec))

    for shape in ("NONE", "DOI", "PMID"):
        for use in R.USES:
            for t in range(len(S.TAINTS)):
                for case in S.iter_chunk(shape, use, t):
                    visit(case)
    for d, p, q2, sig in A.iter_valid_pair_lookups():
        _sd, _sp, _s2, wd, wp, w2, co = sig
        for use in R.USES:
            for taint in S.TAINTS:
                visit(R.Case(use, "PAIR", taint, False, d, p, q2, wd, wp, w2, co))
    assert n_valid == 244_884
    failures = []
    for sig, (case, dec) in sorted(seen.items()):
        problems = errors(_claim_of(case, dec, R), CLAIM)
        if problems:
            failures.append((sig, problems[:2]))
    assert failures == [], failures[:5]
    assert len(seen) > 100


@pytest.mark.simulation
def test_oracle_and_model_unchanged_by_step5() -> None:
    """Exit criterion 10: the frozen Step 4 oracle and reference model are unchanged."""
    import subprocess

    out = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "244c4b6", "--", "simulations/stage04"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        pytest.skip("git history unavailable: " + out.stderr.strip()[:200])
    assert out.stdout.strip() == ""
