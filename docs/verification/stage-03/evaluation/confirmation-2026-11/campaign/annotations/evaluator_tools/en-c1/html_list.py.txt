import sys, lxml.html
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import BASE
key=sys.argv[1]; mode=sys.argv[2]
doc=lxml.html.parse(f'{BASE}/packets/{key}/render.html').getroot()
for st in list(doc.iter('style')): st.getparent().remove(st)
if mode=='sup':
    for i,e in enumerate(doc.iter('sup')):
        if 'mw:Extension/ref' in (e.get('typeof') or ''):
            print(i,e.get('id'),(e.get('data-mw') or '')[:int(sys.argv[3]) if len(sys.argv)>3 else 200])
elif mode=='li':
    for e in doc.iter('li'):
        if (e.get('id') or '').startswith('cite_note'):
            print(e.get('id'),'|',' '.join(e.text_content().split())[:int(sys.argv[3]) if len(sys.argv)>3 else 200])
