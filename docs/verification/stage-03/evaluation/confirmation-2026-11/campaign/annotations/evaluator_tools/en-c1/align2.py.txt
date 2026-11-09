import sys,re,json,lxml.html
sys.path.insert(0,'/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1/tools')
from lib import *
key=sys.argv[1]; lo=int(sys.argv[2]); hi=int(sys.argv[3]); a=Art(key)
d=lxml.html.parse(f'{BASE}/packets/{key}/render.html').getroot()
for st in list(d.iter('style')): st.getparent().remove(st)
sups=[e for e in d.iter('sup') if 'mw:Extension/ref' in (e.get('typeof') or '')]
dn=[json.loads(s.get('data-mw'))['attrs'].get('name') for s in sups]
srcrefs=list(re.finditer(r'<ref\b[^>]*>',a.text))
sn=[]
for m in srcrefs:
    nm=re.search(r'name\s*=\s*"?([^"/>]*?)"?\s*/?>',m.group()); sn.append(nm.group(1).strip() if nm else None)
# align: dynamic - allow skipping sups
j=0; pairs={}
for i,n in enumerate(dn):
    if j<len(sn) and sn[j]==n: pairs[j]=i; j+=1
for j,m in enumerate(srcrefs):
    if lo<=m.start()<hi:
        i=pairs.get(j)
        sp=sups[i] if i is not None else None
        txt=''
        if sp is not None:
            body=json.loads(sp.get('data-mw')).get('body',{}).get('id')
            if body:
                li=d.xpath(f'//*[@id="{body}"]')
                if li: txt=' '.join(li[0].text_content().split())[:70]
        print(m.start(),i,sp.get('id') if sp is not None else None,'|',a.text[m.start():m.start()+45].replace('\n',' '),'|',txt)
