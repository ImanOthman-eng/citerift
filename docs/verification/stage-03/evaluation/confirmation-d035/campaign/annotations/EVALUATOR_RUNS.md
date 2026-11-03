# Evaluator runs of the D-035 confirmation campaign (initial draw)

AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 8, with AMENDMENT_2026-11-02_CONFIRMATION.md section 7. The
evaluators are AI agents (Claude Code `general-purpose` subagents on Claude Sonnet; the model is recorded in each
transcript), each with its own context. The implementing agent runs on Claude Opus. These are AI labels: they are
not human gold, institutional independence or owner review.

## Instances

| Instance | Articles | Split | Packets |
|---|---|---|---|
| d035-eval-ar-h1 … ar-h4 | 6 each | arwiki initial holdout | `packets/ar-h1` … `packets/ar-h4` |
| d035-eval-en-h1, en-h2, en-h3 | 6, 5, 5 | enwiki initial holdout | `packets/en-h1` … `packets/en-h3` |

The packets were built from the final capture bundles in plan order (`packets/ASSIGNMENT.json`) by the frozen
`confirmation-2026-11/campaign/annotations/make_packets.py`, run through `../../scripts/make_packets_partial.py`.
That wrapper changes exactly one guard so that the partial capture `holdout/ar-9335702` (revision 70571172, source
only, render ATTEMPTS_EXHAUSTED) gets a packet; without it the frozen tool refuses the whole plan, while the failure
policy and `run_confirmation.py` (RR-8) require that article to be labelled. Its packet has no `render.html`, as the
unchanged brief allows ("when it was captured").

Each instance received only the text of `../../../confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md` with `{LANG}`,
`{WORK}` and `{INSTANCE}` filled in (`briefs/`). Its work directory, outside the repository, held a byte copy of
`ANNOTATION_GUIDE_v1.1.md` (sha256 `2b40bb32…cf2e`), its packets and an empty `out/`. No instance was told about the
engine, its predictions, the D-035 correction or any earlier result.

## Timeline (UTC, 2026-11-03)

- 16:09: packets and filled briefs committed (`763c1c4`), before any launch.
- 16:10:58: all seven instances started (first transcript entry of each).
- 16:13:21 to 16:14:53: last transcript entry of each instance.
- 16:15: validation and lock.

**Self-reported times.** The `provenance.started_at` and `finished_at` fields are the instances' own statements.
Those of d035-eval-ar-h1 (09:00 to 10:00) are not real times: the instance did not exist then. d035-eval-ar-h4 says
its `started_at` is when it ran its final script. The transcript times above are authoritative. The validation
checks format, quotes and window only, so these fields were not returned or changed.

## Validation and lock

- `validate_labels.py` (2026-11, unchanged) checked format, quotes, windows and hashes only (`VALIDATION.json`): all
  40 files valid at the first submission. No file was returned, edited or chosen by the executor.
- The label files were copied byte for byte into `locked/initial-ar` (24) and `locked/initial-en` (16), and each copy
  was compared with its source (`cmp`). `evaluate.py lock` wrote each `ANNOTATION_LOCK.json`; `LOCK_RECORD.json`
  records the candidate (`fff0e5b`), the amendment commit (`1483024`) and the guide's hash. They were committed before
  any extraction of these articles. No extraction of any campaign article exists.
- `evaluator_tools/` keeps the helper snippets each instance wrote in its own `tools/` directory, byte for byte, with
  `.txt` appended to the names of Python files so that the repository linters do not treat them as project code.

## Isolation audit

`audit_evaluators.py` (2026-11, unchanged) read the seven transcripts and wrote `EVALUATOR_AUDIT.json`
(`evaluator_transcript_map.json` maps each transcript to its instance):

- **No tool call** of any instance names an absolute path outside the instance's own work directory, and none runs
  git, uv, curl, wget, pip or a `citerift` command.
- **Attached by the harness, not opened by the instances:** each instance's context included the repository's
  `CLAUDE.md`, because subagents start in the repository directory. It states governance rules and contains no label,
  no engine output and no result. This is recorded as a deviation from "receives only", as in 2026-11.
- Each instance's final report is kept in `EVALUATOR_AUDIT.json` (`final_report`).

## Judgement calls the instances reported

Their `notes`, `unresolved_notes` and reports hold the full list. The recurring ones:

- DOIs in publisher URLs whose path is not exactly `/doi/10.…` (`/doi/abs/`, `/chapter/10.…`, `/article/10.…`)
  labelled `identifier_link` with a note; the same DOI inside an archive.org URL labelled `not_a_target`.
- Infobox-generated (Wikidata) footnotes and `{{Cite Q}}` / `{{Cite ODNB}}` identifiers with no source location
  left unlabelled under guide 3.3 and named in `unresolved_notes`.
- Shortcut citation templates (`{{EI2}}`, `{{FishBase}}`, `{{Cite ODNB}}`, `{{استشهاد بويب}}`) counted as citation
  templates; `{{Webarchive}}`, `{{وصلة مكسورة}}`, `{{ردمك}}`, `{{Harvnb}}` and `{{معرف جوجل سكولار}}` not.
- List-defined refs labelled as definitions; instances differ on whether such a definition is also a use of itself
  (ar-h2 yes, en-h2 and en-h3 no).
- Citation templates inside `{{PBB_Further_reading}}` (ar-h3) and `{{rma}}` (ar-h1) labelled as bibliography
  entries; `{{ran}}` anchors (ar-h1) and `{{rp}}` (en-h1) not labelled as uses.
- Infobox refs whose rendered marker order differs from source order (ar-h2 `ar-76814232`, en-h3 `en-1382220660`)
  matched by rendered text; ar-h2 found no marker for one call and set its `render_ref_id` to null.
- `ar-70571172` (no render): every `render_note_id` and `render_ref_id` null and every marker `cannot_tell`.
- No instance found a retraction, expression of concern or correction marker.
