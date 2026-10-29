"""Render extraction from a retained Parsoid HTML capture (SPECIFICATION.md 12.2).

The supported profile is Parsoid HTML 2.x as returned by the Core REST revision HTML endpoint: reference uses
are elements whose ``typeof`` contains ``mw:Extension/ref`` (with ``data-mw`` naming the ref's attributes),
reference lists are ``mw:Extension/references`` elements, and template output is grouped by ``about`` with the
first element of a group carrying ``typeof`` ``mw:Transclusion`` and the template's ``data-mw``.

lxml (libxml2) builds the DOM. Every locator is relative to that DOM under the declared parser profile: an
element id with its uniqueness, the lxml element path, a short text quote and the SHA-256 of the element's
lxml serialization. The serialization is derived from the DOM; it is not a byte range of the captured HTML.
No script is executed and no resource is fetched.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import lxml  # type: ignore[import-untyped]
import lxml.etree  # type: ignore[import-untyped]
import lxml.html  # type: ignore[import-untyped]

HTML_PARSER = "lxml"
HTML_PARSER_VERSION = lxml.__version__
LIBXML_VERSION = ".".join(str(x) for x in lxml.etree.LIBXML_VERSION)
SUPPORTED_HTML_MAJOR_MINOR = ("2.8",)
_SKIP_TEXT_TAGS = {"style", "script", "link", "meta", "noscript", "template"}
_HIDDEN_CLASSES = {"cs1-maint", "cs1-hidden-error", "mw-empty-elt"}
_WS = re.compile(r"\s+")
_PATH = re.compile(r"^(?:/[a-z][a-z0-9]{0,15}(?:\[[1-9][0-9]{0,6}\])?){1,400}$(?!\n)")
_STEP = re.compile(r"^([a-z][a-z0-9]{0,15})(?:\[([1-9][0-9]{0,6})\])?$")
# Comments MediaWiki's preprocessor leaves where it stopped expanding (Parser::limitationWarn and friends).
_LIMIT_WARNING = re.compile(
    r"(?i)WARNING: template omitted|template loop detected|expansion depth limit|"
    r"post-expand include size too large|template argument omitted"
)


@dataclass
class Locator:
    element_id: str | None
    id_unique: bool
    path: str
    quote: str
    subtree_sha256: str

    def to_json(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "id_unique": self.id_unique,
            "path": self.path,
            "quote": self.quote,
            "subtree_sha256": self.subtree_sha256,
        }


@dataclass
class RenderUse:
    index: int
    locator: Locator
    name: str | None
    group: str
    target_note: str | None
    in_transclusion: str | None  # about id of the enclosing template output
    in_note: str | None  # id of the reference list item that contains this use (nested refs)
    data_mw_ok: bool


@dataclass
class RenderNote:
    index: int
    locator: Locator
    note_id: str
    group: str
    list_index: int
    backlinks: list[str]
    text_id: str | None


@dataclass
class RenderTransclusion:
    about: str
    locator: Locator
    templates: list[tuple[str, dict[str, str]]]  # (target wikitext, params name -> wikitext)
    in_note: str | None
    in_list_item: str | None
    omitted: str | None = None  # the parser's limit warning when MediaWiki did not expand this template


@dataclass
class RenderLink:
    index: int
    locator: Locator
    href: str
    text: str
    in_note: str | None
    in_list_item: str | None
    in_transclusion: str | None
    hidden: bool


@dataclass
class RenderDoc:
    profile_version: str | None
    revision_about: int | None
    meta: dict[str, str]
    uses: list[RenderUse] = field(default_factory=list)
    notes: list[RenderNote] = field(default_factory=list)
    lists: list[dict[str, Any]] = field(default_factory=list)
    transclusions: list[RenderTransclusion] = field(default_factory=list)
    links: list[RenderLink] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    limit_warnings: list[dict[str, Any]] = field(default_factory=list)
    data_mw_errors: int = 0
    elements: int = 0
    _by_about: dict[str, RenderTransclusion] = field(default_factory=dict, repr=False, compare=False)

    def transclusion(self, about: str | None) -> RenderTransclusion | None:
        """The first transclusion with this ``about`` (index built on first use)."""
        if not self._by_about and self.transclusions:
            for t in self.transclusions:
                self._by_about.setdefault(t.about, t)
        return self._by_about.get(about) if about is not None else None


class RenderLimitExceeded(Exception):
    pass


def _style_hides(style: str | None) -> bool:
    """Whether an inline style hides the element (``display:none`` or ``visibility:hidden``), compared without case
    and whitespace as CSS does. Only inline styles are read; stylesheets are never applied."""
    if not style:
        return False
    flat = re.sub(r"\s+", "", style.lower())
    return "display:none" in flat or "visibility:hidden" in flat


def _norm_text(text: str) -> str:
    return _WS.sub(" ", text).strip()


class RenderReader:
    def __init__(self, data: bytes, max_elements: int = 2_000_000) -> None:
        parser = lxml.html.HTMLParser(encoding="utf-8", remove_comments=False, no_network=True, huge_tree=False)
        self.doc = lxml.html.document_fromstring(data, parser=parser)
        # libxml2 stops building the tree at its nesting limit (about 256 levels without huge_tree) and drops the
        # rest of the document with a fatal error. Such a tree is incomplete: it is never read as the render.
        for entry in parser.error_log:
            if entry.level_name == "FATAL" or "excessive depth" in entry.message.lower():
                raise RenderLimitExceeded(f"HTML parser stopped: {entry.message.strip()[:200]}")
        self.tree = self.doc.getroottree()
        self.ids: Counter[str] = Counter()
        self.about_types: dict[str, set[str]] = {}
        self.parent: dict[Any, Any] = {}
        self._by_path: dict[str, Any] = {}  # elements this reader has located (paths it produced itself)
        self._about_index: dict[str, list[Any]] | None = None
        count = 0
        self.omitted: dict[str, str] = {}  # about -> parser limit warning
        self.limit_warnings: list[dict[str, Any]] = []
        for el in self.doc.iter():
            if not isinstance(el.tag, str):
                if el.tag is lxml.etree.Comment and _LIMIT_WARNING.search(el.text or ""):
                    owner = el.getparent()
                    about = owner.get("about") if owner is not None else None
                    warning = _norm_text(el.text or "")
                    self.limit_warnings.append(
                        {
                            "about": about,
                            "warning": warning,
                            "path": self.tree.getpath(owner) if owner is not None else None,
                        }
                    )
                    if about:
                        self.omitted.setdefault(str(about), warning)
                continue
            count += 1
            if count > max_elements:
                raise RenderLimitExceeded(f"more than {max_elements} elements")
            if el.get("id"):
                self.ids[el.get("id")] += 1
            about = el.get("about")
            if about:
                self.about_types.setdefault(about, set()).update((el.get("typeof") or "").split())
        self.elements = count

    def locator(self, el: Any) -> Locator:
        eid = el.get("id")
        quote = _norm_text(el.text_content())[:160]
        sub = lxml.html.tostring(el, encoding="utf-8", with_tail=False)
        path = self.tree.getpath(el)
        self._by_path[path] = el
        return Locator(eid, bool(eid) and self.ids[eid] == 1, path, quote, hashlib.sha256(sub).hexdigest())

    def _ancestors(self, el: Any) -> list[Any]:
        out = []
        cur = el.getparent()
        while cur is not None:
            out.append(cur)
            cur = cur.getparent()
        return out

    def _transclusion_about(self, el: Any, include_self: bool = False) -> str | None:
        """The template output that contains ``el``. Inside a reference list item the search stops at the item:
        the template that wraps the whole list (for example a reference-list template) is not the item's."""
        chain = ([el] if include_self else []) + self._ancestors(el)
        for node in chain:
            if node.tag == "li" and (node.get("id") or "").startswith("cite_note"):
                return None
            about = node.get("about")
            if about and "mw:Transclusion" in self.about_types.get(about, set()):
                return str(about)
        return None

    def _note_of(self, el: Any) -> str | None:
        for node in self._ancestors(el):
            if node.tag == "li" and (node.get("id") or "").startswith("cite_note"):
                return str(node.get("id"))
        return None

    def _list_item_of(self, el: Any) -> str | None:
        for node in self._ancestors(el):
            if node.tag == "li":
                if (node.get("id") or "").startswith("cite_note"):
                    return None
                return str(self.tree.getpath(node))
        return None

    def read(self) -> RenderDoc:
        head = {}
        for meta in self.doc.iter("meta"):
            prop = meta.get("property") or meta.get("http-equiv")
            if prop in (
                "mw:revisionSHA1",
                "mw:pageId",
                "mw:pageNamespace",
                "mw:htmlVersion",
                "mw:html:version",
                "x-mediawiki-render-id",
                "dc:modified",
                "content-language",
            ):
                head[prop] = meta.get("content") or ""
        about = self.doc.get("about") or ""
        m = re.search(r"/revision/([0-9]+)$", about)
        out = RenderDoc(head.get("mw:htmlVersion") or head.get("mw:html:version"), int(m.group(1)) if m else None, head)
        out.elements = self.elements
        out.duplicate_ids = sorted(k for k, v in self.ids.items() if v > 1)
        out.limit_warnings = self.limit_warnings
        for el in self.doc.iter():
            if not isinstance(el.tag, str):
                continue
            types = (el.get("typeof") or "").split()
            if "mw:Extension/ref" in types:
                self._use(el, out)
            if "mw:Extension/references" in types:
                self._references(el, out)
            if "mw:Transclusion" in types:
                self._transclusion(el, out)
            if el.tag == "a" and el.get("href") and "mw:ExtLink" in (el.get("rel") or ""):
                self._link(el, out)
        return out

    def _data_mw(self, el: Any, out: RenderDoc) -> dict[str, Any] | None:
        raw = el.get("data-mw")
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except ValueError:
            out.data_mw_errors += 1
            return None
        return value if isinstance(value, dict) else None

    def _use(self, el: Any, out: RenderDoc) -> None:
        dm = self._data_mw(el, out)
        attrs = dm.get("attrs", {}) if dm else {}
        a = el.find(".//a")
        href = a.get("href") if a is not None else None
        target = None
        if href and "#" in href:
            target = urllib.parse.unquote(href.split("#", 1)[1])
        name = attrs.get("name") if isinstance(attrs, dict) else None
        group = attrs.get("group") if isinstance(attrs, dict) else None
        out.uses.append(
            RenderUse(
                len(out.uses),
                self.locator(el),
                name.strip() if isinstance(name, str) else None,
                group.strip() if isinstance(group, str) else "",
                target,
                self._transclusion_about(el, include_self=True),
                self._note_of(el),
                dm is not None,
            )
        )

    def _references(self, el: Any, out: RenderDoc) -> None:
        dm = self._data_mw(el, out)
        attrs = dm.get("attrs", {}) if dm else {}
        group = attrs.get("group", "") if isinstance(attrs, dict) else ""
        group = group.strip() if isinstance(group, str) else ""
        list_index = len(out.lists)
        items = []
        for li in el.iter("li"):
            nid = li.get("id")
            if not nid or not nid.startswith("cite_note"):
                continue
            back = []
            for a in li.iter("a"):
                if a.get("rel") == "mw:referencedBy" and a.get("href") and "#" in a.get("href"):
                    back.append(urllib.parse.unquote(a.get("href").split("#", 1)[1]))
            text = li.find(".//span[@class]")
            text_id = None
            for span in li.iter("span"):
                if "mw-reference-text" in (span.get("class") or "").split():
                    text_id = span.get("id")
                    break
            del text
            note = RenderNote(len(out.notes), self.locator(li), nid, group, list_index, back, text_id)
            out.notes.append(note)
            items.append(nid)
        out.lists.append({"index": list_index, "group": group, "locator": self.locator(el).to_json(), "notes": items})

    def _transclusion(self, el: Any, out: RenderDoc) -> None:
        dm = self._data_mw(el, out)
        templates = []
        if dm:
            for part in dm.get("parts", []):
                if isinstance(part, dict) and isinstance(part.get("template"), dict):
                    t = part["template"]
                    target = t.get("target", {}).get("wt")
                    params = {}
                    for k, v in (t.get("params") or {}).items():
                        if isinstance(v, dict) and isinstance(v.get("wt"), str):
                            params[str(k)] = v["wt"]
                    if isinstance(target, str):
                        templates.append((target, params))
        out.transclusions.append(
            RenderTransclusion(
                str(el.get("about")),
                self.locator(el),
                templates,
                self._note_of(el),
                self._list_item_of(el),
                self.omitted.get(str(el.get("about"))),
            )
        )

    def _hidden(self, el: Any) -> bool:
        for node in [el, *self._ancestors(el)]:
            cls = set((node.get("class") or "").split())
            if cls & _HIDDEN_CLASSES or _style_hides(node.get("style")):
                return True
            if node.get("hidden") is not None:
                return True
        return False

    def _link(self, el: Any, out: RenderDoc) -> None:
        out.links.append(
            RenderLink(
                len(out.links),
                self.locator(el),
                el.get("href"),
                _norm_text(el.text_content()),
                self._note_of(el),
                self._list_item_of(el),
                self._transclusion_about(el, include_self=True),
                self._hidden(el),
            )
        )

    def about_group(self, about: str) -> list[Any]:
        """Every element of one template's output (the elements that share its ``about``), in document order."""
        if self._about_index is None:
            index: dict[str, list[Any]] = {}
            for el in self.doc.iter():
                if isinstance(el.tag, str) and el.get("about"):
                    index.setdefault(str(el.get("about")), []).append(el)
            self._about_index = index
        return list(self._about_index.get(about, []))

    def contains(self, outer: Any, inner: Any) -> bool:
        """Whether ``inner`` is ``outer`` or one of its descendants."""
        node = inner
        while node is not None:
            if node is outer:
                return True
            node = node.getparent()
        return False

    def element_by_path(self, path: str) -> Any:
        """The element at an lxml element path (``/html/body/section[2]/p``), or None. The path is walked step by
        step; it is never evaluated as XPath, so a path read from a record cannot run an expression."""
        if path in self._by_path:
            return self._by_path[path]
        if not _PATH.match(path):
            return None
        steps = path[1:].split("/")
        first = _STEP.match(steps[0])
        if first is None or first.group(1) != self.doc.tag or first.group(2) not in (None, "1"):
            return None
        el = self.doc
        for step in steps[1:]:
            m = _STEP.match(step)
            if m is None:
                return None
            same = [c for c in el if c.tag == m.group(1)]
            if m.group(2) is None:
                if len(same) != 1:
                    return None
                el = same[0]
            else:
                n = int(m.group(2))
                if not 1 <= n <= len(same) or len(same) == 1:
                    return None
                el = same[n - 1]
        return el

    def region_text(self, el: Any) -> dict[str, Any]:
        """Visible-candidate text of a region with the excluded parts kept apart (markers.py applies the rules)."""
        parts: list[str] = []
        cite_parts: list[str] = []
        hidden_parts: list[str] = []
        redlinks: list[str] = []
        hidden_redlinks: list[str] = []
        hidden_flags = 0

        def walk(node: Any, in_cite: bool, hidden: bool) -> None:
            nonlocal hidden_flags
            # The text after a node belongs to the enclosing context, also when the node itself is skipped
            # (a comment, a category <link>, a <style>, a backlink): dropping it would hide shown text.
            tail_target = hidden_parts if hidden else cite_parts if in_cite else parts
            if not isinstance(node.tag, str):
                if node.tail:
                    tail_target.append(node.tail)
                return
            tag = node.tag
            cls = set((node.get("class") or "").split())
            if tag in _SKIP_TEXT_TAGS or "mw-cite-backlink" in cls:
                if node.tail:
                    tail_target.append(node.tail)
                return
            node_hidden = (
                hidden
                or bool(cls & _HIDDEN_CLASSES)
                or _style_hides(node.get("style"))
                or node.get("hidden") is not None
            )
            if node_hidden and not hidden:
                hidden_flags += 1
            if tag == "a" and "new" in cls:
                label = node.get("title") or _norm_text(node.text_content())
                (hidden_redlinks if node_hidden else redlinks).append(label)
                if node.tail:
                    tail_target.append(node.tail)
                return
            target = hidden_parts if node_hidden else cite_parts if (in_cite or tag == "cite") else parts
            if node.text:
                target.append(node.text)
            for child in node:
                walk(child, in_cite or tag == "cite", node_hidden)
            if node.tail:
                tail_target.append(node.tail)

        walk(el, False, False)
        # The region element's own tail is outside the region.
        if el.tail and parts and parts[-1] == el.tail:
            parts.pop()
        return {
            "text": _norm_text(" ".join(parts)),
            "cite_text": _norm_text(" ".join(cite_parts)),
            "hidden_text": _norm_text(" ".join(hidden_parts)),
            "redlinks": redlinks,
            "hidden_redlinks": hidden_redlinks,
            "hidden_elements": hidden_flags,
        }


def read_render(data: bytes, max_elements: int = 2_000_000) -> tuple[RenderDoc, RenderReader]:
    reader = RenderReader(data, max_elements)
    return reader.read(), reader
