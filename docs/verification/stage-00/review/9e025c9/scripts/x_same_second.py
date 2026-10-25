"""Honest add -> block -> resolve with default times, within one second (V-11 area)."""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2/scripts")
from lib import *
from citerift.governance.orchestrator import Orchestrator, GovernanceError, utc_now
from citerift.governance.model import Status, Actor
for attempt in range(5):
    d = mk("same_second")
    O = lambda: Orchestrator(d)
    # wait for the start of a second so that the whole sequence fits in it
    t = time.time(); time.sleep(1 - (t % 1) + 0.01)
    O().transition("02", Status.AUTHORIZED, actor=Actor.OWNER, owner_ref="cmsg_AUTHORIZE0002x", reason="authorize 02")
    O().transition("02", Status.IN_PROGRESS, actor=Actor.ENGINEERING_AGENT, reason="start")
    bid = O().add_blocker("02", "waiting for a data dump")
    O().transition("02", Status.BLOCKED, actor=Actor.ENGINEERING_AGENT, reason="blocked")
    try:
        O().resolve_blocker("02", bid, "dump arrived")
        print(f"attempt {attempt}: resolve ALLOWED", utc_now())
    except GovernanceError as exc:
        print(f"attempt {attempt}: resolve REJECTED at {utc_now()}:", [str(f) for f in exc.findings])
    o = O(); print("   history times:", [h["at"] for h in o.registry["history"][-3:]], "blocker:", o.stage("02")["blockers"])
    break
