# Brief given to the Stage 03 evaluator agents (FROZEN_PROTOCOL.md section 4)

This is the complete task text given to each evaluator instance, with only `ar-1`, `/workspace/stage03-work/final-evaluators-reserve2/ar-1` and `/workspace/stage03-work/final-evaluators-reserve2/output-ar-1`
filled in. It was committed before any evaluator started. The evaluators are separate AI agents with their own
context: they did not write the extractor, they are told not to read it or its output, and they work only from the
raw retained artifacts. This is procedural independence between AI agents, not human gold and not owner review.

---

You are the independent evaluator for CITERIFT Stage 03 (ar-1 Wikipedia). You label Wikipedia articles by
hand so that an extraction engine can later be scored against your labels. You did not build that engine and you
must not look at it.

**Read first, completely:** `/workspace/stage03-work/final-evaluators-reserve2/ANNOTATION_GUIDE.md`. It defines every label. Follow it exactly.

**Your inputs:** `/workspace/stage03-work/final-evaluators-reserve2/ar-1` holds one directory per article (`<wiki>-<revision_id>/`) with `source.wikitext`
(the article's wikitext at a pinned revision), `render.html` (the Parsoid HTML of the same revision) and
`packet.json` (the SHA-256 of each file and the window `[cp_start, cp_end)` in Unicode code points).

**Your output:** one file per article, `/workspace/stage03-work/final-evaluators-reserve2/output-ar-1/<wiki>-<revision_id>.json`, in the format of section 4 of the guide.
Write `"window": [cp_start, cp_end]` exactly as `packet.json` gives it, and copy `revision_id`, `source_sha256` and
`html_sha256` from `packet.json`.

**Rules (non-negotiable):**

1. Do not open, read, search, import or run anything under `src/`, `tests/`, `simulations/`,
   `docs/verification/stage-03/calibration/`, `docs/verification/stage-03/review/`,
   `docs/verification/stage-03/protocol/scripts/`, `/mnt/project-files/`, or any file whose name contains
   `extraction`. Do not run `citerift-wiki` or any CITERIFT command. Do not use the network.
2. Do not write anywhere except `/workspace/stage03-work/final-evaluators-reserve2/output-ar-1`. Do not modify any repository file. Do not run git.
3. Work from the raw files only. You may write small throwaway Python snippets (run with `python3 -I`) that use
   only the standard library and `lxml` to search text and list HTML elements and attributes, for example to find
   every `<ref`, every `{{cite`, every `10.` or `PMID`, every `<sup typeof="mw:Extension/ref">` and its `id` and
   `data-mw`, and every `<li id="cite_note-…">`. Do not write a general reference parser and do not reuse code from
   anywhere in the repository; decide each label yourself by looking at the text.
4. Verify every location before you write it: `text[cp:cp+len(quote)] == quote` where `text` is
   `source.wikitext` read as UTF-8. Positions are code points (Python string indices), not bytes.
5. Label everything in scope (the guide's section 2), including what looks broken or unusual. When unsure, give
   your best reading and say why in `notes`; never drop an item. Use `unresolved_notes` for anything you could not
   place.
6. Fill `provenance`: `agent` ("stage03-evaluator-ar-1"), `started_at` and `finished_at` (UTC ISO 8601), every
   file you opened with its SHA-256 (from `packet.json`, plus the guide), the tools you used, and what you could
   not decide.
7. When you finish, reply with: the list of files you wrote, per article the counts of definitions, uses and
   identifiers in the window, and any article you found hard and why. Do not summarize anything about an extraction
   engine; you have not seen one.

Put any helper script only under `/workspace/stage03-work/final-evaluators-reserve2/output-ar-1/tools/`; do not create or use any other directory.
Record the actual evaluator tool as ChatGPT/Codex in provenance; do not claim Claude authored these annotations.
