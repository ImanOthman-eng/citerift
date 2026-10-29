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

import bisect
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from citerift.wiki.model import SourceModel
from citerift.wiki.profile import WikiProfile
from citerift.wiki.reconcile import Reconciliation
from citerift.wiki.render import HARD, RenderDoc, RenderReader, TextChannel

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


def _quoted(text: str, positions: list[int]) -> dict[int, bool]:
    """For each position, whether it lies inside a quoted span of ``text`` (a title written in quotation marks): an
    odd number of straight double quotes before it, or a typographic opening quote after its last closing quote.
    One pass over the text for all positions."""
    out: dict[int, bool] = {}
    straight = 0
    last = {q: -1 for pair in _OPEN_QUOTES.items() for q in pair}
    i = 0
    for pos in sorted(set(positions)):
        while i < pos:
            c = text[i]
            if c == '"':
                straight += 1
            elif c in last:
                last[c] = i
            i += 1
        out[pos] = straight % 2 == 1 or any(last[o] > last[c] for o, c in _OPEN_QUOTES.items())
    return out


_CONTEXT = 64  # characters read before a match for a negation (the last two words)
_ATTACHED_MAX = 6  # letters read on each side of an Arabic match; more means another word


def _exclusion(term: str, folded: str, start: int, end: int, text: str, s: int, e: int, quoted: bool) -> str | None:
    """Why a warning-term match is not a statement about the cited work, or None. Such a match is kept as
    ambiguous evidence: a title prefix ("RETRACTED: ..."), a negation, a quoted title, or an Arabic word with other
    letters. Only a bounded neighbourhood of the match is read."""
    if _is_arabic(term):
        ws = start
        while ws > 0 and start - ws <= _ATTACHED_MAX and folded[ws - 1].isalpha():
            ws -= 1
        we = end
        while we < len(folded) and we - end <= _ATTACHED_MAX and folded[we].isalpha():
            we += 1
        if folded[ws:start] not in _AR_PREFIXES or folded[end:we] not in _AR_SUFFIXES:
            return "attached_letters"
    if text[e : e + 16].lstrip(" \u00a0").startswith((":", "：")):
        return "title_prefix"
    window = max(0, s - _CONTEXT)
    before = fold(text[window:s]).replace("’", "'").split()
    if window > 0 and before:
        before = before[1:]  # the first word may be cut by the window
    if before and (before[-1] in _NEGATIONS or (len(before) > 1 and before[-2] in _NEGATIONS and before[-1] == "been")):
        return "negated"
    if quoted:
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


def _variants(ch: TextChannel, text: str) -> list[tuple[str, list[int]]]:
    """The channel's text with its soft boundaries joined, and with them separated by a space; each with the index
    of the channel character behind every text character (-1 for an inserted space)."""
    joined = (text, list(range(len(text))))
    if not ch.soft:
        return [joined]
    chars: list[str] = []
    index: list[int] = []
    for i, c in enumerate(text):
        if i in ch.soft:
            chars.append(" ")
            index.append(-1)
        chars.append(c)
        index.append(i)
    return [joined, ("".join(chars), index)]


def _find(terms: tuple[str, ...], ch: TextChannel, kind: str) -> list[dict[str, Any]]:
    """Every term match in a channel, as evidence items with the internal ``_span`` (channel character indices).

    A match must be found, at the same characters, both with the soft boundaries joined and with them separated; it
    must not cross a soft boundary or an edge, nor start or end at an edge. Otherwise it is ambiguous
    (``interrupted``): content of another kind lies inside it or beside it, and how a reader saw the text is not
    evaluated. The cost is linear in the text and in the number of matches."""
    text = ch.text
    variants = _variants(ch, text)
    soft = sorted(ch.soft)
    edges = sorted(ch.edges)
    found: dict[tuple[str, int, int], dict[str, Any]] = {}
    seen_in: dict[tuple[str, int, int], int] = {}
    for vtext, index in variants:  # the separated variant comes last: its item (and exclusion context) is kept
        folded, origin = fold_map(vtext)
        hits: list[tuple[str, int, int, int, int]] = []
        for term in terms:
            for m in term_pattern(term).finditer(folded):
                if m.end() > m.start():
                    hits.append((term, m.start(), m.end(), origin[m.start()], origin[m.end() - 1] + 1))
        quoted = _quoted(vtext, [h[3] for h in hits]) if kind == "warning" else {}
        for term, fs, fe, s, e in hits:
            cs, ce = index[s], index[e - 1] + 1
            if cs < 0 or ce <= 0:
                continue
            key = (term, cs, ce)
            seen_in[key] = seen_in.get(key, 0) + 1
            item: dict[str, Any] = {
                "term": term,
                "kind": kind,
                "matched": text[cs:ce],
                "snippet": text[max(0, cs - _SNIPPET) : ce + _SNIPPET].replace(HARD, "\n"),
                "_span": (cs, ce),
            }
            if kind == "warning":
                reason = _exclusion(term, folded, fs, fe, vtext, s, e, quoted[s])
                if reason is not None:
                    item["kind"] = "ambiguous"
                    item["exclusion"] = reason
            found[key] = item
    for key, item in found.items():
        cs, ce = key[1], key[2]
        crosses = bisect.bisect_right(soft, cs) < bisect.bisect_left(soft, ce)
        touches = bisect.bisect_left(edges, cs) < bisect.bisect_right(edges, ce)
        if item["kind"] == "warning" and (crosses or touches or seen_in[key] < len(variants)):
            item["kind"] = "ambiguous"
            item["exclusion"] = "interrupted"
    return [found[k] for k in sorted(found, key=lambda k: (k[1], k[2], k[0]))]


