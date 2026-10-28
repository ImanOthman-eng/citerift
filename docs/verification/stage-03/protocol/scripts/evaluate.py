"""Stage 03 evaluation tooling (FROZEN_PROTOCOL.md). Written and committed before any holdout prediction exists.

Usage:
  python evaluate.py packets OUT_DIR BUNDLE [BUNDLE ...]      evaluator packets: raw source, raw HTML, window
  python evaluate.py lock ANNOTATION_DIR                      ANNOTATION_LOCK.json with the SHA-256 of each file
  python evaluate.py score SPEC.json > scores.json            metrics, gates, baselines and A/B/C comparison

SPEC.json names, per article: the bundle, the locked annotation, the optional adjudicated annotation and the
extraction produced after the lock, plus the split ("holdout", "challenge_observed", ...).

This file does not import the extractor (citerift.wiki): the expected labels come only from the annotation
files, and the engine's output is read as JSON. B1 (simple structural baseline) and B0
(Stage 01 known-identifier confirmation) are implemented here from their written definitions, without the
extractor's parsing code.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree
from lxml import html as lxml_html

WINDOW_CP = 8000
WINDOW_SALT = "citerift-stage03-window-v1"
REF_OPEN = re.compile(r"<ref[\s>/]", re.IGNORECASE)
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261028
ROLES = (
    "primary_citation_field",
    "identifier_link",
    "labeled_reference_text",
    "marker_target",
    "textual_mention",
    "unresolved",
    "not_a_target",
)
CITED_WORK_ROLES = ("primary_citation_field", "identifier_link")
NON_PROMOTABLE = ("marker_target", "textual_mention", "not_a_target")
MARKER_LABELS = ("warning", "ambiguous", "missing_template_link_only", "none", "not_inspected")
ENGINE_MARKER = {
    "recognized_warning_text": "warning",
    "ambiguous_text": "ambiguous",
    "missing_template_link_only": "missing_template_link_only",
    "no_recognized_warning_in_inspected_region": "none",
    "not_inspected": "not_inspected",
    "unavailable": "not_inspected",
}

# Frozen gates (FROZEN_PROTOCOL.md section 7), per language, on the adjudicated holdout labels.
GATES: dict[str, tuple[str, str, float]] = {
    "G1a identifier precision": ("identifiers", "precision", 0.97),
    "G1b identifier recall": ("identifiers", "recall", 0.90),
    "G2 normalized-key error rate": ("identifiers", "key_error_rate", 0.01),
    "G3a promotions to a cited-work role": ("identifiers", "promotions", 0),
    "G3b role agreement": ("identifiers", "role_agreement", 0.90),
    "G4a use precision": ("uses", "precision", 0.97),
    "G4b use recall": ("uses", "recall", 0.95),
    "G4c binding accuracy": ("uses", "binding_accuracy", 0.97),
    "G5a definition precision": ("definitions", "precision", 0.95),
    "G5b definition recall": ("definitions", "recall", 0.95),
    "G5c unit precision": ("units", "precision", 0.95),
    "G5d unit recall": ("units", "recall", 0.95),
    "G6a render link precision": ("render", "precision", 0.98),
    "G6b render false attachments": ("render", "false_attachments_allowed", 0),
    "G6c render coverage": ("render", "coverage", 0.85),
    "G7 fabricated negative markers": ("markers", "fabricated_negatives", 0),
}
MAX_IS_BOUND = {"G2 normalized-key error rate", "G3a promotions to a cited-work role", "G7 fabricated negative markers"}
MIN_DENOMINATORS = {"identifiers": 50, "uses": 80, "definitions": 60, "render": 60}


# --------------------------------------------------------------------------------------------- bundles


@dataclass
class Article:
    key: str
    wiki: str
    revision_id: int
    text: str
    html_bytes: bytes | None
    source_sha256: str
    html_sha256: str | None
    window: tuple[int, int]


def load_bundle(path: Path) -> Article:
    cap = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    page, source, render = cap["page"], cap["source"], cap["render"]
    raw = (path / "artifacts" / source["artifact"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source["artifact"]:
        raise SystemExit(f"{path}: source artifact hash mismatch")
    html_bytes = None
    if render.get("state") == "captured":
        html_bytes = (path / "artifacts" / render["artifact"]).read_bytes()
        if hashlib.sha256(html_bytes).hexdigest() != render["artifact"]:
            raise SystemExit(f"{path}: render artifact hash mismatch")
    text = raw.decode("utf-8")
    key = f"{page['wiki']}-{page['revision_id']}"
    return Article(
        key,
        page["wiki"],
        page["revision_id"],
        text,
        html_bytes,
        source["artifact"],
        render.get("artifact") if html_bytes is not None else None,
        window(text, page["wiki"], page["revision_id"]),
    )


def window(text: str, wiki: str, revision_id: int) -> tuple[int, int]:
    """The annotated scope: WINDOW_CP code points from the line holding a seeded-random <ref opening."""
    if len(text) <= WINDOW_CP:
        return 0, len(text)
    starts = [m.start() for m in REF_OPEN.finditer(text)]
    start = 0
    if starts:
        pick = int(hashlib.sha256(f"{WINDOW_SALT}|{wiki}|{revision_id}".encode()).hexdigest(), 16) % len(starts)
        start = text.rfind("\n", 0, starts[pick]) + 1
    start = min(start, len(text) - WINDOW_CP)
    return start, start + WINDOW_CP


def packets(out: Path, bundles: list[Path]) -> None:
    out.mkdir(parents=True, exist_ok=False)
    for b in bundles:
        art = load_bundle(b)
        d = out / art.key
        d.mkdir()
        (d / "source.wikitext").write_text(art.text, encoding="utf-8", newline="")
        if art.html_bytes is not None:
            (d / "render.html").write_bytes(art.html_bytes)
        ws, we = art.window
        info = {
            "wiki": art.wiki,
            "revision_id": art.revision_id,
            "source_sha256": art.source_sha256,
            "source_code_points": len(art.text),
            "html_sha256": art.html_sha256,
            "window": {"cp_start": ws, "cp_end": we},
            "window_first_line": art.text[ws : ws + 120],
        }
        (d / "packet.json").write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def lock(directory: Path) -> None:
    files = sorted(p for p in directory.glob("*.json") if p.name != "ANNOTATION_LOCK.json")
    entries = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (directory / "ANNOTATION_LOCK.json").write_text(json.dumps(entries, indent=1) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------- items


@dataclass
class Pred:
    """One predicted item in the common form scored for the engine and for B1."""

    start: int
    end: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Predictions:
    definitions: list[Pred]
    uses: list[Pred]
    units: list[Pred]
    identifiers: list[Pred]


def engine_predictions(doc: dict[str, Any]) -> Predictions:
    """Read an extraction document (schema urn:citerift:schema:wiki:v1:extraction) into the common form."""
    markers = {m["container_id"]: ENGINE_MARKER[m["state"]] for m in doc["markers"]}
    defs: list[Pred] = []
    spans: dict[str, list[tuple[int, int]]] = {}
    for c in doc["containers"]:
        items = [d["source"] for d in c["definitions"]] or [c["source"]]
        spans[c["id"]] = [(s["cp_start"], s["cp_end"]) for s in items]
        for s in items:
            defs.append(
                Pred(
                    s["cp_start"],
                    s["cp_end"],
                    {
                        "container": c["id"],
                        "kind": c["kind"],
                        "name": c["name"],
                        "group": c["group"],
                        "note_id": c["render"]["region_id"] if c["render"]["state"] == "matched" else None,
                        "marker": markers.get(c["id"], "not_inspected"),
                    },
                )
            )
    uses = []
    for u in doc["uses"]:
        r = u["render"]
        linked = r["locator"]["element_id"] if r["state"] == "matched" and r.get("locator") else None
        uses.append(
            Pred(
                u["source"]["cp_start"],
                u["source"]["cp_end"],
                {
                    "container": u["container_id"],
                    "binding": u["binding"],
                    "targets": spans.get(u["container_id"] or "", []),
                    "ref_id": linked,
                    "render_state": r["state"],
                },
            )
        )
    units = [
        Pred(
            un["source"]["cp_start"],
            un["source"]["cp_end"],
            {
                "kind": "unstructured" if un["kind"] == "unstructured_text" else "template",
                "container": un["container_id"],
            },
        )
        for un in doc["units"]
    ]
    idents = [
        Pred(
            i["source"]["cp_start"],
            i["source"]["cp_end"],
            {
                "scheme": i["scheme"],
                "key": i["normalization"]["normalized"],
                "role": i["role"],
                "container": i["container_id"],
            },
        )
        for i in doc["identifiers"]
    ]
    return Predictions(defs, uses, units, idents)


# --------------------------------------------------------------------------------------------- B1


B1_REF = re.compile(r"<ref(?P<attrs>[^>]*?)(?:/>|>(?P<body>.*?)</ref\s*>)", re.IGNORECASE | re.DOTALL)
B1_NAME = re.compile(r"""name\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'/>]+))""", re.IGNORECASE)
B1_TEMPLATE = re.compile(r"\{\{\s*(?:cite\s|citation\b|استشهاد)", re.IGNORECASE)
B1_IDS = (
    ("doi", "primary_citation_field", re.compile(r"\|\s*(?:doi|دوي)\s*=\s*(10\.[^\s|}<]+)", re.IGNORECASE)),
    ("pmid", "primary_citation_field", re.compile(r"\|\s*pmid\s*=\s*([0-9]+)", re.IGNORECASE)),
    ("doi", "identifier_link", re.compile(r"(?:dx\.)?doi\.org/(10\.[^\s|\]}<]+)", re.IGNORECASE)),
    (
        "pmid",
        "identifier_link",
        re.compile(r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|ncbi\.nlm\.nih\.gov/pubmed/)([0-9]+)", re.IGNORECASE),
    ),
)
B1_WARNING = {"en": ("retracted",), "ar": ("مسحوب",)}


