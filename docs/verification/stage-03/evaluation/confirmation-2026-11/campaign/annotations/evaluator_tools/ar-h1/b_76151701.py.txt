import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h1/tools')
from lib import *
TOOLS='Python 3 stdlib (str.find, re) and lxml to list sup/li elements; helper scripts in tools/'
a=A('ar-76151701'); t=a.t
D=[]
def ref(pos,rid,mt,tpl='{{استشهاد',**kw):
    d=a.at(pos,'<ref')
    c=a.at(d['cp'],tpl)
    a.define(d,'note',templates=[c],rid=rid,mtext=mt,**kw); return d
d1=ref(8588,'cite_note-مولد_تلقائيا1-10','Yamashita, Soichiro; Sato, Shigehito; ... "Lidocaine Toxicity During Frequent Viscous Lidocaine Use for Painful Tongue Ulcer"',name='مولد تلقائيا1')
a.use(d1,d1,'cite_ref-مولد_تلقائيا1_10-0')
s=a.at(9300,'<ref name="مولد تلقائيا1" />')
a.use(s,d1,'cite_ref-مولد_تلقائيا1_10-1','self-closing reuse')
d3=ref(9551,'cite_note-11','Elad, Sharon; Cohen, Galit; ... "Systemic absorption of lidocaine..."'); a.use(d3,d3,'cite_ref-11')
d4=ref(11281,'cite_note-12','"\'MuGard Clinical Data\'". مؤرشف من الأصل في 2013-05-25.'); a.use(d4,d4,'cite_ref-12')
d5=ref(12635,'cite_note-13','"Episil current prescribing information". مؤرشف من الأصل في 2018-09-26.'); a.use(d5,d5,'cite_ref-13')
d6=ref(13109,'cite_note-14','Tiberg، F؛ وآخرون (2009). "Treatment of oral mucositis pain..."'); a.use(d6,d6,'cite_ref-14')
d7=ref(13326,'cite_note-15','Tiberg، F؛ وآخرون. "Data on file". CAMURUS.'); a.use(d7,d7,'cite_ref-15')
d8=ref(13970,'cite_note-16','Abdulrhman، M (أبريل 2012). "Honey and a mixture of honey..."'); a.use(d8,d8,'cite_ref-16')
# identifiers
def idn(after,q,scheme,role,key,notes=''): a.ident(a.at(after,q,80),scheme,role,key,notes)
idn(8588,'10.1016/S0885-3924(02)00498-0|'[:-1],'doi','primary_citation_field','10.1016/s0885-3924(02)00498-0','DOI= field (uppercase field name)')
u=t.find('https://onlinelibrary.wiley.com/doi/abs/10.1111',9551)
q=t[u:t.find('|',u)]
idn(u,q,'doi','identifier_link','10.1111/j.1600-0714.1999.tb02018.x','publisher URL, path /doi/abs/10.… (guide names /doi/10.… ; read the same way); in مسار= field')
idn(9800,'10.1111/j.1600-0714.1999.tb02018.x','doi','primary_citation_field','10.1111/j.1600-0714.1999.tb02018.x','DOI= field')
u=t.find('https://web.archive.org/web/20191211052540',9551)
q=t[u:t.find('|',u)]
idn(u,q,'doi','not_a_target','10.1111/j.1600-0714.1999.tb02018.x','archive.org snapshot URL containing a publisher /doi/abs/ URL; another site URL, so not an identifier of its own. Key is the DOI text inside.')
idn(14200,'22475306','pmid','primary_citation_field','22475306','pmid= field')
idn(14300,'10.3109/08880018.2012.669026','doi','primary_citation_field','10.3109/08880018.2012.669026','doi= field')
a.write(TOOLS,['The 3 lines under "== مصادر عامة ==" (from 14920) are bare external links with no list marker, citation template or DOI/PMID; not labelled as bibliography entries (3.4). {{webarchive}} and {{وصلة مكسورة}} are not citation templates.','The ref at 7253 (Sonis et al.) starts before the window and has no use in the window; not listed.','Render has a Wikidata-generated infobox reference (cite_ref-wikidata-..._1-1) that has no source location; not listed (3.3).','The jpsmjournal.com URL contains a PII (S0885-3924(02)00498-0), not a DOI; not labelled.'],'nothing undecided')
