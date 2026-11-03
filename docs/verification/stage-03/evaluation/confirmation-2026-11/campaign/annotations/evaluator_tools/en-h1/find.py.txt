import re,sys
aid=sys.argv[1]
t=open(f'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h1/packets/{aid}/source.wikitext',encoding='utf-8').read()
pat=sys.argv[2] if len(sys.argv)>2 else r'<ref|\{\{\s*(?:cite|citation|sfn|sfnp|harv|efn|refn|r\||reflist|notelist|rp|doi|pmid|retract|expression|cn\b)|10\.\d{4}|PMID|pubmed|doi|</ref|<!--|nowiki|\{\{\s*(?:\*|#)'
for m in re.finditer(pat,t,re.I):
    print(m.start(),repr(t[m.start():m.start()+70]))
