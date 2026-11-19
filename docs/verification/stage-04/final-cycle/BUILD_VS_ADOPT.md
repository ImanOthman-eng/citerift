# Final corrective cycle: Build-vs-Adopt review of the bibliographic-object consistency layer

Owner decision D-083, item 1; permanent Open-Source Leverage rule of 2026-11-10 (16 fields per candidate).
Subject: what the bib-1 layer needs (parse a citation template's arguments; fold and tokenize text in Latin and Arabic
script; compare authors and titles with threshold-free relations) and whether an existing project should do any of it.

## 1. Baseline

- Template parsing: mwparserfromhell 0.7.2, **already pinned** (Stage 03 scanner `citerift.wiki.source`; MIT, no
  runtime dependency). bib-1 calls `mwparserfromhell.parse`, `Template.params` and `Wikicode.strip_code` only.
- Folding and tokenizing: Python standard library (`unicodedata.normalize("NFKD")`, `unicodedata.category`,
  `str.casefold`, `re` with `[^\W_]+`, `unicodedata.name` for the script).
- Relations: equality, contiguous containment, shared word, no shared word (specification section 4). No similarity
  score; owner item 1 forbids fuzzy thresholds without an independent specification and adversarial evidence, so a
  candidate whose value is a score is out of scope by design.

## 2. Method

