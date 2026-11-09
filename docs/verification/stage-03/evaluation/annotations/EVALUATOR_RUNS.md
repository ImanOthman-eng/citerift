# Evaluator runs (FROZEN_PROTOCOL.md section 4)

Annotation took place on 2026-10-29, between about 08:43 and 09:20 UTC. It was done by ten separate evaluator
instances. Each one is a Claude Code `general-purpose` subagent with its own context. They were started by the
executor's session and ran the same model as the executor. They are AI agents, not human annotators. Their
separation from the implementation is procedural: none of them wrote or reviewed engine code, and each was told not
to read it or any extraction output. This is not human gold, institutional independence or owner review.

Each instance received exactly the text of `../EVALUATOR_BRIEF.md`, with only `{LANG}`, `{PACKETS}` and `{OUT}`
filled in. The filled-in briefs are in `briefs/`. Packets were built from the capture bundles with
`../../protocol/scripts/evaluate.py packets`; their `packet.json` files are in `packets/`, and `packet_plan.json`
maps each group to its bundles. The packets themselves (source wikitext and HTML) are byte copies of the bundle
artifacts in `../capture/bundles/`.

| Instance (group) | Articles | Split | Dispatched (UTC) | Packets taken from |
|---|---|---|---|---|
| ar-h1 | 5 | holdout positions 1-5 | 08:43 | `capture_states.snapshot.json` |
| en-h1 | 5 | holdout positions 1-5 | 08:43 | `capture_states.snapshot.json` |
| ar-c | 3 | observed challenge | 08:43 | `capture_states.snapshot.json` |
| en-c | 3 | observed challenge | 08:43 | `capture_states.snapshot.json` |
| ar-r1, ar-r2 | 3 + 3 | reserve positions 11-13, 14-16 | about 08:55 | `capture_states.snapshot2.json` |
| en-r1, en-r2 | 3 + 3 | reserve positions 11-13, 14-16 | about 09:05 | `capture_states.snapshot3.json` |
| ar-h2, en-h2 | 5 + 5 | holdout positions 6-10 | about 09:12 | `capture_states.json` after the retry pass |

Positions are in the order of `../selection/selection.json`. The first holdout groups took the first five
articles that had a complete capture at the time. The three articles whose render had been rate-limited went to
the second groups, after the retry pass. In that pass `holdout/ar-1873306` and `holdout/en-78247163` were captured
completely. `holdout/en-81119391` stayed partial (source only), so its annotation has no render ids and its
markers are `cannot_tell`.

## Reserve articles annotated before the reserve decision

FROZEN_PROTOCOL.md 7.2 adds reserve articles "in order, two at a time, up to 16, only on the counts of the locked
annotations". To save time, all six reserve articles per wiki were annotated in parallel with the holdout. Which
of them count is decided afterwards, only from locked label counts, by the mechanical rule in
`RESERVE_DECISION.json`. A reserve annotation that the rule does not need stays locked and published but is not
scored. No prediction existed when the annotations were made or when the decision was taken.

## Deviations the instances reported

These deviations are recorded in the instances' replies and in their files' `provenance`.

- **Writes outside the output directory (rule 2).** ar-h1, en-c, ar-r1, en-r1, en-r2, ar-h2 and en-h2 each wrote
  small throwaway listing or verification scripts to a helper folder in the session scratchpad
  (`scratchpad/evaltools/` or `scratchpad/eval/tools/`). Some of them deleted the folder afterwards, and en-c
  found its script already removed. The folder was shared between instances that ran at the same time, so an
  instance could have seen another's helper script. The reports describe these scripts as listing tools (element
  ids, positions, quote checks), not labels. No annotation file was written there.
- **One read-only `git status --short` (rule 2, "do not run git").** ar-h2 ran it at the end. It printed nothing
  and changed nothing.
- **No instance reported** opening `src/`, `tests/`, `simulations/`, calibration, review or protocol scripts, any
  extraction output or the network, or running a CITERIFT command. The brief did not forbid reading
  `docs/verification/stage-03/SPECIFICATION.md`, and the executor cannot prove that no instance read it. The
  instances report opening only the annotation guide and their packets.

## Judgement calls the instances flagged

Their `notes` and `unresolved_notes` hold the full list. The main ones:

- **Publisher URLs whose DOI is not under `/doi/`.** The guide's URL row names `/doi/` paths. iopscience
  `/article/10.…`, Springer `/article/10.…`, annualreviews `/content/journals/10.…` and journals.co.za
  `/doi/abs/10.…` were labelled either as whole-URL or as DOI-text `identifier_link`. The choice and the
  alternative are noted in each case.
- **Wikidata references emitted by infoboxes.** These references have no source location and are only noted
  (guide 3.3).
- **List-defined references.** Instances counted them as definitions, not as uses.
- **Retraction templates on Arabic Wikipedia.** `{{Retracted}}` does not exist there and renders as a red link,
  so it was labelled `missing_template_link_only`. Its identifiers are `marker_target`.

## Lock

`locked/ANNOTATION_LOCK.json` holds the SHA-256 of each of the 38 annotation files. Before locking, the executor
checked every file for the following, and found 0 problems over 1560 locations:

- each file parses;
- its revision, hashes and window equal its packet;
- every location satisfies `text[cp:cp+len(quote)] == quote`.

The executor changed no label. The lock and the annotations are committed before any holdout or challenge
extraction. `../scripts/run_holdout.py` refuses to run otherwise.
