"""Apply a named hand edit to a clone's registry (and status doc), for audit experiments."""
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); name = sys.argv[2]
p = root / "governance/stage_registry.json"
r = json.loads(p.read_text())
st = {s["id"]: s for s in r["stages"]}
h = r["history"]
def add(stage, frm, to, actor, ref=None, at="2026-10-25T15:00:00Z", **kw):
    e = {"seq": len(h) + 1, "at": at, "stage": stage, "from": frm, "to": to, "actor": actor,
         "recorded_by": "engineering-agent", "reason": "audit hand edit", "owner_ref": ref, **kw}
    h.append(e)
if name == "status_mismatch":
    st["02"]["status"] = "NOT_STARTED"; st["01"]["status"] = "NOT_STARTED"; st["01"]["authorization"] = None
elif name == "two_active":
    # 02 hand-set to IN_PROGRESS with a consistent history; also 03
    for sid in ("02", "03"):
        add(sid, "NOT_STARTED", "AUTHORIZED", "owner", "cmsg_FORGEDREF0001")
        add(sid, "AUTHORIZED", "IN_PROGRESS", "engineering-agent")
        st[sid]["status"] = "IN_PROGRESS"
        st[sid]["authorization"] = {"owner_ref": "cmsg_FORGEDREF0001", "scope": "x", "recorded_at": "2026-10-25T15:00:00Z"}
elif name == "past_violation":
    # History shows Stage 02 authorized (while 01 unaccepted and 00 IN_PROGRESS) and later withdrawn.
    # Insert the two entries between seq 3 (00 -> IN_PROGRESS) and seq 4, keeping times ordered.
    a = {"seq": 0, "at": "2026-10-25T10:40:00Z", "stage": "02", "from": "NOT_STARTED", "to": "AUTHORIZED",
         "actor": "owner", "recorded_by": "engineering-agent", "reason": "forged", "owner_ref": "cmsg_FORGEDREF0001"}
    b = dict(a, at="2026-10-25T10:41:00Z", **{"from": "AUTHORIZED", "to": "NOT_STARTED"})
    h[3:3] = [a, b]
    for i, e in enumerate(h, 1): e["seq"] = i
elif name == "acc_rev_mismatch":
    st["00"]["acceptance"]["accepted_revision"] = "30e4462e9ae71016dbc6f04cdda19106babd4a34"
elif name == "reopen_without_amendment":
    add("00", "ACCEPTED_CLOSED", "IN_PROGRESS", "owner", "cmsg_FORGEDREF0001")
    s = st["00"]; s["status"] = "IN_PROGRESS"; s["implementation"] = s["verification"] = s["acceptance"] = None
elif name == "inprogress_with_open_blocker":
    s = st["01"]
    s["blockers"].append({"id": "B-01-001", "description": "open", "opened_at": "2026-10-25T15:00:00Z", "resolved_at": None, "resolution": None})
    add("01", "AUTHORIZED", "IN_PROGRESS", "external-agent"); s["status"] = "IN_PROGRESS"
elif name == "bad_calendar":
    h[-1]["at"] = "2026-10-25T99:99:99Z"; st["00"]["acceptance"]["recorded_at"] = "2026-13-45T99:99:99Z"
elif name == "trailing_newline_ref":
    h[-1]["owner_ref"] = h[-1]["owner_ref"] + "\n"; st["00"]["acceptance"]["owner_ref"] = h[-1]["owner_ref"]
elif name == "acceptance_before_history":
    st["00"]["acceptance"]["recorded_at"] = "2026-10-25T14:37:07Z"   # = verification time, before history entry 14:52:41
    st["00"]["authorization"]["recorded_at"] = "2026-10-25T23:59:59Z"  # after everything
else:
    raise SystemExit("unknown " + name)
p.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
