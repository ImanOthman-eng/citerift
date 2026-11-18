"""Stage 04 exposure manifest, version 2: the corrective cycle after the failed gate 04-I (owner decision D-071,
section 13). Derived from the Step 12 builder (``freeze/exposure/build_exposure_manifest.py``, kept unchanged with its
manifest); the differences are the campaign source, the corrective identifiers block and the superseded-manifest pin.

Usage (from the repository root):

    python -I docs/verification/stage-04/freeze-2/exposure/build_exposure_manifest.py \
        --out docs/verification/stage-04/freeze-2/exposure/EXPOSURE_MANIFEST.json

It lists, at article level (wiki plus page id, or wiki plus normalised title when no page id is recorded), every
Wikipedia article that the project examined before the Stage 04 freeze and that therefore may not enter the final
evaluation frame:

- ``S03-BUNDLE``: every tracked Stage 03 capture bundle (``capture.json``), including Stage 03 challenge, reserve
  and holdout bundles and the Stage 03 fixtures (all are design-exposed for Stage 04);
- ``S04-DEV-232``: the 232 development revisions measured in Step 9 (``dev_measurements.json``);
- ``S04-REF``: bundles named by Stage 04 code, tests or evidence (Steps 8 to 12, the vertical slice);
- ``S03-ATTEMPTED``: articles Stage 03 selected and attempted (``capture_states*.json``), with or without a bundle;
- ``S03-DEV-TITLE``: the Stage 03 development selection (``dev_selection*.json``), some known only by title;
- ``S01-PURPOSIVE``: Stage 01 purposive discovery observations (wiki, page id, revision) and ``S01-PURPOSIVE-HITS``:
  the titles its searches returned;
- ``S01-EVIDENCE``: Stage 01 evidence-manifest cases;
- ``S04-CAMPAIGN-80`` (new): the 80 articles of the failed Step 14 campaign (``evaluation-campaign``), with their
  revisions; each record names its bundle, extraction and packet, and the article's locked items are counted under
  ``campaign``. They are development evidence after D-071 and may never be counted as unseen again. Their bundles are
  labelled ``S04-CAMPAIGN-80``, not ``S03-BUNDLE``. Root-cause and regression work of the corrective cycle inspected
  only
  articles already listed here (the campaign article ``en-39868218``, the 232 development revisions, the vertical
  slice); ``S04-REF`` picks up every bundle the corrective code, tests or evidence name.

Retraction Watch works (not Wikipedia articles) are recorded under ``identifiers`` for information only, never as an
exclusion input (reviewer finding F-04): the census read every DOI and PMID of the pinned snapshot, so record-level
exposure is the whole snapshot, and the rule treats every record alike. Excluding articles that cite role-colliding
keys would remove the very cases a new gate must test; the frame excludes by article only. The block names the keys of
the role-collision fixture (``tests/stage04/fixtures/corrective/rw_role_collision.json``) as the ones examined by name.

The wiki-agnostic, deliberately over-inclusive Stage 03 rule (``confirmation-d036/scripts/exposure_set.py``) is
recomputed and kept as a separate ``listed`` block with its own digest; whether the frame also excludes it is a
pre-registration choice (Step 13).

Only tracked files are read (``git ls-files``), and the builder refuses a working tree that differs from the commit
it names, so the manifest describes exactly ``source_commit`` (reviewer finding F-03); no request is made; the
Stage 01 census and dump-scan frames are not read, and no evaluation frame, sample or draw is produced or inspected.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "stage04-exposure-manifest/2"
S03_RULE = "docs/verification/stage-03/evaluation/confirmation-d036/scripts/exposure_set.py"
DEV = "docs/verification/stage-04/review/step9/dev_measurements.json"
PURPOSIVE = "docs/verification/stage-01/data/purposive_discovery.json"
EVIDENCE = "docs/verification/stage-01/EVIDENCE_MANIFEST.json"
REF_ROOTS = ("src/citerift/investigation", "tests/stage04", "docs/verification/stage-04")
# The superseded freeze is covered by the check that every article of its manifest is listed here (reviewer finding
# F-05); freeze-2 is scanned except this manifest's own directory.
SELF_DIR = ("docs/verification/stage-04/freeze/", "docs/verification/stage-04/freeze-2/exposure/")
CAMPAIGN = "docs/verification/stage-04/evaluation-campaign"
CAMPAIGN_ARTICLES = 80
FIXTURE = "tests/stage04/fixtures/corrective/rw_role_collision.json"
SUPERSEDED = "docs/verification/stage-04/freeze/exposure/EXPOSURE_MANIFEST.json"
WIKIS = ("ar", "en")


def git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(ROOT), *args],  # noqa: S607
        capture_output=True,
        check=True,
        text=True,
    ).stdout


def tracked() -> list[str]:
    return sorted(p for p in git("ls-files", "-z").split("\0") if p)


def load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def norm_title(wiki: str, title: str) -> str:
    t = unicodedata.normalize("NFC", title).replace("_", " ").strip()
    if wiki == "en" and t:
        t = t[0].upper() + t[1:]
    return t


class Articles:
    def __init__(self) -> None:
        self.by_id: dict[tuple[str, int], dict[str, Any]] = {}
        self.by_title: dict[tuple[str, str], dict[str, Any]] = {}

    def add(
        self,
        source: str,
        wiki: Any,
        evidence: str,
        page_id: Any = None,
        title: Any = None,
        revision_id: Any = None,
    ) -> None:
        if wiki not in WIKIS:
            raise SystemExit(f"unexpected wiki {wiki!r} in {evidence}")
        pid = page_id if isinstance(page_id, int) and not isinstance(page_id, bool) else None
        t = norm_title(wiki, title) if isinstance(title, str) and title.strip() else None
        if pid is None and t is None:
            raise SystemExit(f"no page id and no title in {evidence}")
        rec = self.by_id.get((wiki, pid)) if pid is not None else None
        if rec is None and t is not None:
            rec = self.by_title.get((wiki, t))
        if rec is None:
            rec = {
                "wiki": wiki,
                "page_id": None,
                "titles": set(),
                "revision_ids": set(),
                "sources": set(),
                "evidence_paths": set(),
            }
        if pid is not None:
            if rec["page_id"] not in (None, pid):
                # Same title, two page ids (a moved page): keep both records, linked by the title.
                rec = self.by_id.get((wiki, pid)) or {
                    "wiki": wiki,
                    "page_id": pid,
                    "titles": set(),
                    "revision_ids": set(),
                    "sources": set(),
                    "evidence_paths": set(),
                }
            rec["page_id"] = pid
            self.by_id[(wiki, pid)] = rec
        if t is not None:
            rec["titles"].add(t)
            self.by_title.setdefault((wiki, t), rec)
        if isinstance(revision_id, int) and not isinstance(revision_id, bool):
            rec["revision_ids"].add(revision_id)
        rec["sources"].add(source)
        rec["evidence_paths"].add(evidence)

    def records(self) -> list[dict[str, Any]]:
        seen: dict[int, dict[str, Any]] = {}
        for rec in [*self.by_id.values(), *self.by_title.values()]:
            seen[id(rec)] = rec
        out = []
        for rec in seen.values():
            titles = sorted(rec["titles"])
            out.append(
                {
                    "wiki": rec["wiki"],
                    "page_id": rec["page_id"],
                    "key": f"{rec['wiki']}:{rec['page_id']}"
                    if rec["page_id"] is not None
                    else f"{rec['wiki']}:title:{titles[0]}",
                    "titles": titles,
                    "revision_ids": sorted(rec["revision_ids"]),
                    "sources": sorted(rec["sources"]),
                    "evidence_paths": sorted(rec["evidence_paths"]),
                }
            )
        out.sort(key=lambda r: (r["wiki"], r["page_id"] is None, r["page_id"] or 0, r["titles"]))
        keys = [r["key"] for r in out]
        if len(keys) != len(set(keys)):
            raise SystemExit("duplicate article key")
        return out


def walk_pages(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if node.get("wiki") in WIKIS and any(k in node for k in ("page_id", "pageid", "title")):
            found.append(node)
        for v in node.values():
            found.extend(walk_pages(v))
    elif isinstance(node, list):
        for v in node:
            found.extend(walk_pages(v))
    return found


def campaign_articles(arts: Articles, bundles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The 80 acquired articles of the failed campaign, cross-checked against their bundles, packets and the lock."""
    acq = load(f"{CAMPAIGN}/ACQUISITION.json")["attempts"]
    lock = load(f"{CAMPAIGN}/LOCK.json")
    items: dict[str, int] = {}
    for item_id in lock["final"]:
        wiki, rev = item_id.split("-")[:2]
        items[f"{wiki}-{rev}"] = items.get(f"{wiki}-{rev}", 0) + 1
    names = []
    for att in acq:
        if att["status"] != "acquired":
            raise SystemExit(f"campaign attempt {att['name']} is not acquired")
        name, wiki = att["name"], att["name"].split("-", 1)[0]
        bdir = f"{CAMPAIGN}/bundles/{name}"
        page = bundles.get(bdir)
        packet = load(f"{CAMPAIGN}/packets/{name}.json")["article"]
        if page is None or (page["page_id"], page["revision_id"]) != (att["page_id"], att["revision_id"]):
            raise SystemExit(f"campaign bundle {bdir} does not match its acquisition record")
        if (packet["wiki"], packet["page_id"], packet["revision_id"]) != (wiki, att["page_id"], att["revision_id"]):
            raise SystemExit(f"campaign packet {name} does not match its acquisition record")
        for ev in (f"{CAMPAIGN}/extractions/{name}.json", f"{CAMPAIGN}/packets/{name}.json"):
            arts.add("S04-CAMPAIGN-80", wiki, ev, att["page_id"], att.get("title"), att["revision_id"])
        names.append(name)
    if len(set(names)) != CAMPAIGN_ARTICLES:
        raise SystemExit(f"expected {CAMPAIGN_ARTICLES} campaign articles, found {len(set(names))}")
    revs = {f"{n.split('-', 1)[0]}-{a['revision_id']}" for n, a in zip(names, acq, strict=True)}
    if set(items) - revs:
        raise SystemExit(f"locked items name unknown revisions: {sorted(set(items) - revs)[:3]}")
    return {
        "articles": len(names),
        "items": len(lock["final"]),
        "lock_sha256": hashlib.sha256((ROOT / CAMPAIGN / "LOCK.json").read_bytes()).hexdigest(),
        "acquisition_sha256": hashlib.sha256((ROOT / CAMPAIGN / "ACQUISITION.json").read_bytes()).hexdigest(),
        "note": "development evidence after D-071 section 1; never counted as unseen again",
    }


