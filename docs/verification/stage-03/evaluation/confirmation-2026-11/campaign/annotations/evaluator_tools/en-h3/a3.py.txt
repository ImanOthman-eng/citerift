import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art('en-1371041332'); t=A.t
refs=A.finds('<ref'); assert len(refs)==len(A.sups)
first={}; defs=[]; uses=[]
for i,cp in enumerate(refs):
    sp=A.sups[i]; nm=sp['name']
    if sp['body']:
        first[nm]=cp
        defs.append(dict(cp=cp,kind='note',name=nm,group='',unstructured=False,sup=i,templates=[t.index('{{',cp)],notes='Named reference.'+(' Located inside the |authority= parameter of {{Speciesbox}}.' if nm=='LPSN' else '')))
        uses.append(dict(cp=cp,bind=cp,sup=i))
    else:
        uses.append(dict(cp=cp,bind=first[nm],sup=i))
ids=[]
for q,s in [('10.1099/00207713-52-6-2183','doi'),('12508887','pmid'),('10.1016/j.syapm.2021.126289','doi'),('34920232','pmid'),('10.3390/microorganisms10071363','doi'),('35889082','pmid')]:
    ids.append(dict(cp=A.find(q),q=q,scheme=s,role='primary_citation_field',key=q.lower()))
A.build(defs,uses,ids,['pmc=9320692 is a PMC id, not in scope.','{{Taxonbar|from=Q62904786}} may emit rendered links but no source identifiers.'],
 'Python 3 stdlib + lxml helper snippets (text search, HTML sup/li listing, location verification); decisions made by reading the text.','2026-11-03T01:56:12Z','')
