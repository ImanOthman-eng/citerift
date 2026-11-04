import sys,re
d=sys.argv[1]; t=open(f'packets/{d}/source.wikitext',encoding='utf-8').read()
import json; p=json.load(open(f'packets/{d}/packet.json'))['window']
a,b=p['cp_start'],p['cp_end']
pat=re.compile(r'<ref|\{\{\s*(?:cite|citation|sfn|sfnp|harv|efn|refn|r\||doi|pmid|reflist|notelist|retract|expression)|10\.\d{4}|PMID|pmid|doi|</ref>|/>',re.I)
print(len(t),a,b)
for m in pat.finditer(t):
    if a-300<=m.start()<b+300: print(m.start(), repr(t[m.start():m.start()+70]))
