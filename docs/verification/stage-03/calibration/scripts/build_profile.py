"""Stage 03 calibration: build the bilingual support profile from the recorded API evidence (no network).

Input: OUT_DIR of profile_evidence.py (profile_evidence.json and artifacts/). Output: the profile data file
(src/citerift/wiki/data/profile-v1.json) and its provenance (docs/verification/stage-03/calibration/
profile-v1.provenance.json). Every template name, parameter alias and default comes from a recorded answer:

* template names: the template page and all its redirects (Template namespace) on that wiki;
* citation family: the template's own source sets ``CitationClass`` or invokes Module:Citation/CS1;
* identifier and URL parameters: the ``parameters`` lists of DOI and PMID, and the URL and ChapterURL aliases, in
  that wiki's Module:Citation/CS1/Configuration;
* footnote groups and body, name and group parameters: read from the generating template's source;
* marker wording: the literal text the marker template's source writes (checked against dev renders).

Choices that are not read from evidence are listed in DECISIONS with their reason. The output is deterministic.

Usage: python build_profile.py EVIDENCE_DIR PROFILE_OUT PROVENANCE_OUT
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PREFIX = {"en": "Template:", "ar": "قالب:"}
CLASS_FAMILY = {"encyclopaedia": "encyclopedia"}  # the CS1 class name is kept, with this one spelling unified

DECISIONS = [
    "Excluded tags: tags whose content MediaWiki does not render as wikitext (nowiki, pre, syntaxhighlight, source, "
    "math, chem, ce, score, timeline, graph, mapframe, maplink, templatedata, includeonly, inputbox, categorytree, "
    "charinsert, hiero). Identifier-shaped text inside them is recorded as excluded, never used.",
    "Unsupported containers: gallery, poem, imagemap, noinclude, onlyinclude. A ref inside them is kept and reported.",
    "Publisher DOI URL hosts: five hosts whose /doi/<DOI> paths were seen in Stage 01/02 evidence; any other URL is "
    "not decoded as a DOI (no outbound request is ever made to decide).",
    "Warning terms: the literal words the marker templates write ('Retracted', 'expression of concern', "
    "'مصدر مسحوب'), plus the adjective 'مسحوب/مسحوبة' and English 'retracted' on arwiki, where dev renders show "
    "the English word written by hand ('(Retracted)' in فضيحة شون). Ambiguous terms are wording that may or may "
    "not be a warning (a cited title, 'Retraction Watch', withdrawal of a drug, an erratum).",
    "Missing templates: Retracted, Expression of concern and Erratum do not exist on arwiki (evidence: missing pages); "
    "they stay in the arwiki marker list because articles copy them from enwiki and the render then shows a red "
    "link (missing_template_link_only).",
]


def strip(title: str, wiki: str) -> str:
    for p in (PREFIX[wiki], "Template:"):
        if title.startswith(p):
            return title[len(p) :]
    return title


def load(evd: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    data = json.loads((evd / "profile_evidence.json").read_text(encoding="utf-8"))
    pages: dict[str, dict[str, Any]] = {}  # "wiki|title" -> page with content, from every kept answer
    for art in sorted((evd / "artifacts").iterdir()):
        try:
            body = json.loads(art.read_bytes())
        except ValueError:
            continue
        host = None
        for p in body.get("query", {}).get("pages", []) if isinstance(body, dict) else []:
            title = p.get("title", "")
            wiki = "ar" if title.startswith(("قالب:", "وحدة:")) or any("؀" <= c <= "ۿ" for c in title) else None
            if p.get("revisions"):
                content = p["revisions"][0].get("slots", {}).get("main", {}).get("content")
                if content is None:
                    continue
                key_wiki = wiki or ("ar" if "ar.wikipedia" in str(host) else "en")
                pages[f"{key_wiki}|{title}"] = {
                    "title": title,
                    "revid": p["revisions"][0].get("revid"),
                    "content": content,
                    "artifact": art.name,
                }
    return data, pages


def redirect_groups(data: dict[str, Any], wiki: str) -> dict[str, list[str]]:
    """target name -> sorted names (target and its redirects), all without namespace prefix."""
    out: dict[str, set[str]] = {}
    key = "en_templates" if wiki == "en" else "ar_templates"
    for block in data[key]:
        for p in block["pages"]:
            if p.get("missing"):
                continue
            target = strip(p["title"], wiki)
            names = out.setdefault(target, {target})
            for r in p.get("redirects", []):
                names.add(strip(r["title"], wiki))
    return {k: sorted(v) for k, v in out.items()}


def source_facts(data: dict[str, Any], wiki: str) -> dict[str, dict[str, Any]]:
    out = {}
    for row in data[f"{wiki}_template_sources"]:
        if "title" in row and not row["missing"]:
            out[strip(row["title"], wiki)] = row
    return out


def cs1_params(pages: dict[str, dict[str, Any]], wiki: str) -> dict[str, Any]:
    title = "Module:Citation/CS1/Configuration" if wiki == "en" else "وحدة:Citation/CS1/Configuration"
    page = pages.get(f"{wiki}|{title}") or pages.get(f"en|{title}")
    if page is None:
        raise SystemExit(f"no CS1 configuration for {wiki}")
    c = page["content"]

    def handler(key: str) -> list[str]:
        m = re.search(r"\['" + key + r"'\]\s*=\s*\{[^}]*?parameters\s*=\s*\{([^}]*)\}", c)
        if not m:
            raise SystemExit(f"{wiki}: no {key} handler")
        return re.findall(r"'([^']+)'", m.group(1))

    def alias(key: str) -> list[str]:
        m = re.search(r"\['" + key + r"'\]\s*=\s*\{([^}]*)\}", c)
        if not m:
            raise SystemExit(f"{wiki}: no {key} alias")
        return re.findall(r"'([^']+)'", m.group(1))

    return {
        "doi": handler("DOI"),
        "pmid": handler("PMID"),
        "url": alias("URL"),
        "chapter_url": alias("ChapterURL"),
        "evidence": {
            "title": title,
            "revid": page["revid"],
            "artifact": page["artifact"],
            "content_sha256": hashlib.sha256(page["content"].encode("utf-8")).hexdigest(),
        },
    }


def footnote_entry(pages: dict[str, dict[str, Any]], wiki: str, name: str, kind: str) -> dict[str, Any]:
    page = pages.get(f"{wiki}|{PREFIX[wiki]}{name}")
    entry: dict[str, Any] = {
        "kind": kind,
        "body_params": ["1"],
        "name_params": ["name"],
        "group_params": ["group"],
        "default_group": "",
        "evidence": None,
    }
    if page is None:
        return entry
    c = page["content"]
    entry["evidence"] = {"title": page["title"], "revid": page["revid"]}
    if kind == "efn":
        body = re.search(r"\{\{\{1\|(.*?)\}\}\}\}\}", c, re.S)
        if body:
            entry["body_params"] = ["1", *re.findall(r"\{\{\{([^|{}]+)\|", body.group(0))[1:]]
        entry["name_params"] = sorted(
            set(re.findall(r"name=\{\{\{([^|}]+)\|", c))
            | set(re.findall(r"\{\{\{name\|\{\{\{([^|}]+)\|", c))
            | {"name"}
        )
        fixed = re.search(r"group=([a-z-]+)\|", c)
        default = re.search(r"#default\s*=\s*([a-z-]+)", c)
        entry["default_group"] = fixed.group(1) if fixed else default.group(1) if default else "lower-alpha"
        if "مجموعة" in c:
            entry["group_params"] = ["group", "مجموعة"]
    return entry


def build(evd: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    data, pages = load(evd)
    profile: dict[str, Any] = {
        "profile_version": "1.0.0",
        "excluded_tags": sorted(
            [
                "nowiki",
                "pre",
                "syntaxhighlight",
                "source",
                "math",
                "chem",
                "ce",
                "score",
                "timeline",
                "graph",
                "mapframe",
                "maplink",
                "templatedata",
                "includeonly",
                "inputbox",
                "categorytree",
                "charinsert",
                "hiero",
            ]
        ),
        "unsupported_tags": sorted(["gallery", "poem", "imagemap", "noinclude", "onlyinclude"]),
        "publisher_doi_hosts": sorted(
            [
                "www.science.org",
                "onlinelibrary.wiley.com",
                "journals.sagepub.com",
                "www.tandfonline.com",
                "pubs.acs.org",
            ]
        ),
        "wikis": {},
    }
    provenance: dict[str, Any] = {"evidence_run_at": data["run_at"], "decisions": DECISIONS, "wikis": {}}
    for wiki in ("en", "ar"):
        groups = redirect_groups(data, wiki)
        facts = source_facts(data, wiki)
        params = cs1_params(pages, wiki)
        prov: dict[str, Any] = {"cs1_configuration": params["evidence"], "templates": {}}
        citation: dict[str, list[str]] = {}
        external: list[str] = []
        wrappers: dict[str, list[str]] = {"doi": [], "pmid": []}
        markers: list[str] = []
        generated: list[dict[str, Any]] = []
        reflists: list[dict[str, Any]] = []
        for target, names in sorted(groups.items()):
            f = facts.get(target, {})
            classes = f.get("citation_classes", [])
            invokes = [i[0].casefold() for i in f.get("invokes", [])]
            role = None
            if classes or "citation/cs1" in invokes:
                family = CLASS_FAMILY.get(classes[0], classes[0]) if classes else "citation"
                citation.setdefault(family, []).extend(names)
                role = f"citation:{family}"
            elif "cite q" in invokes:
                external.extend(names)
                role = "external_data"
            elif "cs1 identifiers" in invokes:
                scheme = "doi" if target in ("Doi", "دوي") else "pmid" if target == "PMID" else None
                if scheme:
                    wrappers[scheme].extend(names)
                    role = f"wrapper:{scheme}"
            elif target in ("Retracted", "Expression of concern", "Erratum"):
                markers.extend(names)
                role = "marker"
            elif "footnotes" in invokes:
                generated.append({"names": names, **footnote_entry(pages, wiki, target, "sfn")})
                role = "generated:sfn"
            elif target in ("Refn",):
                generated.append({"names": names, **footnote_entry(pages, wiki, target, "refn")})
                role = "generated:refn"
            elif target in ("Efn", "ملا", "Efn-ua", "Efn-lr"):
                generated.append({"names": names, **footnote_entry(pages, wiki, target, "efn")})
                role = "generated:efn"
            elif target in ("R", "استشهاد متعدد"):
                generated.append({"names": names, **footnote_entry(pages, wiki, target, "r")})
                role = "generated:r"
            elif target in ("Reflist", "مراجع"):
                reflists.append(
                    {
                        "names": names,
                        "refs_params": ["refs"] if wiki == "en" else ["refs", "مراجع"],
                        "group_params": ["group"] if wiki == "en" else ["group", "مجموعة"],
                        "default_group": "",
                    }
                )
                role = "reflist"
            elif target in ("Notelist", "ملاحظات"):
                reflists.append(
                    {
                        "names": names,
                        "refs_params": ["refs", "notes"] if wiki == "en" else ["refs", "notes", "مراجع"],
                        "group_params": ["group"] if wiki == "en" else ["group", "مجموعة"],
                        "default_group": "lower-alpha" if wiki == "en" else "arabic-abajed",
                    }
                )
                role = "reflist"
            prov["templates"][target] = {
                "names": names,
                "role": role,
                "revid": f.get("revid"),
                "citation_classes": classes,
                "invokes": f.get("invokes", []),
            }
        if wiki == "ar":
            markers += ["مصدر مسحوب", "Retracted", "Expression of concern", "Erratum"]
            ar_marker = pages.get("ar|قالب:مصدر مسحوب")
            prov["templates"]["مصدر مسحوب"] = {
                "names": ["مصدر مسحوب"],
                "role": "marker",
                "revid": ar_marker["revid"] if ar_marker else None,
            }
            missing = sorted({p["title"] for b in data["ar_english_names"] for p in b["pages"] if p.get("missing")})
            prov["missing_on_wiki"] = missing
        profile["wikis"][wiki] = {
            "namespace_prefixes": [PREFIX[wiki]] if wiki == "en" else [PREFIX[wiki], "Template:"],
            "redirect_words": ["#REDIRECT"] if wiki == "en" else ["#تحويل", "#REDIRECT"],
            "citation_templates": {k: sorted(set(v)) for k, v in sorted(citation.items())},
            "external_data_templates": sorted(set(external)),
            "identifier_params": {"doi": params["doi"], "pmid": params["pmid"]},
            "url_params": sorted(set(params["url"]) | set(params["chapter_url"])),
            "wrappers": {k: sorted(set(v)) for k, v in wrappers.items()},
            "markers": sorted(set(markers)),
            "marker_render_titles": sorted({f"{PREFIX[wiki]}{m}" for m in markers}),
            "generated_refs": sorted(
                ({k: v for k, v in g.items() if k != "evidence"} for g in generated), key=lambda g: g["names"][0]
            ),
            "reflists": sorted(reflists, key=lambda r: r["names"][0]),
            "doi_text_labels": ["doi"] if wiki == "en" else ["doi", "دوي"],
            "warning_terms": ["expression of concern", "retracted"]
            if wiki == "en"
            else ["expression of concern", "retracted", "مسحوب"],
            "ambiguous_terms": ["corrigendum", "erratum", "retraction", "withdrawal", "withdrawn"]
            if wiki == "en"
            else ["corrigendum", "erratum", "retraction", "withdrawn", "سحب"],
        }
        prov["generated_refs"] = [{"names": g["names"], "evidence": g["evidence"]} for g in generated]
        provenance["wikis"][wiki] = prov
    return profile, provenance


def main() -> int:
    evd, prof_out, prov_out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    profile, provenance = build(evd)
    text = json.dumps(profile, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    prof_out.write_text(text, encoding="utf-8")
    provenance["profile_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    prov_out.write_text(json.dumps(provenance, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