def clean_tree() -> None:
    """Refuse a working tree that differs from HEAD (tracked changes or untracked files), so that the bytes read are
    the bytes of ``source_commit`` (reviewer finding F-03)."""
    dirty = git("status", "--porcelain", "--untracked-files=all").strip()
    if dirty:
        raise SystemExit(f"the working tree differs from HEAD; commit first:\n{dirty[:2000]}")


def fixture_identifiers() -> dict[str, Any]:
    """Retraction Watch keys examined by name in the corrective cycle (works, not articles); information only."""
    fx = load(FIXTURE)
    dois: set[str] = set()
    pmids: set[str] = set()
    for cls in fx["classes"].values():
        for scheme, out in (("doi", dois), ("pmid", pmids)):
            if cls.get(scheme):
                out.add(cls[scheme])
    for keys in fx["campaign_bundle"].values():
        dois.update(keys["doi"])
        pmids.update(keys["pmid"])
    for q in fx["outcomes"]:
        if q.get("doi"):
            dois.add(q["doi"])
        if q.get("pmid"):
            pmids.add(q["pmid"])
    return {
        "source": FIXTURE,
        "source_sha256": hashlib.sha256((ROOT / FIXTURE).read_bytes()).hexdigest(),
        "doi": sorted(dois),
        "pmid": sorted(pmids),
        "role": "information only, never an exclusion input (reviewer finding F-04)",
        "census_scope": "every DOI and PMID of the pinned snapshot rw-2f116e9ffed718e6 was read by the corrective "
        "census (corrective/census/CENSUS.json, PAIR_CENSUS.json, PAIR_CENSUS_LENIENT.json); record-level exposure "
        "is the whole snapshot",
        "note": "the keys of the role-collision fixture, examined by name in root-cause and adversarial work; the rule "
        "treats every record alike, and a frame excludes by article only",
    }


