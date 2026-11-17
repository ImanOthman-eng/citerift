"""Stage 04 Step 11: the full production vertical slice VS-1 to VS-10 (owner instruction of 2026-11-16, SPEC 14).

Every investigation runs through the production command line (``citerift-investigate``, entered through
``vs_entry.py``) in a child process placed in a network namespace with no interface (``unshare -rn``) and with a
socket counter: the real Investigation Memory, controller, Stage 03 retained extraction, bounded Stage 02 lookup over
the full pinned index, dt-1, ASSEMBLE, VERIFY, the report graph, v1 projections, export and the D-052 checkpoint.
Only VS-8's Retry-After case uses a live-capture request, served by the SYNTHETIC-network child of the Step 8 tests.

The Stage 02 index is built here, by Stage 02 ``build``, from the pinned Retraction Watch snapshot (receipt
``a987928``, the file's SHA-256 is checked against the receipt). Every input is design-exposed data (owner decision
D-5): the SPEC S-7.4 bundles, the challenge bundles used at Steps 9 and 10, and two reserve bundles for VS-6. No
holdout bundle and no evaluation frame is read. Nothing here is precision, recall or an evaluation.

Run (from the repository root; about 15 minutes, of which about 3.5 wait for a Retry-After instant):

    uv run python docs/verification/stage-04/evidence/vertical-slice/run_vertical_slice.py \\
        --csv <retraction_watch.csv of the pinned snapshot> --work <empty scratch directory>

Step 12 (D-062) reruns it as the freeze reference with ``--results <dir>`` (``../../freeze/vertical-slice``); the
Step 11 ``results/`` stay as historical engineering evidence. VS-10 then also shows that other index bytes with the
same canonical Stage 02 content are not a change, that another canonical content is STALE, and that an index whose
content does not prove its stored identity is refused (exit 3), never STALE.

Writes ``results/`` beside itself (or the ``--results`` directory): ``vertical_slice.json`` (every case, check,
digest, exit code, timing and network count), and per successful case the minimal retained evidence (journal, export
manifest, report manifest, projection set, v1 records); Investigation Memory directories and blobs stay in the
scratch directory (they are rebuilt from the bundle and the pinned snapshot).
"""

# ruff: noqa: PLC0415  (citerift modules are imported where a check needs them, after the index is built)

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
ENTRY = HERE / "vs_entry.py"
RESULTS = HERE / "results"  # replaced by --results
PY = sys.executable

S03 = "docs/verification/stage-03"
CHALLENGE = f"{S03}/evaluation/confirmation-2026-11/campaign/capture/bundles/challenge"
CASES: dict[str, dict[str, Any]] = {
    "VS-1": {"bundle": f"{S03}/demonstrations/bundles/en-1381772671", "label": "MMR vaccine, en 1381772671"},
    "VS-2": {"bundle": "tests/stage03/fixtures/observed/ar-76190003", "label": "Haruko Obokata, ar 76190003"},
    "VS-3a": {"bundle": "tests/stage03/fixtures/observed/en-1372543632", "label": "Haruko Obokata, en 1372543632"},
    "VS-3b": {"bundle": f"{S03}/demonstrations/bundles/en-1374726997", "label": "GFAJ-1, en 1374726997"},
    "VS-4": {"bundle": f"{CHALLENGE}/en-65547507-a1", "label": "expression of concern, en 1360148888"},
    "VS-5": {"bundle": f"{S03}/evaluation/capture/bundles/challenge/ar-4541237-a1", "label": "BCAS3, ar 76488293"},
    "VS-6a": {"bundle": f"{S03}/evaluation/capture/bundles/reserve/ar-9617858-a1", "label": "reserve, ar 73356164"},
    "VS-6b": {
        "bundle": f"{S03}/evaluation/confirmation-2026-11/campaign/capture/bundles/reserve1/en-44351447-a1",
        "label": "reserve, en 1345535167",
    },
}
WAKEFIELD = ("10.1016/s0140-6736(97)11096-0", "9500320")
LANCET_NOTICE = ("10.1016/s0140-6736(10)60175-4", "20137807")
OBOKATA_CONFLICT = ("10.1038/nature12969", "24476881")
FORBIDDEN = ("clean", "safe", "not retracted", "no retracted citations")
POSITIVE = ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")
STEPS = ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY")


# Command-line calls -----------------------------------------------------------------------------------------------


@dataclass
class Call:
    label: str
    argv: list[str]
    code: int
    out: Any
    wall_s: float
    network_attempts: int
    stderr: str = ""


@dataclass
class Run:
    work: Path
    calls: list[Call] = field(default_factory=list)

    def cli(self, label: str, *args: Any, env: dict[str, str] | None = None, timeout: float = 900) -> Call:
        log = self.work / "net" / f"{len(self.calls):03d}-{label}.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(b"")
        argv = [str(a) for a in args]
        if not (argv[0] == "checkpoint" and "--out" not in argv):
            argv += ["--format", "json"]
        cmd = ["unshare", "-rn", PY, str(ENTRY), *argv]
        environ = {k: v for k, v in os.environ.items() if not k.startswith("VS_")}
        environ.update({"VS_NET_LOG": str(log), **(env or {})})
        t0 = time.perf_counter()
        p = subprocess.run(cmd, env=environ, capture_output=True, timeout=timeout, cwd=REPO, check=False)  # noqa: S603
        wall = time.perf_counter() - t0
        try:
            out = json.loads(p.stdout) if p.stdout.strip() else None
        except ValueError:
            out = p.stdout.decode("utf-8", "replace")
        attempts = len(log.read_text(encoding="utf-8").splitlines())
        call = Call(
            label, argv, p.returncode, out, round(wall, 3), attempts, p.stderr.decode("utf-8", "replace")[-2000:]
        )
        self.calls.append(call)
        return call

    def memory_root(self, name: str) -> Path:
        root = self.work / "memory" / name
        root.mkdir(parents=True, mode=0o700)
        root.chmod(0o700)
        return root


def rel(value: Any, work: Path) -> Any:
    """Paths of the scratch directory and the repository written relative to them in retained evidence."""
    if isinstance(value, str):
        return value.replace(str(work), "<work>").replace(str(REPO) + "/", "")
    if isinstance(value, list):
        return [rel(v, work) for v in value]
    if isinstance(value, dict):
        return {k: rel(v, work) for k, v in value.items()}
    return value


# Reading committed state (read-only; the citerift fold for the view, raw files for the independent walk) ---------


def journal(root: Path, key: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (root / key / "journal.jsonl").read_bytes().splitlines() if line]


def blob(root: Path, key: str, digest: str) -> Any:
    data = (root / key / "blobs" / digest).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit(f"blob {digest} does not hash to its name")
    return json.loads(data)


def view(root: Path, key: str) -> dict[str, Any]:
    from citerift.investigation.memory import InvestigationMemory

    with InvestigationMemory.open(root, key, writable=False) as mem:
        f = mem.view
        return {
            "logical": json.loads(json.dumps(f.logical)),
            "lifecycle": f.lifecycle(),
            "content_digest": f.content_digest(),
            "open_questions": f.open_questions(),
        }


def step_spans(recs: list[dict[str, Any]]) -> dict[str, float]:
    def at(r: dict[str, Any]) -> datetime:
        return datetime.fromisoformat(r["at"].replace("Z", "+00:00"))

    out: dict[str, float] = {}
    for s in STEPS:
        starts = [r for r in recs if r["kind"] == "step_started" and r["step"] == s]
        ends = [r for r in recs if r["kind"] in ("step_succeeded", "step_failed", "step_deferred") and r["step"] == s]
        if starts and ends:
            out[s] = round((at(ends[-1]) - at(starts[0])).total_seconds(), 3)
    out["journal_span"] = round((at(recs[-1]) - at(recs[0])).total_seconds(), 3)
    return out


