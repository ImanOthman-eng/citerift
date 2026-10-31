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
from collections.abc import Callable
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
# Region text (region_text): elements whose content renders nothing and takes no room, so the text around them
# joins; block elements, whose content never runs into the text around them; and inline elements, whose text runs
# on. Any other element (an image, an unknown tag) is a soft boundary: a match across it is only ambiguous.
_TRANSPARENT_TAGS = frozenset(_SKIP_TEXT_TAGS | {"wbr"})
_BLOCK_TAGS = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "caption",
        "center",
        "dd",
        "details",
        "dialog",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "legend",
        "li",
        "main",
        "menu",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    ]
)
_INLINE_TAGS = frozenset(
    [
        "a",
        "abbr",
        "b",
        "bdi",
        "bdo",
        "big",
        "cite",
        "code",
        "data",
        "del",
        "dfn",
        "em",
        "font",
        "i",
        "ins",
        "kbd",
        "mark",
        "q",
        "rp",
        "rt",
        "ruby",
        "s",
        "samp",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "tt",
        "u",
        "var",
    ]
)
HARD = "\u2029"  # a block boundary in region text (PARAGRAPH SEPARATOR): never inside a term, never a space
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


@dataclass
class TextChannel:
    """One channel of a region's text: its characters, the element and the hiding basis of each (None for a hard
    boundary), and the positions p where a soft boundary falls between characters p-1 and p."""

    chars: list[str] = field(default_factory=list)
    origin: list[Any] = field(default_factory=list)
    basis: list[str | None] = field(default_factory=list)
    label: list[str] = field(default_factory=list)  # the channel each character came from ("text", "cite", ...)
    soft: set[int] = field(default_factory=set)
    # Positions where content a reader sees but that is not this channel's text (a marker link's label, a backlink,
    # an unknown element) touches a character with no space between: a match that starts or ends there is unsure.
    edges: set[int] = field(default_factory=set)

    def add(self, c: str, el: Any, basis: str | None, label: str) -> None:
        self.chars.append(c)
        self.origin.append(el)
        self.basis.append(basis)
        self.label.append(label)

    def pop(self) -> None:
        self.chars.pop()
        self.origin.pop()
        self.basis.pop()
        self.label.pop()

    @property
    def text(self) -> str:
        return "".join(self.chars)


@dataclass
class RegionLink:
    """A link in a region whose target names a marker template: its label is not region text."""

    element: Any
    label: str
    target: str
    basis: str  # where the target was read: "href" or "title_attribute"
    red: bool
    href: str | None
    hidden: str | None  # the hiding basis, or None


@dataclass
class RegionText:
    channels: dict[str, TextChannel]
    marker_links: list[RegionLink]
    hidden_elements: int


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
        self._locators: dict[Any, Locator] = {}  # the tree never changes after parsing
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
        cached = self._locators.get(el)
        if cached is not None:
            return cached
        loc = self._locator(el)
        self._locators[el] = loc
        return loc

    def _locator(self, el: Any) -> Locator:
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

    def common_ancestor(self, els: list[Any]) -> Any:
        """The nearest element that contains every element of ``els`` (non-empty)."""
        chain = [els[0], *self._ancestors(els[0])]
        for el in els[1:]:
            mine = {id(n) for n in [el, *self._ancestors(el)]}
            chain = [n for n in chain if id(n) in mine]
        return chain[0]

    def enclosing_link(self, el: Any, region: list[Any]) -> dict[str, Any] | None:
        """The link an evidence element lies in, within the region: its target, how the target was read, and
        whether it is a red link (a page that does not exist)."""
        for node in [el, *self._ancestors(el)]:
            if node.tag == "a":
                target, basis = link_target(node)
                return {
                    "target": target,
                    "target_basis": basis,
                    "red": "new" in (node.get("class") or "").split(),
                    "href": node.get("href"),
                }
            if any(node is r for r in region):
                return None
        return None

    def hide_reason(self, node: Any) -> str | None:
        """Why the HTML itself hides this element (the supported rules only), or None."""
        cls = set((node.get("class") or "").split())
        if _style_hides(node.get("style")):
            flat = re.sub(r"\s+", "", (node.get("style") or "").lower())
            rule = "display:none" if "display:none" in flat else "visibility:hidden"
        elif node.get("hidden") is not None:
            rule = "hidden attribute"
        elif cls & _HIDDEN_CLASSES:
            rule = "class " + ",".join(sorted(cls & _HIDDEN_CLASSES))
        else:
            return None
        return f"{rule} on <{node.tag}> {self.tree.getpath(node)}"

    def inherited_hiding(self, el: Any) -> str | None:
        """The nearest hiding element among ``el`` and its ancestors (outside the region too), or None."""
        for node in [el, *self._ancestors(el)]:
            if isinstance(node.tag, str):
                reason = self.hide_reason(node)
                if reason is not None:
                    return reason
        return None

    def region_text(self, els: list[Any], marker_link: Callable[[str], bool]) -> RegionText:
        """The text of a rendered region in two channels (SPECIFICATION.md 13): the text a reader is shown (each
        character labelled ``text``, or ``cite`` inside ``<cite>``) and the text the HTML hides; links to
        marker-template pages are kept apart. The text is rebuilt as a reader reads it: inline elements and comments
        do not break a word (``<span>Re</span>tracted`` is "Retracted"), ``<q>`` adds its quotation marks, block
        elements and ``<br>`` break it, and hidden content inside shown text is a soft boundary, across which a match
        is only ambiguous. Hiding is inherited from every ancestor, also outside the region. ``marker_link`` tells
        whether a link target names a marker template."""
        tokens: list[tuple[Any, ...]] = []
        links: list[RegionLink] = []
        hiding: set[str] = set()

        def emit(text: str, channel: str, el: Any, basis: str | None) -> None:
            if text:
                tokens.append(("t", channel, text, el, basis))

        def element(node: Any, channel: str, basis: str | None) -> None:
            tag = node.tag
            cls = set((node.get("class") or "").split())
            if tag in _TRANSPARENT_TAGS:
                return
            if "mw-cite-backlink" in cls and _structural_backlink(node):
                tokens.append(("soft",))
                return
            own = self.hide_reason(node) if basis is None else None
            if own is not None:
                hiding.add(own)
            basis = basis or own
            if tag == "a":
                target, how = link_target(node)
                if target is not None and marker_link(target):
                    links.append(
                        RegionLink(
                            node, _norm_text(node.text_content()), target, how, "new" in cls, node.get("href"), basis
                        )
                    )
                    tokens.append(("soft",))
                    return
            if tag in _BLOCK_TAGS:
                tokens.append(("hard",))
            elif tag not in _INLINE_TAGS:
                tokens.append(("soft",))
            inner = "hidden" if basis is not None else "cite" if (channel == "cite" or tag == "cite") else channel
            if tag == "q":
                emit("\u201c", inner, node, basis)
            emit(node.text or "", inner, node, basis)
            for child in node:
                if isinstance(child.tag, str):
                    element(child, inner, basis)
                # Comments and processing instructions render nothing: the text around them joins.
                emit(child.tail or "", inner, node, basis)
            if tag == "q":
                emit("\u201d", inner, node, basis)
            if tag in _BLOCK_TAGS:
                tokens.append(("hard",))
            elif tag not in _INLINE_TAGS:
                tokens.append(("soft",))

        for i, el in enumerate(els):
            if i:
                tokens.append(("hard",))
            parent = el.getparent()
            basis = self.inherited_hiding(parent) if parent is not None else None
            if basis is not None:
                hiding.add(basis)
            start = "cite" if any(a.tag == "cite" for a in self._ancestors(el)) else "text"
            # The region element's own tail is outside the region.
            element(el, start, basis)
        return RegionText(
            {
                "shown": _channel(tokens, frozenset(("text", "cite"))),
                "hidden": _channel(tokens, frozenset(("hidden",))),
            },
            links,
            len(hiding),
        )


