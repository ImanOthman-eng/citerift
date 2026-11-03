import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h1/tools')
from lib import *
TOOLS='Python 3 stdlib (str.find, re) and lxml to list sup/li elements; helper scripts in tools/'
for d in ['ar-64908403','ar-64908413']:
    a=A(d)
    a.write(TOOLS,['The rendered page has two footnote markers (Wikidata-generated references from the infobox template {{صندوق معلومات مجرة}}); they are not in the source and are not listed (3.3).','No <ref>, footnote template, bibliography entry, DOI or PMID in the window. The line "* {{ويكي سكاي}}" is an external-link template, not a citation template.'],'nothing undecided')
a=A('ar-74870204')
t=a.t
r1=t.find('<ref>')
d1=a.at(r1,'<ref>{{استشهاد ويب')
c1=a.at(r1,'{{استشهاد ويب')
r2=t.find('<ref>',r1+10)
d2=a.at(r2,'<ref>{{استشهاد ويب')
c2=a.at(r2,'{{استشهاد ويب')
a.define(d1,'note',templates=[c1],rid='cite_note-6',mtext='"SIMBAD Astronomical Database". سيمباد. مؤرشف من الأصل في 2018-01-08.')
a.define(d2,'note',templates=[c2],rid='cite_note-7',mtext='"VizieR". فيزير. {{استشهاد بويب}}: الوسيط |مسار= غير موجود أو فارع (مساعدة)',notes='Citation template has no url (the second field is عنوان/عمل only); Cite error text appears in rendering, not a retraction marker.')
a.use(d1,d1,'cite_ref-6'); a.use(d2,d2,'cite_ref-7')
a.write(TOOLS,['Eight rendered markers: six wikidata-generated ones from the infobox/templates (not in source, 3.3) and two source refs (cite_ref-6, cite_ref-7).'],'nothing undecided')
