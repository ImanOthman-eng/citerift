from __future__ import annotations

from pathlib import Path

import pytest
from sandbox_repo import Sandbox


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path / "repo")
