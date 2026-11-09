import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2/tools')
from lib import *
A=Art('en-1341454454'); t=A.t
# definitions: (cp, name, note_id)
D=[(3258,'ProtoLife','cite_note-ProtoLife-7'),(4302,'CEPR','cite_note-CEPR-10'),
 (7665,None,'cite_note-13'),(7949,None,'cite_note-14'),(8470,None,'cite_note-15'),(9149,None,'cite_note-16'),
 (9665,None,'cite_note-17'),(10328,None,'cite_note-18'),(11470,None,'cite_note-19'),(12008,None,'cite_note-20'),
 (12934,':0','cite_note-:0-21'),(13214,None,'cite_note-22'),(13496,None,'cite_note-23'),(14344,None,'cite_note-24')]
notes={9665:'Same work (Batt/Appelbaum, CEPR report) as the named CEPR reference and as the later footnote 20, but the body differs (quote= field), so it is a distinct reference content and counts as its own definition.',
 12008:'Same work as the definition at the earlier unnamed CEPR report ref, but the quote= field differs, so the content differs; own definition (rendered as separate footnote 20).',
 11470:'Similar title to footnote 15 (Yahoo) but different author, work and quote; distinct content.',
 4302:'Defined before the window; listed as binding target for named uses in the window.',
 3258:'Defined before the window; listed as binding target for named uses in the window.'}
defcp={}
for cp,n,nid in D:
    assert t.startswith('<ref',cp)
    tc=t.index('{{',cp)
    name=n; 
    mk='none';mt=None;nt=notes.get(cp,'')
    if cp==13496:
        mk='ambiguous'; mt='(Erratum: doi:10.1016/S0140-6736(11)61666-8, )'
        nt='Followed by {{Erratum|...|doi=10.1016/S0140-6736(11)61666-8}}: a correction notice (erratum) attached to the cited Lancet article; erratum vocabulary is ambiguous per guide, not a retraction.'
    A.adddef(cp,'note',name,'',[tc],False,nid,mk,mt,nt)
    defcp[cp]=cp
CEPR,PL,Z=4302,3258,12934
U=[(7665,7665,'cite_ref-13'),(7949,7949,'cite_ref-14'),(8256,CEPR,'cite_ref-CEPR_10-5'),(8470,8470,'cite_ref-15'),(8870,CEPR,'cite_ref-CEPR_10-6'),(9130,CEPR,'cite_ref-CEPR_10-7'),
(9149,9149,'cite_ref-16'),(9665,9665,'cite_ref-17'),(10328,10328,'cite_ref-18'),(11087,PL,'cite_ref-ProtoLife_7-3'),(11283,CEPR,'cite_ref-CEPR_10-8'),(11470,11470,'cite_ref-19'),(12008,12008,'cite_ref-20'),(12525,PL,'cite_ref-ProtoLife_7-4'),
(12934,Z,'cite_ref-:0_21-0'),(13214,13214,'cite_ref-22'),(13496,13496,'cite_ref-23'),(14163,Z,'cite_ref-:0_21-1'),(14344,14344,'cite_ref-24')]
for cp,b,r in U:
    assert t.startswith('<ref',cp); A.adduse(cp,b,r)
f=A.find
A.addid(f('10.1542/peds.2007-2362'),'10.1542/peds.2007-2362','doi','primary_citation_field','10.1542/peds.2007-2362')
A.addid(f('17967921'),'17967921','pmid','primary_citation_field','17967921')
A.addid(f('10.1016/S0140-6736(09)61376-3'),'10.1016/S0140-6736(09)61376-3','doi','primary_citation_field','10.1016/s0140-6736(09)61376-3')
A.addid(f('19819542'),'19819542','pmid','primary_citation_field','19819542')
A.addid(f('10.1016/S0140-6736(11)61666-8'),'10.1016/S0140-6736(11)61666-8','doi','marker_target','10.1016/s0140-6736(11)61666-8','doi= parameter of {{Erratum}}: the erratum notice, not the cited article.')
for i in A.ids: assert A.inw(i['at']['cp'])
A.write('2026-11-03T01:56:00Z',files(A),'python3 stdlib (str.find, re) and lxml listing of sup/li ids; helper scripts in tools/','Whether erratum counts as ambiguous or warning: chose ambiguous per guide wording.',
 ['External links list items (two plain URL bullets, one with {{Webarchive}}) contain no citation template and no DOI/PMID, so not labelled as bibliography entries.','The Reflist is {{Reflist|2}} with no list-defined refs; ProtoLife and CEPR are defined in the body before the window.'])
