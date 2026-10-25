"""Contract semantics probes against R's schemas (valid full fixture as the base)."""
import copy, json, sys
from pathlib import Path
from citerift.contracts import load_contracts
root = Path(sys.argv[1])
cs = load_contracts(root / "schemas/contracts/v1")
base = json.loads((root / "tests/stage00/fixtures/contracts/v1/valid/investigation_full.json").read_text())
assert cs.validate(base) == []
src = {"source_id": "retraction-watch", "locator": "https://example.org/x", "retrieved_at": "2026-01-01T00:00:00Z"}
def run(label, mutate):
    rec = copy.deepcopy(base); mutate(rec); probs = cs.validate(rec)
    print(f"{label}: {'VALID' if not probs else 'INVALID -> ' + str(probs[0])[:150]}")
# Real Wikipedia language-edition subdomains (wikipedia.org), incl. ones with hyphens
for code in ("en", "ar", "simple", "zh-yue", "zh-min-nan", "be-tarask", "be-x-old", "roa-tara", "nds-nl", "map-bms",
             "cbk-zam", "fiu-vro", "bat-smg", "roa-rup", "zh-classical"):
    run(f"wiki language {code!r}", lambda r, c=code: r["citations"][0]["article"].__setitem__("language", c))
def dup_alts(r):
    r["subject_paper"]["retraction_status"] = {"status": "conflicting", "value": None, "alternatives": [
        {"value": "retracted", "provenance": [src]}, {"value": "retracted", "provenance": [src]}]}
run("conflicting retraction_status whose two alternatives are the same value", dup_alts)
def date_without_retraction(r):
    r["subject_paper"]["retraction_status"] = {"status": "uncertain", "value": "not_found_in_checked_sources", "reason": "no record", "provenance": [src]}
    r["subject_paper"]["retraction_date"] = {"status": "verified_fact", "value": "2020-01-01", "provenance": [src]}
run("verified retraction_date while retraction_status is not_found_in_checked_sources", date_without_retraction)
run("unavailable retraction_status with value 'retracted'", lambda r: r["subject_paper"].__setitem__("retraction_status", {"status": "unavailable", "value": "retracted", "reason": "x"}))
run("verified_fact not_found_in_checked_sources", lambda r: r["subject_paper"].__setitem__("retraction_status", {"status": "verified_fact", "value": "not_found_in_checked_sources", "provenance": [src]}))
