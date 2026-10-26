import copy, json, sys
from pathlib import Path
from citerift.contracts import load_contracts
root = Path(sys.argv[1])
cs = load_contracts(root / "schemas/contracts/v1")
base = json.loads((root / "tests/stage00/fixtures/contracts/v1/valid/investigation_full.json").read_text())
assert cs.validate(base) == [], cs.validate(base)
src = {"source_id": "retraction-watch", "locator": "https://example.org/x", "retrieved_at": "2026-01-01T00:00:00Z"}
def run(label, mutate):
    rec = copy.deepcopy(base); mutate(rec); probs = cs.validate(rec)
    print(f"{label}: {'VALID' if not probs else 'INVALID -> ' + '; '.join(str(p) for p in probs[:2])}")
def conflicting(rec):
    rec["subject_paper"]["retraction_status"] = {"status": "conflicting", "value": None, "alternatives": [
        {"value": "not_retracted", "provenance": [src]}, {"value": False, "provenance": [src]}]}
run("A retraction_status conflicting with alternatives 'not_retracted' and false", conflicting)
def model_uncertain(rec):
    rec["subject_paper"]["retraction_status"] = {"status": "uncertain", "value": "retracted", "reason": "model said so",
        "model": {"name": "some-llm", "version": "1"}, "confidence": 0.97}
run("B retraction_status from a model, labelled uncertain with model+confidence", model_uncertain)
def nf_model(rec):
    rec["subject_paper"]["retraction_status"] = {"status": "uncertain", "value": "not_found_in_checked_sources", "reason": "r",
        "provenance": [src], "model": {"name": "m", "version": "1"}, "confidence": 0.99}
run("B2 not_found + model confidence 0.99", nf_model)
def ev(rec, a, b):
    rec["events"] = [{"at": a, "kind": "created", "description": "x"}, {"at": b, "kind": "checked", "description": "y"}]
run("C events 00:00:00Z then 00:00:00.5Z (chronological)", lambda r: ev(r, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00.5Z"))
run("C2 events 00:00:00.5Z then 00:00:00Z (NOT chronological)", lambda r: ev(r, "2026-01-01T00:00:00.5Z", "2026-01-01T00:00:00Z"))
run("D schema_version '1.0.0\\n' (trailing newline)", lambda r: r.__setitem__("schema_version", "1.0.0\n"))
run("D2 investigation_id with trailing newline", lambda r: r.__setitem__("investigation_id", r["investigation_id"] + "\n"))
run("D3 created_at with trailing newline", lambda r: r.__setitem__("created_at", r["created_at"] + "\n"))
run("E created_at 2026-02-31T00:00:00Z", lambda r: r.__setitem__("created_at", "2026-02-31T00:00:00Z"))
def doi(rec, v): rec["subject_paper"]["identifiers"]["doi"] = v
run("F doi with U+001C inside (Python \\S treats it as space; JS does not)", lambda r: doi(r, "10.5555/ab\x1ccd"))
