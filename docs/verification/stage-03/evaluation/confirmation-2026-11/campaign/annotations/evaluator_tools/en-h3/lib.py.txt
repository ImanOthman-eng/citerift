import json,re,hashlib
from lxml import html
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h3'
class Art:
    def __init__(s,d):
        s.d=d
        s.pk=json.load(open(f'{BASE}/packets/{d}/packet.json'))
        s.t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
        assert len(s.t)==s.pk['source_code_points']
        s.w=(s.pk['window']['cp_start'],s.pk['window']['cp_end'])
        try:
            s.doc=html.parse(f'{BASE}/packets/{d}/render.html').getroot()
        except Exception: s.doc=None
        s.sups=[]; s.lis={}
        if s.doc is not None:
            for e in s.doc.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
                dm=json.loads(e.get('data-mw') or '{}')
                s.sups.append(dict(id=e.get('id'),name=dm.get('attrs',{}).get('name'),group=dm.get('attrs',{}).get('group'),body=(dm.get('body') or {}).get('id'),text=e.text_content()))
            for l in s.doc.xpath('//li[starts-with(@id,"cite_note")]'):
                for st in l.xpath('.//style'): st.drop_tree()
                s.lis[l.get('id')]=' '.join(l.text_content().split())
    def find(s,needle,n=0,start=0):
        i=start-1
        for _ in range(n+1):
            i=s.t.index(needle,i+1)
        return i
    def finds(s,needle):
        return [m.start() for m in re.finditer(re.escape(needle),s.t)]
    def loc(s,cp,n=40):
        q=s.t[cp:cp+n]
        if '\n' in q[8:]: q=q[:8+q[8:].index('\n')]
        assert s.t[cp:cp+len(q)]==q
        return {'cp':cp,'quote':q}
    def li_for(s,sup):
        if sup is None or not sup['body']: return None
        i='cite_note-'+sup['body'].split('cite_note-',1)[1]
        return i if i in s.lis else None
    def build(s,defs,uses,idents,unresolved,tools,started,unresolved_prov='',finished=None):
        # defs: list of dict(cp,kind,name,group,templates[cp],unstructured,marker,marker_text,notes,sup(index into s.sups or None), render_note_id optional)
        # uses: list of dict(cp,bind(cp or 'missing'/'unclear'),sup(index or None),notes)
        defs=sorted(defs,key=lambda x:x['cp'])
        out_defs=[]
        for i,x in enumerate(defs,1):
            rid=x.get('render_note_id','auto')
            if rid=='auto':
                rid=s.li_for(s.sups[x['sup']]) if x.get('sup') is not None else None
            mt=x.get('marker_text')
            if mt is None and rid:
                mt=re.sub(r'^(↑\s*|(\d+\s+)+(?=\D))','',re.sub(r'\s*(\.mw-parser-output[^{]*\{[^}]*\}\s*)+','  ',s.lis[rid]).strip())
            out_defs.append({'id':f'd{i}','at':s.loc(x['cp']),'in_window':s.w[0]<=x['cp']<s.w[1],'kind':x['kind'],
              'name':x.get('name'),'group':x.get('group'),'templates':[{'at':s.loc(c)} for c in x.get('templates',[])],
              'unstructured':x['unstructured'],'render_note_id':rid,'marker':x.get('marker','none'),'marker_text':mt,'notes':x.get('notes','')})
        out_uses=[]
        for i,x in enumerate(sorted(uses,key=lambda x:x['cp']),1):
            b=x['bind']
            if isinstance(b,int): b=s.loc(b)
            rr=x.get('sup')
            rr=s.sups[rr]['id'] if rr is not None else None
            out_uses.append({'id':f'u{i}','at':s.loc(x['cp']),'binds_to':b,'render_ref_id':rr,'notes':x.get('notes','')})
        out_ids=[]
        for x in sorted(idents,key=lambda x:x['cp']):
            q=x['q']; assert s.t[x['cp']:x['cp']+len(q)]==q,(x['cp'],q)
            out_ids.append({'at':{'cp':x['cp'],'quote':q},'scheme':x['scheme'],'role':x['role'],'key':x['key'],'notes':x.get('notes','')})
        for o in out_defs+out_uses:
            if o['at']['cp']>=s.w[1] and 'in_window' not in o: pass
        sha=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()
        files=[{'path':f'packets/{s.d}/packet.json','sha256':sha(f'{BASE}/packets/{s.d}/packet.json')},
               {'path':f'packets/{s.d}/source.wikitext','sha256':s.pk['source_sha256']},
               {'path':f'packets/{s.d}/render.html','sha256':s.pk['html_sha256']},
               {'path':'ANNOTATION_GUIDE_v1.1.md','sha256':sha(f'{BASE}/ANNOTATION_GUIDE_v1.1.md')}]
        import datetime
        fin=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        res={'format':'citerift-stage03-annotation-v1',
         'article':{'wiki':'en','revision_id':s.pk['revision_id'],'source_sha256':s.pk['source_sha256'],'html_sha256':s.pk['html_sha256'],'window':list(s.w)},
         'provenance':{'agent':'cf11-eval-en-h3','started_at':started,'finished_at':fin,'files_opened':files,'tools':tools,'unresolved':unresolved_prov},
         'definitions':out_defs,'uses':out_uses,'identifiers':out_ids,'unresolved_notes':unresolved}
        p=f'{BASE}/out/en-{s.pk["revision_id"]}.json'
        json.dump(res,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        print(s.d,'defs',len(out_defs),'uses',len(out_uses),'ids',len(out_ids),'sups',len(s.sups))

def ref_tags(t):
    out=[]
    for m in re.finditer(r'<ref\b[^>]*>',t):
        tag=m.group(0)
        nm=re.search(r'\bname\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'/>]+))',tag)
        nm=(nm.group(1) or nm.group(2) or nm.group(3)) if nm else None
        gp=re.search(r'\bgroup\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'/>]+))',tag)
        gp=(gp.group(1) or gp.group(2) or gp.group(3)) if gp else ''
        out.append(dict(cp=m.start(),name=nm,group=gp,selfclose=tag.endswith('/>')))
    return out
def body_of(t,cp):
    e=t.index('</ref>',cp); s=t.index('>',cp)+1
    return t[s:e]
def sup_for(A,name,group,k):
    """k-th (0-based) source occurrence of named ref -> index into A.sups"""
    c=[i for i,s in enumerate(A.sups) if s['name']==name and (s['group'] or '')==group and s['id'].endswith('-%d'%k)]
    return c[0] if len(c)==1 else None
