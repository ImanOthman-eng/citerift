import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2/tools')
from lib import *
A=Art('en-1376686890'); t=A.t
D=[(6928,'Sneppen','cite_note-Sneppen-11',False),(7298,None,'cite_note-12',False),(7913,'Blumhofer-Hutter-1997-','cite_note-Blumhofer-Hutter-1997--13',False),
(8899,None,'cite_note-14',False),(9196,None,'cite_note-15',False),(11783,'MathWorld','cite_note-MathWorld-16',True),(13022,':1','cite_note-:1-17',False)]
rid={6928:'cite_ref-Sneppen_11-0',7298:'cite_ref-12',7913:'cite_ref-Blumhofer-Hutter-1997-_13-0',8899:'cite_ref-14',9196:'cite_ref-15',11783:'cite_ref-MathWorld_16-0',13022:'cite_ref-:1_17-0'}
for cp,n,nid,un in D:
    assert t.startswith('<ref',cp)
    tcs=[] if un else [t.index('{{',cp)]
    mk='none';mt=None;nt=''
    if cp==7913:
        mk='ambiguous';mt='(Erratum: doi:10.1016/S0550-3213(97)00228-9)'
        nt='Followed by {{erratum|doi=10.1016/S0550-3213(97)00228-9}}: an erratum notice for the cited article; not a retraction. ref name ends with a hyphen. Definition body is spread over several lines.'
    if un: nt='Hand-written citation with a bare MathWorld URL link; no citation template.'
    A.adddef(cp,'note',n,'',tcs,un,nid,mk,mt,nt)
    A.adduse(cp,cp,rid[cp])
f=A.find
A.addid(f('34244573',6900),'34244573','pmid','primary_citation_field','34244573')
A.addid(f('10.1038/s41598-021-93595-w'),'10.1038/s41598-021-93595-w','doi','primary_citation_field','10.1038/s41598-021-93595-w')
A.addid(f('10.1016/S0550-3213(96)00644-X'),'10.1016/S0550-3213(96)00644-X','doi','primary_citation_field','10.1016/s0550-3213(96)00644-x')
A.addid(f('10.1016/S0550-3213(97)00228-9'),'10.1016/S0550-3213(97)00228-9','doi','marker_target','10.1016/s0550-3213(97)00228-9','doi= of {{erratum}}: the erratum notice, not the cited article.')
A.addid(f('10.1038/scientificamerican0575-102'),'10.1038/scientificamerican0575-102','doi','primary_citation_field','10.1038/scientificamerican0575-102')
for i in A.ids: assert A.inw(i['at']['cp'])
A.write('2026-11-03T01:56:00Z',files(A),'python3 stdlib (str.find, re) and lxml listing of sup/li ids; helper scripts in tools/','Erratum classified as ambiguous per guide wording.',
 ['Further reading item (Baker and Wüstholz, with {{ISBN}} only) has no citation template and no DOI/PMID, so not labelled a bibliography entry by the guide 3.4 wording; External links bullets likewise.','No reuses by name occur in this article; every named ref is defined once.'])
