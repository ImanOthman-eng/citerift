"""Tools of the 2026-11-02 confirmation campaign (``evaluation/confirmation-2026-11/scripts``): the draw and the
positive warning challenge. SYNTHETIC: a scripted API stand-in and synthetic bundles; no request is made."""

from __future__ import annotations

import importlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from wiki_support import bundle, doi_link, extract, note_li, ref_sup, references

SCRIPTS = Path(__file__).resolve().parents[2] / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts"
sys.path.insert(0, str(SCRIPTS))
sel = importlib.import_module("select_confirmation")
wc = importlib.import_module("warning_challenge")


# ------------------------------------------------------------------------------------------------ the draw


class FakeApi:
    """list=random gives pages 1..N per batch; ids divisible by 3 link to doi.org; embeddedin lists given pages."""

    def __init__(self, per_batch: int, embedded: dict[str, list[int]]) -> None:
        self.per_batch = per_batch
        self.batch = 0
        self.embedded = embedded
        self.urls: list[str] = []

    def __call__(self, url: str) -> Any:
        self.urls.append(url)
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        if q.get("list") == "random":
            start = self.batch * self.per_batch
            self.batch += 1
            return {
                "query": {"random": [{"id": i, "title": f"T{i}"} for i in range(start + 1, start + 1 + self.per_batch)]}
            }
        if q.get("prop") == "extlinks":
            pages = [int(x) for x in q["pageids"].split("|")]
            return {
                "query": {"pages": [{"pageid": p, "extlinks": [{"url": "x"}] if p % 3 == 0 else []} for p in pages]}
            }
        if q.get("list") == "embeddedin":
            ids = self.embedded.get(q["eititle"], [])
            return {"query": {"embeddedin": [{"pageid": p, "title": f"E{p}"} for p in ids]}}
        raise AssertionError(url)


@pytest.mark.unit
def test_the_draw_orders_by_salted_hash_and_excludes_exposure() -> None:
    api = FakeApi(500, {"Template:Retracted": [9001, 9002, 3], "Template:Erratum": [9002, 9003]})
    out = sel.select(api, {"page_ids": [3, 6], "titles": ["T9"]})
    ar, en = out["frame"]["ar"], out["frame"]["en"]
    assert {3, 6, 9} <= set(ar["excluded_as_exposed"])
    order = [r["page_id"] for r in ar["eligible_order"]]
    assert order == sorted(order, key=lambda p: sel.order(sel.SALT, "ar", p))
    assert len(ar["initial"]) == 24 and [len(b) for b in ar["reserve_blocks"]] == [4] * 6
    assert len(en["initial"]) == 16 and [len(b) for b in en["reserve_blocks"]] == [4] * 4
    assert [r["position"] for r in ar["initial"]] == list(range(1, 25))
    # 500 random pages give 164 eligible: one batch is enough
    assert sum(1 for u in api.urls if "list=random" in u and "ar.wikipedia" in u) == 1
    # challenge: exposed (3) and drawn pages excluded; an article is placed in its first stratum only
    ch = out["challenge"]["en"]
    assert [r["page_id"] for r in ch["retraction"]["selected"]] == sorted(
        [9001, 9002], key=lambda p: sel.order(sel.CHALLENGE_SALT, "en", "retraction", p)
    )
    assert [r["page_id"] for r in ch["correction"]["selected"]] == [9003]


@pytest.mark.unit
def test_a_thin_frame_stops_at_the_batch_limit() -> None:
    api = FakeApi(15, {})
    out = sel.select(api, {"page_ids": [], "titles": []})
    ar = out["frame"]["ar"]
    assert len(ar["batches"]) == sel.MAX_BATCHES["ar"] and ar["eligible"] == 6 * 5
    assert len(ar["initial"]) == 24 and [len(b) for b in ar["reserve_blocks"]] == [4, 2]  # a short last block


