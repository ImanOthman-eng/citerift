# Evaluator runs of the confirmation campaign (initial draw)

AMENDMENT_2026-11-02_CONFIRMATION.md section 7. The evaluators are AI agents (Claude Code `general-purpose`
subagents on Claude Sonnet), each with its own context. The implementing agent runs on Claude Opus. These are AI
labels: they are not human gold, institutional independence or owner review.

## Instances

| Instance | Articles | Split | Packets |
|---|---|---|---|
| cf11-eval-ar-h1 … ar-h4 | 6 each | arwiki initial holdout | `packets/ar-h1` … `packets/ar-h4` |
| cf11-eval-en-h1, en-h2, en-h3 | 6, 5, 5 | enwiki initial holdout | `packets/en-h1` … `packets/en-h3` |
| cf11-eval-en-c1, en-c2 | 5, 5 | enwiki warning challenge | `packets/en-c1`, `packets/en-c2` |

`make_packets.py` built the packets from the final capture bundles in plan order (`packets/ASSIGNMENT.json`). Each
instance received only the text of `../../EVALUATOR_BRIEF_v1.1.md` with `{LANG}`, `{WORK}` and `{INSTANCE}` filled in
(`briefs/`). Its work directory, outside the repository, held a byte copy of `ANNOTATION_GUIDE_v1.1.md`, its
packets and an empty `out/`. Challenge instances were not told that their articles are challenge articles.

## Timeline (UTC)

- 2026-11-02 19:41: first launch of all nine instances. Every instance stopped within its first two tool calls on
  the account's five-hour usage limit (`rate_limit`, HTTP 429). No instance wrote a file: every `out/` and `tools/`
  directory was empty afterwards (checked 2026-11-03 01:55).
- 2026-11-03 01:56: the nine instances were started again with the same briefs and the same work directories.
  Their self-reported `finished_at` values lie between 01:56:55 and 02:00:50.
- The packets and filled briefs were committed (`5e2ec1d`) before the second launch.

## Validation and lock

- `validate_labels.py` checked format, quotes, windows and hashes only (`VALIDATION.json`): all 50 files valid at the
  first submission. No file was returned, edited or chosen by the executor.
- The label files were copied byte for byte into `locked/initial-ar` (24), `locked/initial-en` (16) and
  `locked/challenge-en` (10). `evaluate.py lock` wrote each `ANNOTATION_LOCK.json`; `LOCK_RECORD.json` records the
  frozen candidate (`3e51792`) and the guide's hash. They were committed before any extraction of these articles.
- `evaluator_tools/` keeps the helper snippets each instance wrote in its own `tools/` directory, byte for byte, with `.txt` appended to the names of Python files so that the repository linters do not treat them as project code.

## Isolation audit

`audit_evaluators.py` read the transcripts of both launches and of the reserve instance and wrote `EVALUATOR_AUDIT.json`:

- **For the nine initial instances, no tool call** names an absolute path outside the instance's own work directory, and none runs git, uv, curl,
  wget, pip or a `citerift` command. Relative `..` paths in the transcripts all stay inside the work directory
  (`tools/../packets`).
- **Attached by the harness, not opened by the instances:** each instance's context included the repository's
  `CLAUDE.md`, because subagents start in the repository directory. That file states governance rules (commit
  trailers, report endings, stage procedure). It contains no label, no engine output and no result. It explains
  why two reports end with a governance verdict line ("VERIFIED COMPLETE", "NOT VERIFIED"), which has no meaning for
  the labels. No project memory was attached. This is recorded as a deviation from "receives only".
- Each instance's final report is kept in `EVALUATOR_AUDIT.json` (`final_report`).

## Reserve block 1 (enwiki)

- Reserve decision 1 (`../reserve/step-1.json`, from the committed locks only) named block `reserve1` for enwiki.
  It was captured (capture-2), packed with the frozen window (`packets-reserve1/`, committed in `6f39025`) and
  labelled by one more instance, cf11-eval-en-r1-1 (Claude Sonnet, same brief), launched 2026-11-03 02:09:55.
- Its four files passed `validate_labels.py` at first submission and are locked in `locked/reserve1-en`.
- **Isolation deviation.** The audit flagged two of its 17 tool calls: it wrote its own scan listing of one packet
  (`en-1371940951`) to `/tmp/claude-0/s3.txt`, outside its work directory, and read it back. The file holds only
  lines of that packet's source text; a copy is kept as
  `evaluator_tools/en-r1-1/OUTSIDE_WORKDIR_tmp_claude-0_s3.txt`. It read no other path outside its directory.

## Judgement calls the instances reported

Their `notes`, `unresolved_notes` and reports hold the full list. The recurring ones:

- DOIs in publisher URLs whose path is not exactly `/doi/10.…` (`/doi/abs/`, `/doi/full/`, `/article/10.…`,
  `/store/10.…`, `link.springer.com/content/pdf/10.…`, a jstor or ukwhoswho path), labelled `identifier_link` with a
  note; DOIs inside archive.org snapshot URLs labelled `not_a_target`.
- Infobox-generated (Wikidata) footnotes with no source location, left unlabelled under guide 3.3.
- Shortcut or Wikidata-driven citation templates (`{{EI2}}`, `{{استشهاد بويكي بيانات}}`, `{{NRDB species}}`,
  `{{Fishbase}}`, `{{IUCN}}`) counted as citation templates; `{{Harvnb}}`-only bodies not counted.
- "Further reading" items without a citation template or DOI/PMID: two instances labelled them as unstructured
  bibliography entries, others left them out under guide 3.4.
- Challenge markers: en-c1 labelled five definitions `warning` (three expressions of concern, two retractions);
  en-c2 labelled one `warning` (expression of concern) and two `ambiguous` (`{{Erratum}}` notices).