def marker_target(title: str, wiki: WikiProfile) -> bool:
    """Whether a link target is the page of a marker template: a title in the template namespace (the canonical
    "Template:" or the wiki's own name for it) whose template name is one of the profile's marker templates. A link
    to any other page, red or not, is ordinary text."""
    name = re.sub(r"[_\s]+", " ", title).strip()
    ns, sep, rest = name.partition(":")
    if not sep:
        return False
    local = {t.split(":", 1)[0].casefold() for t in wiki.marker_render_titles if ":" in t}
    if ns.strip().casefold() not in local | {"template"}:
        return False
    return wiki.canonical_template(rest) in wiki.markers


def _line_continues(last: Any) -> bool:
    """Whether letters or digits follow a template's output on its rendered line: the tail of its last element and
    the following siblings in the same block, up to a line break."""
    pieces = [last.tail or ""]
    for sib in last.itersiblings():
        if isinstance(sib.tag, str) and sib.tag in ("br", "p", "div", "ul", "ol", "dl", "table", "li"):
            break
        if isinstance(sib.tag, str) and sib.tag not in ("style", "script", "link", "meta"):
            pieces.append(sib.text_content())
        pieces.append(sib.tail or "")
    line = "".join(pieces).split("\n", 1)[0]
    return any(ch.isalnum() for ch in line)


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
        region = reader.region_text(els, lambda title: marker_target(title, wiki))
        shown, hidden_ch = region.channels["shown"], region.channels["hidden"]
        locator = reader.locator(els[0]).to_json()

        def placed(
            items: list[dict[str, Any]], ch: TextChannel, hidden_part: bool, els: list[Any] = els
        ) -> list[dict[str, Any]]:
            """Give each item its channel part, element locator, link and hiding basis. A term inside the citation's
            own text, or spanning its boundary, is only ambiguous: a cited title may contain it."""
            for x in items:
                cs, ce = x.pop("_span")
                if hidden_part:
                    x["part"] = "hidden_text"
                else:
                    labels = set(ch.label[cs:ce])
                    x["part"] = "text" if labels == {"text"} else "cite_text"
                    if labels != {"text"} and x["kind"] == "warning":
                        x["kind"] = "ambiguous"
                        if labels != {"cite"}:
                            x["exclusion"] = "spans_citation"
                owners = [o for o in ch.origin[cs:ce] if o is not None]
                owner = reader.common_ancestor(owners) if owners else els[0]
                x["locator"] = reader.locator(owner).to_json()
                link = reader.enclosing_link(owner, els)
                if link is not None:
                    x["link"] = link
                if hidden_part and ch.basis[cs] is not None:
                    x["hidden_basis"] = ch.basis[cs]
            return items

        found = placed(_find(wiki.warning_terms, shown, "warning"), shown, False)
        evidence = [x for x in found if x["kind"] == "warning"]
        cite_warn = [x for x in found if x["kind"] == "ambiguous" and x["part"] == "cite_text"]
        ambiguous = [x for x in found if x["kind"] == "ambiguous" and x["part"] == "text"]
        ambiguous += placed(_find(wiki.ambiguous_terms, shown, "ambiguous"), shown, False)
        hidden = placed(_find(wiki.warning_terms + wiki.ambiguous_terms, hidden_ch, "hidden"), hidden_ch, True)
        for x in hidden:
            x["kind"] = "hidden"
            x.pop("exclusion", None)
        redlinks = []
        for ln in region.marker_links:
            item = {
                "kind": "missing_template_link" if ln.red else "ambiguous",
                "part": "redlink" if ln.red else "template_link",
                "matched": ln.label,
                "target": ln.target,
                "target_basis": ln.basis,
                "locator": reader.locator(ln.element).to_json(),
            }
            if not ln.red:
                item["exclusion"] = "template_page_link"
            if ln.hidden is not None:
                item.update(kind="hidden", part="hidden_redlink" if ln.red else "hidden_template_link")
                item["hidden_basis"] = ln.hidden
                hidden.append(item)
            elif ln.red:
                redlinks.append(item)
            else:
                ambiguous.append(item)
        all_evidence = evidence + cite_warn + ambiguous + hidden + redlinks
        region_json = {"region_id": region_id, "locator": locator, "hidden_elements": region.hidden_elements}
        limited = region_id in omitted_regions or any(
            reader.contains(e, w) or reader.contains(w, e) for e in els for w in warning_owners
        )
        empty = not (shown.chars or hidden_ch.chars or region.marker_links)
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
        elif c.layout == "standalone_template" and _line_continues(els[-1]):
            state, reason = (
                "not_inspected",
                "a citation template in running text: the rest of its line is not part of the inspected region",
            )
        else:
            state, reason = "no_recognized_warning_in_inspected_region", "no profile term in the inspected text"
        out.append(MarkerObservation(c.id, state, reason, region_json, all_evidence, source_markers))
    return out
