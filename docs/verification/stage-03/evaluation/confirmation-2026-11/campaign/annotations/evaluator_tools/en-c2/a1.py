import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2/tools')
from lib import *
A=Art('en-1329904848'); t=A.t
refs=['SIMBAD','GaiaEDR3','Anderson_Francis_2012','MAST','Humason_Merrill_1921','Merrill_et_al_1925','Merrill_1949','Merrill_1952','Samus_et_al_2017','Jönsson_et_al_2020','Sandell_et_al_2018','Merrill_Burwell_1933','Doazan_1965','Kuan_Huhi_1975','Allen_1973','Hutsemekers_1985','Merrill_1931','Bopp_1993','Pogodin_1997','Jeřábková_et_al_2016','Kluska_et_al_2016','Koutoulaki_et_al_2018','Varga_et_al_2019']
pos={}
for n in refs:
    pos[n]=A.find(f'<ref name={n}>',6700)
tm={'SIMBAD':'cite simbad','GaiaEDR3':'Cite Gaia EDR3','Anderson_Francis_2012':'cite XHIP','MAST':'cite web'}
for n in refs:
    c=pos[n]; tc=t.index('{{',c)
    unstr=False
    A.adddef(c,'list_defined_note',n,'',[tc],unstr,f'cite_note-{n}-X','none',None,'')
# render ids fix
li={}
import re
from lxml import html
doc=html.parse(f'{BASE}/packets/en-1329904848/render.html').getroot()
for l in doc.iter('li'):
    i=l.get('id') or ''
    if i.startswith('cite_note-'): li[i]=1
for d in A.defs:
    n=d['name']; m=[i for i in li if i.startswith(f'cite_note-{n}-')]
    assert len(m)==1,(n,m); d['render_note_id']=m[0]
    d['marker_text']=None
# uses: body uses in window then list-defined self uses
supid={}
body_uses=[(5947,'Jeřábková_et_al_2016','cite_ref-Jeřábková_et_al_2016_23-1'),(6158,'Kluska_et_al_2016','cite_ref-Kluska_et_al_2016_22-1'),(6385,'Varga_et_al_2019','cite_ref-Varga_et_al_2019_4-1'),(6534,'Jeřábková_et_al_2016','cite_ref-Jeřábková_et_al_2016_23-2'),(6701,'Koutoulaki_et_al_2018','cite_ref-Koutoulaki_et_al_2018_7-4')]
for cp,n,r in body_uses:
    assert t[cp:cp+len(f'<ref name={n}/>')]==f'<ref name={n}/>'
    A.adduse(cp,pos[n],r,'self-closing reuse of the list-defined reference')
for n in refs:
    A.adduse(pos[n],pos[n],None,'list-defined <ref> inside <references>; Parsoid emits no marker for it (marker only at the self-closing calls)')
# identifiers
for m in re.finditer(r'\bdoi=(10\.\S+?)(?=\s|\||\}\})',t):
    cp=m.start(1)
    if A.inw(cp): 
        v=m.group(1); A.addid(cp,v,'doi','primary_citation_field',v.lower())
print(len(A.ids),[i['at']['quote'] for i in A.ids])
A.write('2026-11-03T01:56:00Z',files(A),'python3 stdlib (str.find, re) and lxml listing of sup/li ids; helper scripts in tools/','Nothing undecided. Rendered marker text is not available for list-defined footnotes beyond reading the li text; no retraction vocabulary seen in any rendered footnote.')
