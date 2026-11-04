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
import subprocess
import sys
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
    """What the synthetic template shows for a parameter value: plain text as is; ``{{val|x}}`` as ``x``;
    ``{{icon|x}}`` as nothing a reader can compare (an image)."""
    if wikitext.startswith("{{val|"):
        return wikitext[len("{{val|") : -2]
    if wikitext.startswith("{{icon|"):
        return '<span class="flagicon"><img alt="" src="./x.png"/></span>'
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
    values = ["{{icon|Germany}}", "{{icon|France}}", "{{icon|Spain}}"]
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
    values = [f"{{{{icon|c{i}}}}}" for i in range(n)]
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


@pytest.mark.negative
def test_r038_before_marker_text_is_stable_across_element_proxies() -> None:
    """lxml creates element proxies on demand; the before-marker text must not depend on which proxy ids happen to be
    reused (an id()-keyed ancestor set once cut ", Germany" from "Munich, Germany" at random)."""
    from citerift.wiki.render import read_render

    cell = '<a rel="mw:WikiLink" href="./Munich">Munich</a>, Germany' + marker(
        1, "cite_note-M-1", "cite_ref-M_1-0", "M", body="reuse"
    )
    filler = "".join(f"<p><span>x{i}</span><b>y</b></p>" for i in range(200))
    render, reader = read_render(parsoid(f"{filler}<table><tbody><tr><td>{cell}</td></tr></tbody></table>", "x"))
    el = reader.element_by_path(render.uses[0].locator.path)
    seen = set()
    for _ in range(300):
        _ = [len(list(p.iter())) for p in reader.doc.iter("p")]  # create and release many proxies
        seen.add(reader.preceding_text(el))
    assert seen == {"Munich, Germany"}


@pytest.mark.integration
def test_r038_text_on_both_sides_of_another_marker_is_not_one_word(tmp_path: Path) -> None:
    other = '<ref name="J">Other text.</ref>'
    values = ["6,391" + other + "13,000", "7.0"]
    order = [1, 0]
    params = [(f"p{i}", v + REUSE) for i, v in enumerate(values)]
    rows = [
        ("P1", "7.0" + marker(1, "cite_note-M-1", "cite_ref-M_1-1", "M", body="reuse")),
        (
            "P0",
            "6,391"
            + marker(2, "cite_note-J-2", "cite_ref-J_2-0", "J", body="id")
            + "13,000"
            + marker(1, "cite_note-M-1", "cite_ref-M_1-2", "M", body="reuse"),
        ),
    ]
    src, table = infobox("Infobox star", params, rows)
    text = src + "\nThe body.\n" + DEF + "\n"
    body = (
        table
        + "<p>The body."
        + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body="id")
        + "</p>"
        + references(
            [
                note_li("cite_note-M-1", ["cite_ref-M_1-0", "cite_ref-M_1-1", "cite_ref-M_1-2"], "Colors."),
                note_li("cite_note-J-2", ["cite_ref-J_2-0"], "Other text."),
            ]
        )
    )
    del order
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert got[reuse_at(text, "13,000")] == ("matched", "cite_ref-M_1-2")
    assert got[reuse_at(text, "7.0")] == ("matched", "cite_ref-M_1-1")


# Values written with templates: the numbers they show ------------------------------------------------------------


def shown(values: list[str], render_texts: list[str], order: list[int]) -> tuple[str, str]:
    """Like ``reuses``, but the template shows ``render_texts[i]`` for parameter ``i``."""
    params = [(f"p{i}", v + REUSE) for i, v in enumerate(values)]
    rows = [
        (f"P{i}", render_texts[i] + marker(1, "cite_note-M-1", f"cite_ref-M_1-{k + 1}", "M", body="reuse"))
        for k, i in enumerate(order)
    ]
    src, table = infobox("Infobox star", params, rows)
    text = src + "\nThe body.\n" + DEF + "\n"
    body = (
        table
        + "<p>The body."
        + marker(1, "cite_note-M-1", "cite_ref-M_1-0", "M", body="id")
        + "</p>"
        + references([note_li("cite_note-M-1", [f"cite_ref-M_1-{k}" for k in range(len(values) + 1)], "Colors.")])
    )
    return text, body


