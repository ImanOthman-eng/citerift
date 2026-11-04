"""R-038 (D-036): repeated reference names inside one template's output are paired by evidence, never by source order.

A template renders its parameters in its own order (an infobox can show the U-B row before the B-V row), so the
source order of two uses of one reference name says nothing about which rendered marker is which. The render gives
two kinds of evidence: Parsoid's ``data-mw`` ``body`` marks the marker that carries the reference's text (the
definition), and the visible text just before a marker in its table cell, list item or paragraph can be compared with
the parameter text just before the ``<ref>`` in the source. Where the evidence does not settle a pairing, the uses are
abstained (``RECONCILIATION_ABSTAINED``) and no marker is attached.

The synthetic cases are SYNTHETIC Parsoid documents. The real-bundle cases are post-exposure regressions: the three
articles were captured and scored (or reviewed) in earlier campaigns before this correction.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, capture, codes, doi_link, extract, note_li, parsoid, references

from citerift.wiki.extract import ExtractConfig, extract_bundle

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "docs/verification/stage-03/evaluation"

_ABOUT = [100]


def marker(
    n: int,
    note: str,
    ref_id: str,
    name: str | None = None,
    group: str | None = None,
    body: str | None = "id",
) -> str:
    """A Parsoid reference marker. ``body``: ``"id"`` (the definition: data-mw names the note text), ``"reuse"`` (no
    body), ``"empty_html"`` (an empty inline body, as for an empty reuse), ``"other_id"`` (a body naming another note's
    text), ``"no_data_mw"`` (no data-mw attribute) or ``"bad_json"`` (an unreadable one)."""
    attrs: dict[str, str] = {}
    if name is not None:
        attrs["name"] = name
    if group is not None:
        attrs["group"] = group
    dm: dict[str, Any] = {"name": "ref", "attrs": attrs}
    if body == "id":
        dm["body"] = {"id": f"mw-reference-text-{note}"}
    elif body == "empty_html":
        dm["body"] = {"html": ""}
    elif body == "other_id":
        dm["body"] = {"id": "mw-reference-text-cite_note-elsewhere-99"}
    if body == "no_data_mw":
        data = ""
    elif body == "bad_json":
        data = ' data-mw="{bad json"'
    else:
        data = f' data-mw="{html.escape(json.dumps(dm, ensure_ascii=False), quote=True)}"'
    _ABOUT[0] += 1
    label = f"{group} {n}" if group else str(n)
    return (
        f'<sup about="#mwr{_ABOUT[0]}" class="mw-ref reference" id="{ref_id}" rel="dc:references" '
        f'typeof="mw:Extension/ref"{data}><a href="./SYNTHETIC#{note}"><span class="mw-reflink-text">'
        f'<span class="cite-bracket">[</span>{label}<span class="cite-bracket">]</span></span></a></sup>'
    )


def infobox(target: str, params: list[tuple[str, str]], rows: list[tuple[str, str]], n: int = 5) -> tuple[str, str]:
    """A source template call with ``params`` (name, wikitext value, in source order) and its Parsoid render: a table
    whose ``rows`` (label, cell HTML) are in the order the template shows them."""
    src = "{{" + target + "\n" + "".join(f"| {k} = {v}\n" for k, v in params) + "}}"
    part = {"target": {"wt": target}, "params": {k: {"wt": v} for k, v in params}, "i": 0}
    dm = html.escape(json.dumps({"parts": [{"template": part}]}, ensure_ascii=False), quote=True)
    body = "".join(f"<tr><th>{label}</th><td>{cell}</td></tr>" for label, cell in rows)
    return src, f'<table about="#mwt{n}" typeof="mw:Transclusion" data-mw="{dm}"><tbody>{body}</tbody></table>'


def pairs(doc: dict[str, Any], name: str | None = None) -> dict[int, tuple[str, str | None]]:
    """Source position of each use (of ``name``) -> (render state, matched marker id)."""
    out = {}
    for u in doc["uses"]:
        if name is not None and u["name"] != name:
            continue
        loc = u["render"].get("locator") or {}
        out[u["source"]["cp_start"]] = (u["render"]["state"], loc.get("element_id"))
    return out


def no_marker_used_twice(doc: dict[str, Any]) -> None:
    paths = [u["render"]["locator"]["path"] for u in doc["uses"] if u["render"]["state"] == "matched"]
    assert len(paths) == len(set(paths))


def cp(text: str, needle: str, nth: int = 0) -> int:
    at = -1
    for _ in range(nth + 1):
        at = text.index(needle, at + 1)
    return at


def reuse_at(text: str, value: str, nth: int = 0) -> int:
    """Source position of the reuse that follows ``value`` in a parameter."""
    return cp(text, value + REUSE, nth) + len(value)


DEF = '<ref name="M">{{cite journal |title=Colors |doi=10.1000/m}}</ref>'
REUSE = '<ref name="M" />'
NOTE_M = note_li(
    "cite_note-M-1",
    ["cite_ref-M_1-0", "cite_ref-M_1-1"],
    '<cite class="citation journal cs1">Colors. ' + doi_link("10.1000/m") + "</cite>",
)


def star(order: str, *, def_body: str = "id", reuse_body: str = "reuse", wiki: str = "en") -> tuple[str, str]:
    """B-V holds the definition and U-B the reuse in the source; ``order`` is the render's row order."""
    src, table = infobox(
        "Infobox star",
        [("b-v", "+1.31" + DEF), ("u-b", "+1.45" + REUSE)],
        [
            ("U−B", "+1.45" + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body=reuse_body)),
            ("B−V", "+1.31" + marker(1, "cite_note-M-1", "cite_ref-M_1-1", "M", body=def_body)),
        ]
        if order == "reuse_first"
        else [
            ("B−V", "+1.31" + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body=def_body)),
            ("U−B", "+1.45" + marker(1, "cite_note-M-1", "cite_ref-M_1-1", "M", body=reuse_body)),
        ],
    )
    return src + "\nThe star.\n", table + "<p>The star.</p>" + references([NOTE_M])


