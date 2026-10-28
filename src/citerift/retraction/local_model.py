"""Local open-model ranker for the Evidence Ambiguity Investigator (AI Protocol v2; SPECIFICATION.md 12.4).

``LocalAmbiguityModel.rank(bundle, model_manifest, budget)`` scores each supplied candidate against the
query with a pinned, permissively licensed reranker running on the local CPU, then applies a frozen
select-or-abstain wrapper. It is the same code path for the evaluation, the CLI and any later layer.

Boundaries:

- Advisory only. The result is an ``AdvisoryAssessment``; nothing in the package accepts it as evidence, it
  has no path into the store, and this module imports neither the build nor the query modules.
- Loaded only on an explicit call. The deterministic engine never imports torch or transformers; they are
  imported here lazily, from the optional inference environment (requirements/inference-cpu.txt).
- Offline. Weights are read only from a local directory whose files must match the manifest's SHA-256
  values; nothing is downloaded and no remote code runs (``trust_remote_code=False``, safetensors only).
- Fail closed. Missing weights, a wrong artifact, a missing runtime, a bad bundle, an over-long input, a
  non-finite score or the deadline gives ``abstain`` with a reason code. It never means "not retracted".
- Scores are the reranker's yes/no logit difference: a ranking score, not a calibrated probability.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from citerift.retraction.advisory import BUNDLE_FIELDS, MAX_CANDIDATES
from citerift.retraction.canonical import canonical

MANIFEST_FORMAT = "citerift.model-manifest/1"
SCORE_TYPE = "reranker yes/no logit difference (ranking score; not a calibrated probability)"
CANDIDATE_ID = re.compile(r"^c[1-5]$")
MANIFEST_KEYS = (
    "format",
    "model_id",
    "source",
    "license",
    "files",
    "architecture",
    "runtime",
    "template",
    "encoding",
    "wrapper",
)


class Scorer(Protocol):
    """A loaded scorer: token count of a text, and the score of one complete pair text."""

    def count(self, text: str) -> int: ...

    def score(self, text: str) -> float: ...


@dataclass(frozen=True)
class Budget:
    """Per-case limits (PROTOCOL_V2.md, CPU envelope)."""

    deadline_s: float = 30.0
    max_pair_tokens: int = 512
    max_candidates: int = MAX_CANDIDATES


@dataclass(frozen=True)
class AdvisoryAssessment:
    """The model's advisory result for one bundle. Never a link, a fact or a projection input."""

    decision: str  # "select" or "abstain"
    candidate_id: str | None
    ranked: tuple[tuple[str, float], ...]
    reason_codes: tuple[str, ...]
    evidence_pointers: tuple[str, ...]
    model: dict[str, Any]
    input_sha256: str
    timing: dict[str, float]
    usage: dict[str, int]
    score_type: str = SCORE_TYPE
    problems: tuple[str, ...] = field(default=())

    def to_json(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "candidate_id": self.candidate_id,
            "ranked": [{"candidate_id": c, "score": s} for c, s in self.ranked],
            "reason_codes": list(self.reason_codes),
            "evidence_pointers": list(self.evidence_pointers),
            "model": self.model,
            "input_sha256": self.input_sha256,
            "timing": self.timing,
            "usage": self.usage,
            "score_type": self.score_type,
            "problems": list(self.problems),
            "advisory": True,
        }


