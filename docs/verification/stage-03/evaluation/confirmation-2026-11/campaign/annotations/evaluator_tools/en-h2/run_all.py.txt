import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h2/tools')
from build import *
import json

# ---------- plant
A=Art('en-1328575831')
specs=[
 ('<ref>{{cite iucn','{{cite iucn',False,'cite_note-1','cite_ref-1','Ref sits inside the |status_ref= parameter of {{Speciesbox}}; it is in the article source, so it is labelled.'),
 ('<ref>{{Cite book| url=','{{Cite book',False,'cite_note-2','cite_ref-2',''),
]
def plain(A,key,a,tpl,uns,nid,rid,name=None,notes=''):
    A.define(key,a,'note',name,'',tpl,uns,nid,notes)
    A.use(a,key,rid)
plain(A,'p1','<ref>{{cite iucn',['{{cite iucn'],False,'cite_note-1','cite_ref-1',notes='Reference sits inside the |status_ref= parameter of {{Speciesbox}}; it is present in the article source, so it is labelled.')
plain(A,'p2','<ref>{{Cite book| url=',['{{Cite book'],False,'cite_note-2','cite_ref-2')
plain(A,'p3','<ref name=POWO>',['{{cite web'],False,'cite_note-POWO-3','cite_ref-POWO_3-0',name='POWO')
plain(A,'p4','<ref name=COL>',['{{cite web'],False,'cite_note-COL-4','cite_ref-COL_4-0',name='COL')
plain(A,'p5','<ref>Makino, Tomit',[],True,'cite_note-5','cite_ref-5')
plain(A,'p6','<ref>{{Cite web|url=http://www.efloras',['{{Cite web'],False,'cite_note-6','cite_ref-6')
plain(A,'p7','<ref>Ohwi, J.',[],True,'cite_note-7','cite_ref-7')
plain(A,'p8','<ref>Czerepanov',[],True,'cite_note-8','cite_ref-8')
plain(A,'p9','<ref>Kharkevich',[],True,'cite_note-9','cite_ref-9')
plain(A,'p10','<ref>Lee, W.T.',[],True,'cite_note-10','cite_ref-10')
plain(A,'p11','<ref>Kuo, J.',[],True,'cite_note-11','cite_ref-11')
A.ident('10.2305/IUCN.UK.2010-3.RLTS.T173341A6994909.en','doi','primary_citation_field','10.2305/iucn.uk.2010-3.rlts.t173341a6994909.en','doi= value of {{cite iucn}}')
A.write()

# ---------- snake
S=Art('en-1355030157')
S.define('iucn','<ref name=iucn>','note','iucn','',[],True,'cite_note-iucn-1','Inside |status_ref= of {{Speciesbox}} (present in source). Plain-text IUCN Red List citation with a dx.doi.org URL, no citation template. Reused 3 more times by <ref name=iucn/>.')
S.define('RDB','<ref name=RDB>{{NRDB','note','RDB','',['{{NRDB species'],False,'cite_note-RDB-2','First occurrence with a body. The earlier <ref name=RDB/> in |synonyms_ref= is self-closing. {{NRDB species}} (Reptile Database link) is counted as a citation template because its purpose is to format a citation; a reader applying a narrower list could exclude it.')
S.define('Blgr','<ref name=Blgr1903>','note','Blgr1903','',[],True,'cite_note-Blgr1903-4','Hand-written citation, no citation template.')
S.define('EDR','<ref name=EDR>','note','EDR','',[],True,'cite_note-EDR-5','Hand-written citation; {{ISBN}} is an identifier wrapper, not a citation template.')
S.define('Port','<ref name="Portillo et al. 2019">{{cite journal','list_defined_note','Portillo et al. 2019','',['{{cite journal'],False,'cite_note-Portillo_et_al._2019-3','Defined in {{Reflist|refs=}} after all its uses (two self-closing calls earlier in the text).')
S.define('Sp','*[[species:Stephen Spawls','bibliography_entry',None,'',[],True,None,'Further reading list item. It has neither a citation template nor a DOI/PMID (only {{ISBN}}), so under the literal wording of 3.4 it may fall outside; labelled as a hand-written bibliography entry because it is plainly a citation outside footnotes.')
S.define('Til','*[[species:Colin R. Tilbury|Tilbury, Colin]]','bibliography_entry',None,'',[],True,None,'Further reading list item, hand-written, no citation template or identifier; same caveat as the previous bibliography entry.')
S.use('<ref name=iucn>','iucn','cite_ref-iucn_1-0')
S.use('<ref name=RDB/>','RDB','cite_ref-RDB_2-0','Self-closing call in |synonyms_ref= of {{Speciesbox}}, before the defining occurrence.',n=0)
S.use('<ref name=RDB>{{NRDB','RDB','cite_ref-RDB_2-1')
S.use('<ref name="Portillo et al. 2019"/>','Port','cite_ref-Portillo_et_al._2019_3-0',n=0)
S.use('<ref name=Blgr1903>','Blgr','cite_ref-Blgr1903_4-0')
S.use('<ref name=EDR>','EDR','cite_ref-EDR_5-0')
S.use('<ref name=EDR/>','EDR','cite_ref-EDR_5-1')
S.use('<ref name="Portillo et al. 2019"/>','Port','cite_ref-Portillo_et_al._2019_3-1',n=1)
S.use('<ref name=iucn/>','iucn','cite_ref-iucn_1-1',n=0)
S.use('<ref name=Blgr1903/>','Blgr','cite_ref-Blgr1903_4-1')
S.use('<ref name=iucn/>','iucn','cite_ref-iucn_1-2',n=1)
S.use('<ref name=RDB/>','RDB','cite_ref-RDB_2-2',n=1)
S.ident('https://dx.doi.org/10.2305/IUCN.UK.2021-2.RLTS.T13264526A13264534.en','doi','identifier_link','10.2305/iucn.uk.2021-2.rlts.t13264526a13264534.en','Resolver URL in a plain-text reference; the sentence-final period after ".en" is not part of the URL or the DOI.')
S.ident('10.1643/CH-18-098','doi','primary_citation_field','10.1643/ch-18-098','doi= value in the list-defined Portillo et al. 2019 reference.')
S.write()