@pytest.mark.integration
def test_r038_template_values_pair_by_the_numbers_they_show(tmp_path: Path) -> None:
    values = ["{{val|9494|143}}", "{{val|3.94|0.09}}", "{{val|0.96|0.16}}", "2.0{{±|0.6}}"]
    texts = ["9,494±143", "3.94±0.09", "0.96±0.16", "2.0±0.6"]
    order = [1, 0, 3, 2]
    text, body = shown(values, texts, order)
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    for i, v in enumerate(values):
        assert got[reuse_at(text, v)] == ("matched", expected_marker(order, i)), v


@pytest.mark.negative
def test_r038_template_that_changes_its_numbers_gives_no_anchor(tmp_path: Path) -> None:
    values = ["{{val|1.2|0.4|e=3}}", "{{val|7.0|2.1}}"]
    texts = ["(1.2±0.4)×10<sup>3</sup>", "7.1±2.0"]  # neither shows its source numbers in order
    text, body = shown(values, texts, [1, 0])
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert [got[reuse_at(text, v)][0] for v in values] == ["abstained", "abstained"]


@pytest.mark.integration
def test_r038_short_value_anchors_only_a_whole_cell(tmp_path: Path) -> None:
    values = ["6", "{{val|7.0|2.1}}", "16"]
    texts = ["6", "7.0±2.1", "16"]
    order = [2, 1, 0]
    text, body = shown(values, texts, order)
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    for i, v in enumerate(values):
        assert got[reuse_at(text, v)] == ("matched", expected_marker(order, i)), v


@pytest.mark.negative
def test_r038_equal_numbers_in_two_parameters_are_ambiguous(tmp_path: Path) -> None:
    values = ["{{val|0.5|0.1}}", "{{val|0.5|0.1|u=K}}"]
    texts = ["0.5±0.1", "0.5±0.1 K"]
    text, body = shown(values, texts, [1, 0])
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert [got[reuse_at(text, v)][0] for v in values] == ["abstained", "abstained"]


@pytest.mark.integration
def test_r038_real_english_infobox_borisov2023_labelled_swap() -> None:
    """en-1378959744 (D-034 challenge split, where render links were labelled but not scored): the locked and
    adjudicated labels attach the uses at cp 2175 and 2233 to ``…_11-1`` and ``…_11-0``; the old engine had them
    the other way round. Values are ``{{val}}`` templates."""
    got = by_cp(real("confirmation-2026-11/campaign/capture/bundles/challenge/en-70970708-a2"), "Borisov2023")
    assert got[2175] == ("matched", "cite_ref-Borisov2023_11-1")
    assert got[2233] == ("matched", "cite_ref-Borisov2023_11-0")
    assert got[2291] == ("matched", "cite_ref-Borisov2023_11-2")
    assert got[2482] == ("matched", "cite_ref-Borisov2023_11-3")


@pytest.mark.negative
def test_r038_a_one_or_two_digit_number_is_too_weak_to_anchor(tmp_path: Path) -> None:
    """Found by the template-order simulation (``simulations/stage03/template_order_sim.py``, adversarial mode): a
    template that changes its small argument (``{{double|2}}`` shows 4) while another parameter's template shows
    exactly that argument (a data template showing 2). The number 2 then points to the other parameter's marker and
    elimination gives the rest: a swap. A number support needs at least three digits in all."""
    values = ["{{double|2}}", "{{data|k}}"]
    texts = ["4", "2"]
    text, body = shown(values, texts, [1, 0])
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    assert [got[reuse_at(text, v)][0] for v in values] == ["abstained", "abstained"]


