"""Z-02 variants: URL forms tried against the verification transition (sandbox), after the fix in 6d1fa00.
Each case is a fresh verification attempt on the same IMPLEMENTED_NOT_VERIFIED sandbox (apply=False)."""
from lib import new_sandbox, codes
from citerift.governance.model import Status
sb = new_sandbox("vZ02")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("impl/00.txt", "x\n"); rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
repo = sb.registry()["project"]["repository"]
print("sandbox repository:", repo)
P = f"https://github.com/{repo}/actions/runs/"
dotless = repo.replace("i", "ı", 1) if "i" in repo else None
cases = {
    "control: exact": P + "123",
    "control: upper-case owner/repo": f"https://github.com/{repo.upper()}/actions/runs/123",
    "dot segments (original Z-02)": P + "1/../../../../../other-owner/other-repo/actions/runs/2",
    "percent-encoded dot segments": P + "1/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/o/r/actions/runs/2",
    "trailing newline": P + "123\n",
    "query string": P + "123?x=1",
    "fragment": P + "123#x",
    "attempt suffix": P + "123/attempts/2",
    "userinfo": f"https://x@github.com/{repo}/actions/runs/123",
    "port": f"https://github.com:443/{repo}/actions/runs/123",
    "http scheme": f"http://github.com/{repo}/actions/runs/123",
    "dot segment inside the repository part": f"https://github.com/{repo}/../{repo}/actions/runs/123",
    "fullwidth digit id": P + "１２",
    "repository with a dotless i (U+0131) in place of i": f"https://github.com/{dotless}/actions/runs/123" if dotless else None,
    "repository with a dotted capital I (U+0130) in place of i": f"https://github.com/{repo.replace('i', chr(0x130), 1)}/actions/runs/123" if "i" in repo else None,
    "repository with long s (U+017F) in place of s": f"https://github.com/{repo.replace('s', chr(0x17f), 1)}/actions/runs/123" if "s" in repo else None,
    "repository with Kelvin sign (U+212A) in place of k": f"https://github.com/{repo.replace('k', chr(0x212a), 1)}/actions/runs/123" if "k" in repo.lower() else None,
}
for label, u in cases.items():
    if u is None:
        print(f"{label}: not applicable to this repository name"); continue
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, apply=False, gates=sb.gates("00"),
              ci={"run_url": u, "head_sha": rev, "conclusion": "success"})
    print(f"{label}: {u!r} -> allowed={r.allowed} {codes(r.findings)}")
# apply the first accepted non-ASCII case and confirm check stays at 0 errors
u = cases["repository with a dotless i (U+0131) in place of i"]
if u:
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"), ci={"run_url": u, "head_sha": rev, "conclusion": "success"})
    print("apply dotless-i URL: allowed", r.allowed)
    if r.allowed:
        sb.commit("verify")
        print("check after verification:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
        print("recorded run_url is ASCII:", u.isascii())
