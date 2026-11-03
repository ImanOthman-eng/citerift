import re,sys
d=sys.argv[1]
t=open(f'packets/{d}/source.wikitext',encoding='utf-8').read()
pat=re.compile(r'<ref\b|</ref>|\{\{\s*(?:cite|citation|sfn|sfnp|harv|efn|refn|r\||reflist|rp|notelist|doi|pmid|retracted|expression)|10\.\d{4}|PMID|pmid|doi|<!--|<nowiki|^[*#:;]',re.I|re.M)
for m in pat.finditer(t):
    print(m.start(),repr(t[m.start():m.start()+70]))
