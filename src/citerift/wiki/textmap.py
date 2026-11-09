"""Code point to UTF-8 byte offsets for one source text (SPECIFICATION.md 12.1).

Parsers work in Unicode code points; anchors are UTF-8 byte intervals [start, end) of the retained source
bytes. The conversion is explicit: byte(i) = i + (extra UTF-8 bytes of the non-ASCII code points before i).
"""

from __future__ import annotations

import re
from bisect import bisect_left

_NON_ASCII = re.compile(r"[^\x00-\x7f]")


class ByteMap:
    def __init__(self, text: str) -> None:
        self.text = text
        self._pos: list[int] = []
        self._cum: list[int] = []
        extra = 0
        for m in _NON_ASCII.finditer(text):
            cp = ord(m.group(0))
            extra += 1 if cp < 0x800 else 2 if cp < 0x10000 else 3
            self._pos.append(m.start())
            self._cum.append(extra)
        self.total_bytes = len(text) + extra

    def byte(self, index: int) -> int:
        """UTF-8 byte offset of code point index ``index`` (0 <= index <= len(text))."""
        if not 0 <= index <= len(self.text):
            raise IndexError(index)
        k = bisect_left(self._pos, index)
        return index + (self._cum[k - 1] if k else 0)

    def interval(self, start: int, end: int) -> tuple[int, int]:
        return self.byte(start), self.byte(end)
