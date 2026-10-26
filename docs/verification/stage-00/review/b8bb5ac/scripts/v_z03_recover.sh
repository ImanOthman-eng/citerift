#!/bin/sh
# recover output on the clone at b8bb5ac, and Z-03 variants: a copy without .git, and git missing from PATH.
W="$1"; PY="$W/base/.venv/bin/python"
echo "== recover on \$W/base"; cd "$W/base" && PYTHONPATH="$W/base/src" "$PY" -P -m citerift.governance.cli recover; echo "exit $?"
rm -rf "$W/sandbox-vZ03" && mkdir -p "$W/sandbox-vZ03" && cd "$W/base" && git archive HEAD | tar -x -C "$W/sandbox-vZ03"
echo "== recover in a copy without .git"; cd "$W/sandbox-vZ03" && PYTHONPATH="$W/base/src" "$PY" -P -m citerift.governance.cli recover 2>&1 | grep -n -i "uncommitted\|ERROR\|HEAD" ; echo "exit $?"
mkdir -p "$W/sandbox-vZ03-bin" && ln -sf "$PY" "$W/sandbox-vZ03-bin/python"
echo "== recover in \$W/base with git missing from PATH"; cd "$W/base" && PATH="$W/sandbox-vZ03-bin" PYTHONPATH="$W/base/src" "$PY" -P -m citerift.governance.cli recover 2>&1 | grep -n -i "uncommitted\|ERROR\|HEAD\|Traceback"; echo "exit $?"
