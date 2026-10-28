"""Source extraction: a lossless traversal of the saved wikitext (SPECIFICATION.md 11, 12.1).

mwparserfromhell parses the slot text; ``str(tree) == text`` is required. Every node's code point interval is
computed from its parent's interval with the serialization formula of its node type, and each interval is
checked against the text itself (``text[start:end] == str(node)``) before it is used: a boundary that fails the
check is reported and never used as an exact anchor. Nothing is located with a global text search.

The traversal records ref tags (and the few ref-generating templates the profile supports), templates with
their parameters, and identifier candidates with their context. ``extract.py`` turns these records into
containers, units, uses and identifier occurrences.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

import mwparserfromhell
from mwparserfromhell.nodes import (
    Argument,
    Comment,
    ExternalLink,
    Heading,
    HTMLEntity,
    Node,
    Tag,
    Template,
    Text,
    Wikilink,
)
from mwparserfromhell.nodes.extras import Parameter
from mwparserfromhell.wikicode import Wikicode

from citerift.wiki.identifiers import url_scheme
from citerift.wiki.profile import TAG_REF, Profile, WikiProfile

PARSER_NAME = "mwparserfromhell"
PARSER_VERSION = mwparserfromhell.__version__

# A DOI starts with "10.", a registrant code of 4 to 9 digits (optionally subdivided) and a slash. Its end in free
# text is the first whitespace or wikitext delimiter; nothing else is trimmed (SPECIFICATION.md 11.4).
_DOI_START = re.compile(r"(?<![0-9A-Za-z])10\.[0-9]{4,9}(?:\.[0-9]+)*/")
_LEXEME_STOP = re.compile(r"[\s|\[\]{}<>\"]")
_TRAILING_AMBIGUOUS = ".,;:"
_DIGITS = "0-9٠-٩۰-۹"
_PMID_LABEL = re.compile(rf"(?i)(?<![A-Za-z])pmid\s*:?\s*([{_DIGITS}]+)(?![{_DIGITS}A-Za-z])")


@dataclass
class Limits:
    max_nodes: int = 400_000
    max_depth: int = 60
    max_refs: int = 20_000
    max_templates: int = 50_000
    max_candidates: int = 50_000


class LimitExceeded(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class Frame:
    """An enclosing template parameter."""

    template: int
    param: str | None  # None while inside the template name


@dataclass
class Ctx:
    excluded: str | None = None
    ref: int | None = None
    list_zone: bool = False
    list_group: str = ""
    frames: tuple[Frame, ...] = ()
    link_display: bool = False
    unsupported: str | None = None


@dataclass
class RefRecord:
    index: int
    start: int
    end: int
    body_start: int | None
    body_end: int | None
    origin: str  # "tag" | generated-ref kind from the profile ("tag_ref", "refn", "efn", "r")
    name_raw: str | None
    name: str | None
    group_raw: str | None
    group: str
    name_problem: str | None
    has_body: bool
    zone: str  # "prose" | "list_defined" | "nested" | "template_param"
    parent_ref: int | None
    template: int | None
    unsupported_context: str | None
    extra_attributes: tuple[str, ...]
    exact: bool = True
    uses_names: tuple[str, ...] = ()  # for {{r}}: the names it uses


@dataclass
class ParamRecord:
    name_raw: str
    name: str
    showkey: bool
    start: int
    end: int
    value_start: int
    value_end: int


@dataclass
class TemplateRecord:
    index: int
    start: int
    end: int
    raw_name: str
    canonical: str | None
    kind: str  # citation | external_data | wrapper | marker | generated_ref | reflist | other
    family: str | None
    params: list[ParamRecord]
    ref: int | None
    parent_template: int | None
    excluded: str | None
    exact: bool = True


@dataclass
class Candidate:
    """An identifier-shaped value found in the source, before roles and containers are assigned."""

    scheme: str
    origin: str  # template_field | wrapper | url | label_text | plain_text
    start: int
    end: int
    raw: str
    decoded: str
    steps: tuple[str, ...]
    boundary: str  # field | delimited | ambiguous_trailing_punctuation | url
    ref: int | None
    template: int | None
    param: str | None
    frames: tuple[Frame, ...]
    excluded: str | None
    link_display: bool = False
    has_markup: bool = False


@dataclass
class SourceScan:
    text: str
    refs: list[RefRecord] = field(default_factory=list)
    templates: list[TemplateRecord] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    excluded_candidates: list[Candidate] = field(default_factory=list)
    unclosed_refs: list[tuple[int, int]] = field(default_factory=list)
    inexact: list[tuple[int, int, str]] = field(default_factory=list)
    unparsed: list[tuple[int, int, str]] = field(default_factory=list)
    unsupported: list[tuple[int, int, str]] = field(default_factory=list)
    headings: list[tuple[int, int, str]] = field(default_factory=list)
    comment_cut: int | None = None
    nodes: int = 0


def _decode_attr(value: str) -> str:
    return html.unescape(value).strip()


def _has_markup(code: Wikicode) -> bool:
    """True when the value holds markup other than text, entities, comments and bare URLs. A bare URL (a free external
    link without brackets and without markup inside) is text in a parameter value: counting it as markup would
    traverse it a second time and report the same bytes twice."""
    return any(not isinstance(n, (Text, HTMLEntity, Comment)) and not _bare_url(n) for n in code.nodes)


def _bare_url(node: object) -> bool:
    return isinstance(node, ExternalLink) and not node.brackets and not _has_markup(node.url)


def _plain(code: Wikicode) -> tuple[str, list[str]]:
    """Text of a value with comments removed and entities decoded, and the steps that were applied."""
    steps = []
    parts = []
    for n in code.nodes:
        if isinstance(n, Comment):
            steps.append("COMMENT_REMOVED")
        elif isinstance(n, HTMLEntity):
            parts.append(n.normalize())
            steps.append("HTML_ENTITY_DECODED")
        else:
            parts.append(str(n))
    return "".join(parts), sorted(set(steps))


class Scanner:
    def __init__(self, text: str, wiki: WikiProfile, profile: Profile, limits: Limits) -> None:
        self.text = text
        self.wiki = wiki
        self.profile = profile
        self.limits = limits
        self.scan = SourceScan(text)

    # Traversal --------------------------------------------------------------------------------------------

    def run(self) -> SourceScan:
        tree = mwparserfromhell.parse(self.text, skip_style_tags=True)
        if str(tree) != self.text:
            raise LimitExceeded("SOURCE_PARSE_LOSSY", "the parse tree does not reproduce the text")
        self._code(tree, 0, Ctx(), 0)
        return self.scan

    def _children(self, code: Wikicode, base: int) -> Iterator[tuple[Node, int, int]]:
        pos = base
        for node in code.nodes:
            length = len(str(node))
            yield node, pos, pos + length
            pos += length

    def _check(self, node: object, start: int, end: int) -> bool:
        if self.text[start:end] == str(node):
            return True
        self.scan.inexact.append((start, end, type(node).__name__))
        return False

    def _code(self, code: Wikicode, base: int, ctx: Ctx, depth: int) -> None:
        if depth > self.limits.max_depth:
            raise LimitExceeded("LIMIT_DEPTH", f"nesting deeper than {self.limits.max_depth}")
        run: list[tuple[Node, int, int]] = []
        for node, start, end in self._children(code, base):
            self.scan.nodes += 1
            if self.scan.nodes > self.limits.max_nodes:
                raise LimitExceeded("LIMIT_NODES", f"more than {self.limits.max_nodes} nodes")
            if not self._check(node, start, end):
                continue
            if isinstance(node, (Text, HTMLEntity)):
                run.append((node, start, end))
                continue
            if run:
                self._text_run(run, ctx)
                run = []
            self._node(node, start, end, ctx, depth)
        if run:
            self._text_run(run, ctx)

    def _node(self, node: Node, start: int, end: int, ctx: Ctx, depth: int) -> None:
        if isinstance(node, Comment):
            self._scan_excluded(start + 4, end - 3, ctx, "comment")
        elif isinstance(node, Template):
            self._template(node, start, end, ctx, depth)
        elif isinstance(node, Tag):
            self._tag(node, start, end, ctx, depth)
        elif isinstance(node, Wikilink):
            t0 = start + 2
            t1 = t0 + len(str(node.title))
            self._code(node.title, t0, Ctx(**{**ctx.__dict__, "link_display": True}), depth + 1)
            if node.text is not None:
                self._code(node.text, t1 + 1, ctx, depth + 1)
        elif isinstance(node, ExternalLink):
            self._external_link(node, start, end, ctx, depth)
        elif isinstance(node, Heading):
            t0 = start + node.level
            self.scan.headings.append((start, end, str(node.title).strip()))
            self._code(node.title, t0, ctx, depth + 1)
        elif isinstance(node, Argument):
            self.scan.unsupported.append((start, end, "template_argument"))

    # Templates --------------------------------------------------------------------------------------------

    def _classify(self, raw_name: str) -> tuple[str | None, str, str | None]:
        stripped = raw_name.strip()
        low = stripped.casefold()
        if low.startswith("#tag:"):
            tag = low[5:].strip()
            return None, ("generated_ref" if tag == "ref" else "other"), ("tag_ref" if tag == "ref" else None)
        canonical = self.wiki.canonical_template(stripped)
        if canonical is None:
            return None, "other", None
        w = self.wiki
        if canonical in w.citation_templates:
            return canonical, "citation", w.citation_templates[canonical]
        if canonical in w.external_data_templates:
            return canonical, "external_data", None
        if canonical in w.wrappers:
            return canonical, "wrapper", w.wrappers[canonical]
        if canonical in w.markers:
            return canonical, "marker", None
        if canonical in w.generated_refs:
            return canonical, "generated_ref", w.generated_refs[canonical].kind
        if canonical in w.reflists:
            return canonical, "reflist", None
        return canonical, "other", None

    def _template(self, node: Template, start: int, end: int, ctx: Ctx, depth: int) -> None:
        if len(self.scan.templates) >= self.limits.max_templates:
            raise LimitExceeded("LIMIT_OCCURRENCES", f"more than {self.limits.max_templates} templates")
        raw_name = str(node.name)
        name_plain, _ = _plain(node.name)
        canonical, kind, family = self._classify(name_plain)
        if _has_markup(node.name):
            canonical, kind, family = None, "other", None
        index = len(self.scan.templates)
        rec = TemplateRecord(
            index,
            start,
            end,
            raw_name,
            canonical,
            kind,
            family,
            [],
            ctx.ref,
            ctx.frames[-1].template if ctx.frames else None,
            ctx.excluded,
        )
        self.scan.templates.append(rec)
        pos = start + 2
        self._code(node.name, pos, Ctx(**{**ctx.__dict__, "frames": (*ctx.frames, Frame(index, None))}), depth + 1)
        pos += len(raw_name)
        for param in node.params:
            pos += 1  # "|"
            p_start = pos
            p_str = str(param)
            if param.showkey:
                name_raw = str(param.name)
                v_start = p_start + len(name_raw) + 1
            else:
                name_raw = str(param.name)
                v_start = p_start
            v_end = p_start + len(p_str)
            if self.text[v_start:v_end] != str(param.value):
                self.scan.inexact.append((p_start, v_end, "Parameter"))
                rec.exact = False
                pos = v_end
                continue
            pname = _plain(param.name)[0].strip() if param.showkey else name_raw.strip()
            rec.params.append(ParamRecord(name_raw, pname, bool(param.showkey), p_start, v_end, v_start, v_end))
            pos = v_end
        if pos + 2 != end:
            self.scan.inexact.append((start, end, "Template"))
            rec.exact = False
        if kind == "generated_ref" and not ctx.excluded:
            self._generated_ref(node, rec, ctx, depth)
            return
        seen: dict[str, int] = {}
        for prm, param in zip(rec.params, node.params, strict=False):
            seen[prm.name] = seen.get(prm.name, 0) + 1
            sub = Ctx(**{**ctx.__dict__, "frames": (*ctx.frames, Frame(index, prm.name))})
            spec = self.wiki.reflists.get(canonical or "") if kind == "reflist" else None
            if spec is not None and prm.name in spec.refs_params:
                sub.list_zone = True
                sub.ref = None
                given = [
                    _plain(v.value)[0].strip()
                    for q, v in zip(rec.params, node.params, strict=False)
                    if q.name in spec.group_params
                ]
                sub.list_group = next((g for g in given if g), spec.default_group)
            if self._identifier_param(rec, prm, param.value, ctx):
                continue
            self._code(param.value, prm.value_start, sub, depth + 1)

    def _identifier_param(self, rec: TemplateRecord, prm: ParamRecord, value: Wikicode, ctx: Ctx) -> bool:
        """An identifier or URL field of a citation, external-data or unsupported template, or a wrapper's value.
        Returns True when the value was consumed as one candidate."""
        scheme: str | None = None
        origin = "template_field"
        if rec.kind == "wrapper" and prm.name == "1":
            scheme, origin = rec.family, "wrapper"
        elif rec.kind in ("citation", "external_data", "other", "marker") and prm.name in self.wiki.identifier_params:
            scheme = self.wiki.identifier_params[prm.name]
        elif rec.kind in ("citation", "external_data") and prm.name in self.wiki.url_params:
            plain, _ = _plain(value)
            if self._url_scheme(plain.strip()) is None:
                return False
            scheme, origin = self._url_scheme(plain.strip()), "url"
        if scheme is None:
            return False
        decoded, steps = _plain(value)
        markup = _has_markup(value)
        frames = (*ctx.frames, Frame(rec.index, prm.name))
        cand = Candidate(
            scheme,
            origin,
            prm.value_start,
            prm.value_end,
            self.text[prm.value_start : prm.value_end],
            decoded,
            tuple(steps),
            "url" if origin == "url" else "field",
            ctx.ref,
            rec.index,
            prm.name,
            frames,
            ctx.excluded,
            has_markup=markup,
        )
        self._add(cand)
        if markup:
            # Nested markup (for example a wrapper template inside the field) is still traversed.
            self._code(value, prm.value_start, Ctx(**{**ctx.__dict__, "frames": frames}), 1)
        return True

    def _generated_ref(self, node: Template, rec: TemplateRecord, ctx: Ctx, depth: int) -> None:
        """{{#tag:ref|body|name=|group=}}, {{refn}}, {{efn}} (body in parameter 1) and {{r|name|...}} (uses)."""
        kind = rec.family or ""
        params = {p.name: (p, prm) for p, prm in zip(rec.params, node.params, strict=False)}
        if kind == "r":
            # {{r|a|b}} uses the refs named a and b; named parameters (page numbers and the like) are not names.
            names = tuple(
                _plain(prm.value)[0].strip() for p, prm in zip(rec.params, node.params, strict=False) if not p.showkey
            )
            spec_r = self.wiki.generated_refs.get(rec.canonical or "")
            group_r = next(
                (_plain(params[g][1].value)[0].strip() for g in (spec_r.group_params if spec_r else ()) if g in params),
                "",
            )
            self._add_ref(rec.start, rec.end, None, None, "r", None, None, group_r, ctx, (), uses_names=names)
            return
        if kind == "sfn":
            # {{sfn}} and relatives generate a short footnote from their parameters; the note text is not in the
            # source. Identical calls share one note (the template derives the ref name from the parameters).
            self._add_ref(rec.start, rec.end, None, None, "sfn", None, None, None, ctx, (), body_has_text=True)
            for p, prm in zip(rec.params, node.params, strict=False):
                sub = Ctx(**{**ctx.__dict__, "frames": (*ctx.frames, Frame(rec.index, p.name))})
                self._code(prm.value, p.value_start, sub, depth + 1)
            return
        spec = self.wiki.generated_refs.get(rec.canonical or "", TAG_REF)

        def first(names: tuple[str, ...]) -> tuple[ParamRecord, Parameter] | None:
            return next((params[n] for n in names if n in params), None)

        body = first(spec.body_params)
        name = first(spec.name_params)
        group = first(spec.group_params)
        given_group = _plain(group[1].value)[0].strip() if group else ""
        # The footnote templates map an empty or unknown group to their default (their #switch); a group the
        # template accepts is passed on unchanged.
        group_value: str | None = given_group or spec.default_group or None
        name_value = _plain(name[1].value)[0].strip() if name else None
        name_markup = bool(name and _has_markup(name[1].value)) or bool(group and _has_markup(group[1].value))
        ref_index = self._add_ref(
            rec.start,
            rec.end,
            body[0].value_start if body else None,
            body[0].value_end if body else None,
            kind,
            str(name[1].value) if name else None,
            name_value,
            group_value,
            ctx,
            (),
            name_problem="REF_NAME_HAS_MARKUP" if name_markup else None,
            body_has_text=bool(body and str(body[1].value).strip()),
        )
        for p, prm in zip(rec.params, node.params, strict=False):
            sub = Ctx(**{**ctx.__dict__, "frames": (*ctx.frames, Frame(rec.index, p.name))})
            if body is not None and p is body[0]:
                sub.ref = ref_index
                sub.list_zone = False
            self._code(prm.value, p.value_start, sub, depth + 1)

    # Tags -------------------------------------------------------------------------------------------------

    def _tag(self, node: Tag, start: int, end: int, ctx: Ctx, depth: int) -> None:
        name = str(node.tag).strip().casefold()
        if node.wiki_markup:
            # Tables and other wiki markup: contents only.
            if node.contents is not None and not node.self_closing:
                offset = self._contents_offset(node, start, end)
                if offset is not None:
                    self._code(node.contents, offset, ctx, depth + 1)
            return
        if name in self.profile.excluded_tags:
            if node.self_closing or node.contents is None:
                return
            offset = self._contents_offset(node, start, end)
            if offset is not None and node.contents is not None:
                self._scan_excluded(offset, offset + len(str(node.contents)), ctx, f"tag:{name}")
            return
        if name == "ref" and not node.invalid:
            self._ref_tag(node, start, end, ctx, depth)
            return
        sub = ctx
        if name == "references":
            group_attr = next(
                (
                    _decode_attr(_plain(a.value)[0])
                    for a in node.attributes
                    if str(a.name).strip().casefold() == "group" and a.value is not None
                ),
                "",
            )
            sub = Ctx(**{**ctx.__dict__, "list_zone": True, "ref": None, "list_group": group_attr})
        elif name in self.profile.unsupported_tags:
            sub = Ctx(**{**ctx.__dict__, "unsupported": f"tag:{name}"})
        if node.self_closing or node.contents is None:
            return
        offset = self._contents_offset(node, start, end)
        if offset is None:
            return
        contents = node.contents
        if name in self.profile.unsupported_tags and all(isinstance(n, (Text, HTMLEntity)) for n in contents.nodes):
            # mwparserfromhell leaves the body of <gallery> or <poem> as text; MediaWiki parses its captions and
            # lines as wikitext, so the body is parsed again here (same offsets, checked like any other node).
            contents = mwparserfromhell.parse(str(contents), skip_style_tags=True)
        self._code(contents, offset, sub, depth + 1)

    def _contents_offset(self, node: Tag, start: int, end: int) -> int | None:
        contents = str(node.contents)
        close = (node.closing_wiki_markup or "") if node.wiki_markup else "</" + str(node.closing_tag) + ">"
        offset = end - len(close) - len(contents)
        if self.text[offset : end - len(close)] != contents or self.text[end - len(close) : end] != close:
            self.scan.inexact.append((start, end, "TagContents"))
            return None
        return offset

    def _ref_tag(self, node: Tag, start: int, end: int, ctx: Ctx, depth: int) -> None:
        name_raw = group_raw = None
        name = None
        group = ""
        problem = None
        extra = []
        for attr in node.attributes:
            key = str(attr.name).strip().casefold()
            if attr.value is None:
                continue
            if key in ("name", "group"):
                if _has_markup(attr.value):
                    problem = "REF_NAME_HAS_MARKUP"
                if key == "name":
                    name_raw = str(attr.value)
                    name = _decode_attr(_plain(attr.value)[0]) or None
                else:
                    group_raw = str(attr.value)
                    group = _decode_attr(_plain(attr.value)[0])
            else:
                extra.append(key)
        body_start = body_end = None
        has_body = False
        if not node.self_closing and node.contents is not None:
            offset = self._contents_offset(node, start, end)
            if offset is not None:
                body_start, body_end = offset, offset + len(str(node.contents))
                has_body = bool(str(node.contents).strip())
        index = self._add_ref(
            start,
            end,
            body_start,
            body_end,
            "tag",
            name_raw,
            name,
            group,
            ctx,
            tuple(sorted(extra)),
            name_problem=problem,
            body_has_text=has_body,
            group_raw=group_raw,
        )
        if body_start is not None and node.contents is not None:
            self._code(node.contents, body_start, Ctx(**{**ctx.__dict__, "ref": index, "list_zone": False}), depth + 1)

    def _add_ref(
        self,
        start: int,
        end: int,
        body_start: int | None,
        body_end: int | None,
        origin: str,
        name_raw: str | None,
        name: str | None,
        group: str | None,
        ctx: Ctx,
        extra: tuple[str, ...],
        *,
        name_problem: str | None = None,
        body_has_text: bool = False,
        group_raw: str | None = None,
        uses_names: tuple[str, ...] = (),
    ) -> int:
        if ctx.excluded:
            return -1
        if len(self.scan.refs) >= self.limits.max_refs:
            raise LimitExceeded("LIMIT_OCCURRENCES", f"more than {self.limits.max_refs} refs")
        if ctx.list_zone and ctx.ref is None:
            zone = "list_defined"
            if not group:
                group = ctx.list_group  # a list-defined ref takes the list's group unless it names its own
        elif ctx.ref is not None:
            zone = "nested"
        elif ctx.frames:
            zone = "template_param"
        else:
            zone = "prose"
        index = len(self.scan.refs)
        self.scan.refs.append(
            RefRecord(
                index,
                start,
                end,
                body_start,
                body_end,
                origin,
                name_raw,
                name,
                group_raw,
                group or "",
                name_problem,
                body_has_text,
                zone,
                ctx.ref,
                ctx.frames[-1].template if ctx.frames else None,
                ctx.unsupported,
                extra,
                uses_names=uses_names,
            )
        )
        return index

    # External links ---------------------------------------------------------------------------------------

    def _url_scheme(self, url: str) -> str | None:
        return url_scheme(url)

    def _external_link(self, node: ExternalLink, start: int, end: int, ctx: Ctx, depth: int) -> None:
        url_start = start + 1 if node.brackets else start
        url_str = str(node.url)
        url_end = url_start + len(url_str)
        decoded, steps = _plain(node.url)
        scheme = None if _has_markup(node.url) else self._url_scheme(decoded.strip())
        if scheme is not None:
            self._add(
                Candidate(
                    scheme,
                    "url",
                    url_start,
                    url_end,
                    url_str,
                    decoded,
                    tuple(steps),
                    "url",
                    ctx.ref,
                    ctx.frames[-1].template if ctx.frames else None,
                    ctx.frames[-1].param if ctx.frames else None,
                    ctx.frames,
                    ctx.excluded,
                )
            )
        if node.brackets and node.title is not None:
            t_start = url_end + (0 if node.suppress_space else 1)
            sub = Ctx(**{**ctx.__dict__, "link_display": scheme is not None or ctx.link_display})
            self._code(node.title, t_start, sub, depth + 1)

    # Text -------------------------------------------------------------------------------------------------

    def _decoded_run(self, run: list[tuple[Node, int, int]]) -> tuple[str, list[int], list[int]]:
        """Decoded text of a run of Text and HTMLEntity nodes with the source interval of every decoded char."""
        chars: list[str] = []
        starts: list[int] = []
        ends: list[int] = []
        for node, s, e in run:
            if isinstance(node, HTMLEntity):
                value = node.normalize()
                for ch in value:
                    chars.append(ch)
                    starts.append(s)
                    ends.append(e)
            else:
                for i, ch in enumerate(str(node)):
                    chars.append(ch)
                    starts.append(s + i)
                    ends.append(s + i + 1)
        return "".join(chars), starts, ends

    def _text_run(self, run: list[tuple[Node, int, int]], ctx: Ctx) -> None:
        decoded, starts, ends = self._decoded_run(run)
        raw_start, raw_end = run[0][1], run[-1][2]
        if "<!--" in self.text[raw_start:raw_end] and not ctx.excluded:
            at = raw_start + self.text[raw_start:raw_end].index("<!--")
            if self.scan.comment_cut is None or at < self.scan.comment_cut:
                self.scan.comment_cut = at
        if not ctx.excluded and re.search(r"(?i)<ref[\s>/]", decoded):
            self.scan.unclosed_refs.append((raw_start, raw_end))
        if "{{" in decoded and not ctx.excluded:
            self.scan.unparsed.append((raw_start, raw_end, "template_braces_in_text"))
        for m in _DOI_START.finditer(decoded):
            i = m.start()
            stop = _LEXEME_STOP.search(decoded, m.end())
            j = stop.start() if stop else len(decoded)
            lexeme = decoded[i:j]
            boundary = "delimited"
            if lexeme[-1] in _TRAILING_AMBIGUOUS or (lexeme.endswith(")") and lexeme.count("(") < lexeme.count(")")):
                boundary = "ambiguous_trailing_punctuation"
            before = decoded[max(0, i - 12) : i]
            labels = "|".join(re.escape(x) for x in ("doi", *self._doi_labels()))
            origin = "label_text" if re.search(rf"(?i)(?:{labels})\s*:\s*$", before) else "plain_text"
            s, e = starts[i], ends[j - 1]
            raw = self.text[s:e]
            steps = ("HTML_ENTITY_DECODED",) if raw != lexeme else ()
            self._add(self._text_cand("doi", origin, s, e, raw, lexeme, steps, boundary, ctx))
        for m in _PMID_LABEL.finditer(decoded):
            i, j = m.start(1), m.end(1)
            s, e = starts[i], ends[j - 1]
            raw = self.text[s:e]
            self._add(self._text_cand("pmid", "label_text", s, e, raw, m.group(1), (), "delimited", ctx))

    def _doi_labels(self) -> tuple[str, ...]:
        return self.wiki.doi_text_labels

    def _text_cand(
        self,
        scheme: str,
        origin: str,
        s: int,
        e: int,
        raw: str,
        decoded: str,
        steps: tuple[str, ...],
        boundary: str,
        ctx: Ctx,
    ) -> Candidate:
        return Candidate(
            scheme,
            origin,
            s,
            e,
            raw,
            decoded,
            steps,
            boundary,
            ctx.ref,
            ctx.frames[-1].template if ctx.frames else None,
            ctx.frames[-1].param if ctx.frames else None,
            ctx.frames,
            ctx.excluded,
            link_display=ctx.link_display,
        )

    def _scan_excluded(self, start: int, end: int, ctx: Ctx, reason: str) -> None:
        """Identifier-shaped strings inside comments and non-rendered tags: recorded as excluded, never used."""
        segment = self.text[start:end]
        excluded_ctx = Ctx(**{**ctx.__dict__, "excluded": ctx.excluded or reason})
        for m in _DOI_START.finditer(segment):
            stop = _LEXEME_STOP.search(segment, m.end())
            j = stop.start() if stop else len(segment)
            s, e = start + m.start(), start + j
            self.scan.excluded_candidates.append(
                self._text_cand(
                    "doi", "plain_text", s, e, self.text[s:e], self.text[s:e], (), "delimited", excluded_ctx
                )
            )
        for m in _PMID_LABEL.finditer(segment):
            s, e = start + m.start(1), start + m.end(1)
            self.scan.excluded_candidates.append(
                self._text_cand(
                    "pmid", "label_text", s, e, self.text[s:e], self.text[s:e], (), "delimited", excluded_ctx
                )
            )

    def _add(self, cand: Candidate) -> None:
        if cand.excluded:
            self.scan.excluded_candidates.append(cand)
            return
        if len(self.scan.candidates) >= self.limits.max_candidates:
            raise LimitExceeded("LIMIT_OCCURRENCES", f"more than {self.limits.max_candidates} identifier candidates")
        self.scan.candidates.append(cand)


def scan_source(text: str, wiki: WikiProfile, profile: Profile, limits: Limits | None = None) -> SourceScan:
    scan = Scanner(text, wiki, profile, limits or Limits()).run()
    return _apply_comment_cut(scan)


def _apply_comment_cut(scan: SourceScan) -> SourceScan:
    """Everything from an unclosed ``<!--`` to the end is a comment in MediaWiki: move it out of the results."""
    cut = scan.comment_cut
    if cut is None:
        return scan
    scan.unparsed.append((cut, len(scan.text), "unclosed_comment"))
    keep = [c for c in scan.candidates if c.start < cut]
    for c in scan.candidates:
        if c.start >= cut:
            c.excluded = "unclosed_comment"
            scan.excluded_candidates.append(c)
    scan.candidates = keep
    dropped = {r.index for r in scan.refs if r.start >= cut}
    scan.refs = [r for r in scan.refs if r.index not in dropped]
    scan.templates = [t for t in scan.templates if t.start < cut]
    return scan
