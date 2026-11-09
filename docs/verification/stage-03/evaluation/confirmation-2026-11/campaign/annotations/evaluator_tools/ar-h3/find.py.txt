import sys,re,json
d=sys.argv[1]
t=open(f'packets/{d}/source.wikitext',encoding='utf-8').read()
p=json.load(open(f'packets/{d}/packet.json'))['window']
print(len(t),p)
pat=r'<ref\b[^>]*>|</ref>|\{\{\s*(?:sfn|sfnp|efn|refn|ملا|r|harv|استشهاد|cite|citation|Cite|doi|دوي|pmid|PMID|مصدر مسحوب|Retracted|[Rr]eflist|قائمة)[^|}]*|10\.\d{4,}|PMID|pmid|doi|دوي|<!--|<nowiki|^[*#:;].*$|\{\{\s*[Rr]eflist'
for m in re.finditer(pat,t,re.M):
    print(m.start(), repr(t[m.start():m.start()+70]))