def build() -> dict[str, Any]:
    files = tracked()
    arts = Articles()
    bundles: dict[str, dict[str, Any]] = {}

    for path in files:
        if path.endswith("/capture.json"):
            page = load(path).get("page") or {}
            bdir = path[: -len("/capture.json")]
            bundles[bdir] = page
            source = "S04-CAMPAIGN-80" if bdir.startswith(f"{CAMPAIGN}/bundles/") else "S03-BUNDLE"
            arts.add(source, page.get("wiki"), bdir, page.get("page_id"), page.get("title"), page.get("revision_id"))

    campaign = campaign_articles(arts, bundles)

    dev = load(DEV)
    for key, row in sorted(dev["revisions"].items()):
        page = bundles.get(row["bundle"])
        if page is None:
            raise SystemExit(f"{DEV}: {key} names an untracked bundle {row['bundle']}")
        arts.add("S04-DEV-232", page["wiki"], row["bundle"], page["page_id"], page.get("title"), page["revision_id"])

    tokens: dict[str, str] = {}
    for bdir, page in bundles.items():
        tokens[bdir] = bdir
        tokens[f"{page['wiki']}-{page['revision_id']}"] = bdir
        tokens[Path(bdir).name] = bdir
    pattern = re.compile("|".join(sorted((re.escape(t) for t in tokens), key=len, reverse=True)))
    for path in files:
        if not path.startswith(REF_ROOTS) or path.startswith(SELF_DIR):
            continue
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        for m in pattern.finditer(text):
            end = m.end()
            if end < len(text) and text[end].isdigit():
                continue
            bdir = tokens[m.group(0)]
            page = bundles[bdir]
            arts.add("S04-REF", page["wiki"], path, page["page_id"], page.get("title"), page["revision_id"])

    for path in files:
        name = Path(path).name
        if name.startswith("capture_states") and name.endswith(".json"):
            for node in walk_pages(load(path)):
                arts.add("S03-ATTEMPTED", node["wiki"], path, node.get("page_id"), node.get("title"))
        elif path.startswith("docs/verification/stage-03/calibration/dev_selection") and name.endswith(".json"):
            for node in load(path)["articles"]:
                arts.add(
                    "S03-DEV-TITLE", node["wiki"], path, node.get("page_id"), node.get("title"), node.get("revision_id")
                )

    purposive = load(PURPOSIVE)
    for result in purposive["results"]:
        for obs in result.get("observations", []):
            arts.add("S01-PURPOSIVE", obs["wiki"], PURPOSIVE, obs.get("pageid"), obs.get("title"), obs.get("revid"))
        for method in ("m1", "m2"):
            for title in (result.get(method) or {}).get("titles", []):
                arts.add("S01-PURPOSIVE-HITS", result["wiki"], PURPOSIVE, None, title)
    for node in walk_pages(load(EVIDENCE)):
        arts.add(
            "S01-EVIDENCE",
            node["wiki"],
            EVIDENCE,
            node.get("page_id", node.get("pageid")),
            node.get("title"),
            node.get("revision_id", node.get("revid")),
        )

    records = arts.records()
    if sum("S04-CAMPAIGN-80" in r["sources"] for r in records) != CAMPAIGN_ARTICLES:
        raise SystemExit("the campaign articles are not exactly the 80 acquired articles")
    counts: dict[str, int] = {}
    for rec in records:
        for s in rec["sources"]:
            counts[s] = counts.get(s, 0) + 1

    listed_raw = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, "-I", str(ROOT / S03_RULE)],
        capture_output=True,
        check=True,
        cwd=ROOT,
    ).stdout
    listed = json.loads(listed_raw)
    listed_block = {
        "rule": S03_RULE,
        "rule_sha256": hashlib.sha256((ROOT / S03_RULE).read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(listed_raw).hexdigest(),
        "page_ids": len(listed.get("page_ids", [])),
        "titles": len(listed.get("titles", [])),
        "note": "wiki-agnostic and over-inclusive; adoption for frame exclusion is a pre-registration choice",
    }

    inputs = git("ls-files", "-s").encode("utf-8")
    return {
        "schema": SCHEMA,
        "source_commit": git("rev-parse", "HEAD").strip(),
        "generator": "docs/verification/stage-04/freeze-2/exposure/build_exposure_manifest.py",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs_sha256": hashlib.sha256(inputs).hexdigest(),
        "level": "article (wiki, page_id); (wiki, normalised title) where no page id is recorded",
        "frame_rule": (
            "exclude a frame article when its (wiki, page_id) is a record's, or its (wiki, normalised "
            "title) is one of a record's titles; re-check drawn articles on capture identity"
        ),
        "counts": {
            "articles": len(records),
            "by_wiki": {w: sum(r["wiki"] == w for r in records) for w in WIKIS},
            "without_page_id": sum(r["page_id"] is None for r in records),
            "by_source": dict(sorted(counts.items())),
        },
        "articles": records,
        "listed": listed_block,
        "campaign": campaign,
        "identifiers": fixture_identifiers(),
        "supersedes": {
            "path": SUPERSEDED,
            "sha256": hashlib.sha256((ROOT / SUPERSEDED).read_bytes()).hexdigest(),
            "note": "the Step 12 manifest (freeze b5bf8ed), kept unchanged; every article it lists is listed here",
        },
    }


def covers_superseded(records: list[dict[str, Any]]) -> None:
    """Every article of the superseded manifest is listed here, by key, with its titles and revisions (F-05)."""
    mine = {r["key"]: r for r in records}
    for old in load(SUPERSEDED)["articles"]:
        new = mine.get(old["key"])
        if (
            new is None
            or not set(old["titles"]) <= set(new["titles"])
            or not set(old["revision_ids"]) <= set(new["revision_ids"])
        ):
            raise SystemExit(f"{old['key']} of the superseded manifest is not fully listed")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] != "--out":
        raise SystemExit("usage: build_exposure_manifest.py --out FILE")
    clean_tree()
    doc = build()
    covers_superseded(doc["articles"])
    Path(args[1]).write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