@pytest.mark.simulation
def test_r038_template_order_simulation_has_no_swap_or_wrong_attachment() -> None:
    """``simulations/stage03/template_order_sim.py``: random parameter orders, clean and adversarial values, with
    and without a marker's data-mw. No use may take another use's marker (swap) or another reference's (wrong)."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "simulations" / "stage03" / "template_order_sim.py"), "40", "20261104"],
        capture_output=True,
        text=True,
        check=True,
        timeout=600,
    )
    summary = json.loads(proc.stdout)
    assert summary["failure_count"] == 0
    totals = summary["totals"]
    assert all(t["swap"] == 0 and t["wrong"] == 0 for t in totals.values())
    assert totals["clean/none"]["linked"] > totals["clean/none"]["abstain"] > 0


@pytest.mark.negative
def test_r038_before_marker_budget_counts_every_child() -> None:
    """Review B-2: the node budget of the before-marker walk must count every child it iterates, markers and hidden
    elements included, so a block that holds many markers is "too large" (no anchor) instead of costing a walk over
    all of them for every marker."""
    from citerift.wiki.render import read_render

    sups = "".join(marker(1, "cite_note-M-1", f"cite_ref-M_1-{k}", "M", body="reuse") for k in range(30))
    render, reader = read_render(parsoid(f"<p>text {sups} end{sups}</p>", "x"))
    last = reader.element_by_path(render.uses[-1].locator.path)
    assert reader.preceding_text(last, max_nodes=10) is None
    assert reader.preceding_text(last) == "text end"


@pytest.mark.regression
def test_r038_before_marker_texts_of_one_block_are_collected_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review B-2: the texts before all the markers of one block come from one walk of that block, and each equals the
    text a walk to that marker alone gives."""
    from citerift.wiki import render as render_module

    sups = [marker(1, "cite_note-M-1", f"cite_ref-M_1-{k}", "M", body="reuse") for k in range(50)]
    body = "<p>" + "".join(f"item {k} " + s for k, s in enumerate(sups)) + "</p><p>other " + sups[0] + "</p>"
    render, reader = render_module.read_render(parsoid(body, "x"))
    calls: list[object] = []
    original = render_module.RenderReader._collect_prefixes

    def counting(self: object, block: object, max_nodes: int) -> object:
        calls.append(block)
        return original(self, block, max_nodes)  # type: ignore[arg-type]

    monkeypatch.setattr(render_module.RenderReader, "_collect_prefixes", counting)
    els = [reader.element_by_path(u.locator.path) for u in render.uses]
    texts = [reader.preceding_text(el) for el in els]
    assert len(calls) == 2  # two paragraphs
    assert texts[:3] == ["item 0", "item 0 item 1", "item 0 item 1 item 2"]
    p = els[0].getparent()
    assert all(texts[k] == reader._walk_to(p, els[k], 20_000) for k in range(50))


def no_wrong_link(text: str, doc: dict[str, Any], values: list[str], order: list[int]) -> list[str]:
    """Each value's use is either attached to its own marker or abstained; returns the states."""
    got = pairs(doc, "M")
    states = []
    for i, v in enumerate(values):
        state, marker_id = got[reuse_at(text, v)]
        assert state == "abstained" or marker_id == expected_marker(order, i), (v, state, marker_id)
        states.append(state)
    return states


@pytest.mark.negative
@pytest.mark.parametrize(
    ("values", "texts"),
    [
        # review A-01 S1: the template groups the digits of one value; another value shows them ungrouped
        (["12345", "{{val|12345}}"], ["12,345", "12345"]),
        # review A-01 S1b: the other value is read from a data source, so its source text cannot be read
        (["12345", "{{Wikidata|P1082}}"], ["12,345", "12345"]),
        # the template adds a unit after one value
        (["12345", "{{Wikidata|P1082}}"], ["12,345 km", "12345"]),
        # review B-1: a short value shown with a qualifier, beside a template value showing the same digit
        (["{{val|6}}", "6"], ["6", "c. 6"]),
    ],
)
def test_r038_a_restyled_value_never_takes_another_values_marker(
    tmp_path: Path, values: list[str], texts: list[str]
) -> None:
    """Reviews A-01 and B-1: when a template restyles one value (digit groups, a unit, a qualifier) and another
    marker of the same name shows that value's source text, the support of the restyled value must still hold its own
    marker. Otherwise elimination gives both uses each other's markers. Here the evidence cannot decide, so both
    abstain."""
    order = [0, 1]
    text, body = shown(values, texts, order)
    states = no_wrong_link(text, extract(bundle(tmp_path, text, body)), values, order)
    assert states == ["abstained", "abstained"]


