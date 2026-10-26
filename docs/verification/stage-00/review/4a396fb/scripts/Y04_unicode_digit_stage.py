"""Y-04: an open critical defect whose Stage field is written with non-ASCII decimal digits
(Arabic-Indic U+0660 or fullwidth U+FF10) passes the RISKS.md validation but does not block
the stage it names. Control: the same entry with ASCII digits blocks verification."""
from lib import new_sandbox, codes
from citerift.governance.model import Status
from citerift.governance import memory

ENTRY = """
## R-002 — Evidence hashes are computed on the wrong bytes
- Status: open
- Severity: critical
- Kind: defect
- Stage: {stage}

Synthetic critical defect for the review.
"""

for label, stage in (("ascii 00 (control)", "00"), ("arabic-indic \\u0660\\u0660", "٠٠"),
                     ("fullwidth \\uff10\\uff10", "００")):
    sb = new_sandbox("y01")
    sb.write("RISKS.md", (sb.root / "RISKS.md").read_text(encoding="utf-8") + ENTRY.format(stage=stage))
    sb.commit("record a critical defect")
    entries, problems = memory.check_risks(sb.root / "RISKS.md")
    print(f"== Stage field {label}")
    print("   memory problems:", [p.code for p in problems])
    print("   open_critical_defects('00'):", [e.id for e in memory.open_critical_defects(entries, "00")])
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    sb.write("impl/00.txt", "x\n")
    rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"), ci=sb.ci(rev))
    print("   verify allowed:", r.allowed, codes(r.findings))
    if r.allowed:
        sb.commit("verify")
        r2 = sb.go("00", Status.ACCEPTED_CLOSED)
        print("   accept allowed:", r2.allowed, codes(r2.findings))
        print("   check errors after acceptance:", codes(sb.orc().check()))

# Variant: the entry id itself. "R-٠٠١" parses as an entry id beside "R-001",
# so two entries that read as R-001 are not RISK_DUPLICATE_ID.
text = "# Risks\n" + "".join(
    f"\n## R-{i} — t\n- Status: open\n- Severity: low\n- Kind: risk\n- Stage: 00\n" for i in ("001", "٠٠١")
)
import tempfile, pathlib
p = pathlib.Path(tempfile.mkdtemp()) / "RISKS.md"
p.write_text(text, encoding="utf-8")
entries, problems = memory.check_risks(p)
print("== heading ids", [e.id for e in entries], "problems:", [x.code for x in problems])
