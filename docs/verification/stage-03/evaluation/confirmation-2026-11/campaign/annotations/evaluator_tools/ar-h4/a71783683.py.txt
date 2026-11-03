import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4/tools')
from lib import *
from lxml import html
A=Art('ar-71783683'); T=A.t
doc=html.parse(f'{BASE}/packets/ar-71783683/render.html').getroot()
sups=[s.get('id') for s in doc.xpath('//sup[contains(@typeof,"mw:Extension/ref")]')]
lis=[l.get('id') for l in doc.xpath('//li[starts-with(@id,"cite_note")]')]
nih=[s for s in sups if 'NIH' in s]; nihli=[l for l in lis if 'NIH' in l]
assert len(nih)==2 and len(nihli)==1
P=A.at
d1=A.defn(P('<ref name="pmid16112947">'),'note',name='pmid16112947',templates=[P('{{استشهاد بدورية محكمة\n| عدة مؤلفين = Kuhl H')],rid='cite_note-pmid16112947-1',notes='Definition starts before the window; listed as binding target (its use markers 2 and 3 are in the window). Its identifier fields are in the window.')
A.use(P('<ref name="pmid16112947" />',1),d1,'cite_ref-pmid16112947_1-1')
A.use(P('<ref name="pmid16112947" />',2),d1,'cite_ref-pmid16112947_1-2')
dm=A.defn(P('<ref name="Micromedex">'),'note',name='Micromedex',templates=[P('{{استشهاد ويب\n| مسار = http://www.micro')],rid='cite_note-Micromedex-2'); A.use(dm,dm,'cite_ref-Micromedex_2-0')
A.use(P('<ref name="Micromedex" />'),dm,'cite_ref-Micromedex_2-1')
dM=A.defn(P('<ref name="Martindale">'),'note',name='Martindale',templates=[P('{{استشهاد بكتاب\n| محرر = Sweetman')],rid='cite_note-Martindale-3'); A.use(dM,dM,'cite_ref-Martindale_3-0')
dD=A.defn(P('<ref name="Drugs.com">'),'note',name='Drugs.com',templates=[P('{{استشهاد ويب\n| مسار = https://www.drugs.com')],rid='cite_note-Drugs.com-4'); A.use(dD,dD,'cite_ref-Drugs.com_4-0')
nm='titleNIH\xa0— Menopausal Hormone Therapy Information'
dN=A.defn(P('<ref name="titleNIH'),'note',name=nm,templates=[P('{{استشهاد ويب\n| مسار = http://www.nih.gov/PHTindex.htm')],rid=nihli[0],notes='Name contains a non-breaking space (U+00A0) after titleNIH.'); A.use(dN,dN,nih[0])
A.use(P('<ref name="titleNIH',2),dN,nih[1])
d6=A.defn(P('<ref name="pmid16396517">'),'note',name='pmid16396517',templates=[P('{{استشهاد بدورية محكمة\n| عدة مؤلفين = Menon')],rid='cite_note-pmid16396517-6'); A.use(d6,d6,'cite_ref-pmid16396517_6-0')
# identifiers
A.ident(P('pmid = 16112947',off=7,ln=8),'pmid','primary_citation_field','16112947')
A.ident(P('doi = 10.1080/13697130500148875',off=6,ln=25),'doi','primary_citation_field','10.1080/13697130500148875')
A.ident(P('<ref name="pmid16112947" />',1,off=15,ln=8),'pmid','not_a_target','16112947','digits inside the value of ref name= in a reuse')
A.ident(P('<ref name="pmid16112947" />',2,off=15,ln=8),'pmid','not_a_target','16112947','digits inside the value of ref name= in a reuse')
A.ident(P('<ref name="pmid16396517">',off=15,ln=8),'pmid','not_a_target','16396517','digits inside the value of ref name=')
A.ident(P('pmid = 16396517',off=7,ln=8),'pmid','primary_citation_field','16396517')
A.ident(P('doi = 10.2165/00024677-200605010-00005',off=6,ln=31),'doi','primary_citation_field','10.2165/00024677-200605010-00005')
A.write(0,'python3 stdlib listing, lxml sup/li listing, own quote-checking builder tools/lib.py','The first use (the definition of pmid16112947 at 1503) and the name-value digits there start before the window and are not labelled as in-window items.','2026-11-03T01:56:13Z')
