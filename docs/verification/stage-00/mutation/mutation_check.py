# ruff: noqa: E501  (mutation patterns must match source lines exactly)
"""Stage 00 mutation check (correction A-00-001): each mutant disables one rule; the test suite must fail.

Run from a clean checkout: python docs/verification/stage-00/mutation/mutation_check.py
Each pattern must occur exactly once. Every file is restored after its mutant
runs. M1 to M9 are the mutants of the accepted revision 741476c (archived in
superseded/741476c/mutation/), with patterns updated where the code changed;
M10 onwards cover the checks added by the correction.
"""

import pathlib
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[4]
ORC = "src/citerift/governance/orchestrator.py"
EVI = "src/citerift/governance/evidence.py"
MEM = "src/citerift/governance/memory.py"
REP = "src/citerift/governance/pytest_report.py"
M = [
    (
        "M1 single-active rule (current state) disabled",
        ORC,
        "        if len(active) > 1:\n            return [",
        "        if False:\n            return [",
    ),
    ("M2 owner-only edge check disabled", ORC, "            if actor != Actor.OWNER:", "            if False:"),
    (
        "M3 absence-of-record must be uncertain (schema)",
        "schemas/contracts/v1/investigation.schema.json",
        '"then": {"properties": {"status": {"const": "uncertain"}',
        '"then": {"properties": {"status": {}',
    ),
    ("M4 test report revision check disabled", EVI, 'if report.get("revision") != revision:', "if False:"),
    ("M5 drift detection disabled", ORC, "if changes and all(changes):", "if False:"),
    ("M6 history replay conflict disabled", ORC, 'if replay[s["id"]] != s["status"]:', "if False:"),
    (
        "M7 artifact hash check disabled",
        EVI,
        'if expected_sha is not None and sha256_file(path) != expected_sha:\n        problems.append(\n            Problem(\n                "EVIDENCE_STALE"',
        'if False:\n        problems.append(\n            Problem(\n                "EVIDENCE_STALE"',
    ),
    (
        "M8 dependency check (current state) disabled",
        ORC,
        'for d in self.dependencies(s["id"])["unsatisfied"]:\n                if d in reopened:',
        "for d in []:\n                if d in reopened:",
    ),
    (
        "M9 acceptance-of-other-revision check disabled",
        ORC,
        'if acc["accepted_revision"] != ver["revision"]:',
        "if False:",
    ),
    (
        "M10 F-04 single-active rule over history disabled",
        ORC,
        "                if len(active) > 1:\n                    out.append(",
        "                if False:\n                    out.append(",
    ),
    ("M11 F-04 dependencies over history disabled", ORC, "            if pending:", "            if False:"),
    (
        "M12 F-05 correction amendment for reopening disabled",
        ORC,
        'if amendment is None or amendment["kind"] != "correction" or amendment["recorded_at"] > at:',
        "if False:",
    ),
    ("M13 F-05 block without blocker disabled", ORC, "if target == Status.BLOCKED and not open_then:", "if False:"),
    (
        "M14 F-05 start or verify with open blocker disabled",
        ORC,
        "        if open_then and (",
        "        if False and (",
    ),
    ("M15 F-02 manifest hash comparison disabled", ORC, "elif current[rel] != sha:", "elif False:"),
    (
        "M16 F-02 unlisted evidence disabled",
        ORC,
        "for rel in sorted(set(current) - set(recorded_hashes) - later):",
        "for rel in []:",
    ),
    ("M17 F-02 gate evidence pinning disabled", ORC, "            if not pinned:", "            if False:"),
    (
        "M18 F-03 definition hash disabled",
        ORC,
        'if recorded["definition_sha256"] != self._definition_sha256(stage):',
        "if False:",
    ),
    (
        "M19 F-07 complete-run requirement disabled",
        EVI,
        'if not isinstance(selection, dict) or selection.get("complete") is not True:',
        "if False:",
    ),
    (
        "M20 F-07 plugin reports every run as complete",
        "src/citerift/governance/pytest_report.py",
        '"complete": whole and not any(narrowing.values()),',
        '"complete": True,',
    ),
    (
        "M21 F-10 date-time format checker removed",
        "src/citerift/contracts/validate.py",
        "registry=self.registry, format_checker=FORMAT_CHECKER)",
        "registry=self.registry)",
    ),
    (
        "M22 F-09 events compared as strings",
        "src/citerift/contracts/validate.py",
        'times = [t for t in (parse_utc_timestamp(e["at"]) for e in record["events"]) if t is not None]',
        'times = [e["at"] for e in record["events"]]',
    ),
    (
        "M23 F-08 retraction alternatives untyped",
        "schemas/contracts/v1/investigation.schema.json",
        '"value": {"enum": ["retracted", "expression_of_concern", "correction", "reinstated", "not_found_in_checked_sources"]}',
        '"value": true',
    ),
    (
        "M24 F-10 trailing-newline guard removed from timestamps",
        "schemas/contracts/v1/common.schema.json",
        '(\\\\.[0-9]{1,6})?Z$(?!\\\\n)"',
        '(\\\\.[0-9]{1,6})?Z$"',
    ),
    (
        "M25 F-18 duplicate keys accepted",
        "src/citerift/contracts/formats.py",
        "        if key in out:",
        "        if False:",
    ),
    (
        "M26 F-06 malformed headings ignored",
        MEM,
        "if m and m.group(1) == prefix[0] and not _HEADING.match(line):",
        "if False:",
    ),
    (
        "M27 F-06 project-wide critical defects ignored",
        MEM,
        'and (stage_id in r.refs("Stage") or r.get("Stage") == "project")',
        'and (stage_id in r.refs("Stage"))',
    ),
    (
        "M28 F-11 reopened dependency is an error again",
        ORC,
        "                if d in reopened:",
        "                if False:",
    ),
    ("M29 F-16 future timestamps accepted", ORC, "    if at > limit:", "    if False:"),
    ("M30 F-17 owner reference reuse accepted", ORC, "                if reused:", "                if False:"),
    (
        "M31 F-17 record/history mismatch accepted",
        ORC,
        '                    last is None\n                    or last["at"] != record["recorded_at"]',
        '                    False\n                    and last["at"] != record["recorded_at"]',
    ),
    (
        "M32 F-19 uncommitted owned changes ignored",
        ORC,
        "        if dirty:\n            out.append(",
        "        if False:\n            out.append(",
    ),
    (
        "M33 F-03 policy values not fixed in the schema",
        "schemas/governance/stage_registry.schema.json",
        '"single_active_engineering_stage": {"const": true}',
        '"single_active_engineering_stage": {"type": "boolean"}',
    ),
    ("M34 S-01 files git ignores pinned as evidence", EVI, "skip = gitutil.ignored(root, files)", "skip = set()"),
    # Fixes of the final independent review (V-01 to V-16).
    ("M35 V-01 items dropped by a conftest ignored", REP, 'and not selection["dropped"]', "and True"),
    (
        "M36 V-01 committed test files not compared",
        EVI,
        'problems.extend(_files_not_run(root, rel, revision, selection.get("files")))',
        "pass",
    ),
    (
        "M37 V-01 ini overrides allowed",
        REP,
        '"override_ini": [o for o in config.option.override_ini or [] if o not in _STRICTER_OVERRIDES],',
        '"override_ini": [],',
    ),
    (
        "M38 V-02 a URL counts as pinned evidence",
        ORC,
        "                if evidence.is_url(ref):\n                    continue",
        "                if evidence.is_url(ref):\n                    pinned = True\n                    continue",
    ),
    (
        "M39 V-02 unpinned co-cited file accepted",
        ORC,
        '                else:\n                    out.append(\n                        Finding(\n                            "GATE_EVIDENCE_UNPINNED",',
        '                elif False:\n                    out.append(\n                        Finding(\n                            "GATE_EVIDENCE_UNPINNED",',
    ),
    (
        "M40 V-03 stage artifact list not fixed for engineering stages",
        "schemas/governance/stage_registry.schema.json",
        '          "required_artifacts": {\n            "const": [',
        '          "required_artifacts": {\n            "examples": [',
    ),
    (
        "M41 V-03 executors not fixed by stage",
        "schemas/governance/stage_registry.schema.json",
        '"else": {"properties": {"executor": {"const": "engineering-agent"}}}',
        '"else": {}',
    ),
    ("M42 V-03 handoff not always required", ORC, "            names.append(handoff)", "            pass"),
    ("M43 V-05 correction test reports exempt again", ORC, ' and a["kind"] == "enhancement"\n', "\n"),
    (
        "M44 V-06 orphan entry fields ignored",
        MEM,
        "            if not attached and m.group(1) in _ENTRY_FIELDS:",
        "            if False:",
    ),
    (
        "M45 V-06 topic spelling variants distinct",
        MEM,
        'return _SEPARATORS.sub("-", unicodedata.normalize("NFKC", topic)).strip("-").casefold()',
        "return topic.casefold()",
    ),
    (
        "M46 V-07 amendment references not searched",
        ORC,
        'if a["owner_ref"] == acc["owner_ref"] and a["recorded_at"] <= verified_entry["at"]',
        "if False",
    ),
    ("M47 V-08 one amendment for many reopenings", ORC, "            if earlier:", "            if False:"),
    (
        "M48 V-09 duplicate record ids accepted",
        ORC,
        "for dup in sorted({v for v in values if values.count(v) > 1}):",
        "for dup in []:",
    ),
    (
        "M49 V-10 commands run on a schema-invalid registry",
        "src/citerift/governance/cli.py",
        '    if schema_errors and args.command != "check":',
        "    if False:",
    ),
    (
        "M50 V-11 default time ignores recorded times",
        ORC,
        "        now: str = max([utc_now(), *recorded])",
        "        now: str = utc_now()",
    ),
    (
        "M51 V-12 nested .gitattributes accepted",
        ORC,
        'nested = [p for p in gitutil.tracked_files(self.root, "HEAD", ".") if p.endswith("/.gitattributes")]',
        "nested: list[str] = []",
    ),
    (
        "M52 V-13 replace refs honoured",
        "src/citerift/governance/gitutil.py",
        '[git, "--no-replace-objects", "-C", str(root), *args],',
        '[git, "-C", str(root), *args],',
    ),
    (
        "M53 V-15 clock skew bound widened",
        ORC,
        "MAX_CLOCK_SKEW = timedelta(minutes=5)",
        "MAX_CLOCK_SKEW = timedelta(days=3650)",
    ),
    (
        "M54 V-16 report directory not created",
        REP,
        "    Path(path).parent.mkdir(parents=True, exist_ok=True)",
        "    pass",
    ),
]


def main() -> int:
    survived = 0
    for name, rel, old, new in M:
        path = R / rel
        orig = path.read_text(encoding="utf-8")
        if orig.count(old) != 1:
            print(f"{name}: PATTERN FOUND {orig.count(old)} TIMES")
            survived += 1
            continue
        path.write_text(orig.replace(old, new, 1), encoding="utf-8")
        try:
            r = subprocess.run(
                ["uv", "run", "--no-sync", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/stage00"],  # noqa: S607
                cwd=R,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            last = [line for line in r.stdout.splitlines() if "passed" in line or "failed" in line][-1:]
            killed = r.returncode != 0
            survived += not killed
            print(f"{name}: {'KILLED' if killed else 'SURVIVED'} {last}", flush=True)
        finally:
            path.write_text(orig, encoding="utf-8")
    print(f"{len(M)} mutants, {len(M) - survived} killed, {survived} survived")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
