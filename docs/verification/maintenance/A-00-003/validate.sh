#!/bin/bash
# A-00-003 validation: complete suite on the clean revision V, once per CI Python version.
S=/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/a003
while pgrep -f "pytest -q -p no:cacheprovider$" >/dev/null; do sleep 20; done
for v in 312 313; do
  cd $S/v$v
  export CITERIFT_WIKI_NETWORK_LOCK=$S/gate-$v.lock
  start=$(date -u +%s)
  PYTHONPATH=src .venv/bin/python -P -m pytest -q -p no:cacheprovider --citerift-report $S/test-report-py3.${v#3}.json > $S/validation-py3.${v#3}.log 2>&1
  rc=$?
  end=$(date -u +%s)
  echo "exit $rc; wall $((end-start)) s; python $(.venv/bin/python -V)" >> $S/validation-py3.${v#3}.log
  echo "git status after the run:" >> $S/validation-py3.${v#3}.log
  git status --porcelain=v1 --untracked-files=all >> $S/validation-py3.${v#3}.log
done