# Reordered infobox parameters; reuse rendered before its definition -------------------------------------------


@pytest.mark.integration
def test_r038_reuse_rendered_before_definition_pairs_by_body(tmp_path: Path) -> None:
    text, body = star("reuse_first")
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert got[cp(text, DEF)] == ("matched", "cite_ref-M_1-1"), "the definition is the marker whose data-mw has a body"
    assert got[cp(text, REUSE)] == ("matched", "cite_ref-M_1-0")
    no_marker_used_twice(doc)


@pytest.mark.integration
def test_r038_definition_followed_by_reuse_in_source_order(tmp_path: Path) -> None:
    text, body = star("source_order")
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert got[cp(text, DEF)] == ("matched", "cite_ref-M_1-0")
    assert got[cp(text, REUSE)] == ("matched", "cite_ref-M_1-1")
    assert doc["containers"][0]["render"]["state"] == "matched"


@pytest.mark.integration
def test_r038_empty_inline_body_is_a_reuse(tmp_path: Path) -> None:
    text, body = star("reuse_first", reuse_body="empty_html")
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert got[cp(text, DEF)] == ("matched", "cite_ref-M_1-1")
    assert got[cp(text, REUSE)] == ("matched", "cite_ref-M_1-0")


# Missing, contradictory and malformed data-mw ------------------------------------------------------------------


@pytest.mark.negative
@pytest.mark.parametrize("bad", ["no_data_mw", "bad_json"])
def test_r038_missing_or_unreadable_data_mw_abstains(tmp_path: Path, bad: str) -> None:
    text, body = star("reuse_first", def_body=bad)
    doc = extract(bundle(tmp_path, text, body))
    assert {s for s, _ in pairs(doc, "M").values()} == {"abstained"}
    assert "RECONCILIATION_ABSTAINED" in codes(doc)


@pytest.mark.negative
@pytest.mark.parametrize("bodies", [("id", "id"), ("reuse", "reuse"), ("other_id", "reuse")])
def test_r038_contradictory_data_mw_abstains(tmp_path: Path, bodies: tuple[str, str]) -> None:
    """Two bodies, no body, or a body naming another note's text: the definition marker is not established."""
    text, body = star("reuse_first", def_body=bodies[0], reuse_body=bodies[1])
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert got[cp(text, DEF)][0] == "abstained" and got[cp(text, REUSE)][0] == "abstained"
    assert "RECONCILIATION_ABSTAINED" in codes(doc)


@pytest.mark.negative
def test_r038_duplicate_marker_ids_never_attach_wrongly(tmp_path: Path) -> None:
    text, body = star("reuse_first")
    body = body.replace('id="cite_ref-M_1-1"', 'id="cite_ref-M_1-0"')
    doc = extract(bundle(tmp_path, text, body))
    assert "DOM_ID_DUPLICATE" in codes(doc)
    rows = {u["source"]["cp_start"]: u["render"] for u in doc["uses"]}
    d, r = rows[cp(text, DEF)], rows[cp(text, REUSE)]
    if d["state"] == "matched":
        assert d["locator"]["path"].endswith("tr[2]/td/sup"), "the definition is in the second rendered row"
    if r["state"] == "matched":
        assert r["locator"]["path"].endswith("tr[1]/td/sup")
    no_marker_used_twice(doc)


