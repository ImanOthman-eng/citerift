# Evaluator runs of the D-036 confirmation campaign (initial draw)

AMENDMENT_2026-11-04_D036_CONFIRMATION.md section 6, which keeps the procedure of AMENDMENT_2026-11-03_D035_CONFIRMATION.md
section 8. The evaluators are AI agents (Claude Code `general-purpose` subagents on Claude Sonnet; the model is
recorded in each transcript), each with its own context. The implementing agent runs on Claude Opus. These are AI
labels: they are not human gold, institutional independence or owner review.

## Instances

| Instance | Articles | Split | Packets |
|---|---|---|---|
| d036-eval-ar-h1 … ar-h4 | 6 each | arwiki initial holdout | `packets/ar-h1` … `packets/ar-h4` |
| d036-eval-en-h1, en-h2, en-h3 | 6, 5, 5 | enwiki initial holdout | `packets/en-h1` … `packets/en-h3` |

The packets were built from the final capture bundles in plan order (`packets/ASSIGNMENT.json`) by the frozen
`confirmation-2026-11/campaign/annotations/make_packets.py`, run through `../../scripts/make_packets_partial.py` (the
packet tool of this campaign from the start). All 40 captures are complete, so every packet has its `render.html`.

Each instance received only the text of `../../../confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md` with `{LANG}`,
`{WORK}` and `{INSTANCE}` filled in (`briefs/`; each instance's first transcript message equals its brief file byte
for byte). Its work directory, outside the repository, held a byte copy of `ANNOTATION_GUIDE_v1.1.md` (sha256
`2b40bb32…cf2e`), its packets and an empty `out/`. No instance was told about the engine, its predictions, the R-038
correction, the D-035 result or any earlier failure.

## Timeline (UTC, 2026-11-04)

- 10:23: packets and filled briefs committed (`e5c1908`), before any launch.
- 10:23:58 to 10:24:29: all seven instances started (first assistant entry of each transcript).
- 10:26:20 to 10:26:25: **every instance stopped on a service usage limit** (an API error recorded in each
  transcript). At that moment the instances had written 4 (ar-h1, ar-h3, en-h1), 5 (ar-h2, en-h2), 3 (en-h3) and
  6 (ar-h4) of their files to their own `out/`.
- 13:48:45: after the limit reset, the executor resumed each instance in its own context with one fixed message,
  identical for all seven: "Your run was interrupted by a service usage limit. Continue the same task from where you
  stopped, under the same brief and rules; check which output files are already complete before writing." It carries
  no information about articles, labels, the engine or any result.
- 13:49:00 to 13:50:36: last transcript entry of each instance. Each reports that it checked the files already
  written and completed the remaining ones.
- 13:51: validation and lock.

**Deviation (recorded).** The interruption is a property of the tooling, not of the procedure: the instances are the
same instances, with the same context, brief, work directory and packets; nothing was shown to them between the two
parts except the message above. No instance was restarted, replaced or given another instance's files. The
self-reported `provenance.started_at` and `finished_at` fields are the instances' own statements; the transcript
times above are authoritative.

## Validation and lock

- `validate_labels.py` (2026-11, unchanged) checked format, quotes, windows and hashes only (`VALIDATION.json`): all
  40 files valid at the first submission. No file was returned, edited or chosen by the executor.
- The label files were copied byte for byte into `locked/initial-ar` (24) and `locked/initial-en` (16), and each copy
  was compared with its source (`cmp`, 40 identical). `evaluate.py lock` wrote each `ANNOTATION_LOCK.json`;
  `LOCK_RECORD.json` records the candidate (`8901a59`), the amendment commit (`10db8cb`) and the guide's hash. They
  were committed before any extraction of these articles. No extraction of any campaign article exists.
- `evaluator_tools/` keeps the helper snippets each instance wrote in its own `tools/` directory, byte for byte, with
  `.txt` appended to the names of Python files so that the repository linters do not treat them as project code
  (`__pycache__` directories were not copied).

## Isolation audit

`audit_evaluators.py` (2026-11, unchanged) read the seven transcripts and wrote `EVALUATOR_AUDIT.json`
(`evaluator_transcript_map.json` maps each transcript to its instance):

- **No tool call** of any instance names an absolute path outside the instance's own work directory, and none runs
  git, uv, curl, wget, pip or a `citerift` command (0 flagged calls in 132).
- **Attached by the harness, not opened by the instances:** each instance's context included the repository's
  `CLAUDE.md`, because subagents start in the repository directory. It states governance rules and contains no label,
  no engine output and no result. This is recorded as a deviation from "receives only", as in 2026-11 and D-035.
- Each instance's final report is kept in `EVALUATOR_AUDIT.json` (`final_report`).

## Judgement calls the instances reported

Their `notes`, `unresolved_notes` and reports hold the full list. The recurring ones:

- DOIs in publisher URLs whose path is not exactly `/doi/10.…` (iopscience `/article/10.…`, PLOS `article?id=10.…`)
  labelled `identifier_link` with a note; the same DOI inside an archive.org URL labelled `not_a_target`.
