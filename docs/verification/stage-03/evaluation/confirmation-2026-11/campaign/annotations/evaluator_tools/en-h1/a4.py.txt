import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h1/tools')
from lib import *
ST='2026-11-03T01:58:00Z'
TOOLS='Python 3 standard library (re/str.find, slicing) to list and verify locations; lxml (xpath) to list sup[typeof=mw:Extension/ref] ids/data-mw and li[id^=cite_note]; grep for retraction vocabulary in render.html. Labels decided by reading the text.'
a=Art('en-1378828001')
specs=[('<ref>{{cite web |url= http://atlas','{{cite web','cite_note-2','cite_ref-2',None,'Unnamed ref; cite web, url-status dead with archiveurl.'),
('<ref>{{citation |author= Dominik','{{citation','cite_note-3','cite_ref-3',None,'Unnamed ref; {{citation}} with doi, arxiv, s2cid.'),
('<ref name="ET">','{{Cite news','cite_note-ET-4','cite_ref-ET_4-0','ET','Named ref, used once in the whole article.'),
('<ref>{{Cite journal |last=Balland |first=Pierre-Alexandre |last2=Rigby','{{Cite journal','cite_note-5','cite_ref-5',None,'Unnamed ref; cite journal with doi and DOI-bearing publisher URL.'),
('<ref>{{Cite journal |last=Balland |first=Pierre-Alexandre |last2=Jara','{{Cite journal','cite_note-6','cite_ref-6',None,'Unnamed ref; cite journal with doi.'),
('<ref>{{Cite web |title=The Atlas of Economic Complexity by','{{Cite web','cite_note-7','cite_ref-7',None,'Unnamed ref inside a table caption (|+ line); renders as a normal footnote.')]
for i,(anc,tpl,nid,rid,name,note) in enumerate(specs,1):
    r=a.L(anc); t=a.L(tpl,frm=r['cp'])
    a.D(f'd{i}',r,name=name,templates=[t],nid=nid,notes=note)
    a.U(f'u{i}',r,r,rid)
a.I(a.L('10.1016/j.worlddev.2016.12.020'),'doi','primary_citation_field','10.1016/j.worlddev.2016.12.020','doi= field of {{citation}}.')
a.I(a.L('https://www.tandfonline.com/doi/full/10.1080/00130095.2016.1205947',ql=60),'doi','identifier_link','10.1080/00130095.2016.1205947','url= field; path is /doi/full/10.… (not exactly /doi/10.…), DOI read from the path segment after /doi/full/. Whole URL quoted.')
a.I(a.L('10.1080/00130095.2016.1205947',n=1),'doi','primary_citation_field','10.1080/00130095.2016.1205947','doi= field.')
a.I(a.L('10.1038/s41562-019-0803-3'),'doi','primary_citation_field','10.1038/s41562-019-0803-3','doi= field.')
a.unres.append('https://www.nature.com/articles/s41562-019-0803-3 (url= of the Nature Human Behaviour citation) contains the DOI suffix but no 10.1038 prefix, so it was not labelled as a DOI occurrence.')
a.unres.append('https://www.sciencedirect.com/science/article/abs/pii/S0305750X15309876 contains a PII, not a DOI; not labelled.')
a.unres.append('Ref at cp 1337 (before window, cite_ref-1) and ref at cp 15892 (after window, cite_ref-8) are outside the window and not listed; no use in the window binds to them.')
a.write(ST,TOOLS,'Nothing undecided; only judgement call is the /doi/full/ publisher URL, labelled identifier_link.')