@pytest.mark.integration
def test_r038_grouped_digits_and_case_still_anchor(tmp_path: Path) -> None:
    """Folding keeps coverage: a value shown with digit groups or another case still pairs when nothing else
    matches it. (A third value shown only as an icon used to be settled by elimination; since re-review R-02 a
    marker that no value explains blocks the name, see the test below.)"""
    values = ["12345", "Kaiser Wilhelm Society"]
    texts = ["12,345", "KAISER WILHELM SOCIETY"]
    order = [1, 0]
    text, body = shown(values, texts, order)
    got = pairs(extract(bundle(tmp_path, text, body)), "M")
    for i, v in enumerate(values):
        assert got[reuse_at(text, v)] == ("matched", expected_marker(order, i)), v


# Review findings on the R-038 correction (A-02 to A-07). Each case is a SYNTHETIC Parsoid document built after the
# reviewer's reproduction.


def multipart(parts: list[tuple[str, dict[str, str]] | str], inner: str, tag: str = "table", n: int = 7) -> str:
    """One Parsoid transclusion element for several top-level source templates (a multi-part transclusion, as
    ``{{Election box begin}} ... {{Election box end}}`` or ``{{div col}} ... {{div col end}}`` render)."""
    out: list[object] = []
    for i, p in enumerate(parts):
        if isinstance(p, str):
            out.append(p)
        else:
            target, params = p
            out.append(
                {"template": {"target": {"wt": target}, "params": {k: {"wt": v} for k, v in params.items()}, "i": i}}
            )
    dm = html.escape(json.dumps({"parts": out}, ensure_ascii=False), quote=True)
    return f'<{tag} about="#mwt{n}" typeof="mw:Transclusion" data-mw="{dm}">{inner}</{tag}>'


def located(doc: dict[str, Any]) -> dict[int, tuple[str, str | None]]:
    return {
        u["source"]["cp_start"]: (u["render"]["state"], (u["render"].get("locator") or {}).get("element_id"))
        for u in doc["uses"]
    }


def election(candidates: list[tuple[str, str]], rows: list[tuple[str, str]]) -> tuple[str, str]:
    """``candidates``: (party, votes wikitext) in source order; ``rows``: (party, cell HTML) in render order."""
    src = "Intro.\n{{Election box begin|title=Election}}\n"
    src += "".join(f"{{{{Election box candidate|party={p}|votes={v}}}}}\n" for p, v in candidates)
    src += "{{Election box end}}\n"
    parts: list[tuple[str, dict[str, str]] | str] = [("Election box begin", {"title": "Election"}), "\n"]
    for p, v in candidates:
        parts += [("Election box candidate", {"party": p, "votes": v}), "\n"]
    parts.append(("Election box end", {}))
    inner = "<tbody>" + "".join(f"<tr><td>{p}</td><td>{cell}</td></tr>" for p, cell in rows) + "</tbody>"
    return src, "<p>Intro.</p>" + multipart(parts, inner)


@pytest.mark.negative
@pytest.mark.parametrize("second_shown", [True, False])
def test_r038_templates_of_one_transclusion_never_claim_one_marker_twice(tmp_path: Path, second_shown: bool) -> None:
    """Review A-02: several source templates rendered as one transclusion share its markers. They are reconciled as
    one group, so no marker is paired with two uses and no use takes a marker its template does not show."""
    rows = [("A", "100" + marker(1, "cite_note-1", "cite_ref-1"))]
    notes = [note_li("cite_note-1", ["cite_ref-1"], "Official result A")]
    if second_shown:
        rows.append(("B", "200" + marker(2, "cite_note-2", "cite_ref-2")))
        notes.append(note_li("cite_note-2", ["cite_ref-2"], "Official result B"))
    else:
        rows.append(("B", "200"))
    src, body = election([("A", "100<ref>Official result A</ref>"), ("B", "200<ref>Official result B</ref>")], rows)
    doc = extract(bundle(tmp_path, src, body + references(notes)))
    truth = {src.index("<ref>Official result A"): "cite_ref-1", src.index("<ref>Official result B"): "cite_ref-2"}
    got = located(doc)
    claimed = [m for state, m in got.values() if state == "matched"]
    assert len(claimed) == len(set(claimed))
    for cp, want in truth.items():
        state, marker_id = got[cp]
        assert state != "matched" or marker_id == want, (cp, state, marker_id)