def b1_predictions(art: Article) -> Predictions:
    """B1: regular expressions over <ref> tags only; names bind to the first definition with the same name
    (groups ignored); identifiers by field and resolver-URL patterns inside ref bodies; k-th use linked to the
    k-th rendered footnote marker; a warning when a fixed word occurs in the ref body."""
    text = art.text
    defs: list[Pred] = []
    uses: list[Pred] = []
    units: list[Pred] = []
    idents: list[Pred] = []
    first_def: dict[str, tuple[int, int]] = {}
    matches = list(B1_REF.finditer(text))
    for m in matches:
        nm = B1_NAME.search(m.group("attrs") or "")
        name = next((g for g in nm.groups() if g is not None), None) if nm else None
        body = m.group("body")
        if body is not None and body.strip():
            if name is not None:
                first_def.setdefault(name, (m.start(), m.end()))
            low = body.lower()
            marker = "warning" if any(w in low for w in B1_WARNING[art.wiki]) else "none"
            defs.append(Pred(m.start(), m.end(), {"name": name, "group": "", "note_id": None, "marker": marker}))
            bstart = m.start("body")
            tmpl = list(B1_TEMPLATE.finditer(body))
            units += [Pred(bstart + t.start(), bstart + t.end(), {"kind": "template"}) for t in tmpl]
            if not tmpl:
                units.append(Pred(m.start(), m.end(), {"kind": "unstructured"}))
            for scheme, role, rx in B1_IDS:
                for im in rx.finditer(body):
                    value = im.group(1).rstrip(".,;)")
                    s = bstart + im.start(1)
                    key = value.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
                    idents.append(Pred(s, s + len(value), {"scheme": scheme, "key": key, "role": role}))
    sups = rendered_ref_markers(art.html_bytes) if art.html_bytes is not None else []
    for k, m in enumerate(matches):
        nm = B1_NAME.search(m.group("attrs") or "")
        name = next((g for g in nm.groups() if g is not None), None) if nm else None
        has_body = m.group("body") is not None and bool(m.group("body").strip())
        if has_body:
            target = [(m.start(), m.end())]
        elif name is not None and name in first_def:
            target = [first_def[name]]
        else:
            target = []
        uses.append(
            Pred(
                m.start(),
                m.end(),
                {
                    "binding": "bound" if target else "definition_missing",
                    "targets": target,
                    "ref_id": sups[k] if k < len(sups) else None,
                },
            )
        )
    return Predictions(defs, uses, units, idents)


