# Security review: the five withheld captured files (third-party presigned URL)

*CITERIFT — Created and Directed by EVE TELOS · IM*

Owner instruction of 2026-11-04, section 9 (DECISIONS.md D-036). Reviewed 2026-11-04 by the executor (Claude Code,
an AI coding agent). The URL was never requested, opened or followed: every finding below comes from reading the
local bytes. No key id, signature or object path is reproduced in this document.

## 1. What the files hold

The five files listed in `../evaluation/confirmation-d035/campaign/WITHHELD_FILES.json` are byte copies of English
Wikipedia article 614753, revision 1380218630 (its wikitext and Parsoid render, as captured on 2026-11-03, and the
two files of the evaluator packet built from them). They are three distinct git blobs, because the packet's
`source.wikitext` is the same bytes as the bundle's wikitext artifact.

The article cites a document through one URL that appears once in the wikitext and three times in the render. Read
locally, it is:

| Property | Finding |
|---|---|
| Kind | an Amazon S3 query-string authenticated URL, signature version 2 (`AWSAccessKeyId`, `Expires`, `Signature`, plus a `response-content-disposition` file name) on the host `s3.amazonaws.com` |
| Key material | the 20-character access key **id** of a third party's AWS account (pattern `AKIA[0-9A-Z]{16}`) and a 28-character request signature. No secret access key and no session token. An access key id is an identifier, not a secret: it cannot sign anything by itself |
| Validity | `Expires` is 2024-03-25 12:29:04 UTC. A signature-version-2 URL is refused by S3 after that time, so the URL grants no access since then. Whether the object still exists, and whether the key id is still active, is unknown and was not tested |
| Origin | the URL is part of the public article text on Wikipedia (it was added by a Wikipedia editor); the same bytes are served to anyone who opens that revision |
| One URL | every match in the five files is the same key id, the same expiry and the same signature |

Classification: **key id plus an expired request signature; no secret; not access-bearing at capture time.** It is
not a credential leak by CITERIFT. It is still a string that the accepted Stage 00 policy forbids in tracked files
(`tests/stage00/test_repository.py::test_no_secrets_in_repository_files`), and automated scanners may report it.

## 2. Where the string is

A scan of every blob in the local object database (4,467 blobs; script below) finds the pattern in exactly three
blobs. They are reachable only from the pull-request branch `claude/beautiful-planck-fm0pya`:

| Commit | What it did |
|---|---|
| `4766a1f` | added the bundle (three files hold the pattern) |
| `763c1c4` | added the evaluator packet (two more files) |
| `153efae`, `0ff6446` | later commits whose trees still hold the five files |
| `eba17d7` | removed the five files from the index (they stay on disk, untracked) |

None of these commits is in `main` (`git merge-base --is-ancestor 4766a1f origin/main` is false). At the pull
request's head no tracked file contains the pattern, the words `AWSAccessKeyId` or `X-Amz-Signature`, or the URL's
expiry value (`git grep` at HEAD), and the Stage 00 secret test passes.

The nested `.gitignore` that keeps the five untracked files out of `git status` does not remove anything from
history and is not relied on here as proof of anything (integration audit F-4).

The D-035 evidence export in the owner's project files holds the five files under `withheld/` on purpose (they are
needed to replay the campaign); none of its other 4,358 files, including the 12 evaluator and adjudicator
transcripts, contains the pattern. That export is private to the project; it is not a public redistribution.

## 3. What a merge would do

Pull requests here are merged with merge commits (CLAUDE.md; the registry cites commit SHAs that a squash or rebase
would drop). A merge commit makes every commit of the branch, including `4766a1f` to `0ff6446`, part of `main`'s
history. The public repository would then carry the expired URL and the third party's key id in `main`'s history
permanently, unless history is rewritten (which needs the owner's explicit authorization and breaks every recorded
SHA).

Therefore pull request #5 must not be described as free of this material. It is not a credential exposure (section
1), but merging it publishes a string that the project's own secret policy rejects.

## 4. A clean merge path

A branch without those commits in its history avoids the propagation. The final tree of pull request #5 contains
none of the five files, so a commit with exactly that tree, whose only parent is `main`, has no flagged blob in its
history. Such a branch keeps provenance by tree identity: `git rev-parse <commit>^{tree}` gives the same tree id for
the delivery commit and for the verified pull-request commit, which proves byte-identical content.

Two constraints decide how such a branch must be built:

* the registry's revision references must be ancestors of the merged head (`citerift-gov check`,
  `REVISION_NOT_IN_HISTORY`), so the delivery branch needs its own registry record that cites its own commits, with
  the verified pull-request revision named as the source of an identical tree;
* the scientific record (protocol commits, the frozen candidate, the campaign commits) cites pull-request SHAs. Those
  commits stay on the pull-request branch and in the checksummed export; a delivery branch would cite them as
  external provenance, not as ancestors.

The executor prepares such a branch only after the final verification, so that its tree is the verified tree (see
the final handoff for its state). Choosing between merging pull request #5 and merging the delivery branch is the
owner's decision; the executor merges neither.

## 5. Owner-side actions that this session cannot perform

* Choose the merge path (pull request #5 with the history above, or the clean delivery branch).
* Optionally, tell the third party (the operator of the S3 bucket, apparently the site that issued the download link)
  that a long-term key id appears in public presigned links on Wikipedia; only its owner can rotate the key. The URL
  is already public on Wikipedia, so this is a courtesy, not a containment step for CITERIFT.
* If the owner wants the branch history itself cleaned, that requires rewriting and force-pushing the public
  pull-request branch, which is not authorized; the delivery branch makes it unnecessary.

## 6. Reproduction (no network)

```
# blobs with the pattern in the object database
python3 - <<'PY'
import subprocess, re
pat = re.compile(rb"AKIA[0-9A-Z]{16}")
lines = subprocess.run(["git", "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)"],
                       capture_output=True, text=True).stdout.split("\n")
blobs = [l.split()[0] for l in lines if l.endswith(" blob")]
p = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
hits = 0
for b in blobs:
    p.stdin.write((b + "\n").encode()); p.stdin.flush()
    size = int(p.stdout.readline().split()[2]); data = p.stdout.read(size); p.stdout.read(1)
    hits += bool(pat.search(data))
print(len(blobs), "blobs,", hits, "with the pattern")
PY
git log --all --format=%h --find-object=<blob id>    # for each blob found
git grep -c -I -E "AKIA[0-9A-Z]{16}|AWSAccessKeyId|X-Amz-Signature" HEAD -- .   # empty at the head
```
