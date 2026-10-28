# Running the local model from a clean checkout

The optional open-model ranker of the Evidence Ambiguity Investigator (`src/citerift/retraction/local_model.py`).
It is not needed for the deterministic engine, governance or CI, and none of them install it. Everything below runs
on a CPU with no account, API key or paid service. Network access is needed only for steps 2 and 3.

Requirements: Linux x86_64, Python 3.12, `uv` 0.11 or later, about 4 GB of free disk and 4 GiB of free memory.

## 1. Clone at the reviewed revision

```bash
git clone https://github.com/ImanOthman-eng/citerift.git && cd citerift
git checkout <revision>
```

## 2. Build the inference environment (hash-pinned)

```bash
uv venv .venv-infer --python 3.12
uv export --locked --no-dev --no-emit-project --no-header --format requirements.txt -o /tmp/core-requirements.txt
uv pip install --python .venv-infer/bin/python --require-hashes -r /tmp/core-requirements.txt
uv pip install --python .venv-infer/bin/python --require-hashes \
  --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
  -r requirements/inference-cpu.txt
uv pip install --python .venv-infer/bin/python --no-deps .
```

`requirements/inference-cpu.txt` pins torch 2.14.1+cpu (no CUDA packages) and transformers 5.19.0, every package with
its SHA-256. `.venv-infer/` is in `.gitignore`. The audit of this file is in `inference/`: no known
vulnerabilities (pip-audit; torch was audited as 2.14.1, because its `+cpu` build is not on PyPI).

## 3. Download the pinned weights (public, no account)

```bash
.venv-infer/bin/python -I -c "
from huggingface_hub import snapshot_download
snapshot_download('mixedbread-ai/mxbai-rerank-base-v2',
                  revision='3ea9d4dffa7d12a4f366be8e275c349de9fc9865',
                  local_dir='models/mxbai-rerank-base-v2',
                  allow_patterns=['*.json', '*.txt', '*.jinja', '*.safetensors', 'LICENSE'])"
```

`models/` is in `.gitignore`. The adapter checks the size and SHA-256 of every file against
`src/citerift/retraction/model_manifests/mxbai-rerank-base-v2.json` before loading, and refuses anything else.

## 4. Run offline

From here on no network is needed. The adapter sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, loads with
`local_files_only=True`, `trust_remote_code=False` and safetensors only. To prove it on Linux, run inside a network
namespace with no interfaces:

```bash
unshare -rn env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy \
  .venv-infer/bin/citerift-rde ambiguity --index <index.sqlite> --event <event id> \
  --model-dir models/mxbai-rerank-base-v2
```

(`-r` maps the current user to root inside the namespace; run as root, `unshare -n` is enough.)

The output is the deterministic baseline suggestion, unchanged, plus a `model_assessment` with the model's advisory
decision, ranked candidates and scores, reason codes, timing and token usage. Events that carry their own DOI or PMID
return `exact` and run no model.

Without weights, or with any wrong file, the assessment is `abstain` with `MODEL_UNAVAILABLE` or
`MODEL_ARTIFACT_MISMATCH`. That is not a negative finding. The model output is advisory: it is never a link, a fact or
a record change, and the protocol result decides whether any product layer may show it
(`holdout-result.json`).

## 5. CPU envelope used in the evaluation

4 threads, one worker, float32, no batching; at most 5 candidates and 512 tokens per pair; 30 s per case. Measured on
the development cases (4 vCPU container): cold initialization about 4 s, warm p95 about 2.8 s per case, peak RSS
about 3.3 GiB.
