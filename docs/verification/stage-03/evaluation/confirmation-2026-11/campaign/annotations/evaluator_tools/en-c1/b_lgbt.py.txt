import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
st=now(); a=Art('en-1377291884'); L=a.loc; T=a.text
rows=[(162615,'{{Cite journal','cite_note-182','cite_ref-182'),(163066,'{{Cite journal','cite_note-183','cite_ref-183'),
(163761,'{{Cite web','cite_note-184','cite_ref-184'),(168390,'{{Cite journal','cite_note-185','cite_ref-185'),
(169259,'{{Citation','cite_note-186','cite_ref-186'),(170297,'{{Cite journal','cite_note-187','cite_ref-187')]
defs=[];uses=[]
for i,(p,tpl,nid,rid) in enumerate(rows,1):
    assert T.startswith('<ref>',p)
    r={'cp':p,'quote':T[p:p+min(60,T.find('>',p)-p+1+25)]}
    marker='none';mt=None;nt=''
    if p==163066:
        marker='warning';mt='This paper currently has an expression of concern, see doi:10.1155/2017/4981984, PMID 28848679, Retraction Watch.'
        nt='Body also holds {{Expression of Concern|...}} (not a citation template); rendered note states an expression of concern about the cited paper.'
    if p==169259: nt='Rendered author text contains the word "Concerns" only as part of an organisation name (Committee on Lesbian, Gay, and Bisexual Concerns); not a marker. Template parameters use <nowiki>.'
    defs.append(D(a,f'd{i}',r,'note',[L(tpl,after=p)],nid,marker=marker,marker_text=mt,notes=nt))
    uses.append((p,U('',r,r,rid)))
pre={'ncpcr':(5865,'cite_note-ncpcr-10'),'dcpcri':(17967,'cite_note-dcpcri-27')}
pl={}
for k,(p,nid) in pre.items():
    qt=f'<ref name="{k}">'; assert T.startswith(qt,p)
    r={'cp':p,'quote':qt+'Intervenor: '}; assert T.startswith(r['quote'],p)
    pl[k]=r
    defs.insert(0,D(a,'p_'+k,r,'note',[],nid,name=k,in_window=False,notes='Definition before the window (body is text plus {{Harvnb}}, not a citation template); listed as binding target of uses in the window.'))
reuse=[(164345,'ncpcr','cite_ref-ncpcr_10-5'),(164700,'dcpcri','cite_ref-dcpcri_27-1'),(165443,'dcpcri','cite_ref-dcpcri_27-2'),(166023,'dcpcri','cite_ref-dcpcri_27-3'),
 (166549,'dcpcri','cite_ref-dcpcri_27-4'),(167041,'dcpcri','cite_ref-dcpcri_27-5'),(168139,'dcpcri','cite_ref-dcpcri_27-6')]
for p,k,rid in reuse:
    qt=f'<ref name="{k}" />'; assert T.startswith(qt,p)
    uses.append((p,U('',{'cp':p,'quote':qt},pl[k],rid,'Self-closing reuse of a definition before the window.')))
uses.sort(key=lambda x:x[0]); uses=[u for _,u in uses]
for i,u in enumerate(uses,1): u['id']=f'u{i}'
for i,d in enumerate(defs,1): d['id']=f'd{i}'
ids=[]
eoc=T.find('{{Expression of Concern',a.w0)
for sch,cp,val in fields(a):
    at={'cp':cp,'quote':val}
    if eoc<cp<eoc+80: ids.append(I(at,sch,'marker_target',val.lower(),'Argument of {{Expression of Concern}} attached to Sullins 2016 reference: identifier of the notice.'))
    else: ids.append(I(at,sch,'primary_citation_field',val.lower()))
finish(a,defs,uses,ids,st,'Nothing undecided.')