@pytest.mark.unit
def test_the_capture_plan_takes_whole_blocks_in_order() -> None:
    api = FakeApi(500, {"Template:Retracted": [9001]})
    out = sel.select(api, {"page_ids": [], "titles": []})
    p = sel.plan(out, {"ar": 2}, with_challenge=True)
    splits = Counter((a["split"], a["wiki"]) for a in p["articles"])
    assert splits == {
        ("holdout", "ar"): 24,
        ("holdout", "en"): 16,
        ("reserve1", "ar"): 4,
        ("reserve2", "ar"): 4,
        ("challenge", "en"): 1,
    }
    ids = [a["page_id"] for a in p["articles"] if a["split"] == "reserve1"]
    assert ids == [r["page_id"] for r in out["frame"]["ar"]["reserve_blocks"][0]]


# -------------------------------------------------------------------------------------- warning challenge


def long_text(marker: str, before: int = 9000) -> str:
    filler = "".join(f"Line {i} of filler text.<ref>Plain {i}.</ref>\n" for i in range(before // 30))
    return filler + f'Claim.<ref name="a">{{{{cite journal |title=Paper |doi=10.1000/p}}}} {marker}</ref>\n' + filler


@pytest.mark.unit
def test_the_challenge_window_holds_a_marker_call() -> None:
    text = long_text("{{Retracted|doi=10.1000/n}}")
    ws, we = wc.challenge_window(text, "en", 1)
    assert we - ws == 8000 and ws <= text.index("{{Retracted") < we


@pytest.mark.unit
def test_hidden_marker_calls_are_not_window_anchors() -> None:
    text = long_text("<!-- {{Retracted|doi=10.1000/n}} -->")
    assert wc.marker_calls(text, "en") == []
    assert wc.challenge_window(text, "en", 1) == wc.v1.window(text, "en", 1)


@pytest.mark.unit
def test_arabic_marker_calls_are_found() -> None:
    assert wc.marker_calls("أ<ref>x {{مصدر مسحوب|دوي=10.1/x}}</ref>", "ar") == [8]
    assert wc.marker_calls("{{قالب:Expression_of concern|x}}", "ar") == [0]


@pytest.mark.integration
def test_the_challenge_score_reports_detection_and_its_denominator(tmp_path: Path) -> None:
    text = 'A.<ref name="a">{{cite journal |title=Paper |doi=10.1000/p}} {{Retracted|doi=10.1000/n}}</ref>\n'
    inner = (
        "<cite>Paper. " + doi_link("10.1000/p") + "</cite> <span>(Retracted, see " + doi_link("10.1000/n") + ")</span>"
    )
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], inner)])
    )
    path = bundle(tmp_path, text, body)
    (tmp_path / "x.json").write_text(json.dumps(extract(path)))
    art = wc.load(path)
    cp = text.index('<ref name="a">')
    ann = {
        "format": "citerift-stage03-annotation-v1",
        "article": {
            "wiki": "en",
            "revision_id": art.revision_id,
            "source_sha256": art.source_sha256,
            "html_sha256": art.html_sha256,
            "window": list(art.window),
        },
        "definitions": [
            {
                "id": "d1",
                "at": {"cp": cp, "quote": text[cp : cp + 14]},
                "in_window": True,
                "kind": "note",
                "name": "a",
                "group": "",
                "templates": [],
                "unstructured": False,
                "render_note_id": "cite_note-a-1",
                "marker": "warning",
                "marker_text": "Retracted",
            }
        ],
        "uses": [],
        "identifiers": [],
    }
    (tmp_path / "a.json").write_text(json.dumps(ann))
    spec = {"articles": [{"bundle": str(path), "extraction": "x.json", "locked": "a.json", "stratum": "retraction"}]}
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    got = wc.score(tmp_path / "spec.json")["labels"]["locked"]["en/retraction"]
    assert got["labelled_warnings"] == 1 and got["sensitivity"] == 1.0 and got["fabricated_negatives"] == 0


@pytest.mark.unit
def test_the_challenge_summary_counts_misses_as_fabricated_negatives() -> None:
    s = wc.summarize(
        Counter({"warning->none": 1, "warning->warning": 3, "none->warning": 2, "warning->not_inspected": 1})
    )
    assert s["labelled_warnings"] == 5 and s["sensitivity"] == 3 / 5
    assert s["fabricated_negatives"] == 1 and s["false_warnings"] == 2 and s["not_inspected"] == 1
    assert wc.summarize(Counter())["sensitivity"] is None


# ------------------------------------------------------------------------------------------ reserve step

rs = importlib.import_module("reserve_step")


