import sys,json
from lxml import html
d=sys.argv[1]
doc=html.parse(f'packets/{d}/render.html').getroot()
print("== SUPS")
for s in doc.iter('sup'):
    if 'mw:Extension/ref' in (s.get('typeof') or ''):
        dm=json.loads(s.get('data-mw') or '{}')
        a=dm.get('attrs',{})
        body=(dm.get('body') or {}).get('html') or (dm.get('body') or {}).get('id') or ''
        print(s.get('id'),'|',a.get('name'),a.get('group'),'|',s.text_content()[:15].strip(),'|',body[:50].replace('\n',' '))
print("== LIS")
for l in doc.iter('li'):
    if (l.get('id') or '').startswith('cite_note'):
        print(l.get('id'),'|',' '.join(l.text_content().split())[:110])
