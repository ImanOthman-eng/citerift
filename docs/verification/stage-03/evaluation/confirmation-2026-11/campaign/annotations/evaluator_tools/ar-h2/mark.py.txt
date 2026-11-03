import sys,re
from lxml import html
d=sys.argv[1]
r=html.parse(f'../packets/{d}/render.html').getroot()
for l in r.iter('li'):
    i=l.get('id') or ''
    if i.startswith('cite_note'):
        t=l.text_content()
        hits=re.findall(r'retract|withdr|erratum|corrig|concern|سحب|مسحوب|تصحيح|تراجع|correct',t,re.I)
        news=[(a.get('title'),a.text_content()) for a in l.iter('a') if 'new' in (a.get('class') or '')]
        print(i,hits,news)
