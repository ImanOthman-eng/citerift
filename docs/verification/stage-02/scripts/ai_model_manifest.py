"""Write a model manifest (citerift.model-manifest/1) for a downloaded reranker directory.

Hashes every file the runtime reads (the Hub's own .cache folder is skipped) and records the pinned source,
license, runtime, pair template, encoding and wrapper. The wrapper starts as "never select" for screening;
the finalist's calibrated thresholds are written by ai_model_run.py calibrate.

Run (inference environment): .venv-infer/bin/python -I docs/verification/stage-02/scripts/ai_model_manifest.py
    --model-dir models/qwen3-reranker-0.6b --spec qwen3 --out docs/verification/stage-02/ai/v2/manifests/qwen3.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch  # the inference environment only
import transformers

INSTRUCTION = (
    "Given a bibliographic record whose identifiers are hidden, judge whether the Document is the same "
    "published work as the Query: the same paper in the same venue and year, not a related paper, a "
    "duplicate publication elsewhere, or another version"
)
SPECS = {
    "qwen3": {
        "model_id": "Qwen/Qwen3-Reranker-0.6B",
        "source": {
            "repository": "https://huggingface.co/Qwen/Qwen3-Reranker-0.6B",
            "revision": "e61197ed45024b0ed8a2d74b80b4d909f1255473",
            "base_model": "Qwen/Qwen3-0.6B-Base",
        },
        "license": {
            "spdx": "Apache-2.0",
            "evidence": (
                "model card metadata 'license: apache-2.0' at the pinned revision; the repository has no LICENSE file"
            ),
            "base_model_license": "Apache-2.0 (Qwen3-0.6B-Base model card)",
        },
        "architecture": "Qwen3ForCausalLM",
        "template": {
            "prefix": "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and "
            'the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n',
            "body": "<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}",
            "suffix": "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n",
            "instruction": INSTRUCTION,
            "true_token": "yes",
            "true_token_id": 9693,
            "false_token": "no",
            "false_token_id": 2152,
            "source": "model card 'transformers usage' at the pinned revision; instruction written for this task",
        },
    },
    "mxbai": {
        "model_id": "mixedbread-ai/mxbai-rerank-base-v2",
        "source": {
            "repository": "https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2",
            "revision": "3ea9d4dffa7d12a4f366be8e275c349de9fc9865",
            "base_model": "Qwen2.5-0.5B (per the publisher's description)",
        },
        "license": {
            "spdx": "Apache-2.0",
            "evidence": "LICENSE file (Apache License 2.0) and model card metadata at the pinned revision",
            "base_model_license": "Apache-2.0 (Qwen2.5-0.5B model card)",
        },
        "architecture": "Qwen2ForCausalLM",
        "template": {
            "prefix": "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant."
            "<|im_end|>\n"
            "<|im_start|>user\n",
            "body": "query: {query}\ndocument: {document}\n{instruction}",
            "suffix": "<|im_end|>\n<|im_start|>assistant\n",
            "instruction": "You are a search relevance expert who evaluates how well documents match search queries. "
            "For each query-document pair, carefully analyze the semantic relationship between them, then provide "
            "your binary relevance judgment (0 for not relevant, 1 for relevant).\nRelevance:",
            "true_token": "1",
            "true_token_id": 16,
            "false_token": "0",
            "false_token_id": 15,
            "source": "chat_template.jinja and 1_LogitScore/config.json at the pinned revision (publisher prompt)",
        },
    },
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--spec", choices=sorted(SPECS), required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    spec = SPECS[args.spec]
    files = {}
    for p in sorted(args.model_dir.rglob("*")):
        rel = p.relative_to(args.model_dir).as_posix()
        if p.is_file() and not rel.startswith(".cache/") and rel != "README.md":
            files[rel] = {"size": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    manifest = {
        "format": "citerift.model-manifest/1",
        **{k: spec[k] for k in ("model_id", "source", "license", "architecture", "template")},
        "files": files,
        "weights_format": "safetensors (no pickle); trust_remote_code false",
        "runtime": {
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "requirements": "requirements/inference-cpu.txt (hash-pinned)",
            "device": "cpu",
            "threads": 4,
            "dtype": "float32",
            "batching": "none: one forward pass per query-candidate pair",
        },
        "encoding": {
            "fields": ["title", "authors", "journal", "original_year"],
            "rendering": "Title/Authors/Journal/Year lines; NFC; control characters become spaces; missing = unknown",
            "author_limits": [20, 5, 1],
            "on_too_long": "abstain INPUT_TOO_LONG; title, journal and year are never cut",
        },
        "wrapper": {"tau_s": 1e9, "tau_m": 0.0, "state": "screening: never selects"},
        "languages": (
            "publisher reports multilingual training; this project evaluates only the snapshot's titles "
            "(Latin script except one Arabic-script record): no Arabic accuracy claim"
        ),
    }
    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "files": len(files), "bytes": sum(f["size"] for f in files.values())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
