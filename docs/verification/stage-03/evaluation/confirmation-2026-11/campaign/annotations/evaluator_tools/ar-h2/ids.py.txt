import sys,re
d=sys.argv[1]
t=open(f'../packets/{d}/source.wikitext',encoding='utf-8').read()
a=int(sys.argv[2]) if len(sys.argv)>2 else 0
b=int(sys.argv[3]) if len(sys.argv)>3 else len(t)
for m in re.finditer(r'10\.\d{3,}|doi|pmid|pubmed|ncbi|دوي|pmc|biorxiv|medrxiv|\bpm=|DOI',t,re.I):
    if a<=m.start()<b: print(m.start(),repr(t[max(0,m.start()-40):m.start()+80]))
