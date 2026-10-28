# Evidence Ambiguity Investigator: model selection (AI Protocol v2)

Owner authorization: directive `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT`, section 4. Binding values:
`protocol-v2.json` (part 1) and `protocol-v2-frozen.json` (part 2).

## 1. Requirements every product model must meet

- Freely obtainable public weights, with a permissive licence on the model and its base model.
- Self-hosted on open-source software on the local CPU. No paid provider, API key, subscription or hosted endpoint.
  Claude, OpenAI, Gemini and the session agent are not the product model.
- Safetensors only, `trust_remote_code=False`, offline after setup. A pinned revision with every file hashed.
- Within the CPU envelope (`protocol-v2.json`, `cpu_envelope`): artifact at most 2 GiB, model RSS at most 4 GiB,
  4 threads, 512 tokens per pair.
- No fine-tuning (directive). So the model must already score a query-document pair.

## 2. Options considered and not screened

These were excluded from their public model cards and file listings, before any model was run.

| Option | Reason not screened |
|---|---|
| BAAI/bge-reranker-v2-m3 | Its weights are about 2.27 GB, above the 2 GiB artifact limit. |
| cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | Trained on MS MARCO derivatives, whose terms restrict use to non-commercial research. A licence risk for the product. |
| Alibaba-NLP/gte-multilingual-reranker-base | Needs `trust_remote_code=True` (custom model code). |
| BAAI/bge-reranker-base | Trained for English and Chinese only. |
| A generative chat model (for example a Qwen3 1.7B GGUF build) | Needs a separate runtime and prompt-parsing for a yes/no decision a reranker already gives. More cost and attack surface with no shown benefit. |

## 3. Screened (two candidates, the same 40 development cases, offline)

| | mixedbread-ai/mxbai-rerank-base-v2 | Qwen/Qwen3-Reranker-0.6B |
|---|---|---|
| Revision | `3ea9d4dffa7d12a4f366be8e275c349de9fc9865` | `e61197ed45024b0ed8a2d74b80b4d909f1255473` |
| Licence | Apache-2.0 (LICENSE file at the revision); base Qwen2.5-0.5B, Apache-2.0 | Apache-2.0 (model card) |
| Weights | `model.safetensors`, 988,097,536 bytes | `model.safetensors`, 1,191,588,280 bytes |
| Scoring | yes/no logit difference ("1" vs "0"), publisher prompt | yes/no logit difference ("yes" vs "no"), publisher prompt |
| Correct of 40, best wrapper on the 40 | **33** (τ_s 9.75, τ_m 2) | 29 (τ_s 5.25, τ_m 2) |
| Positives with the target ranked first | 19/19 | 14/19 |
| Cold initialization | 4.0 s | 4.7 s |
| Warm p95 per case (5 pairs) | 2.70 s | 3.60 s |
| Peak process RSS | 3,304 MiB | 3,887 MiB |

The baseline gets 34 of the same 40. Both screening runs ran under `unshare -n` with the proxy variables unset
and the script's socket guard; the summaries record `network_denied: true`. Screened artifacts total
2,179,685,816 bytes (2.03 GiB), within the 4 GiB limit.

**Finalist: mxbai-rerank-base-v2**, by the preregistered rule (more correct decisions on the 40).

## 4. Calibration and freeze

The finalist alone was then run on the other 256 development cases, and the wrapper was calibrated there by the
rule in `protocol-v2.json` (420 grid points). The chosen wrapper is τ_s = 9.75, τ_m = 2.

On those 256 cases the model gets 222 right and the baseline 241, with 13 negative false selections each. The model
fixes 10 baseline errors and adds 29. This was recorded in `protocol-v2-frozen.json` before the holdout draw. The
protocol has no development futility stop and allows no change after freezing, so the frozen pipeline runs once on
the holdout as preregistered.

The frozen manifest is `src/citerift/retraction/model_manifests/mxbai-rerank-base-v2.json`. It is used by the evaluation,
by `citerift-rde ambiguity --model-dir`, and by any later layer.

## 5. Known limitations of the selected model

- Scores are ranking logits, not probabilities.
- The snapshot holds one Arabic-script record. The publisher reports multilingual training, but no Arabic accuracy
  is claimed.
- The model sees titles, authors, journal and year only. It cannot know which of two records carrying the same
  title is the original, so near-duplicate cases stay hard.
