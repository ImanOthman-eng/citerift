"""Reducer invariants of MATHEMATICAL_MODEL.md 4 (INV-P1 to INV-P3, INV-P8) over seeded random evidence sets.

Directive section 9: a concern followed by retraction is not a conflict, a later correction does not undo a
retraction, and a reinstatement changes nothing without supersession evidence."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from citerift.retraction import policy
from citerift.retraction.dates import parse_rw_date

TYPES = ("retracted", "correction", "expression_of_concern", "reinstated")
ORIGINS = ("retraction-watch", "publisher", "crossref", "unknown")
NOTICES = (None, "doi:10.5555/n1", "doi:10.5555/n2")
SEEDS = range(400)


def _assertion(rng: random.Random, i: int, type_: str, notice: str | None, rw: bool) -> policy.TypedAssertion:
    return policy.TypedAssertion(
        assertion_id=f"a{i}",
        origin="retraction-watch" if rw else rng.choice(ORIGINS),
        channel="rw-gitlab-csv" if rw else "crossref-rest-api",
        type=type_,
        notice_key=notice,
        anchor="doi:10.5555/o",
        source_ref={"source_id": "retraction-watch" if rw else "crossref", "locator": f"loc-{i}"},
        event_id=f"ev-{i + 1:07d}" if rw else None,
        notice_date=parse_rw_date(
            f"{rng.randint(1, 12)}/{rng.choice([1, 2, 15, 28])}/{rng.randint(2001, 2020)} 0:00", "notice_date"
        )
        if rw
        else None,
    )


def random_set(seed: int, types: tuple[str, ...] = TYPES) -> policy.EvidenceSet:
    rng = random.Random(seed)  # a fixed, reproducible draw
    assertions = tuple(
        _assertion(rng, i, rng.choice(types), rng.choice(NOTICES), i == 0 or rng.random() < 0.6)
        for i in range(rng.randint(1, 6))
    )
    return policy.EvidenceSet("matched", "exact", "doi:10.5555/o", assertions, ({"source_id": "retraction-watch"},))


def _status(es: policy.EvidenceSet) -> tuple[str, str | None]:
    s = policy.reduce(es)["retraction_status"]
    return s["status"], s["value"]


@pytest.mark.regression
def test_rde_inv_p1_retracted_needs_a_clear_known_origin_retraction() -> None:
    checked = 0
    for seed in SEEDS:
        es = random_set(seed)
        out = policy.reduce(es)
        if out["retraction_status"]["value"] == "retracted":
            checked += 1
            support = {a.assertion_id: a for a in es.assertions}
            ids = out["basis"]["supporting_assertions"]
            assert ids and all(support[i].type == "retracted" for i in ids), seed
            assert any(support[i].origin != "unknown" for i in ids), seed  # INV-P8
    assert checked >= 50  # the draw is not vacuous


@pytest.mark.regression
def test_rde_inv_p2_a_later_concern_or_correction_does_not_undo_a_retraction() -> None:
    checked = 0
    for seed in SEEDS:
        es = random_set(seed, ("retracted", "correction", "expression_of_concern"))
        if _status(es) != ("verified_fact", "retracted"):
            continue
        checked += 1
        rng = random.Random(seed + 10_000)
        added = [
            # another proposition: a separate notice of the same original
            _assertion(rng, 50, rng.choice(("correction", "expression_of_concern")), "doi:10.5555/other", True),
            _assertion(rng, 51, "correction", None, False),
        ]
        for extra in added:
            assert _status(policy.with_assertions(es, [*es.assertions, extra])) == ("verified_fact", "retracted"), seed
    assert checked >= 50


@pytest.mark.regression
@pytest.mark.parametrize("gap", [1, 400])
def test_rde_inv_p2_concern_then_retraction_on_one_notice_is_not_a_conflict(gap: int) -> None:
    rng = random.Random(gap)
    concern = _assertion(rng, 0, "expression_of_concern", "doi:10.5555/n1", True)
    retraction = _assertion(rng, 1, "retracted", "doi:10.5555/n1", True)
    later = "3/11/2015 0:00" if gap == 1 else "4/14/2016 0:00"
    concern = replace(concern, notice_date=parse_rw_date("3/10/2015 0:00", "notice_date"))
    retraction = replace(retraction, notice_date=parse_rw_date(later, "notice_date"))
    es = policy.EvidenceSet(
        "matched", "exact", "doi:10.5555/o", (concern, retraction), ({"source_id": "retraction-watch"},)
    )
    out = policy.reduce(es)
    assert (out["retraction_status"]["status"], out["retraction_status"]["value"]) == ("verified_fact", "retracted")
    assert "SEQUENTIAL_EVENTS_SHARE_NOTICE" in out["basis"]["reasons"]


@pytest.mark.regression
def test_rde_inv_p3_no_reinstatement_without_supersession() -> None:
    checked = 0
    for seed in SEEDS:
        es = random_set(seed)
        if any(a.type == "reinstated" for a in es.assertions):
            checked += 1
            assert _status(es) == ("uncertain", None), seed
    sole = random_set(0, ("reinstated",))  # C-11: reinstatements alone are unlinked too
    assert _status(sole) == ("uncertain", None)
    assert checked >= 50
