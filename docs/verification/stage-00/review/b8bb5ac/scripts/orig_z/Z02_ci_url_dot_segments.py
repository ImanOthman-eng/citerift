"""Z-02 (variant of Y-10): the CI record check is a string-prefix test on run_url. A URL that starts with this
repository's prefix and then climbs out with '..' segments passes the schema and CI_WRONG_REPOSITORY, although
by RFC 3986 dot-segment removal it names a run of another repository."""
from urllib.parse import urljoin
from lib import new_sandbox, codes
from citerift.governance.model import Status
sb = new_sandbox("Z02")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("impl/00.txt", "x\n"); rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
repo = sb.registry()["project"]["repository"]
url = f"https://github.com/{repo}/actions/runs/1/../../../../../other-owner/other-repo/actions/runs/2"
import posixpath; print("recorded run_url:", url); print("after RFC 3986 dot-segment removal:", "https://github.com" + posixpath.normpath(url[len("https://github.com"):]))
for label, u in (("control: other repository", "https://github.com/other-owner/other-repo/actions/runs/2"), ("dot segments", url)):
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"), ci={"run_url": u, "head_sha": rev, "conclusion": "success"})
    print(f"{label}: allowed={r.allowed} {codes(r.findings)}")
    if r.allowed:
        sb.commit("verify"); print("check after verification:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