# ---------- mine
M=Art('en-1368235550')
M.define('an','<ref name=anuario2024>','note','anuario2024','',['{{Cite report'],False,'cite_note-anuario2024-1','Inside |amount= of {{Infobox Mine}} (present in source).')
M.define('ia','<ref name="Iacobeni">','note','Iacobeni','',['{{cite web'],False,'cite_note-Iacobeni-2','')
M.define('jom','<ref>{{Cite journal |title=Processing','note',None,'',['{{Cite journal'],False,'cite_note-3','')
M.define('cip','<ref name=ciperbronce>','note','ciperbronce','',['{{Cite news'],False,'cite_note-ciperbronce-4','')
M.define('df','<ref>{{Cite news |title=Disputada','note',None,'',['{{Cite news'],False,'cite_note-5','')
M.define('son','<ref name=Sonia2015>','note','Sonia2015','',['{{Cite book'],False,'cite_note-Sonia2015-6','')
M.define('bn','<ref name=bnamericas>','note','bnamericas','',['{{Cite web'],False,'cite_note-bnamericas-7','')
M.define('bre','<ref>{{Cite journal |title=Miner','note',None,'',['{{Cite journal'],False,'cite_note-8','')
M.define('piq','<ref name=Piqueretal1019>','note','Piqueretal1019','',['{{cite journal'],False,'cite_note-Piqueretal1019-9','')
for k,a,r in [('an','<ref name=anuario2024>','cite_ref-anuario2024_1-0'),('ia','<ref name="Iacobeni">','cite_ref-Iacobeni_2-0'),('jom','<ref>{{Cite journal |title=Processing','cite_ref-3'),('cip','<ref name=ciperbronce>','cite_ref-ciperbronce_4-0')]:
    M.use(a,k,r)
M.use('<ref name=ciperbronce/>','cip','cite_ref-ciperbronce_4-1')
M.use('<ref>{{Cite news |title=Disputada','df','cite_ref-5')
M.use('<ref name=Sonia2015>','son','cite_ref-Sonia2015_6-0')
M.use('<ref name=Sonia2015/>','son','cite_ref-Sonia2015_6-1')
M.use('<ref name=bnamericas>','bn','cite_ref-bnamericas_7-0')
M.use('<ref>{{Cite journal |title=Miner','bre','cite_ref-8')
M.use('<ref name=Piqueretal1019>','piq','cite_ref-Piqueretal1019_9-0')
M.ident('10.1007/s11837-020-04255-9','doi','primary_citation_field','10.1007/s11837-020-04255-9','doi= value of the JOM citation.',start=M.t.index('doi=10.1007')-1,off=0) if False else None
i=M.t.index('|doi=10.1007/s11837')
M.ident('10.1007/s11837-020-04255-9','doi','primary_citation_field','10.1007/s11837-020-04255-9','doi= value of the JOM citation.',start=i)
M.ident('10.1007/s11837-020-04255-9','doi','identifier_link','10.1007/s11837-020-04255-9','DOI embedded in the publisher URL (link.springer.com/content/pdf/10.1007/...pdf) in |url=. The path has no "/doi/" segment, so it is not one of the URL forms the guide lists; labelled as "anything else: the identifier text" (quote starts at "10.1007"), ".pdf" is not part of the DOI. May be out of scope under a strict reading.',start=M.t.index('link.springer.com/content/pdf/'))
M.ident('10.5027/andgeoV46n2-3108','doi','primary_citation_field','10.5027/andgeov46n2-3108','doi= value; |doi-access=free present.')
M.write()