class ModelUnavailable(RuntimeError):
    """The local model cannot be used; ``code`` is the abstention reason."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# ----------------------------------------------------------------------------- manifest and encoding


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(manifest).encode()).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in MANIFEST_KEYS if k not in data]
    if data.get("format") != MANIFEST_FORMAT or missing:
        raise ModelUnavailable("MANIFEST_INVALID", f"{path}: format {data.get('format')!r}, missing {missing}")
    return data


def _clean(value: Any) -> str:
    """NFC text without control characters; ``unknown`` for a missing field."""
    if value is None or value == "":
        return "unknown"
    text = unicodedata.normalize("NFC", str(value))
    return "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in text).strip() or "unknown"


def render_record(record: dict[str, Any], max_authors: int) -> tuple[str, bool]:
    """The frozen field-aware rendering of one record (title, authors, journal, year), and whether the author
    list was shortened. Title, journal and year are never cut: a pair that does not fit abstains instead."""
    names = [n.strip() for n in str(record.get("authors") or "").split(";") if n.strip()]
    shown = names[:max_authors]
    cut = len(names) > len(shown)
    authors = "; ".join(_clean(n) for n in shown) if shown else "unknown"
    if cut:
        authors += f" (and {len(names) - len(shown)} more)"
    year = record.get("original_year")
    lines = [
        f"Title: {_clean(record.get('title'))}",
        f"Authors: {authors}",
        f"Journal: {_clean(record.get('journal'))}",
        f"Year: {year if isinstance(year, int) else 'unknown'}",
    ]
    return "\n".join(lines), cut


def pair_text(manifest: dict[str, Any], query: str, document: str) -> str:
    t = manifest["template"]
    return str(
        t["prefix"] + t["body"].format(instruction=t["instruction"], query=query, document=document) + t["suffix"]
    )


def bundle_problems(bundle: Any, budget: Budget) -> list[str]:
    if not isinstance(bundle, dict) or set(bundle) != {"query", "candidates"}:
        return ["the bundle must have exactly the keys query and candidates"]
    out = []
    records = [("query", bundle["query"])]
    cands = bundle["candidates"]
    if not isinstance(cands, list):
        return ["candidates must be a list"]
    if len(cands) > budget.max_candidates:
        out.append(f"{len(cands)} candidates; at most {budget.max_candidates}")
    ids = [c.get("candidate_id") if isinstance(c, dict) else None for c in cands]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and CANDIDATE_ID.match(i) for i in ids):
        out.append(f"candidate ids must be distinct c1..c5: {ids}")
    records += [(f"candidate {i}", c) for i, c in zip(ids, cands, strict=True)]
    for name, r in records:
        if not isinstance(r, dict):
            out.append(f"{name} is not an object")
            continue
        extra = set(r) - set(BUNDLE_FIELDS) - {"candidate_id"}
        if extra:
            out.append(f"{name} has unexpected fields {sorted(extra)}")
        for k in ("title", "authors", "journal"):
            if r.get(k) is not None and not isinstance(r.get(k), str):
                out.append(f"{name}.{k} is not text")
        y = r.get("original_year")
        if y is not None and (not isinstance(y, int) or isinstance(y, bool)):
            out.append(f"{name}.original_year is not an integer")
    if not out and not str(bundle["query"].get("title") or "").strip():
        out.append("the query has no title")
    return out


def decide(scores: Sequence[tuple[str, float]], wrapper: dict[str, Any]) -> tuple[str, str | None]:
    """Frozen wrapper: select the top candidate iff its score >= tau_s and it leads the second by >= tau_m."""
    if not scores:
        return "abstain", None
    ranked = sorted(scores, key=lambda cs: (-cs[1], cs[0]))
    top = ranked[0][1]
    margin = top - ranked[1][1] if len(ranked) > 1 else math.inf
    if top >= wrapper["tau_s"] and margin >= wrapper["tau_m"]:
        return "select", ranked[0][0]
    return "abstain", None


# ----------------------------------------------------------------------------- the real backend


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifacts(model_dir: Path, manifest: dict[str, Any]) -> None:
    """Every manifest file is present with its pinned size and SHA-256; raises ModelUnavailable otherwise."""
    if not model_dir.is_dir():
        raise ModelUnavailable("MODEL_UNAVAILABLE", f"no local model directory {model_dir}")
    for name, pin in sorted(manifest["files"].items()):
        path = model_dir / name
        if not path.is_file():
            raise ModelUnavailable("MODEL_UNAVAILABLE", f"{name} is missing from {model_dir}")
        if path.stat().st_size != pin["size"] or sha256_file(path) != pin["sha256"]:
            raise ModelUnavailable("MODEL_ARTIFACT_MISMATCH", f"{name} does not match the manifest")


class TransformersYesNoScorer:
    """A causal-LM reranker scored by the logit difference of its answer tokens, on CPU, unbatched."""

    def __init__(self, model_dir: Path, manifest: dict[str, Any]):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            # The optional stack, imported only when a model is loaded (it is not a project dependency).
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            raise ModelUnavailable("RUNTIME_UNAVAILABLE", f"optional inference stack not installed: {exc}") from exc
        rt = manifest["runtime"]
        found = {"torch": torch.__version__, "transformers": transformers.__version__}
        if found != {"torch": rt["torch"], "transformers": rt["transformers"]}:
            raise ModelUnavailable("RUNTIME_MISMATCH", f"runtime {found} is not the pinned {rt}")
        config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
        if config.get("architectures") != [manifest["architecture"]]:
            raise ModelUnavailable("MODEL_ARTIFACT_MISMATCH", f"architecture {config.get('architectures')}")
        torch.set_num_threads(int(rt["threads"]))
        dtype = {"float32": torch.float32, "bfloat16": torch.bfloat16}[rt["dtype"]]
        self._torch = torch
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            str(model_dir), local_files_only=True, trust_remote_code=False
        )
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            str(model_dir), local_files_only=True, trust_remote_code=False, use_safetensors=True, dtype=dtype
        ).eval()
        t = manifest["template"]
        for token, pinned in ((t["true_token"], t["true_token_id"]), (t["false_token"], t["false_token_id"])):
            if self.tokenizer.convert_tokens_to_ids(token) != pinned:
                raise ModelUnavailable("MODEL_ARTIFACT_MISMATCH", f"token {token!r} is not id {pinned}")
        self.true_id, self.false_id = t["true_token_id"], t["false_token_id"]

    def count(self, text: str) -> int:
        return len(self.tokenizer(text, add_special_tokens=False).input_ids)

    def score(self, text: str) -> float:
        ids = self.tokenizer(text, add_special_tokens=False, return_tensors="pt")
        with self._torch.inference_mode():
            logits = self.model(**ids).logits[0, -1].float()
        return float(logits[self.true_id] - logits[self.false_id])


# ----------------------------------------------------------------------------- the adapter


class LocalAmbiguityModel:
    """Loads the pinned local model on first use and reuses it for later calls with the same manifest."""

    def __init__(
        self,
        model_dir: Path,
        *,
        loader: Callable[[Path, dict[str, Any]], Scorer] | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ):
        self.model_dir = model_dir
        self._loader = loader or self._load_real
        self._clock = clock
        self._scorer: Scorer | None = None
        self._loaded_sha: str | None = None
        self._failure: ModelUnavailable | None = None
        self.init_s: float | None = None

    @staticmethod
    def _load_real(model_dir: Path, manifest: dict[str, Any]) -> Scorer:
        verify_artifacts(model_dir, manifest)
        return TransformersYesNoScorer(model_dir, manifest)

    def _ensure(self, manifest: dict[str, Any]) -> Scorer:
        sha = manifest_sha256(manifest)
        if self._loaded_sha != sha:
            self._scorer, self._failure, self._loaded_sha = None, None, sha
            start = self._clock()
            try:
                self._scorer = self._loader(self.model_dir, manifest)
            except ModelUnavailable as exc:
                self._failure = exc
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                self._failure = ModelUnavailable("MODEL_UNAVAILABLE", f"{type(exc).__name__}: {exc}")
            self.init_s = self._clock() - start
        if self._scorer is None:
            raise self._failure or ModelUnavailable("MODEL_UNAVAILABLE", "the model did not load")
        return self._scorer

    def rank(
        self, bundle: dict[str, Any], model_manifest: dict[str, Any], budget: Budget | None = None
    ) -> AdvisoryAssessment:
        budget = budget or Budget()
        start = self._clock()
        input_sha = hashlib.sha256(canonical(bundle).encode()).hexdigest() if isinstance(bundle, dict) else ""
        ref = {
            "model_id": model_manifest.get("model_id"),
            "revision": (model_manifest.get("source") or {}).get("revision"),
            "manifest_sha256": manifest_sha256(model_manifest),
        }

        def result(
            decision: str,
            cid: str | None,
            ranked: list[tuple[str, float]],
            reasons: list[str],
            pointers: tuple[str, ...] = (),
            usage: dict[str, int] | None = None,
            problems: list[str] | None = None,
        ) -> AdvisoryAssessment:
            return AdvisoryAssessment(
                decision,
                cid,
                tuple(ranked),
                tuple(reasons),
                pointers,
                ref,
                input_sha,
                {"init_s": round(self.init_s or 0.0, 6), "case_s": round(self._clock() - start, 6)},
                usage or {"pairs": 0, "tokens": 0},
                problems=tuple(problems or ()),
            )

        problems = bundle_problems(bundle, budget)
        if problems:
            return result("abstain", None, [], ["INVALID_BUNDLE"], problems=problems)
        if not bundle["candidates"]:
            return result("abstain", None, [], ["NO_CANDIDATES"])
        try:
            scorer = self._ensure(model_manifest)
        except ModelUnavailable as exc:
            return result("abstain", None, [], [exc.code], problems=[exc.detail])
        start = self._clock()  # the case deadline covers scoring, not the one-time initialization
        enc = model_manifest["encoding"]
        reasons: list[str] = []
        scores: list[tuple[str, float]] = []
        pairs = tokens = 0
        for cand in bundle["candidates"]:
            if self._clock() - start > budget.deadline_s:
                return result("abstain", None, [], ["TIMEOUT"], usage={"pairs": pairs, "tokens": tokens})
            text = None
            for max_authors in enc["author_limits"]:
                q, q_cut = render_record(bundle["query"], max_authors)
                d, d_cut = render_record(cand, max_authors)
                candidate_text = pair_text(model_manifest, q, d)
                n = scorer.count(candidate_text)
                if n <= budget.max_pair_tokens:
                    text = candidate_text
                    if (q_cut or d_cut) and "AUTHORS_SHORTENED" not in reasons:
                        reasons.append("AUTHORS_SHORTENED")
                    break
            if text is None:
                return result("abstain", None, [], ["INPUT_TOO_LONG"], usage={"pairs": pairs, "tokens": tokens})
            try:
                s = scorer.score(text)
            except (RuntimeError, MemoryError, ValueError) as exc:
                return result(
                    "abstain",
                    None,
                    [],
                    ["RUNTIME_ERROR"],
                    usage={"pairs": pairs, "tokens": tokens},
                    problems=[f"{type(exc).__name__}: {str(exc)[:200]}"],
                )
            pairs += 1
            tokens += n
            if not math.isfinite(s):
                return result("abstain", None, [], ["NONFINITE_SCORE"], usage={"pairs": pairs, "tokens": tokens})
            scores.append((cand["candidate_id"], round(s, 6)))
        if self._clock() - start > budget.deadline_s:
            return result("abstain", None, [], ["TIMEOUT"], usage={"pairs": pairs, "tokens": tokens})
        ranked = sorted(scores, key=lambda cs: (-cs[1], cs[0]))
        decision, cid = decide(ranked, model_manifest["wrapper"])
        if decision == "abstain":
            reasons.append("BELOW_THRESHOLD_OR_MARGIN")
            pointers: tuple[str, ...] = ()
        else:
            i = next(k for k, c in enumerate(bundle["candidates"]) if c["candidate_id"] == cid)
            pointers = tuple(f"/query/{f}" for f in BUNDLE_FIELDS) + tuple(
                f"/candidates/{i}/{f}" for f in BUNDLE_FIELDS
            )
        return result(decision, cid, ranked, reasons, pointers, {"pairs": pairs, "tokens": tokens})
