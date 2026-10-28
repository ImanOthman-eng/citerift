"""Evidence Tension invariants and metamorphic properties over seeded random evidence sets (SPECIFICATION.md
11.2; directive section 14 metamorphic properties: redistributed duplication is not an independent witness,
evidence removal cannot manufacture a positive observation, views never mutate evidence)."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from citerift.retraction import policy, tension
from citerift.retraction.dates import parse_rw_date

TYPES = ("retracted", "correction", "expression_of_concern", "reinstated", None)
ORIGINS = ("retraction-watch", "publisher", "crossref", "unknown")
SEEDS = range(300)


def random_set(seed: int) -> policy.EvidenceSet:
    rng = random.Random(seed)  # a fixed, reproducible draw
    assertions = []
    for i in range(rng.randint(1, 6)):
        rw = i == 0 or rng.random() < 0.5
        day = rng.choice([1, 2, 15, 28])
        assertions.append(
            policy.TypedAssertion(
                assertion_id=f"a{i}",
                origin="retraction-watch" if rw else rng.choice(ORIGINS),
                channel="rw-gitlab-csv" if rw else "crossref-rest-api",
                type=rng.choice(TYPES[:4]) if rw else rng.choice(TYPES),
                notice_key=rng.choice([None, "doi:10.5555/n1", "doi:10.5555/n2"]),
                anchor="doi:10.5555/o",
                source_ref={"source_id": "retraction-watch" if rw else "crossref", "locator": f"loc-{i}"},
                event_id=f"ev-{i + 1:07d}" if rw else None,
                notice_date=parse_rw_date(f"{rng.randint(1, 12)}/{day}/{rng.randint(2001, 2020)} 0:00", "notice_date")
                if rw
                else None,
                bridged=rw and i > 0 and rng.random() < 0.3,
                notice_ambiguous=rng.random() < 0.2,
                depends_on=("retraction-watch",) if not rw and rng.random() < 0.4 else (),
            )
        )
    sources = ({"source_id": "retraction-watch"},) + (({"source_id": "crossref"},) if rng.random() < 0.6 else ())
    identity = "bridged" if any(a.bridged for a in assertions) else "exact"
    return policy.EvidenceSet("matched", identity, "doi:10.5555/o", tuple(assertions), sources, (), rng.random() < 0.1)


def plans(es: policy.EvidenceSet) -> list[tuple[str, tuple[str, ...]]]:
    origins = tension.origins_in(es)
    return [
        ("collapse_shared_origin", ()),
        *[("exclude_origin", (o,)) for o in origins],
        ("exclude_ambiguous_links", ()),
        ("require_temporal_bounds", ()),
    ]


def _views_never_mutate_or_invent_evidence(seed: int) -> None:
    es = random_set(seed)
    digest = tension.set_digest(es)
    base = policy.reduce(es)
    base_ids = {a.assertion_id for a in es.assertions}
    base_types = {a.type for a in es.assertions if a.type is not None}
    for name, origins in plans(es):
        v, affected = tension.view(es, name, origins)
        assert tension.set_digest(es) == digest  # the input is never changed
        assert set(affected) <= base_ids
        assert {a.assertion_id for a in v.assertions} <= base_ids  # nothing added
        reduced = policy.reduce(v)
        assert set(reduced["basis"]["supporting_assertions"]) <= base_ids
        value = reduced["retraction_status"]["value"]
        if value in TYPES[:4]:
            assert value in base_types  # removal cannot manufacture a positive observation
        if name != "collapse_shared_origin":
            assert reduced["compare"]["support.observations"] <= max(len(es.assertions), 0)
        # Withholding a date never invents one; a withheld date is never a verified fact.
        withheld_date = reduced["retraction_date"] if name == "require_temporal_bounds" else None
        if withheld_date is not None and withheld_date["status"] == "verified_fact":
            assert base["retraction_date"] is not None and base["retraction_date"]["status"] == "verified_fact"


def _collapse_counts_origins_not_channels(seed: int) -> None:
    es = random_set(seed)
    base = policy.reduce(es)
    collapsed = policy.reduce(replace(es, collapse=True))
    assert collapsed["compare"]["support.observations"] == len(base["basis"]["origins"])
    assert collapsed["retraction_status"] == base["retraction_status"]  # accounting only, never the answer


def _redistributed_copy_is_not_an_independent_witness(seed: int) -> None:
    es = random_set(seed)
    base = policy.reduce(es)
    support = [a for a in es.assertions if a.assertion_id in base["basis"]["supporting_assertions"]]
    if not support:
        return
    copy = replace(support[0], assertion_id="redistributed", channel="mirror", event_id=None, notice_date=None)
    more = replace(es, assertions=(*es.assertions, copy))
    after = policy.reduce(more)
    assert after["retraction_status"]["status"] == base["retraction_status"]["status"]
    assert after["retraction_status"]["value"] == base["retraction_status"]["value"]
    assert after["basis"]["origins"] == base["basis"]["origins"]  # the same origin, however many channels
    collapsed_before = policy.reduce(replace(es, collapse=True))["compare"]["support.observations"]
    collapsed_after = policy.reduce(replace(more, collapse=True))["compare"]["support.observations"]
    assert collapsed_after == collapsed_before


def _report_is_deterministic_and_bounded(seed: int) -> None:
    es = random_set(seed)
    a = [tension.run_intervention(es, n, o) for n, o in plans(es)]
    b = [tension.run_intervention(es, n, o) for n, o in plans(es)]
    assert a == b
    classes = tension.diagnostic_classes(a)
    assert classes == ["control"] or "control" not in classes
    for r in a:
        if not r["applicable"]:
            assert r["changed_fields"] == []  # an inapplicable intervention changes nothing
    with pytest.raises(tension.TensionError):
        tension.view(es, "exclude_origin", ("a", "b", "c"))
    with pytest.raises(tension.TensionError):
        tension.view(es, "exclude_origin", ())
    with pytest.raises(tension.TensionError):
        tension.view(es, "all_subsets")


@pytest.mark.simulation
def test_rde_control_without_diagnostics() -> None:
    a = policy.TypedAssertion(
        "ev-0000001/event_type",
        policy.RW_ORIGIN,
        "rw-gitlab-csv",
        "retracted",
        "doi:10.5555/n",
        "doi:10.5555/o",
        {"source_id": "retraction-watch", "locator": "x"},
        event_id="ev-0000001",
        notice_date=parse_rw_date("3/12/2015 0:00", "notice_date"),
    )
    es = policy.EvidenceSet("matched", "exact", "doi:10.5555/o", (a,), ({"source_id": "retraction-watch"},))
    results = [tension.run_intervention(es, n, o) for n, o in tension.default_plan(es)]
    assert tension.diagnostic_classes(results) == ["control"]
    assert all(r["changed_fields"] == [] for r in results)
    assert [n for n, _ in tension.default_plan(es)] == [
        "collapse_shared_origin",
        "exclude_ambiguous_links",
        "require_temporal_bounds",
    ]  # a single origin gets no exclude_origin step


@pytest.mark.simulation
def test_rde_views_never_mutate_or_invent_evidence() -> None:
    for seed in SEEDS:
        try:
            _views_never_mutate_or_invent_evidence(seed)
        except AssertionError as exc:
            raise AssertionError(f"seed {seed}: {exc}") from exc


@pytest.mark.simulation
def test_rde_collapse_counts_origins_not_channels() -> None:
    for seed in SEEDS:
        try:
            _collapse_counts_origins_not_channels(seed)
        except AssertionError as exc:
            raise AssertionError(f"seed {seed}: {exc}") from exc


@pytest.mark.simulation
def test_rde_redistributed_copy_is_not_an_independent_witness() -> None:
    for seed in SEEDS:
        try:
            _redistributed_copy_is_not_an_independent_witness(seed)
        except AssertionError as exc:
            raise AssertionError(f"seed {seed}: {exc}") from exc


@pytest.mark.simulation
def test_rde_report_is_deterministic_and_bounded() -> None:
    for seed in SEEDS:
        try:
            _report_is_deterministic_and_bounded(seed)
        except AssertionError as exc:
            raise AssertionError(f"seed {seed}: {exc}") from exc
