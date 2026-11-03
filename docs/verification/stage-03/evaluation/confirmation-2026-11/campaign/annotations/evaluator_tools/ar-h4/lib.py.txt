import json,hashlib,re,datetime
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h4'
class Art:
    def __init__(s,d):
        s.d=d; s.p=json.load(open(f'{BASE}/packets/{d}/packet.json'))
        s.t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
        s.w=(s.p['window']['cp_start'],s.p['window']['cp_end'])
        s.defs=[];s.uses=[];s.ids=[];s.unres=[];s.n=0;s.un=0
    def loc(s,cp,q):
        assert s.t[cp:cp+len(q)]==q,(cp,q,s.t[cp:cp+len(q)])
        return {'cp':cp,'quote':q}
    def at(s,anchor,n=1,off=0,ln=60):
        """position of nth occurrence of anchor (+off), quote ln chars from there"""
        i=-1
        for _ in range(n):
            i=s.t.find(anchor,i+1); assert i>=0,(anchor,n)
        i+=off
        return s.loc(i,s.t[i:i+ln])
    def at_cp(s,cp,ln=60):
        return s.loc(cp,s.t[cp:cp+ln])
    def inw(s,cp): return s.w[0]<=cp<s.w[1]
    def defn(s,at,kind,name=None,group='',templates=(),unstructured=False,rid=None,marker='none',mt=None,notes='',inwin=None):
        s.n+=1; i=f'd{s.n}'
        s.defs.append({'id':i,'at':at,'in_window':s.inw(at['cp']) if inwin is None else inwin,'kind':kind,'name':name,'group':group,
          'templates':[{'at':x} for x in templates],'unstructured':unstructured,'render_note_id':rid,'marker':marker,'marker_text':mt,'notes':notes})
        return at
    def use(s,at,binds,rid=None,notes=''):
        s.un+=1
        s.uses.append({'id':f'u{s.un}','at':at,'binds_to':binds,'render_ref_id':rid,'notes':notes})
    def ident(s,at,scheme,role,key,notes=''):
        s.ids.append({'at':at,'scheme':scheme,'role':role,'key':key,'notes':notes})
    def write(s,files,tools,unresolved,start):
        o={'format':'citerift-stage03-annotation-v1',
         'article':{'wiki':s.p['wiki'],'revision_id':s.p['revision_id'],'source_sha256':s.p['source_sha256'],'html_sha256':s.p['html_sha256'],'window':list(s.w)},
         'provenance':{'agent':'cf11-eval-ar-h4','started_at':start,'finished_at':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           'files_opened':[{'path':f'packets/{s.d}/source.wikitext','sha256':s.p['source_sha256']},{'path':f'packets/{s.d}/render.html','sha256':s.p['html_sha256']},{'path':f'packets/{s.d}/packet.json','sha256':hashlib.sha256(open(f"{BASE}/packets/{s.d}/packet.json",'rb').read()).hexdigest()},{'path':'ANNOTATION_GUIDE_v1.1.md','sha256':'2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e'}],
           'tools':tools,'unresolved':unresolved},
         'definitions':s.defs,'uses':s.uses,'identifiers':s.ids,'unresolved_notes':s.unres}
        json.dump(o,open(f'{BASE}/out/ar-{s.p["revision_id"]}.json','w'),ensure_ascii=False,indent=1)
        print(s.d,'defs',len(s.defs),'uses',len(s.uses),'ids',len(s.ids))
def lines(t,w):
    pos=0
    for l in t.split('\n'):
        yield pos,l
        pos+=len(l)+1
