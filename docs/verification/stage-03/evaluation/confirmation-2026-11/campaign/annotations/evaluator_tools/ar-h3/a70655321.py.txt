import sys;sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h3/tools')
from lib import A
a=A('ar-70655321')
d1=a.D('d1','<ref name="Reidenberg">{{',name='Reidenberg',tpl=[('{{استشهاد بدورية محكمة',)],rn='cite_note-Reidenberg-1',notes='first definition; five later self-closing uses (u2-u6)')
rid=['cite_ref-Reidenberg_1-%d'%i for i in range(6)]
a.U('u1','<ref name="Reidenberg">{{',d1,rid[0])
pos=d1['cp']
for k in range(2,7):
    at=a.U('u%d'%k,'<ref name="Reidenberg" />',d1,rid[k-1],after=pos+1); pos=at['cp']
a.I('10.1002/ar.20541','doi','identifier_link','10.1002/ar.20541',notes='inside the url= value https://onlinelibrary.wiley.com/store/10.1002/ar.20541/asset/20541_ftp.pdf; not a /doi/ path so end of DOI is inferred from the same template doi= field',after=d1['cp'])
a.I('10.1002/ar.20541','doi','primary_citation_field','10.1002/ar.20541',after=a.t.find('doi = 10.1002',d1['cp']))
a.I('17516440','pmid','primary_citation_field','17516440')
a.I('10.1002/ar.20541','doi','not_a_target','10.1002/ar.20541',notes='inside an archive.org snapshot URL (مسار أرشيف), another site URL',after=a.t.find('web.archive.org',d1['cp']))
a.un.append('Window starts at cp 2047, inside the first sentence; the Reidenberg <ref> definition at cp 2139 is the first and only definition and lies in the window. The rest of the window is a taxonomic bullet list with no citations.')
a.write()