Facts were read on 2026-11-19 from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`: latest version, upload date
of its files, license expression or classifiers, `requires_python`, declared dependencies). Repositories outside this
session's GitHub scope could not be read, so open issues and security advisories were not read; "maintenance" is the
release history only, and "security" is a statement about the attack surface, not an advisory search. Nothing was
installed. Where a fact was not verified it says so.

## 3. Candidates (16 fields)

Fields: 1 repository/package; 2 capability; 3 latest release; 4 license; 5 transitive licenses (declared runtime
dependencies only); 6 maintenance; 7 security surface; 8 Python 3.12/3.13 compatibility; 9 cost; 10 reproducibility;
11 network needs; 12 complexity saved; 13 complexity added; 14 testability; 15 versus the internal baseline;
16 decision.

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mwparserfromhell | MediaWiki parser: templates, params, `strip_code` | 0.7.2, 2025-07-01 | MIT | none | released 2025; already pinned and audited for Stage 03 | parses untrusted wikitext; already in the trust boundary of Stage 03 | `>=3.9`; run in CI on 3.12 and 3.13 | free | pinned in `uv.lock` | none | argument semantics (later duplicate wins, `showkey`, markup removal) | none (already a dependency) | already exercised by the Stage 03 suite and the bib-1 corpus | it is the baseline | **ADOPT (existing pin, no change)** |
| wikitextparser | MediaWiki parser | 3.0.0, 2026-10-08 | GPL-3.0 | regex (Apache-2.0), wcwidth (MIT) | active | parses untrusted text | `>=3.9`; not run | free | could be pinned | none | none beyond mwparserfromhell | a second parser with different semantics | not evaluated | duplicates the pinned parser | **REJECT** (copyleft; duplicate) |
| rapidfuzz | string similarity scores (Levenshtein, token ratios) | 3.14.6, 2026-08-30 | MIT | none (numpy optional) | active | native extension | `>=3.11`; not run | free | could be pinned | none | none: bib-1 has no score | a threshold to fit (forbidden by item 1) | scores need calibration data | contradicts the threshold-free specification | **REJECT** |
| jellyfish | phonetic codes and edit distances | 1.3.0, 2026-10-16 | MIT | none | active | native extension (Rust) | `>=3.11`; not run | free | could be pinned | none | none | a threshold or a phonetic heuristic | as above | as above | **REJECT** |
| nameparser | split personal names into parts | 3.1.0, 2026-11-17 | LGPL-2.1-or-later | none | active | pure Python | `>=3.11`; not run | free | could be pinned | none | name-part detection, not needed (bib-1 compares any name word) | language-specific rules (Latin names) | not evaluated | bib-1 needs no name parts | **REJECT** (copyleft needs an owner decision; not needed) |
| probablepeople | CRF model to label name parts | 0.5.6, 2024-10-29 | MIT | python-crfsuite (MIT), probableparsing, doublemetaphone (not verified) | release 2024 | native CRF library | `>=3.9`; not run | free | a trained model inside the package | none | as nameparser | a statistical model whose output is not explainable rule by rule | model behaviour not specifiable | not needed | **REJECT** |
| Unidecode | ASCII transliteration | 1.4.0, 2025-04-24 | GPL-2.0-or-later | none | released 2025 | pure Python | `>=3.7`; not run | free | could be pinned | none | Latin transliteration of Arabic names | lossy, language-blind transliteration would create false agreements | deterministic | a false AGREE is the dangerous direction (a positive) | **REJECT** (copyleft; unsafe direction) |
| PyICU | ICU collation, transliteration, normalization | 2.17, 2026-10-23 | MIT (ICU: Unicode license) | ICU C++ library (system) | active | native ICU | not verified | free | depends on the system ICU version | none | locale-aware folding | a system library whose version changes results | results vary with ICU version | stdlib NFKD + casefold is enough for the relations used | **REJECT** (reproducibility) |
| refextract | extract references from PDFs/text | 1.1.7, 2026-10-01 | GPL-2.0-or-later | inspire-utils, pypdf, python-magic, requests, unidecode (GPL) | active | parses documents; network client | `<3.15,>=3.11`; not run | free | not evaluated | uses requests | free-text reference parsing (not in scope: bib-1 reads templates) | many dependencies | not evaluated | out of scope | **REJECT** |
| grobid-client-python (GROBID) | client for the GROBID reference-parsing service | 0.2.2, 2026-11-06 | not stated on PyPI (not verified) | requests, dateparser, beautifulsoup4, lxml | active | needs a GROBID server (Java) | not verified | a service to run | depends on a server and its model version | a server over HTTP | free-text parsing | a Java service and a network hop | not deterministic across model versions | out of scope; network | **REJECT** |
| habanero | Crossref API client | 2.9.2, 2026-06-17 | MIT | httpx2, packaging, tqdm, urllib3 | active | network client | `>=3.10`; not run | free (rate-limited API) | depends on live API | Crossref API | record metadata from Crossref | a live network source at decision time | not reproducible offline | the record side already comes from Stage 02 (accepted interface) | **REJECT** (network; not needed) |
| pybtex / citeproc-py | BibTeX parsing / CSL formatting | 0.26.1, 2026-04-03 / 0.12.3, 2026-11-12 | MIT / BSD-2-Clause-Views | latexcodec, pyyaml / lxml | active | parsers of their own formats | not run | free | could be pinned | none | none (other formats; formatting, not comparison) | unrelated data models | not evaluated | out of scope | **REJECT** |
| Wikipedia CS1 configuration (`Module:Citation/CS1/Configuration`, en rev 1384336575, ar rev 76424085) | the wikis' own parameter-alias tables | revisions of 2026-11-07 and 2026-09-03 | wiki content (CC BY-SA 4.0); used here as interface facts (parameter names) | none | maintained by the wiki communities | data only, read once, hashed | n/a | free | content SHA-256 and revision id recorded in `bib-profile-1.json` | read once (2026-11-19), never at run time | the alias lists (hand-made lists would miss aliases) | a profile file in the engine identity | the profile is checked equal to an independently extracted one | better than a hand-made list | **ADAPT** (parameter names extracted into a pinned, attributed profile) |

## 4. Decision

**No new dependency is adopted.** bib-1 uses the already pinned mwparserfromhell 0.7.2 and the standard library. The
alias profile is data taken from the wikis' own CS1 configuration modules at recorded revisions (source page, revision
id, timestamp and content SHA-256 are in the profile; the profile holds parameter names only). Every similarity
library is rejected because the specification is threshold-free by owner instruction; every network or service
candidate is rejected because the record side already comes from the accepted Stage 02 interface and decisions must
be reproducible offline; copyleft candidates are not needed, so no owner licence decision is required.

Note for the owner: the profile copies parameter names (interface identifiers) from CC BY-SA wiki modules, with
attribution by page and revision. We treat names of template parameters as functional facts; if the owner prefers,
the profile can carry an explicit CC BY-SA notice without any change to the alias data (the profile digest, part of the engine identity, would change).

## 5. Verification

- `uv.lock` is unchanged by this cycle (`git diff 6663314 -- uv.lock pyproject.toml` is empty at the freeze-3
  candidate; recorded in the freeze report).
- pip-audit and the dependency matrix are part of the freeze-3 check list.