@pytest.mark.integration
def test_r038_a_name_reused_across_templates_of_one_transclusion_pairs_by_evidence(tmp_path: Path) -> None:
    """Review A-02: a reference defined in one part and reused in another part of one transclusion is paired by role
    and anchors across the parts, whatever order the rows are rendered in."""
    rows = [
        ("B", "2000" + marker(1, "cite_note-r-1", "cite_ref-r_1-1", "r", body="reuse")),
        ("A", "1000" + marker(1, "cite_note-r-1", "cite_ref-r_1-0", "r")),
    ]
    src, body = election([("A", '1000<ref name="r">Official result</ref>'), ("B", '2000<ref name="r"/>')], rows)
    note = note_li("cite_note-r-1", ["cite_ref-r_1-0", "cite_ref-r_1-1"], "Official result")
    got = located(extract(bundle(tmp_path, src, body + references([note]))))
    assert got[src.index('<ref name="r">')] == ("matched", "cite_ref-r_1-0")
    assert got[src.index('<ref name="r"/>')] == ("matched", "cite_ref-r_1-1")


@pytest.mark.regression
def test_r038_nested_uses_of_one_name_pair_by_evidence_not_order(tmp_path: Path) -> None:
    """Review A-05: two uses of one name inside a citation template inside a reference. The template renders its
    parameters in its own order (author before title), so the k-th use is not the k-th marker."""
    src = (
        'Claim.<ref name="X">{{cite book |title=Title{{r|a}} |author=Author{{r|a}}}}</ref>'
        ' Other.<ref name="a">Def A</ref>\n'
    )
    note_x = note_li(
        "cite_note-X-1",
        ["cite_ref-X_1-0"],
        '<cite class="citation book cs1">Author'
        + marker(2, "cite_note-a-2", "cite_ref-a_2-1", "a", body="empty_html")
        + ". <i>Title"
        + marker(2, "cite_note-a-2", "cite_ref-a_2-2", "a", body="empty_html")
        + "</i>.</cite>",
    )
    note_a = note_li("cite_note-a-2", ["cite_ref-a_2-0", "cite_ref-a_2-1", "cite_ref-a_2-2"], "Def A")
    body = (
        "<p>Claim."
        + marker(1, "cite_note-X-1", "cite_ref-X_1-0", "X")
        + " Other."
        + marker(2, "cite_note-a-2", "cite_ref-a_2-0", "a")
        + "</p>"
        + references([note_x, note_a])
    )
    got = located(extract(bundle(tmp_path, src, body)))
    for at, want in (("Title{{r|a}}", "cite_ref-a_2-2"), ("Author{{r|a}}", "cite_ref-a_2-1")):
        state, marker_id = got[src.index(at) + at.index("{{")]
        assert state != "matched" or marker_id == want, (at, state, marker_id)
        assert state == "matched"


@pytest.mark.negative
def test_r038_a_count_only_pair_in_template_output_needs_agreeing_text(tmp_path: Path) -> None:
    """Review A-04: a template that does not show the parameter holding a source reference, and shows a reference of
    its own (here imported from a data source), is not paired by count alone when the texts disagree (the source
    reference stands after 500, the marker after 480). The container is then not matched to another reference's note,
    and no negative marker observation is made over that note."""
    src, box = infobox(
        "Infobox town",
        [("name", "X"), ("populaton", "500<ref>Smith 2001, p. 5. Retracted.</ref>")],
        [("Name", "X"), ("Population", "480" + marker(1, "cite_note-1", "cite_ref-1"))],
    )
    note = note_li(
        "cite_note-1", ["cite_ref-1"], 'Imported from a data source: <a href="https://stats.example.org/x">S</a>'
    )
    doc = extract(bundle(tmp_path, "Intro.\n" + src + "\n", "<p>Intro.</p>" + box + references([note])))
    assert [u["render"]["state"] for u in doc["uses"]] == ["abstained"]
    assert [c["render"]["state"] for c in doc["containers"]] == ["unmatched"]
    assert all(m["state"] != "no_recognized_warning_in_inspected_region" for m in doc["markers"])