@pytest.mark.negative
def test_r038_render_of_another_revision_attaches_nothing(tmp_path: Path) -> None:
    text, body = star("reuse_first")
    html_bytes = parsoid(body, text, revision=999)
    outcome = capture(tmp_path / "b", text, html_bytes)
    if outcome.bundle is None:  # the capture itself refuses the mismatched render: nothing can be attached
        assert outcome.issues
        return
    doc = extract(outcome.bundle)
    assert all(u["render"]["state"] != "matched" for u in doc["uses"])


# Several reuses: local text anchors, elimination, ambiguity ------------------------------------------------------


def reuses(values: list[str], render_order: list[int], *, definition_in_prose: bool = True) -> tuple[str, str]:
    """A reference defined in article text and reused once per infobox parameter ``p{i}`` (value ``values[i]``);
    the infobox shows the parameters in ``render_order``. Marker ids follow the render order, as Cite numbers them."""
    params = [(f"p{i}", v + REUSE) for i, v in enumerate(values)]
    rows = []
    for k, i in enumerate(render_order):
        rows.append(
            (f"P{i}", html_value(values[i]) + marker(1, "cite_note-M-1", f"cite_ref-M_1-{k + 1}", "M", body="reuse"))
        )
    src, table = infobox("Infobox organization", params, rows)
    text = src + "\nThe body.\n" + DEF + "\n"
    note = note_li(
        "cite_note-M-1",
        [f"cite_ref-M_1-{k}" for k in range(len(values) + 1)],
        '<cite class="citation journal cs1">Colors. ' + doi_link("10.1000/m") + "</cite>",
    )
    body = (
        table
        + "<p>The body."
        + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body="id")
        + "</p>"
        + references([note])
    )
    return text, body


def html_value(wikitext: str) -> str:
    """What the synthetic template shows for a parameter value (plain text as is; {{val|x}} as ``x``)."""
    if wikitext.startswith("{{val|"):
        return wikitext[len("{{val|") : -2]
    return wikitext


def expected_marker(render_order: list[int], i: int) -> str:
    return f"cite_ref-M_1-{render_order.index(i) + 1}"


@pytest.mark.integration
def test_r038_multiple_reuses_reordered_pair_by_text_anchor(tmp_path: Path) -> None:
    values = ["1.65", "3.13", "12.9", "6,187", "3.66"]
    order = [0, 1, 2, 4, 3]
    text, body = reuses(values, order)
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    for i, v in enumerate(values):
        assert got[reuse_at(text, v)] == ("matched", expected_marker(order, i)), v
    no_marker_used_twice(doc)


@pytest.mark.integration
def test_r038_one_unanchored_reuse_is_settled_by_elimination(tmp_path: Path) -> None:
    values = ["Kaiser Wilhelm Society", "{{val|1911}}", "Non-profit research organization", "Munich, Germany"]
    order = [2, 0, 3, 1]
    text, body = reuses(values, order)
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    for i, v in enumerate(values):
        assert got[reuse_at(text, v)] == ("matched", expected_marker(order, i)), v


@pytest.mark.negative
def test_r038_unanchored_reuses_abstain(tmp_path: Path) -> None:
    values = ["{{val|0.403}}", "{{val|0.406}}", "{{val|0.0210}}"]
    order = [2, 1, 0]
    text, body = reuses(values, order)
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    for v in values:
        assert got[reuse_at(text, v)][0] == "abstained", v
    assert "RECONCILIATION_ABSTAINED" in codes(doc)
    assert got[cp(text, DEF)] == ("matched", "cite_ref-M_1-0"), "the prose definition is unaffected"


@pytest.mark.negative
def test_r038_identical_anchors_are_ambiguous(tmp_path: Path) -> None:
    text, body = reuses(["2020", "2020"], [1, 0])
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert [got[reuse_at(text, "2020", k)][0] for k in (0, 1)] == ["abstained", "abstained"]
    assert "RECONCILIATION_ABSTAINED" in codes(doc)


