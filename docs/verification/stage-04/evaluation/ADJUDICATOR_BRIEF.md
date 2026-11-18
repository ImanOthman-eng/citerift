# Brief for the Stage 04 evaluation adjudicators (ADJ)

Pre-registered with `PREREGISTRATION.md` (section 7). Owner decision D-3: disagreements are adjudicated by a third
independent Claude Sonnet instance, blinded to the prediction.

**When.** After A and B have labelled every item of a round, `s13_labels.py disagreements` lists the items on which
their labels differ in any scored field (`kind`, `same_work`, `records`, `single_identifier_attachable`; `note` is not
scored). Every such item, and only those, is adjudicated. An item on which A and B agree is final as it is.

**Instances.** Each adjudicating instance is a new Claude Sonnet agent with its own context. It is neither an A nor a
B instance and wrote no CITERIFT code. It adjudicates the disagreed items of at most six articles of one language. The
executor records the same metadata as for annotators (model name and version, times, batch, files, transcript or its
absence).

`{WORK}` is a new directory outside the repository holding only:

- `ANNOTATION_GUIDE.md`;
- `items/<article>.json`: the packet of each article, as the annotators saw it;
- `disputed/<article>.json`: for each disagreed item of the article, its `item_id` and the two labels, `A` and `B`
  (with their notes);
- an empty `out/`.

No Stage 04 output exists when adjudication runs (the one prediction run starts only after every round is locked), so
none can be shown.

---

You are adjudicator instance `{INSTANCE}` of a research evaluation of a tool that relates Wikipedia citations to
Retraction Watch records. Two annotators labelled citation units independently under an annotation guide, and
disagreed on the items listed for you. For each of them, you decide the final label. You are not grading a tool, and
there is no tool output.

**Read first, completely:** `{WORK}/ANNOTATION_GUIDE.md`. Its definitions decide every label.

**For each disputed item**, read the unit and its records yourself (`items/`), then read both labels and their notes
(`disputed/`). Write the label the guide requires: it may equal A's, B's, or neither (any value the guide allows).
Base it on the guide's wording and the item; where the guide is ambiguous, choose the reading that follows its
wording most closely and say so in `note`. Give a reason in `note` for every label.

**Your output:** one file `{WORK}/out/labels-{INSTANCE}.json` in the format of the guide's section 4, with
`"annotator": "ADJ"`, `"instance": "{INSTANCE}"`, your model name and version in `"model"`, your start and finish
times, and one complete label for every disputed item and for no other item.

**Rules (non-negotiable):**

1. Read and write only inside `{WORK}`. Do not open, list or search anything outside it. Do not run git, `uv` or any
   CITERIFT command. Do not use the network.
2. Put any helper snippet in `{WORK}/tools/` or run it from stdin (`python3 -I -`), using only the standard library.
3. Label only the disputed items.
4. When you finish, reply with: per article, the number of items adjudicated, and per item the field(s) in which your
   label differs from A's and from B's.
