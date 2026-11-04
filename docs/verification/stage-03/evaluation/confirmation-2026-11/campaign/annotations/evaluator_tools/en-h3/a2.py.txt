import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art('en-1361736284'); t=A.t; W0,W1=A.w
refs=A.finds('<ref')
assert len(refs)==len(A.sups),(len(refs),len(A.sups))
first={}; defs=[]; uses=[]
def tmpl(cp,tag='{{'):
    return t.index('{{',cp)
for i,cp in enumerate(refs):
    sp=A.sups[i]; nm=sp['name']
    selfclose = sp['body'] is None
    if not selfclose:
        # definition
        if nm: first[nm]=cp
        inwin=W0<=cp<W1
        # include if in window or if a window use binds to it (decide later)
        defs.append(dict(cp=cp,kind='note',name=nm,group='',unstructured=False,sup=i,templates=[tmpl(cp)],_nm=nm))
        uses.append(dict(cp=cp,bind=cp,sup=i,_nm=nm))
    else:
        uses.append(dict(cp=cp,bind=first[nm],sup=i,_nm=nm))
uses=[u for u in uses if W0<=u['cp']<W1]
need={u['bind'] for u in uses}
defs=[d for d in defs if W0<=d['cp']<W1 or d['cp'] in need]
ids=[]
def idt(q,scheme,role,key,occ=0,start=W0,notes=''):
    cp=A.find(q,occ,start); ids.append(dict(cp=cp,q=q,scheme=scheme,role=role,key=key,notes=notes))
idt('10.1671/0272-4634(2007)27[145:CACFWM]2.0.CO;2','doi','primary_citation_field','10.1671/0272-4634(2007)27[145:cacfwm]2.0.co;2')
u='https://www.tandfonline.com/doi/abs/10.1080/14772019.2021.1910868'
idt(u,'doi','identifier_link','10.1080/14772019.2021.1910868',notes='publisher URL with /doi/abs/ path in url= field; DOI ends at the URL end')
idt('10.1080/14772019.2021.1910868','doi','primary_citation_field','10.1080/14772019.2021.1910868',start=A.find(u)+len(u))
idt('10.7717/peerj.13457','doi','primary_citation_field','10.7717/peerj.13457')
idt('35726261','pmid','primary_citation_field','35726261')
for d in defs:
    if d['name']: d['notes']='Named reference; later uses by name bind here.'
A.build(defs,uses,ids,
 ['Senut ref (starts cp 13936) lies in window; its doi (10.1016/j.crte.2009.03.008, cp ~14327) starts after cp_end so is not listed as an identifier.',
  'Named refs defined before the window (:22, :02, :12, :0, :1, :2) are listed with in_window=false because uses in the window bind to them; their citation templates and identifiers before the window are not otherwise labelled.',
  'Parsoid li for cite_note-:22-1 contains inline CSS text; marker_text has the CSS stripped.'],
 'Python 3 stdlib + lxml helper snippets (text search, HTML sup/li listing, location verification); decisions made by reading the text.',
 '2026-11-03T01:56:12Z','')
