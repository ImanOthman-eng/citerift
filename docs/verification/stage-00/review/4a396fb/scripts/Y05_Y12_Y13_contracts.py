"""Y-05 (a), Y-12 (b), Y-13 (c): contract records that 1.0.1 accepts although the documentation says they cannot be
stored, and a valid identifier it rejects."""
import copy
import json

from lib import BASE
from citerift.contracts.validate import load_contracts

contracts = load_contracts(BASE / "schemas/contracts")
base = json.loads((BASE / "tests/stage00/fixtures/contracts/v1/valid/investigation_minimal.json").read_text())
src = {"source_id": "retraction-watch", "locator": "https://example.org/rw", "retrieved_at": "2026-10-25T00:00:00Z"}
src2 = {"source_id": "crossref", "locator": "https://example.org/cr", "retrieved_at": "2026-10-25T00:00:00Z"}


def check(label, paper_patch=None, doi=None):
    rec = copy.deepcopy(base)
    if paper_patch:
        rec["subject_paper"].update(paper_patch)
    if doi:
        rec["subject_paper"]["identifiers"] = {"doi": doi}
    problems = contracts.validate(rec)
    print(f"{'valid  ' if not problems else 'INVALID'} {label}" + (f"  -> {problems[0]}" if problems else ""))


# a) "Missing records are not evidence ... not_found_in_checked_sources ... always uncertain with
#    provenance" (docs/data-contracts.md). Inside a conflicting alternative it has no status at all,
#    and two sources that BOTH hold no record are stored as "sources disagree".
check("conflicting: two sources, both 'not_found_in_checked_sources'", {"retraction_status": {
    "status": "conflicting", "value": None,
    "alternatives": [{"value": "not_found_in_checked_sources", "provenance": [src]},
                     {"value": "not_found_in_checked_sources", "provenance": [src2]}]}})
check("conflicting: 'retracted' vs 'not_found_in_checked_sources' (absence stored as a counter-claim)", {
    "retraction_status": {"status": "conflicting", "value": None,
                          "alternatives": [{"value": "retracted", "provenance": [src]},
                                           {"value": "not_found_in_checked_sources", "provenance": [src2]}]}})
# b) a verified retraction date on a paper whose checked sources hold no retraction record
check("verified retraction_date with retraction_status not_found_in_checked_sources", {
    "retraction_status": {"status": "uncertain", "value": "not_found_in_checked_sources",
                          "reason": "no record", "provenance": [src]},
    "retraction_date": {"status": "verified_fact", "value": "2020-05-01", "provenance": [src]}})
# c) DOI with a subdivided registrant code, which the DOI Handbook (2.2.2) allows
check("DOI 10.1000.10/abc (subdivided prefix)", doi="10.1000.10/abc")
check("control: DOI 10.1000/abc", doi="10.1000/abc")