def bibliography(entries: list[tuple[str, str | None, str]]) -> tuple[str, str]:
    """``entries``: (title, DOI or None, trailing source wikitext) in a ``{{div col}}`` list; the render is one
    multi-part transclusion whose first element is the column ``div``."""
    src = "Intro.\n== Further reading ==\n{{div col}}\n"
    parts: list[tuple[str, dict[str, str]] | str] = [("div col", {})]
    items = ""
    for title, doi, tail in entries:
        params = {"title": title} | ({"doi": doi} if doi else {})
        src += "* {{cite journal |" + " |".join(f"{k}={v}" for k, v in params.items()) + "}}" + tail + "\n"
        parts += ["\n* ", ("cite journal", params)]
        if tail:
            parts += [" ", ("Retracted", {})]
        link = doi_link(doi) if doi else ""
        shown_tail = " <b>Retracted article</b>" if tail else ""
        items += f'<li><cite class="citation journal cs1">"{title}". {link}</cite>{shown_tail}</li>'
    src += "{{div col end}}\n"
    parts += ["\n", ("div col end", {})]
    body = "<p>Intro.</p><h2>Further reading</h2>" + multipart(parts, f"<ul>{items}</ul>", tag="div")
    return src, body


@pytest.mark.regression
def test_r038_bibliography_entries_of_one_list_template_get_their_own_items(tmp_path: Path) -> None:
    """Review A-03: entries inside one multi-part list transclusion do not share the whole list as their region; each
    is matched to the list item that holds its own identifier link, so one entry's retraction text is not reported
    for another entry."""
    src, body = bibliography([("Alpha study", "10.1000/a", ""), ("Beta study", "10.1000/b", " {{Retracted}}")])
    doc = extract(bundle(tmp_path, src, body))
    regions = [c["render"]["region_id"] for c in doc["containers"]]
    assert len(set(regions)) == 2 and all(r and r.endswith(("li[1]", "li[2]")) for r in regions)
    states = {m["container_id"]: m["state"] for m in doc["markers"]}
    first, second = (c["id"] for c in doc["containers"])
    assert states[first] == "no_recognized_warning_in_inspected_region"
    assert states[second] == "recognized_warning_text"


@pytest.mark.negative
def test_r038_bibliography_entries_without_their_own_item_are_ambiguous(tmp_path: Path) -> None:
    """Review A-03: when the shared list region cannot be split (no entry has a link of its own), no entry is given
    the whole list: each is reported ambiguous and no marker observation is made over another entry's text."""
    src, body = bibliography([("Alpha study", None, ""), ("Beta study", None, " {{Retracted}}")])
    doc = extract(bundle(tmp_path, src, body))
    assert [c["render"]["state"] for c in doc["containers"]] == ["note_ambiguous", "note_ambiguous"]
    assert "RENDER_NOTE_AMBIGUOUS" in codes(doc)
    assert all(
        m["state"] not in ("recognized_warning_text", "no_recognized_warning_in_inspected_region")
        for m in doc["markers"]
    )


@pytest.mark.regression
def test_r038_an_abstention_issue_names_only_uses_that_end_abstained(tmp_path: Path) -> None:
    """Review A-07: a use found ``source_only`` (no rendered counterpart is left) is not named by a
    ``RECONCILIATION_ABSTAINED`` issue."""
    src, box = infobox(
        "Infobox town",
        [("name", "X"), ("populaton", "500<ref>Smith 2001.</ref>")],
        [("Name", "X")],
    )
    doc = extract(bundle(tmp_path, "Intro.\n" + src + "\n", "<p>Intro.</p>" + box))
    states = {u["id"]: u["render"]["state"] for u in doc["uses"]}
    assert list(states.values()) == ["source_only"]
    for issue in doc["issues"]:
        if issue["code"] == "RECONCILIATION_ABSTAINED":
            assert all(states.get(e) == "abstained" for e in issue["entities"]), issue


