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
  never counts as shown; a term found only there makes the region ambiguous, never "no warning", since what a
  reader saw is not evaluated;
* matching folds case and, for Arabic, ignores harakat and tatweel; English terms must stand as words, Arabic terms
  may carry attached letters (the article and prepositions are written joined).
"""

from __future__ import annotations

import re
import unicodedata
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
_ARABIC_MARKS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_SNIPPET = 48
# Letters an Arabic warning word may carry and still be that word: conjunction, preposition and article written
# joined (و ف / ب ل ك / ال, with ل + ال written لل), and the feminine ending. Any other attached letters make a
# different word (مسحوبات "withdrawals"), so such a match is only ambiguous.
_AR_PREFIXES = frozenset(
    c + p + a for c in ("", "و", "ف") for p in ("", "ب", "ل", "ك") for a in ("", "ال") if not (p == "ل" and a)
) | frozenset(c + "لل" for c in ("", "و", "ف"))
_AR_SUFFIXES = frozenset(("", "ة"))
_OPEN_QUOTES = {"“": "”", "«": "»", "„": "“"}
# A warning term right after a negation ("not retracted", "غير مسحوب") says the opposite of a warning.
_NEGATIONS = frozenset(("not", "never", "no", "isn't", "wasn't", "hasn't", "غير", "ليس", "ليست", "لم", "لا", "ما"))


def _drop(ch: str) -> bool:
    return bool(_ARABIC_MARKS.match(ch)) or unicodedata.category(ch) == "Cf"


def fold_map(text: str) -> tuple[str, list[int]]:
    """Matching form and, for each folded character, the index of the original character it came from.

    Arabic harakat, Quranic marks, tatweel and format characters (ZWNJ, ZWJ, bidi marks, soft hyphen) are removed;
    each remaining character is NFKC-normalized (Arabic presentation forms, ligatures) and case folded, which may
    expand it (ß -> ss), so offsets are mapped character by character. Evidence keeps the original text."""
    out: list[str] = []
    origin: list[int] = []
    for i, ch in enumerate(text):
        if _drop(ch):
            continue
        for piece in unicodedata.normalize("NFKC", ch).casefold():
            if not _drop(piece):
                out.append(piece)
                origin.append(i)
    return "".join(out), origin


def fold(text: str) -> str:
    return fold_map(text)[0]


def _is_arabic(term: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in term)


def term_pattern(term: str) -> re.Pattern[str]:
    folded = re.escape(fold(term))
    if _is_arabic(term):
        return re.compile(folded)
    return re.compile(rf"(?<![^\W_]){folded}(?![^\W_])")


def _in_quotes(text: str, pos: int) -> bool:
    """Whether ``pos`` lies inside a quoted span of ``text`` (a title written in quotation marks)."""
    before = text[:pos]
    if before.count('"') % 2 == 1:
        return True
    return any(before.rfind(open_q) > before.rfind(close_q) for open_q, close_q in _OPEN_QUOTES.items())


def _exclusion(term: str, folded: str, start: int, end: int, text: str, s: int, e: int) -> str | None:
    """Why a warning-term match is not a statement about the cited work, or None. Such a match is kept as
    ambiguous evidence: a title prefix ("RETRACTED: ..."), a quoted title, or an Arabic word with other letters."""
    if _is_arabic(term):
        ws = start
        while ws > 0 and folded[ws - 1].isalpha():
            ws -= 1
        we = end
        while we < len(folded) and folded[we].isalpha():
            we += 1
        if folded[ws:start] not in _AR_PREFIXES or folded[end:we] not in _AR_SUFFIXES:
            return "attached_letters"
    if text[e:].lstrip(" \u00a0").startswith((":", "：")):
        return "title_prefix"
    before = fold(text[:s]).replace("’", "'").split()
    if before and (before[-1] in _NEGATIONS or (len(before) > 1 and before[-2] in _NEGATIONS and before[-1] == "been")):
        return "negated"
    if _in_quotes(text, s):
        return "quoted"
    return None


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
    folded, origin = fold_map(text)
    for term in terms:
        for m in term_pattern(term).finditer(folded):
            if m.end() <= m.start():
                continue
            s = origin[m.start()]
            e = origin[m.end() - 1] + 1
            item = {
                "term": term,
                "kind": kind,
                "part": part,
                "matched": text[s:e],
                "snippet": text[max(0, s - _SNIPPET) : e + _SNIPPET],
            }
            if kind == "warning":
                reason = _exclusion(term, folded, m.start(), m.end(), text, s, e)
                if reason is not None:
                    item["kind"] = "ambiguous"
                    item["exclusion"] = reason
            out.append(item)
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
    warning_owners: list[Any] = []
    if render is not None:
        omitted_regions = {t.in_note or t.in_list_item for t in render.transclusions if t.omitted}
    if reader is not None:
        # Every parser-limit warning, also one whose owner element carries no ``about``.
        for w in reader.limit_warnings:
            owner = reader.element_by_path(w["path"]) if w.get("path") else None
            if owner is not None:
                warning_owners.append(owner)
    marker_templates = [t for t in model.templates.values() if t.kind == "marker"]
    for c in model.containers:
        source_markers = []
        def_refs = set(c.def_refs)
        for t in marker_templates:
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
            els = [reader.element_by_path(notes[region_id].locator.path)]
        elif region_id.startswith("about:"):
            # A standalone template's output is a group of sibling elements sharing one ``about`` (CS1 output starts
            # with an empty <link> to its styles): every element of the group is inspected.
            els = reader.about_group(region_id[6:])
        else:
            els = [reader.element_by_path(region_id)]
        els = [e for e in els if e is not None]
        if not els:
            out.append(
                MarkerObservation(
                    c.id, "not_inspected", "rendered region not found", None, source_marker_templates=source_markers
                )
            )
            continue
        texts = [reader.region_text(e) for e in els]
        region = {
            "text": " ".join(t["text"] for t in texts if t["text"]),
            "cite_text": " ".join(t["cite_text"] for t in texts if t["cite_text"]),
            "hidden_text": " ".join(t["hidden_text"] for t in texts if t["hidden_text"]),
            "redlinks": [r for t in texts for r in t["redlinks"]],
            "hidden_redlinks": [r for t in texts for r in t["hidden_redlinks"]],
            "hidden_elements": sum(t["hidden_elements"] for t in texts),
        }
        locator = reader.locator(els[0]).to_json()
        found = _find(wiki.warning_terms, region["text"], "text", "warning")
        evidence = [x for x in found if x["kind"] == "warning"]
        cite_warn = _find(wiki.warning_terms, region["cite_text"], "cite_text", "warning")
        for x in cite_warn:
            x["kind"] = "ambiguous"
        ambiguous = (
            [x for x in found if x["kind"] == "ambiguous"]
            + _find(wiki.ambiguous_terms, region["text"], "text", "ambiguous")
            + _find(wiki.ambiguous_terms, region["cite_text"], "cite_text", "ambiguous")
        )
        hidden = _find(wiki.warning_terms + wiki.ambiguous_terms, region["hidden_text"], "hidden_text", "hidden")
        for x in hidden:
            x["kind"] = "hidden"

        def is_marker(title: str) -> bool:
            return wiki.canonical_template(title) in wiki.markers or title in wiki.marker_render_titles

        redlinks = [t for t in region["redlinks"] if is_marker(t)]
        hidden += [
            {"kind": "hidden", "part": "hidden_redlink", "matched": t}
            for t in region["hidden_redlinks"]
            if is_marker(t)
        ]
        all_evidence = (
            evidence
            + cite_warn
            + ambiguous
            + hidden
            + [{"kind": "missing_template_link", "part": "redlink", "matched": t} for t in redlinks]
        )
        region_json = {"region_id": region_id, "locator": locator, "hidden_elements": region["hidden_elements"]}
        limited = region_id in omitted_regions or any(
            reader.contains(e, w) or reader.contains(w, e) for e in els for w in warning_owners
        )
        empty = not (region["text"] or region["cite_text"] or region["hidden_text"] or region["redlinks"])
        if evidence:
            state, reason = "recognized_warning_text", "a warning term in the region's visible text"
        elif cite_warn or ambiguous or hidden:
            state, reason = (
                "ambiguous_text",
                "only ambiguous wording, a warning term inside the citation itself, in a title prefix or quotation, "
                "with other attached letters, or in text the HTML hides",
            )
        elif limited:
            state, reason = "not_inspected", "MediaWiki omitted a template in or around this region (parser limit)"
        elif redlinks:
            state, reason = "missing_template_link_only", "a link to a marker template that does not exist"
        elif empty:
            state, reason = "not_inspected", "the rendered region has no text"
        elif c.id in rec.doubtful_regions:
            state, reason = "not_inspected", "the region's backlinks do not include every matched use"
        else:
            state, reason = "no_recognized_warning_in_inspected_region", "no profile term in the inspected text"
        out.append(MarkerObservation(c.id, state, reason, region_json, all_evidence, source_markers))
    return out
