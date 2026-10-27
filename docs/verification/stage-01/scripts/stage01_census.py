#!/usr/bin/env python3
"""CITERIFT Stage 01: census of Retraction Watch identifiers in Wikipedia external links (FEASIBILITY_REPORT §16).

Standard library only. Phases:

1. ``dump-scan``: offline. Reads the pinned Wikimedia SQL dumps of one wiki (externallinks, page) and the pinned
   Retraction Watch CSV, and lists every page with an external link to the DOI or PMID of a Retraction Watch record
   (the original paper or the notice). No request is sent to Wikipedia.
2. ``confirm``: live, through the throttled client of stage01_probe.py. Reads the current wikitext of each article
   found in phase 1 (50 pages per request) and records, per record, whether the identifier is still cited at that
   pinned revision and whether a {{Retracted}}-family template marks the citation.

``langmap`` maps article ids of one wiki to their counterpart titles in another wiki through the langlinks dump.

Dump files are verified against the sha1 that dumps.wikimedia.org publishes in the run's dumpstatus.json; dumps,
article text and the Retraction Watch CSV are never written to the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import urllib.parse
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_PROBE = Path(__file__).resolve().parent / "stage01_probe.py"
_spec = importlib.util.spec_from_file_location("stage01_probe", _PROBE)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {_PROBE}")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

DUMP_RUN = "20261001"
# sha1 published in https://dumps.wikimedia.org/<wiki>/20261001/dumpstatus.json
DUMP_SHA1 = {
    "arwiki-20261001-externallinks.sql.gz": "4dfe5a157f0d3b491f4c3a03871643e34f60ac78",
    "arwiki-20261001-page.sql.gz": "b3bae1b98bde409fd70ba9e34f919431466f3f90",
    "arwiki-20261001-langlinks.sql.gz": "fec05e630baa2e5dab9a0772a411d15cfd5a89eb",
    "enwiki-20261001-externallinks.sql.gz": "fa9292b70da69208e38a5599fc60f84d82e5c9b5",
    "enwiki-20261001-page.sql.gz": "08c19861e908c6f324ad091687ea19bff8d62bb4",
    "enwiki-20261001-langlinks.sql.gz": "39f698f4e6bfab15eb78c8824ea2dcda22f1234c",
}
MISSING_PMID = {"", "0"}
DOI_START = re.compile(r"10\.\d{4,9}/")
# Characters after which a DOI found inside a URL may end; "." and ")" are excluded because DOIs contain them and a
# figure or supplement DOI (10.1371/journal.pone.0012345.g001) must not count as the paper's DOI.
DOI_END = set("/?#&;")
FILE_SUFFIX = re.compile(r"(?:\.pdf|\.full|\.abstract|\.html?|\.xml|\.epdf)$")
PUBMED = (
    ("pubmed", re.compile(r"^https?://gov\.nih\.nlm\.ncbi\.pubmed\.$"), re.compile(r"^/(\d{1,9})/?$")),
    ("pubmed", re.compile(r"^https?://gov\.nih\.nlm\.ncbi\.www\.$"), re.compile(r"^/pubmed/(?:\?term=)?(\d{1,9})/?$")),
    (
        "europepmc",
        re.compile(r"^https?://org\.europepmc\.(?:www\.)?$"),
        re.compile(r"^/(?:abstract|article)/MED/(\d{1,9})/?$"),
    ),
)
DOI_RESOLVER = re.compile(r"^https?://org\.doi\.(?:dx\.|www\.)?$")
ESCAPES = {b"0": b"\0", b"n": b"\n", b"r": b"\r", b"t": b"\t", b"Z": b"\x1a"}
FIELD = re.compile(rb"NULL|-?[0-9.e+-]+|'(?:[^'\\]|\\.)*'")


# ------------------------------------------------------------------ dumps


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()  # noqa: S324 - matches the checksum published by dumps.wikimedia.org
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_dump(path: Path) -> dict[str, str]:
    expected = DUMP_SHA1.get(path.name)
    if expected is None:
        sys.exit(f"{path.name} is not a pinned dump file")
    actual = sha1_file(path)
    if actual != expected:
        sys.exit(f"{path} sha1 {actual} differs from the published {expected}")
    return {"file": path.name, "run": DUMP_RUN, "sha1": actual}


def sql_rows(path: Path, prefilter: str | None = None) -> Iterator[bytes]:
    """Lines of the dump that hold one row each ("(...),"); an optional grep -E prefilter keeps the scan fast."""
    gz = subprocess.Popen(["gzip", "-dc", str(path)], stdout=subprocess.PIPE)  # noqa: S603, S607
    if gz.stdout is None:
        raise RuntimeError("gzip produced no output pipe")
    source = gz.stdout
    grep = None
    if prefilter:
        grep = subprocess.Popen(  # noqa: S603
            ["grep", "-aE", prefilter],  # noqa: S607
            stdin=gz.stdout,
            stdout=subprocess.PIPE,
            env={"LC_ALL": "C"},
        )
        if grep.stdout is None:
            raise RuntimeError("grep produced no output pipe")
        source = grep.stdout
    for line in source:
        if line.startswith(b"("):
            yield line.rstrip(b"\n")
    if grep:
        grep.wait()
    if gz.wait() != 0:
        raise RuntimeError(f"gzip failed on {path}")


def unescape(value: bytes) -> bytes:
    return re.sub(rb"\\(.)", lambda m: ESCAPES.get(m.group(1), m.group(1)), value, flags=re.DOTALL)


def fields(line: bytes) -> list[str | None]:
    """Values of one dumped row: NULL as None, strings unescaped and decoded, numbers as text."""
    out: list[str | None] = []
    for m in FIELD.finditer(line, 1):
        tok = m.group(0)
        if tok == b"NULL":
            out.append(None)
        elif tok.startswith(b"'"):
            out.append(unescape(tok[1:-1]).decode("utf-8", "replace"))
        else:
            out.append(tok.decode())
    return out


def domain_host(index: str) -> tuple[str, str]:
    """('https', 'pubmed.ncbi.nlm.nih.gov') from 'https://gov.nih.nlm.ncbi.pubmed.'."""
    scheme, _, rest = index.partition("://")
    return scheme, ".".join(reversed(rest.rstrip(".").split(".")))


# ------------------------------------------------------------------ identifiers

Index = dict[str, list[tuple[str, str]]]


def rw_identifiers(rows: list[dict[str, str]]) -> tuple[Index, Index]:
    """DOI and PMID indexes: identifier -> [(record id, side)], side "original" or "notice"."""
    dois: Index = {}
    pmids: Index = {}
    for r in rows:
        for side, dcol, pcol in (
            ("original", "OriginalPaperDOI", "OriginalPaperPubMedID"),
            ("notice", "RetractionDOI", "RetractionPubMedID"),
        ):
            d = probe.norm_doi(r[dcol])
            if d not in probe.MISSING_DOI:
                dois.setdefault(d, []).append((r["Record ID"], side))
            p = r[pcol].strip()
            if p not in MISSING_PMID:
                pmids.setdefault(p, []).append((r["Record ID"], side))
    return dois, pmids


def dois_in_url(url: str, known: Index) -> list[str]:
    """Known DOIs that a URL contains, each ending at the end of the URL or before one of DOI_END."""
    text = url
    for _ in range(2):  # links may be encoded twice (%252F)
        text = urllib.parse.unquote(text)
    text = text.lower()
    found = []
    for m in DOI_START.finditer(text):
        tail = re.split(r"\s", text[m.start() :], maxsplit=1)[0]
        cands = [tail, FILE_SUFFIX.sub("", tail), tail.rstrip("/")]
        cands += [tail[:i] for i, ch in enumerate(tail) if ch in DOI_END]
        hit = next((c for c in sorted(set(cands), key=len, reverse=True) if c in known), None)
        if hit:
            found.append(hit)
    return found


def link_matches(index: str, path: str, dois: Index, pmids: Index) -> list[dict[str, str]]:
    out = []
    for kind, dom, pat in PUBMED:
        if dom.match(index):
            m = pat.match(path)
            if m and m.group(1) in pmids:
                out.append({"id_type": "pmid", "id": m.group(1), "link_kind": kind})
            return out
    scheme, host = domain_host(index)
    for d in dict.fromkeys(dois_in_url(f"{scheme}://{host}{path}", dois)):
        resolver = DOI_RESOLVER.match(index) is not None and urllib.parse.unquote(path).strip("/").lower() == d
        out.append({"id_type": "doi", "id": d, "link_kind": "doi_resolver" if resolver else "doi_in_url"})
    return out


# ------------------------------------------------------------------ phase 1


def dump_scan(csv_path: Path, wiki: str, externallinks: Path, page: Path) -> dict[str, Any]:
    rows = probe.rw_load(csv_path)
    by_id = {r["Record ID"]: r for r in rows}
    dois, pmids = rw_identifiers(rows)
    dumps = [check_dump(externallinks), check_dump(page)]
    links: dict[int, list[dict[str, str]]] = {}
    scanned = 0
    for line in sql_rows(externallinks, r"10\.[0-9]{4}|pubmed|europepmc"):
        f = fields(line)
        if len(f) != 4 or f[2] is None:
            continue
        scanned += 1
        for m in link_matches(f[2], f[3] or "", dois, pmids):
            links.setdefault(int(str(f[1])), []).append(m)
    pages: dict[int, dict[str, Any]] = {}
    for line in sql_rows(page):
        pid = int(line[1 : line.index(b",")])
        if pid in links:
            f = fields(line)
            pages[pid] = {"ns": int(str(f[1])), "title": str(f[2]).replace("_", " "), "redirect": f[3] == "1"}
            pages[pid]["latest_revid_in_dump"] = int(str(f[8]))
    out = []
    for pid in sorted(links):
        records: dict[str, dict[str, Any]] = {}
        for m in links[pid]:
            index = dois if m["id_type"] == "doi" else pmids
            for rid, side in index[m["id"]]:
                rec = records.setdefault(rid, {"record_id": rid, "nature": by_id[rid]["RetractionNature"], "via": []})
                via = {"side": side, **m}
                if via not in rec["via"]:
                    rec["via"].append(via)
        info = pages.get(pid, {"ns": None, "title": None, "redirect": None, "latest_revid_in_dump": None})
        out.append({"page_id": pid, **info, "records": sorted(records.values(), key=lambda r: int(r["record_id"]))})
    return {
        "wiki": wiki,
        "generated_at": probe.now(),
        "dumps": dumps,
        "retraction_watch": {"sha256": probe.RW_SOURCE["sha256"], "records": len(rows)},
        "index_sizes": {"dois": len(dois), "pmids": len(pmids)},
        "candidate_link_rows_scanned": scanned,
        "pages": out,
    }


def langmap(langlinks: Path, page_ids: set[int], lang: str) -> dict[str, Any]:
    dump = check_dump(langlinks)
    mapping: dict[str, str] = {}
    needle = f",'{lang}',".encode()
    for line in sql_rows(langlinks, needle.decode()):
        if needle not in line:
            continue
        pid = int(line[1 : line.index(b",")])
        if pid in page_ids:
            f = fields(line)
            if f[1] == lang:
                mapping[str(pid)] = str(f[2])
    return {"dump": dump, "lang": lang, "map": mapping}


def title_ids(page: Path, titles: set[str], ns: int = 0) -> dict[str, Any]:
    """Page id, redirect flag and dump revision of the given titles (spaces, not underscores) in namespace ns."""
    dump = check_dump(page)
    want = {t.replace(" ", "_") for t in titles}
    prefix = f",{ns},'".encode()
    found: dict[str, dict[str, Any]] = {}
    for line in sql_rows(page):
        if prefix not in line[:20]:
            continue
        f = fields(line)
        if f[1] == str(ns) and f[2] in want:
            found[str(f[2]).replace("_", " ")] = {
                "page_id": int(str(f[0])),
                "redirect": f[3] == "1",
                "latest_revid_in_dump": int(str(f[8])),
            }
    return {"dump": dump, "titles": found}


# ------------------------------------------------------------------ phase 2


PMID_PATTERNS = (
    r"\|\s*(?:pmid|بمد|بي إم آي دي)\s*=\s*{p}(?!\d)",
    r"pubmed(?:\.ncbi\.nlm\.nih\.gov|/)/?(?:\?term=)?{p}(?!\d)",
    r"europepmc\.org/(?:abstract|article)/MED/{p}(?!\d)",
    r"\{{\{{\s*pmid\s*\|\s*{p}(?!\d)",
)


def pmid_positions(content: str, pmid: str) -> list[int]:
    """Start positions of a |pmid= parameter (English or Arabic alias), a {{pmid}} template or a PubMed / Europe PMC
    URL with this PMID."""
    found = set()
    for pat in PMID_PATTERNS:
        found |= {m.start() for m in re.finditer(pat.format(p=re.escape(pmid)), content, re.IGNORECASE)}
    return sorted(found)


def marked_at(content: str, positions: list[int]) -> bool:
    """probe.marked for given citation positions: a {{Retracted}}-family template in the reference or directly after
    it on the same line."""
    for i in positions:
        start, end = probe.reference_span(content, i)
        stop = min(x for x in (content.find("\n", end), content.find("<ref", end), end + 300) if x != -1)
        names = re.findall(r"\{\{\s*([^|}\n]+?)\s*[|}]", content[start:stop])
        if any(n.strip().lower() in probe.RETRACTED_TEMPLATES for n in names):
            return True
    return False


def assess(content: str, record: dict[str, Any]) -> dict[str, Any]:
    """Whether the current wikitext cites the record's original paper or its notice, and whether it is marked."""
    out: dict[str, Any] = {"record_id": record["record_id"], "nature": record["nature"]}
    for side in ("original", "notice"):
        ids = [v for v in record["via"] if v["side"] == side]
        if not ids:
            continue
        dois = sorted({v["id"] for v in ids if v["id_type"] == "doi"})
        pm = sorted({v["id"] for v in ids if v["id_type"] == "pmid"})
        cited = [d for d in dois if probe.cited(content, d)] + [p for p in pm if pmid_positions(content, p)]
        present = [d for d in dois if probe.doi_positions(content, d)] + [p for p in pm if p in content]
        out[side] = {
            "identifiers": dois + pm,
            "cited_in_wikitext": cited,
            "identifier_text_present": present,
            "marked": any(probe.marked(content, d) for d in dois)
            or any(marked_at(content, pmid_positions(content, p)) for p in pm),
        }
    return out


