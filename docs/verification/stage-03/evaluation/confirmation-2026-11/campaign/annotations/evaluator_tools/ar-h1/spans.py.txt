import re,sys
t=open(sys.argv[1]+'/source.wikitext',encoding='utf8').read()
for m in re.finditer(r'<ref\b[^>]*?(/>|>)',t):
    if m.group(1)=='/>': print(m.start(),'SELF',m.group()); continue
    e=t.find('</ref>',m.end())
    print(m.start(),e+6,'|',t[m.start():e+6].replace('\n','⏎'))
