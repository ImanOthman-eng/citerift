import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h1/tools')
from lib import *
TOOLS='Python 3 stdlib (str.find, re) and lxml to list sup/li elements; helper scripts in tools/'
a=A('ar-77110166')
def ref(pos,rid,mt,tpl='{{استشهاد',**kw):
    d=a.at(pos,'<ref'); assert d['cp']-pos<3
    a.define(d,'note',templates=[a.at(d['cp'],tpl)],rid=rid,mtext=mt,**kw); return d
def su(after,q,bind,rid,notes=''): a.use(a.at(after,q),bind,rid,notes)
d=ref(343,'cite_note-1','(Wikidata-based citation, Q111309344; li text is the template output)'); a.use(d,d,'cite_ref-1')
Z=ref(604,'cite_note-:0-2','"الحلة السيراء، تأليف ابن الأبار، (1/37)". الموسوعة الشاملة.',name=':0'); a.use(Z,Z,'cite_ref-:0_2-0')
d=ref(1024,'cite_note-3','أعلام نساء الأندلس. Dar Al Kotob Al Ilmiyah'); a.use(d,d,'cite_ref-3')
E=ref(2262,'cite_note-EI2-4','The Encyclopaedia of Islam, Second Edition (12 vols.). Leiden: E. J. Brill. 1960–2005.','{{EI2}}',name='EI2',notes='Body is the shortcut template {{EI2}}, which renders a full citation; counted as a citation template by purpose. Not certain it counts.')
a.use(E,E,'cite_ref-EI2_4-0')
su(2400,'<ref name="EI2" />',E,'cite_ref-EI2_4-1')
d=ref(2500,'cite_note-5','خير الدين. الأعلام - ج 2 : افتخار - دنانير'); a.use(d,d,'cite_ref-5')
d=ref(3291,'cite_note-6','كامل سلمان جاسم. معجم الأدباء'); a.use(d,d,'cite_ref-6')
d=ref(4515,'cite_note-7','"تمام بن عامِر". www.islamic-content.com'); a.use(d,d,'cite_ref-7')
d=ref(4871,'cite_note-8','خير الدين الزركلي (2002)، الأعلام... (Wikidata-based citation Q113504685)'); a.use(d,d,'cite_ref-8')
d=ref(4926,'cite_note-9','"موسوعة التراجم والأعلام - تمام بن عامر". www.taraajem.com'); a.use(d,d,'cite_ref-9')
su(5400,'<ref name="EI2" />',E,'cite_ref-EI2_4-2')
su(5700,'<ref name="EI2" />',E,'cite_ref-EI2_4-3')
d=ref(5785,'cite_note-10','Hermes، Nizar F. (2014). "The Moor\'s First Sight..." Springer'); a.use(d,d,'cite_ref-10')
su(6200,'<ref name=":0" />',Z,'cite_ref-:0_2-1')
d=ref(6305,'cite_note-11','ابن الابار... الحلة السيراء (في تراجم الشعراء من أعيان الأندلس والمغرب)'); a.use(d,d,'cite_ref-11')
a.ident(a.at(5785,'10.1057/9781137405029_3'),'doi','primary_citation_field','10.1057/9781137405029_3','DOI = field (uppercase name)')
a.write(TOOLS,['Two citations (343 and 4871) use {{استشهاد بويكي بيانات|Q…}}, a Wikidata-driven citation template; their content is not in the source. Counted as citation templates with a note-free definition.'],'nothing undecided; whether {{EI2}} is a citation template')
