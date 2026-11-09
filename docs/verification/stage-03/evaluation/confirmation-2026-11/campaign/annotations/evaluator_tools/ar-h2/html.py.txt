import sys,json
from lxml import html
d=sys.argv[1]
r=html.parse(f'../packets/{d}/render.html').getroot()
for s in r.iter('sup'):
    if 'mw:Extension/ref' in (s.get('typeof') or ''):
        dm=json.loads(s.get('data-mw') or '{}')
        body=(dm.get('body',{}) or {}).get('html') or (dm.get('body',{}) or {}).get('id','')
        a=dm.get('attrs',{})
        print('SUP',s.get('id'),a,repr(body[:90]))
for l in r.iter('li'):
    i=l.get('id') or ''
    if i.startswith('cite_note'):
        print('LI',i,repr(l.text_content().strip()[:140]))
