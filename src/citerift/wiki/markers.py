"""Marker observations: what the captured render shows near a reference, read as text (SPECIFICATION.md 13).

A marker observation describes one reference container's rendered region. It never says whether a work is retracted:
it says whether the captured HTML of that region contains text the profile lists as retraction-warning wording,
only ambiguous wording, only a link to a missing marker template, or none of these. Visibility in a browser is never
evaluated (``browser_visibility`` is always ``not_evaluated``): CSS, scripts, skins and gadgets are not applied.

Text rules (all in the profile, nothing guessed):

* the region is the reference list item (or bibliography list item) matched to the container, without its
  backlinks, styles and scripts;
* text inside ``<cite>`` (the citation's own title and fields) is kept apart: a warning term there is ambiguous,
  since a cited work's title may itself contain it;
* text the HTML itself hides (``display:none``, the ``hidden`` attribute, CS1 maintenance classes) is kept apart and
  never counts as shown;
* matching folds case and, for Arabic, ignores harakat and tatweel; English terms must stand as words, Arabic terms
  may carry attached letters (the article and prepositions are written joined).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from citerift.wiki.model import SourceModel
from citerift.wiki.profile import WikiProfile
from citerift.wiki.reconcile import Reconciliation
from citerift.wiki.render import RenderDoc, RenderReader

STATES = (
    "recognized_warning_text",
    "ambiguous_text",
    "missing_template_link_only",
    "no_recognized_warning_in_inspected_region",
    "not_inspected",
    "unavailable",
)
_ARABIC_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_SNIPPET = 48


def fold(text: str) -> str:
    """Matching form: Arabic harakat, Quranic marks and tatweel removed, then case folded. Used for matching only;
    evidence keeps the original text."""
    return _ARABIC_MARKS.sub("", text).casefold()


def _is_arabic(term: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in term)


def term_pattern(term: str) -> re.Pattern[str]:
    folded = re.escape(fold(term))
    if _is_arabic(term):
        return re.compile(folded)
    return re.compile(rf"(?<![^\W_]){folded}(?![^\W_])")


@dataclass
class MarkerObservation:
    container_id: str
    state: str
    reason: str
    region: dict[str, Any] | None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    source_marker_templates: list[dict[str, Any]] = field(default_factory=list)
    browser_visibility: str = "not_evaluated"

    def to_json(self) -> dict[str, Any]:
        return {
            "container_id": self.container_id,
            "state": self.state,
            "reason": self.reason,
            "region": self.region,
            "evidence": self.evidence,
            "source_marker_templates": self.source_marker_templates,
            "browser_visibility": self.browser_visibility,
        }


def _find(terms: tuple[str, ...], text: str, part: str, kind: str) -> list[dict[str, Any]]:
    out = []
    folded = fold(text)
    # Folding only removes characters; map folded offsets back to the original for the snippet.
    keep = [i for i, ch in enumerate(text) if not _ARABIC_MARKS.match(ch)]
    for term in terms:
        for m in term_pattern(term).finditer(folded):
            s = keep[m.start()] if m.start() < len(keep) else len(text)
            e = keep[m.end() - 1] + 1 if m.end() - 1 < len(keep) else len(text)
            out.append(
                {
                    "term": term,
                    "kind": kind,
                    "part": part,
                    "matched": text[s:e],
                    "snippet": text[max(0, s - _SNIPPET) : e + _SNIPPET],
                }
            )
    return out


def observe(
    model: SourceModel,
    rec: Reconciliation | None,
    render: RenderDoc | None,
    reader: RenderReader | None,
    wiki: WikiProfile,
    render_state: str,
) -> list[MarkerObservation]:
    out: list[MarkerObservation] = []
    notes = {n.note_id: n for n in render.notes} if render else {}
    omitted_regions = set()
    if render is not None:
        omitted_regions = {t.in_note or t.in_list_item for t in render.transclusions if t.omitted}
    for c in model.containers:
        source_markers = []
        def_refs = set(c.def_refs)
        for t in model.templates.values():
            if t.kind != "marker":
                continue
            inside = (
                t.ref in def_refs if c.kind != "bibliography_entry" else (t.ref is None and c.start <= t.start < c.end)
            )
            if inside:
                source_markers.append({"template": t.canonical, "cp_start": t.start, "cp_end": t.end})
        if render is None or reader is None or rec is None:
            out.append(
                MarkerObservation(
                    c.id, "unavailable", f"render {render_state}", None, source_marker_templates=source_markers
                )
            )
            continue
        region_id = rec.container_note.get(c.id)
        if region_id is None:
            out.append(
                MarkerObservation(
                    c.id,
                    "not_inspected",
                    "container not matched to a rendered region",
                    None,
                    source_marker_templates=source_markers,
                )
            )
            continue
        if region_id in notes:
            el = reader.element_by_path(notes[region_id].locator.path)
        elif region_id.startswith("about:"):
            el = None
            about = region_id[6:]
            tr = next((t for t in render.transclusions if t.about == about), None)
            if tr is not None:
                el = reader.element_by_path(tr.locator.path)
        else:
            el = reader.element_by_path(region_id)
        if el is None:
            out.append(
                MarkerObservation(
                    c.id, "not_inspected", "rendered region not found", None, source_marker_templates=source_markers
                )
            )
            continue
        region = reader.region_text(el)
        locator = reader.locator(el).to_json()
        evidence = _find(wiki.warning_terms, region["text"], "text", "warning")
        cite_warn = _find(wiki.warning_terms, region["cite_text"], "cite_text", "warning")
        ambiguous = _find(wiki.ambiguous_terms, region["text"], "text", "ambiguous") + _find(
            wiki.ambiguous_terms, region["cite_text"], "cite_text", "ambiguous"
        )
        hidden = _find(wiki.warning_terms + wiki.ambiguous_terms, region["hidden_text"], "hidden_text", "hidden")
        redlinks = [
            t
            for t in region["redlinks"]
            if wiki.canonical_template(t) in wiki.markers or t in wiki.marker_render_titles
        ]
        all_evidence = (
            evidence
            + cite_warn
            + ambiguous
            + hidden
            + [{"kind": "missing_template_link", "part": "redlink", "matched": t} for t in redlinks]
        )
        region_json = {"region_id": region_id, "locator": locator, "hidden_elements": region["hidden_elements"]}
        if evidence:
            state, reason = "recognized_warning_text", "a warning term in the region's visible text"
        elif cite_warn or ambiguous:
            state, reason = "ambiguous_text", "only ambiguous wording, or a warning term inside the citation itself"
        elif region_id in omitted_regions:
            state, reason = "not_inspected", "MediaWiki omitted a template in this region (parser limit)"
        elif redlinks:
            state, reason = "missing_template_link_only", "a link to a marker template that does not exist"
        else:
            state, reason = "no_recognized_warning_in_inspected_region", "no profile term in the inspected text"
        out.append(MarkerObservation(c.id, state, reason, region_json, all_evidence, source_markers))
    return out
