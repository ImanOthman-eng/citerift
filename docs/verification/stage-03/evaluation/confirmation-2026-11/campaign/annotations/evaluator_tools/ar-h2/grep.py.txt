import sys,re
d=sys.argv[1]
t=open(f'../packets/{d}/source.wikitext',encoding='utf-8').read()
pat=r'<ref|</ref|\{\{\s*(?:cite|citation|استشهاد|sfn|efn|refn|ملا|r\||harv|doi|دوي|pmid|Reflist|مراجع|Retract|مصدر)|10\.\d|PMID|pmid|doi|دوي|<!--|nowiki|\n[*#:;]|\{\{'
for m in re.finditer(pat,t,re.I):
    print(m.start(),repr(t[m.start():m.start()+70]))
