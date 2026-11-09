import sys,re
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3/tools')
from lib import *
A=Art(sys.argv[1])
for k,v in A.lis.items():
    v=re.sub(r'\.mw-parser-output[^}]*\}','',v)
    if re.search(r'retract|withdraw|erratum|corrigend|correction|concern|retraction|مسحوب|سحب',v,re.I): print(k,v[:300])
if A.doc is not None:
    for e in A.doc.xpath('//li[starts-with(@id,"cite_note")]//a[@class="new"]'): print('RED',e.get('title'))
t=A.t
for m in re.finditer(r'retract|withdraw|erratum|corrigend|expression of concern',t,re.I): print('SRC',m.start(),t[max(0,m.start()-40):m.start()+40].replace('\n',' '))
