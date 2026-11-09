# Reuse-template sources retained for F4 (2026-10-29)

F4 asks that numbered reuse arguments be resolved "against the actual supported template implementation and
MediaWiki rules". The calibration evidence kept only the content hashes of these templates, so their current source
was requested once more by `../template_sources.py`, through the production shared network gate. That means one
request in flight on the host, at least 10 s between attempts, and Retry-After honoured and recorded for every
process. No other process used the gate at the time.

| Run | What | Attempts | Answers |
|---|---|---|---|
| `run-1-en/` | enwiki `Template:R`, then `Module:R` | 6 | 4 refusals (two 274-byte "too many requests" bodies, two 1966-byte Wikimedia error pages), then 2 × 200 |
| `run-2-ar/` | arwiki `قالب:استشهاد متعدد` | 2 | 429 (Retry-After 21), then 200 |
| `run-3-ar-ref/` | arwiki `قالب:R/ref` (redirect to `قالب:استشهاد متعدد/ref`) | 4 | 429 (Retry-After 25), 429 (1), 429 (1), then 200 |

That is 12 attempts, 7 of them refused, and about 40 kB of bodies (40,513 bytes).

**Disclosure.** The script's first version wrote its log only at the end. Run 1 stopped at its own 6-request
ceiling before it could start arwiki, and its log was lost. The 6 bodies are retained under their SHA-256. Their
order and times come from the file modification times (14:49:12, 14:50:00, 14:50:10, 14:50:21, 14:51:00 and
14:51:11 UTC); the exact status codes of the four refusals are not retained. The script was then changed to write
`log.json` after every attempt, and runs 2 and 3 have complete logs.

## What the sources say (the rules implemented in `src/citerift/wiki/source.py`, `Scanner._reuse`)

- **enwiki** `Template:R` (revision 1380062808) is `{{#invoke:R|r}}`. `Module:R` (revision 1382388315) reads its
  arguments through `Module:Arguments`, which trims every value and drops blank ones.
  - First name: `firstArg(args, 'name1', 'name', 'n1', 'n', 1)`.
  - Name k ≥ 2: `firstArg(args, 'name'..k, 'n'..k, k)`, while one exists.
  - Group: `firstArg(args, 'group', 'grp', 'g')`.
  - The `reference…` / `annotation…` aliases put text into a note, and `style=sub` makes a subreference.
- **arwiki** `قالب:استشهاد متعدد` (revision 46208498; `قالب:R` redirects to it) passes `{{{1}}}`, then `{{{2}}}` …
  `{{{9}}}`, to `قالب:استشهاد متعدد/ref` (revision 63007181), which writes `{{#tag:ref||name=…|group=…}}`.
  - Each `#if` test for names 2 to 9 is nested inside the previous one, so an empty name hides all later names.
  - A non-blank 10th name shows an error instead of a use.
- **MediaWiki** (PPFrame): unnamed arguments are numbered 1, 2, … among unnamed arguments only. A named argument's
  key is its trimmed name: `1=` sets position 1, and `01=` is the named key "01". A repeated key takes its last
  value. A Lua module receives the same key-to-value table whichever way a call wrote its arguments.
