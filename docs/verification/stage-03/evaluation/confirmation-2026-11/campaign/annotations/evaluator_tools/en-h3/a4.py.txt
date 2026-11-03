import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art('en-1377237744'); t=A.t; W0,W1=A.w
R=ref_tags(t)
efns=A.finds('{{efn|'); assert len(efns)==3
efn_sups=[i for i,s in enumerate(A.sups) if s['group']=='lower-alpha' and not s['name']]
assert len(efn_sups)==3
cnt={}; first={}; items=[]
for r in R:
    n=r['name']; k=cnt.get(n,0); cnt[n]=k+1
    sidx=sup_for(A,n,'',k); assert sidx is not None,(n,k)
    if not r['selfclose'] and n not in first: first[n]=r['cp']
    items.append(dict(cp=r['cp'],name=n,sup=sidx,body=not r['selfclose']))
for e,si in zip(efns,efn_sups): items.append(dict(cp=e,name=None,sup=si,body=True,efn=True))
items.sort(key=lambda x:x['cp'])
defs=[];uses=[]
for it in items:
    cp=it['cp']
    if it.get('efn'):
        defs.append(dict(cp=cp,kind='generated_note',name=None,group='lower-alpha',unstructured=False,sup=it['sup'],notes='efn on enwiki defaults to group lower-alpha (render data-mw group=lower-alpha). Explanatory note; may contain nested refs, which are labelled separately.'))
        uses.append(dict(cp=cp,bind=cp,sup=it['sup'])); continue
    if it['body'] and first[it['name']]==cp:
        defs.append(dict(cp=cp,kind='note',name=it['name'],group='',unstructured=True,sup=it['sup'],templates=[],notes='Plain-text citation, no citation template.'))
        uses.append(dict(cp=cp,bind=cp,sup=it['sup']))
    else:
        uses.append(dict(cp=cp,bind=first[it['name']],sup=it['sup'],notes='Named reuse; definition appears later in source' if first[it['name']]>cp else ''))
uses=[u for u in uses if W0<=u['cp']<W1]
need={u['bind'] for u in uses}
defs=[d for d in defs if W0<=d['cp']<W1 or d['cp'] in need]
for m in re.finditer(r'^\* \{\{cite ',t,re.M):
    if W0<=m.start()<W1:
        defs.append(dict(cp=m.start(),kind='bibliography_entry',unstructured=False,templates=[t.index('{{',m.start())],render_note_id=None,marker='none'))
A.build(defs,uses,[],
 ['No DOI or PMID occurs in the window (checked by text search; the HTML comment at ~7563 holds none).',
  'Bibliography entries beginning at cp 13453 and later start after cp_end and are not listed.',
  'Parsoid lists the sups of refs nested inside the three efn notes after the main-text sups; render_ref_id was assigned by name and source occurrence index (id suffix) rather than list position.',
  'Red links in the rendered footnotes (John de Cumin etc.) point to missing articles, not templates; marker none.'],
 'Python 3 stdlib + lxml helper snippets (text search, HTML sup/li listing, location verification); decisions made by reading the text.','2026-11-03T01:56:12Z','')
