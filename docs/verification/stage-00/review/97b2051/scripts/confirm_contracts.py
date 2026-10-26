"""Contract confirmations at 97b2051: F-08, F-10, X-11, Y-05, Y-12, Y-13 with close variants, and the claims of
docs/data-contracts.md (fixture counts, 1.0.0 fixtures still valid)."""
import copy, json, os, subprocess, sys
from pathlib import Path
W = Path(os.environ["W"]); BASE = W / "base"; sys.path.insert(0, str(BASE / "src"))
from citerift.contracts.validate import load_contracts  # noqa: E402
from citerift.contracts.formats import loads_strict  # noqa: E402
cs = load_contracts(BASE / "schemas/contracts")
fx = BASE / "tests/stage00/fixtures/contracts/v1"
base = json.loads((fx / "valid/investigation_minimal.json").read_text())
src = {"source_id": "retraction-watch", "locator": "https://example.org/rw", "retrieved_at": "2026-10-25T00:00:00Z"}
src2 = {"source_id": "crossref", "locator": "https://example.org/cr", "retrieved_at": "2026-10-25T00:00:00Z"}
def check(label, patch=None, doi=None, rec=None):
    r = copy.deepcopy(rec or base)
    if patch: r["subject_paper"].update(patch)
    if doi: r["subject_paper"]["identifiers"] = {"doi": doi}
    p = cs.validate(r)
    print(f"{'valid  ' if not p else 'INVALID'} {label}" + (f"  -> {str(p[0])[:150]}" if p else ""))
NF = {"status": "uncertain", "value": "not_found_in_checked_sources", "reason": "no record", "provenance": [src]}
print("## Y-05")
check("conflicting retracted vs retracted (two sources)", {"retraction_status": {"status": "conflicting", "value": None,
      "alternatives": [{"value": "retracted", "provenance": [src]}, {"value": "retracted", "provenance": [src2]}]}})
check("conflicting with a single alternative", {"retraction_status": {"status": "conflicting", "value": None,
      "alternatives": [{"value": "retracted", "provenance": [src]}]}})
check("conflicting alternative without provenance", {"retraction_status": {"status": "conflicting", "value": None,
      "alternatives": [{"value": "retracted"}, {"value": "correction", "provenance": [src2]}]}})
check("conflicting retracted vs 'not_retracted'", {"retraction_status": {"status": "conflicting", "value": None,
      "alternatives": [{"value": "retracted", "provenance": [src]}, {"value": "not_retracted", "provenance": [src2]}]}})
check("control: conflicting retracted vs correction", {"retraction_status": {"status": "conflicting", "value": None,
      "alternatives": [{"value": "retracted", "provenance": [src]}, {"value": "correction", "provenance": [src2]}]}})
check("retraction_date conflicting with two equal dates (status retracted)", {
      "retraction_status": {"status": "verified_fact", "value": "retracted", "provenance": [src]},
      "retraction_date": {"status": "conflicting", "value": None, "alternatives": [{"value": "2020-01-01", "provenance": [src]}, {"value": "2020-01-01", "provenance": [src2]}]}})
print("## Y-12 / F-08")
check("not_found + retraction_date uncertain with a value", {"retraction_status": NF,
      "retraction_date": {"status": "uncertain", "value": "2020", "reason": "maybe", "provenance": [src]}})
check("not_found + retraction_date conflicting", {"retraction_status": NF,
      "retraction_date": {"status": "conflicting", "value": None, "alternatives": [{"value": "2020", "provenance": [src]}, {"value": "2021", "provenance": [src2]}]}})
check("not_found + retraction_date model_inference", {"retraction_status": NF,
      "retraction_date": {"status": "model_inference", "value": "2020", "model": {"name": "m", "version": "1"}, "confidence": 0.5}})
check("control: not_found + retraction_date unavailable (null)", {"retraction_status": NF,
      "retraction_date": {"status": "unavailable", "value": None, "reason": "none"}})
check("not_found as verified_fact (no date)", {"retraction_status": {"status": "verified_fact", "value": "not_found_in_checked_sources", "provenance": [src]}})
check("not_found uncertain without provenance", {"retraction_status": {"status": "uncertain", "value": "not_found_in_checked_sources", "reason": "x"}})
check("retraction_status model_inference", {"retraction_status": {"status": "model_inference", "value": "retracted", "model": {"name": "m", "version": "1"}, "confidence": 0.9}})
check("retraction_status value false", {"retraction_status": {"status": "verified_fact", "value": False, "provenance": [src]}})
print("## Y-13 / DOI")
for d in ("10.1000.10/abc", "10.1000.10.5/abc", "10.1000/abc", "10.1000./abc", "10.1000..10/abc", "10.1000.x/abc", "10.1000/abc\n"):
    check(f"DOI {d!r}", doi=d)
print("## F-10 dates")
for v in ("2023-02-29", "2024-02-29", "2023-13", "2023"):
    check(f"retraction_date {v}", {"retraction_status": {"status": "verified_fact", "value": "retracted", "provenance": [src]},
          "retraction_date": {"status": "verified_fact", "value": v, "provenance": [src]}})
print("## documentation counts")
print("valid fixtures:", sorted(p.name for p in (fx / "valid").glob("*.json")))
print("invalid cases:", len(loads_strict((fx / "invalid_cases.json").read_text())))
print("valid fixtures validate:", {p.name: cs.validate(json.loads(p.read_text())) == [] for p in (fx / "valid").glob("*.json")})
for rev in ("ae2ce9e", "741476c"):
    names = subprocess.run(["git", "-C", str(BASE), "ls-tree", "--name-only", f"{rev}:tests/stage00/fixtures/contracts/v1/valid/"], capture_output=True, text=True).stdout.split()
    res = {n: cs.validate(json.loads(subprocess.run(["git", "-C", str(BASE), "show", f"{rev}:tests/stage00/fixtures/contracts/v1/valid/{n}"], capture_output=True, text=True).stdout)) == [] for n in names}
    print(f"1.0.0 valid fixtures at {rev} valid under 1.0.1:", res)
