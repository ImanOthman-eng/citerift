import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
st=now(); a=Art('en-1382942090'); L=a.loc; T=a.text
# in-window definitions: (pos, cite tpl, note id, ref id, name)
rows=[(37066,'{{Cite journal','cite_note-78','cite_ref-78',None),
(37621,'{{Cite news','cite_note-79','cite_ref-79',None),
(37885,'{{Cite journal','cite_note-80','cite_ref-80',None),
(38547,'{{cite web','cite_note-81','cite_ref-81',None),
(39161,'{{Cite web','cite_note-82','cite_ref-82',None),
(39501,'{{Cite web','cite_note-83','cite_ref-83',None),
(39782,'{{Cite journal','cite_note-84','cite_ref-84',None),
(41031,'{{Cite book','cite_note-85','cite_ref-85',None),
(41481,'{{Cite book','cite_note-86','cite_ref-86',None),
(42188,'{{Cite journal','cite_note-87','cite_ref-87',None),
(43608,'{{Cite journal','cite_note-Schrotenboer-88','cite_ref-Schrotenboer_88-0','Schrotenboer'),
(44239,'{{Cite news','cite_note-Lipták-89','cite_ref-Lipták_89-0','Lipták'),
(44862,'{{cite web','cite_note-90','cite_ref-90',None)]
defs=[];uses=[];ids=[]
loc_of={}
for i,(p,tpl,nid,rid,name) in enumerate(rows,1):
    assert T.startswith('<ref',p)
    e=T.find('>',p)+1
    r={'cp':p,'quote':T[p:p+min(60,e-p)] if e-p>=8 else T[p:p+20]}
    marker='none';mt=None;nt=''
    if p==37885:
        marker='warning';mt='(Retracted, see doi:10.1016/j.ijhydene.2026.157095. If this is an intentional citation to a retracted paper, please replace {{retracted|...}} with {{retracted|...|intentional=yes}}.)'
        nt='Body also holds {{Retracted|doi=...}} (not a citation template); the rendered note states the cited paper is retracted.'
    defs.append(D(a,f'd{i}',r,'note',[L(tpl,after=p)],nid,name=name,marker=marker,marker_text=mt,notes=nt))
    uses.append((p,U('',r,r,rid)))
    loc_of[name]=r
# pre-window definitions that window uses bind to
pre={'IPCC-2022a':(3760,'{{Cite book','cite_note-IPCC-2022a-8'),'role2':(17279,'{{Cite journal','cite_note-role2-30'),
 'Collins l_collins2':(17660,'{{Cite news','cite_note-Collins_l_collins2-31'),'Chu':(18173,'{{Cite book','cite_note-Chu-32'),
 'Outlook2023':(18565,'{{Cite book','cite_note-Outlook2023-33')}
pl={}
for k,(p,tpl,nid) in pre.items():
    assert T.startswith(f'<ref name="{k}">',p)
    r={'cp':p,'quote':T[p:p+len(f'<ref name="{k}">')]}
    pl[k]=r
    defs.insert(0,D(a,'p_'+k,r,'note',[L(tpl,after=p)],nid,name=k,in_window=False,notes='Definition before the window; listed as binding target for a use in the window.'))
reuse=[(40549,'<ref name="IPCC-2022a"/>','IPCC-2022a','cite_ref-IPCC-2022a_8-4'),
 (42671,'<ref name="Chu" />','Chu','cite_ref-Chu_32-1'),(42741,'<ref name="Outlook2023" />','Outlook2023','cite_ref-Outlook2023_33-1'),
 (42904,'<ref name="role2" />','role2','cite_ref-role2_30-1'),(42924,'<ref name="Collins l_collins2" />','Collins l_collins2','cite_ref-Collins_l_collins2_31-1')]
for p,qt,k,rid in reuse:
    assert T[p:p+len(qt)]==qt
    uses.append((p,U('',{'cp':p,'quote':qt},pl[k],rid,'Reuse by name of a definition that lies before the window.')))
uses.sort(key=lambda x:x[0]); uses=[u for _,u in uses]
for i,u in enumerate(uses,1): u['id']=f'u{i}'
# renumber defs
for i,d in enumerate(defs,1): d['id']=f'd{i}'
retr=T.find('{{Retracted',a.w0)
for sch,cp,val in fields(a):
    at={'cp':cp,'quote':val}
    if retr<cp<retr+60: ids.append(I(at,sch,'marker_target',val.lower(),'Argument of {{Retracted}}: DOI of the retraction notice for the Yusaf et al. paper.'))
    else: ids.append(I(at,sch,'primary_citation_field',val.lower()))
finish(a,defs,uses,ids,st,'Nothing undecided. Template-transcluded sections elsewhere add rendered refs not in this source; none lie in the window.')
