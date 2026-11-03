import sys,json
from lxml import html
d=sys.argv[1]
doc=html.parse(f'packets/{d}/render.html').getroot()
for s in doc.iter('sup'):
    if 'mw:Extension/ref' in (s.get('typeof') or ''):
        dm=s.get('data-mw') or ''
        print('SUP',s.get('id'),dm[:110].replace('\n',' '))
for li in doc.iter('li'):
    i=li.get('id') or ''
    if i.startswith('cite_note'):
        print('LI',i,' '.join(li.text_content().split())[:150], [a.get('title') for a in li.iter('a') if 'new' in (a.get('class') or '')])
