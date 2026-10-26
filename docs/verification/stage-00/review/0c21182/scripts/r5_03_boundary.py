"""R5-03 boundary cases, run against the revision in $BASE (its src and tests/stage00 sandbox helper).

Part A: exhaustive scan. Which non-ASCII code points match an ASCII letter under the flags the revision uses?
        The flags are read from the revision's orchestrator.py source line, not assumed.
Part B: end to end. A sandbox whose project repository is renamed to an ASCII name containing i, s, k and other
        letters; each variant URL goes through the real verification transition (apply=False). Expected on a fixed
        revision: only ASCII case variants allowed.
Part C: a record written with a dotless-i URL (applied on this revision if it is accepted) is then checked with the
        checker of $CHECK_BASE (the fixed revision), to see whether `check` also flags an already recorded URL.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from lib import BASE, W, codes, new_sandbox
from citerift.governance.model import Status

src = (BASE / "src/citerift/governance/orchestrator.py").read_text(encoding="utf-8")
line = next(l for l in src.splitlines() if 'actions/runs/[0-9]+", ci["run_url"]' in l)
flag_text = line.rsplit('ci["run_url"],', 1)[1].strip().rstrip(")").strip()
flags = eval(flag_text, {"re": re})  # e.g. "re.I" or "re.I | re.A", taken from the revision's source
print(f"revision {BASE.name}: run_url fullmatch flags in source: {flag_text}")

# Part A
ANY = re.compile("|".join("abcdefghijklmnopqrstuvwxyz"), flags)
hits = []
for cp in range(0x80, 0x110000):
    if 0xD800 <= cp <= 0xDFFF:
        continue
    ch = chr(cp)
    if ANY.fullmatch(ch):
        hits.append((f"U+{cp:04X}", [a for a in "abcdefghijklmnopqrstuvwxyz" if re.fullmatch(a, ch, flags)]))
print(f"A: non-ASCII code points matching an ASCII letter under {flag_text}: {len(hits)} {hits}")
digits = [f"U+{cp:04X}" for cp in range(0x80, 0x110000) if not 0xD800 <= cp <= 0xDFFF and re.fullmatch("[0-9]", chr(cp), flags)]
print(f"A: non-ASCII code points matching [0-9]: {digits}")

# Part B
sb = new_sandbox("r503")
reg = sb.registry()
reg["project"]["repository"] = "kis-owner/skik-repo"
sb.save_registry(reg)
sb.commit("rename repository")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("impl/00.txt", "x\n")
rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
repo = sb.registry()["project"]["repository"]
print("B: sandbox repository:", repo)


def url(r: str) -> str:
    return f"https://github.com/{r}/actions/runs/123"


def sub(old: str, new: str) -> str:
    return repo.replace(old, new, 1)


cases = {
    "exact (control)": url(repo),
    "upper-case ASCII": url(repo.upper()),
    "mixed-case ASCII": url("KiS-Owner/SkIk-Repo"),
    "U+0131 dotless i for i": url(sub("i", "ı")),
    "U+0130 capital I with dot for i": url(sub("i", "İ")),
    "U+017F long s for s": url(sub("s", "ſ")),
    "U+212A Kelvin sign for k": url(sub("k", "K")),
    "U+212A Kelvin sign in the repository name": url(repo.replace("/s" + "kik", "/sKik")),
    "all four at once": url(repo.replace("k", "K").replace("s", "ſ").replace("i", "ı")),
    "U+FF49 fullwidth i": url(sub("i", "ｉ")),
    "U+FF29 fullwidth I": url(sub("i", "Ｉ")),
    "U+0456 Cyrillic i": url(sub("i", "і")),
    "U+0049 U+0307 (I + combining dot)": url(sub("i", "İ")),
    "U+00DF sharp s for ss (none here; s+s)": url(sub("s", "ß")),
    "other repository (control)": url("kis-owner/other"),
}
for label, u in cases.items():
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, apply=False, gates=sb.gates("00"),
              ci={"run_url": u, "head_sha": rev, "conclusion": "success"})
    print(f"B: {label}: {u!r} -> allowed={r.allowed} {codes(r.findings)}")

# Part C
check_base = Path(os.environ.get("CHECK_BASE", str(BASE)))
u = cases["U+0131 dotless i for i"]
r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"),
          ci={"run_url": u, "head_sha": rev, "conclusion": "success"})
print(f"C: apply dotless-i URL on {BASE.name}: allowed={r.allowed}")
if r.allowed:
    sb.commit("verify with dotless i")
    print(f"C: check with {BASE.name} code:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
    out = subprocess.run([str(check_base / ".venv/bin/python"), "-P", "-m", "citerift.governance.cli", "--root",
                          str(sb.root), "check"], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": str(check_base / "src")})
    lines = [l for l in (out.stdout + out.stderr).splitlines() if "CI_WRONG_REPOSITORY" in l or "Consistency" in l]
    print(f"C: check of that record with {check_base.name} code: exit {out.returncode}:", " / ".join(lines))
