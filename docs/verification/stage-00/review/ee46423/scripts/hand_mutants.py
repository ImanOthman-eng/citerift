import pathlib, subprocess, sys
R = pathlib.Path(sys.argv[1])
ORC = "src/citerift/governance/orchestrator.py"; PR = "src/citerift/governance/pytest_report.py"; MEM = "src/citerift/governance/memory.py"
M = [
 ("H1 amendment must predate the reopening: time comparison removed", ORC,
  'if amendment is None or amendment["kind"] != "correction" or amendment["recorded_at"] > at:',
  'if amendment is None or amendment["kind"] != "correction":'),
 ("H2 --ignore not treated as narrowing", PR, '        "ignore": list(config.getoption("ignore") or []),\n', ''),
 ("H3 deselected count ignored", PR, 'and not selection["deselected"] and not totals.get("not_run")', 'and not totals.get("not_run")'),
 ("H4 owned-path gate evidence not accepted as pinned", ORC, 'elif ref in manifest_paths or self._owned(stage, ref):', 'elif ref in manifest_paths:'),
 ("H5 topic normalization removed", MEM, '    return " ".join(topic.replace("_", "-").split()).casefold()', '    return topic'),
 ("H6 clock skew widened to 10 years", ORC, 'MAX_CLOCK_SKEW = timedelta(minutes=5)', 'MAX_CLOCK_SKEW = timedelta(days=3650)'),
 ("H7 owner-ref reuse compared with first verification only", ORC, 'if h["seq"] < verified_at[-1] and h["owner_ref"] == acc["owner_ref"]', 'if h["seq"] < verified_at[0] and h["owner_ref"] == acc["owner_ref"]'),
 ("H8 heading-like detector requires an ASCII hyphen", MEM, r'_HEADING_LIKE = re.compile(r"^\s{0,3}#+\s*\**\s*([DR])\s*-?\s*\d+")', r'_HEADING_LIKE = re.compile(r"^\s{0,3}#+\s*\**\s*([DR])\s*-\s*\d+")'),
 ("H9 not_run tests ignored in the report check", "src/citerift/governance/evidence.py", 'if isinstance(totals, dict) and totals.get("not_run", 0):', 'if False:'),
 ("H10 URL gate evidence no longer counts as pinned", ORC, '                if evidence.is_url(ref):\n                    pinned = True', '                if evidence.is_url(ref):\n                    pinned = False'),
 ("H11 blocker-resolution actor ignored (always executor)", ORC, '            actor=actor,\n            recorded_by=recorded_by,\n            reason=f"all blockers resolved', '            actor=Actor(stage["executor"]),\n            recorded_by=Actor(stage["executor"]),\n            reason=f"all blockers resolved'),
 ("H12 DEFINITION_WEAK check removed", ORC, '        if stage["executor"] == Actor.ENGINEERING_AGENT:\n            for field_name in ("owned_paths"', '        if False:\n            for field_name in ("owned_paths"'),
]
for name, rel, old, new in M:
    p = R / rel; orig = p.read_text()
    if orig.count(old) != 1:
        print(f"{name}: PATTERN FOUND {orig.count(old)} TIMES", flush=True); continue
    p.write_text(orig.replace(old, new, 1))
    try:
        r = subprocess.run(["uv", "run", "--no-sync", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/stage00"], cwd=R, capture_output=True, text=True, timeout=900)
        last = [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l][-1:]
        failed = [l for l in r.stdout.splitlines() if l.startswith("FAILED")][:1]
        print(f"{name}: {'KILLED' if r.returncode else 'SURVIVED'} {last} {failed}", flush=True)
    finally:
        p.write_text(orig)
