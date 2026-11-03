import sys,re; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2/tools')
from lib import *
from lxml import html
A=Art('en-1378959744'); t=A.t
doc=html.parse(f'{BASE}/packets/{A.d}/render.html').getroot()
lis=[l.get('id') for l in doc.iter('li') if (l.get('id') or '').startswith('cite_note-')]
names=['SIMBAD','GaiaEDR3','Houk_Smith-Moore_1978','HIPCurve','Nature1950','Gontcharov2006','Samus_et_al_2017','Shulyak_et_al_2014','Royer_et_al_2002','Borisov2023','Rusomarov_et_al_2016','Anderson_Francis_2012','Eggleton_Tokovinin_2008','Morgan1931','Deutsch1947','Babcock1947','Hockey1969','Stibbs1950','Renson_Manfroid_2009','ozuyar2018']
pos={}
for n in names:
    m=re.search(r'<ref name="?'+re.escape(n)+r'"?>',t[6876:]); pos[n]=6876+m.start()
for n in names:
    c=pos[n]; nid=[i for i in lis if re.fullmatch(r'cite_note-'+re.escape(n)+r'-\d+',i)]; assert len(nid)==1,(n,nid)
    A.adddef(c,'list_defined_note',n,'',[t.index('{{',c)],False,nid[0],'none',None,'Defined in <references> after the body; Starbox infobox uses and body uses bind here.' if not A.inw(c) else '')
uses=[(721,'Renson_Manfroid_2009','Renson_Manfroid_2009_4-0'),(765,'Houk_Smith-Moore_1978','Houk_Smith-Moore_1978_5-0'),(832,'Anderson_Francis_2012','Anderson_Francis_2012_6-0'),
(938,'Samus_et_al_2017','Samus_et_al_2017_2-1'),(1021,'Gontcharov2006','Gontcharov2006_7-0'),(1115,'GaiaEDR3',None),(1207,'GaiaEDR3','GaiaEDR3_1-4'),(1249,'Anderson_Francis_2012','Anderson_Francis_2012_6-1'),(1319,'Hockey1969','Hockey1969_8-0'),
(1994,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-0'),(2048,'Shulyak_et_al_2014','Shulyak_et_al_2014_10-0'),(2109,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-1'),
(2175,'Borisov2023','Borisov2023_11-1'),(2233,'Borisov2023','Borisov2023_11-0'),(2291,'Borisov2023','Borisov2023_11-2'),(2342,'Royer_et_al_2002','Royer_et_al_2002_12-0'),
(2429,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-2'),(2482,'Borisov2023','Borisov2023_11-3'),(2680,'SIMBAD','SIMBAD_13-0'),(2797,'Eggleton_Tokovinin_2008','Eggleton_Tokovinin_2008_14-0'),
(3195,'Samus_et_al_2017','Samus_et_al_2017_2-2'),(3363,'GaiaEDR3','GaiaEDR3_1-5'),(3463,'Gontcharov2006','Gontcharov2006_7-1'),(4293,'Morgan1931','Morgan1931_15-0'),(4411,'Deutsch1947','Deutsch1947_16-0'),
(4940,'Babcock1947','Babcock1947_17-0'),(5060,'Hockey1969','Hockey1969_8-1'),(5207,'Stibbs1950','Stibbs1950_18-0'),(5308,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-3'),(5450,'HIPCurve','HIPCurve_19-0'),
(5653,'Hockey1969','Hockey1969_8-2'),(5750,'Renson_Manfroid_2009','Renson_Manfroid_2009_4-1'),(6015,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-4'),(6047,'Shulyak_et_al_2014','Shulyak_et_al_2014_10-1'),
(6184,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-5'),(6341,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-6'),(6488,'Nature1950','Nature1950_20-0'),(6662,'Samus_et_al_2017','Samus_et_al_2017_2-3'),(6812,'Rusomarov_et_al_2016','Rusomarov_et_al_2016_9-7')]
# verify all self-closing refs in window are covered
found=[m.start() for m in re.finditer(r'<ref [^>]*/>',t) if A.inw(m.start())]
assert found==[u[0] for u in uses],(set(found)^set(u[0] for u in uses))
for cp,n,r in uses:
    assert re.match(r'<ref name="?'+re.escape(n)+r'"?/>',t[cp:]),(cp,n)
    note=''
    if cp==1115: note='pm_footnote in the Starbox astrometry template; Parsoid renders it as two markers (cite_ref-GaiaEDR3_1-2 and _1-3, proper motion RA and Dec), equally plausible, so null.'
    if cp in (2175,2233,2291,2429,2342): note='Starbox infobox renders its rows in a different order than the source; marker aligned by the row label in the rendered infobox.'
    A.adduse(cp,pos[n],('cite_ref-'+r) if r else None,note)
for n in names:
    if A.inw(pos[n]): A.adduse(pos[n],pos[n],None,'list-defined <ref> inside <references>; no marker of its own')
for key in ('10.1038/165195a0','10.1134/S1063773706110065','10.1134/S1063772917010085'):
    cp=t.index(key,6876); assert A.inw(cp)
    A.addid(cp,key,'doi','primary_citation_field',key.lower())
# any other doi/pmid in window?
print([m.start() for m in re.finditer(r'10\.\d{4}|pmid',t,re.I) if A.inw(m.start())])
A.write('2026-11-03T01:56:00Z',files(A),'python3 stdlib (str.find, re) and lxml listing of sup/li ids and rendered infobox rows; helper scripts in tools/','Which of two rendered markers belongs to the pm_footnote use at 1115.',
 ['Window contains the Starbox infobox: all refs there are self-closing reuses of list-defined refs.','The bibliography-like list items after the window are outside the window and were not labelled.'])
