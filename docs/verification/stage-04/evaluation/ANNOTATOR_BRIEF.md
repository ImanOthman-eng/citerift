# Brief for the Stage 04 evaluation annotators (A and B)

Pre-registered with `PREREGISTRATION.md` (section 7). Owner decision D-3: two independent Claude Sonnet instances per
item, blinded to Stage 04 predictions and to each other.

**Instances.** Each instance is a new Claude Sonnet agent with its own context, started by the executor with the text
below, `{ROLE}` (`A` or `B`), `{INSTANCE}` (for example `A-ar-03`) and `{WORK}` filled in. An instance labels the items
of at most six articles of one language. A and B instances of a batch receive the same items and never see each other's
work. No instance wrote any CITERIFT code. The executor records, per instance: the model name and version the platform
reports, the start and end time, the batch, the files given and the full transcript where the platform keeps one; a
missing transcript is recorded as missing, never reconstructed.

`{WORK}` is a new directory outside the repository holding only:

- `ANNOTATION_GUIDE.md` (this campaign's guide, unchanged);
- `items/<article>.json`: the packet of each article of the batch (unit text, identifiers, Retraction Watch records;
  nothing of Stage 04);
- an empty `out/`.

---

You are annotator `{ROLE}` (instance `{INSTANCE}`) of a research evaluation of a tool that relates Wikipedia citations
to Retraction Watch records. You label citation units by hand under an annotation guide. Your labels will be locked
before any tool output is produced; you are not grading a tool, and there is no tool output to see or to agree with.
Another annotator labels the same items independently; you never see their work.

**Read first, completely:** `{WORK}/ANNOTATION_GUIDE.md`. Its definitions decide every label.

**Your inputs:** `{WORK}/items/` holds one JSON file per article. Each has the article's wiki, title and revision and
a list `items`; each item has `item_id`, `text` (the unit's wikitext, possibly truncated and then marked
`[...TRUNCATED]`), `identifiers` and `records`.

**For every item of every article**, write one label exactly as the guide's section 2 defines it, with one value in
`records` for every record ref of that item. Read the unit text yourself; base each value on the guide's wording and
on the item. Where the item does not let you decide, answer `cannot_tell` and say why in `note`.

**Your output:** one file `{WORK}/out/labels-{INSTANCE}.json` in the format of the guide's section 4, with
`"annotator": "{ROLE}"`, `"instance": "{INSTANCE}"`, your model name and version in `"model"` as you know it, and
your start and finish times.

**Rules (non-negotiable):**

1. Read and write only inside `{WORK}`. Do not open, list or search anything outside it (not the repository, not any
   other path). Do not run git, `uv` or any CITERIFT command. Do not use the network.
2. Put any helper snippet in `{WORK}/tools/` or run it from stdin (`python3 -I -`), using only the standard library.
   A helper may read and write JSON; it never decides a label for you.
3. Label every item, and only the items given.
4. When you finish, reply with: per article, the number of items labelled, and the number of items with any
   `cannot_tell` value.
