import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
st=now(); a=Art('en-1323580591'); L=a.loc
def fld(label,val,after=0):
    p=a.text.find(label+val,after); assert p>=0
    return {'cp':p+len(label),'quote':val}
# (ref open quote, name, note id, ref id, tpl or None, notes)
rows=[
 ('<ref>{{Harvnb|Rekers|Lovaas|1974|pp=173}}',None,'cite_note-50','cite_ref-50',None,'Body is only {{Harvnb}} (a short-citation link template, not a citation template).'),
 ('<ref>{{Harvnb|Rekers|Lovaas|1974|pp=174}}',None,'cite_note-51','cite_ref-51',None,'Body is only {{Harvnb}} (pp=174; different from the pp=173 note).'),
 ('<ref name="behavioraltreatment">','behavioraltreatment','cite_note-behavioraltreatment-52','cite_ref-behavioraltreatment_52-0','{{cite journal',''),
 ('<ref name="cnn7jun2011">','cnn7jun2011','cite_note-cnn7jun2011-53','cite_ref-cnn7jun2011_53-0','{{cite news',''),
 ('<ref>{{cite news|url=https://healthland.time.com',None,'cite_note-54','cite_ref-54','{{cite news',''),
 ('<ref>{{cite news|url=http://www.huffingtonpost.com',None,'cite_note-55','cite_ref-55','{{cite news',''),
 ('<ref>{{citation |url=http://www.apa.org',None,'cite_note-56','cite_ref-56','{{citation',''),
 ('<ref>{{citation|url=http://lgbtphysicists.org',None,'cite_note-57','cite_ref-57','{{citation',''),
 ('<ref name="Nicolosi">','Nicolosi','cite_note-Nicolosi-58','cite_ref-Nicolosi_58-0','{{cite book',''),
 ('<ref name="NARTH">','NARTH','cite_note-NARTH-59','cite_ref-NARTH_59-0','{{citation',''),
 ('<ref>{{cite news |last= Quandt',None,'cite_note-60','cite_ref-60','{{cite news',''),
 ('<ref>{{cite web|url=https://www.theatlantic.com',None,'cite_note-61','cite_ref-61','{{cite web',''),
 ('<ref>{{cite web|url=http://www.newsweek.com',None,'cite_note-62','cite_ref-62','{{cite web',''),
 ('<ref>{{Cite web|title=UN panel',None,'cite_note-63','cite_ref-63','{{Cite web','Inside the caption of a [[File:SamBrinton.jpg]] image.'),
 ('<ref name="SurgeonGeneral">','SurgeonGeneral','cite_note-SurgeonGeneral-64','cite_ref-SurgeonGeneral_64-0','{{citation',''),
 ('<ref name="Ritter">','Ritter','cite_note-Ritter-66','cite_ref-Ritter_66-0','{{cite news',''),
]
defs=[];uses=[];ids=[]
n=0
for q,name,nid,rid,tpl,nt in rows:
    n+=1
    r=L(q); r['quote']=q if len(q)<=60 else q[:60]
    L(r['quote'],after=r['cp']) 
    marker='none'; mt=None; note=nt
    tp=[L(tpl,after=r['cp'])] if tpl else []
    if name=='behavioraltreatment':
        marker='warning'; mt='This paper currently has an expression of concern, see doi:10.1002/jaba.781, PMID 33084123, Retraction Watch.'
        note='Body also holds {{Expression of Concern}} (not a citation template), rendering a warning about the cited JABA paper. ref=none in the cite template only suppresses the harv anchor.'
    defs.append(D(a,f'd{n}',r,'note',tp,nid,name=name,marker=marker,marker_text=mt,notes=note,unstructured=False))
    uses.append(U(f'u{n}',r,r,rid))
sf=L('{{sfn|Spitzer|2003}}')
defs.append(D(a,f'd{n+1}',sf,'generated_note',[],'cite_note-FOOTNOTESpitzer2003-65',name=None,group='',notes='Only sfn call with these arguments in the article, so a definition. Rendered footnote "Spitzer 2003." links to a bibliography entry elsewhere (outside window).'))
uses.append(U(f'u{n+1}',sf,sf,'cite_ref-FOOTNOTESpitzer2003_65-0'))
ids+= [I(fld('doi=','10.1901/jaba.1974.7-173'),'doi','primary_citation_field','10.1901/jaba.1974.7-173'),
       I(fld('pmid=','4436165'),'pmid','primary_citation_field','4436165'),
       I(fld('doi=','10.1002/jaba.781'),'doi','marker_target','10.1002/jaba.781','Argument of {{Expression of Concern}}: the notice DOI.'),
       I(fld('pmid=','33084123'),'pmid','marker_target','33084123','Argument of {{Expression of Concern}}.')]
finish(a,defs,uses,ids,st,'Whether {{Harvnb}}-only <ref> bodies count as unstructured: labelled false (a template, though not a citation template). Spitzer sfn is a generated_note definition; no earlier call exists in the article.')
