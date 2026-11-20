"""Step 13: the pre-registered evaluation tooling (owner decision D-069), on exposed development fixtures only.

The tools live in ``docs/verification/stage-04/evaluation/tools``, outside ``src/``; nothing in ``src/`` imports them.
Fixtures: the design-exposed bundles of VS-1 (MMR vaccine, Wakefield) and VS-2 (Obokata, arwiki 76190003), the
attributed Step 8 Retraction Watch subset index, synthetic frames and labels, and one recorded drand round. No
holdout article, label or prediction exists or is read here.
"""

from __future__ import annotations

import ast
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "docs/verification/stage-04/evaluation/tools"
EVALUATION = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import s13_acquire as AQ  # noqa: E402
import s13_baseline as BL  # noqa: E402
import s13_common as C  # noqa: E402
import s13_draw as DR  # noqa: E402
import s13_frame as FR  # noqa: E402
import s13_labels as LB  # noqa: E402
import s13_packets as PK  # noqa: E402
import s13_score as SC  # noqa: E402
import s13_sensitivity as SV  # noqa: E402

from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.plan import Integration  # noqa: E402

PARAMS = C.read_json(EVALUATION / "PARAMETERS.json")
WAKEFIELD = {("doi", "10.1016/s0140-6736(97)11096-0"), ("pmid", "9500320")}
LANCET_NOTICE = {("doi", "10.1016/s0140-6736(10)60175-4"), ("pmid", "20137807")}
OBOKATA_CONFLICT = [("doi", "10.1038/nature12969"), ("pmid", "24476881")]
# drand quicknet round 34062356, read from api.drand.sh on 2026-11-18 (a past round: a fixed public value).
DRAND_ROUND = {
    "round": 34062356,
    "randomness": "f977081543d017d79b303356d481dfc684fa6148c064304a0d90e3a66bf4e141",
    "signature": "8163ffdd5c91ef2c3cc456983c3ea93a338476913864bd95063c76cbd0e63808bb1b9469c41c10f225188e38766986a6",
}


# ------------------------------------------------------------------------------------------------ boundaries