def fetch_current(client: Any, wiki: str, page_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Current revision (ids, timestamp, content) of each page id, 50 per request; failures are recorded."""
    got: dict[int, dict[str, Any]] = {}
    for i in range(0, len(page_ids), 50):
        batch = page_ids[i : i + 50]
        params = {
            "prop": "revisions",
            "pageids": "|".join(map(str, batch)),
            "rvprop": "ids|timestamp|sha1|content",
            "rvslots": "main",
        }
        res = probe.wq(client, wiki, **params)
        if not probe.api_ok(res):
            for pid in batch:
                got[pid] = {"ok": False, "reason": "request_failed", "status": res["status"]}
            continue
        for p in res["body"]["query"].get("pages", []):
            pid = int(p.get("pageid", 0))
            if "missing" in p or "revisions" not in p:
                got[pid] = {"ok": False, "reason": "missing" if "missing" in p else "malformed_response"}
                continue
            rev = p["revisions"][0]
            got[pid] = {
                "ok": True,
                "title": p["title"],
                "ns": p["ns"],
                "revid": rev["revid"],
                "timestamp": rev["timestamp"],
                "sha1": rev["sha1"],
                "content": rev["slots"]["main"].get("content", ""),
                "retrieved_at": res["retrieved_at"],
            }
        for pid in batch:  # an id absent from a successful answer is unknown, never "not cited"
            got.setdefault(pid, {"ok": False, "reason": "absent_from_response"})
    return got


def retracted_templates(content: str) -> list[str]:
    names = re.findall(r"\{\{\s*([^|}\n]+?)\s*[|}]", content)
    return sorted({n.strip() for n in names if n.strip().lower() in probe.RETRACTED_TEMPLATES})


def confirm(client: Any, scan: dict[str, Any], namespaces: set[int]) -> dict[str, Any]:
    pages = [p for p in scan["pages"] if p["ns"] in namespaces and not p["redirect"]]
    current = fetch_current(client, scan["wiki"], [p["page_id"] for p in pages])
    rows = []
    for p in pages:
        cur = current[p["page_id"]]
        row: dict[str, Any] = {"page_id": p["page_id"], "title_in_dump": p["title"], "ok": cur["ok"]}
        if not cur["ok"]:
            row["reason"] = cur["reason"]
            rows.append(row)
            continue
        content = cur["content"]
        row.update({k: cur[k] for k in ("title", "revid", "timestamp", "sha1", "retrieved_at")})
        row["retracted_templates_on_page"] = retracted_templates(content)
        row["records"] = [assess(content, r) for r in p["records"]]
        rows.append(row)
    return {"wiki": scan["wiki"], "user_agent": probe.USER_AGENT, "run_at": probe.now(), "pages": rows}


def render(client: Any, confirmed: dict[str, Any], natures: set[str]) -> dict[str, Any]:
    """Rendered check (one parse of the pinned revision per article) of every cited original paper whose record has
    one of the given natures. A failed render is recorded as render_unavailable, never as an absent warning."""
    rows = []
    for page in confirmed["pages"]:
        todo = [
            r
            for r in page.get("records", [])
            if r["nature"] in natures and r.get("original", {}).get("cited_in_wikitext")
        ]
        if not page["ok"] or not todo:
            continue
        meta, text = probe.parse_html(client, confirmed["wiki"], page["revid"])
        for r in todo:
            row = {"title": page["title"], "record_id": r["record_id"], "nature": r["nature"], **meta}
            row["wikitext_marked"] = r["original"]["marked"]
            if text is None:
                rows.append({**row, "state": "render_unavailable"})
                continue
            refs: list[dict[str, Any]] = []
            for ident in r["original"]["cited_in_wikitext"]:
                doi, pmid = (ident, None) if ident.startswith("10.") else (None, ident)
                refs += [x for x in probe.rendered_references(text, doi, pmid) if x not in refs]
            location = "footnotes"
            if not refs:  # a citation in a bibliography list or in prose, outside the footnotes
                location = "outside_footnotes"
                for ident in r["original"]["cited_in_wikitext"]:
                    doi, pmid = (ident, None) if ident.startswith("10.") else (None, ident)
                    refs += [x for x in probe.rendered_other_items(text, doi, pmid) if x not in refs]
            state = probe.rendered_state(refs)
            rows.append({**row, "state": state, "location": location if refs else None, "references": refs})
    return {"wiki": confirmed["wiki"], "user_agent": probe.USER_AGENT, "run_at": probe.now(), "checks": rows}


# ------------------------------------------------------------------ cross-wiki divergence


def rw_record_ids(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """record id -> a record in the shape of a scan record, listing all of the original paper's RW identifiers."""
    out = {}
    for r in rows:
        via = []
        d = probe.norm_doi(r["OriginalPaperDOI"])
        if d not in probe.MISSING_DOI:
            via.append({"side": "original", "id_type": "doi", "id": d})
        pm = r["OriginalPaperPubMedID"].strip()
        if pm not in MISSING_PMID:
            via.append({"side": "original", "id_type": "pmid", "id": pm})
        out[r["Record ID"]] = {"record_id": r["Record ID"], "nature": r["RetractionNature"], "via": via}
    return out


def revision_near(
    client: Any, wiki: str, page_id: int, *, first: bool = False, at: str | None = None
) -> dict[str, Any]:
    """The first revision of a page, or its revision in force at timestamp `at` (None if the page did not exist)."""
    params = {
        "prop": "revisions",
        "pageids": str(page_id),
        "rvlimit": "1",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "rvdir": "newer" if first else "older",
    }
    if at is not None:
        params["rvstart"] = at
    res = probe.wq(client, wiki, **params)
    if not probe.api_ok(res):
        return {"ok": False, "reason": "request_failed", "status": res["status"]}
    pages = res["body"]["query"].get("pages", [])
    if not pages or "missing" in pages[0]:
        return {"ok": False, "reason": "missing"}
    revs = pages[0].get("revisions", [])
    if not revs:
        return {"ok": True, "exists": False}
    rev = revs[0]
    return {
        "ok": True,
        "exists": True,
        "revid": rev["revid"],
        "timestamp": rev["timestamp"],
        "content": rev["slots"]["main"].get("content", ""),
    }


def pair_category(src: dict[str, Any], dst: dict[str, Any] | None) -> str:
    if dst is None:
        return "unknown_target_unavailable"
    if not dst["cited_in_wikitext"]:
        return "not_carried"
    return {
        (True, True): "carried_marked_both",
        (True, False): "carried_marked_source_only",
        (False, True): "carried_marked_target_only",
        (False, False): "carried_marked_neither",
    }[(bool(src["marked"]), bool(dst["marked"]))]


def crosswiki_census(
    client: Any,
    rows: list[dict[str, str]],
    scan: dict[str, Any],
    lmap: dict[str, Any],
    dst: str,
    natures: set[str],
    history: bool,
) -> dict[str, Any]:
    """For every source article whose external links cite a record of the given natures: is the record still cited
    there now, does the linked target article cite it (by any of the record's RW identifiers), and is each citation
    marked. With history, each source-cited / target-not-cited pair also gets the target's first revision and the
    source revision in force at that moment, to tell "never carried" from "carried, then removed"."""
    records = rw_record_ids(rows)
    src_pages = [
        p
        for p in scan["pages"]
        if p["ns"] == 0
        and not p["redirect"]
        and any(r["nature"] in natures and any(v["side"] == "original" for v in r["via"]) for r in p["records"])
    ]
    linked = [p for p in src_pages if str(p["page_id"]) in lmap["map"]]
    targets = lmap["targets"]["titles"]
    src_now = fetch_current(client, scan["wiki"], [p["page_id"] for p in linked])
    dst_ids = sorted(
        {
            targets[t]["page_id"]
            for t in (lmap["map"][str(p["page_id"])] for p in linked)
            if t in targets and not targets[t]["redirect"]
        }
    )
    dst_now = fetch_current(client, dst, dst_ids)
    pairs = []
    for p in linked:
        title = lmap["map"][str(p["page_id"])]
        cur = src_now[p["page_id"]]
        tgt = targets.get(title)
        base: dict[str, Any] = {"source_page_id": p["page_id"], "source_title": p["title"], "target_title": title}
        if not cur["ok"]:
            pairs.append({**base, "status": "source_fetch_failed", "reason": cur["reason"]})
            continue
        base.update({"source_revid": cur["revid"], "source_timestamp": cur["timestamp"]})
        if tgt is None:
            status, dcur = "target_not_in_dump", None
        elif tgt["redirect"]:
            status, dcur = "target_is_redirect", None
        else:
            dcur = dst_now[tgt["page_id"]]
            status = "ok" if dcur["ok"] else "target_fetch_failed"
            base["target_page_id"] = tgt["page_id"]
            if dcur["ok"]:
                base.update({"target_revid": dcur["revid"], "target_timestamp": dcur["timestamp"]})
        for r in p["records"]:
            if r["nature"] not in natures or not any(v["side"] == "original" for v in r["via"]):
                continue
            full = records[r["record_id"]]
            src_a = assess(cur["content"], full)["original"]
            row = {**base, "record_id": r["record_id"], "nature": r["nature"], "status": status, "source": src_a}
            if not src_a["cited_in_wikitext"]:
                row["category"] = "source_no_longer_cites"
            elif status != "ok" or dcur is None:
                row["category"] = "unknown_target_unavailable"
            else:
                row["target"] = assess(dcur["content"], full)["original"]
                row["category"] = pair_category(src_a, row["target"])
            pairs.append(row)
    if history:
        for tid in sorted({r["target_page_id"] for r in pairs if r.get("category") == "not_carried"}):
            first = revision_near(client, dst, tid, first=True)
            src_at = None
            for r in (r for r in pairs if r.get("target_page_id") == tid and r["category"] == "not_carried"):
                full = records[r["record_id"]]
                h: dict[str, Any] = {"target_first": {k: v for k, v in first.items() if k != "content"}}
                if first.get("exists"):
                    h["target_first_cites"] = bool(assess(first["content"], full)["original"]["cited_in_wikitext"])
                    if src_at is None:
                        src_at = revision_near(client, scan["wiki"], r["source_page_id"], at=first["timestamp"])
                    h["source_at_target_creation"] = {k: v for k, v in src_at.items() if k != "content"}
                    if src_at.get("exists"):
                        h["source_cited_at_target_creation"] = bool(
                            assess(src_at["content"], full)["original"]["cited_in_wikitext"]
                        )
                r["history"] = h
            src_at = None
    return {
        "source_wiki": scan["wiki"],
        "target_wiki": dst,
        "natures": sorted(natures),
        "user_agent": probe.USER_AGENT,
        "run_at": probe.now(),
        "source_articles_citing": len(src_pages),
        "source_articles_with_target_link": len(linked),
        "pairs": pairs,
    }


# ------------------------------------------------------------------ summaries


def summarize_scan(scan: dict[str, Any]) -> dict[str, Any]:
    ns0 = [p for p in scan["pages"] if p["ns"] == 0 and not p["redirect"]]
    by_nature: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    records: dict[str, set[str]] = {}
    for p in ns0:
        for r in p["records"]:
            sides = {v["side"] for v in r["via"]}
            for s in sides:
                records.setdefault(s, set()).add(r["record_id"])
            by_nature[r["nature"] + (" (original)" if "original" in sides else " (notice only)")] += 1
            kinds.update(v["link_kind"] for v in r["via"])
    return {
        "pages_any_namespace": len(scan["pages"]),
        "pages_by_namespace": dict(Counter(str(p["ns"]) for p in scan["pages"])),
        "articles": len(ns0),
        "article_record_pairs_by_nature": dict(by_nature),
        "link_kinds_in_articles": dict(kinds),
        "distinct_records_original": len(records.get("original", set())),
        "distinct_records_notice": len(records.get("notice", set())),
    }


def work_key(rec: dict[str, Any]) -> str:
    """One key per paper: its RW original DOI, else its PMID (several RW records can describe one paper)."""
    ids = {v["id_type"]: v["id"] for v in rec["via"]}
    return ids.get("doi") or f"pmid:{ids.get('pmid', '?')}"


def summarize(rows: list[dict[str, str]], w: dict[str, Any], en_scan: dict[str, Any]) -> dict[str, Any]:
    """Counts behind FEASIBILITY_REPORT.md §16, from the census files (w: name -> parsed JSON)."""
    recs = rw_record_ids(rows)
    retr = [r for r in recs.values() if r["nature"] == "Retraction"]
    denominators = {
        "rw_records": len(rows),
        "retraction_records": len(retr),
        "retraction_records_with_original_doi_or_pmid": sum(bool(r["via"]) for r in retr),
        "retraction_papers_with_original_doi_or_pmid": len({work_key(r) for r in retr if r["via"]}),
    }
    pairs: dict[str, list[tuple[str, str]]] = {}
    marked: dict[str, int] = Counter()
    failed = [p for p in w["ar_confirm"]["pages"] if not p["ok"]]
    link_only: Counter[str] = Counter()
    for page in w["ar_confirm"]["pages"]:
        for r in page.get("records", []):
            o = r.get("original")
            if not o:
                continue
            if o["cited_in_wikitext"]:
                pairs.setdefault(r["nature"], []).append((page["title"], r["record_id"]))
                marked[r["nature"]] += bool(o["marked"])
            else:
                link_only[r["nature"]] += 1
    ar = {
        nature: {
            "article_record_pairs": len(v),
            "articles": len({t for t, _ in v}),
            "records": len({rid for _, rid in v}),
            "papers": len({work_key(recs[rid]) for _, rid in v}),
            "pairs_marked_in_wikitext": marked[nature],
        }
        for nature, v in sorted(pairs.items())
    }
    render_states: dict[str, Counter[str]] = {}
    unwarned: dict[str, set[str]] = {}
    for c in w["ar_render"]["checks"]:
        render_states.setdefault(c["nature"], Counter())[c["state"]] += 1
        if c["state"] in {
            "no_warning_text_in_inspected_rendered_reference",
            "missing_template_link_only_in_rendered_reference",
        }:
            unwarned.setdefault(c["nature"], set()).add(c["title"])
    cross = {}
    for name in ("crosswiki_en_to_ar", "crosswiki_ar_to_en"):
        x = w[name]
        cats: Counter[str] = Counter(r.get("category", r["status"]) for r in x["pairs"])
        hist: Counter[str] = Counter()
        for r in x["pairs"]:
            h = r.get("history")
            if h is None:
                continue
            if not h["target_first"].get("ok"):
                hist["target_first_revision_unavailable"] += 1
            elif h.get("target_first_cites"):
                hist["target_cited_at_creation_then_removed"] += 1
            elif not h["source_at_target_creation"].get("ok"):
                hist["source_revision_unavailable"] += 1
            elif "source_cited_at_target_creation" not in h:
                hist["source_article_not_yet_created"] += 1
            elif h["source_cited_at_target_creation"]:
                hist["source_cited_when_target_was_created_target_first_revision_did_not"] += 1
            else:
                hist["source_added_it_after_target_was_created"] += 1
        cross[name] = {
            "source_articles_citing": x["source_articles_citing"],
            "source_articles_with_target_link": x["source_articles_with_target_link"],
            "pair_categories": dict(cats),
            "papers_by_category": {
                k: len({work_key(recs[r["record_id"]]) for r in x["pairs"] if r.get("category") == k})
                for k in cats
                if k in {r.get("category") for r in x["pairs"]}
            },
            "not_carried_history": dict(hist),
        }
    ar_state = {(c["title"], c["record_id"]): c["state"] for c in w["ar_render"]["checks"]}
    for name, ar_side in (("crosswiki_en_to_ar", "target_title"), ("crosswiki_ar_to_en", "source_title")):
        joined: Counter[str] = Counter(
            f"{r['category']} / ar render: {ar_state.get((r[ar_side], r['record_id']), 'not_in_ar_census')}"
            for r in w[name]["pairs"]
            if r.get("category", "").startswith("carried")
        )
        cross[name]["carried_pairs_by_ar_render_state"] = dict(sorted(joined.items()))
        removed = [r for r in w[name]["pairs"] if (r.get("history") or {}).get("target_first_cites")]
        cross[name]["removed_from_target_after_creation"] = {
            "pairs": len(removed),
            "articles": len({r["target_title"] for r in removed}),
            "papers": len({work_key(recs[r["record_id"]]) for r in removed}),
        }
    return {
        "generated_from": sorted(w),
        "denominators": denominators,
        "ar_dump_scan": w["ar_scan"]["summary"],
        "ar_confirmed_cited": ar,
        "ar_confirm_failures": len(failed),
        "ar_linked_in_dump_but_not_cited_in_current_wikitext": dict(link_only),
        "ar_render_states": {k: dict(v) for k, v in render_states.items()},
        "ar_articles_with_an_unwarned_rendered_citation": {k: len(v) for k, v in unwarned.items()},
        "en_dump_scan": summarize_scan(en_scan),
        "crosswiki": cross,
    }


def crosscheck(discovery: list[dict[str, Any]], scans: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compare the dump scan with the live M1/M2 discovery of the purposive set (FEASIBILITY_REPORT.md §5.4)."""
    found: dict[tuple[str, str], set[str]] = {}
    for wiki, scan in scans.items():
        for p in scan["pages"]:
            if p["ns"] == 0 and not p["redirect"]:
                for r in p["records"]:
                    for v in r["via"]:
                        if v["id_type"] == "doi" and v["side"] == "original":
                            found.setdefault((wiki, v["id"]), set()).add(p["title"])
    rows = []
    for d in discovery:
        confirmed = {o["title"] for o in d["observations"] if o.get("confirmed")}
        dump = found.get((d["wiki"], probe.norm_doi(d["doi"])), set())
        rows.append(
            {
                "wiki": d["wiki"],
                "doi": d["doi"],
                "confirmed_by_api_2026_10_26": len(confirmed),
                "in_dump_2026_10_01": len(dump),
                "confirmed_not_in_dump": sorted(confirmed - dump),
                "in_dump_not_confirmed": sorted(dump - confirmed),
            }
        )
    agree = sum(not r["confirmed_not_in_dump"] and not r["in_dump_not_confirmed"] for r in rows)
    return {"pairs": len(rows), "identical_article_sets": agree, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--cache", type=Path, default=Path(".stage01-cache"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("dump-scan")
    s.add_argument("--csv", type=Path, required=True)
    s.add_argument("--wiki", required=True)
    s.add_argument("--externallinks", type=Path, required=True)
    s.add_argument("--page", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("confirm")
    c.add_argument("--scan", type=Path, required=True)
    c.add_argument("--namespaces", default="0")
    c.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("render")
    r.add_argument("--confirmed", type=Path, required=True)
    r.add_argument("--natures", default="Retraction")
    r.add_argument("--out", type=Path, required=True)
    x = sub.add_parser("crosswiki")
    x.add_argument("--csv", type=Path, required=True)
    x.add_argument("--scan", type=Path, required=True, help="dump scan of the source wiki")
    x.add_argument("--langmap", type=Path, required=True)
    x.add_argument("--dst", required=True)
    x.add_argument("--natures", default="Retraction")
    x.add_argument("--history", action="store_true")
    x.add_argument("--out", type=Path, required=True)
    z = sub.add_parser("summarize")
    z.add_argument("--csv", type=Path, required=True)
    z.add_argument("--dir", type=Path, required=True)
    z.add_argument("--en-scan", type=Path, required=True)
    z.add_argument("--out", type=Path, required=True)
    k = sub.add_parser("crosscheck")
    k.add_argument("--discovery", type=Path, required=True)
    k.add_argument("--ar-scan", type=Path, required=True)
    k.add_argument("--en-scan", type=Path, required=True)
    k.add_argument("--out", type=Path, required=True)
    m = sub.add_parser("langmap")
    m.add_argument("--scan", type=Path, required=True)
    m.add_argument("--langlinks", type=Path, required=True)
    m.add_argument("--lang", required=True)
    m.add_argument("--target-page", type=Path, required=True, help="page dump of the target wiki")
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "dump-scan":
        scan = dump_scan(a.csv, a.wiki, a.externallinks, a.page)
        scan["summary"] = summarize_scan(scan)
        probe.write(a.out, scan)
        print(json.dumps(scan["summary"], indent=1))
    elif a.cmd == "confirm":
        scan = json.loads(a.scan.read_text(encoding="utf-8"))
        ns = {int(x) for x in a.namespaces.split(",")}
        probe.write(a.out, confirm(probe.Client(a.cache), scan, ns))
    elif a.cmd == "crosswiki":
        scan = json.loads(a.scan.read_text(encoding="utf-8"))
        lmap = json.loads(a.langmap.read_text(encoding="utf-8"))
        natures = set(a.natures.split(","))
        out = crosswiki_census(probe.Client(a.cache), probe.rw_load(a.csv), scan, lmap, a.dst, natures, a.history)
        probe.write(a.out, out)
    elif a.cmd == "summarize":
        names = ("ar_scan", "ar_confirm", "ar_render", "crosswiki_en_to_ar", "crosswiki_ar_to_en")
        w = {n: json.loads((a.dir / f"{n}.json").read_text(encoding="utf-8")) for n in names}
        en_scan = json.loads(a.en_scan.read_text(encoding="utf-8"))
        out = summarize(probe.rw_load(a.csv), w, en_scan)
        probe.write(a.out, out)
        print(json.dumps(out, indent=1, ensure_ascii=False))
    elif a.cmd == "crosscheck":
        scans = {w: json.loads(f.read_text(encoding="utf-8")) for w, f in (("ar", a.ar_scan), ("en", a.en_scan))}
        out = crosscheck(json.loads(a.discovery.read_text(encoding="utf-8"))["results"], scans)
        probe.write(a.out, out)
        print(out["identical_article_sets"], "of", out["pairs"], "identical")
    elif a.cmd == "render":
        confirmed = json.loads(a.confirmed.read_text(encoding="utf-8"))
        probe.write(a.out, render(probe.Client(a.cache), confirmed, set(a.natures.split(","))))
    else:
        scan = json.loads(a.scan.read_text(encoding="utf-8"))
        ids = {p["page_id"] for p in scan["pages"] if p["ns"] == 0 and not p["redirect"]}
        lm = langmap(a.langlinks, ids, a.lang)
        lm["targets"] = title_ids(a.target_page, set(lm["map"].values()))
        probe.write(a.out, lm)
        print(len(lm["map"]), "linked;", len(lm["targets"]["titles"]), "targets found in the dump")
    return 0


if __name__ == "__main__":
    sys.exit(main())
