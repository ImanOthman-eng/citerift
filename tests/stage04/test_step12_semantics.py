"""Stage 04 Step 12: the dt-1 detector and explanation corrections of Reviewer A (STEP12_TRIAGE.md).

- A-01: a D-12 claim (``no_record`` with a coverage gap) is explained as "no record matched" with the unchecked rows,
  never as "a record exists"; the reason and limitation texts name quarantined rows or invalid identifiers.
- A-03: every taint reason has its chain (S-12.1): the unit's identifier occurrences support every claim that carries
  a taint reason, a tainted D-6 claim included; the rule, class, status and reasons stay those of the frozen model.
- A-04: the co-reported text no longer says the citation names more than one work.

Synthetic DETECT inputs of ``step9_support`` (the frozen Step 4 reference model's cases); no network, no index.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

import pytest
import step9_support as S9

from citerift.investigation import explanations, ids
from citerift.investigation.adapters.detector import dt1_detector

pytestmark = pytest.mark.unit

R = S9.R
DEFAULT_SHAPE = {
    "matched": "vf:retracted",
    "ambiguous_identity": "unc:ambiguous",
    "no_record": "unc:not_found",
}


def lk(state: str, shape: str = "") -> Any:
    return (state, shape or DEFAULT_SHAPE[state], False)


def _detect(case: Any) -> tuple[dict[str, Any], dict[str, Any], Any]:
    inp, _ = S9.concretize(case)
    out = dt1_detector(inp)
    assert len(out.claims) == 1
    claim, value_set = out.claims[0]
    return dict(claim), dict(value_set), inp


def _occurrences(value: Any) -> set[str]:
    """Every identifier-occurrence id the units of the DETECT input name."""
    found: set[str] = set()
    if isinstance(value, dict):
        if isinstance(value.get("occurrences"), list):
            found.update(value["occurrences"])
        for v in value.values():
            found |= _occurrences(v)
    elif isinstance(value, list):
        for v in value:
            found |= _occurrences(v)
    return found


TAINTED_D6 = R.Case(
    "CITED",
    "PAIR",
    frozenset({"IDENTIFIER_UNCONFIRMED"}),
    False,
    lk("matched"),
    lk("no_record"),
    lk("ambiguous_identity"),
    wd=True,
    w2=True,
)


def test_a03_a_tainted_d6_claim_is_supported_by_the_units_occurrences() -> None:
    """The unit also holds a malformed identifier (an occurrence that is no key): the claim's taint reason must have
    that occurrence in its supporting evidence (fails without the Step 12 change: only the key occurrences were)."""
    inp, blobs = S9.concretize(TAINTED_D6)
    inputs = copy.deepcopy(inp.candidate_inputs)
    blobs[inputs["extraction"]]["identifiers"].append(
        {"id": "id-x", "scheme": "doi", "unit_id": "un-1", "normalization": {"valid": False, "normalized": None}}
    )
    extra = ids.evidence_id(inputs["extraction"], "/identifiers/2", "identifier_occurrence")
    unit = inputs["units"][0]
    unit["occurrences"] = [*unit["occurrences"], extra]  # a new list: the candidate's key evidence is unchanged
    out = dt1_detector(dataclasses.replace(inp, candidate_inputs=inputs))
    [(claim, value_set)] = out.claims
    exp = S9.expected(TAINTED_D6)
    assert (claim["rule"], claim["class"], sorted(claim["reasons"])) == (exp["rule"], exp["class"], exp["reasons"])
    assert claim["rule"] == "D-6" and "IDENTIFIER_UNCONFIRMED" in claim["reasons"]
    occurrences = _occurrences(inputs)
    assert extra in occurrences and occurrences <= set(value_set["supporting"])


def test_a03_an_untainted_d6_claim_is_unchanged_by_the_taint_rule() -> None:
    untainted = R.Case("CITED", "PAIR", frozenset(), False, *TAINTED_D6.lookups(), wd=True, w2=True)
    claim, _, _ = _detect(untainted)
    exp = S9.expected(untainted)
    assert (claim["rule"], sorted(claim["reasons"])) == (exp["rule"], exp["reasons"])
    assert not {"IDENTIFIER_UNCONFIRMED", "IDENTIFIER_MALFORMED", "IDENTIFIER_ROLE_UNRESOLVED"} & set(claim["reasons"])


def _entry(claim: dict[str, Any]) -> dict[str, Any]:
    unit = {"unit_id": "un-1", "byte_start": 0, "byte_end": 1, "unit_span_sha256": "0" * 64}
    return {"claim": claim, "checked_sources": [], "unit": unit, "question": None, "decision": {"disposition": "-"}}


def test_a01_a_d12_claim_never_says_a_record_exists() -> None:
    case = R.Case("CITED", "DOI", frozenset(), False, lk("no_record", "unc:gap"), None, None)
    claim, _, _ = _detect(case)
    assert (claim["rule"], claim["class"]) == ("D-12", "UNRESOLVED_STATUS")
    text = explanations.claim_explanation(_entry(claim))["text"]
    assert "A record exists" not in text
    assert text.startswith("No record in the checked sources matched this citation")
    assert "quarantined rows or invalid identifiers" in text
    assert "invalid identifiers" in explanations.REASON_TEXT["COVERAGE_GAP_RELEVANT_ROWS"]
    assert "invalid identifiers" in explanations.LIMITATION_TEMPLATES["UNRESOLVED_STATUS"]


def test_a01_a_d11_claim_keeps_the_record_exists_text() -> None:
    case = R.Case("CITED", "DOI", frozenset(), False, lk("matched", "unc"), None, None)
    claim, _, _ = _detect(case)
    assert (claim["rule"], claim["class"]) == ("D-11", "UNRESOLVED_STATUS")
    assert explanations.claim_explanation(_entry(claim))["text"].startswith("A record exists")


def test_a04_the_co_reported_text_names_identifiers_not_works() -> None:
    text = explanations.REASON_TEXT["CO_REPORTED_MULTIPLE"]
    assert "more than one work" not in text and "identifier" in text
