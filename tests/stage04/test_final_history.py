"""Final corrective cycle (owner decision D-083, item 11; reviewer finding D-08): the historical evaluations, freezes
and oracles are unchanged in the working tree.

Each directory is compared, through git, with the commit that last wrote it: the P2 pre-registration and its campaign
(run, scores, lock and report included), the P pre-registration and its campaign, the two freezes and the dt-1 and
dt-2 oracles. Nothing here is a pre-registered file; the P and P2 test files keep their own checks.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
S04 = "docs/verification/stage-04"

# directory -> the commit that last wrote it (git log -1 -- <directory>, before the final cycle).
HISTORICAL = {
    f"{S04}/evaluation": "827ac1a",  # P (Step 13, D-069)
    f"{S04}/evaluation-campaign": "1064113",  # the failed P campaign (Step 14)
    f"{S04}/evaluation-p2": "10cc9d8",  # P2 (D-077)
    f"{S04}/evaluation-p2-campaign": "2b45931",  # the failed P2 campaign: RUN, SCORES, LOCK, report (D-080)
    f"{S04}/freeze": "9963908",  # freeze 1 (b5bf8ed), marked SUPERSEDED_AFTER_FAILED_04_I in the corrective cycle
    f"{S04}/freeze-2": "6dab7f8",  # freeze-2 (28ba646, D-076)
    "simulations/stage04/oracle": "244c4b6",  # dt-1 oracle (Step 4)
    "simulations/stage04/oracle-dt2": "dfee881",  # dt-2 oracle (corrective cycle)
}

pytestmark = pytest.mark.unit


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def _require_history() -> None:
    """The history is required, never skipped (CI checks out the full history)."""
    for commit in HISTORICAL.values():
        found = subprocess.run(["git", "cat-file", "-e", commit], cwd=REPO, check=False)
        assert found.returncode == 0, f"commit {commit} is needed (a full git checkout)"


@pytest.mark.parametrize("directory", sorted(HISTORICAL))
def test_historical_directory_is_unchanged(directory: str) -> None:
    _require_history()
    commit = HISTORICAL[directory]
    assert _git("log", "-1", "--format=%h", "--abbrev=7", "--", directory).strip().startswith(commit[:7])
    assert _git("diff", "--name-only", commit, "--", directory) == "", directory
    untracked = _git("ls-files", "--others", "--exclude-standard", "--", directory)
    assert untracked == "", untracked


def test_the_p2_campaign_outcome_files_exist_at_their_commit() -> None:
    _require_history()
    names = _git("ls-tree", "-r", "--name-only", "2b45931", f"{S04}/evaluation-p2-campaign").split()
    for leaf in ("RUN.json", "SCORES.json", "LOCK.json"):
        assert any(n.endswith("/" + leaf) for n in names), leaf