@pytest.mark.unit
def test_tools_are_outside_src_and_never_imported_by_production() -> None:
    for path in (REPO / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "s13_" not in text and "evaluation/tools" not in text, path


@pytest.mark.unit
def test_tools_write_nothing_into_src() -> None:
    for path in TOOLS.glob("s13_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.startswith("src/"), (path.name, node.value)


@pytest.mark.unit
def test_retrieval_constants_are_the_preregistered_ones() -> None:
    r = PARAMS["retrieval"]
    assert (
        r["max_text_bytes"],
        r["min_title_tokens"],
        r["title_coverage"],
        r["max_title_records"],
    ) == (PK.MAX_TEXT, PK.MIN_TITLE_TOKENS, PK.TITLE_COVERAGE, PK.MAX_TITLE_RECORDS)


@pytest.mark.unit
def test_scorer_uses_the_four_positive_classes_of_d068() -> None:
    assert SC.POSITIVE == ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")
    assert set(SC.SECONDARY) < set(SC.POSITIVE)


@pytest.mark.unit
def test_variant_b_removes_only_rule_d6() -> None:
    assert [r[0] for r in dt1.RULES if r not in SV.NO_D6] == ["D-6"]
    assert len(SV.NO_D6) == len(dt1.RULES) - 1


# ------------------------------------------------------------------------------------------------ intervals


@pytest.mark.unit
def test_clopper_pearson_matches_the_mathematical_model() -> None:
    # MM 11.2: with x = 0, u = 1 - 0.05 ** (1 / n); n = 30 gives 0.0950 and n = 59 gives 0.0495.
    for n, want in ((30, 0.0950), (59, 0.0495)):
        u = C.clopper_pearson(0, n)["one_sided_95_upper"]
        assert abs(u - (1 - 0.05 ** (1 / n))) < 1e-9
        assert round(u, 4) == want
    r = C.clopper_pearson(3, 30)
    lo, hi = r["two_sided_95"]
    assert abs(C.binom_cdf(3, 30, hi) - 0.025) < 1e-9
    assert abs((1 - C.binom_cdf(2, 30, lo)) - 0.025) < 1e-9
    assert C.clopper_pearson(30, 30)["two_sided_95"][1] == 1.0
    assert C.clopper_pearson(0, 0)["estimate"] is None


# ------------------------------------------------------------------------------------------------ seed and draw


@pytest.mark.unit
def test_beacon_round_is_verified_and_the_seed_is_deterministic() -> None:
    assert DR.check_beacon(DRAND_ROUND, 34062356) == DRAND_ROUND["randomness"]
    with pytest.raises(ValueError):
        DR.check_beacon({**DRAND_ROUND, "randomness": "00" * 32}, 34062356)
    with pytest.raises(ValueError):
        DR.check_beacon(DRAND_ROUND, 34062357)
    s1 = DR.seed_of("d" * 64, 34062356, DRAND_ROUND["randomness"])
    assert s1 == DR.seed_of("d" * 64, 34062356, DRAND_ROUND["randomness"])
    assert s1 != DR.seed_of("e" * 64, 34062356, DRAND_ROUND["randomness"])


@pytest.mark.unit
def test_round_is_the_first_one_hour_after_acceptance() -> None:
    from datetime import UTC, datetime

    t = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)
    r = DR.round_for(t)
    assert DR.round_time(r) >= int(t.timestamp()) + 3600 > DR.round_time(r - 1)


def _frame(n1: int, n2: int) -> dict[str, Any]:
    def members(wiki: str) -> list[dict[str, Any]]:
        return [{"page_id": i, "title": f"{wiki}{i}", "stratum": "S1" if i < n1 else "S2"} for i in range(n1 + n2)]

    return {"frames": {w: {"frame": members(w)} for w in C.LANGUAGES}}


@pytest.mark.unit
def test_plan_follows_the_allocation_in_draw_order_without_repeats() -> None:
    sampling = PARAMS["sampling"]
    seed = "a" * 64
    plan = DR.plan(_frame(150, 60), seed, sampling)
    assert plan == DR.plan(_frame(150, 60), seed, sampling)
    for wiki in C.LANGUAGES:
        pos = plan[wiki]["positions"]
        ids = [p["page_id"] for p in pos]
        assert len(ids) == len(set(ids))
        alloc = sampling["allocation"][wiki]
        for block in ("primary", "reserve"):
            for s in ("S1", "S2"):
                assert sum(1 for p in pos if p["block"] == block and p["stratum"] == s) == alloc[block][s]
        for s in ("S1", "S2"):
            keys = [p["order_key"] for p in pos if p["stratum"] == s]
            assert keys == sorted(keys)
    assert DR.plan(_frame(150, 60), "b" * 64, sampling) != plan


# ------------------------------------------------------------------------------------------------ frame


@pytest.mark.unit
def test_frame_strata_and_exclusion() -> None:
    def page(pid: int, title: str, nature: str, side: str) -> dict[str, Any]:
        return {
            "page_id": pid,
            "ns": 0,
            "title": title,
            "redirect": False,
            "records": [{"nature": nature, "via": [{"side": side}]}],
        }

    scans = {
        "ar": {
            "wiki": "ar",
            "dumps": {},
            "retraction_watch": {},
            "pages": [
                page(1, "A", "Retraction", "original"),
                page(2, "B", "Retraction", "notice"),
                page(3, "C", "Correction", "original"),
                {**page(4, "D", "Retraction", "original"), "redirect": True},
            ],
        },
        "en": {
            "wiki": "en",
            "dumps": {},
            "retraction_watch": {},
            "pages": [
                page(1, "x", "Retraction", "original"),
                page(7, "Exposed title", "Retraction", "original"),
                page(8, "Listed", "Retraction", "original"),
                page(9, "Fine", "Expression of concern", "original"),
            ],
        },
    }
    manifest = {
        "articles": [
            {"wiki": "en", "page_id": None, "titles": ["Exposed_title"]},
            {"wiki": "ar", "page_id": 3, "titles": []},
        ]
    }
    listed = {"page_ids": [1], "titles": ["listed"]}
    out = FR.build(scans, manifest, listed, True)
    assert [(m["page_id"], m["stratum"]) for m in out["ar"]["frame"]] == [(2, "S2")]
    assert {e["page_id"]: e["reasons"] for e in out["ar"]["excluded"]} == {
        1: ["listed_page_id"],
        3: ["exposure_page_id"],
    }
    assert [(m["page_id"], m["stratum"]) for m in out["en"]["frame"]] == [(9, "S2")]
    assert {e["page_id"]: e["reasons"][0] for e in out["en"]["excluded"]} == {
        1: "listed_page_id",
        7: "exposure_title",
        8: "listed_title",
    }
    assert out["ar"]["counts"]["namespace0_non_redirect"] == 3
    kept = FR.build(scans, manifest, listed, False)  # listed tier recorded, not applied (PARAMETERS.json frame)
    assert [(m["page_id"], m.get("listed_only", False)) for m in kept["en"]["frame"]] == [
        (1, True),
        (8, True),
        (9, False),
    ]
    assert {e["page_id"] for e in kept["en"]["excluded"]} == {7}
    other = FR.build(
        {**scans, "ar": {**scans["ar"], "pages": [page(5, "Exposed title", "Retraction", "original")]}},
        manifest,
        listed,
        False,
    )
    assert [e["reasons"] for e in other["ar"]["excluded"]] == [["exposure_title_other_wiki"]]


# ------------------------------------------------------------------------------------------------ labels


def _label(
    iid: str, recs: dict[str, str], kind: str = "work_citation", same: str = "yes", att: str = "yes"
) -> dict[str, Any]:
    return {
        "item_id": iid,
        "kind": kind,
        "same_work": same,
        "records": recs,
        "single_identifier_attachable": att,
        "note": "",
    }


@pytest.mark.unit
def test_label_format_lock_and_merge(tmp_path: Path) -> None:
    items = [{"item_id": "i1", "records": [{"ref": "R1"}]}, {"item_id": "i2", "records": [{"ref": "R1"}]}]
    packet = tmp_path / "packets" / "p.json"
    C.write_json(packet, {"items": items})
    a = [_label("i1", {"R1": "cited_work"}), _label("i2", {"R1": "cited_work"})]
    b = [_label("i1", {"R1": "cited_work"}), _label("i2", {"R1": "unrelated"})]
    adj = [_label("i2", {"R1": "unrelated"})]
    rd = tmp_path / "rounds" / "primary"
    for role, labs in (("A", a), ("B", b), ("ADJ", adj)):
        C.write_json(rd / f"{role}.json", {"format": LB.FORMAT, "annotator": role, "labels": labs})
    assert LB.label_problems({**a[0], "kind": "bogus"}, items[0]) == ["kind 'bogus'"]
    assert LB.label_problems({**a[0], "records": {}}, items[0])
    res = LB.lock([packet], rd / "A.json", rd / "B.json", rd / "ADJ.json", rd / "LOCK.json")
    assert res["disagreed"] == 1
    assert res["final"]["i1"]["source"] == "agreed" and res["final"]["i2"]["source"] == "adjudicated"
    assert res["final"]["i2"]["records"] == {"R1": "unrelated"}
    assert res["packets"] == {"p.json": C.file_sha256(packet)}
    merged = LB.merge([rd / "LOCK.json"], tmp_path / "LOCK.json")
    assert merged["final"] == res["final"] and list(merged["rounds"]) == ["primary"]
    with pytest.raises(ValueError):
        LB.merge([rd / "LOCK.json", rd / "LOCK.json"], tmp_path / "LOCK2.json")
    C.write_json(rd / "ADJ.json", {"format": LB.FORMAT, "annotator": "ADJ", "labels": []})
    with pytest.raises(ValueError):
        LB.lock([packet], rd / "A.json", rd / "B.json", rd / "ADJ.json", rd / "LOCK.json")


# ------------------------------------------------------------------------------------------------ real fixtures


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def mmr_packet(index: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    return PK.packet(S8.EN_MMR, index)


@pytest.mark.integration
def test_packet_is_engine_independent_and_reaches_wakefield(mmr_packet: tuple[dict[str, Any], dict[str, Any]]) -> None:
    packet, extraction = mmr_packet
    assert packet["extraction_digest"] == extraction["extraction_digest"]
    text = json.dumps(packet)
    for stage04 in ("RETRACTED_WORK_CITED", "NOTICE_CITED", '"class"', '"rule"', "primary_citation_field"):
        assert stage04 not in text
    by_unit = {it["unit_id"]: it for it in packet["items"]}
    wake = [
        it for it in by_unit.values() if {(i["scheme"], i.get("normalized")) for i in it["identifiers"]} >= WAKEFIELD
    ]
    assert len(wake) == 1
    assert any(r.endswith(" as original") for rec in wake[0]["records"] for r in rec["reached_by"])
    notice = [
        it
        for it in by_unit.values()
        if {(i["scheme"], i.get("normalized")) for i in it["identifiers"]} >= LANCET_NOTICE
    ]
    assert len(notice) == 1
    assert all(
        not r.endswith(" as original")
        for rec in notice[0]["records"]
        for r in rec["reached_by"]
        if not r.startswith("title")
    )
    assert packet["items_digest"] == C.digest(packet["items"])


@pytest.mark.integration
def test_baseline_flags_the_notice_citation_too(mmr_packet: tuple[dict[str, Any], dict[str, Any]], index: Path) -> None:
    _, extraction = mmr_packet
    with sqlite3.connect(f"file:{index}?mode=ro", uri=True) as conn:
        flagged = BL.flagged_units(extraction, conn)
    keys = BL.eligible_keys(extraction)
    assert any(keys[u] >= WAKEFIELD for u in flagged)
    assert any(keys[u] >= LANCET_NOTICE for u in flagged)


class _Inv:
    def __init__(self, tmp: Path, bundle: Path, index: Path) -> None:
        with pytest.MonkeyPatch.context() as mp:
            offline = S8.NoNetwork(mp)
            self.root = S8.memory_root(tmp)
            self.payload = S8.create(self.root, S8.request(bundle, index, self.root))
            self.result = S8.run(self.root, self.payload, Integration())
            assert offline.attempts == []
        self.key = self.payload["investigation_key"]


@pytest.fixture(scope="module")
def obokata(tmp_path_factory: pytest.TempPathFactory, index: Path) -> _Inv:
    return _Inv(tmp_path_factory.mktemp("ar"), S8.AR_OBOKATA, index)


@pytest.mark.integration
def test_variants_on_obokata_self_checks_and_variant_b(obokata: _Inv) -> None:
    assert obokata.result.status == "NEEDS_RESOLUTION"
    var = SV.variants(obokata.root, obokata.key)  # raises Unfaithful if a self-check fails
    conflict = [
        r for r, v in var["frozen"].items() if [(k["scheme"], k["normalized"]) for k in v["keys"]] == OBOKATA_CONFLICT
    ]
    assert len(conflict) == 1
    ref = conflict[0]
    assert var["frozen"][ref]["class"] == "IDENTITY_CONFLICT" and var["frozen"][ref]["rule"] == "D-6"
    assert var["b"][ref]["class"] != "IDENTITY_CONFLICT"  # protection disabled: the case is decided otherwise
    for v in ("a", "c"):
        assert all(c["class"] for c in var[v].values())
    assert {r: v["class"] for r, v in var["frozen"].items()} == {
        r: v["class"] for r, v in SV.variants(obokata.root, obokata.key)["frozen"].items()
    }


@pytest.mark.integration
def test_variant_a_never_adds_a_candidate(obokata: _Inv) -> None:
    var = SV.variants(obokata.root, obokata.key)
    assert len(var["a"]) <= len(var["frozen"]) <= len(var["c"])


@pytest.mark.integration
def test_sensitivity_refuses_an_unfaithful_memory(obokata: _Inv, monkeypatch: pytest.MonkeyPatch) -> None:
    real = SV.classify

    def wrong(inputs: Any, lookups: Any, rules: Any = dt1.RULES) -> dict[str, Any]:
        out = real(inputs, lookups, rules)
        for v in out.values():
            v["class"] = "NOT_FOUND_IN_CHECKED_SOURCES"
        return out

    monkeypatch.setattr(SV, "classify", wrong)
    with pytest.raises(SV.Unfaithful):
        SV.variants(obokata.root, obokata.key)


# ------------------------------------------------------------------------------------------------ scorer


def _index_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE event (ordinal INTEGER, event_id TEXT);"
        "CREATE TABLE ident (ordinal INTEGER, scheme TEXT, norm TEXT, role TEXT);"
        "INSERT INTO event VALUES (1, 'ev-1'), (2, 'ev-2');"
        "INSERT INTO ident VALUES (1, 'doi', '10.1/work', 'original'), (1, 'doi', '10.1/notice', 'notice'),"
        "(2, 'doi', '10.2/other', 'original');"
    )
    return conn


def _item(uid: str) -> dict[str, Any]:
    return {
        "item_id": f"x-{uid}",
        "unit_id": uid,
        "records": [
            {"ref": "R1", "event_id": "ev-1", "reached_by": ["doi:10.1/work as original"]},
            {"ref": "R2", "event_id": "ev-2", "reached_by": ["doi:10.2/other as original"]},
        ],
    }


@pytest.mark.unit
def test_scorer_correct_false_and_hazards() -> None:
    conn = _index_db()
    work = [{"scheme": "doi", "normalized": "10.1/work"}]
    notice = [{"scheme": "doi", "normalized": "10.1/notice"}]
    units = {
        "u1": [{"class": "RETRACTED_WORK_CITED", "keys": work}],
        "u2": [{"class": "RETRACTED_WORK_CITED", "keys": work}],
        "u3": [{"class": "CORRECTION_CITED", "keys": work}],
        "u4": [{"class": "NOT_FOUND_IN_CHECKED_SOURCES", "keys": notice}],
        "u5": [{"class": "IDENTITY_CONFLICT", "keys": work}],
        "u6": [{"class": "RETRACTED_WORK_CITED", "keys": work}],
    }
    items = {u: _item(u) for u in units}
    labels = {
        "u1": _label("x-u1", {"R1": "cited_work", "R2": "unrelated"}),
        "u2": _label("x-u2", {"R1": "unrelated", "R2": "unrelated"}),
        "u3": _label("x-u3", {"R1": "cited_notice", "R2": "unrelated"}, kind="notice_citation"),
        "u4": _label("x-u4", {"R1": "cited_work", "R2": "unrelated"}),
        "u5": _label("x-u5", {"R1": "cited_work", "R2": "cited_work"}, same="no", att="yes"),
    }
    out = SC.score_units(units, items, labels, conn)
    pos = {p["unit_id"]: p for p in out["positive"]}
    assert pos["u1"]["correct"] and not pos["u2"]["correct"] and not pos["u3"]["correct"]
    assert pos["u6"]["unannotated"] and not pos["u6"]["correct"]
    hazards = {(h["unit_id"], h["hazard"]) for h in out["hazards"]}
    assert ("u3", "H1_NOTICE_AS_ATTACHMENT") in hazards
    assert ("u4", "H4_EXACT_MISS") in hazards
    assert out["negative"] == [{"unit_id": "u4", "truth_positive": True}]
    (conf,) = out["conflict"]
    assert conf["unit_id"] == "u5" and conf["abstained"] and conf["abstention_justified"]
    assert conf["single_identifier_attachable"] == "yes" and not conf["converted_to_positive"]


@pytest.mark.unit
def test_scorer_converted_conflict_is_a_hazard_and_never_correct() -> None:
    conn = _index_db()
    work = [{"scheme": "doi", "normalized": "10.1/work"}]
    units = {"u5": [{"class": "RETRACTED_WORK_CITED", "keys": work}]}
    labels = {"u5": _label("x-u5", {"R1": "cited_work", "R2": "cited_work"}, same="no")}
    out = SC.score_units(units, {"u5": _item("u5")}, labels, conn)
    assert not out["positive"][0]["correct"]
    assert {"unit_id": "u5", "hazard": "H3_CONFLICT_AS_ATTACHMENT"} in out["hazards"]
    assert out["conflict"][0]["converted_to_positive"]


@pytest.mark.unit
def test_summary_gates() -> None:
    def art(n_pos: int, n_false: int, n_neg: int) -> dict[str, Any]:
        positive = [
            {
                "unit_id": f"p{i}",
                "classes": ["RETRACTED_WORK_CITED"],
                "correct": i >= n_false,
                "unannotated": False,
                "unverifiable": False,
            }
            for i in range(n_pos)
        ]
        negative = [{"unit_id": f"n{i}", "truth_positive": False} for i in range(n_neg)]
        engine = {"positive": positive, "negative": negative, "conflict": [], "hazards": []}
        return {"article": "en-1", "wiki": "en", "truth_positive_units": [], "structural": [], "engine": engine}

    params = {"gates": PARAMS["gates"]}
    s = SC.summarize([art(30, 0, 60)], params)["en"]
    assert s["passed"] and s["false_attachment_rate"]["one_sided_95_upper"] < 0.0951
    s = SC.summarize([art(30, 1, 60)], params)["en"]
    assert not s["gates"]["G2_false_attachment_bound"]
    s = SC.summarize([art(59, 1, 60)], params)["en"]
    assert s["gates"]["G2_false_attachment_bound"]
    s = SC.summarize([art(29, 0, 60)], params)["en"]
    assert not s["gates"]["G1_positive_denominator"]
    s = SC.summarize([art(30, 0, 59)], params)["en"]
    assert not s["gates"]["G5_negative_denominator"]
    assert SC.summarize([art(30, 0, 60)], params)["ar"]["positive_units"] == 0


@pytest.mark.unit
def test_forbidden_phrases_are_the_frozen_list() -> None:
    from citerift.investigation.explanations import FORBIDDEN

    assert SC.FORBIDDEN is FORBIDDEN
    assert SC.forbidden_in("The citation is clean.") == ["clean"]
    assert SC.forbidden_in("Not found in the checked sources.") == []


# ------------------------------------------------------------------------------------------------ acquisition


@pytest.mark.unit
def test_acquisition_replaces_failures_by_reserves_and_counts_attempts(tmp_path: Path) -> None:
    plan = DR.plan(_frame(150, 60), "c" * 64, PARAMS["sampling"])
    C.write_json(tmp_path / "DRAW.json", {"seed": "c" * 64, "plan": plan})
    first_s1 = next(p for p in plan["ar"]["positions"] if p["block"] == "primary" and p["stratum"] == "S1")

    def capture(pos: dict[str, Any], out: Path) -> tuple[int, str]:
        if pos["page_id"] == first_s1["page_id"]:
            return 7, "REDIRECT_NOT_FOLLOWED"
        out.mkdir(parents=True)
        return 0, "ok"

    def make_packet(bundle: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        page_id = int(bundle.name.split("-", 1)[1])  # the bundle directory is <wiki>-<page_id>
        art = {"revision_id": 1, "page_id": page_id, "title": f"t{page_id}"}
        return (
            {"extraction_status": "complete", "article": art, "extraction_digest": "d", "items": []},
            {"extraction_digest": "d"},
        )

    log = AQ.acquire_round(tmp_path, "primary", PARAMS, capture, make_packet, sleep=lambda s: None)
    failed = [a for a in log["attempts"] if a["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["failure"] == "CAPTURE_FAILED"
    reserve = next(p for p in plan["ar"]["positions"] if p["block"] == "reserve" and p["stratum"] == "S1")
    assert failed[0]["replaced_by"] == f"ar-{reserve['page_id']}"
    acquired = C.read_json(tmp_path / "rounds" / "primary" / "ARTICLES.json")["articles"]
    assert len(acquired) == 60 and f"ar-{reserve['page_id']}" in acquired
    assert AQ.attempts_used(log) == 61
    with pytest.raises(ValueError):
        AQ.acquire_round(tmp_path, "primary", PARAMS, capture, make_packet, sleep=lambda s: None)


@pytest.mark.unit
def test_transient_capture_is_retried_then_fails(tmp_path: Path) -> None:
    calls: list[int] = []

    def capture(pos: dict[str, Any], out: Path) -> tuple[int, str]:
        calls.append(1)
        return 4, "unavailable"

    pos = {"wiki": "en", "page_id": 5, "title": "t", "stratum": "S1", "block": "primary"}
    rec = AQ.acquire_one(pos, tmp_path, PARAMS, capture, lambda b: ({}, {}), sleep=lambda s: None)
    assert rec["status"] == "failed" and len(calls) == PARAMS["acquisition"]["transient_retries"] + 1


@pytest.mark.unit
def test_expansion_counts_are_engine_independent() -> None:
    item = {
        "records": [
            {"ref": "R1", "reached_by": ["doi:10.1/work as original"]},
            {"ref": "R2", "reached_by": ["title tokens (0.90 of the record title)"]},
        ]
    }
    assert AQ.id_reached_truth_positive(item, _label("i", {"R1": "cited_work", "R2": "unrelated"}))
    assert not AQ.id_reached_truth_positive(item, _label("i", {"R1": "unrelated", "R2": "cited_work"}))
    assert not AQ.id_reached_truth_positive(item, _label("i", {"R1": "cited_work", "R2": "x"}, same="no"))
    conn = _index_db()
    ext = {
        "identifiers": [
            {
                "unit_id": "u1",
                "role": "primary_citation_field",
                "scheme": "doi",
                "normalization": {"valid": True, "normalized": "10.9/none"},
            },
            {
                "unit_id": "u2",
                "role": "identifier_link",
                "scheme": "doi",
                "normalization": {"valid": True, "normalized": "10.1/work"},
            },
            {
                "unit_id": "u3",
                "role": "labeled_reference_text",
                "scheme": "doi",
                "normalization": {"valid": True, "normalized": "10.9/other"},
            },
        ]
    }
    assert AQ.negative_proxy_units(ext, conn) == 1


# ------------------------------------------------------------------------------------------------ run guard


# Owner decision D-074 (2026-11-19): the frozen-engine check is proved in its historical context. The repository HEAD
# no longer has to equal the superseded engine b5bf8ed (D-071 replaced it by dt-2); P is identified by its historical
# commit 827ac1a and its digest, and the proof reads those git objects. P itself is not changed.

PREREG_COMMIT = "827ac1aa1d9d16d444d4860e4119f8633d8e802e"
P_DIGEST = "4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a"
FROZEN_ENGINE = "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0"
CAMPAIGN_COMMIT = "1064113902c674f1c61dcb7eda33afe40350ca71"
MANIFEST_REL = "docs/verification/stage-04/evaluation/PREREGISTRATION_MANIFEST.json"
THIS_TEST = "tests/stage04/test_step13_evaluation.py"  # changed by D-074 only; its P bytes are proved from git


def _git(*args: str, text: bool = True) -> Any:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True, text=text).stdout


def _require_history() -> None:
    for commit in (PREREG_COMMIT, FROZEN_ENGINE, CAMPAIGN_COMMIT):
        probe = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO, capture_output=True, check=False
        )
        if probe.returncode != 0:
            pytest.fail(f"commit {commit} is missing: the historical proof needs the full history (no shallow clone)")


def _historical_manifest() -> dict[str, Any]:
    return json.loads(_git("show", f"{PREREG_COMMIT}:{MANIFEST_REL}"))


@pytest.mark.unit
def test_p_resolves_to_the_historical_preregistration_files() -> None:
    """D-074 (1, 2): the manifest at 827ac1a has digest P, every file it lists hashes, at 827ac1a, to its recorded
    SHA-256, and the manifest in the tree is that same manifest."""
    import hashlib

    _require_history()
    manifest = _historical_manifest()
    assert C.digest(manifest) == P_DIGEST
    assert (REPO / MANIFEST_REL).read_bytes() == _git("show", f"{PREREG_COMMIT}:{MANIFEST_REL}", text=False)
    assert len(manifest["files"]) > 20
    for f in manifest["files"]:
        blob = _git("show", f"{PREREG_COMMIT}:{f['path']}", text=False)
        assert hashlib.sha256(blob).hexdigest() == f["sha256"], f["path"]


@pytest.mark.unit
def test_p_files_are_unchanged_in_the_tree_except_this_test() -> None:
    """D-074: every pre-registered file except this test file still has its P bytes; this file alone differs, and
    only because D-074 replaced its frozen-engine check (its P bytes are proved from git above)."""
    changed = sorted(
        f["path"] for f in _historical_manifest()["files"] if C.file_sha256(REPO / f["path"]) != f["sha256"]
    )
    assert changed == [THIS_TEST]


@pytest.mark.unit
def test_p_names_the_superseded_frozen_engine() -> None:
    """D-074 (3): the frozen engine named by P is exactly b5bf8ed, its tree and its freeze manifest digest."""
    _require_history()
    frozen = _historical_manifest()["frozen_engine"]
    assert frozen == PARAMS["frozen_engine"]
    assert frozen["content_commit"] == FROZEN_ENGINE
    assert frozen["tree"] == _git("rev-parse", f"{FROZEN_ENGINE}^{{tree}}").strip()
    assert frozen["freeze_manifest_digest"] == "609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc"


def _historical_checkout(tmp: Path, commit: str, paths: list[str]) -> Path:
    """A worktree at ``commit`` with only ``paths`` checked out (the frozen check reads only those)."""
    wt = tmp / "frozen"
    _git("worktree", "add", "--no-checkout", "--detach", str(wt), commit)
    subprocess.run(["git", "reset", "-q"], cwd=wt, check=True)
    subprocess.run(["git", "checkout", "--", *paths], cwd=wt, check=True)
    return wt


@pytest.mark.unit
def test_the_historical_frozen_check_passes_on_the_historical_frozen_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-074 (4, 5): the pre-registered run guard (``s13_run.frozen_check``, unchanged) passes on the frozen tree
    b5bf8ed, and the trees it reports are exactly those the Step 14 campaign recorded when it ran."""
    import s13_run as RN

    _require_history()
    paths = PARAMS["frozen_engine"]["checked_paths"]
    wt = _historical_checkout(tmp_path, FROZEN_ENGINE, paths)
    try:
        monkeypatch.setattr(C, "REPO", wt)  # s13_common.git runs in C.REPO
        historical_params = json.loads(
            _git("show", f"{PREREG_COMMIT}:docs/verification/stage-04/evaluation/PARAMETERS.json")
        )
        res = RN.frozen_check(historical_params)
    finally:
        monkeypatch.undo()
        _git("worktree", "remove", "--force", str(wt))
    assert res["head"] == FROZEN_ENGINE
    assert set(res["trees"]) == set(paths)
    run = json.loads(_git("show", f"{CAMPAIGN_COMMIT}:docs/verification/stage-04/evaluation-campaign/run/RUN.json"))
    assert (REPO / "docs/verification/stage-04/evaluation-campaign/run/RUN.json").read_text(encoding="utf-8") == (
        _git("show", f"{CAMPAIGN_COMMIT}:docs/verification/stage-04/evaluation-campaign/run/RUN.json")
    )
    assert run["checks"]["frozen"]["content_commit"] == FROZEN_ENGINE
    assert run["checks"]["frozen"]["trees"] == res["trees"]
    assert run["checks"]["preregistration"]["prereg_digest"] == P_DIGEST


@pytest.mark.unit
def test_the_current_engine_is_not_the_superseded_frozen_engine() -> None:
    """D-074 (6): the current engine (dt-3 since D-083) has a different identity and must not satisfy the old guard."""
    import s13_run as RN

    _require_history()
    with pytest.raises(SystemExit, match="the engine is not the frozen one"):
        RN.frozen_check(PARAMS)
    assert dt1.TABLE_VERSION == "dt-4"
    frozen_dt1 = _git("show", f"{FROZEN_ENGINE}:src/citerift/investigation/dt1.py")
    assert 'TABLE_VERSION = "dt-1"' in frozen_dt1


@pytest.mark.unit
def test_capture_identity_is_rechecked_against_the_exposure_rule(tmp_path: Path) -> None:
    def capture(pos: dict[str, Any], out: Path) -> tuple[int, str]:
        out.mkdir(parents=True)
        return 0, "ok"

    def packet_for(page_id: int, title: str) -> Any:
        def make(bundle: Path) -> tuple[dict[str, Any], dict[str, Any]]:
            art = {"page_id": page_id, "title": title, "revision_id": 9, "wiki": "en"}
            return (
                {"extraction_status": "complete", "article": art, "extraction_digest": "d", "items": []},
                {"extraction_digest": "d"},
            )

        return make

    def excluded(wiki: str, page_id: int, title: str) -> list[str]:
        return ["exposure_title"] if title == "Moved here" else []

    pos = {"wiki": "en", "page_id": 5, "title": "t", "stratum": "S1", "block": "primary"}
    rec = AQ.acquire_one(pos, tmp_path / "a", PARAMS, capture, packet_for(5, "Moved here"), lambda s: None, excluded)
    assert (rec["status"], rec["failure"]) == ("failed", "EXPOSED_AT_CAPTURE")
    rec = AQ.acquire_one(pos, tmp_path / "b", PARAMS, capture, packet_for(6, "t"), lambda s: None, excluded)
    assert (rec["status"], rec["failure"]) == ("failed", "PAGE_ID_MISMATCH")
    rec = AQ.acquire_one(pos, tmp_path / "c", PARAMS, capture, packet_for(5, "t"), lambda s: None, excluded)
    assert rec["status"] == "acquired"


@pytest.mark.unit
def test_exposure_check_uses_the_committed_listed_tier() -> None:
    excluded = AQ.exposure_check()
    manifest = C.read_json(FR.EXPOSURE)
    exposed = next(a for a in manifest["articles"] if a["page_id"] is not None)
    assert "exposure_page_id" in excluded(exposed["wiki"], int(exposed["page_id"]), "Some other title")


@pytest.mark.unit
def test_combine_joins_instances_of_one_role(tmp_path: Path) -> None:
    for i, iid in enumerate(("i1", "i2")):
        C.write_json(
            tmp_path / f"a{i}.json",
            {
                "format": LB.FORMAT,
                "annotator": "A",
                "instance": f"A-{i}",
                "model": "m",
                "labels": [_label(iid, {"R1": "cited_work"})],
            },
        )
    res = LB.combine("A", [tmp_path / "a0.json", tmp_path / "a1.json"], tmp_path / "A.json")
    assert [lab["item_id"] for lab in res["labels"]] == ["i1", "i2"] and len(res["instances"]) == 2
    with pytest.raises(ValueError):
        LB.combine("A", [tmp_path / "a0.json", tmp_path / "a0.json"], tmp_path / "A2.json")
    with pytest.raises(ValueError):
        LB.combine("B", [tmp_path / "a0.json"], tmp_path / "B.json")


@pytest.mark.unit
def test_preregistration_manifest_matches_the_files() -> None:
    """The manifest in the tree is the one P names, and ``s13_manifest.build`` over today's files differs from it only
    in this test file's digest (owner decision D-074); the P bytes of this file are proved from git above."""
    import s13_manifest as MF

    assert MF.MANIFEST.exists()
    recorded = C.read_json(MF.MANIFEST)
    assert C.digest(recorded) == P_DIGEST
    now = MF.build()
    assert {k: v for k, v in now.items() if k != "files"} == {k: v for k, v in recorded.items() if k != "files"}
    assert [f["path"] for f in now["files"]] == [f["path"] for f in recorded["files"]]
    differing = [a["path"] for a, b in zip(now["files"], recorded["files"], strict=True) if a != b]
    assert differing == [THIS_TEST]
    assert recorded["frozen_engine"] == PARAMS["frozen_engine"]
