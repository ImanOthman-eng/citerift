"""Stage 04 P2: the descriptive sensitivity variants (owner decision D-069; planning package 8.4).

P2 (D-076): the same variants on the frozen freeze-2 engine, whose decision table is dt-2 (``dt1.TABLE_VERSION``;
the module keeps its historical name). ``dt1.decide`` and ``dt1.RULES`` are the frozen dt-2 ones, so the self-check
reproduces dt-2 claims, variant (b) removes only rule D-6 (the dt-2 role-collision guard in D-10 stays), and no
variant disables or approximates the role-collision guard. The callers (``p2_dev``, ``p2_score``) check the engine
identity first.

Computed from the frozen retained intermediate evidence of each investigation (its Investigation Memory, opened
read-only), with the frozen functions of the engine called as they are. Nothing in ``src/`` is changed and nothing
here is imported by production code. No lookup is ever made: a variant that needs a Stage 02 lookup the investigation
did not retain is reported as ``NOT_COMPUTABLE`` for that unit, never approximated.

- **baseline** (self-check): the frozen candidate inputs and lookups through ``dt1.decide`` with the frozen table;
  every class must equal the committed claim's class, otherwise the tool stops (it would not be faithful).
- **(a) identifier_link excluded**: the committed Stage 03 extraction with every ``identifier_link`` occurrence given
  the role ``labeled_reference_text`` (a non-candidate role: NORMALIZE treats both as ``OBSERVATION_ROLE``, and
  ``role`` is read nowhere else except ``unresolved``), run through the frozen ``normalize`` adapter; then dt-1.
- **(b) P-2 / identity-conflict protection disabled**: the frozen candidates and lookups through ``dt1.decide`` with
  the frozen table without rule D-6 (``rules`` is a parameter of the frozen ``decide``).
- **(c) labeled_reference_text included**: the extraction with every ``labeled_reference_text`` occurrence given the
  candidate role ``identifier_link``, through the frozen ``normalize``; then dt-1.

For (a) and (c) the frozen ``normalize`` is first run on the unmodified extraction, and its output must equal the
committed candidate inputs byte for byte (faithfulness self-check). Every Q1 lookup of every keyed occurrence (any
role) is retained by the engine (S-6.7), so only a new DOI-PMID pair (a Q2 query) can be missing.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.investigation import dt1
from citerift.investigation.adapters import StepRequest, Succeeded
from citerift.investigation.adapters import normalize as norm_adapter
from citerift.investigation.adapters.detector import candidate_view, lookup_roles, lookup_view
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.memory import InvestigationMemory

SCHEMA = "urn:citerift:schema:investigation:v1:"
EXTRACTION = "urn:citerift:schema:wiki:v1:extraction"
NOT_COMPUTABLE = "NOT_COMPUTABLE"
NO_D6 = tuple(r for r in dt1.RULES if r[0] != "D-6")
RELABEL = {"a": ("identifier_link", "labeled_reference_text"), "c": ("labeled_reference_text", "identifier_link")}


class Unfaithful(Exception):
    """A self-check failed: the variant would not be computed by the frozen functions on the retained evidence."""


class Retained:
    """The committed records and blobs of one investigation, read-only."""

    def __init__(self, root: Path, key: str) -> None:
        with InvestigationMemory.open(root, key, writable=False) as mem:
            self.root = copy.deepcopy(mem.view.root)
            self.logical = [copy.deepcopy(r) for r in mem.view.logical]
            self.raw: dict[str, bytes] = {d: mem.blobs.get(d) for d in mem.view.referenced_blobs()}
        self.json: dict[str, Any] = {}
        for d, data in self.raw.items():
            try:
                self.json[d] = json.loads(data)
            except ValueError:
                continue

    def one(self, schema: str) -> tuple[str, dict[str, Any]]:
        found = [(d, v) for d, v in self.json.items() if isinstance(v, dict) and v.get("schema") == schema]
        if len(found) != 1:
            raise Unfaithful(f"{len(found)} blobs of schema {schema}")
        return found[0]

    def claims(self) -> list[dict[str, Any]]:
        return [r["payload"] for r in self.logical if r["kind"] == "claim_recorded"]

    def lookups(self) -> dict[str, dt1.Lookup]:
        """Every retained lookup, by canonical query."""
        _, plan = self.one(SCHEMA + "lookup-plan")
        return {canon(e["query"]).decode(): lookup_view(self.json[e["observation"]]) for e in plan["lookups"]}


def classify(inputs: Mapping[str, Any], lookups: Mapping[str, dt1.Lookup], rules: Any = dt1.RULES) -> dict[str, Any]:
    """Class of every candidate (by cand_ref), or NOT_COMPUTABLE when a needed lookup was not retained."""
    units = {u["unit_id"]: u for u in inputs["units"]}
    out: dict[str, Any] = {}
    for cand in inputs["candidates"]:
        queries = [q for _, q in _roles(cand)]
        if any(q not in lookups for q in queries):
            out[cand["cand_ref"]] = {"unit_id": cand["unit_id"], "class": NOT_COMPUTABLE, "keys": cand["keys"]}
            continue
        view = candidate_view(cand, units[cand["unit_id"]], {q: lookups[q] for q in queries})
        outcome = dt1.decide(view, rules)
        out[cand["cand_ref"]] = {
            "unit_id": cand["unit_id"],
            "class": outcome.cls if outcome.cls is not None else outcome.failure,
            "rule": outcome.rule,
            "keys": cand["keys"],
        }
    return out


def _roles(cand: Mapping[str, Any]) -> list[tuple[str, str]]:
    return lookup_roles(cand)


def _normalize(ret: Retained, extraction: dict[str, Any]) -> dict[str, Any]:
    """The frozen NORMALIZE adapter on ``extraction`` (in place of the committed one); its candidate-inputs blob."""
    manifest_digest, _ = ret.one(SCHEMA + "bundle-observation")
    ext_bytes = canon(extraction, allow_float=True)
    ext_digest = sha256_hex(ext_bytes)
    blobs = dict(ret.json)
    blobs[ext_digest] = extraction

    def read_blob(d: str) -> Any:
        return copy.deepcopy(blobs[d])

    def read_bytes(d: str) -> bytes:
        return ret.raw.get(d, ext_bytes)

    req = StepRequest(
        step="NORMALIZE",
        attempt=1,
        step_key="sensitivity",
        live=False,
        request={},
        request_key={},
        root=ret.root,
        inputs={"ACQUIRE": (manifest_digest,), "EXTRACT": (ext_digest,)},
        committed=(),
        stored=(),
        content_digest="",
        read_blob=read_blob,
        read_bytes=read_bytes,
        now=datetime(2026, 1, 1, tzinfo=UTC),
        investigation={},
    )
    res = norm_adapter.normalize(req)
    if not isinstance(res, Succeeded):
        raise Unfaithful(f"frozen NORMALIZE failed: {res}")
    return dict(res.blobs[0])


def variants(root: Path, key: str) -> dict[str, Any]:
    """Per candidate, the frozen class and the class under (a), (b) and (c); plus the self-checks."""
    ret = Retained(root, key)
    lookups = ret.lookups()
    _, inputs = ret.one(SCHEMA + "candidate-inputs")
    _, extraction = ret.one(EXTRACTION)
    committed = {c["cand_ref"]: c["class"] for c in ret.claims()}
    frozen = classify(inputs, lookups)
    mismatch = [r for r, v in frozen.items() if committed.get(r) != v["class"]]
    if mismatch or set(committed) != set(frozen):
        raise Unfaithful(f"dt-1 on the retained inputs differs from the committed claims: {mismatch[:3]}")
    again = _normalize(ret, extraction)
    if canon(again, allow_float=True) != canon(inputs, allow_float=True):
        raise Unfaithful("the frozen NORMALIZE on the committed extraction does not reproduce the candidate inputs")
    out: dict[str, Any] = {"frozen": frozen, "b": classify(inputs, lookups, NO_D6)}
    for name, (old, new) in RELABEL.items():
        ext = copy.deepcopy(extraction)
        for ident in ext["identifiers"]:
            if ident["role"] == old:
                ident["role"] = new
        out[name] = classify(_normalize(ret, ext), lookups)
    return out


def unit_classes(per_candidate: Mapping[str, Any]) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}
    for v in per_candidate.values():
        out.setdefault(v["unit_id"], set()).add(v["class"])
    return {u: sorted(c) for u, c in sorted(out.items())}