# ---------- electro
E=Art('en-1371897367')
espec=[('<ref>K. J. Gabriel',[],True),('<ref>Cleopatra',[],True),('<ref>Moghimi, M. J. Chattergoon',[],True),
 ('<ref>{{cite journal|last1=Bifano',['{{cite journal'],False),
 ('<ref>{{cite journal|last1=Moghimi|first1=Mohammad J.|last2',['{{cite journal'],False),
 ('<ref>{{cite journal|last1=Moghimi|first1=Mohammad J|title=MOEMS',['{{cite journal'],False),
 ('<ref>{{cite web|url=http://www.imagine',['{{cite web'],False),
 ('<ref>{{cite web|url=http://www.bridger',['{{cite web'],False),
 ('<ref>Moghimi, M. J. Wilson, C. Dickensheets',[],True),
 ('<ref>Moghimi, M. J. Wilson, C. R.',[],True),
 ('<ref>{{cite book|last1=Bansal',['{{cite book'],False)]
for n,(a,tp,u) in enumerate(espec,1):
    notes=''
    if n==5: notes='This <ref> starts on a new line directly after the previous </ref>; still a normal unnamed reference.'
    E.define(f'e{n}',a,'note',None,'',tp,u,f'cite_note-{n}',notes)
    E.use(a,f'e{n}',f'cite_ref-{n}')
E.ident('10.1038/nphoton.2010.297','doi','primary_citation_field','10.1038/nphoton.2010.297')
E.ident('10.1109/JMEMS.2013.2251320','doi','primary_citation_field','10.1109/jmems.2013.2251320')
E.ident('10.1117/1.3574129','doi','primary_citation_field','10.1117/1.3574129','|doi-access=free present.')
E.write()

# ---------- semantic web
W=Art('en-1382621840')
W.define('BL','<ref name="Berners-Lee">{{cite magazine','list_defined_note','Berners-Lee','',['{{cite magazine'],False,'cite_note-Berners-Lee-7','Starts after the window (in {{Reflist|refs=}}); listed only as the binding target of the self-closing use in the window. Also used again at cp 12543 (outside the window).')
sp=[('<ref>{{cite news|url=https://www.bloomberg',['{{cite news'],'cite_note-6','cite_ref-6'),
 ('<ref>{{cite magazine |access-date=February 24, 2010',['{{cite magazine'],'cite_note-8','cite_ref-8'),
 ('<ref>{{cite web |last=Berners-Lee |first=Tim |title=Plenary',['{{cite web'],'cite_note-9','cite_ref-9'),
 ('<ref>{{cite web |last=Berners-Lee |first=Tim |title=Semantic Web Road map',['{{cite web'],'cite_note-10','cite_ref-10'),
 ('<ref>{{cite journal |last1=Sheth',['{{cite journal'],'cite_note-11','cite_ref-11'),
 ('<ref>{{cite book |last=Berners-Lee |first=Tim |author-link',['{{cite book'],'cite_note-12','cite_ref-12'),
 ('<ref>{{cite magazine |access-date=March 13, 2008',['{{cite magazine'],'cite_note-13','cite_ref-13'),
 ('<ref>{{cite web\n | url=http://eprints.ecs',['{{cite web'],'cite_note-14','cite_ref-14'),
 ('<ref>{{cite web\n | url=http://iswc2013',['{{cite web'],'cite_note-15','cite_ref-15')]
for n,(a,tp,ni,ri) in enumerate(sp):
    W.define(f'w{n}',a,'note',None,'',tp,False,ni,'',start=2569)
    W.use(a,f'w{n}',ri,start=2569)
    if n==0:
        W.use('<ref name="Berners-Lee"/>','BL','cite_ref-Berners-Lee_7-0','Self-closing; the body is in the later {{Reflist|refs=}} block.',start=2569)
W.unres.append('Window contains no DOI or PMID occurrence (checked for "10.", doi, pmid, pubmed); the s2cid/jstor fields in the 2001 Scientific American citation are not in scope. The <syntaxhighlight> blocks in the window hold no reference or identifier.')
W.write()
