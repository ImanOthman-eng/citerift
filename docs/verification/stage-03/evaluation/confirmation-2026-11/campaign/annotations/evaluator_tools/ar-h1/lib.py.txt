import json,hashlib,os
B='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h1'
START='2026-11-03T09:00:00Z'
class A:
    def __init__(s,d):
        s.d=d; s.p=json.load(open(f'{B}/packets/{d}/packet.json'))
        s.t=open(f'{B}/packets/{d}/source.wikitext',encoding='utf8').read()
        s.defs=[];s.uses=[];s.ids=[]
    def at(s,after,q,n=60):
        """location of first occurrence of q at/after cp `after`"""
        cp=s.t.find(q,after); assert cp>=0,(q,after)
        return s.L(cp,len(q) if len(q)<=n else n)
    def L(s,cp,n=40):
        q=s.t[cp:cp+n]; assert s.t[cp:cp+len(q)]==q
        return {'cp':cp,'quote':q}
    def win(s): return s.p['window']['cp_start'],s.p['window']['cp_end']
    def define(s,loc,kind,name=None,group='',templates=(),unstructured=False,rid=None,marker='none',mtext=None,notes='',inwin=True):
        i='d%d'%(len(s.defs)+1)
        s.defs.append(dict(id=i,at=loc,in_window=inwin,kind=kind,name=name,group=group,templates=[{'at':x} for x in templates],unstructured=unstructured,render_note_id=rid,marker=marker,marker_text=mtext,notes=notes))
        return loc
    def use(s,loc,binds,rid=None,notes=''):
        s.uses.append(dict(id='u%d'%(len(s.uses)+1),at=loc,binds_to=binds,render_ref_id=rid,notes=notes))
    def ident(s,loc,scheme,role,key,notes=''):
        s.ids.append(dict(at=loc,scheme=scheme,role=role,key=key,notes=notes))
    def write(s,tools,unresolved=(),prov_unres=''):
        pj=f'{B}/packets/{s.d}/'
        files=[{'path':f'packets/{s.d}/{n}','sha256':hashlib.sha256(open(pj+n,'rb').read()).hexdigest()} for n in ('source.wikitext','render.html','packet.json')]
        files.append({'path':'ANNOTATION_GUIDE_v1.1.md','sha256':hashlib.sha256(open(B+'/ANNOTATION_GUIDE_v1.1.md','rb').read()).hexdigest()})
        assert files[0]['sha256']==s.p['source_sha256'] and files[1]['sha256']==s.p['html_sha256']
        w=s.win()
        for x in s.defs+s.uses+s.ids:
            c=x['at']; assert s.t[c['cp']:c['cp']+len(c['quote'])]==c['quote']
        for x in s.defs:
            for tp in x['templates']: c=tp['at']; assert s.t[c['cp']:c['cp']+len(c['quote'])]==c['quote']
        for u in s.uses:
            b=u['binds_to']
            if isinstance(b,dict): assert s.t[b['cp']:b['cp']+len(b['quote'])]==b['quote']
        for x in s.defs:
            if x['in_window']: assert w[0]<=x['at']['cp']<w[1]
        for x in s.uses+s.ids: assert w[0]<=x['at']['cp']<w[1],x
        out=dict(format='citerift-stage03-annotation-v1',article=dict(wiki=s.p['wiki'],revision_id=s.p['revision_id'],source_sha256=s.p['source_sha256'],html_sha256=s.p['html_sha256'],window=[w[0],w[1]]),
          provenance=dict(agent='cf11-eval-ar-h1',started_at=START,finished_at=__import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),files_opened=files,tools=tools,unresolved=prov_unres),
          definitions=s.defs,uses=s.uses,identifiers=s.ids,unresolved_notes=list(unresolved))
        json.dump(out,open(f'{B}/out/ar-{s.p["revision_id"]}.json','w'),ensure_ascii=False,indent=1)
        print(s.d,len(s.defs),len(s.uses),len(s.ids))
