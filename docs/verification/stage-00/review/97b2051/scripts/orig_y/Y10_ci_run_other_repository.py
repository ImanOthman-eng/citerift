"""Y-10: the CI record of a verification is not tied to the project's repository. A run URL of
any other GitHub repository is accepted (R-004 says the run URL "is public for this repository
and can be checked by anyone"; nothing checks that it is this repository's run)."""
from lib import new_sandbox, codes
from citerift.governance.model import Status

sb = new_sandbox("y04")
print("project.repository:", sb.registry()["project"]["repository"])
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("impl/00.txt", "x\n")
rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
ci = {"run_url": "https://github.com/some-other-owner/unrelated-project/actions/runs/123456789",
      "head_sha": rev, "conclusion": "success"}
r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"), ci=ci)
print("verify with another repository's CI run: allowed =", r.allowed, codes(r.findings))