# Focused re-review (R-01, R-02, R-04).


@pytest.mark.negative
@pytest.mark.parametrize(
    ("values", "texts"),
    [
        # R-02: a value shown in a form the folding does not cover, and the partner shows the value's source text
        (["5%", "{{Wikidata|P2}}"], ["5 %", "5%"]),
        # R-02: a value the template replaces by another one
        (["Kaiser Wilhelm Society", "{{Wikidata|P1}}"], ["Max Planck Society", "Kaiser Wilhelm Society"]),
        # R-02: a value the template hides (shows only an icon)
        (
            ["Kaiser Wilhelm Society", "{{Wikidata|P1}}"],
            ['<span class="flagicon"><img alt="" src="./x.png"/></span>', "Kaiser Wilhelm Society"],
        ),
    ],
)
def test_r038_a_marker_no_value_explains_blocks_the_whole_name(
    tmp_path: Path, values: list[str], texts: list[str]
) -> None:
    """Re-review R-02: a marker whose text supports no use means some value is not shown as written, so an anchor of
    another use may point to the wrong marker (the safety condition of MATHEMATICAL_MODEL.md fails). The class is
    then not settled at all: no elimination and no anchor pair."""
    order = [0, 1]
    text, body = shown(values, texts, order)
    states = no_wrong_link(text, extract(bundle(tmp_path, text, body)), values, order)
    assert states == ["abstained", "abstained"]


@pytest.mark.negative
def test_r038_a_named_template_use_is_not_paired_by_count_with_a_disagreeing_marker(tmp_path: Path) -> None:
    """Re-review R-01: a named use made by a template (``{{r|census}}``) and an anonymous marker that the template emits
    itself are not paired by count alone when the texts disagree (500 against 480)."""
    src = (
        'Intro.<ref name="census">Census 2001.</ref>\n{{Infobox town\n| name = X\n| population = 500{{r|census}}\n}}\n'
    )
    part = {
        "target": {"wt": "Infobox town"},
        "params": {"name": {"wt": "X"}, "population": {"wt": "500{{r|census}}"}},
        "i": 0,
    }
    dm = html.escape(json.dumps({"parts": [{"template": part}]}), quote=True)
    box = (
        f'<table about="#mwt5" typeof="mw:Transclusion" data-mw="{dm}"><tbody><tr><th>Name</th><td>X</td></tr>'
        f"<tr><th>Population</th><td>480{marker(2, 'cite_note-2', 'cite_ref-2')}</td></tr></tbody></table>"
    )
    notes = [
        note_li("cite_note-census-1", ["cite_ref-census_1-0"], "Census 2001."),
        note_li("cite_note-2", ["cite_ref-2"], "Imported from a data source"),
    ]
    body = "<p>Intro." + marker(1, "cite_note-census-1", "cite_ref-census_1-0", "census") + "</p>" + box
    doc = extract(bundle(tmp_path, src, body + references(notes)))
    got = located(doc)
    assert got[src.index("{{r|census}}")][1] != "cite_ref-2"


@pytest.mark.regression
def test_r038_the_word_index_never_drops_a_support() -> None:
    """Re-review R-04: the index of before-marker words must find every marker that ``anchor_supports`` accepts (an
    underscore is a word character for ``\\w`` but not for the whole-word rule)."""
    from citerift.wiki.reconcile import _support_sets, anchor_supports

    for anchor, rendered in ((("Alpha", False), "Alpha_1"), (("x_y", False), "a x_y"), (("12345", False), "n_12345")):
        want = {0} if anchor_supports(anchor, rendered) else set()
        assert _support_sets([anchor], [None], [rendered], [()]) == [want], (anchor, rendered)
