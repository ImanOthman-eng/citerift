# CITERIFT Identity Standard

Applies to every stage. Set by the owner on 2026-10-25 (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPGk43kowXCxBqhPw9S7z5df`; DECISIONS.md D-017).
Later stages apply this standard; they do not rebrand.

## Identity architecture

| Element | Value | Use |
|---|---|---|
| Project identity | CITERIFT | the product and repository name, always first |
| Primary public identity | EVE TELOS | the creator and research director, always prominent |
| Founder monogram | IM | a secondary personal signature, never alone and never in place of EVE TELOS |
| Professional signature | EVE TELOS · IM | founder attribution lines |
| Repository ownership | GitHub `ImanOthman-eng` | ownership records only (OWNERSHIP.md) |

Final identity standard, used verbatim:

> CITERIFT — Created and Directed by EVE TELOS · IM

The separator is a middle dot (U+00B7) with one space on each side. Where only
ASCII is possible (for example a package metadata field that rejects it), write
`EVE TELOS - IM`.

## Where it appears

| Surface | Form |
|---|---|
| README | the identity standard line under the title |
| OWNERSHIP.md | the identity standard line, the role table |
| Package metadata (`pyproject.toml` authors) | `EVE TELOS · IM` |
| Stage reports and handoffs | `Project owner: EVE TELOS` where a stage names its owner |
| Frontend (Stage 08) | the identity standard line in the footer or About view; IM may appear as a small monogram mark next to EVE TELOS |
| Research report and Devpost (Stage 09) | author: EVE TELOS; signature line: the identity standard |

## Rules

1. EVE TELOS is the prominent creator identity on every public surface. IM
   accompanies it and is never larger or more prominent.
2. The public materials do not state the founder's full legal name. The link
   between EVE TELOS and the legitimate owner is the repository owner account,
   recorded in OWNERSHIP.md.
3. The monogram is a signature, not a claim. It is never presented as proof of
   authorship, a copyright registration or a trademark: no ™ or ® marks.
4. The identity belongs to the project and its owner, not to any tool. AI tools
   used in development are disclosed as tools (OWNERSHIP.md, "AI-assisted
   engineering") and never presented as the creator, owner or brand.
5. Historical records stay as they are: commit authors, co-author trailers and
   accepted stage evidence are never rewritten to match this standard.

## Visual identity (Stage 08)

Defined when Stage 08 is authorized. Constraints set now: the CITERIFT wordmark
leads; the founder line uses the exact text above; an IM monogram, if drawn, is
small, typographic and placed next to EVE TELOS, never as the application logo.
