import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art('en-1361411235'); t=A.t
cps=[A.find('{{efn|')]+A.finds('{{sfn|')+[A.find('<ref>')]
cps.sort(); assert len(cps)==len(A.sups),(len(cps),len(A.sups))
first={}; uses=[]; defs=[]
for i,cp in enumerate(cps):
    sp=A.sups[i]; key=(sp['name'],sp['group'])
    if t.startswith('{{efn',cp):
        defs.append(dict(cp=cp,kind='generated_note',name=None,group='lower-alpha',unstructured=False,sup=i,notes='efn on enwiki defaults to group lower-alpha (render data-mw group=lower-alpha). Plain-text explanatory note, no citation template.'))
        uses.append(dict(cp=cp,bind=cp,sup=i)); continue
    if t.startswith('<ref>',cp):
        defs.append(dict(cp=cp,kind='note',name=None,group='',unstructured=False,sup=i,templates=[],
          notes='Body is {{harvnb|Németh|2018|p=3}} plus prose. harvnb generates an inline link, not a footnote, so it is not labelled as a use or short-footnote definition; no Cite template; explanatory note.'))
        uses.append(dict(cp=cp,bind=cp,sup=i)); continue
    if key not in first:
        first[key]=cp
        defs.append(dict(cp=cp,kind='generated_note',name=None,group='',unstructured=False,sup=i))
    uses.append(dict(cp=cp,bind=first[key],sup=i))
bib=[]
for m in re.finditer(r'^\*\{\{cite ',t,re.M):
    cp=m.start(); c=cp+1
    bib.append(dict(cp=cp,kind='bibliography_entry',unstructured=False,templates=[c],render_note_id=None,marker='none',marker_text=None,notes=''))
defs+=bib
ids=[]
for d in ['10.1002/9781444338386.wbeah08041','10.1017/9781139626880']:
    ids.append(dict(cp=A.find(d),q=d,scheme='doi',role='primary_citation_field',key=d.lower()))
A.build(defs,uses,ids,
 ['Editions section list items (lines starting *''Excerpta historica... and ** Volumen ...) hold archive.org URLs and {{ill}} templates but no citation template or DOI/PMID, so not labelled as bibliography entries.',
  '{{CEEOL|608919}} after the Manafis cite journal is an external-link template, not a DOI/PMID; not labelled.'],
 'Python 3 stdlib + lxml helper snippets (text search, HTML sup/li listing, location verification); decisions made by reading the text.',
 '2026-11-03T01:56:12Z','Whether harvnb inside a ref (cp 3397) counts as unstructured; chose false.')