def _structural_backlink(node: Any) -> bool:
    """Parsoid's backlink span: a direct child of the note's list item holding the ``mw:referencedBy`` links. Any
    other element with that class (an editor can set classes) is ordinary content."""
    parent = node.getparent()
    return (
        parent is not None
        and parent.tag == "li"
        and any("mw:referencedBy" in (a.get("rel") or "").split() for a in node.iter("a"))
    )


def link_target(a: Any) -> tuple[str | None, str]:
    """The page a link points to and where that was read: Parsoid writes wiki links as ``./Title`` (red links add
    ``?action=edit&redlink=1``); the title attribute is the fallback."""
    href = a.get("href") or ""
    if href.startswith("./"):
        path = href[2:].split("#", 1)[0].split("?", 1)[0]
        return urllib.parse.unquote(path).replace("_", " "), "href"
    title = a.get("title")
    if title:
        return title, "title_attribute"
    return None, "none"


def _channel(tokens: list[tuple[Any, ...]], include: frozenset[str]) -> TextChannel:
    """The characters of the channels in ``include``: whitespace runs (any Unicode space, U+2029 included) as one
    space, a hard boundary as U+2029, and the soft boundaries and edges between characters.

    A soft boundary is content outside ``include`` (hidden text for the shown channel) or an excluded element lying
    between two characters with no space between them. An edge is where an excluded element a reader sees (a
    ``("soft",)`` token: a marker link, a backlink, an unknown element) touches a character with no space."""
    ch = TextChannel()
    hard = soft = edge = ws = False
    for tok in tokens:
        if tok[0] == "hard":
            hard = True
            continue
        if tok[0] == "soft" or tok[1] not in include:
            visible = tok[0] == "soft"
            if visible and not ws and ch.chars and ch.chars[-1] not in (" ", HARD):
                ch.edges.add(len(ch.chars))
            soft, edge, ws = True, edge or visible, False
            continue
        for c in tok[2]:
            if c.isspace():
                ws = True
                if ch.chars and ch.chars[-1] not in (" ", HARD):
                    ch.add(" ", tok[3], tok[4], tok[1])
                continue
            if hard and ch.chars:
                if ch.chars[-1] == " ":
                    ch.pop()
                if ch.chars[-1] != HARD:
                    ch.add(HARD, None, None, "")
            elif not hard and not ws:
                if soft and ch.chars and ch.chars[-1] not in (" ", HARD):
                    ch.soft.add(len(ch.chars))
                if edge:
                    ch.edges.add(len(ch.chars))
            hard = soft = edge = ws = False
            ch.add(c, tok[3], tok[4], tok[1])
    while ch.chars and ch.chars[-1] in (" ", HARD):
        ch.pop()
    n = len(ch.chars)
    ch.soft = {p for p in ch.soft if 0 < p < n}
    ch.edges = {p for p in ch.edges if p <= n}
    return ch


def read_render(data: bytes, max_elements: int = 2_000_000) -> tuple[RenderDoc, RenderReader]:
    reader = RenderReader(data, max_elements)
    return reader.read(), reader
