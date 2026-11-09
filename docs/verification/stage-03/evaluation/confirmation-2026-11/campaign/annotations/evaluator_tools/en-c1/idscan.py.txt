import sys,re
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import Art
a=Art(sys.argv[1]); lo=a.w0-int(sys.argv[2]) if len(sys.argv)>2 else a.w0; hi=a.w1
for m in re.finditer(r'(?i)pubmed|nlm\.nih|doi|\b10\.\d{3,}|pmid|/doi/',a.text):
    if lo<=m.start()<hi: print(m.start(),repr(a.text[max(0,m.start()-25):m.start()+60].replace('\n','\\n')))
