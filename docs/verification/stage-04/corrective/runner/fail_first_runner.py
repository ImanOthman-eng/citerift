"""Fail-first evidence of the runner correction (D-071 section 9).

Runs one previously exposed article (VS-1, enwiki 1381772671) on the attributed Step 8 subset index three ways, in a
temporary directory outside the repository, and prints the outcome of each:

1. the historical tool ``evaluation/tools/s13_run.py`` (unchanged) with no ``run/exports``: the first article keeps no
   export (OUTPUT_PATH_UNSAFE);
2. the corrected tool with its export-parent creation removed (a mutant): its own guard refuses to start, so no
   article can run without an export parent (and the test of the correction fails);
3. the corrected tool: the parent is prepared before the first article, and the first article exports.

Run: ``uv run python docs/verification/stage-04/corrective/runner/fail_first_runner.py``.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "tests/stage04"))
import step8_support as S8  # noqa: E402

NAME = "en-1381772671"
OLD = REPO / "docs/verification/stage-04/evaluation/tools/s13_run.py"
NEW = REPO / "docs/verification/stage-04/corrective/runner/s13_run_v2.py"
PREP = "        exports.mkdir(parents=True, exist_ok=True)\n"


def load(path: Path, name: str, source: str | None = None):  # type: ignore[no-untyped-def]
    sys.path.insert(0, str(path.parent))
    if source is not None:
        spec = importlib.util.spec_from_loader(name, loader=None)
        if spec is None:
            raise SystemExit(f"cannot load {path}")
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(path)
        exec(compile(source, str(path), "exec"), mod.__dict__)  # noqa: S102 - evidence mutant of a repository file
        return mod
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        index = S8.build_index(base / "rw")

        def campaign(k: str) -> Path:
            c = base / k / "campaign"
            shutil.copytree(S8.EN_MMR, c / "bundles" / NAME)
            return c

        old = load(OLD, "s13_run_historical")
        c = campaign("historical")
        (c / "run" / "memory").mkdir(mode=0o700, parents=True)
        r = old.run_article(NAME, "en", c, index)
        print(
            "1 historical tool:",
            "export" if r["export"] else "NO EXPORT",
            (r.get("export_error") or {}).get("error", {}).get("code"),
        )

        src = NEW.read_text(encoding="utf-8")
        if src.count(PREP) != 1:
            raise SystemExit("the export-parent line of the corrected tool was not found exactly once")
        mutant = load(NEW, "s13_run_v2_mutant", src.replace(PREP, "        pass  # MUTANT: no export parent\n"))
        c = campaign("mutant")
        try:
            mutant.prepare(c, base / "mutant-memory")
            print("2 corrected tool without the preparation: prepared (unexpected)")
        except SystemExit as exc:  # RunnerRefused: the guard that follows the preparation refuses to start
            print("2 corrected tool without the preparation: REFUSED before the first article:", type(exc).__name__)

        new = load(NEW, "s13_run_v2")
        c = campaign("corrected")
        print("3 corrected tool: run/exports exists before prepare:", (c / "run" / "exports").exists())
        op = new.prepare(c, base / "corrected-memory")
        print("3 corrected tool: run/exports exists after prepare:", (c / "run" / "exports").is_dir())
        r = new.run_article(NAME, "en", c, index, Path(op["memory_root"]))
        print("3 corrected tool:", r["lifecycle"], "verify", r["verify_passed"], "export", r["export"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
