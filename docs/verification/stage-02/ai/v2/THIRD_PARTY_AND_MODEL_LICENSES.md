# Third-party and model licences: optional local inference

Scope: what a developer downloads to run `LocalAmbiguityModel` (INFERENCE_GUIDE.md). The deterministic engine adds
no runtime dependency (D-022); its locked dependencies are audited by CI as before. This report does not choose a
licence for CITERIFT itself: that decision stays reserved for release.

## 1. Model weights

| Artifact | Revision | Licence | Evidence | Notes |
|---|---|---|---|---|
| mixedbread-ai/mxbai-rerank-base-v2 (selected) | `3ea9d4dffa7d12a4f366be8e275c349de9fc9865` | Apache-2.0 | `LICENSE` file in the pinned snapshot (SHA-256 `4b0dfefcb74f1e50a8df72a9f2bf0088753f8568bc479387292469b4948705d4`) and the model card metadata | Base model Qwen2.5-0.5B, Apache-2.0 per its model card. Weights, tokenizer and configuration come from the same repository and revision. No quantization or conversion: the published float32 safetensors are used as downloaded. |
| Qwen/Qwen3-Reranker-0.6B (screened, not selected) | `e61197ed45024b0ed8a2d74b80b4d909f1255473` | Apache-2.0 | model card metadata | Only used for the 40-case screening. |

Both are public, need no account or token, and were downloaded anonymously from huggingface.co. Apache-2.0 permits
use, modification and redistribution. It requires keeping the licence and any NOTICE file, and stating changes. A
redistribution of the weights must carry the `LICENSE` file. CITERIFT does not redistribute them: the guide
downloads them from the publisher.

What "open" means here. The weights and the inference software are freely available under permissive licences. The
training code and training data of these models are not published in full. So the AI component is
"open-weight, open-source runtime", not a fully open model in the stronger sense.

## 2. Inference software (`requirements/inference-cpu.txt`, hash-pinned)

From the installed distribution metadata (`inference/license-inventory-inference-cpu.json`):

| Package | Version | Licence (as declared) |
|---|---|---|
| torch | 2.14.1+cpu | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT |
| transformers | 5.19.0 | Apache 2.0 |
| tokenizers | 0.23.3 | Apache |
| safetensors | 0.8.0 | Apache |
| huggingface_hub | 2.3.0 | Apache |
| hf-xet | 1.7.0 | Apache-2.0 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| regex | 2026.9.29 | Apache-2.0 AND CNRI-Python |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| sympy, mpmath, networkx, jinja2, markupsafe, fsspec, click, idna, httpx2, httpcore2 | as pinned | BSD |
| pyyaml, filelock, anyio, h11, rich, markdown-it-py, mdurl, typer, annotated-doc, shellingham, setuptools, truststore | as pinned | MIT or ISC |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| typing_extensions | 4.16.0 | PSF-2.0 |

All are permissive. The only file-level copyleft is tqdm (MPL-2.0 AND MIT): MPL-2.0 applies to modified tqdm files
only and does not extend to CITERIFT code. No GPL or AGPL package is in the environment. No CUDA package is
installed.

Security audit: `pip-audit --strict --require-hashes` over the file reported no known vulnerability in 33 packages
(`inference/pip-audit-inference-cpu.json`). torch's `+cpu` build is not on PyPI, so torch 2.14.1 was audited
separately by version (`inference/pip-audit-torch-2.14.1.json`): no known vulnerability. Both audits ran on
2026-10-28 and only cover advisories known on that day.

## 3. Data

The model reads fields of the pinned Retraction Watch snapshot (Crossref, Retraction Watch data repository, commit
`a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4`), under the terms already recorded for Stage 01 and Stage 02. No data is
sent anywhere: inference is local and offline.