def rendered_ref_markers(html_bytes: bytes) -> list[str]:
    """ids of rendered footnote markers (sup elements typed mw:Extension/ref), in document order."""
    root = lxml_html.document_fromstring(html_bytes)
    out = []
    for el in root.iter("sup"):
        if "mw:Extension/ref" in (el.get("typeof") or "").split() and el.get("id"):
            out.append(el.get("id"))
    return out


# --------------------------------------------------------------------------------------------- annotations


def load_annotation(path: Path, art: Article) -> tuple[dict[str, Any], list[str]]:
    ann = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    a = ann["article"]
    if a["revision_id"] != art.revision_id or a["source_sha256"] != art.source_sha256:
        problems.append("annotation is for another revision or source")
    if tuple(a["window"]) != art.window:
        problems.append(f"annotation window {a['window']} differs from the protocol window {list(art.window)}")
    return ann, problems


def at_ok(text: str, at: dict[str, Any]) -> bool:
    cp, quote = at.get("cp"), at.get("quote")
    return isinstance(cp, int) and isinstance(quote, str) and quote != "" and text[cp : cp + len(quote)] == quote


def in_window(cp: int, win: tuple[int, int]) -> bool:
    return win[0] <= cp < win[1]


def match_points(points: list[tuple[int, Any]], preds: list[Pred]) -> tuple[dict[int, int], set[int]]:
    """Annotation point -> predicted interval containing it, nearest start first, one to one."""
    taken: set[int] = set()
    result: dict[int, int] = {}
    for ai, (cp, _) in sorted(enumerate(points), key=lambda x: x[1][0]):
        best = None
        for pi, p in enumerate(preds):
            if pi in taken or not (p.start <= cp < max(p.end, p.start + 1)):
                continue
            score = (abs(p.start - cp), p.end - p.start)
            if best is None or score < best[0]:
                best = (score, pi)
        if best is not None:
            taken.add(best[1])
            result[ai] = best[1]
    return result, taken


