import sys,re,lxml.html
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
key=sys.argv[1]
d=lxml.html.parse(f'{BASE}/packets/{key}/render.html').getroot()
for st in list(d.iter('style')): st.getparent().remove(st)
for li in d.iter('li'):
    i=li.get('id') or ''
    if i.startswith('cite_note'):
        t=' '.join(li.text_content().split())
        for m in re.finditer(r'(?i)retract|concern|withdraw|erratum|corrigend|correction|مسحوب|سحب',t):
            print(i,'|',t[max(0,m.start()-60):m.start()+100]); 
        if li.xpath('.//a[contains(@class,"new")]'): print(i,'REDLINK',[ (a.get('title')) for a in li.xpath('.//a[contains(@class,"new")]')])
a=Art(key)
for m in re.finditer(r'(?i)retract|expression of concern|withdraw|erratum|corrigend|correction',a.text):
    if a.w0<=m.start()<a.w1: print('SRC',m.start(),repr(a.text[max(0,m.start()-40):m.start()+60]))
