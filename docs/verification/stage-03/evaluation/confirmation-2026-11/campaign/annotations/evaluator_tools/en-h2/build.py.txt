import json, datetime
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h2'
GUIDE_SHA='2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e'
START=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

class Art:
    def __init__(s, d):
        s.d=d
        s.p=json.load(open(f'{BASE}/packets/{d}/packet.json'))
        s.t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
        s.defs=[]; s.uses=[]; s.ids=[]; s.keys={}; s.unres=[]
        s.w=(s.p['window']['cp_start'],s.p['window']['cp_end'])
    def loc(s, a, n=0, start=0, off=0, q=None):
        i=start-1
        for _ in range(n+1):
            i=s.t.index(a, i+1)
        i+=off
        q=q or a[off:]
        assert s.t[i:i+len(q)]==q,(a,q)
        return {'cp':i,'quote':q[:60]}
    def inw(s,l): return s.w[0]<=l['cp']<s.w[1]
    def define(s,key,a,kind,name=None,group='',tpl=(),uns=False,note_id=None,notes='',n=0,start=0,marker='none',tstart=None):
        at=s.loc(a,n,start)
        tl=[]
        for ta in tpl:
            tl.append({'at':s.loc(ta,0,at['cp'])})
        d={'id':f'd{len(s.defs)+1}','at':at,'in_window':s.inw(at),'kind':kind,'name':name,'group':group,
           'templates':tl,'unstructured':uns,'render_note_id':note_id,'marker':marker,'marker_text':None,'notes':notes}
        s.defs.append(d); s.keys[key]=at
    def use(s,a,bind,rid,notes='',n=0,start=0):
        at=s.loc(a,n,start)
        s.uses.append({'id':f'u{len(s.uses)+1}','at':at,'binds_to':s.keys[bind] if bind in s.keys else bind,'render_ref_id':rid,'notes':notes})
    def ident(s,a,scheme,role,key,notes='',n=0,start=0,off=0,q=None):
        s.ids.append({'at':s.loc(a,n,start,off,q),'scheme':scheme,'role':role,'key':key,'notes':notes})
    def write(s, opened_extra=()):
        end=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        out={'format':'citerift-stage03-annotation-v1',
         'article':{'wiki':s.p['wiki'],'revision_id':s.p['revision_id'],'source_sha256':s.p['source_sha256'],'html_sha256':s.p['html_sha256'],'window':[s.w[0],s.w[1]]},
         'provenance':{'agent':'cf11-eval-en-h2','started_at':START,'finished_at':end,
           'files_opened':[{'path':'ANNOTATION_GUIDE_v1.1.md','sha256':GUIDE_SHA},
             {'path':f'packets/{s.d}/source.wikitext','sha256':s.p['source_sha256']},
             {'path':f'packets/{s.d}/render.html','sha256':s.p['html_sha256']},
             {'path':f'packets/{s.d}/packet.json','sha256':__import__('hashlib').sha256(open(f'{BASE}/packets/{s.d}/packet.json','rb').read()).hexdigest()}],
           'tools':'python3 -I with stdlib re/json and lxml (list sup[typeof=mw:Extension/ref] and li[id^=cite_note] from render.html; regex search of source.wikitext for <ref, {{cite, doi, PMID); location verification text[cp:cp+len(quote)]==quote; build script in tools/. Labels decided by hand.',
           'unresolved':' | '.join(s.unres) if s.unres else 'none beyond notes'},
         'definitions':s.defs,'uses':s.uses,'identifiers':s.ids,'unresolved_notes':s.unres}
        # verify every location
        def chk(l):
            if isinstance(l,dict) and 'cp' in l: assert s.t[l['cp']:l['cp']+len(l['quote'])]==l['quote'],l
        for d in s.defs:
            chk(d['at']); [chk(x['at']) for x in d['templates']]
        for u in s.uses: chk(u['at']); chk(u['binds_to'])
        for i in s.ids: chk(i['at'])
        json.dump(out,open(f"{BASE}/out/{s.p['wiki']}-{s.p['revision_id']}.json",'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        print(s.d,'defs',sum(d['in_window'] for d in s.defs),'(+%d outside)'%sum(not d['in_window'] for d in s.defs),'uses',sum(s.inw(u['at']) for u in s.uses),'ids',len(s.ids))