@pytest.mark.integration
def test_r038_distinct_anchors_with_a_shared_ending_settle(tmp_path: Path) -> None:
    order = [1, 0]
    text, body = reuses(["Founded 2020", "Opened 2020"], order)
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert got[reuse_at(text, "Founded 2020")] == ("matched", expected_marker(order, 0))
    assert got[reuse_at(text, "Opened 2020")] == ("matched", expected_marker(order, 1))


@pytest.mark.negative
def test_r038_a_number_inside_a_longer_number_is_not_an_anchor(tmp_path: Path) -> None:
    text, body = reuses(["1.31", "11.31"], [1, 0])
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    # "11.31" ends with "1.31": the shorter value supports both markers, so only elimination by the longer one could
    # settle it; the pairing must be the true one or none.
    for i, v in enumerate(["1.31", "11.31"]):
        state, mid = got[reuse_at(text, v)]
        assert state == "abstained" or mid == expected_marker([1, 0], i), v


# Groups, anonymous references, nested templates, generated markers -----------------------------------------------


@pytest.mark.integration
def test_r038_same_name_in_two_groups_and_reordered_group(tmp_path: Path) -> None:
    gdef, greuse = '<ref group="n" name="M">Group note text.</ref>', '<ref group="n" name="M" />'
    src, table = infobox(
        "Infobox star",
        [("a", "Alpha" + gdef), ("b", "Beta" + DEF), ("c", "Gamma" + greuse)],
        [
            ("C", "Gamma" + marker(1, "cite_note-n-M-1", "cite_ref-n-M_1-0", "M", group="n", body="reuse")),
            ("B", "Beta" + marker(1, "cite_note-M-2", "cite_ref-M_2-0", "M", body="id")),
            ("A", "Alpha" + marker(1, "cite_note-n-M-1", "cite_ref-n-M_1-1", "M", group="n", body="id")),
        ],
    )
    body = (
        table
        + references([note_li("cite_note-n-M-1", ["cite_ref-n-M_1-0", "cite_ref-n-M_1-1"], "Group note text.")], "n")
        + references([note_li("cite_note-M-2", ["cite_ref-M_2-0"], "Colors. " + doi_link("10.1000/m"))])
    )
    doc = extract(bundle(tmp_path, src + "\n", body))
    got = pairs(doc)
    assert got[cp(src, gdef)] == ("matched", "cite_ref-n-M_1-1")
    assert got[cp(src, greuse)] == ("matched", "cite_ref-n-M_1-0")
    assert got[cp(src, DEF)] == ("matched", "cite_ref-M_2-0")


@pytest.mark.negative
def test_r038_two_anonymous_references_in_template_output_abstain(tmp_path: Path) -> None:
    src, table = infobox(
        "Infobox star",
        [("a", "Alpha<ref>First text.</ref>"), ("b", "Beta<ref>Second text.</ref>")],
        [
            ("B", "Beta" + marker(2, "cite_note-2", "cite_ref-2", body="id")),
            ("A", "Alpha" + marker(1, "cite_note-1", "cite_ref-1", body="id")),
        ],
    )
    body = table + references(
        [note_li("cite_note-1", ["cite_ref-1"], "First text."), note_li("cite_note-2", ["cite_ref-2"], "Second text.")]
    )
    doc = extract(bundle(tmp_path, src + "\n", body))
    assert {s for s, _ in pairs(doc).values()} == {"abstained"}


@pytest.mark.integration
def test_r038_nested_template_parameters_reordered(tmp_path: Path) -> None:
    d = '<ref name="M">Nested text.</ref>'
    src, table = infobox(
        "Infobox star",
        [("b-v", "{{nowrap|+1.31" + d + "}}"), ("u-b", "{{nowrap|+1.45" + REUSE + "}}")],
        [
            (
                "U−B",
                '<span class="nowrap">+1.45'
                + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body="reuse")
                + "</span>",
            ),
            (
                "B−V",
                '<span class="nowrap">+1.31' + marker(1, "cite_note-M-1", "cite_ref-M_1-1", "M", body="id") + "</span>",
            ),
        ],
    )
    body = table + references([note_li("cite_note-M-1", ["cite_ref-M_1-0", "cite_ref-M_1-1"], "Nested text.")])
    got = pairs(extract(bundle(tmp_path, src + "\n", body)), "M")
    assert got[cp(src, d)] == ("matched", "cite_ref-M_1-1")
    assert got[cp(src, REUSE)] == ("matched", "cite_ref-M_1-0")


# Arabic and English -------------------------------------------------------------------------------------------------


