import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4/tools')
from lib import *
A=Art('ar-72638823'); T=A.t
CT=lambda n=1:A.at('{{استشهاد',n)
r=[]
# refs in source order
d1=A.defn(A.at('<ref>{{استشهاد بدورية محكمة|عنوان=Meanings'),'note',templates=[A.at('{{استشهاد بدورية محكمة|عنوان=Meanings')],rid='cite_note-1')
A.use(d1,d1,'cite_ref-1')
d2=A.defn(A.at('<ref name="مولد تلقائيا1">'),'note',name='مولد تلقائيا1',templates=[A.at('{{استشهاد بدورية محكمة|عنوان=Gee,')],rid='cite_note-مولد_تلقائيا1-2')
A.use(d2,d2,'cite_ref-مولد_تلقائيا1_2-0')
d3=A.defn(A.at('<ref>{{استشهاد بدورية محكمة|عنوان=Poliomyelitis'),'note',templates=[A.at('{{استشهاد بدورية محكمة|عنوان=Poliomyelitis')],rid='cite_note-3')
A.use(d3,d3,'cite_ref-3')
A.use(A.at('<ref name="مولد تلقائيا1" />'),d2,'cite_ref-مولد_تلقائيا1_2-1','self-closing reuse')
d4=A.defn(A.at('<ref>{{استشهاد بدورية محكمة|عنوان=Environmental Protection'),'note',templates=[A.at('{{استشهاد بدورية محكمة|عنوان=Environmental Protection')],rid='cite_note-4')
A.use(d4,d4,'cite_ref-4')
d5=A.defn(A.at('<ref>{{استشهاد بدورية محكمة|عنوان=EPA proposes'),'note',templates=[A.at('{{استشهاد بدورية محكمة|عنوان=EPA proposes')],rid='cite_note-5')
A.use(d5,d5,'cite_ref-5')
D1='10.2134/jeq1997.00472425002600030002x'
u=A.at('https://acsess.onlinelibrary.wiley.com/doi/abs/'+D1,ln=len('https://acsess.onlinelibrary.wiley.com/doi/abs/'+D1))
A.ident(u,'doi','identifier_link',D1,'publisher URL with /doi/ path (url field)')
A.ident(A.at('DOI='+D1,off=4,ln=len(D1)),'doi','primary_citation_field',D1)
s='https://web.archive.org/web/20200421004828/https://acsess.onlinelibrary.wiley.com/doi/abs/'+D1
A.ident(A.at(s,ln=len(s)),'doi','not_a_target',D1,'archive.org snapshot URL of the publisher URL (مسار أرشيف)')
D2='10.1093/ww/9780199540884.001.0001/ww-9780199540884-e-16908'
A.ident(A.at('ukwhoswho.com/view/'+D2,off=19,ln=len(D2)),'doi','identifier_link',D2,'DOI is the path of a publisher URL without /doi/ segment; I took the path after /view/ to the end of the URL as the DOI. Quote is the DOI text, not the whole URL.')
A.ident(A.at('http://www.ukwhoswho.com/view/'+D2,off=len('http://www.ukwhoswho.com/view/'),ln=len(D2)),'doi','not_a_target',D2,'inside an archive.org snapshot URL; quote is the DOI text')
D3='10.2307/4591085'
A.ident(A.at('jstor.org/stable/'+D3+'?origin',off=len('jstor.org/stable/'),ln=len(D3)),'doi','identifier_link',D3,'DOI in the path of a jstor URL (no /doi/ segment); ?origin=crossref is a query, not part of the DOI')
A.ident(A.at('DOI='+D3,off=4,ln=len(D3)),'doi','primary_citation_field',D3)
A.ident(A.at('web/20200421033729/https://www.jstor.org/stable/'+D3,off=len('web/20200421033729/https://www.jstor.org/stable/'),ln=len(D3)),'doi','not_a_target',D3,'inside an archive.org snapshot URL; quote is the DOI text')
A.ident(A.at('DOI=10.1038/nature.2012.10343',off=4,ln=len('10.1038/nature.2012.10343')),'doi','primary_citation_field','10.1038/nature.2012.10343')
A.write(0,'python3 stdlib (re/str.find listing), lxml (list sup/li); own quote-checking builder tools/lib.py','Archive-URL and non-/doi/ publisher-URL identifiers: raw text chosen as DOI substring (see notes).','2026-11-03T01:56:13Z')
