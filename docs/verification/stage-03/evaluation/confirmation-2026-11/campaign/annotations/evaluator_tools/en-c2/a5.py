import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2/tools')
from lib import *
from lxml import html
A=Art('en-1382450117'); t=A.t
doc=html.parse(f'{BASE}/packets/{A.d}/render.html').getroot()
lis=[l.get('id') for l in doc.iter('li') if (l.get('id') or '').startswith('cite_note-')]
names=[m.group(1) for m in re.finditer(r'<ref name="([^"]+)">',t[15400:])]
assert len(names)==20,names
pos={n:15400+re.search(r'<ref name="'+n+r'">',t[15400:]).start() for n in names}
for n in names:
    c=pos[n]; nid=[i for i in lis if re.fullmatch(r'cite_note-'+n+r'-\d+',i)]; assert len(nid)==1,(n,nid)
    mk='none';mt=None;nt=''
    if n=='Sergeyev2017':
        mk='warning'; mt='(This paper currently has an expression of concern, see doi:10.4171/EMSS/4-2-3. If this is an intentional citation to a such a paper, please replace {{expression of concern|...}} with {{expression of concern|...|intentional=yes}}.)'
        nt='{{Expression of Concern|doi=10.4171/EMSS/4-2-3}} follows the cite journal template inside the ref; rendered text states the cited paper has an expression of concern. Template list contains the cite journal only (the Expression of Concern template is a notice, not a citation template).'
    A.adddef(c,'list_defined_note',n,'',[t.index('{{',c)],False,nid[0],mk,mt,nt)
uses=[(14500,'Gutman2008','cite_ref-Gutman2008_10-2'),(14750,'Gutman2017','cite_ref-Gutman2017_24-0'),(14910,'Sergeyev2019','cite_ref-Sergeyev2019_14-1'),(15123,'Ernest2023','cite_ref-Ernest2023_11-4')]
found=[m.start() for m in re.finditer(r'<ref [^>]*/>',t) if A.inw(m.start())]
assert found==[u[0] for u in uses]
for cp,n,r in uses:
    assert t.startswith(f'<ref name="{n}" />',cp); A.adduse(cp,pos[n],r)
for n in names: A.adduse(pos[n],pos[n],None,'list-defined <ref> inside {{Reflist|refs=}}; no marker of its own')
cnt=0
for m in re.finditer(r'10\.\d{4,9}/[^\s|}<]+',t):
    cp=m.start()
    if not A.inw(cp): continue
    v=m.group()
    role='primary_citation_field'; nt=''
    if cp==t.index('{{Expression of Concern')+len('{{Expression of Concern|doi='):
        role='marker_target'; nt='doi= of {{Expression of Concern}}: the notice, same identifier as the cited paper.'
    A.addid(cp,v,'doi',role,v.lower(),nt); cnt+=1
print(cnt,[ (i['at']['quote'],i['role']) for i in A.ids if i['role']!='primary_citation_field'])
print([m.start() for m in re.finditer(r'pmid|doi:|doi\.org',t,re.I) if A.inw(m.start())])
A.write('2026-11-03T01:56:00Z',files(A),'python3 stdlib (str.find, re) and lxml listing of sup/li ids; helper scripts in tools/','Nothing undecided.',
 ['Montagna et al. appears twice as separate references (unnamed-name :0 in the body, before the window, and list-defined Montagna2015); different names, so two references.','Bibliography-like list items: only the See also list (wikilinks) falls in the window; none has a citation template or DOI/PMID.'])