def match_spans(spans: list[tuple[int, int, str]], preds: list[Pred]) -> tuple[dict[int, int], set[int]]:
    """Annotated identifier span -> overlapping predicted span of the same scheme, largest overlap, one to one."""
    taken: set[int] = set()
    result: dict[int, int] = {}
    for ai, (s, e, scheme) in sorted(enumerate(spans), key=lambda x: x[1][0]):
        best = None
        for pi, p in enumerate(preds):
            if pi in taken or p.data["scheme"] != scheme:
                continue
            overlap = min(e, p.end) - max(s, p.start)
            if overlap > 0 and (best is None or overlap > best[0]):
                best = (overlap, pi)
        if best is not None:
            taken.add(best[1])
            result[ai] = best[1]
    return result, taken


def prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def score_article(art: Article, ann: dict[str, Any], pred: Predictions) -> dict[str, Any]:
    text, win = art.text, art.window
    invalid: list[str] = []

    def valid(items: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        out = []
        for it in items:
            if not at_ok(text, it["at"]):
                invalid.append(f"{kind} {it.get('id')}: quote does not occur at cp {it['at'].get('cp')}")
            elif in_window(it["at"]["cp"], win):
                out.append(it)
        return out

    a_defs = valid(ann["definitions"], "definition")
    a_uses = valid(ann["uses"], "use")
    a_ids = valid(ann["identifiers"], "identifier")
    p_defs = [p for p in pred.definitions if in_window(p.start, win)]
    p_uses = [p for p in pred.uses if in_window(p.start, win)]
    p_units = [p for p in pred.units if in_window(p.start, win)]
    p_ids = [p for p in pred.identifiers if in_window(p.start, win)]
    res: dict[str, Any] = {"article": art.key, "wiki": art.wiki, "window": list(win), "invalid_annotations": invalid}

    # Definitions and container grouping
    dm, dtaken = match_points([(d["at"]["cp"], d) for d in a_defs], p_defs)
    res["definitions"] = prf(len(dm), len(p_defs) - len(dtaken), len(a_defs) - len(dm))
    pairs_ok = pairs = 0
    matched = sorted(dm.items())
    for x in range(len(matched)):
        for y in range(x + 1, len(matched)):
            da, db = a_defs[matched[x][0]], a_defs[matched[y][0]]
            same_a = da.get("name") is not None and (da.get("name"), da.get("group", "")) == (
                db.get("name"),
                db.get("group", ""),
            )
            ca, cb = p_defs[matched[x][1]].data.get("container"), p_defs[matched[y][1]].data.get("container")
            same_p = ca is not None and ca == cb
            pairs += 1
            pairs_ok += same_a == same_p
    res["definitions"]["grouping_pairs"] = {"agree": pairs_ok, "total": pairs}

    # Units: citation/external-data templates inside definitions, and unstructured definitions
    # A template is in scope when its own start is in the window, whatever the start of its definition.
    tpl_a: list[tuple[int, str]] = []
    for d in ann["definitions"]:
        for t in d.get("templates", []):
            if not at_ok(text, t["at"]):
                invalid.append(f"template in {d.get('id')}: quote does not occur at cp {t['at'].get('cp')}")
            elif in_window(t["at"]["cp"], win):
                tpl_a.append((t["at"]["cp"], "template"))
    tpl_p = [p for p in p_units if p.data["kind"] == "template"]
    um, utaken = match_points(tpl_a, tpl_p)
    # An unstructured unit is a property of a definition: it matches an engine unstructured unit that starts
    # inside the engine definition matched to that annotated definition.
    # ... and in scope when that definition starts in the window.
    uns_p = [
        p
        for p in pred.units
        if p.data["kind"] == "unstructured" and any(d.start <= p.start < max(d.end, d.start + 1) for d in p_defs)
    ]
    uns_taken: set[int] = set()
    uns_a = uns_tp = 0
    for ai, d in enumerate(a_defs):
        if not d.get("unstructured"):
            continue
        uns_a += 1
        if ai in dm:
            pd = p_defs[dm[ai]]
            hit = next(
                (
                    k
                    for k, p in enumerate(uns_p)
                    if k not in uns_taken and pd.start <= p.start < max(pd.end, pd.start + 1)
                ),
                None,
            )
            if hit is not None:
                uns_taken.add(hit)
                uns_tp += 1
    res["units"] = prf(
        len(um) + uns_tp,
        len(tpl_p) - len(utaken) + len(uns_p) - len(uns_taken),
        len(tpl_a) - len(um) + uns_a - uns_tp,
    )

    # Uses, binding and render links
    um_, utk = match_points([(u["at"]["cp"], u) for u in a_uses], p_uses)
    res["uses"] = prf(len(um_), len(p_uses) - len(utk), len(a_uses) - len(um_))
    bind_ok = bind_total = 0
    correct = false_att = abstain = linkable = engine_links = 0
    render_rows = []
    for ai, pi in um_.items():
        au, pu = a_uses[ai], p_uses[pi]
        target = au.get("binds_to")
        if isinstance(target, dict) and at_ok(text, target):
            bind_total += 1
            bind_ok += any(s <= target["cp"] < max(e, s + 1) for s, e in pu.data["targets"])
        elif target == "missing":
            bind_total += 1
            bind_ok += pu.data["binding"] in ("definition_missing", "unbindable_name")
        want, got = au.get("render_ref_id"), pu.data.get("ref_id")
        if got is not None:
            engine_links += 1
        if want is not None:
            linkable += 1
            if got == want:
                correct += 1
            elif got is None:
                abstain += 1
            else:
                false_att += 1
                render_rows.append({"use": au.get("id"), "expected": want, "engine": got})
        elif got is not None:
            false_att += 1
            render_rows.append({"use": au.get("id"), "expected": None, "engine": got})
    res["uses"]["binding"] = {"correct": bind_ok, "total": bind_total}
    res["render"] = {
        "linkable": linkable,
        "engine_links": engine_links,
        "correct": correct,
        "false_attachments": false_att,
        "abstained": abstain,
        "false_attachment_rows": render_rows,
    }

    # Identifiers: occurrence detection, keys, roles
    targets = [i for i in a_ids if i["role"] != "not_a_target"]
    spans = [(i["at"]["cp"], i["at"]["cp"] + len(i["at"]["quote"]), i["scheme"]) for i in a_ids]
    im, itaken = match_spans(spans, p_ids)
    tp = sum(1 for ai in im if a_ids[ai]["role"] != "not_a_target")
    fp_nontarget = sum(1 for ai in im if a_ids[ai]["role"] == "not_a_target")
    fp = len(p_ids) - len(itaken) + fp_nontarget
    res["identifiers"] = prf(tp, fp, len(targets) - tp)
    key_err, roles, promotions, rows = 0, Counter(), 0, []
    for ai, pi in im.items():
        a, p = a_ids[ai], p_ids[pi]
        if a["role"] == "not_a_target":
            rows.append({"kind": "non_target_reported", "at": a["at"], "engine_role": p.data["role"]})
            continue
        roles[(a["role"], p.data["role"])] += 1
        if a.get("key") != p.data.get("key"):
            key_err += 1
            rows.append({"kind": "key", "at": a["at"], "expected": a.get("key"), "engine": p.data.get("key")})
        if a["role"] in NON_PROMOTABLE and p.data["role"] in CITED_WORK_ROLES:
            promotions += 1
            rows.append({"kind": "promotion", "at": a["at"], "expected": a["role"], "engine": p.data["role"]})
    for ai, a in enumerate(a_ids):
        if ai not in im and a["role"] != "not_a_target":
            rows.append({"kind": "missed", "at": a["at"], "role": a["role"]})
    res["identifiers"].update(
        {
            "key_errors": key_err,
            "promotions": promotions,
            "role_pairs": {f"{x}->{y}": n for (x, y), n in sorted(roles.items())},
            "role_agree": sum(n for (x, y), n in roles.items() if x == y),
            "role_total": sum(roles.values()),
            "rows": rows,
        }
    )

    # Markers: per matched definition
    confusion: Counter[tuple[str, str]] = Counter()
    fabricated = 0
    for ai, pi in dm.items():
        want = a_defs[ai].get("marker")
        if want in (None, "cannot_tell"):
            continue
        got = p_defs[pi].data.get("marker", "not_inspected")
        confusion[(want, got)] += 1
        fabricated += want == "warning" and got == "none"
    res["markers"] = {
        "confusion": {f"{x}->{y}": n for (x, y), n in sorted(confusion.items())},
        "fabricated_negatives": fabricated,
        "not_inspected": sum(n for (x, y), n in confusion.items() if y == "not_inspected"),
    }
    return res


# --------------------------------------------------------------------------------------------- baselines


def b0(art: Article, ann: dict[str, Any]) -> dict[str, Any]:
    """Stage 01 confirmation (PROTOCOL.md 3.3) on its valid task: is a known DOI present in the wikitext
    (case-insensitive, or its URL-encoded form)? Applied to every DOI key the annotator recorded in scope."""
    low = art.text.lower()
    by_key: dict[str, set[str]] = {}
    for i in ann["identifiers"]:
        if i["scheme"] == "doi" and i.get("key") and at_ok(art.text, i["at"]) and in_window(i["at"]["cp"], art.window):
            by_key.setdefault(i["key"], set()).add(i["role"])
    rows = []
    for key, roles in sorted(by_key.items()):
        encoded = re.sub(r"[^A-Za-z0-9._~/-]", lambda m: "".join(f"%{b:02x}" for b in m.group().encode()), key)
        found = key in low or encoded.lower() in low
        rows.append(
            {
                "key": key,
                "found": found,
                "annotated_roles": sorted(roles),
                "cited_work": bool(roles & set(CITED_WORK_ROLES)),
            }
        )
    return {
        "keys": len(rows),
        "found": sum(r["found"] for r in rows),
        "found_but_never_cited_work": sum(r["found"] and not r["cited_work"] for r in rows),
        "rows": rows,
    }


# --------------------------------------------------------------------------------------------- A/B/C


def note_texts(html_bytes: bytes | None) -> dict[str, str]:
    if html_bytes is None:
        return {}
    root = lxml_html.document_fromstring(html_bytes)
    out = {}
    for li in root.iter("li"):
        lid = li.get("id")
        if lid and lid.startswith("cite_note"):
            out[lid] = etree.tostring(li, method="text", encoding="unicode").lower()
    return out


def relocation(art: Article, ann: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    """Relocate each annotated cited-work DOI occurrence from three record forms (FROZEN_PROTOCOL.md 8)."""
    text, low = art.text, art.text.lower()
    notes = note_texts(art.html_bytes)
    pred = engine_predictions(doc)
    p_ids = pred.identifiers
    containers = {c["id"]: c for c in doc["containers"]}
    uses_by_container: dict[str, list[dict[str, Any]]] = {}
    for u in doc["uses"]:
        if u["container_id"]:
            uses_by_container.setdefault(u["container_id"], []).append(u)
    defs = [d for d in ann["definitions"] if at_ok(text, d["at"])]
    a_uses = [u for u in ann["uses"] if at_ok(text, u["at"])]
    out = {k: Counter() for k in ("A", "B", "C")}
    bytes_ = {k: 0 for k in ("A", "B", "C")}
    n = 0
    for a in ann["identifiers"]:
        if a["scheme"] != "doi" or a["role"] not in CITED_WORK_ROLES or not a.get("key"):
            continue
        if not at_ok(text, a["at"]) or not in_window(a["at"]["cp"], art.window):
            continue
        n += 1
        s, e = a["at"]["cp"], a["at"]["cp"] + len(a["at"]["quote"])
        home = min((d for d in defs if d["at"]["cp"] <= s), key=lambda d: s - d["at"]["cp"], default=None)
        note_want = home.get("render_note_id") if home else None
        uses_want = {
            u.get("render_ref_id")
            for u in a_uses
            if home and isinstance(u.get("binds_to"), dict) and u["binds_to"]["cp"] == home["at"]["cp"]
        } - {None}
        # A: DOI and revision URL only
        hits = [m.start() for m in re.finditer(re.escape(a["key"]), low)]
        out["A"]["source_unique" if len(hits) == 1 else ("source_ambiguous" if hits else "source_failed")] += 1
        if len(hits) == 1:
            out["A"][
                "source_correct" if s <= hits[0] < e or hits[0] <= s < hits[0] + len(a["key"]) else "source_wrong"
            ] += 1
        rnotes = [k for k, v in notes.items() if a["key"] in v]
        out["A"]["note_unique" if len(rnotes) == 1 else ("note_ambiguous" if rnotes else "note_failed")] += 1
        if len(rnotes) == 1 and note_want is not None:
            out["A"]["note_correct" if rnotes[0] == note_want else "note_wrong"] += 1
        bytes_["A"] += len(
            json.dumps(
                {"doi": a["key"], "revision": f"https://{art.wiki}.wikipedia.org/w/index.php?oldid={art.revision_id}"}
            )
        )
        # B and C share the engine's exact source anchor
        match = next((p for p in p_ids if p.data["scheme"] == "doi" and min(e, p.end) - max(s, p.start) > 0), None)
        rec = next((i for i in doc["identifiers"] if match and i["source"]["cp_start"] == match.start), None)
        for k in ("B", "C"):
            if match is None:
                out[k]["source_failed"] += 1
            else:
                out[k]["source_unique"] += 1
                out[k]["source_correct"] += 1
        if rec is not None:
            bytes_["B"] += len(json.dumps({"doi": a["key"], "revision": art.revision_id, "source": rec["source"]}))
        # C: render note and every use of the citing reference
        c = containers.get(rec["container_id"]) if rec and rec.get("container_id") else None
        got_note = c["render"]["region_id"] if c and c["render"]["state"] == "matched" else None
        if got_note is None:
            out["C"]["note_abstained"] += 1
        elif note_want is None:
            out["C"]["note_unverifiable"] += 1
        else:
            out["C"]["note_correct" if got_note == note_want else "note_wrong"] += 1
        got_uses = (
            {
                u["render"]["locator"]["element_id"]
                for u in uses_by_container.get(c["id"], [])
                if u["render"]["state"] == "matched" and u["render"].get("locator")
            }
            if c
            else set()
        )
        out["C"]["uses_expected"] += len(uses_want)
        out["C"]["uses_correct"] += len(uses_want & got_uses)
        out["C"]["uses_wrong"] += len(got_uses - uses_want)
        if rec is not None and c is not None:
            ledger = {
                "identifier": rec,
                "container": c,
                "uses": uses_by_container.get(c["id"], []),
                "markers": [m for m in doc["markers"] if m["container_id"] == c["id"]],
            }
            bytes_["C"] += len(json.dumps(ledger))
    return {"doi_occurrences": n, "counts": {k: dict(v) for k, v in out.items()}, "record_bytes": bytes_}


# --------------------------------------------------------------------------------------------- aggregate


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def ssum(path: tuple[str, ...]) -> int:
        total = 0
        for r in rows:
            v: Any = r
            for p in path:
                v = v[p]
            total += v
        return total

    out: dict[str, Any] = {"articles": len(rows)}
    for part in ("definitions", "units", "uses", "identifiers"):
        out[part] = prf(ssum((part, "tp")), ssum((part, "fp")), ssum((part, "fn")))
    ident = out["identifiers"]
    matched_targets = ssum(("identifiers", "role_total"))
    ident["key_errors"] = ssum(("identifiers", "key_errors"))
    ident["key_error_rate"] = ident["key_errors"] / matched_targets if matched_targets else None
    ident["promotions"] = ssum(("identifiers", "promotions"))
    ident["role_agreement"] = ssum(("identifiers", "role_agree")) / matched_targets if matched_targets else None
    b_ok, b_tot = ssum(("uses", "binding", "correct")), ssum(("uses", "binding", "total"))
    out["uses"]["binding_accuracy"] = b_ok / b_tot if b_tot else None
    out["uses"]["binding"] = {"correct": b_ok, "total": b_tot}
    rend = {k: ssum(("render", k)) for k in ("linkable", "engine_links", "correct", "false_attachments", "abstained")}
    rend["precision"] = rend["correct"] / rend["engine_links"] if rend["engine_links"] else None
    rend["coverage"] = rend["correct"] / rend["linkable"] if rend["linkable"] else None
    rend["false_attachments_allowed"] = rend["false_attachments"] - max(1, int(0.01 * rend["engine_links"]))
    out["render"] = rend
    conf: Counter[str] = Counter()
    for r in rows:
        conf.update(r["markers"]["confusion"])
    out["markers"] = {
        "confusion": dict(sorted(conf.items())),
        "fabricated_negatives": ssum(("markers", "fabricated_negatives")),
        "not_inspected": ssum(("markers", "not_inspected")),
    }
    out["denominators"] = {
        "identifiers": out["identifiers"]["tp"] + out["identifiers"]["fn"],
        "uses": out["uses"]["tp"] + out["uses"]["fn"],
        "definitions": out["definitions"]["tp"] + out["definitions"]["fn"],
        "render": rend["linkable"],
    }
    return out


def bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Article-cluster bootstrap: 95 % percentile intervals of the main ratios, resampling whole articles."""
    rng = random.Random(BOOTSTRAP_SEED)  # noqa: S311 - seeded resampling, not security
    keys = [
        ("identifiers", "precision"),
        ("identifiers", "recall"),
        ("uses", "precision"),
        ("uses", "recall"),
        ("definitions", "precision"),
        ("definitions", "recall"),
        ("render", "precision"),
        ("render", "coverage"),
    ]
    samples: dict[str, list[float]] = {f"{a}.{b}": [] for a, b in keys}
    if not rows:
        return {}
    for _ in range(BOOTSTRAP_RESAMPLES):
        agg = aggregate([rows[rng.randrange(len(rows))] for _ in rows])
        for a, b in keys:
            v = agg[a][b]
            if v is not None:
                samples[f"{a}.{b}"].append(v)
    out = {}
    for k, vals in samples.items():
        vals.sort()
        out[k] = [vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]] if vals else None
    return out


def gates(agg: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for name, (part, metric, bound) in GATES.items():
        value = agg[part][metric]
        if value is None:
            out[name] = {"value": None, "bound": bound, "passed": None, "note": "zero denominator"}
            continue
        passed = value <= bound if name in MAX_IS_BOUND or metric == "false_attachments_allowed" else value >= bound
        out[name] = {"value": value, "bound": bound, "passed": passed}
    short = {k: v for k, v in agg["denominators"].items() if v < MIN_DENOMINATORS[k]}
    out["minimum denominators"] = {"value": agg["denominators"], "bound": MIN_DENOMINATORS, "passed": not short}
    return out


def score(spec_path: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    result: dict[str, Any] = {"protocol": "FROZEN_PROTOCOL.md", "gates_frozen": GATES, "splits": {}}
    for split, entries in spec["splits"].items():
        per: dict[str, dict[str, list[Any]]] = {}
        for e in entries:
            art = load_bundle(base / e["bundle"])
            doc = json.loads((base / e["extraction"]).read_text(encoding="utf-8"))
            if doc["capture"]["revision_id"] != art.revision_id:
                raise SystemExit(f"{e['extraction']}: extraction is for another revision")
            for label in ("locked", "adjudicated"):
                path = e.get(label) or e["locked"]
                ann, problems = load_annotation(base / path, art)
                if problems:
                    raise SystemExit(f"{path}: {problems}")
                slot = per.setdefault(art.wiki, {}).setdefault(label, [])
                slot.append(
                    {
                        "engine": score_article(art, ann, engine_predictions(doc)),
                        "b1": score_article(art, ann, b1_predictions(art)),
                        "b0": b0(art, ann),
                        "abc": relocation(art, ann, doc),
                    }
                )
        out: dict[str, Any] = {}
        for wiki, labels in sorted(per.items()):
            out[wiki] = {}
            for label, rows in labels.items():
                eng = [r["engine"] for r in rows]
                agg = aggregate(eng)
                out[wiki][label] = {
                    "engine": agg,
                    "engine_bootstrap_95": bootstrap(eng),
                    "gates": gates(agg),
                    "b1": aggregate([r["b1"] for r in rows]),
                    "b0": {
                        "keys": sum(r["b0"]["keys"] for r in rows),
                        "found": sum(r["b0"]["found"] for r in rows),
                        "found_but_never_cited_work": sum(r["b0"]["found_but_never_cited_work"] for r in rows),
                    },
                    "abc": [r["abc"] for r in rows],
                    "per_article": rows,
                }
        result["splits"][split] = out
    return result


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "packets":
        packets(Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]])
    elif cmd == "lock":
        lock(Path(sys.argv[2]))
    elif cmd == "score":
        sys.stdout.write(json.dumps(score(Path(sys.argv[2])), ensure_ascii=False, indent=1, default=str) + "\n")
    else:
        raise SystemExit(f"unknown command {cmd!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
