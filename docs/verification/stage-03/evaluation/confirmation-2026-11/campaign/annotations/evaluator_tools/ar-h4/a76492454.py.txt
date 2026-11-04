import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4/tools')
from lib import *
A=Art('ar-76492454'); T=A.t
specs=[('<ref name="pmid 17090528">','pmid 17090528','{{استشهاد بدورية محكمة |عدة مؤلفين=Burgis','cite_note-pmid_17090528-1','cite_ref-pmid_17090528_1-0','pmid = 17090528','17090528','doi = 10.1074/jbc.M608708200','10.1074/jbc.M608708200'),
('<ref name="entrez">','entrez','{{استشهاد ويب','cite_note-entrez-2','cite_ref-entrez_2-0',None,None,None,None),
('<ref name="pmid11278832">','pmid11278832','{{استشهاد بدورية محكمة |عدة مؤلفين=Lin S','cite_note-pmid11278832-3','cite_ref-pmid11278832_3-0','pmid = 11278832','11278832','doi = 10.1074/jbc.M011084200','10.1074/jbc.M011084200'),
('<ref name="pmid 22531138">','pmid 22531138','{{استشهاد بدورية محكمة |عدة مؤلفين=Davies','cite_note-pmid_22531138-4','cite_ref-pmid_22531138_4-0','pmid = 22531138','22531138','doi = 10.5483/BMBRep.2012.45.4.259','10.5483/bmbrep.2012.45.4.259')]
for a,name,tp,rid,sid,pm,pk,dd,dk in specs:
    d=A.defn(A.at(a),'note',name=name,templates=[A.at(tp)],rid=rid)
    A.use(d,d,sid)
    if name.startswith('pmid'):
        dg=re.search(r'\d+',name).group()
        A.ident(A.at(a,off=len('<ref name="pmid')+(1 if ' ' in name else 0),ln=len(dg)),'pmid','not_a_target',dg,'digits inside the value of ref name=')
    if pm:
        A.ident(A.at(pm,off=len('pmid = '),ln=len(pk)),'pmid','primary_citation_field',pk)
        A.ident(A.at(dd,off=len('doi = '),ln=len(dd)-6),'doi','primary_citation_field',dk)
for pos,l in lines(T,A.w):
    if l.startswith('* {{استشهاد') and A.inw(pos):
        A.defn(A.at_cp(pos),'bibliography_entry',templates=[A.at_cp(pos+2)],notes='List item in the قراءة متعمقة section (between {{بداية المراجع}} and the end); no render li.')
        pm=re.findall(r'pmid=\s*(\d+)',l); dm=re.findall(r'doi=\s*(\S+)',l)
        assert len(pm)==1 and len(dm)<=1,(l[:60],pm,dm)
        m=re.search(r'pmid=\s*(\d+)',l)
        if A.inw(pos+m.start(1)): A.ident(A.at_cp(pos+m.start(1),len(m.group(1))),'pmid','primary_citation_field',m.group(1))
        m=re.search(r'doi=\s*(\S+)',l)
        if m and A.inw(pos+m.start(1)): A.ident(A.at_cp(pos+m.start(1),len(m.group(1))),'doi','primary_citation_field',m.group(1).lower())
A.write(0,'python3 stdlib listing, lxml sup/li listing, own quote-checking builder tools/lib.py','Window ends at 8022; the next bibliography entry starts at 8040 and is out of scope. Reading of Further reading list items as bibliography entries per 3.4.','2026-11-03T01:56:13Z')
