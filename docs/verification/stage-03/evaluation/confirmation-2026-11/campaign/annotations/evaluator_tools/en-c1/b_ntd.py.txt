import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
st=now(); a=Art('en-1383058278'); L=a.loc
T=a.text
def q(s,after=0):
    return L(s,after=after)
rows=[ # open quote, name, note id, ref id, tpl, unstructured, notes
 ('<ref name=":0">',':0','cite_note-:0-48','cite_ref-:0_48-0','{{Cite journal',False,''),
 ('<ref>{{cite journal | doi = 10.1001/jama.252.11.1438',None,'cite_note-49','cite_ref-49','{{cite journal',False,''),
 ('<ref>Summer [http://msc.sagepub.com',None,'cite_note-50','cite_ref-50',None,True,'Hand-written plain-text citation with a bare external link; no citation template; no DOI/PMID.'),
 ('<ref>{{Cite journal | doi=10.1111/j.1471-0528.2008.01700.x',None,'cite_note-51','cite_ref-51','{{Cite journal',False,''),
 ('<ref>Norem et.al [http://journals.lww.com',None,'cite_note-52','cite_ref-52',None,True,'Hand-written plain-text citation with a bare external link; no citation template; no DOI/PMID.'),
 ('<ref>{{Cite journal |last1=De Wals |first1=Philippe',None,'cite_note-53','cite_ref-53','{{Cite journal',False,'Same NEJM paper (doi 10.1056/NEJMoa067103) as the later De Wals reference, but the bodies differ and both are unnamed, so each is its own definition.'),
 ('<ref>{{cite journal |last1=Daly |first1=S',None,'cite_note-54','cite_ref-54','{{cite journal',False,''),
 ('<ref>{{Cite journal |last=Ray |first=Joel G.',None,'cite_note-55','cite_ref-55','{{Cite journal',False,''),
 ('<ref name="Greene, N. D. E. 20092">','Greene, N. D. E. 20092','cite_note-Greene,_N._D._E._20092-56','cite_ref-Greene,_N._D._E._20092_56-0','{{cite journal',False,'Distinct from the earlier name "Genetics of human neural tube defects" (before window).'),
 ('<ref>{{cite journal |last1=Milunsky |first1=A |last2=Jick',None,'cite_note-57','cite_ref-57','{{cite journal',False,''),
 ('<ref>{{cite journal |last1=Goh |first1=YI',None,'cite_note-58','cite_ref-58','{{cite journal',False,''),
 ('<ref>{{cite journal |author=De Wals P',None,'cite_note-59','cite_ref-59','{{cite journal',False,'Same NEJM paper as the earlier De Wals reference (d6) but different body and unnamed, so a separate definition.'),
 ('<ref>{{Cite journal |last1=Naithani',None,'cite_note-60','cite_ref-60','{{Cite journal',False,''),
]
defs=[];uses=[];ids=[]
n=0;first={}
for qq,name,nid,rid,tpl,uns,nt in rows:
    n+=1
    r=L(qq,after=a.w0); r['quote']=qq[:60]; L(r['quote'],after=r['cp'])
    assert r['cp']>=a.w0 and r['cp']<a.w1
    marker='none';mt=None
    if name==':0':
        marker='warning'; mt='(Retracted, see doi:10.1016/j.jogc.2022.06.009, PMID 35934417. If this is an intentional citation to a retracted paper, please replace {{retracted|...}} with {{retracted|...|intentional=yes}}.)'
        nt='Body also holds {{Retracted|doi=...|pmid=...}} (not a citation template); rendered note says the cited JOGC paper is retracted.'
        first[name]=r
    tp=[L(tpl,after=r['cp'])] if tpl else []
    defs.append(D(a,f'd{n}',r,'note',tp,nid,name=name,unstructured=uns,marker=marker,marker_text=mt,notes=nt))
    uses.append(U(f'u{n}',r,r,rid))
u2=L('<ref name=":0" />'); assert u2['cp']>a.w0
uses.insert(1,U('u_0b',u2,first[':0'],'cite_ref-:0_48-1','Self-closing reuse of :0; binds to the first definition (retracted-paper reference).'))
for i,u in enumerate(uses): u['id']=f'u{i+1}'
# identifiers
retr=T.find('{{Retracted')
for sch,cp,val in fields(a):
    at={'cp':cp,'quote':val}
    if cp>retr and cp<retr+80:
        ids.append(I(at,sch,'marker_target',val.lower() if sch=='doi' else val,'Argument of {{Retracted}}: DOI/PMID of the retraction notice for the Wilson et al. paper.'))
    else:
        ids.append(I(at,sch,'primary_citation_field',val.lower() if sch=='doi' else val))
finish(a,defs,uses,ids,st,'Nothing undecided. Summer and Norem refs are plain-text citations with external links and no DOI/PMID.')
