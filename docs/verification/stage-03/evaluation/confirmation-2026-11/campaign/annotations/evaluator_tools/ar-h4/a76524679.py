import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4/tools')
from lib import *
A=Art('ar-76524679'); T=A.t
TOOLS='python3 stdlib (str.find, re listing), lxml listing of sup/li; own builder script that checks quotes (tools/lib.py)'
d1=A.defn(A.at('<ref name="pmid11222756">'),'note',name='pmid11222756',templates=[A.at('{{استشهاد بدورية محكمة | عدة مؤلفين = Rivero')],rid='cite_note-pmid11222756-1')
A.use(d1,d1,'cite_ref-pmid11222756_1-0')
d2=A.defn(A.at('<ref name="entrez">'),'note',name='entrez',templates=[A.at('{{استشهاد بويب')],rid='cite_note-entrez-2')
A.use(d2,d2,'cite_ref-entrez_2-0')
# name value
A.ident(A.at('pmid11222756',off=4,ln=8),'pmid','not_a_target','11222756','digits inside the value of ref name="pmid11222756"')
A.ident(A.at('pmid = 11222756',off=7,ln=8),'pmid','primary_citation_field','11222756')
A.ident(A.at('doi =10.1093/nar/29.5.1068',off=5,ln=21),'doi','primary_citation_field','10.1093/nar/29.5.1068')
# bibliography entries
for pos,l in lines(T,A.w):
    if l.startswith('*{{استشهاد'):
        d=A.defn(A.at_cp(pos),'bibliography_entry',templates=[A.at_cp(pos+1)],notes='List item inside {{PBB Further reading|citations=...}} under قراءة متعمقة; no render li (template output).')
        m=re.search(r'pmid=\s*(\d+)',l); A.ident(A.at_cp(pos+m.start(1),len(m.group(1))),'pmid','primary_citation_field',m.group(1))
        m=re.search(r'doi=\s*(\S+)',l); k=m.group(1).lower(); A.ident(A.at_cp(pos+m.start(1),len(m.group(1))),'doi','primary_citation_field',k)
A.write(None,TOOLS,'Bibliography reading: PBB Further reading citations treated as bibliography entries per 3.4. Nothing else undecided.','2026-11-03T01:56:13Z')