def summary(root: Path, key: str) -> dict[str, Any]:
    """Claims, decisions, questions, positive works, lookups and identities of a committed investigation."""
    v = view(root, key)
    recs = journal(root, key)
    created = recs[0]["payload"]
    claims = [r["payload"] for r in v["logical"] if r["kind"] == "claim_recorded"]
    decisions = {r["payload"]["claim_id"]: r["payload"] for r in v["logical"] if r["kind"] == "decision_recorded"}
    questions = [r["payload"] for r in v["logical"] if r["kind"] == "question_opened"]
    obs = [r["payload"] for r in v["logical"] if r["kind"] == "observation_recorded"]
    extraction = next((blob(root, key, o["blob"]) for o in obs if o["obs_kind"] == "extraction"), None)
    lookups = [blob(root, key, o["blob"]) for o in obs if o["obs_kind"] == "lookup"]
    index_identity = next((blob(root, key, o["blob"]) for o in obs if o["obs_kind"] == "index_identity"), None)
    report = next((r["payload"] for r in recs if r["kind"] == "report_recorded"), None)
    manifest = blob(root, key, report["report"]) if report else None
    works: list[Any] = []
    if manifest:
        for c in manifest["components"]["positive_works"]["chunks"]:
            works += blob(root, key, c["chunk"])["items"]
    return {
        "view": v,
        "records": recs,
        "created": created,
        "claims": claims,
        "decisions": decisions,
        "questions": questions,
        "extraction": extraction,
        "lookups": lookups,
        "index_identity": index_identity,
        "report": report,
        "manifest": manifest,
        "works": works,
    }


def keys_of(claim: dict[str, Any]) -> tuple[str | None, str | None]:
    k = {x["scheme"]: x["normalized"] for x in claim["candidate"]["keys"]}
    return k.get("doi"), k.get("pmid")


def lookup_of(s: dict[str, Any], doi: str | None, pmid: str | None) -> dict[str, Any] | None:
    for lk in s["lookups"]:
        if lk["query"].get("doi") == doi and lk["query"].get("pmid") == pmid:
            return lk
    return None


def claim_view(s: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    doi, pmid = keys_of(c)
    lk = lookup_of(s, doi, pmid)
    d = s["decisions"].get(c["claim_id"], {})
    return {
        "class": c["class"],
        "rule": c["rule"],
        "status": c["status"],
        "value": c["value"],
        "keys": {"doi": doi, "pmid": pmid},
        "shape": c["candidate"]["shape"],
        "coherence": c["candidate"]["coherence"],
        "reasons": c["reasons"],
        "upstream_reasons": [u["code"] for u in c["upstream_reasons"]],
        "claim_id": c["claim_id"],
        "cand_ref": c["cand_ref"],
        "evidence_set": c["evidence_set"],
        "supporting": c["supporting_count"],
        "contradicting": c["contradicting_count"],
        "alternatives": len(c["alternatives"]),
        "disposition": d.get("disposition"),
        "deciding_lookup": None
        if lk is None
        else {
            "state": lk["result"]["lookup_state"],
            "events": [
                {k: e.get(k) for k in ("event_id", "event_type", "record_id", "row_sha256", "matched_by", "anchor")}
                for e in lk["events"]
            ],
            "identity_anchor": (lk["result"].get("identity") or {}).get("anchor"),
        },
    }


# The independent provenance walk (owner item 20) -------------------------------------------------------------------


def _pointer(doc: Any, pointer: str) -> Any:
    for raw in pointer.split("/")[1:] if pointer else []:
        part = raw.replace("~1", "/").replace("~0", "~")
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def csv_rows(csv_path: Path, record_ids: set[str]) -> dict[str, str]:
    """``Record ID`` -> SHA-256 of the canonical JSON of the CSV fields (Stage 02's row_sha256 definition), read here
    with the standard library from the pinned file."""
    import csv

    out: dict[str, str] = {}
    csv.field_size_limit(1 << 26)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, strict=True)
        header = next(reader)
        col = header.index("Record ID")
        for row in reader:
            if row and row[col] in record_ids:
                text = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                out[row[col]] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return out


def walk(root: Path, key: str, claim_id: str, csv_path: Path, export_dir: Path | None) -> dict[str, Any]:
    """Walk one claim from the article revision to the report and the v1 projection, recomputing every digest from
    bytes (SHA-256 of blobs and artifacts, the D-043 span, Stage 02 row hashes from the pinned CSV, evidence ids,
    claim and decision ids) and resolving every pointer. Each link is recorded with what was compared."""
    from citerift.investigation import ids

    links: list[dict[str, Any]] = []

    def link(name: str, ok: bool, detail: Any) -> None:
        links.append({"link": name, "ok": bool(ok), "detail": detail})

    recs = journal(root, key)
    prev = ids.genesis(key)
    chain_ok = True
    for r in recs:
        chain_ok &= r["prev"] == prev and ids.record_digest(r) == r["digest"]
        prev = r["digest"]
    link("journal hash chain", chain_ok, {"records": len(recs), "final_digest": prev})
    bundle_obs = next(
        r["payload"] for r in recs if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "bundle"
    )
    bundle = blob(root, key, bundle_obs["blob"])
    capture_raw = (root / key / "blobs" / bundle["capture"]["blob"]).read_bytes() if "capture" in bundle else None
    ident = bundle["identity"]
    if capture_raw is not None:
        cap = json.loads(capture_raw)
        link(
            "Wikipedia revision -> Stage 03 capture",
            hashlib.sha256(capture_raw).hexdigest() == ident["capture_sha256"]
            and cap["page"]["revision_id"] == ident["revision_id"],
            {"wiki": ident["wiki"], "revision_id": ident["revision_id"], "capture_sha256": ident["capture_sha256"]},
        )
    claims = {r["payload"]["claim_id"]: r for r in view(root, key)["logical"] if r["kind"] == "claim_recorded"}
    claim = claims[claim_id]["payload"]
    evidence: dict[str, dict[str, Any]] = {}
    for r in recs:
        if r["kind"] == "evidence_batch_recorded":
            for it in blob(root, key, r["payload"]["batch"])["items"]:
                evidence[it["evidence_id"]] = it
    es = blob(root, key, claim["evidence_set"])
    members = es["supporting"] + es["contradicting"] + [m for a in es["alternatives"] for m in a]
    bad_ids, bad_ptr = [], []
    for m in members:
        it = evidence[m]
        if ids.evidence_id(it["observation"], it["pointer"], it["kind"]) != m:
            bad_ids.append(m)
        try:
            _pointer(blob(root, key, it["observation"]), it["pointer"])
        except (KeyError, IndexError, ValueError):
            bad_ptr.append(m)
    link(
        "evidence set -> evidence items (ids recomputed, pointers resolved)",
        not bad_ids and not bad_ptr,
        {"evidence_set": claim["evidence_set"], "members": len(members), "bad_ids": bad_ids, "bad_pointers": bad_ptr},
    )
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for m in members:
        by_kind.setdefault(evidence[m]["kind"], []).append(evidence[m])
    units = [it for it in by_kind.get("unit", [])]
    span_ok = []
    extraction = None
    for u in units:
        extraction = blob(root, key, u["observation"])
        unit = _pointer(extraction, u["pointer"])
        art = u["value"]["source_artifact"]
        data = (root / key / "blobs" / art).read_bytes()
        src = unit["source"]
        span = data[src["byte_start"] : src["byte_end"]]
        span_ok.append(
            {
                "unit": unit["id"],
                "artifact_sha256_ok": hashlib.sha256(data).hexdigest() == art,
                "byte_start": src["byte_start"],
                "byte_end": src["byte_end"],
                "span_sha256_ok": hashlib.sha256(span).hexdigest() == u["value"]["unit_span_sha256"],
                "identifiers_in_span": [
                    raw.strip()
                    for raw in (
                        extraction["identifiers"][int(i.split("-")[1]) - 1]["normalization"]["raw"]
                        for i in unit["identifier_ids"]
                    )
                    if raw.strip().encode("utf-8") in span
                ],
            }
        )
    link(
        "Stage 03 extraction -> source byte anchor (D-043 span re-hashed from the retained artifact)",
        bool(span_ok) and all(x["artifact_sha256_ok"] and x["span_sha256_ok"] for x in span_ok),
        span_ok,
    )
    occ = by_kind.get("identifier_occurrence", [])
    link(
        "source anchor -> normalized identifiers",
        {tuple(sorted(o["value"]["key"].values())) for o in occ}
        >= {tuple(sorted(k.values())) for k in claim["candidate"]["keys"]},
        [o["value"]["key"] for o in occ],
    )
    rows = by_kind.get("lookup_event", [])
    lookup_results = by_kind.get("lookup_result", [])
    events = [_pointer(blob(root, key, e["observation"]), e["pointer"]) for e in rows]
    if events:
        hashes = csv_rows(csv_path, {e["record_id"] for e in events})
        link(
            "Stage 02 lookup -> event row hash (recomputed from the pinned CSV)",
            all(hashes.get(e["record_id"]) == e["row_sha256"] for e in events),
            [{"event": e["event_id"], "record": e["record_id"], "row_sha256": e["row_sha256"]} for e in events],
        )
    else:
        states = [_pointer(blob(root, key, r["observation"]), "/result")["lookup_state"] for r in lookup_results]
        link("Stage 02 lookup -> result (no event)", bool(states), {"lookup_states": states})
    ident_obs = by_kind.get("index_identity", [])
    if ident_obs:
        ii = blob(root, key, ident_obs[0]["observation"])
        link("Stage 02 lookup -> pinned index identity", ii.get("snapshot_id") is not None, ii)
    link(
        "dt-1 rule -> claim id (recomputed)",
        ids.claim_id(claim["cand_ref"], claim["class"], claim["rule"], claim["table_version"], claim["evidence_set"])
        == claim_id,
        {"rule": claim["rule"], "class": claim["class"], "table_version": claim["table_version"]},
    )
    decision = next(
        r["payload"]
        for r in view(root, key)["logical"]
        if r["kind"] == "decision_recorded" and r["payload"]["claim_id"] == claim_id
    )
    link(
        "claim -> decision (id recomputed)",
        ids.decision_id(claim_id, decision["disposition"]) == decision["decision_id"],
        decision,
    )
    report = next((r["payload"] for r in recs if r["kind"] == "report_recorded"), None)
    if report:
        manifest = blob(root, key, report["report"])
        in_report = any(
            item.get("claim_id") == claim_id or item.get("claim", {}).get("claim_id") == claim_id
            for c in manifest["components"]["claims"]["chunks"]
            for item in blob(root, key, c["chunk"])["items"]
        )
        link("decision -> report claims component", in_report, {"report": report["report"]})
        pset = blob(root, key, report["projection_set"])
        if claim["class"] in POSITIVE and export_dir is not None:
            doi, pmid = keys_of({"candidate": claim["candidate"]})
            hit = []
            for body in pset["projections"]:
                rec = json.loads((export_dir / "v1" / f"{body}.json").read_bytes())
                stored = blob(root, key, body)
                same = {k: v for k, v in rec.items() if k != "created_at"} == stored
                ids_ = [c["identifiers"] for c in rec["citations"]]
                if any(i.get("doi") == doi or i.get("pmid") == pmid for i in ids_):
                    hit.append({"body": body, "export_equals_stored_plus_created_at": same, "status": rec["status"]})
            link(
                "report -> v1 projection (export = stored body + created_at)",
                bool(hit) and all(h["export_equals_stored_plus_created_at"] for h in hit),
                hit,
            )
        else:
            link(
                "report -> no v1 projection for a non-positive claim",
                True,
                {"class": claim["class"], "projections": len(pset["projections"])},
            )
    return {"claim_id": claim_id, "class": claim["class"], "ok": all(x["ok"] for x in links), "links": links}


