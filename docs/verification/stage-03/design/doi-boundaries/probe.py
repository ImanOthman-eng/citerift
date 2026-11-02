# Boundary probe 1: identifiers.decode on URL forms. Run: uv run python probe.py (output: probe.out.txt). SYNTHETIC.
import sys
from citerift.wiki.identifiers import decode
cases = [
 "https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1365-2486.2009.02000.x",
 "https://onlinelibrary.wiley.com/doi/full/10.1111/j.1365-2486.2009.02000.x",
 "https://onlinelibrary.wiley.com/doi/epdf/10.1002/abc.123",
 "https://www.tandfonline.com/doi/full/10.1080/00001.2020.1/abstract",
 "https://onlinelibrary.wiley.com/DOI/10.1002/ABC.123",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123?journalCode=x",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123#sec1",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123/abstract?x=1",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123/abstract#a",
 "https://onlinelibrary.wiley.com/doi/10.1002%2Fabc.123",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc&amp;123",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123.",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123)",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc/10.1003/def",
 "https://web.archive.org/web/2020/https://onlinelibrary.wiley.com/doi/10.1002/abc.123",
 "https://www.science.org/doi/10.1126/science.abc1234",
 "https://www.science.org/doi/full/10.1126/science.abc1234",
 "https://journals.sagepub.com/doi/pdf/10.1177/0956797611417632",
 "https://pubs.acs.org/doi/pdf/10.1021/ja00001a001",
 "https://www.pnas.org/doi/10.1073/pnas.1000000107",
 "https://doi.org/10.1002/abc.123/abstract",
 "https://doi.org/10.1002/abc.123.",
 "https://dx.doi.org/10.1002/ABC%2F123",
 "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0000001",
 "https://link.springer.com/article/10.1007/s00000-000-0000-0",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123/full/",
 "https://onlinelibrary.wiley.com/doi/10.1002/abc.123/citedby",
 "https://onlinelibrary.wiley.com/doi/book/10.1002/9780470000000",
 "https://onlinelibrary.wiley.com/doi/10.1002/9780470000000.ch1/summary",
 "https://pubmed.ncbi.nlm.nih.gov/12345678/",
 "https://www.ncbi.nlm.nih.gov/pubmed/0012345678",
 "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456/",
]
for u in cases:
    sch = "pmid" if "pubmed" in u else "doi"
    g = decode(sch, "url", u, ())
    print(u, "\n   ->", None if g is None else (g.normalizer_input, g.normalized.normalized if g.normalized else None, list(g.steps)))
