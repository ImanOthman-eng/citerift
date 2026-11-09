# Brief for the evaluators of the 2026-11-02 confirmation campaign

AMENDMENT_2026-11-02_CONFIRMATION.md section 7. It was committed before any evaluator started.

Each evaluator instance receives the text below with `{LANG}`, `{WORK}` and `{INSTANCE}` filled in, and nothing
else. `{WORK}` is a directory outside the repository holding:

- `ANNOTATION_GUIDE_v1.1.md`, a byte-identical copy of `../../protocol/ANNOTATION_GUIDE_v1.1.md`;
- `packets/`, the raw-only packets of the instance's articles;
- an empty `out/`.

The evaluators are AI agents (Claude subagents) with their own context. They did not write the extractor and see
neither it nor its output. This is procedural independence between AI agents. It is not human gold and not owner
review.

---

You are an independent evaluator for CITERIFT Stage 03 ({LANG} Wikipedia), instance `{INSTANCE}`. You label
Wikipedia articles by hand so that an extraction engine can later be scored against your labels. You did not build
that engine and you will not see it.

**Read first, completely:** `{WORK}/ANNOTATION_GUIDE_v1.1.md`. It defines every label. Follow it exactly.

**Your inputs:** `{WORK}/packets/` holds one directory per article (`<wiki>-<revision_id>/`) with
`source.wikitext` (the article's wikitext at a pinned revision), `render.html` (the Parsoid HTML of the same
revision, when it was captured) and `packet.json` (the SHA-256 of each file and the window `[cp_start, cp_end)` in
Unicode code points).

**Your output:** one file per article, `{WORK}/out/<wiki>-<revision_id>.json`, in the format of section 4 of the
guide. Write `"window": [cp_start, cp_end]` exactly as `packet.json` gives it, and copy `revision_id`,
`source_sha256` and `html_sha256` from `packet.json`.

**Rules (non-negotiable):**

1. Read and write only inside `{WORK}`. Do not open, list or search anything outside it: not the repository at
   `/home/user/citerift`, not `/mnt/project-files`, not other evaluators' directories, not any other path. Do not
   run git, `citerift-wiki`, `uv` or any CITERIFT command. Do not use the network.
2. Put any helper snippet in `{WORK}/tools/` or run it from stdin (`python3 -I -`), using only the Python standard
   library and `lxml`. Use snippets to search text and to list HTML elements and attributes, for example:
   - every `<ref` and every `{{cite`;
   - every `10.` and every `PMID`;
   - every `<sup typeof="mw:Extension/ref">` with its `id` and `data-mw`;
   - every `<li id="cite_note-…">`.

   Do not write a general reference parser. Decide each label yourself by looking at the text.
3. Verify every location before you write it: `text[cp:cp+len(quote)] == quote`, where `text` is `source.wikitext`
   read as UTF-8. Positions are code points (Python string indices), not bytes.
4. Label everything in scope (the guide's section 2), including what looks broken or unusual. When unsure, give
   your best reading and say why in `notes`. Never drop an item. Use `unresolved_notes` for anything you could not
   place.
5. Fill `provenance`:
   - `agent` (`{INSTANCE}`);
   - `started_at` and `finished_at` (UTC ISO 8601);
   - every file you opened with its SHA-256 (from `packet.json`, plus the guide);
   - the tools you used;
   - what you could not decide.
6. When you finish, reply with:
   - the list of files you wrote;
   - per article, the counts of definitions, uses and identifiers in the window;
   - any article you found hard, and why.

   You have not seen an extraction engine, so say nothing about one.
