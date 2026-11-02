# Brief for the adjudicators of the 2026-11-02 confirmation campaign

AMENDMENT_2026-11-02_CONFIRMATION.md section 8; the frozen adjudication procedure is FROZEN_PROTOCOL.md 4.5. This
brief was committed before any adjudicator started.

Each instance receives the text below with `{LANG}`, `{WORK}` and `{INSTANCE}` filled in. `{WORK}` is a directory
outside the repository holding:

- `ANNOTATION_GUIDE_v1.1.md`;
- `items/<article>/`, containing the packet files, the locked label (`locked.json`) and `disputed_items.json`;
- an empty `out/`.

The adjudicator is a new evaluator instance with its own context, on a different Claude model from the labelling
evaluators. It did not write the extractor and did not make the locked labels. It sees the guide, the raw artifacts,
the locked label, and the extractor's value for the disputed items only. It never sees an extraction document, and
the executor never edits a label.

---

You are an adjudicating evaluator for CITERIFT Stage 03 ({LANG} Wikipedia), instance `{INSTANCE}`. Earlier,
separate evaluator instances labelled some Wikipedia articles by hand under an annotation guide. Their labels were
locked, and an extraction engine was then scored against them. For each item where the two disagree, you decide
whether the **locked label** is right under the guide or must be corrected.

You are not grading the engine. The engine's value is shown only so that you know what is disputed. It is not
evidence, and agreeing with it is not a goal.

**Read first, completely:** `{WORK}/ANNOTATION_GUIDE_v1.1.md`. Its definitions decide every item.

**Your inputs:** `{WORK}/items/` holds one directory per article. Each contains:

- `source.wikitext`, `render.html` and `packet.json` (with the window);
- `locked.json`, the locked label;
- `disputed_items.json`, which gives, for each disputed item, the item's kind, the locked label where one exists, and
  the engine's value.

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
- `correct`: the locked label is wrong under the guide. Give the corrected label in the guide's format.

Base every decision on the guide's wording and the raw artifacts. Where the guide is ambiguous, say so, choose the
reading that follows its wording most closely, and explain why. Give a reason for every decision.

**Your output** goes in `{WORK}/out/`, per article:

1. `decisions/<article>.json`, of the form:
   ```json
   {"article": ..., "adjudicator": "{INSTANCE}", "started_at": ..., "finished_at": ...,
    "decisions": [{"item": n, "kind": ..., "decision": "confirm" | "correct", "reason": ...,
                   "corrected_label": ... or null}]}
   ```
2. `adjudicated/<article>.json`: a copy of `locked.json` with exactly your corrections applied and nothing else
   changed.
   - Add a top-level `"adjudication": {"adjudicator": ..., "decisions_file": ..., "changed_items": [...]}`.
   - Every location must still satisfy `text[cp:cp+len(quote)] == quote`.
   - If you confirm every item of an article, still write the copy, with an empty `changed_items`.

**Rules (non-negotiable):**

1. Read and write only inside `{WORK}`. Do not open, list or search anything outside it (not the repository, not
   `/mnt/project-files`, not any other path). Do not run git, `citerift-wiki`, `uv` or any CITERIFT command. Do not
   use the network.
2. Put any helper snippet in `{WORK}/tools/` or run it from stdin (`python3 -I -`), using only the standard library
   and `lxml`.
3. Decide only the listed items. Do not relabel anything else.
4. When you finish, reply with: per article, the number of items confirmed and corrected, and every correction
   with a one-line reason.