# Cases ------------------------------------------------------------------------------------------------------------


def run_case(r: Run, name: str, bundle: Path, index: Path, repeats: int) -> dict[str, Any]:
    root = r.memory_root(name)
    run = r.cli(f"{name}-run", "run", "--bundle", bundle, "--index", index, "--memory-root", root)
    res = run.out["result"]
    key = res["investigation_key"]
    out: dict[str, Any] = {"case": name, "input": CASES.get(name, {}), "investigation_key": key, "run": _call(run)}
    karg = ("--memory-root", root, "--key", key)
    show = r.cli(f"{name}-show", "show", *karg, "--claims")
    verify = r.cli(f"{name}-verify", "verify", *karg)
    replay = r.cli(f"{name}-replay", "replay", *karg)
    export_dir = r.work / "exports" / name
    export = r.cli(f"{name}-export", "export", *karg, "--out", export_dir)
    s = summary(root, key)
    created = s["created"]
    out.update(
        exit_codes={
            "run": run.code,
            "show": show.code,
            "verify": verify.code,
            "replay": replay.code,
            "export": export.code,
        },
        cli_status=run.out["status"],
        lifecycle=s["view"]["lifecycle"],
        report_outcome=s["manifest"]["outcome"] if s["manifest"] else None,
        extraction_status=s["extraction"]["status"] if s["extraction"] else None,
        identities={
            "request_key": created["request_key"],
            "config_digest": created["config_digest"],
            "root_id": next(
                (
                    x["payload"]["root"]["root_id"]
                    for x in s["records"]
                    if x["kind"] == "step_succeeded" and x["step"] == "ACQUIRE"
                ),
                None,
            ),
            "index": s["index_identity"],
            "extractor": s["extraction"]["extractor"] if s["extraction"] else None,
            "extraction_digest": s["extraction"]["extraction_digest"] if s["extraction"] else None,
            "stage04": created.get("stage04") or created.get("identities", {}).get("stage04"),
        },
        journal={
            "records": len(s["records"]),
            "final_seq": s["records"][-1]["seq"],
            "final_digest": s["records"][-1]["digest"],
        },
        content_digest=s["view"]["content_digest"],
        report=s["report"],
        positive_works=s["works"],
        claims_by_class=dict(Counter(c["class"] for c in s["claims"])),
        claims=[claim_view(s, c) for c in s["claims"] if c["class"] not in ("NO_IDENTIFIER",)],
        questions=s["questions"],
        verify={
            "result": verify.out["result"]["result"],
            "checks": [(c["check"], c["passed"]) for c in verify.out["result"]["checks"]],
        },
        replay=replay.out["result"],
        export=export.out.get("result") if isinstance(export.out, dict) else export.out,
        summary_statement=(show.out["result"]["report"] or {}).get("summary"),
        limitations=[x["code"] for x in (show.out["result"]["report"] or {}).get("limitations", [])],
        explanations=[
            e.get("text") if isinstance(e, dict) else e for e in (show.out["result"]["report"] or {}).get("claims", [])
        ],
        network_attempts=sum(c.network_attempts for c in (run, show, verify, replay, export)),
    )
    if export.code in (0, 6, 10):
        v1 = []
        ex = json.loads((export_dir / "export.json").read_bytes())
        for f in ex["files"]:
            if f["path"].startswith("v1/"):
                v1.append(json.loads((export_dir / f["path"]).read_bytes()))
        out["v1_records"] = [
            {
                "status": x["status"],
                "schema_version": x["schema_version"],
                "identifiers": [c["identifiers"] for c in x["citations"]],
                "events": [e["kind"] for e in x["events"]],
            }
            for x in v1
        ]
        out["v1_valid"] = _v1_valid(v1)
        _retain(name, root, key, export_dir)
    # performance: the first run above plus repeats - 1 fresh investigations of the same request
    timings = [{"wall_s": run.wall_s, **step_spans(s["records"]), "replay_wall_s": replay.wall_s}]
    for i in range(1, repeats):
        rr = r.memory_root(f"{name}-perf{i}")
        c = r.cli(f"{name}-perf{i}", "run", "--bundle", bundle, "--index", index, "--memory-root", rr)
        rp = r.cli(f"{name}-perf{i}-replay", "replay", "--memory-root", rr, "--key", key)
        timings.append({"wall_s": c.wall_s, **step_spans(journal(rr, key)), "replay_wall_s": rp.wall_s})
        out["network_attempts"] += c.network_attempts + rp.network_attempts
        if view(rr, key)["content_digest"] != out["content_digest"]:
            raise SystemExit(f"{name}: a repeated run gave another C(J)")
    out["timings"] = timings
    out["perf"] = _perf(timings)
    out["_summary"] = s
    out["_root"] = root
    return out


