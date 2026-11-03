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

from citerift.wiki.model import CITATION_MARKUP, NO_CITATION_MARKUP, SHORT_CITATION_LINK, outermost_in_ref
from citerift.wiki.profile import WikiProfile
from citerift.wiki.reconcile import TemplateKey, render_template_key, source_template_key
from citerift.wiki.render import RenderDoc, RenderReader
from citerift.wiki.source import SourceScan, TemplateRecord


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
        and (
            (_decides_in_ref(t) and outermost_in_ref(t, templates))
            or (t.kind == "other" and t.ref is None and t.parent_template is None and t.index in holding)
        )
    ]


def _decides_in_ref(t: TemplateRecord) -> bool:
    return t.kind == "other" or (t.kind == "citation" and t.family == "unlisted")


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
    """Source template index -> render evidence, for the templates that can decide a unit."""
    wanted: dict[TemplateKey, list[int]] = {}
    for t in deciding_templates(scan):
        wanted.setdefault(source_template_key(t, text, wiki), []).append(t.index)
    if not wanted:
        return {}
    seen: dict[TemplateKey, set[str]] = {}
    for tr in render.transclusions:
        if tr.omitted or len(tr.templates) != 1:
            continue
        target, params = tr.templates[0]
        key = render_template_key(target, params, wiki)
        if key in wanted:
            seen.setdefault(key, set()).add(output_evidence(reader.about_group(tr.about)))
    out: dict[int, str] = {}
    for key, values in seen.items():
        if len(values) == 1:
            for index in wanted[key]:
                out[index] = next(iter(values))
    return out
