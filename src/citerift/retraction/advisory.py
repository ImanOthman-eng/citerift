"""Evidence Ambiguity Investigator boundary (SPECIFICATION.md 12.1).

A model may only suggest one of the supplied candidates or abstain. Its output is parsed here into an
``AdvisorySuggestion``, which has no path into the store: this module imports neither the build nor the
query modules, and nothing in the package accepts an ``AdvisorySuggestion`` as evidence. Every malformed,
unsupported or over-reaching output becomes an abstention with a reason code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from citerift.contracts.formats import loads_strict
from citerift.retraction.schemas import advisory_problems

BUNDLE_FIELDS = ("title", "authors", "journal", "original_year")
MAX_CANDIDATES = 5
MAX_RATIONALE = 2000
INSTRUCTIONS = """You are the advisory component of a bibliographic record-linking evaluation.

STRICT RULES:
- Do NOT use any tools (no file reads, no shell, no web). Answer only from the bundle below. A response
  produced after any tool use is invalid.
- You only suggest a link; you never state facts about retraction status.
- Reply with exactly one JSON object and nothing else, with exactly these keys:
  {"decision": "select" | "abstain", "candidate_id": string or null, "cited_pointers": [JSON pointers into
  the bundle], "rationale": string of at most 2000 characters}
- "candidate_id" is one of the supplied candidate ids when decision is "select", and null when "abstain".
- Cite only pointers that exist in the bundle. Never include keys named verified_fact, retraction_status,
  status, value or provenance.
- Abstain when the evidence does not single out one candidate. Abstaining is a correct answer when no
  candidate is the same paper.

TASK: The query record's own paper identifiers are masked. Decide whether exactly one candidate describes
the same original paper as the query record, or abstain.

BUNDLE:
"""


@dataclass(frozen=True)
class AdvisorySuggestion:
    """A model's suggestion. Advisory only: never a link, a fact or a projection input."""

    decision: str  # "select" or "abstain"
    candidate_id: str | None
    cited_pointers: tuple[str, ...]
    rationale: str
    reason_code: str | None = None  # why an output became an abstention
    problems: tuple[str, ...] = field(default=())

    def to_json(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "candidate_id": self.candidate_id,
            "cited_pointers": list(self.cited_pointers),
            "rationale": self.rationale,
            "reason_code": self.reason_code,
            "problems": list(self.problems),
            "advisory": True,
        }


def make_bundle(query: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """A bounded bundle: the query's fields and at most five candidates (ids c1..c5), no identifiers."""
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError("at most five candidates")
    return {
        "query": {k: query.get(k) for k in BUNDLE_FIELDS},
        "candidates": [
            {"candidate_id": f"c{i}", **{k: c.get(k) for k in BUNDLE_FIELDS}} for i, c in enumerate(candidates, 1)
        ],
    }


def pointers_of(bundle: dict[str, Any]) -> set[str]:
    out = {f"/query/{k}" for k in bundle["query"]} | {"/query"}
    for i, c in enumerate(bundle["candidates"]):
        out |= {f"/candidates/{i}"} | {f"/candidates/{i}/{k}" for k in c}
    return out


def prompt_text(bundle: dict[str, Any]) -> str:
    return INSTRUCTIONS + json.dumps(bundle, ensure_ascii=False, sort_keys=True)


def _abstain(reason: str, problems: list[str] | None = None) -> AdvisorySuggestion:
    return AdvisorySuggestion("abstain", None, (), "", reason, tuple(problems or ()))


def interpret(
    text: str | None, bundle: dict[str, Any], *, failure: str | None = None, tool_uses: tuple[str, ...] = ()
) -> AdvisorySuggestion:
    """Turn raw model output into a suggestion. ``failure`` is a transport, timeout or budget reason;
    ``tool_uses`` lists tools the call used other than the harness's hand-back."""
    if failure is not None:
        return _abstain(failure)
    if tool_uses:
        return _abstain("TOOL_USE_DETECTED", list(tool_uses))
    if text is None:
        return _abstain("EMPTY_OUTPUT")
    try:
        response = loads_strict(text.strip())
    except ValueError as exc:
        return _abstain("OUTPUT_NOT_JSON", [str(exc)[:200]])
    ids = {c["candidate_id"] for c in bundle["candidates"]}
    problems = advisory_problems(response, ids, pointers_of(bundle))
    if problems:
        code = problems[0].code
        reason = {
            "FORBIDDEN_KEY": "FORBIDDEN_KEY",
            "UNKNOWN_CANDIDATE": "UNKNOWN_CANDIDATE",
            "UNSUPPLIED_POINTER": "UNSUPPLIED_POINTER",
        }.get(code, "SCHEMA_INVALID")
        return _abstain(reason, [str(p) for p in problems[:5]])
    return AdvisorySuggestion(
        response["decision"],
        response["candidate_id"],
        tuple(response["cited_pointers"]),
        response["rationale"][:MAX_RATIONALE],
    )