def _call(c: Call) -> dict[str, Any]:
    return {"argv": c.argv, "exit_code": c.code, "wall_s": c.wall_s, "network_attempts": c.network_attempts}


def _v1_valid(records: list[dict[str, Any]]) -> bool:
    from citerift.investigation.projections import record_problems

    return all(not record_problems(r) for r in records)


def _perf(timings: list[dict[str, Any]]) -> dict[str, Any]:
    keys = ["wall_s", "journal_span", *STEPS, "replay_wall_s"]
    out = {}
    for k in keys:
        vals = sorted(t[k] for t in timings if k in t)
        if vals:
            idx = max(0, -(-95 * len(vals) // 100) - 1)
            out[k] = {"median": round(statistics.median(vals), 3), "p95": vals[idx], "max": vals[-1], "n": len(vals)}
    return out


def _retain(name: str, root: Path, key: str, export_dir: Path) -> None:
    dest = RESULTS / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copyfile(root / key / "journal.jsonl", dest / "journal.jsonl")
    ex = json.loads((export_dir / "export.json").read_bytes())
    shutil.copyfile(export_dir / "export.json", dest / "export.json")
    shutil.copyfile(export_dir / "projection_set.json", dest / "projection_set.json")
    shutil.copyfile(export_dir / "report" / f"{ex['report']}.json", dest / "report_manifest.json")
    for f in ex["files"]:
        if f["path"].startswith("v1/"):
            (dest / "v1").mkdir(exist_ok=True)
            shutil.copyfile(export_dir / f["path"], dest / f["path"])


# Case checks --------------------------------------------------------------------------------------------------------


def _claim(case: dict[str, Any], doi: str | None, pmid: str | None) -> dict[str, Any] | None:
    for c in case["claims"]:
        if c["keys"] == {"doi": doi, "pmid": pmid}:
            return c
    return None


def _wording_ok(case: dict[str, Any]) -> bool:
    texts = [case.get("summary_statement") or "", *[t or "" for t in case.get("explanations", [])]]
    low = " ".join(texts).lower()
    return not any(f" {w} " in f" {low} " or f" {w}." in low or f" {w}," in low for w in FORBIDDEN)


def common_checks(case: dict[str, Any]) -> dict[str, bool]:
    ok_codes = {"COMPLETED": (0, 6), "NEEDS_RESOLUTION": (10,)}
    lc = case["lifecycle"]
    pos_classes = sum(n for c, n in case["claims_by_class"].items() if c in POSITIVE)
    return {
        "lifecycle verified": lc in ok_codes,
        "run exit code matches status": case["run"]["exit_code"] in ok_codes.get(lc, ()),
        "VERIFY passes (every named check)": case["verify"]["result"] == "passed"
        and all(p for _, p in case["verify"]["checks"]),
        "replay reproduced": case["replay"].get("result") == "reproduced",
        "export succeeded after VERIFY": case["exit_codes"]["export"] == case["run"]["exit_code"],
        "export report = committed report": case["export"]["report"] == case["report"]["report"]
        and case["export"]["projection_set"] == case["report"]["projection_set"],
        "projection count = distinct positive works": case["report"]["projection_count"] == len(case["positive_works"]),
        "no projection without a positive claim": pos_classes > 0 or case["report"]["projection_count"] == 0,
        "every v1 record valid against contracts v1": case.get("v1_valid", True),
        "S-7.7 wording: no forbidden phrase": _wording_ok(case),
        "no network attempt": case["network_attempts"] == 0,
    }


def vs_checks(name: str, case: dict[str, Any]) -> dict[str, bool]:
    c = common_checks(case)
    s = case["_summary"]
    ex = s["extraction"]
    if name == "VS-1":
        wake, notice = _claim(case, *WAKEFIELD), _claim(case, *LANCET_NOTICE)
        markers = [i for i in ex["identifiers"] if i["role"] == "marker_target"]
        marker_ids = {i["id"] for i in markers}
        in_units = {i for u in ex["units"] for i in u["identifier_ids"]}
        c.update(
            {
                "Wakefield original RETRACTED_WORK_CITED": wake is not None and wake["class"] == "RETRACTED_WORK_CITED",
                "Lancet notice citation NOTICE_CITED": notice is not None and notice["class"] == "NOTICE_CITED",
                "notice is not the original work (no positive work keyed by the notice)": all(
                    LANCET_NOTICE[0] not in json.dumps(w) for w in case["positive_works"]
                ),
                "markers observed (marker_target identifiers and marker states retained)": bool(markers)
                and bool(ex["markers"]),
                "marker targets are not candidate keys": not (marker_ids & in_units),
                "summary separates the classes": "NOTICE_CITED: 1" in (case["summary_statement"] or "")
                and "RETRACTED_WORK_CITED: 1" in (case["summary_statement"] or ""),
                "one v1 projection, for the positive work only": case["report"]["projection_count"] == 1
                and all(WAKEFIELD[0] in json.dumps(v["identifiers"]) for v in case.get("v1_records", [])),
            }
        )
    elif name == "VS-2":
        conflict = _claim(case, *OBOKATA_CONFLICT)
        pos = next((x for x in case["claims"] if x["keys"]["doi"] == "10.1038/nature12968"), None)
        others = [
            x
            for x in case["claims"]
            if OBOKATA_CONFLICT[0] in (x["keys"]["doi"] or "") or x["keys"]["pmid"] == OBOKATA_CONFLICT[1]
        ]
        q = case["questions"]
        c.update(
            {
                "nature12968 RETRACTED_WORK_CITED": pos is not None and pos["class"] == "RETRACTED_WORK_CITED",
                "nature12969 + PMID 24476881 IDENTITY_CONFLICT": conflict is not None
                and conflict["class"] == "IDENTITY_CONFLICT",
                "conflict disposition ROUTE_NEEDS_RESOLUTION": conflict is not None
                and conflict["disposition"] == "ROUTE_NEEDS_RESOLUTION",
                "conflict has two alternatives": conflict is not None and conflict["alternatives"] == 2,
                "one open question on the conflict": len(q) == 1
                and conflict is not None
                and q[0].get("claim_id") == conflict["claim_id"],
                "no positive or NOT_FOUND claim for that candidate": all(
                    x["class"] == "IDENTITY_CONFLICT" for x in others
                ),
                "lifecycle NEEDS_RESOLUTION": case["lifecycle"] == "NEEDS_RESOLUTION",
            }
        )
    elif name in ("VS-3a", "VS-3b"):
        anchors = [json.dumps(w["work"], sort_keys=True) for w in case["positive_works"]]
        c.update(
            {
                "a retracted original found": case["claims_by_class"].get("RETRACTED_WORK_CITED", 0) >= 1,
                "positive works keyed by distinct Stage 02 identity anchors": len(anchors) == len(set(anchors)),
                "v1 projections = distinct positive works": len(case.get("v1_records", []))
                == len(case["positive_works"]),
            }
        )
    elif name == "VS-4":
        concern = [x for x in case["claims"] if x["class"] == "CONCERN_CITED"]
        c.update(
            {
                "CONCERN_CITED present": bool(concern),
                "never RETRACTED_WORK_CITED": "RETRACTED_WORK_CITED" not in case["claims_by_class"],
                "v1 status is not retracted": all(v["status"] != "retracted" for v in case.get("v1_records", [])),
                "no explanation says retracted for the concern": all(
                    "retract" not in (t or "").lower() for t in case["explanations"] if t and "concern" in t.lower()
                ),
            }
        )
    elif name == "VS-5":
        c.update(vs5_checks(case))
    elif name.startswith("VS-6"):
        nf = [x for x in case["claims"] if x["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"]
        c.update(
            {
                "only NOT_FOUND_IN_CHECKED_SOURCES among keyed claims": set(case["claims_by_class"])
                <= {"NOT_FOUND_IN_CHECKED_SOURCES", "NO_IDENTIFIER"}
                and bool(nf),
                "every deciding lookup is no_record": all(
                    (x["deciding_lookup"] or {}).get("state") == "no_record" for x in nf
                ),
                "checked-source identity retained": bool(case["identities"]["index"]),
                "no positive work, no projection": not case["positive_works"]
                and case["report"]["projection_count"] == 0,
                "scoped not-found sentence in the explanations": all(
                    "no matching record was found in the checked sources" in (t or "").lower()
                    for t in case["explanations"]
                    if t and ("not_found" in t.lower() or "not found" in t.lower())
                ),
            }
        )
    return c


def vs5_checks(case: dict[str, Any]) -> dict[str, bool]:
    s = case["_summary"]
    collisions = []
    for lk in s["lookups"]:
        for i in lk["result"].get("issues", []):
            if i.get("code") == "PMID_ROLE_COLLISION":
                collisions.append(lk["query"])
        for e in lk["events"]:
            if "PMID_ROLE_COLLISION" in json.dumps(e.get("flags", [])) + json.dumps(e.get("issues", [])):
                collisions.append({"event": e["event_id"], **lk["query"]})
    case["vs5"] = {"collisions_in_lookups": collisions}
    decided = [
        x
        for x in case["claims"]
        if x["class"] in ("RETRACTED_WORK_CITED", "IDENTITY_CONFLICT", "NOTICE_CITED") or x["rule"] in ("D-10", "D-14")
    ]
    case["vs5"]["deciding_claims"] = [
        {k: x[k] for k in ("class", "rule", "reasons", "keys", "claim_id")} for x in decided
    ]
    root, key = case["_root"], case["investigation_key"]
    evidence: dict[str, Any] = {}
    for rec in journal(root, key):
        if rec["kind"] == "evidence_batch_recorded":
            for it in blob(root, key, rec["payload"]["batch"])["items"]:
                evidence[it["evidence_id"]] = it
    chains = []
    for x in decided:
        es = blob(root, key, x["evidence_set"])
        hits = []
        for m in es["supporting"] + es["contradicting"] + [i for a in es["alternatives"] for i in a]:
            it = evidence[m]
            if it["kind"] == "lookup_result":
                res = _pointer(blob(root, key, it["observation"]), it["pointer"])
                if any(i.get("code") == "PMID_ROLE_COLLISION" for i in res.get("issues", [])):
                    hits.append({"evidence_id": m, "observation": it["observation"], "pointer": it["pointer"]})
        chains.append(
            {
                "claim_id": x["claim_id"],
                "rule": x["rule"],
                "collision_in_evidence_set": hits,
                "collision_is_a_reason": "PMID_ROLE_COLLISION" in x["reasons"],
            }
        )
    case["vs5"]["evidence_chains"] = chains
    return {
        "collision resolvable in each deciding claim's committed evidence set": bool(chains)
        and all(c["collision_in_evidence_set"] for c in chains),
        "collision is a reason only where the deciding rule uses it (D-10), not under D-14": all(
            c["collision_is_a_reason"] == (c["rule"] == "D-10") for c in chains
        ),
        "PMID_ROLE_COLLISION present in committed lookups": bool(collisions),
        "class by D-10 or D-14 as dt-1 decided": any(x["rule"] in ("D-10", "D-14") for x in decided),
    }


# VS-7 and VS-8 ------------------------------------------------------------------------------------------------------


def failure_case(r: Run, name: str, argv: list[Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    root = r.memory_root(name)
    call = r.cli(name, "run", *argv, "--memory-root", root, env=env)
    out: dict[str, Any] = {
        "case": name,
        "run": _call(call),
        "status": call.out.get("status") if isinstance(call.out, dict) else None,
    }
    if isinstance(call.out, dict) and "result" in call.out:
        res = call.out["result"]
        key = res["investigation_key"]
        recs = journal(root, key)
        out.update(
            lifecycle=res["lifecycle"],
            terminated_by=res.get("terminated_by"),
            claims=sum(1 for x in recs if x["kind"] in ("claim_recorded", "candidate_result_batch_recorded")),
            report=any(x["kind"] == "report_recorded" for x in recs),
        )
        ex_dir = r.work / "exports" / name
        ex = r.cli(f"{name}-export", "export", "--memory-root", root, "--key", key, "--out", ex_dir)
        out["export"] = {
            "exit_code": ex.code,
            "error": ex.out.get("error") if isinstance(ex.out, dict) else None,
            "written": ex_dir.exists(),
        }
        out["json_shape_ok"] = set(call.out) == {"command", "status", "exit_code", "result"}
    else:
        out.update(error=call.out.get("error") if isinstance(call.out, dict) else call.out, created=os.listdir(root))
        out["json_shape_ok"] = isinstance(call.out, dict) and set(call.out) == {
            "command",
            "status",
            "exit_code",
            "error",
        }
    out["network_attempts"] = call.network_attempts
    return out


def _revision_zero(index: Path, root: Path) -> dict[str, Any]:
    from citerift.investigation import operations as ops

    req = ops.live_request("en", 1, index, root)
    req["subject"]["revision_id"] = 0
    return req


def failure_checks(x: dict[str, Any], *, created: bool, lifecycle: str = "FAILED") -> dict[str, bool]:
    if not created:
        return {
            "refused before any investigation exists (exit 3)": x["run"]["exit_code"] == 3 and x["created"] == [],
            "machine-readable error": bool(x["json_shape_ok"]) and bool((x.get("error") or {}).get("code")),
            "no network attempt": x["network_attempts"] == 0,
        }
    return {
        f"lifecycle {lifecycle}": x.get("lifecycle") == lifecycle,
        "stable failure code": bool((x.get("terminated_by") or {}).get("code")),
        "no claim (so no NOT_FOUND)": x.get("claims") == 0,
        "no report": x.get("report") is False,
        "export refused, nothing written": x["export"]["exit_code"] != 0 and not x["export"]["written"],
        "machine-readable result": bool(x["json_shape_ok"]),
        "no network attempt": x["network_attempts"] == 0,
    }


def vs7(r: Run, index: Path) -> list[dict[str, Any]]:
    out = []
    src = REPO / CASES["VS-1"]["bundle"]
    corrupt = r.work / "bundles" / "vs7-corrupt"
    shutil.copytree(src, corrupt)
    art = sorted((corrupt / "artifacts").iterdir())[0]
    data = bytearray(art.read_bytes())
    data[len(data) // 2] ^= 0x01
    art.chmod(0o644)
    art.write_bytes(bytes(data))
    out.append(failure_case(r, "VS-7a corrupted bundle artifact", ["--bundle", corrupt, "--index", index]))
    revision = r.work / "bundles" / "vs7-revision"
    shutil.copytree(src, revision)
    cap = revision / "capture.json"
    cap.chmod(0o644)
    text = cap.read_bytes()
    if text.count(b'"revision_id": 1381772671') != 2:
        raise SystemExit("VS-7b: the VS-1 capture no longer names its revision twice")
    cap.write_bytes(text.replace(b'"revision_id": 1381772671', b'"revision_id": 1381772672'))
    out.append(
        failure_case(r, "VS-7b bundle revision differs from its content", ["--bundle", revision, "--index", index])
    )
    out.append(
        failure_case(
            r,
            "VS-7c schema-invalid extraction",
            ["--bundle", src, "--index", index],
            env={"VS_EXTRACTION": "schema_invalid"},
        )
    )
    root = r.memory_root("vs7-requests")
    for label, req in {
        "VS-7d invalid revision request (revision id 0)": _revision_zero(index, root),
        "VS-7e schema-invalid request (unknown property)": {"schema": "x", "unexpected": True},
    }.items():
        path = r.work / f"{label.split()[0]}.json"
        path.write_text(json.dumps(req), encoding="utf-8")
        call = r.cli(label, "run", "--request", path)
        out.append(
            {
                "case": label,
                "run": _call(call),
                "status": call.out.get("status") if isinstance(call.out, dict) else None,
                "error": call.out.get("error") if isinstance(call.out, dict) else call.out,
                "created": os.listdir(root),
                "json_shape_ok": isinstance(call.out, dict)
                and set(call.out) == {"command", "status", "exit_code", "error"},
                "network_attempts": call.network_attempts,
            }
        )
    return out


def vs8(r: Run, index: Path, live_wait: bool) -> list[dict[str, Any]]:
    out = []
    src = REPO / CASES["VS-2"]["bundle"]
    out.append(failure_case(r, "VS-8a index missing", ["--bundle", src, "--index", r.work / "absent.sqlite"]))
    other = r.work / "other-format.sqlite"
    db = sqlite3.connect(other)
    db.execute("CREATE TABLE t (x)")
    db.commit()
    db.close()
    out.append(failure_case(r, "VS-8b index of another format", ["--bundle", src, "--index", other]))
    out.append(vs8_retry_after(r, index, live_wait))
    return out


def vs8_retry_after(r: Run, index: Path, live_wait: bool) -> dict[str, Any]:
    """A live-capture request (ar 76190003) whose SYNTHETIC server answers 429 with Retry-After: 200 s, longer than
    the remaining Stage 03 deadline, so Stage 03 itself defers: BLOCKED with not_before. A resume before the instant
    does not start ACQUIRE and does not sleep; a resume at or after it captures (the synthetic server now replays the
    retained bundle) and completes."""
    root = r.memory_root("vs8-live")
    base = {
        "VS_LIVE_BUNDLE": str(REPO / CASES["VS-2"]["bundle"]),
        "VS_WORKROOT": str(r.work / "acquire"),
        # Stage 03's network gate is host-wide by default (~/.cache/citerift); this run keeps its own.
        "CITERIFT_WIKI_NETWORK_LOCK": str(r.work / "vs8-network-gate.lock"),
    }
    first = r.cli("VS-8c run (429, Retry-After 200)", "run", "--wiki", "ar", "--revision", "76190003", "--index", index,
                  "--memory-root", root, env={**base, "VS_LIVE_MODE": "throttled:200"})  # fmt: skip
    res = first.out["result"]
    key = res["investigation_key"]
    acquire = next(s for s in res["steps"] if s["step"] == "ACQUIRE")
    not_before = datetime.fromisoformat(acquire["not_before"].replace("Z", "+00:00"))
    j0 = (root / key / "journal.jsonl").read_bytes()
    early = r.cli("VS-8c resume before not_before", "resume", "--memory-root", root, "--key", key,
                  env={**base, "VS_LIVE_MODE": "replay"})  # fmt: skip
    j1 = (root / key / "journal.jsonl").read_bytes()
    ex_dir = r.work / "exports" / "vs8-live"
    ex = r.cli("VS-8c export while BLOCKED", "export", "--memory-root", root, "--key", key, "--out", ex_dir)
    out: dict[str, Any] = {
        "case": "VS-8c Retry-After (SYNTHETIC network)",
        "run": _call(first),
        "lifecycle": res["lifecycle"],
        "status": first.out["status"],
        "acquire": acquire,
        "next": res["next"],
        "resume_before": {
            **_call(early),
            "status": early.out["status"],
            "journal_unchanged": j0 == j1,
            "acquire_attempts": next(s for s in early.out["result"]["steps"] if s["step"] == "ACQUIRE")["attempts"],
        },
        "export_while_blocked": {"exit_code": ex.code, "written": ex_dir.exists()},
        "claims_or_report": any(
            x["kind"] in ("candidate_result_batch_recorded", "report_recorded") for x in journal(root, key)
        ),
    }
    if live_wait:
        delay = (not_before - datetime.now(UTC)).total_seconds()
        if delay > 0:
            time.sleep(delay + 1)  # the runner waits; the command never sleeps
        late = r.cli("VS-8c resume after not_before", "resume", "--memory-root", root, "--key", key,
                     env={**base, "VS_LIVE_MODE": "replay"})  # fmt: skip
        starts = [x for x in journal(root, key) if x["kind"] == "step_started" and x["step"] == "ACQUIRE"]
        second_at = datetime.fromisoformat(starts[-1]["at"].replace("Z", "+00:00"))
        out["resume_after"] = {
            **_call(late),
            "status": late.out["status"],
            "lifecycle": late.out["result"]["lifecycle"],
            "acquire_attempts": len(starts),
            "second_attempt_started_at": starts[-1]["at"],
            "not_before": acquire["not_before"],
            "started_at_or_after_not_before": second_at >= not_before,
        }
    out["network_attempts"] = sum(c.network_attempts for c in r.calls if c.label.startswith("VS-8c"))
    return out


# VS-9 -------------------------------------------------------------------------------------------------------------


def vs9(r: Run, index: Path, reference: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    bundle = REPO / CASES["VS-1"]["bundle"]
    for point in ("controller.after_start", "controller.after_adapter", "controller.after_entry_batch"):
        name = f"VS-9 DETECT {point}"
        root = r.memory_root(f"vs9-{point}")
        killed = r.cli(name + " (killed)", "run", "--bundle", bundle, "--index", index, "--memory-root", root,
                       env={"VS_KILL": f"DETECT:{point}"})  # fmt: skip
        key = reference["investigation_key"]
        before = journal(root, key)
        show = r.cli(name + " show", "show", "--memory-root", root, "--key", key)
        resumed = r.cli(name + " resume", "resume", "--memory-root", root, "--key", key)
        after = journal(root, key)
        s = summary(root, key)
        new = after[len(before) :]
        rerun = sorted({x["step"] for x in new if x["kind"] == "step_started"})
        ref_claims = sorted(c["claim_id"] for c in reference["_summary"]["claims"])
        out.append(
            {
                "case": name,
                "killed": {**_call(killed), "signal": -killed.code if killed.code < 0 else None},
                "lookup_committed_before_kill": any(
                    x["kind"] == "step_succeeded" and x["step"] == "LOOKUP" for x in before
                ),
                "detect_open_at_kill": any(x["kind"] == "step_started" and x["step"] == "DETECT" for x in before)
                and not any(x["kind"] == "step_succeeded" and x["step"] == "DETECT" for x in before),
                "show_after_kill": {"exit_code": show.code, "status": show.out["status"]},
                "resume": _call(resumed) | {"status": resumed.out["status"]},
                "steps_started_after_resume": rerun,
                "retried_steps": [
                    st for st in STEPS if sum(1 for x in after if x["kind"] == "step_started" and x["step"] == st) > 1
                ],
                "acquire_to_lookup_not_repeated": not (
                    {"VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP"} & set(rerun)
                ),
                "transitions_interrupted": [
                    [x["seq"], x["kind"], x["step"], x.get("attempt")] for x in after if x["kind"].startswith("step_")
                ],
                "transitions_reference": [
                    [x["seq"], x["kind"], x["step"], x.get("attempt")]
                    for x in reference["_summary"]["records"]
                    if x["kind"].startswith("step_")
                ],
                "same_claims": sorted(c["claim_id"] for c in s["claims"]) == ref_claims,
                "content_digest": s["view"]["content_digest"],
                "same_content_digest": s["view"]["content_digest"] == reference["content_digest"],
                "same_report_digest": s["report"]["report"] == reference["report"]["report"],
                "same_projection_set": s["report"]["projection_set"] == reference["report"]["projection_set"],
                "network_attempts": killed.network_attempts + show.network_attempts + resumed.network_attempts,
            }
        )
    return out


# VS-10 ------------------------------------------------------------------------------------------------------------


def vs10(r: Run, index: Path) -> dict[str, Any]:
    """Replay of a NEEDS_RESOLUTION investigation (VS-2) whose bundle and index are copies, then one identity changed
    at a time (and restored): stale, naming the identity; the journal is never written by replay. D-057: another
    lookup budget is another investigation key, never STALE of the first."""
    bundle = r.work / "bundles" / "vs10"
    shutil.copytree(REPO / CASES["VS-2"]["bundle"], bundle)
    from citerift.retraction.store import manifest_path_for

    idx = r.work / "vs10-index.sqlite"

    def put_index(src: Path) -> None:  # the index with its build manifest (D-062: a missing manifest refuses)
        shutil.copyfile(src, idx)
        shutil.copyfile(manifest_path_for(src), manifest_path_for(idx))

    put_index(index)
    root = r.memory_root("vs10")
    run = r.cli("VS-10 run", "run", "--bundle", bundle, "--index", idx, "--memory-root", root)
    key = run.out["result"]["investigation_key"]
    karg = ("--memory-root", root, "--key", key)
    out: dict[str, Any] = {"run": _call(run), "investigation_key": key, "mutations": []}
    base = r.cli("VS-10 replay unchanged", "replay", *karg)
    out["unchanged"] = {"exit_code": base.code, "result": base.out["result"]["result"]}
    j0 = (root / key / "journal.jsonl").read_bytes()

    def probe(label: str, env: dict[str, str] | None = None) -> None:
        rp = r.cli(f"VS-10 replay, {label}", "replay", *karg, env=env)
        vf = r.cli(f"VS-10 verify, {label}", "verify", *karg, env=env)
        out["mutations"].append(
            {
                "changed": label,
                "replay": {
                    "exit_code": rp.code,
                    "result": rp.out["result"].get("result"),
                    "changed": rp.out["result"].get("changed"),
                },
                "verify": {
                    "exit_code": vf.code,
                    "result": vf.out["result"].get("result"),
                    "changed": (vf.out["result"].get("stale") or {}).get("changed"),
                },
                "journal_unchanged": (root / key / "journal.jsonl").read_bytes() == j0,
            }
        )

    saved = r.work / "bundles" / "vs10-saved"
    shutil.move(bundle, saved)
    shutil.copytree(REPO / CASES["VS-3a"]["bundle"], bundle)
    probe("capture/root: another capture at the bundle path")
    shutil.rmtree(bundle)
    shutil.move(saved, bundle)
    probe("Stage 03 profile identity", {"VS_PROFILE_DIGEST": "0" * 64})
    sys.path.insert(0, str(REPO / "tests" / "stage04"))
    import step8_support

    put_index(step8_support.build_index(r.work / "vs10-other-snapshot"))  # another canonical Stage 02 content
    probe("Stage 02 index: another canonical content (artifact_digest)")
    put_index(index)
    with open(idx, "ab") as f:
        f.write(b"\0" * 4096)
    rp = r.cli("VS-10 replay, index bytes changed, canonical content equal", "replay", *karg)
    out["index_bytes_only"] = {
        "exit_code": rp.code,
        "result": rp.out["result"].get("result") if isinstance(rp.out, dict) and "result" in rp.out else None,
        "journal_unchanged": (root / key / "journal.jsonl").read_bytes() == j0,
    }
    put_index(index)
    db = sqlite3.connect(idx)
    db.execute("UPDATE meta SET value = ? WHERE key = 'artifact_digest'", ("0" * 64,))
    db.commit()
    db.close()
    refused = []
    for command in ("replay", "verify"):
        c = r.cli(f"VS-10 {command}, index metadata forged", command, *karg)
        refused.append(
            {
                "command": command,
                "exit_code": c.code,
                "error": c.out.get("error") if isinstance(c.out, dict) else None,
                "journal_unchanged": (root / key / "journal.jsonl").read_bytes() == j0,
            }
        )
    out["index_unverifiable"] = refused
    put_index(index)
    probe("Stage 04 schema version", {"VS_STAGE04": json.dumps({"schema_version": "3.0.1"})})
    probe("Stage 04 engine version", {"VS_STAGE04": json.dumps({"engine_version": "0.2.1"})})
    restored = r.cli("VS-10 replay restored", "replay", *karg)
    out["restored"] = {"exit_code": restored.code, "result": restored.out["result"]["result"]}
    other_root = root  # the same memory root: another key beside the first
    b = r.cli("VS-10 D-057 run with another lookup budget", "run", "--bundle", bundle, "--index", idx,
              "--memory-root", other_root, "--lookup-budget", str(8 * 1024 * 1024))  # fmt: skip
    again = r.cli("VS-10 D-057 replay of the first", "replay", *karg)
    out["d057"] = {
        "other_key": b.out["result"]["investigation_key"],
        "keys_differ": b.out["result"]["investigation_key"] != key,
        "other_lifecycle": b.out["result"]["lifecycle"],
        "first_replay": again.out["result"]["result"],
        "first_journal_unchanged": (root / key / "journal.jsonl").read_bytes() == j0,
        "first_has_no_stale_record": not any(x["kind"] == "stale_detected" for x in journal(root, key)),
    }
    out["network_attempts"] = sum(c.network_attempts for c in r.calls if c.label.startswith("VS-10"))
    return out


# Main -------------------------------------------------------------------------------------------------------------


def build_index(csv_path: Path, work: Path) -> tuple[Path, dict[str, Any]]:
    from citerift.retraction.source import load_receipt
    from citerift.retraction.store import build

    receipt = load_receipt()
    t0 = time.perf_counter()
    sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if sha != receipt.expected_sha256:
        raise SystemExit(f"{csv_path}: sha256 {sha} is not the pinned receipt's {receipt.expected_sha256}")
    built = build(csv_path, receipt, work / "index")
    index = built.index_path
    return index, {
        "receipt_commit": receipt.commit,
        "csv_sha256": sha,
        "index_file": index.name,
        "index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
        "index_bytes": index.stat().st_size,
        "build_s": round(time.perf_counter() - t0, 1),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--index", type=Path, default=None, help="a Stage 02 index already built from --csv (debugging)")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--no-live-wait", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--results", type=Path, default=None, help="where to write the results (default: results/)")
    args = ap.parse_args(argv)
    global RESULTS  # noqa: PLW0603 - one run writes one results directory
    if args.results is not None:
        RESULTS = args.results.resolve()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if any(work.iterdir()):
        raise SystemExit(f"{work} is not empty")
    RESULTS.mkdir(exist_ok=True)
    r = Run(work)
    for d in ("exports", "bundles", "memory"):
        (work / d).mkdir()
    t0 = time.perf_counter()
    if args.index is not None:
        index = args.index.resolve()
        index_info = {
            "index_file": index.name,
            "prebuilt": True,
            "index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
        }
    else:
        index, index_info = build_index(args.csv.resolve(), work)
    results: dict[str, Any] = {
        "label": "Stage 04 vertical slice (Step 11 method; Step 12 rerun after D-062 as the freeze reference): "
        "development evidence on design-exposed inputs (D-5); not an evaluation",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "machine": f"{os.uname().machine}, {os.cpu_count()} CPUs",
        "index": index_info,
        "cases": {},
    }
    selected = args.only or list(CASES)
    cases: dict[str, dict[str, Any]] = {}
    for name in [n for n in CASES if n in selected]:
        bundle = (REPO / CASES[name]["bundle"]).resolve()
        cap = json.loads((bundle / "capture.json").read_bytes())
        case = run_case(r, name, bundle, index, args.repeats)
        case["input"] = {
            **CASES[name],
            "bundle": str(bundle.relative_to(REPO)),
            "wiki": cap["request"]["wiki"],
            "revision_id": cap["page"]["revision_id"],
            "title": cap["page"]["title"],
            "capture_status": cap["status"],
            "capture_sha256": hashlib.sha256((bundle / "capture.json").read_bytes()).hexdigest(),
        }
        case["checks"] = vs_checks(name, case)
        if name in ("VS-1", "VS-2", "VS-4", "VS-5", "VS-6a"):
            pick = {
                "VS-1": [c for c in case["claims"] if c["class"] in ("RETRACTED_WORK_CITED", "NOTICE_CITED")],
                "VS-2": [c for c in case["claims"] if c["class"] == "IDENTITY_CONFLICT"],
                "VS-4": [c for c in case["claims"] if c["class"] == "CONCERN_CITED"][:1],
                "VS-5": [c for c in case["claims"] if c["rule"] in ("D-10", "D-14")][:1],
                "VS-6a": [c for c in case["claims"] if c["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"][:1],
            }[name]
            case["provenance_walks"] = [
                walk(
                    work / "memory" / name,
                    case["investigation_key"],
                    c["claim_id"],
                    args.csv.resolve(),
                    work / "exports" / name,
                )
                for c in pick
            ]
            case["checks"]["provenance walk complete"] = bool(pick) and all(w["ok"] for w in case["provenance_walks"])
        cases[name] = case
    if "VS-1" in cases and (args.only is None or "extras" in args.only):
        ref = cases["VS-1"]
        cp = work / "checkpoints" / "vs1.json"
        cp.parent.mkdir()
        root = work / "memory" / "VS-1"
        karg = ("--memory-root", root, "--key", ref["investigation_key"])
        w = r.cli("checkpoint VS-1", "checkpoint", *karg, "--out", cp)
        v = r.cli("verify VS-1 --checkpoint", "verify", *karg, "--checkpoint", cp)
        checkpoint = json.loads(cp.read_bytes())
        shutil.copyfile(cp, RESULTS / "VS-1" / "checkpoint.json")
        results["checkpoint"] = {
            "write": _call(w),
            "verify": {
                "exit_code": v.code,
                "result": v.out["result"]["result"],
                "checkpoint": v.out["result"].get("checkpoint"),
            },
            "checkpoint": checkpoint,
            "matches_final_record": checkpoint.get("seq") == ref["journal"]["final_seq"]
            and checkpoint.get("journal_digest") == ref["journal"]["final_digest"],
        }
        results["vs9"] = vs9(r, index, ref)
    if args.only is None or "extras" in args.only:
        results["vs7"] = vs7(r, index)
        results["vs8"] = vs8(r, index, not args.no_live_wait)
        results["vs10"] = vs10(r, index)
        for x in results["vs7"] + results["vs8"][:2]:
            x["checks"] = failure_checks(x, created="lifecycle" in x)
        live = results["vs8"][2]
        live["checks"] = {
            "BLOCKED with not_before (exit 8)": live["lifecycle"] == "BLOCKED"
            and live["run"]["exit_code"] == 8
            and bool(live["acquire"]["not_before"]),
            "resume before not_before: still BLOCKED, ACQUIRE not started, journal unchanged": live["resume_before"][
                "exit_code"
            ]
            == 8
            and live["resume_before"]["acquire_attempts"] == 1
            and live["resume_before"]["journal_unchanged"],
            "the command did not sleep (resume returned in under 5 s)": live["resume_before"]["wall_s"] < 5,
            "no export while BLOCKED": live["export_while_blocked"]["exit_code"] == 8
            and not live["export_while_blocked"]["written"],
            "no claim, no report while BLOCKED": not live["claims_or_report"],
            "no network attempt by the command": live["network_attempts"] == 0,
        }
        if "resume_after" in live:
            ra = live["resume_after"]
            live["checks"]["resume at/after not_before starts ACQUIRE again and completes"] = (
                ra["started_at_or_after_not_before"]
                and ra["acquire_attempts"] == 2
                and ra["lifecycle"] == "NEEDS_RESOLUTION"
            )
        for x in results.get("vs9", []):
            x["checks"] = {
                "killed by SIGKILL with DETECT open, LOOKUP committed": x["killed"]["signal"] == 9
                and x["lookup_committed_before_kill"]
                and x["detect_open_at_kill"],
                "show after the kill: incomplete (exit 14)": x["show_after_kill"]["exit_code"] == 14,
                "ACQUIRE..LOOKUP not repeated": x["acquire_to_lookup_not_repeated"],
                "same claims": x["same_claims"],
                "same C(J)": x["same_content_digest"],
                "same report digest": x["same_report_digest"],
                "same projection-set digest": x["same_projection_set"],
                "no network attempt": x["network_attempts"] == 0,
            }
        v10 = results["vs10"]
        v10["checks"] = {
            "replay unchanged: reproduced": v10["unchanged"]["result"] == "reproduced",
            **{
                f"replay stale naming the change: {m['changed']}": m["replay"]["result"] == "stale"
                and m["replay"]["exit_code"] == 11
                and bool(m["replay"]["changed"])
                for m in v10["mutations"]
            },
            **{
                f"verify stale: {m['changed']}": m["verify"]["result"] == "stale" and m["verify"]["exit_code"] == 11
                for m in v10["mutations"]
            },
            "replay never writes the journal": all(m["journal_unchanged"] for m in v10["mutations"]),
            "D-062: other index bytes, same canonical content: reproduced, not stale": v10["index_bytes_only"]["result"]
            == "reproduced"
            and v10["index_bytes_only"]["journal_unchanged"],
            "D-062: forged index metadata: refused (exit 3, INDEX_CORRUPT), never stale, nothing written": all(
                x["exit_code"] == 3 and (x["error"] or {}).get("code") == "INDEX_CORRUPT" and x["journal_unchanged"]
                for x in v10["index_unverifiable"]
            ),
            "restored inputs: reproduced again": v10["restored"]["result"] == "reproduced",
            "D-057: another budget is another key; the first is not STALE": v10["d057"]["keys_differ"]
            and v10["d057"]["first_replay"] == "reproduced"
            and v10["d057"]["first_has_no_stale_record"]
            and v10["d057"]["first_journal_unchanged"],
            "no network attempt": v10["network_attempts"] == 0,
        }
    for name, case in cases.items():
        case.pop("_summary")
        case.pop("_root")
        results["cases"][name] = case
    results["i2"] = [
        {
            "case": n,
            "extraction_status": c["extraction_status"],
            "report_outcome": c["report_outcome"],
            "v1_statuses": sorted({v["status"] for v in c.get("v1_records", [])}),
            "cli_status": c["cli_status"],
            "export_status_code": c["exit_codes"]["export"],
            "lifecycle": c["lifecycle"],
        }
        for n, c in cases.items()
        if c["extraction_status"] == "partial"
    ]
    results["network"] = {
        "calls": len(r.calls),
        "attempts": sum(c.network_attempts for c in r.calls),
        "by_call": [[c.label, c.network_attempts] for c in r.calls if c.network_attempts],
        "isolation": "every call ran in `unshare -rn` (no network interface) with the socket counter of vs_entry.py",
    }
    results["calls"] = [_call(c) | {"label": c.label} for c in r.calls]
    results["seconds"] = round(time.perf_counter() - t0, 1)
    failed = {n: [k for k, ok in c["checks"].items() if not ok] for n, c in results["cases"].items()}
    for group in ("vs7", "vs8", "vs9"):
        for x in results.get(group, []):
            failed[x["case"]] = [k for k, ok in x.get("checks", {}).items() if not ok]
    if "vs10" in results:
        failed["VS-10"] = [k for k, ok in results["vs10"]["checks"].items() if not ok]
    if "checkpoint" in results:
        cp = results["checkpoint"]
        failed["checkpoint"] = (
            [] if cp["matches_final_record"] and cp["verify"]["result"] == "passed" else ["checkpoint"]
        )
    results["failed_checks"] = {n: f for n, f in failed.items() if f}
    text = json.dumps(rel(results, work), indent=1, sort_keys=True, ensure_ascii=False, default=str)
    (RESULTS / "vertical_slice.json").write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"failed_checks": results["failed_checks"], "seconds": results["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
