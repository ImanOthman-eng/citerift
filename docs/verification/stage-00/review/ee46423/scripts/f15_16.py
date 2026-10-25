import sys, json
from datetime import timedelta
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status, Actor
d = W / "exp/f15"; sb = Sandbox(d)
assert sb.go("01", Status.AUTHORIZED).allowed and sb.go("01", Status.IN_PROGRESS).allowed
bid = sb.orc().add_blocker("01", "waiting for data", at=sb.tick())
assert sb.go("01", Status.BLOCKED).allowed
sb.commit("blocked")
g = lambda *a: sh(GOV, "--root", str(d), *a, check=False)
r = g("blocker", "resolve", "01", "resolved by engineering agent", "--id", bid, "--at", sb.tick())
print("F-15 original command (default actor):", r.returncode, r.stdout.strip())
r = g("blocker", "resolve", "01", "resolved by engineering agent", "--id", bid, "--actor", "external-agent", "--recorded-by", "external-agent", "--at", sb.tick())
print("F-15 variant: engineering agent passes --actor external-agent --recorded-by external-agent:", r.returncode, r.stdout.strip())
print("   last history entry:", {k: reg(d)["history"][-1][k] for k in ("stage", "from", "to", "actor", "recorded_by")})

# F-16 original
d = W / "exp/f16"; sb = Sandbox(d)
assert sb.go("01", Status.AUTHORIZED).allowed
r = g2 = sh(GOV, "--root", str(d), "transition", "01", "IN_PROGRESS", "--actor", "external-agent", "--reason", "x", "--at", "2030-01-01T00:00:00Z", check=False)
print("F-16 original (--at 2030):", r.returncode, r.stdout.strip().replace("\n", " | "))
# F-16 variant 1: --at 4 minutes ahead (inside the allowed skew), then an immediate correct-clock transition
import citerift.governance.orchestrator as O
ahead = O.utc_now(timedelta(minutes=4))
r = sh(GOV, "--root", str(d), "transition", "01", "IN_PROGRESS", "--actor", "external-agent", "--reason", "x", "--at", ahead, "--apply", check=False)
print(f"F-16 variant: --at {ahead} (now+4min):", r.returncode, r.stdout.strip().splitlines()[0])
r = sh(GOV, "--root", str(d), "blocker", "add", "01", "real-time blocker", check=False)
print("   then a correct-clock blocker add right away:", r.returncode, r.stdout.strip().replace("\n", " | ")[:300])
# F-16 variant 2: writer whose clock is 2 hours fast (simulated by patching utc_now), then a correct machine
d = W / "exp/f16_fastclock"; sb = Sandbox(d)
real = O.utc_now
O.utc_now = lambda offset=timedelta(0): real(offset + timedelta(hours=2))
orc = O.Orchestrator(d); res = orc.propose("01", Status.AUTHORIZED, actor=Actor.OWNER, owner_ref="cmsg_FASTCLOCKREF1", reason="fast clock writer")
print("F-16 variant: fast-clock writer (clock +2h, no --at) authorizes 01:", "ALLOWED" if res.allowed else "REFUSED")
orc.apply(res); sb.commit("fast")
O.utc_now = real
check(d, "same registry checked on a machine with the correct clock")
r = sh(GOV, "--root", str(d), "transition", "01", "IN_PROGRESS", "--actor", "external-agent", "--reason", "x", check=False)
print("   correct-clock transition:", r.returncode, r.stdout.strip().replace("\n", " | ")[:400])
