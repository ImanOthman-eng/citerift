"""Title and author search normalization for candidate retrieval (SPECIFICATION.md 12.2).

This is separate from identifier normalization on purpose: it folds case and compatibility forms and drops
Arabic short-vowel marks and tatweel so that similar titles meet, which would be wrong for identifiers.
The original strings are never changed; only search tokens are derived.
"""

from __future__ import annotations

import unicodedata

MIN_TOKEN_LENGTH = 3
_ARABIC_MARKS = {chr(c) for c in range(0x064B, 0x0660)} | {"ـ", "ٰ"}


def search_normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if ch not in _ARABIC_MARKS)


def _words(text: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for ch in search_normalize(text):
        if ch.isalnum():
            current.append(ch)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def title_tokens(title: str) -> list[str]:
    """Sorted distinct tokens of length >= 3."""
    return sorted({w for w in _words(title) if len(w) >= MIN_TOKEN_LENGTH})


def author_surnames(authors: str) -> list[str]:
    """Last word of each ';'-separated name, search-normalized. A heuristic: not valid for every naming order."""
    out = set()
    for name in authors.split(";"):
        words = _words(name)
        if words:
            out.add(words[-1])
    return sorted(out)


def script_of(text: str) -> str:
    """Coarse script label for reporting strata: 'arabic', 'latin', 'other' or 'none'."""
    arabic = latin = other = 0
    for ch in text:
        if not ch.isalpha():
            continue
        if "؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" or "ﭐ" <= ch <= "﷿":
            arabic += 1
        elif ch.isascii() or unicodedata.name(ch, "").startswith("LATIN"):
            latin += 1
        else:
            other += 1
    if not (arabic or latin or other):
        return "none"
    best = max((arabic, "arabic"), (latin, "latin"), (other, "other"))
    return best[1]
