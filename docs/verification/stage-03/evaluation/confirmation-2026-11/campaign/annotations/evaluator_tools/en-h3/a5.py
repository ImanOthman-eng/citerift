import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art('en-1380967804'); t=A.t; W0,W1=A.w
R=ref_tags(t); assert len(R)==len(A.sups)==12
defs=[];uses=[]
for i,r in enumerate(R):
    cp=r['cp']
    if not (W0<=cp<W1): continue
    b=body_of(t,cp)
    tm=[t.index('{{',cp)] if b.startswith('{{cite') else []
    defs.append(dict(cp=cp,kind='note',name=None,group='',unstructured=not tm,sup=i,templates=tm,
       notes='Unnamed reference; identical text to another unnamed ref elsewhere would still be a separate reference.' if i==10 else ''))
    uses.append(dict(cp=cp,bind=cp,sup=i))
ids=[]
def url(prefix,role,key,notes):
    cp=A.find(prefix,0,W0); m=re.match(r'https?://[^\s;<>|\]]+',t[cp:]); q=m.group(0)
    ids.append(dict(cp=cp,q=q,scheme='doi',role=role,key=key,notes=notes))
url('https://www.emerald.com/insight/content/doi/10.1108','identifier_link','10.1108/qrj-d-18-00004','Publisher URL with /doi/ path segment inside a plain-text ref. The URL ends at ";". The DOI is read as 10.1108/QRJ-D-18-00004; the trailing /full/html is Emerald view-path, not part of the DOI (DOI could in principle contain slashes, so this is a best reading).')
url('https://doi.org/10.1080/01596306.2022.2030594','identifier_link','10.1080/01596306.2022.2030594','doi.org URL inside plain-text ref, followed by </ref>.')
url('https://doi.org/10.1177/2047173415577884','identifier_link','10.1177/2047173415577884','doi.org URL inside plain-text ref, followed by </ref>.')
A.build(defs,uses,ids,
 ['Window starts at cp 1766, inside the first references of the lead; refs starting before it (cp 690, 1081, 1449, 1651) are not listed.',
  'The Publications list (lines starting *) and the External links item hold no citation template, DOI or PMID, so no bibliography entries are labelled.',
  'Refs at cp 5755 and cp 690 are textually identical but unnamed, so each is its own reference and definition; the render shows them as separate list items.'],
 'Python 3 stdlib + lxml helper snippets (text search, HTML sup/li listing, location verification); decisions made by reading the text.','2026-11-03T01:56:12Z','')
