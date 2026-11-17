"""Stage 04 Step 12, owner decision OD-S12-1: the differential tamper proof of the D-062 identity-verification profile.

Every tamper case is applied to a fresh copy of a real Stage 02 index (built by Stage 02 ``build`` from the attributed
Retraction Watch subset of the Step 8 tests, with its build manifest), and the copy is then checked twice:

- by Stage 02's complete ``verify`` (``citerift.retraction.export.verify``, the artifact certification, including the
  JSON-Schema check of every stored event); an index that Stage 02 ``Index`` refuses to open counts as rejected;
- by the Stage 04 D-062 identity-verification profile (``adapters.lookup.verify_index_identity`` through a
  cache-disabled ``IndexVerifier``), the check every Stage 04 process runs.

A case is a **discrepancy** when complete ``verify`` rejects it and the profile accepts it: the owner decision requires
the work to stop before freeze on any such case that can affect LOOKUP, provenance or the canonical identity. A case
both accept must have the untampered identity (same content) or another canonical identity (a different artifact,
STALE by D-062); this is recorded too.

The operational cases (a replaced inode, a size-preserving change after the identity was reused, a file replaced
while LOOKUP reads it) concern the process-local reuse and the before/after guard, which complete ``verify`` does not
have; they are run as the named Step 12 tests and their results recorded.

Run from the repository root, offline:

    unshare -rn uv run python docs/verification/stage-04/freeze/d062/tamper_differential.py --work <empty dir>

Writes ``tamper_differential.json`` beside itself; exit status 1 when a discrepancy or a failed operational test exists.
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

OPERATIONAL_TESTS = {
    "inode replacement (same size and times) after the identity was reused": (
        "test_a_replaced_inode_with_the_same_size_and_times_is_verified_again"
    ),
    "size-preserving in-place change with the mtime restored, after reuse": (
        "test_a_size_preserving_in_place_change_with_restored_mtime_is_verified_again"
    ),
    "file changed after the reuse entry was stored": "test_a_change_after_verification_is_verified_again",
    "file replaced during LOOKUP": "test_a_file_replaced_during_the_lookup_fails_closed",
    "failures are never reused": "test_failures_are_never_cached",
}


def sql(index: Path, *statements: str) -> None:
    conn = sqlite3.connect(index)
    try:
        for s in statements:
            conn.execute(s)
        conn.commit()
    finally:
        conn.close()


def first_event(index: Path) -> str:
    conn = sqlite3.connect(index)
    try:
        return str(conn.execute("SELECT min(event_id) FROM event").fetchone()[0])
    finally:
        conn.close()


def forge_meta(index: Path, key: str, value: str) -> None:
    sql(index, f"UPDATE meta SET value = '{value}' WHERE key = '{key}'")  # noqa: S608 - fixed keys, hex values


def recompute_meta(index: Path) -> None:
    """Store the digests recomputed from the (tampered) content, as a forger would."""
    from citerift.retraction import export
    from citerift.retraction.store import DIGEST_KEYS

    conn = sqlite3.connect(index)
    try:
        digests = export.compute_digests(conn)
        for k in DIGEST_KEYS:
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (str(digests[k]), k))
        conn.commit()
    finally:
        conn.close()


def recompute_manifest(index: Path) -> None:
    """Make the build manifest agree with the (forged) metadata."""
    from citerift.retraction.store import DIGEST_KEYS, manifest_path_for

    path = manifest_path_for(index)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    conn = sqlite3.connect(index)
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    finally:
        conn.close()
    target = manifest.get("digests", manifest)
    for k in DIGEST_KEYS:
        if k in target:
            target[k] = int(meta[k]) if isinstance(target[k], int) else meta[k]
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")


NOTES: dict[str, Any] = {}


def flip_bytes(index: Path) -> None:
    """Size-preserving byte change in the middle of the file (not through SQLite); the page it lands in is recorded
    from SQLite's ``dbstat`` so that the result can be read (a flip in unallocated page space changes no content)."""
    size = index.stat().st_size
    conn = sqlite3.connect(index)
    try:
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        page = size // 2 // page_size + 1
        row = conn.execute("SELECT name, pagetype, ncell, unused FROM dbstat WHERE pageno = ?", (page,)).fetchone()
    finally:
        conn.close()
    NOTES["midpoint"] = {
        "page": page,
        "offset_in_page": size // 2 % page_size,
        "page_size": page_size,
        "dbstat": dict(zip(("table", "pagetype", "cells", "unused_bytes"), row, strict=True)) if row else None,
    }
    with open(index, "r+b") as f:
        f.seek(size // 2)
        chunk = f.read(64)
        f.seek(size // 2)
        f.write(bytes(b ^ 0xFF for b in chunk))


def flip_title_bytes(*, every: bool) -> Callable[[Path], None]:
    """Size-preserving edit of stored row content straight in the file (not through SQLite): the case of one letter
    of the first event's title is swapped where the title is stored (the first place, or every place)."""

    def run(index: Path) -> None:
        conn = sqlite3.connect(index)
        try:
            title = str(conn.execute("SELECT title FROM event ORDER BY event_id LIMIT 1").fetchone()[0])
        finally:
            conn.close()
        needle = title.encode("utf-8")
        pos = next(i for i, ch in enumerate(title) if ch.isascii() and ch.isalpha())
        data = bytearray(index.read_bytes())
        starts, at = [], data.find(needle)
        while at >= 0:
            starts.append(at)
            at = data.find(needle, at + 1)
        if not starts:
            raise SystemExit("title bytes not found in the file")
        for start in starts if every else starts[:1]:
            data[start + pos] ^= 0x20
        index.write_bytes(bytes(data))

    return run


def cases(ev: Callable[[Path], str]) -> dict[str, Callable[[Path], None]]:
    def event(set_clause: str) -> Callable[[Path], None]:
        return lambda p: sql(p, f"UPDATE event SET {set_clause} WHERE event_id = '{ev(p)}'")  # noqa: S608

    return {
        "untampered (control)": lambda p: None,
        "queryable event mutated (title)": event("title = title || ' (edited)'"),
        "queryable event mutated, same length (size-preserving SQL change)": event(
            "title = upper(substr(title, 1, 1)) || lower(substr(title, 2))"
        ),
        "raw record mutated": lambda p: sql(
            p,
            "UPDATE raw_record SET fields = replace(fields, 'a', 'b') "
            "WHERE ordinal = (SELECT min(ordinal) FROM raw_record WHERE instr(fields, 'a') > 0)",
        ),
        "derived table mutated (title_token)": lambda p: sql(
            p, "DELETE FROM title_token WHERE (token, event_id) = (SELECT token, event_id FROM title_token LIMIT 1)"
        ),
        "derived table mutated (ident)": lambda p: sql(
            p, "UPDATE ident SET norm = 'X' || norm WHERE id = (SELECT min(id) FROM ident WHERE norm IS NOT NULL)"
        ),
        "malformed event JSON field (notice_date)": event("notice_date = '{not json'"),
        "event field with a schema-invalid type (flags is a string)": event("flags = '\"not-a-list\"'"),
        "event field with a schema-invalid value (original_year text)": event("original_year = 'nineteen'"),
        "forged stored artifact_digest": lambda p: forge_meta(p, "artifact_digest", "0" * 64),
        "forged stored semantic_digest": lambda p: forge_meta(p, "semantic_digest", "1" * 64),
        "forged stored export_lines": lambda p: forge_meta(p, "export_lines", "1"),
        "manifest mismatch (manifest digest edited)": _edit_manifest,
        "manifest missing": _drop_manifest,
        "content changed, metadata recomputed (manifest stale)": seq(
            event("title = title || ' (edited)'"), recompute_meta
        ),
        "content changed, metadata and manifest recomputed": seq(
            event("title = title || ' (edited)'"), recompute_meta, recompute_manifest
        ),
        "schema-invalid event field, metadata and manifest recomputed": seq(
            event("flags = '\"not-a-list\"'"), recompute_meta, recompute_manifest
        ),
        "raw record and every derived table changed consistently (another artifact)": _other_artifact,
        "size-preserving byte flip at the file midpoint": flip_bytes,
        "size-preserving direct byte edit of stored row content (first place)": flip_title_bytes(every=False),
        "size-preserving direct byte edit of stored row content (every place)": flip_title_bytes(every=True),
    }


def seq(*steps: Callable[[Path], None]) -> Callable[[Path], None]:
    def run(p: Path) -> None:
        for step in steps:
            step(p)

    return run


def _edit_manifest(index: Path) -> None:
    from citerift.retraction.store import manifest_path_for

    path = manifest_path_for(index)
    text = path.read_text(encoding="utf-8")
    conn = sqlite3.connect(index)
    try:
        digest = conn.execute("SELECT value FROM meta WHERE key = 'artifact_digest'").fetchone()[0]
    finally:
        conn.close()
    path.write_text(text.replace(digest, "f" * 64), encoding="utf-8")


def _drop_manifest(index: Path) -> None:
    from citerift.retraction.store import manifest_path_for

    manifest_path_for(index).unlink()


def _other_artifact(index: Path) -> None:
    """A genuinely different, internally consistent artifact: another build (fewer records) at this path."""
    import step8_support as S8

    other = S8.build_index(index.parent / "other-build", S8.RW_FEWER)
    S8.replace_index(index, other)


def check(path: Path) -> dict[str, Any]:
    from citerift.investigation.adapters import lookup as L
    from citerift.retraction import export
    from citerift.retraction.query import Index
    from citerift.retraction.store import IndexUnavailable, manifest_path_for

    out: dict[str, Any] = {}
    try:
        with Index(path) as ix:
            report = export.verify(ix.conn, manifest_path=manifest_path_for(path))
        out["full_verify"] = {
            "accepted": bool(report["ok"]),
            "problems": [str(p) for p in report["problems"]][:5],
            "problem_count": report["problem_count"],
            "events_schema_checked": report.get("events_schema_checked"),
        }
    except IndexUnavailable as exc:
        out["full_verify"] = {"accepted": False, "refused_at_open": exc.code, "problems": [str(exc)[:300]]}
    except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:  # Stage 02 verify raised: not accepted
        out["full_verify"] = {"accepted": False, "raised": f"{type(exc).__name__}: {exc}"[:300]}
    try:
        ident = L.IndexVerifier(enabled=False).identity(path)
        out["profile"] = {"accepted": True, "identity": ident}
    except L.IndexNotVerified as exc:
        out["profile"] = {"accepted": False, "code": exc.code, "detail": exc.detail[:300]}
    except IndexUnavailable as exc:
        out["profile"] = {"accepted": False, "code": exc.code, "refused_at_open": True, "detail": str(exc)[:300]}
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if any(work.iterdir()):
        raise SystemExit(f"{work} is not empty")
    os.environ.setdefault("CITERIFT_WIKI_NETWORK_LOCK", str(work / "network-gate.lock"))
    import step8_support as S8

    from citerift.retraction.store import manifest_path_for

    base = S8.build_index(work / "base")
    baseline = check(base)
    results: dict[str, Any] = {}
    for n, (name, apply) in enumerate(cases(first_event).items()):
        d = work / f"case-{n:02d}"
        d.mkdir()
        path = d / base.name
        shutil.copyfile(base, path)
        shutil.copyfile(manifest_path_for(base), manifest_path_for(path))
        apply(path)
        r = check(path)
        full_ok, prof_ok = r["full_verify"]["accepted"], r["profile"]["accepted"]
        if prof_ok:
            same = r["profile"]["identity"] == baseline["profile"]["identity"]
            r["profile"]["identity_vs_untampered"] = "same" if same else "different canonical identity (STALE)"
        if apply is flip_bytes:
            r["flipped_location"] = NOTES.get("midpoint")
        r["discrepancy"] = (not full_ok) and prof_ok
        r["agree"] = full_ok == prof_ok
        results[name] = r
        print(f"{name}: full {'accept' if full_ok else 'REJECT'} / profile {'accept' if prof_ok else 'REJECT'}")
    tests = sorted(set(OPERATIONAL_TESTS.values()))
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [
            sys.executable,
            "-P",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/stage04/test_step12_d062.py",
            "-k",
            " or ".join(tests),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CITERIFT_WIKI_NETWORK_LOCK": str(work / "pytest-gate.lock")},
    )
    summary = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]
    operational = {
        "cases": OPERATIONAL_TESTS,
        "pytest_exit_code": proc.returncode,
        "pytest_summary": summary,
        "full_verify": "not applicable: complete verify has no process-local reuse and no during-read guard",
    }
    discrepancies = [n for n, r in results.items() if r["discrepancy"]]
    profile_only = [n for n, r in results.items() if r["full_verify"]["accepted"] and not r["profile"]["accepted"]]
    out = {
        "label": "Stage 04 Step 12 OD-S12-1 differential tamper proof: Stage 02 complete verify vs the D-062 "
        "identity-verification profile; attributed Retraction Watch subset index (Step 8 tests); not an evaluation",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "base_identity": baseline["profile"].get("identity"),
        "cases": results,
        "operational": operational,
        "discrepancies": discrepancies,
        "rejected_only_by_the_profile": profile_only,
        "control_accepted_by_both": results["untampered (control)"]["agree"]
        and results["untampered (control)"]["profile"]["accepted"],
    }
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False, default=str).replace(str(work), "<work>")
    (HERE / "tamper_differential.json").write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"discrepancies": discrepancies, "profile_only": profile_only, "operational": summary}))
    return 0 if not discrepancies and proc.returncode == 0 and out["control_accepted_by_both"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