@pytest.mark.integration
def test_r038_arabic_infobox_reordered(tmp_path: Path) -> None:
    d = '<ref name="مالاما">مرجع عن ألوان النجوم https://example.org/colors</ref>'
    r = '<ref name="مالاما" />'
    src, table = infobox(
        "معلومات نجم",
        [("ب-ف", "+1.31 (B−V)" + d), ("ف-ب", "+1.45 قدر" + r)],
        [
            ("U−B", "+1.45 قدر" + marker(1, "cite_note-مالاما-1", "cite_ref-مالاما_1-0", "مالاما", body="reuse")),
            ("B−V", "+1.31 (B−V)" + marker(1, "cite_note-مالاما-1", "cite_ref-مالاما_1-1", "مالاما", body="id")),
        ],
    )
    note = note_li(
        "cite_note-مالاما-1",
        ["cite_ref-مالاما_1-0", "cite_ref-مالاما_1-1"],
        'مرجع عن ألوان النجوم <a rel="mw:ExtLink" href="https://example.org/colors">https://example.org/colors</a>',
    )
    got = pairs(extract(bundle(tmp_path, src + "\nنص.\n", table + "<p>نص.</p>" + references([note]), wiki="ar")))
    assert got[cp(src, d)] == ("matched", "cite_ref-مالاما_1-1")
    assert got[cp(src, r)] == ("matched", "cite_ref-مالاما_1-0")


# Large and pathological templates --------------------------------------------------------------------------------


@pytest.mark.integration
def test_r038_large_reversed_template_with_anchors(tmp_path: Path) -> None:
    n = 150
    values = [f"row {i} value" for i in range(n)]
    order = list(reversed(range(n)))
    text, body = reuses(values, order)
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert all(got[reuse_at(text, v)] == ("matched", expected_marker(order, i)) for i, v in enumerate(values))
    no_marker_used_twice(doc)


@pytest.mark.negative
def test_r038_large_template_without_anchors_abstains(tmp_path: Path) -> None:
    n = 300
    values = [f"{{{{val|{i}}}}}" for i in range(n)]
    order = list(reversed(range(n)))
    text, body = reuses(values, order)
    doc = extract(bundle(tmp_path, text, body))
    got = pairs(doc, "M")
    assert sum(1 for s, _ in got.values() if s == "abstained") == n
    no_marker_used_twice(doc)


# Real bundles (post-exposure regressions) ----------------------------------------------------------------------------


def real(rel: str) -> dict[str, Any]:
    return extract_bundle(EVAL / rel, ExtractConfig(), isolated=False)


def by_cp(doc: dict[str, Any], name: str) -> dict[int, tuple[str, str | None]]:
    return pairs(doc, name)


@pytest.mark.integration
def test_r038_real_arabic_infobox_mallama2014() -> None:
    """ar-76814232 (D-035 holdout, the G6b failure): B-V holds the definition (cp 1897), U-B the reuse (cp 2467); the
    infobox renders U-B first. The locked and adjudicated label pairs the definition with ``…_4-1``."""
    got = by_cp(real("confirmation-d035/campaign/capture/bundles/holdout/ar-10469946-a1"), "Mallama2014")
    assert got[1897] == ("matched", "cite_ref-Mallama2014_4-1")
    assert got[2467] == ("matched", "cite_ref-Mallama2014_4-0")


@pytest.mark.integration
def test_r038_real_english_infobox_chryssides_2001() -> None:
    """en-1371940951 (D-034 reserve; these uses were not in the labelled sample): "movement" holds the definition,
    "field" the reuse; the infobox shows "Known for" (field) before "Movement"."""
    got = by_cp(real("confirmation-2026-11/campaign/capture/bundles/reserve1/en-186224-a1"), "Chryssides 2001")
    assert got[926] == ("matched", "cite_ref-Chryssides_2001_1-1")
    assert got[1069] == ("matched", "cite_ref-Chryssides_2001_1-0")


@pytest.mark.integration
def test_r038_real_english_infobox_ayres2023_reuses() -> None:
    """en-1381005609 (run-1 reserve; not labelled): five reuses; the template shows 3.66 before 6,187."""
    got = by_cp(real("capture/bundles/reserve/en-2695828-a1"), "ayres2023")
    assert got[1950] == ("matched", "cite_ref-ayres2023_12-0")
    assert got[1992] == ("matched", "cite_ref-ayres2023_12-1")
    assert got[2034] == ("matched", "cite_ref-ayres2023_12-2")
    assert got[2077] == ("matched", "cite_ref-ayres2023_12-4"), "6,187"
    assert got[2119] == ("matched", "cite_ref-ayres2023_12-3"), "3.66"
