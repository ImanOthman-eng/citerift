"""What the render shows a template inside a reference to be (SPECIFICATION.md 11.3, citation-unit classes; D-035).

A template the profile does not list can still format a citation or link to one. Two marks in the template's own
Parsoid output say so, the same in every wiki that uses the shared citation modules:

* ``citation_markup``: a ``<cite>`` element with the class ``citation``, which Module:Citation/CS1 (CS1 and CS2
  citations) writes around every citation it formats;
* ``short_citation_link``: a link to a ``#CITEREF…`` anchor, the anchor Module:Footnotes and the CS1 module give
  a full citation so that Harvard-style short citations (``harv``, ``harvnb``, ``harvp`` and their Arabic forms)
  can point to it. The short citation itself formats no work.

Anything else is ``no_citation_markup``. A template without a single-template transclusion of its own in the
render, or whose transclusions disagree, gets no entry: what it is cannot be established from the render.

The evidence is read for the templates that can decide a unit, called inside a ref and not inside another template
of that ref: templates the profile does not classify (kind ``other``), and templates that are citation templates only
by the name rule for unlisted families (RF-37: "Cite …", "استشهاد ب…"). Outside refs it is read for unclassified
templates called at the top level that hold an identifier, which can make a bibliography entry. A name is not
semantics: the Arabic Harvard template ``استشهاد بهارفارد دون أقواس`` matches the name rule and renders a
short-citation link. A source template and a render transclusion are paired by their canonical target and
parameters, the key reconciliation uses; equal keys expand to the same output, so the pairing does not depend on
document order.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from citerift.wiki.model import (
    CITATION_MARKUP,
    NO_CITATION_MARKUP,
    SHORT_CITATION_LINK,
    SourceModel,
    build,
    is_literal_magic_word,
    outermost_in_ref,
)
from citerift.wiki.profile import Profile, WikiProfile
from citerift.wiki.reconcile import Reconciliation, TemplateKey, reconcile, render_template_key, source_template_key
from citerift.wiki.render import RenderDoc, RenderReader
from citerift.wiki.source import SourceScan, TemplateRecord
from citerift.wiki.textmap import ByteMap


def deciding_templates(scan: SourceScan) -> list[TemplateRecord]:
    """Templates whose render decides a unit: inside a ref, the unclassified and RF-37 templates called outside any
    other template of that ref; outside refs, the unclassified templates called at the top level that hold an
    identifier occurrence (they can make a bibliography entry)."""
    templates = {t.index: t for t in scan.templates}
    holding = {f.template for c in scan.candidates if c.ref is None for f in c.frames}
    return [
        t
        for t in scan.templates
        if not t.excluded
        and not is_literal_magic_word(t)
        and (
            (_decides_in_ref(t) and outermost_in_ref(t, templates))
            or (t.kind == "other" and t.ref is None and t.parent_template is None and t.index in holding)
        )
    ]


def _decides_in_ref(t: TemplateRecord) -> bool:
    return (t.kind == "other" and not is_literal_magic_word(t)) or (t.kind == "citation" and t.family == "unlisted")


def output_evidence(elements: list[Any]) -> str:
    """What one transclusion's output elements show (citation markup first: a citation may carry anchors)."""
    citeref = False
    for group in elements:
        for el in group.iter():
            if not isinstance(el.tag, str):
                continue
            if el.tag == "cite" and "citation" in (el.get("class") or "").split():
                return CITATION_MARKUP
            if el.tag == "a":
                href = el.get("href") or ""
                if "#" in href and urllib.parse.unquote(href.split("#", 1)[1]).startswith("CITEREF"):
                    citeref = True
    return SHORT_CITATION_LINK if citeref else NO_CITATION_MARKUP


def template_evidence(
    scan: SourceScan, render: RenderDoc, reader: RenderReader, wiki: WikiProfile, text: str
) -> dict[int, str]:
    """Source template index -> render evidence, for the templates that can decide a unit; and, for an unclassified
    template nested in another template's arguments (which Parsoid renders inside the outer template's output),
    ``no_citation_markup`` when every transclusion of its own name elsewhere in the same render shows none. The
    nested evidence is read only to tell whether the outer template's citation markup can be its own (RV-1, review
    2 RV2-5)."""
    deciding = deciding_templates(scan)
    wanted: dict[TemplateKey, list[int]] = {}
    for t in deciding:
        wanted.setdefault(source_template_key(t, text, wiki), []).append(t.index)
    chosen = {t.index for t in deciding}
    nested: dict[str, list[int]] = {}
    for t in scan.templates:
        if t.kind == "other" and t.parent_template is not None and t.canonical and t.index not in chosen:
            nested.setdefault(source_template_key(t, text, wiki)[0], []).append(t.index)
    if not wanted and not nested:
        return {}
    seen: dict[TemplateKey, set[str]] = {}
    by_name: dict[str, set[str]] = {}
    for tr in render.transclusions:
        if tr.omitted or len(tr.templates) != 1:
            continue
        target, params = tr.templates[0]
        key = render_template_key(target, params, wiki)
        if key in wanted or key[0] in nested:
            value = output_evidence(reader.about_group(tr.about))
            if key in wanted:
                seen.setdefault(key, set()).add(value)
            if key[0] in nested:
                by_name.setdefault(key[0], set()).add(value)
    out: dict[int, str] = {}
    for name, values in by_name.items():
        if values == {NO_CITATION_MARKUP}:
            for index in nested[name]:
                out[index] = NO_CITATION_MARKUP
    for key, values in seen.items():
        if len(values) == 1:
            for index in wanted[key]:
                out[index] = next(iter(values))
    return out


