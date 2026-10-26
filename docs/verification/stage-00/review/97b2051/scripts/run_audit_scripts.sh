#!/bin/sh
# Re-run the audit's own probe scripts (docs/audits/stage-00-2026-10-25/scripts, copied to scripts/orig_f) at 97b2051.
# Registry edits run on clones of the accepted sandbox $W/x2/exp/base (Stage 00 and 01 accepted, built with the
# reviewed sandbox_repo.py), because the real registry at 97b2051 has Stage 00 reopened (no verification record).
PY="$W/base/.venv/bin/python"; export PYTHONPATH="$W/base/src"; F="$W/scripts/orig_f"
gov() { "$PY" -P -m citerift.governance.cli --root "$1" check | head -4 | cut -c1-220; }
echo "== contracts_probe.py (F-08, F-09, F-10)"; "$PY" "$F/contracts_probe.py" "$W/base" | cut -c1-220
for e in gate_dot drop_ci shrink_gates drop_owned_paths; do
  d="$W/x2/exp/f_$e"; rm -rf "$d"; git clone -q "$W/x2/exp/base" "$d"; "$PY" "$F/policy_edit.py" "$d" "$e"
  echo "== policy_edit.py $e (F-02/F-03)"; gov "$d"; done
for e in status_mismatch two_active past_violation acc_rev_mismatch reopen_without_amendment inprogress_with_open_blocker bad_calendar trailing_newline_ref acceptance_before_history; do
  d="$W/x2/exp/m_$e"; rm -rf "$d"; git clone -q "$W/x2/exp/base" "$d"; "$PY" "$F/mutate.py" "$d" "$e" 2>&1 | tail -1
  echo "== mutate.py $e"; gov "$d"; done
mkdir -p "$W/x2/exp/f_tmp"
echo "== reopen_liveness.py (F-11)"; "$PY" "$F/reopen_liveness.py" "$W/base" "$W/x2/exp/f_tmp" | cut -c1-220
echo "== single_active_flip.py (F-03/F-04)"; "$PY" "$F/single_active_flip.py" "$W/base" "$W/x2/exp/f_tmp" 2>&1 | cut -c1-220