- Infobox-generated (Wikidata) footnotes not present in the source left unlabelled under guide 3.3 and named in
  `unresolved_notes` (ar-h1, ar-h3, ar-h4).
- Definitions starting before the window listed with `in_window: false` so that in-window uses bind to them.
- `{{Webarchive}}` and bare URLs not counted as citation templates; Harvard-style short-citation templates inside a
  composite note listed as citation templates (ar-h2, called borderline by the instance).
- en-h3 reports that its `make.py` "assembles the JSON from the `<ref>` tags it finds" while it decided roles,
  bindings and markers itself; the brief asks for no general reference parser. The executor validates format only
  and did not return or change the files; this is recorded, not judged.
- No instance found a retraction, expression of concern or correction marker.

## Reserve block 1 (enwiki)

- Reserve decision 1 (`../reserve/step-1.json`, from the committed locks only) named block `reserve1` for enwiki. It
  was captured (capture-2) and packed with the frozen window (`packets-reserve1/`, committed in `80000f2` with the
  filled brief `briefs/en-r1-1.txt`) before any label.
- **Instance d036-eval-en-r1-1 (lost, never observed).** On 2026-11-04 at about 14:01 UTC the previous executor
  session launched one Claude Sonnet instance with that brief, in a work directory of that session's container. That
  session ended before the instance's output, transcript or isolation audit was committed. The container is gone:
  on 2026-11-09 neither its work directory, nor its transcript, nor any copy under `/mnt/project-files` exists (the
  Codex continuation of 2026-11-04 found the same, `../../../../continuation/codex-d036-2026-11-04/HANDOFF.md`). No
  label of reserve1 was ever committed, read by the executor, validated or used, and no extraction of any campaign
  article exists. Whether that instance finished is unknown and is not claimed either way.
- **Instance d036-eval-en-r1-1b (fresh, owner directive of 2026-11-09, D-038).** Because the lost instance's context
  cannot be resumed, one new Claude Sonnet instance labels the same four packets. Its brief `briefs/en-r1-1b.txt` is
  the unchanged template of `../../../confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md` with `{LANG}` = English and only
  `{WORK}` and `{INSTANCE}` rebound (a new name, so that two different instances never share one). Its work
  directory holds a byte copy of guide 1.1 (sha256 `2b40bb32…cf2e`), byte copies of `packets-reserve1/en-r1-1/packets`
  (compared with `diff -r`) and an empty `out/`. The brief was committed before the launch. D-037 (OpenAI-model
  substitution) is not exercised.
- **Run of d036-eval-en-r1-1b.** One Claude Sonnet context (the model is recorded in its transcript), transcript
  2026-11-09 13:00:58 to 13:03:52 UTC, 16 tool calls. Its first message equals `briefs/en-r1-1b.txt` exactly. Its four
  files passed `validate_labels.py` (2026-11, unchanged) at first submission (`VALIDATION.json`, `en-r1-1b`); none was
  returned, edited or chosen by the executor. They are byte copies (`cmp`) in `locked/reserve1-en`, whose
  `ANNOTATION_LOCK.json` (`evaluate.py lock`) and `LOCK_RECORD.json` were committed before any extraction of these
  articles. Its helper snippets are in `evaluator_tools/en-r1-1b/` (`.txt` appended, `__pycache__` not copied).
- **Isolation audit of en-r1-1b.** `audit_evaluators.py` (2026-11, unchanged) was run on a map holding only this
  instance, because the seven initial transcripts are no longer accessible (they were in the 2026-11-04 container);
  its entry was added to `EVALUATOR_AUDIT.json` and every earlier entry kept byte-identical. No call runs git, uv,
  curl, wget, pip or a `citerift` command, and no call opens the repository, `/mnt/project-files` or another
  evaluator's directory. `CLAUDE.md` was attached by the harness, as for every earlier instance.
  **Deviation (recorded):** two of its 16 calls are flagged. In one Bash call the instance redirected the output of
  its own HTML-listing snippet (run on its own packet `en-1370070834`) to two scratch files, `/tmp/claude-0/h1.txt`
  and `/tmp/claude-0/h1s.txt`, outside its work directory, and read them back in that call and the next. Rule 1 of
  its brief says to read and write only inside the work directory, so this breaks the letter of the brief. Both files
  were created by those calls (modification time 13:01 UTC, the time of the calls) and hold only output derived from
  its own packet; nothing else outside the work directory was opened or listed. No information other than its
  authorized inputs reached the instance, so the independence condition of the protocol ("every evaluator receives
  only" its packets, the guide, an output directory and the brief) holds. The labels are kept as submitted; the two
  files are kept unchanged with the transcript in the private evidence export.
- **Its judgement calls (from its report):** an `{{sfn}}` with a single positional argument and no year labelled as a
  definition with its link target noted as unclear; unnamed refs with near-identical templates and different pages
  labelled as separate definitions; a publisher URL ending in a DOI without a `/doi/` segment labelled
  `identifier_link` and named undecided; `ref={{sfnref|…}}` inside a citation template treated as an anchor builder;
  `<ref name= HansmanGS>` read as the name `HansmanGS`.