def note_evidence(
    model: SourceModel,
    rec: Reconciliation,
    render: RenderDoc,
    reader: RenderReader,
    evidence: dict[int, str],
    wiki: WikiProfile,
    text: str,
) -> dict[int, str]:
    """Evidence for deciding templates that have no output of their own, read from the reference's rendered note
    (review 2, RV2-4). Parsoid renders the templates of a ref written inside another template (a reference list's
    ``refs=``, ``{{refn}}``, an infobox parameter) as part of that template, but the note shows the whole definition:

    * a note without citation markup or a short-citation link shows that none of these templates is either;
    * otherwise the note's evidence is attributed only to the definition's one template without evidence, and only
      when every other deciding template of the definition shows no citation markup of its own.

    Only templates without any transclusion of their own are read this way: a template whose transclusions disagree
    or were not expanded (parser limits) stays without evidence. Only a definition without a unit, in a container
    matched to exactly one note whose backlinks agree, whose definitions do not conflict and which holds no
    unexpanded template, is read."""
    present = {render_template_key(tg, p, wiki) for tr in render.transclusions for tg, p in tr.templates}
    unexpanded = {tr.in_note for tr in render.transclusions if tr.omitted}
    notes = {n.note_id: n for n in render.notes if n.note_id not in unexpanded}
    defined = {u.definition_id for u in model.units}
    own: dict[int, list[TemplateRecord]] = {}
    for t in model.templates.values():
        if t.ref is not None and not t.excluded and outermost_in_ref(t, model.templates) and _decides_in_ref(t):
            own.setdefault(t.ref, []).append(t)
    out: dict[int, str] = {}
    for c in model.containers:
        if c.kind == "bibliography_entry" or c.layout == "short_footnote":
            continue
        if c.binding_state == "conflicting_definitions" or c.id in rec.doubtful_regions:
            continue
        note = notes.get(rec.container_note.get(c.id, ""))
        if note is None:
            continue
        shown: str | None = None
        for i, ref_index in enumerate(c.def_refs):
            if f"{c.id}/d{i + 1}" in defined:
                continue
            ts = own.get(ref_index, [])
            unknown = [t for t in ts if t.index not in evidence]
            if any(source_template_key(t, text, wiki) in present for t in unknown):
                continue
            if not unknown or any(evidence[t.index] != NO_CITATION_MARKUP for t in ts if t.index in evidence):
                continue
            if shown is None:
                el = reader.element_by_path(note.locator.path)
                if el is None:
                    break
                shown = output_evidence([el])
            if shown == NO_CITATION_MARKUP:
                out.update(dict.fromkeys((t.index for t in unknown), NO_CITATION_MARKUP))
            elif len(unknown) == 1:
                out[unknown[0].index] = shown
    return out


def source_model(
    scan: SourceScan,
    wiki: WikiProfile,
    profile: Profile,
    bmap: ByteMap,
    render: RenderDoc | None,
    reader: RenderReader | None,
    text: str,
) -> tuple[SourceModel, Reconciliation | None]:
    """The source model with the render's evidence, and its reconciliation: the one path for extraction, replay and
    the marker reconstruction of verification (review 2, RV2-1). Note evidence needs the matched notes, so a model
    whose undecided definitions it settles is built and reconciled a second time; containers and notes do not
    depend on units, so the second reconciliation matches the same notes."""
    if render is None or reader is None:
        return build(scan, wiki, profile, bmap, None), None
    evidence = template_evidence(scan, render, reader, wiki, text)
    model = build(scan, wiki, profile, bmap, evidence)
    rec = reconcile(model, render, wiki, profile, text)
    more = note_evidence(model, rec, render, reader, evidence, wiki, text)
    if more:
        evidence = {**evidence, **more}
        model = build(scan, wiki, profile, bmap, evidence)
        rec = reconcile(model, render, wiki, profile, text)
    return model, rec
