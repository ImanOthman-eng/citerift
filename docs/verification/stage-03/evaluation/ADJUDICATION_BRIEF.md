# Brief given to the Stage 03 adjudicating evaluators (FROZEN_PROTOCOL.md section 4.5)

Committed before any adjudicator started. Each instance receives the text below with `{LANG}`, `{ITEMS}` and
`{OUT}` filled in. The adjudicator is a new evaluator instance, a Claude Code subagent with its own context. It
did not write the extractor and did not make the locked labels. It sees the guide, the raw artifacts, the locked
label, and the extractor's value for the disputed items only. It never sees an extraction document. The executor
never edits a label.

---

You are the adjudicating evaluator for CITERIFT Stage 03 ({LANG} Wikipedia). Earlier, separate evaluator instances
labelled some Wikipedia articles by hand under an annotation guide. Their labels were locked, and an extraction
engine was then scored against them. For the items where the two disagree, you decide whether the **locked label**
is right under the guide, or must be corrected. You are not grading the engine. The engine's value is shown only
so that you know what is disputed. It is not evidence, and agreeing with it is not a goal.

**Read first, completely:** `docs/verification/stage-03/protocol/ANNOTATION_GUIDE.md` in `/home/user/citerift`.
Its definitions decide every item.

**Your inputs:** `{ITEMS}` holds one directory per article, each with a `disputed_items.json`. That file names:

- the article's packet directory: `source.wikitext`, `render.html`, and `packet.json` with the window;
- the locked annotation file;
- the disputed items. For each item it gives the item's kind, the locked label where one exists, and the engine's
  value.

Item kinds:

- `*_missed`: the locked label has an item the engine did not find.
- `*_extra`: the engine reports an item with no locked label at that place.
- `identifier_role` / `identifier_promotion` / `identifier_key`: the locked role or key differs from the engine's.
- `marker`: the locked warning label differs from the engine's state. An engine state of `not_inspected` means the
  engine did not look, not that it disagrees.
- `render_link`: the locked `render_ref_id` differs from the engine's. `null` from the engine means it did not link.
- `binding`: the use's bound definition differs.

**For each item**, look at the raw source and HTML yourself and decide:

- `confirm`: the locked label is right under the guide. For an `*_extra` item, confirm means "under the guide this
  is not an item, so the locked label correctly has none".
- `correct`: the locked label is wrong under the guide. Give the corrected label in the guide's format, for example
  the identifier entry with its role, or a definition entry, or a changed `templates` / `unstructured` value.

Base every decision on the guide's wording and the raw artifacts. Where the guide is ambiguous, say so, choose the
reading that follows its wording most closely, and explain why. Give a reason for every decision.

**Your output** goes in `{OUT}`, per article:

1. `decisions/<article>.json`: `{"article": ..., "adjudicator": "stage03-adjudicator-{LANG}", "started_at": ...,
   "finished_at": ..., "decisions": [{"item": n, "kind": ..., "decision": "confirm" | "correct", "reason": ...,
   "corrected_label": ... or null}]}`.
2. `adjudicated/<article>.json`: a copy of the locked annotation file with exactly your corrections applied and
   nothing else changed. Add a top-level `"adjudication": {"adjudicator": ..., "decisions_file": ..., "changed_items":
   [...]}`. Every location must still satisfy `text[cp:cp+len(quote)] == quote`. If you confirm every item of an
   article, still write the copy, with an empty `changed_items`.

**Rules (non-negotiable):**

1. Do not open, read, search, import or run anything under `src/`, `tests/`, `simulations/`, `docs/verification/stage-03/calibration/`, `docs/verification/stage-03/review/`, `docs/verification/stage-03/protocol/scripts/`, `docs/verification/stage-03/evaluation/scripts/`, or any file whose name contains `extraction`, `scores` or `disagreements`. Do not run `citerift-wiki`, git, or any CITERIFT command. Do not use the network.
2. Write only under `{OUT}`. Put any helper snippet in `{OUT}/tools/` or run it from stdin (`python3 -I -`), using only the standard library and `lxml`.
3. Decide only the listed items. Do not relabel anything else.
4. When you finish, reply with: per article, the number of items confirmed and corrected, and every correction with a one-line reason.
