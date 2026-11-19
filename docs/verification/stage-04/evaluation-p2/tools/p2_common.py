"""Stage 04 pre-registration P2 tooling: shared helpers (owner decisions D-069, D-076).

Evaluation-only code, derived from the historical Step 13 tooling (``evaluation/tools/s13_common.py``, unchanged). It
lives outside ``src/``, is never imported by production code and changes nothing in the frozen engine (``28ba646``,
freeze-2). Every script of ``tools/`` puts this directory on ``sys.path`` and imports from here.

- the frozen-engine identity check every P2 tool that reads or runs the engine calls first (``engine_check``);

- canonical JSON and SHA-256 helpers;
- exact Clopper-Pearson intervals (no SciPy: bisection on the exact binomial distribution);
- title normalization identical to the Step 12 exposure manifest (``build_exposure_manifest.norm_title``).
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from citerift.investigation import __version__, dt1
from citerift.investigation.adapters.detector import DETECTOR_IDENTITY
from citerift.investigation.adapters.plan import STAGE04_IDENTITY
from citerift.investigation.canonical import canon

TOOLS = Path(__file__).resolve().parent
EVALUATION = TOOLS.parent
REPO = TOOLS.parents[4]
LANGUAGES = ("ar", "en")
PARAMETERS = EVALUATION / "PARAMETERS.json"


class EngineMismatch(SystemExit):
    """The scientific engine is not the frozen freeze-2 engine P2 names: nothing may run."""


def engine_check(params: dict[str, Any] | None = None, *, require_head_trees: bool = True) -> dict[str, Any]:
    """Refuse any scientific-engine mismatch with the pinned freeze-2 engine (D-076).

    Checks, in order: the freeze manifest at the frozen content commit has the pinned canonical digest; that commit has
    the pinned tree; the running package reports the pinned engine, table, schema, claim-schema, plan and detector
    identity; and (``require_head_trees``) the trees of ``checked_paths`` at ``HEAD`` equal those of the content
    commit with no uncommitted change. Raises ``EngineMismatch`` on the first difference."""
    params = read_json(PARAMETERS) if params is None else params
    frozen = params["frozen_engine"]
    commit = frozen["content_commit"]
    try:
        tree = git("rev-parse", f"{commit}^{{tree}}")
        manifest = json.loads(git("show", f"{commit}:{frozen['freeze_manifest_path']}"))
    except subprocess.CalledProcessError as exc:
        raise EngineMismatch(f"the frozen content commit {commit} is not in this repository") from exc
    if tree != frozen["tree"]:
        raise EngineMismatch(f"the frozen content commit has tree {tree}, not {frozen['tree']}")
    manifest_digest = sha256_hex(canon(manifest, allow_float=True))
    if manifest_digest != frozen["freeze_manifest_digest"]:
        raise EngineMismatch(f"the freeze manifest digest is {manifest_digest}, not {frozen['freeze_manifest_digest']}")
    claim_schema = read_json(REPO / "schemas/investigation/v1/claim.schema.json")["x-citerift-version"]
    running = {
        "engine_version": STAGE04_IDENTITY["engine_version"],
        "package_version": __version__,
        "table_version": dt1.TABLE_VERSION,
        "schema_version": STAGE04_IDENTITY["schema_version"],
        "claim_schema_version": claim_schema,
        "plan_version": STAGE04_IDENTITY["plan_version"],
        "detector_identity": DETECTOR_IDENTITY,
    }
    if running != frozen["identity"]:
        raise EngineMismatch(f"the running engine identity {running} is not the pinned {frozen['identity']}")
    named = manifest["stage04_identity"]
    if any(named.get(k) != v for k, v in running.items() if k in named):
        raise EngineMismatch("the freeze manifest names another engine identity than the pinned one")
    out: dict[str, Any] = {"content_commit": commit, "tree": tree, "freeze_manifest_digest": manifest_digest}
    out["identity"] = running
    if require_head_trees:
        paths = frozen["checked_paths"]
        trees = {p: (git("rev-parse", f"HEAD:{p}"), git("rev-parse", f"{commit}:{p}")) for p in paths}
        bad = sorted(p for p, t in trees.items() if t[0] != t[1])
        dirty = git("status", "--porcelain", "--", *paths)
        if bad or dirty:
            raise EngineMismatch(f"the engine is not the frozen one: differing {bad}; uncommitted: {dirty[:300]}")
        out["head"] = git("rev-parse", "HEAD")
        out["trees"] = {p: t[0] for p, t in trees.items()}
    return out


def exposure_check(params: dict[str, Any] | None = None) -> Path:
    """The exposure manifest v2 P2 pins, refused when its SHA-256 differs."""
    params = read_json(PARAMETERS) if params is None else params
    path = REPO / params["exposure"]["manifest_path"]
    sha = file_sha256(path)
    if sha != params["exposure"]["manifest_sha256"]:
        raise EngineMismatch(f"the exposure manifest {path} has SHA-256 {sha}, not the pinned one")
    return path


def canonical_bytes(value: Any) -> bytes:
    """Sorted keys, no insignificant whitespace, UTF-8 (the D-036 / Step 12 convention)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    """``git <args>`` in the repository; its stripped standard output."""
    cmd = ["git", *args]
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> str:
    """Write indented, sorted JSON with a final newline; return the SHA-256 of the written bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return sha256_hex(data)


def norm_title(wiki: str, title: str) -> str:
    """NFC, ``_`` to space, trimmed; the first character upper-cased on enwiki only (exposure manifest rule)."""
    t = unicodedata.normalize("NFC", title).replace("_", " ").strip()
    if wiki == "en" and t:
        t = t[0].upper() + t[1:]
    return t


# ---------------------------------------------------------------------------------------------- exact intervals


def binom_cdf(x: int, n: int, p: float) -> float:
    """P(Bin(n, p) <= x), summed exactly term by term in log space."""
    if x < 0:
        return 0.0
    if x >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    total = 0.0
    for k in range(x + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
    return min(total, 1.0)


def _solve(f: Any, target: float) -> float:
    """The p in [0, 1] with f(p) = target for a decreasing f, by bisection to 1e-12."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2


def cp_upper(x: int, n: int, alpha: float) -> float:
    """Exact upper bound u with P(Bin(n, u) <= x) = alpha (1.0 when x = n)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if x >= n:
        return 1.0
    return _solve(lambda p: binom_cdf(x, n, p), alpha)


def cp_lower(x: int, n: int, alpha: float) -> float:
    """Exact lower bound l with P(Bin(n, l) >= x) = alpha (0.0 when x = 0)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if x <= 0:
        return 0.0
    return 1.0 - cp_upper(n - x, n, alpha)


def clopper_pearson(x: int, n: int) -> dict[str, Any]:
    """Point estimate, two-sided 95 % interval (alpha/2 = 0.025 per side) and the one-sided 95 % bounds."""
    if n == 0:
        return {
            "x": x,
            "n": 0,
            "estimate": None,
            "two_sided_95": None,
            "one_sided_95_upper": None,
            "one_sided_95_lower": None,
        }
    return {
        "x": x,
        "n": n,
        "estimate": x / n,
        "two_sided_95": [cp_lower(x, n, 0.025), cp_upper(x, n, 0.025)],
        "one_sided_95_upper": cp_upper(x, n, 0.05),
        "one_sided_95_lower": cp_lower(x, n, 0.05),
    }
