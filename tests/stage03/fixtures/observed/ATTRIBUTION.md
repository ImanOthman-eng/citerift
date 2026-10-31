# Observed regression fixtures (Wikipedia content)

These two capture bundles hold real Wikipedia content, retained unchanged as evidence for regression tests. They
were captured during Stage 03 development (`docs/verification/stage-03/calibration/`) and rebuilt through the
production capture code from the recorded answers (`build_dev_bundles.py`).

| Bundle | Wiki | Article | Page id | Revision | Revision time (UTC) |
|---|---|---|---|---|---|
| `en-1372543632` | English Wikipedia | Haruko Obokata | 41787575 | 1372543632 | 2026-09-01T04:41:51Z |
| `ar-76190003` | Arabic Wikipedia | هاروكو أوبوكاتا | 10487829 | 76190003 | 2026-08-12T15:13:27Z |

The text and the rendered HTML are by the Wikipedia contributors listed in each article's history
(`https://en.wikipedia.org/w/index.php?curid=41787575&action=history`,
`https://ar.wikipedia.org/w/index.php?curid=10487829&action=history`) and are licensed under the
Creative Commons Attribution-ShareAlike 4.0 License (CC BY-SA 4.0,
`https://creativecommons.org/licenses/by-sa/4.0/`). The exact revisions are
`https://en.wikipedia.org/w/index.php?oldid=1372543632` and `https://ar.wikipedia.org/w/index.php?oldid=76190003`.
No change was made to the content; `capture.json` records how it was obtained.

`expected.json` records the extraction expected from each bundle with the current engine (digest and summary
facts). An intended engine change that alters it must update the file in the same commit and say why.
