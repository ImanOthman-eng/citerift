import sys,re
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import Art
a=Art(sys.argv[1]); lo=int(sys.argv[2]) if len(sys.argv)>2 else a.w0; hi=int(sys.argv[3]) if len(sys.argv)>3 else a.w1
pat=re.compile(r'<ref\b[^>]*>|</ref>|\{\{\s*(?:[Cc]ite|[Cc]itation|[Ss]fn|[Ss]fnp|[Hh]arv|[Ee]fn|[Rr]efn|[Rr]\||[Rr]eflist|[Ss]hort|[Ee]xpression|[Rr]etract|[Dd]oi|[Pp]mid|PMID|[Cc]n|[Pp]b)[^|}]*|10\.\d{4,9}/|[Pp][Mm][Ii][Dd]|\bdoi\b|<!--|<nowiki|^[*#:;]',re.M)
for m in pat.finditer(a.text,lo,hi):
    if m.group() in ('*','#',':',';') and False: continue
    s=m.start(); print(s,repr(a.text[s:s+70].replace('\n','\\n')))
