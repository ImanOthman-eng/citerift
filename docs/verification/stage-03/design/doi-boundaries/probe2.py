# Boundary probe 2: full extraction of short reference texts. SYNTHETIC.
# Run from the repo root: uv run python <this file> (output: probe2.out.txt).
import sys
import tempfile

sys.path.insert(0, "tests/stage03")
from pathlib import Path

from wiki_support import bundle, codes, extract

cases = [
    "A<ref>{{cite journal|title=T|url=https://onlinelibrary.wiley.com/doi/10.1002/abc&amp;123}}</ref>",
    "A<ref>{{cite journal|title=T|url=https://doi.org/10.1002/abc&amp;123}}</ref>",
    "A<ref>See https://onlinelibrary.wiley.com/doi/10.1002/abc.123.</ref>",
    "A<ref>See https://doi.org/10.1002/abc.123.</ref>",
    "A<ref>(see https://doi.org/10.1002/abc.123)</ref>",
    "A<ref>(see https://doi.org/10.1002/abc(1)23)</ref>",
    "A<ref>[https://onlinelibrary.wiley.com/doi/10.1002%2Fabc.123 Paper]</ref>",
    "A<ref>[https://onlinelibrary.wiley.com/doi/abs/10.1002%2Fabc.123 Paper]</ref>",
    "A<ref>[https://web.archive.org/web/2020/https://doi.org/10.1002/abc.123 Paper]</ref>",
    "A<ref>{{cite journal|title=T|doi=10.1002/abc.123|url=https://onlinelibrary.wiley.com/doi/10.1002/abc.123/abstract|pmid=123}}</ref>",
    "A<ref>{{cite journal|title=T|doi=10.1002/abc.123.}}</ref>",
    "A<ref>doi:10.1002/abc.123.</ref>",
    "A<ref>[https://doi.org/10.1002/abc.123?utm=1 x]</ref>",
    "A<ref>[https://www.tandfonline.com/doi/abs/10.1080/1234/full x]</ref>",
]
for i, t in enumerate(cases):
    doc = extract(bundle(Path(tempfile.mkdtemp()), t, name=f"c{i}"))
    print(t)
    for x in doc["identifiers"]:
        print(
            "   ",
            x["scheme"],
            x["origin"],
            x["role"],
            x["normalization"]["normalized"],
            x["decoding"]["structural_steps"],
            x.get("excluded"),
        )
    print("   codes", sorted(c for c in codes(doc) if c != "RECONCILIATION_UNAVAILABLE"))