def _label(tmp: Path, wiki: str, rev: int, ids: int) -> tuple[Path, Path]:
    b = tmp / f"b{rev}"
    b.mkdir()
    (b / "capture.json").write_text(json.dumps({"page": {"wiki": wiki, "revision_id": rev}}))
    ann = {
        "article": {"window": [0, 100]},
        "definitions": [{"at": {"cp": 1}, "in_window": True}] * 3,
        "uses": [{"at": {"cp": 1}, "render_ref_id": "x"}] * 4,
        "identifiers": [{"at": {"cp": 1}, "role": "primary_citation_field"}] * ids,
    }
    f = tmp / "locks" / f"{wiki}-{rev}.json"
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(ann))
    return b, f


@pytest.mark.unit
def test_the_reserve_step_adds_the_next_block_from_locked_counts_only(tmp_path: Path) -> None:
    api = FakeApi(500, {})
    selection = sel.select(api, {"page_ids": [], "titles": []})
    states: dict[str, Any] = {}
    labels: dict[str, Path] = {}
    for wiki in ("ar", "en"):
        for i, r in enumerate(selection["frame"][wiki]["initial"]):
            rev = r["page_id"] * 10 + (1 if wiki == "ar" else 2)
            b, f = _label(tmp_path, wiki, rev, ids=2 if wiki == "ar" else 4)
            states[f"holdout/{wiki}-{r['page_id']}"] = {"final": {"bundle": str(b) if i else None}}
            labels[f.name] = f
    d = rs.decide(selection, states, labels)
    # ar: 23 captured x 2 identifiers = 46 < 50 -> the next block; en: 15 x 4 = 60 >= 50 and other minimums met
    assert d["ar"]["totals"]["target_identifiers"] == 46 and d["ar"]["next_block"] == "reserve1"
    assert d["en"]["minimums_met"] == {
        "target_identifiers": True,
        "uses": False,
        "definitions": False,
        "linkable_uses": True,
    }
    assert d["en"]["next_block"] == "reserve1"  # uses 60 < 80, definitions 45 < 60
    assert d["ar"]["rows"][0]["counts"] is None  # a failed capture counts 0 and is not replaced


@pytest.mark.unit
def test_the_reserve_step_refuses_an_unlocked_or_changed_label(tmp_path: Path) -> None:
    d = tmp_path / "lock"
    d.mkdir()
    (d / "ar-1.json").write_text("{}")
    (d / "ANNOTATION_LOCK.json").write_text(json.dumps({"ar-1.json": "0" * 64}))
    with pytest.raises(SystemExit, match="locked hash"):
        rs.locked_labels([d], check_git=False)


@pytest.mark.unit
def test_disagreements_v2_list_no_repeated_definition_as_extra(tmp_path: Path) -> None:
    dv2 = importlib.import_module("disagreements_v2")
    text = 'A.{{sfn|Smith|2001}} B.{{sfn|Smith|2001}} C.<ref name="j">X</ref> D.<ref name="j">X</ref>\n'
    path = bundle(tmp_path, text)
    (tmp_path / "x.json").write_text(json.dumps(extract(path)))
    art = wc.v1.load_bundle(path)

    def d(needle: str) -> dict[str, Any]:
        cp = text.index(needle)
        return {"at": {"cp": cp, "quote": text[cp : cp + 12]}, "in_window": True, "kind": "note", "marker": "none"}

    ann = {
        "article": {"window": list(art.window)},
        "definitions": [d("{{sfn"), d("<ref")],
        "uses": [],
        "identifiers": [],
    }
    (tmp_path / "a.json").write_text(json.dumps(ann))
    spec = {
        "splits": {
            "holdout": [
                {"bundle": str(path), "extraction": str(tmp_path / "x.json"), "locked": str(tmp_path / "a.json")}
            ]
        }
    }
    got = dv2.items(spec)["holdout"][0]["items"]
    assert [i["kind"] for i in got if i["kind"].startswith("definition")] == []
    # and the retained v1 reading would have listed the two repeats
    v1_items = dv2.d1.article_items(path, tmp_path / "a.json", tmp_path / "x.json")["items"]
    assert sum(i["kind"] == "definition_extra" for i in v1_items) == 2
