import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h1/tools')
from lib import *
TOOLS='Python 3 stdlib (str.find, re) and lxml to list sup/li elements; helper scripts in tools/'
a=A('ar-76868647'); t=a.t
def ref(pos,rid,mt,tpl=True,inwin=True,**kw):
    d=a.at(pos,'<ref')
    assert d['cp']-pos<3
    tp=[a.at(d['cp'],'{{استشهاد')] if tpl else []
    a.define(d,'note',templates=tp,rid=rid,mtext=mt,inwin=inwin,unstructured=not tpl,**kw); return d
# pre-window definitions (binding targets only)
CP=ref(185,'cite_note-CP_History-2','The Canadian Press, About Us (archived)',name='CP History',inwin=False)
MJ=ref(741,'cite_note-Major-3','Flavelle, Dana (26 نوفمبر 2010). "Major publishers invest in Canada\'s oldest news agency"',name='Major',inwin=False)
RE=ref(6108,'cite_note-Retirement-1971-10','"Charles Edwards of Broadcast News retires". The Brandon Sun.',name='Retirement-1971',inwin=False)
PO=ref(6633,'cite_note-Potts-1996-11','Potts، J. Lyman (فبراير 1996). "Charles B. Edwards (1906–1983)".',name='Potts-1996',inwin=False)
TH=ref(7862,'cite_note-the-CP-history-13','"Our Team & Editorial Values". The Canadian Press.',name='the-CP-history',inwin=False)
# in-window definitions
ST=ref(8403,'cite_note-Stylebook-14','McCarten, James (editor).',tpl=False,name='Stylebook',notes='Hand-written plain-text reference, no citation template.')
a.use(ST,ST,'cite_ref-Stylebook_14-0')
d=ref(8608,'cite_note-15','"News Service to Serve Radio, TV". The Sun Times. Owen Sound, Ontario.'); a.use(d,d,'cite_ref-15')
def su(after,q,bind,rid,notes=''): a.use(a.at(after,q),bind,rid,notes)
su(9070,'<ref name="Potts-1996" />',PO,'cite_ref-Potts-1996_11-2','reuse; definition starts before the window')
su(9259,'<ref name="Retirement-1971" />',RE,'cite_ref-Retirement-1971_10-3','reuse; definition starts before the window')
su(9456,'<ref name="Retirement-1971" />',RE,'cite_ref-Retirement-1971_10-4','reuse; definition starts before the window')
su(9548,'<ref name="Stylebook" />',ST,'cite_ref-Stylebook_14-1')
d=ref(9749,'cite_note-16','"United Press Canada absorbed by Canadian Press". United Press International.'); a.use(d,d,'cite_ref-16')
su(10287,'<ref name="the-CP-history" />',TH,'cite_ref-the-CP-history_13-1','reuse; definition starts before the window')
su(10509,'<ref name="CP History" />',CP,'cite_ref-CP_History_2-3','reuse; definition starts before the window')
C1=ref(10578,'cite_note-:1-17','Ford، Arthur R. (1942). "The Canadian Press". Canadian Historical Review. DOI:10.3138/chr-023-03-01.',name=':1'); a.use(C1,C1,'cite_ref-:1_17-0')
su(10927,'<ref name=":1" />',C1,'cite_ref-:1_17-1')
su(11177,'<ref name="Major" />',MJ,'cite_ref-Major_3-1','reuse; definition starts before the window')
d=ref(11335,'cite_note-18','"Media Classified acquires City Parent magazine from Metroland Media". Toronto Star.'); a.use(d,d,'cite_ref-18')
C0=ref(12108,'cite_note-:0-19','Miville، Serge (31 ديسمبر 1969). "Gene Allen, Making National News..." Left History',name=':0'); a.use(C0,C0,'cite_ref-:0_19-0')
su(12971,'<ref name=":0" />',C0,'cite_ref-:0_19-1')
d=ref(13048,'cite_note-20','Miville, Serge (2014). "Gene Allen, Making National News..." Left History',notes='Unnamed ref citing the same article as :0 (same DOI) with different body and extra fields; a separate reference since unnamed.'); a.use(d,d,'cite_ref-20')
d=ref(14514,'cite_note-21','Coyle, Jim (25 Sep 2007). "A brand like no other accepts the price of fame". Toronto Star'); a.use(d,d,'cite_ref-21')
d=ref(15278,'cite_note-22','Blackwell، Richard (11 مارس 2019). "Sun Media to pull out of Canadian Press". The Globe and Mail.',notes='Template repeats مسار أرشيف and تاريخ أرشيف twice; not relevant to the labels.'); a.use(d,d,'cite_ref-22')
def idn(after,q,scheme,role,key,notes=''): a.ident(a.at(after,q,80),scheme,role,key,notes)
idn(10578,'http://dx.doi.org/10.3138/chr-023-03-01','doi','identifier_link','10.3138/chr-023-03-01','dx.doi.org URL in مسار= field')
idn(10700,'10.3138/chr-023-03-01','doi','primary_citation_field','10.3138/chr-023-03-01','دوي= field')
idn(12108,'10.25071/1913-9632.39319','doi','primary_citation_field','10.25071/1913-9632.39319','دوي= field (ref :0)')
idn(13048,'10.25071/1913-9632.39319','doi','primary_citation_field','10.25071/1913-9632.39319','دوي= field (unnamed ref at 13048)')
a.write(TOOLS,['Definitions starting before the window (185, 741, 6108, 6633, 7862) are listed with in_window=false only as binding targets for window uses.','ISBN and S2CID values are out of scope (not DOI/PMID).'],'nothing undecided')
