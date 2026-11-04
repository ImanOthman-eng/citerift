import sys,re,json,lxml.html
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
key=sys.argv[1]; a=Art(key)
d=lxml.html.parse(f'{BASE}/packets/{key}/render.html').getroot()
sups=[e for e in d.iter('sup') if 'mw:Extension/ref' in (e.get('typeof') or '')]
refs=[m.start() for m in re.finditer(r'<ref\b',a.text)]
# exclude refs in comments? just report counts
print('sups',len(sups),'src <ref',len(refs))
if len(sys.argv)>2:
    lo,hi=int(sys.argv[2]),int(sys.argv[3])
    if len(sups)==len(refs):
        for i,(cp,s) in enumerate(zip(refs,sups)):
            if lo<=cp<hi: print(cp,s.get('id'),a.text[cp:cp+50].replace('\n',' '))
