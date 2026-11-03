import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
st=now(); a=Art('en-1360148888'); L=a.loc
def fld(label,val,after=0):
    p=a.text.find(label+val,after); assert p>=0
    return {'cp':p+len(label),'quote':val}
defs=[];uses=[];ids=[]
# refs
r_lag=L('<ref name="Lagier2012">'); r_gg=L('<ref name="GG">'); r_gg2=L('<ref name="GG" />'); 
r_rin=L('<ref>{{cite journal |vauthors=Rinke','<ref>{{cite journal |vauthors=Rinke'); r_rin['quote']='<ref>{{cite journal |vauthors=Rinke'
r_d20=L('<ref>{{cite journal |vauthors=Diakite A, Dubourg G, Dione N et al |title=Optimization')
r_chg=L('<ref>{{cite journal |vauthors=Chang')
r_gg3=L('<ref name="GG" />',nth=1)
r_d19=L('<ref>{{cite journal |vauthors=Diakite A, Dubourg G, Dione N et al |title=Extensive')
defs.append(D(a,'d1',r_lag,'note',[L('{{cite journal',after=r_lag['cp'])],'cite_note-Lagier2012-1',name='Lagier2012'))
defs.append(D(a,'d2',r_gg,'note',[L('{{cite journal',after=r_gg['cp'])],'cite_note-GG-2',name='GG'))
defs.append(D(a,'d3',r_rin,'note',[L('{{cite journal',after=r_rin['cp'])],'cite_note-3'))
defs.append(D(a,'d4',r_d20,'note',[L('{{cite journal',after=r_d20['cp'])],'cite_note-4'))
defs.append(D(a,'d5',r_chg,'note',[L('{{cite journal',after=r_chg['cp'])],'cite_note-5'))
defs.append(D(a,'d6',r_d19,'note',[L('{{cite journal',after=r_d19['cp'])],'cite_note-6',marker='warning',
  marker_text='This paper currently has an expression of concern, see doi:10.1371/journal.pone.0278361, PMID 36512561, Retraction Watch.',
  notes='Body also contains {{Expression of Concern|...}}, which is not a citation template and is not listed under templates; it produces the rendered warning sentence about the cited PLOS ONE paper.'))
b1=L('*{{cite journal |last1=Lagier'); b2=L('*{{cite journal |last1=Bilen')
defs.append(D(a,'d7',b1,'bibliography_entry',[L('{{cite journal',after=b1['cp'])],None,notes='Further reading list item.'))
defs.append(D(a,'d8',b2,'bibliography_entry',[L('{{cite journal',after=b2['cp'])],None,notes='Further reading list item.'))
uses=[U('u1',r_lag,r_lag,'cite_ref-Lagier2012_1-0'),U('u2',r_gg,r_gg,'cite_ref-GG_2-0'),U('u3',r_gg2,r_gg,'cite_ref-GG_2-1'),
 U('u4',r_rin,r_rin,'cite_ref-3'),U('u5',r_d20,r_d20,'cite_ref-4'),U('u6',r_chg,r_chg,'cite_ref-5'),U('u7',r_gg3,r_gg,'cite_ref-GG_2-2'),U('u8',r_d19,r_d19,'cite_ref-6')]
# identifiers
for dv,pv,anchor in [('10.1111/1469-0691.12023','23033984','Lagier2012'),('10.1111/1469-0691.12032','23148445','name="GG">'),
  ('10.1038/nature12352','23851394','Rinke'),('10.1038/s41598-020-66738-8','32541790','Optimization and standardization'),
  ('10.3389/fmicb.2019.02891','31921067','Chang Y'),('10.1371/journal.pone.0223543','31634343','Extensive culturomics'),
  ('10.1128/CMR.00014-14','25567229','Lagier|first1=Jean'),('10.1186/s40168-018-0485-5','29793532','Bilen')]:
    base=a.text.find(anchor if '|' not in anchor else 'last1=Lagier'); assert base>=0
    ids.append(I(fld('doi=',dv,base),'doi','primary_citation_field',dv.lower()))
    ids.append(I(fld('pmid=',pv,base),'pmid','primary_citation_field',pv))
eoc=a.text.find('{{Expression of Concern')
ids.append(I(fld('doi=','10.1371/journal.pone.0278361',eoc),'doi','marker_target','10.1371/journal.pone.0278361','Argument of {{Expression of Concern}} attached to the Diakite 2019 PLOS ONE reference.'))
ids.append(I(fld('pmid=','36512561',eoc),'pmid','marker_target','36512561','Argument of {{Expression of Concern}}.'))
ids.sort(key=lambda x:x['at']['cp'])
finish(a,defs,uses,ids,st,'Nothing undecided. Whether {{Expression of Concern}} counts as a citation template: treated as not (it is a notice).')
