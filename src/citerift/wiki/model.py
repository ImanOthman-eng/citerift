"""From source scan records to containers, uses, citation units and identifier occurrences (SPECIFICATION.md 10, 11).

Binding follows Cite: a ref name binds within its group only; a name and group are compared after trimming and
entity decoding; the same name in two groups is two keys. A definition inside <references> or a reference-list
template's ``refs=`` is not a use. Conflicting definitions stay conflicting; nothing picks the first one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from citerift.wiki.identifiers import Decoded, decode
from citerift.wiki.issues import Issue
from citerift.wiki.profile import Profile, WikiProfile
from citerift.wiki.source import AMBIGUOUS_BOUNDARIES, Candidate, RefRecord, SourceScan, TemplateRecord
from citerift.wiki.textmap import ByteMap

ID_FIELD_PARAMS = frozenset({"id", "ID"})
_WS = re.compile(r"\s+")


@dataclass
class Container:
    id: str
    kind: str  # note | list_defined_note | generated_note | bibliography_entry
    group: str
    name: str | None
    group_raw: str | None
    name_raw: str | None
    binding_state: str
    definitions: list[dict[str, Any]]
    start: int
    end: int
    layout: str | None = None
    unit_ids: list[str] = field(default_factory=list)
    use_ids: list[str] = field(default_factory=list)
    def_refs: list[int] = field(default_factory=list)


@dataclass
class Use:
    id: str
    ref: int
    origin: str
    zone: str
    group: str
    name: str | None
    binding: str
    container_id: str | None
    start: int
    end: int
    template: int | None
    parent_ref: int | None
    position: int = 0  # position among the uses a {{r}} template makes


@dataclass
class Unit:
    id: str
    container_id: str
    definition_id: str | None
    kind: str  # citation_template | external_data_template | unstructured_text
    template: int | None
    start: int
    end: int
    parent_unit: str | None = None
    identifier_ids: list[str] = field(default_factory=list)
    duplicate_params: list[str] = field(default_factory=list)


@dataclass
class Occurrence:
    id: str
    cand: Candidate
    role: str
    role_reason: str
    container_id: str | None
    unit_id: str | None
    decoded: Decoded | None


@dataclass
class SourceModel:
    containers: list[Container]
    uses: list[Use]
    units: list[Unit]
    occurrences: list[Occurrence]
    issues: list[Issue]
    ref_container: dict[int, str]
    template_unit: dict[int, str]
    templates: dict[int, TemplateRecord]
    refs: dict[int, RefRecord]


OVERRIDDEN = "is given again later; MediaWiki uses the last value"


def _overridden(t: TemplateRecord, cand: Candidate) -> bool:
    """The candidate is the value of a parameter that the same template repeats later (the later one wins)."""
    own = [p for p in t.params if p.value_start <= cand.start < max(p.value_end, p.value_start + 1)]
    return bool(own) and any(q.name == own[-1].name and q.value_start > own[-1].value_start for q in t.params)


def _role(
    cand: Candidate, templates: dict[int, TemplateRecord], wiki: WikiProfile, in_container: bool
) -> tuple[str, str]:
    """Markup role of one candidate and the rule that gave it (SPECIFICATION.md 11.5, decision list in order)."""
    frames = [(templates[f.template], f.param) for f in cand.frames if f.template in templates]
    if any(t.kind == "marker" for t, _ in frames):
        return "marker_target", "inside a retraction-marker template"
    if cand.link_display:
        return "textual_mention", "display text of a link"
    citation_frames = [(t, p) for t, p in frames if t.kind in ("citation", "external_data")]
    if citation_frames:
        t, p = citation_frames[-1]
        if p is None:
            return "textual_mention", "inside a citation template name"
        if cand.origin == "template_field" and cand.template == t.index:
            if _overridden(t, cand):
                return "unresolved", f"citation parameter {p} {OVERRIDDEN}"
            return "primary_citation_field", f"citation parameter {p}"
        if p in wiki.identifier_params or p in wiki.url_params or p in ID_FIELD_PARAMS:
            if _overridden(t, cand):
                return "unresolved", f"citation parameter {p} {OVERRIDDEN}"
            if cand.origin in ("url", "wrapper", "template_field"):
                return "identifier_link", f"{cand.origin} in citation parameter {p}"
            if cand.origin == "label_text":
                return "labeled_reference_text", f"labeled text in citation parameter {p}"
        return "textual_mention", f"inside citation parameter {p}"
    if cand.origin == "template_field":
        return "unresolved", "identifier parameter of a template the profile does not support"
    if cand.origin in ("url", "wrapper"):
        return "identifier_link", cand.origin
    if cand.origin == "label_text" and in_container:
        return "labeled_reference_text", "labeled identifier in reference text"
    return "textual_mention", "free text"


def build(scan: SourceScan, wiki: WikiProfile, profile: Profile, bmap: ByteMap) -> SourceModel:
    del bmap
    issues: list[Issue] = []
    refs = {r.index: r for r in scan.refs}
    templates = {t.index: t for t in scan.templates}
    text = scan.text
    containers: list[Container] = []
    uses: list[Use] = []
    ref_container: dict[int, str] = {}

    def cid() -> str:
        return f"ct-{len(containers) + 1:05d}"

    # Definitions -----------------------------------------------------------------------------------------
    by_key: dict[tuple[str, str], list[RefRecord]] = {}
    by_sfn: dict[str, list[RefRecord]] = {}
    for r in scan.refs:
        if r.origin == "r":
            continue
        if r.origin == "sfn":
            by_sfn.setdefault(r.sfn_key or _WS.sub("", text[r.start : r.end]), []).append(r)
            continue
        if not r.has_body:
            continue
        if r.name is not None and r.name_problem is None:
            by_key.setdefault((r.group, r.name), []).append(r)
        elif r.name_problem is not None:
            continue
        else:
            kind = (
                "generated_note" if r.origin != "tag" else ("list_defined_note" if r.zone == "list_defined" else "note")
            )
            c = Container(
                cid(),
                kind,
                r.group,
                None,
                r.group_raw,
                None,
                "anonymous",
                [_definition(r, text)],
                r.start,
                r.end,
                def_refs=[r.index],
            )
            containers.append(c)
            ref_container[r.index] = c.id
    for (group, name), defs in sorted(by_key.items(), key=lambda kv: kv[1][0].start):
        bodies = {text[d.body_start : d.body_end].strip() for d in defs if d.body_start is not None}
        if len(defs) == 1:
            state = "single_definition"
        elif len(bodies) == 1:
            state = "identical_definitions"
        else:
            state = "conflicting_definitions"
        first = defs[0]
        if all(d.zone == "list_defined" for d in defs):
            kind = "list_defined_note"
        elif all(d.origin != "tag" for d in defs):
            kind = "generated_note"
        else:
            kind = "note"
        c = Container(
            cid(),
            kind,
            group,
            name,
            first.group_raw,
            first.name_raw,
            state,
            [_definition(d, text) for d in defs],
            first.start,
            first.end,
            def_refs=[d.index for d in defs],
        )
        containers.append(c)
        for d in defs:
            ref_container[d.index] = c.id
        if state == "conflicting_definitions":
            issues.append(Issue("REF_DEFINITIONS_CONFLICT", (c.id,), f"group {group!r} name {name!r}"))
        elif state == "identical_definitions":
            issues.append(Issue("REF_DEFINITIONS_DUPLICATE", (c.id,), f"group {group!r} name {name!r}"))
    for calls in by_sfn.values():
        first = calls[0]
        c = Container(
            cid(),
            "generated_note",
            "",
            None,
            None,
            None,
            "single_definition" if len(calls) == 1 else "identical_definitions",
            [_definition(d, text) for d in calls],
            first.start,
            first.end,
            layout="short_footnote",
            def_refs=[d.index for d in calls],
        )
        containers.append(c)
        for d in calls:
            ref_container[d.index] = c.id
    containers.sort(key=lambda c: c.start)
    renumber = {c.id: f"ct-{i + 1:05d}" for i, c in enumerate(containers)}
    for c in containers:
        c.id = renumber[c.id]
    ref_container = {k: renumber[v] for k, v in ref_container.items()}
    key_container = {(c.group, c.name): c for c in containers if c.name is not None}
    by_id = {c.id: c for c in containers}

    # Uses ------------------------------------------------------------------------------------------------
    def add_use(r: RefRecord, group: str, name: str | None, position: int = 0) -> None:
        uid = f"us-{len(uses) + 1:05d}"
        if r.name_problem is not None:
            binding, container = "unbindable_name", None
            issues.append(Issue("REF_NAME_HAS_MARKUP", (uid,)))
        elif name is None:
            if r.has_body:
                binding, container = "anonymous", ref_container[r.index]
            else:
                binding, container = "empty_anonymous", None
        elif (group, name) in key_container:
            c = key_container[(group, name)]
            binding = "bound_conflicting" if c.binding_state == "conflicting_definitions" else "bound"
            container = c.id
        else:
            binding, container = "definition_missing", None
            issues.append(Issue("REF_DEFINITION_MISSING", (uid,), f"group {group!r} name {name!r}"))
        uses.append(
            Use(
                uid,
                r.index,
                r.origin,
                r.zone,
                group,
                name,
                binding,
                container,
                r.start,
                r.end,
                r.template,
                r.parent_ref,
                position,
            )
        )
        if container is not None:
            by_id[container].use_ids.append(uid)
        if r.unsupported_context:
            issues.append(Issue("REF_IN_UNSUPPORTED_CONTEXT", (uid,), r.unsupported_context))
        if r.extra_attributes and {"details", "extends"} & set(r.extra_attributes):
            issues.append(Issue("SUBREFERENCE_UNSUPPORTED", (uid,), ",".join(r.extra_attributes)))

    for r in scan.refs:
        if r.zone == "list_defined":
            # A ref inside a reference list defines a reference (whatever wrote it: a tag, {{efn}}, {{#tag:ref}});
            # it is never a use in the article. One without content defines nothing and is reported.
            if not r.has_body:
                issues.append(
                    Issue("LIST_DEFINED_WITHOUT_CONTENT", (), f"code points {r.start}-{r.end}, name {r.name!r}")
                )
            continue
        if r.origin == "r":
            for i, n in enumerate(r.uses_names):
                add_use(r, r.group, n or None, i)
            continue
        add_use(r, r.group, r.name)
    for c in containers:
        if c.kind == "list_defined_note" and not c.use_ids:
            issues.append(Issue("LIST_DEFINED_UNUSED", (c.id,)))

    # Bibliography containers ------------------------------------------------------------------------------
    def line_bounds(start: int, end: int) -> tuple[int, int]:
        ls = text.rfind("\n", 0, start) + 1
        le = text.find("\n", end)
        return ls, (len(text) if le < 0 else le)

    bib: dict[int, Container] = {}
    outside_templates = [t for t in scan.templates if t.ref is None and t.kind in ("citation", "external_data")]
    outside_cands = [c for c in scan.candidates if c.ref is None]
    members: list[tuple[int, int]] = [(t.start, t.end) for t in outside_templates]
    members += [(c.start, c.end) for c in outside_cands]
    for start, end in sorted(members):
        ls, le = line_bounds(start, end)
        if text[ls : ls + 1] in ("*", "#", ":", ";"):
            existing = next((b for b in bib.values() if b.start <= start < b.end), None)
            if existing is None:
                b = Container(
                    "", "bibliography_entry", "", None, None, None, "not_applicable", [], ls, le, layout="list_item"
                )
                bib[ls] = b
            else:
                existing.end = max(existing.end, le)
    for t in outside_templates:
        if not any(b.start <= t.start < b.end for b in bib.values()):
            bib[t.start] = Container(
                "",
                "bibliography_entry",
                "",
                None,
                None,
                None,
                "not_applicable",
                [],
                t.start,
                t.end,
                layout="standalone_template",
            )
    all_containers = containers + list(bib.values())
    all_containers.sort(key=lambda c: (c.start, 0 if c.kind != "bibliography_entry" else 1))
    renumber = {}
    for i, c in enumerate(all_containers):
        new = f"ct-{i + 1:05d}"
        if c.id:
            renumber[c.id] = new
        c.id = new
    ref_container = {k: renumber[v] for k, v in ref_container.items()}
    for u in uses:
        if u.container_id is not None:
            u.container_id = renumber[u.container_id]
    containers = all_containers
    bib_list = [c for c in containers if c.kind == "bibliography_entry"]

    def bib_of(start: int) -> Container | None:
        return next((b for b in bib_list if b.start <= start < b.end), None)

    # Units -----------------------------------------------------------------------------------------------
    units: list[Unit] = []
    template_unit: dict[int, str] = {}
    unit_templates = [tpl for tpl in scan.templates if tpl.kind in ("citation", "external_data") and not tpl.excluded]
    for tpl in unit_templates:
        if tpl.ref is not None:
            if tpl.ref not in ref_container:
                continue  # inside a ref without a bindable definition (for example an empty or unbindable ref)
            owner_id = ref_container[tpl.ref]
            definition_id = f"{owner_id}/d{_def_index(containers, owner_id, tpl.ref)}"
        else:
            entry = bib_of(tpl.start)
            if entry is None:
                continue
            owner_id, definition_id = entry.id, None
        un = Unit(
            f"un-{len(units) + 1:05d}",
            owner_id,
            definition_id,
            "external_data_template" if tpl.kind == "external_data" else "citation_template",
            tpl.index,
            tpl.start,
            tpl.end,
        )
        names = [p.name for p in tpl.params]
        un.duplicate_params = sorted({n for n in names if names.count(n) > 1})
        if un.duplicate_params:
            issues.append(Issue("DUPLICATE_TEMPLATE_PARAMETER", (un.id,), ",".join(un.duplicate_params)))
        units.append(un)
        template_unit[tpl.index] = un.id
    for un in units:
        parent = templates[un.template].parent_template if un.template is not None else None
        while parent is not None:
            if parent in template_unit:
                un.parent_unit = template_unit[parent]
                break
            parent = templates[parent].parent_template if parent in templates else None
    # Unstructured units: a definition or bibliography entry without any citation template.
    with_template = {un.container_id for un in units}
    defined = {un.definition_id for un in units}
    for c in containers:
        if c.kind == "bibliography_entry":
            if c.id not in with_template:
                units.append(Unit(f"un-{len(units) + 1:05d}", c.id, None, "unstructured_text", None, c.start, c.end))
            continue
        if c.layout == "short_footnote":
            continue  # the note text is generated; the cited work is in the bibliography
        for i, dfn in enumerate(c.definitions):
            def_id = f"{c.id}/d{i + 1}"
            if def_id not in defined:
                units.append(
                    Unit(
                        f"un-{len(units) + 1:05d}",
                        c.id,
                        def_id,
                        "unstructured_text",
                        None,
                        dfn["_body"][0],
                        dfn["_body"][1],
                    )
                )
    units.sort(key=lambda un: (un.start, un.end, un.id))
    renumber_u = {un.id: f"un-{i + 1:05d}" for i, un in enumerate(units)}
    for un in units:
        un.id = renumber_u[un.id]
        if un.parent_unit:
            un.parent_unit = renumber_u[un.parent_unit]
    template_unit = {k: renumber_u[v] for k, v in template_unit.items()}
    for c in containers:
        c.unit_ids = [un.id for un in units if un.container_id == c.id]

    unit_by_id = {un.id: un for un in units}
    # Identifier occurrences -------------------------------------------------------------------------------
    occurrences: list[Occurrence] = []
    for cand in sorted(scan.candidates, key=lambda c: (c.start, c.end)):
        holder: str | None = None
        unit_id = None
        if cand.ref is not None:
            holder = ref_container.get(cand.ref)
            if holder is not None:
                def_id = f"{holder}/d{_def_index(containers, holder, cand.ref)}"
                unit_id = _unit_for(cand, units, template_unit, templates, def_id)
        else:
            entry = bib_of(cand.start)
            if entry is not None:
                holder = entry.id
                unit_id = _unit_for(cand, units, template_unit, templates, None, entry.id)
        role, reason = _role(cand, templates, wiki, holder is not None)
        oid = f"id-{len(occurrences) + 1:05d}"
        decoded = None
        if not cand.has_markup:
            decoded = decode(cand.scheme, cand.origin, cand.decoded, cand.steps)
            if decoded is None:
                issues.append(Issue("IDENTIFIER_DECODING_FAILED", (oid,), "invalid percent encoding in a DOI path"))
        else:
            issues.append(Issue("IDENTIFIER_VALUE_HAS_MARKUP", (oid,)))
        if role == "unresolved":
            owner_tpl = templates.get(cand.template) if cand.template is not None else None
            if reason.endswith(OVERRIDDEN):
                issues.append(Issue("IDENTIFIER_PARAMETER_OVERRIDDEN", (oid,), cand.param or "?"))
            else:
                issues.append(
                    Issue("TEMPLATE_UNSUPPORTED", (oid,), owner_tpl.canonical or "?" if owner_tpl is not None else "?")
                )
        if cand.boundary in AMBIGUOUS_BOUNDARIES:
            issues.append(Issue("IDENTIFIER_BOUNDARY_AMBIGUOUS", (oid,)))
        if decoded is not None and "DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS" in decoded.steps:
            issues.append(Issue("IDENTIFIER_BOUNDARY_AMBIGUOUS", (oid,), "the DOI path ends in a page-view segment"))
        if decoded is not None and not decoded.normalized.valid and not decoded.normalized.missing:
            issues.append(Issue("IDENTIFIER_INVALID", (oid,), ",".join(decoded.normalized.issues)))
        occ = Occurrence(oid, cand, role, reason, holder, unit_id, decoded)
        occurrences.append(occ)
        if unit_id is not None:
            unit_by_id[unit_id].identifier_ids.append(oid)
    # A DOI and a PMID in one unit are the normal case. Two distinct values of the same scheme are not: in a template
    # they are co-reported (both kept, neither chosen); in unstructured text the unit may hold more than one work.
    for un in units:
        per_scheme: dict[str, set[str]] = {}
        for o in occurrences:
            if o.unit_id != un.id or o.role not in (
                "primary_citation_field",
                "identifier_link",
                "labeled_reference_text",
            ):
                continue
            if o.decoded is not None and o.decoded.normalized.missing:
                continue
            value = o.decoded.normalized.normalized if o.decoded and o.decoded.normalized.valid else o.cand.raw
            per_scheme.setdefault(o.cand.scheme, set()).add(value or o.cand.raw)
        multi = sorted(s for s, values in per_scheme.items() if len(values) > 1)
        if multi:
            code = "UNIT_BOUNDARY_UNRESOLVED" if un.kind == "unstructured_text" else "CO_REPORTED_IDENTIFIERS"
            issues.append(Issue(code, (un.id,), "more than one distinct value for " + ",".join(multi)))
    return SourceModel(containers, uses, units, occurrences, issues, ref_container, template_unit, templates, refs)


def _definition(r: RefRecord, text: str) -> dict[str, Any]:
    body = (r.body_start, r.body_end) if r.body_start is not None and r.body_end is not None else (r.start, r.end)
    return {
        "_ref": r.index,
        "_span": (r.start, r.end),
        "_body": body,
        "zone": r.zone,
        "origin": r.origin,
        "body_text": text[body[0] : body[1]],
    }


def _def_index(containers: list[Container], container_id: str, ref_index: int) -> int:
    c = next(c for c in containers if c.id == container_id)
    return c.def_refs.index(ref_index) + 1 if ref_index in c.def_refs else 1


def _unit_for(
    cand: Candidate,
    units: list[Unit],
    template_unit: dict[int, str],
    templates: dict[int, TemplateRecord],
    definition_id: str | None,
    container_id: str | None = None,
) -> str | None:
    for frame in reversed(cand.frames):
        if frame.template in template_unit:
            return template_unit[frame.template]
    for u in units:
        if u.kind != "unstructured_text":
            continue
        if definition_id is not None and u.definition_id == definition_id:
            return u.id
        if container_id is not None and u.container_id == container_id and u.definition_id is None:
            return u.id
    del templates
    return None
