import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4/tools')
from lib import *
A=Art('ar-76436758'); T=A.t
def P(a,n=1): return A.at(a,n)
# out-of-window / later definitions (binding targets)
ob='Definition outside the window, listed as binding target.'
dE=A.defn(P('<ref name=edge>'),'note',name='edge',templates=[P('{{استشهاد بويب|مسار=https://www.edge.org')],rid='cite_note-edge-32',notes=ob)
dR=A.defn(P('<ref name="Russel, C.A. 2002 7">'),'note',name='Russel, C.A. 2002 7',templates=[P('{{استشهاد بكتاب|مؤلف=Russel, C.A.')],rid='cite_note-Russel,_C.A._2002_7-6',notes=ob)
dS=A.defn(P('<ref name=Shapin1996>'),'note',name='Shapin1996',templates=[P('{{استشهاد بكتاب| مؤلف = Shapin, S.')],rid='cite_note-Shapin1996-7',notes=ob)
dB=A.defn(P('<ref name=Brooke1991>'),'note',name='Brooke1991',templates=[P('{{استشهاد بكتاب| مؤلف = Brooke, J. H.')],rid='cite_note-Brooke1991-8',notes=ob)
dX=A.defn(P('<ref name="scientists religion">'),'note',name='scientists religion',templates=[P('{{استشهاد بدورية محكمة|الأخير=Ecklund')],rid='cite_note-scientists_religion-44',notes=ob+' Appears after the window; the window use is a self-closing ref that precedes it.')
# window refs in source order
def plain(a,rid,sid,notes=''):
    d=A.defn(P(a),'note',unstructured=True,rid=rid,notes=notes); A.use(d,d,sid); return d
def tmpl(a,t,rid,sid,notes=''):
    d=A.defn(P(a),'note',templates=[P(t)],rid=rid,notes=notes); A.use(d,d,sid); return d
plain('<ref>[[ريتشارد دوكينز]], \'\'[[وهم الإله','cite_note-36','cite_ref-36','Hand-written book citation, no citation template.')
plain('<ref>Richard Dawkins, \'\'{{Ill-WD2','cite_note-37','cite_ref-37','Hand-written book citation; {{Ill-WD2}} is an interlanguage-link template, not a citation template. Its red link is to an article, not a template.')
tmpl('<ref>{{استشهاد بويب|مؤلف1-الأخير=Carroll','{{استشهاد بويب|مؤلف1-الأخير=Carroll','cite_note-38','cite_ref-38')
tmpl('<ref>{{استشهاد بويب|عنوان=Excerpts','{{استشهاد بويب|عنوان=Excerpts','cite_note-39','cite_ref-39')
tmpl('<ref>{{استشهاد بكتاب|مؤلف1-الأخير=Miller','{{استشهاد بكتاب|مؤلف1-الأخير=Miller','cite_note-40','cite_ref-40')
A.use(P('<ref name=edge /><ref>{{استشهاد بويب|مؤلف1-الأخير=Tolman'),dE,'cite_ref-edge_32-2')
tmpl('<ref>{{استشهاد بويب|مؤلف1-الأخير=Tolman','{{استشهاد بويب|مؤلف1-الأخير=Tolman','cite_note-41','cite_ref-41')
tmpl('<ref>{{استشهاد بكتاب|عنوان=Galileo','{{استشهاد بكتاب|عنوان=Galileo','cite_note-42','cite_ref-42')
A.use(P('<ref name="Russel, C.A. 2002 7" />'),dR,'cite_ref-Russel,_C.A._2002_7_6-1')
A.use(P('<ref name="Shapin1996" />'),dS,'cite_ref-Shapin1996_7-1')
A.use(P('<ref name="Brooke1991" />'),dB,'cite_ref-Brooke1991_8-1')
tmpl('<ref>{{استشهاد بكتاب|مؤلف=Ferngren, G.B.|محرر=Ferngren, G.B.|سنة=2002|عنوان=Science & Religion: A Historical Introduction|مسار=https://archive.org/details/sciencereligionh0000unse_p3x7|صفحة=x','{{استشهاد بكتاب|مؤلف=Ferngren','cite_note-43','cite_ref-43')
A.use(P('<ref name="scientists religion" />'),dX,'cite_ref-scientists_religion_44-0','self-closing use; definition appears much later in the article (after the window)')
tmpl('<ref>{{استشهاد\n | الأخير = Harrison','{{استشهاد\n | الأخير = Harrison','cite_note-45','cite_ref-45','Template name is the bare word استشهاد with a newline before the first parameter.')
tmpl('<ref>{{استشهاد بكتاب|مؤلف=Ferngren, G.B.|محرر=Ferngren, G.B.|سنة=2002|عنوان=Science & Religion: A Historical Introduction|مسار=https://archive.org/details/sciencereligionh0000unse_p3x7|صفحات=ix, x','{{استشهاد بكتاب|مؤلف=Ferngren','cite_note-46','cite_ref-46','Same book as the earlier unnamed ref (page=x) but a different body (pages=ix, x, different quotation), unnamed, so a separate reference.')
plain("<ref>Quotation from Ferngren's introduction",'cite_note-47','cite_ref-47','Hand-written; {{ردمك}} is an ISBN wrapper, not a citation template.')
plain('<ref>Quotation from Colin A. Russell','cite_note-48','cite_ref-48','Hand-written; {{ردمك}} is an ISBN wrapper, not a citation template.')
plain('<ref>Gary Ferngren (editor)','cite_note-49','cite_ref-49','Hand-written; {{ردمك}} is an ISBN wrapper, not a citation template.')
dG=tmpl('<ref name="glory rich jones">','{{استشهاد بكتاب|الأخير=Jones','cite_note-glory_rich_jones-50','cite_ref-glory_rich_jones_50-0')
d=[x for x in A.defs if x['at']==dG][0]; d['name']='glory rich jones'
# in-window use order fix: sort uses by position
A.uses.sort(key=lambda u:u['at']['cp']); 
for i,u in enumerate(A.uses,1): u['id']=f'u{i}'
A.write(0,'python3 stdlib listing, lxml sup/li listing, own quote-checking builder tools/lib.py','No DOI/PMID occurrences exist in the window. Out-of-window definitions listed only as binding targets.','2026-11-03T01:56:13Z')
