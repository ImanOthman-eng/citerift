# Accepted Stage 00 verification package (revision 741476c)

This directory holds the verification package that the owner accepted on
2026-10-25. The package verified revision `741476c` and is recorded by history
entries 9 and 10, owner reference
`cmsg_018VCB51nDHP6HXmLU4ea5yP68JgEArkKAaUCqqYkVsnti`.

Correction A-00-001 replaced the package, so it was moved here with `git mv`
in `6ab9206`. That freed the standard file names for the new package. The
accepted package was completed after `741476c` (commits `0cda54e` and
`423187d`), so compare it with the acceptance commit `70ce78e`, not with
`741476c`:

    git diff --stat 70ce78e:docs/verification/stage-00 HEAD:docs/verification/stage-00/superseded/741476c

The command lists two kinds of difference:

- the older `superseded/ecaa845`, `superseded/2bf7d60` and `superseded/30e4462`
  directories, which stayed at `docs/verification/stage-00/superseded/`
- this README

Each of the seven artifacts and `test-report.json` still has the sha256 that
the accepted verification record at `70ce78e` pins. This was checked on
2026-10-25.

The independent review of 2026-10-25 (`docs/audits/stage-00-2026-10-25/`)
found that parts of these documents overstate what is enforced (F-21). The
corrected statements are in the parent directory. These files stay as the
record of what was accepted. Do not edit them.
