import json,hashlib,datetime
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h3'
START=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
class A:
    def __init__(s,d):
        s.d=d; s.t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
        s.p=json.load(open(f'{BASE}/packets/{d}/packet.json'))
        s.defs=[];s.uses=[];s.ids=[];s.un=[];s.unres=''
    def L(s,q,after=0,n=1):
        i=after-1
        for _ in range(n):
            i=s.t.find(q,i+1)
            assert i>=0,(q,after,n)
        return {'cp':i,'quote':s.t[i:i+60] if len(q)<60 else q[:60]} if False else {'cp':i,'quote':s.t[i:i+max(len(q),min(40,len(s.t)-i))][:60]}
    def D(s,id,q,kind='note',name=None,group='',tpl=(),unstructured=False,rn=None,marker='none',mt=None,notes='',after=0,n=1):
        at=s.L(q,after,n)
        w=s.p['window']
        s.defs.append({'id':id,'at':at,'in_window':w['cp_start']<=at['cp']<w['cp_end'],'kind':kind,'name':name,'group':group,
          'templates':[{'at':s.L(x[0],at['cp'],x[1] if len(x)>1 else 1)} for x in tpl],'unstructured':unstructured,
          'render_note_id':rn,'marker':marker,'marker_text':mt,'notes':notes})
        return at
    def U(s,id,q,bind,rid=None,notes='',after=0,n=1):
        at=s.L(q,after,n)
        s.uses.append({'id':id,'at':at,'binds_to':bind,'render_ref_id':rid,'notes':notes});return at
    def I(s,q,scheme,role,key,notes='',after=0,n=1):
        l=s.L(q,after,n); l['quote']=q; s.ids.append({'at':l,'scheme':scheme,'role':role,'key':key,'notes':notes})
    def write(s,extra_files=()):
        for x in s.defs+s.uses+s.ids:
            for l in [x['at']]+([x['binds_to']] if isinstance(x.get('binds_to'),dict) else [])+[t['at'] for t in x.get('templates',[])]:
                assert s.t[l['cp']:l['cp']+len(l['quote'])]==l['quote'],l
        w=s.p['window']
        o={'format':'citerift-stage03-annotation-v1','article':{'wiki':s.p['wiki'],'revision_id':s.p['revision_id'],
           'source_sha256':s.p['source_sha256'],'html_sha256':s.p['html_sha256'],'window':[w['cp_start'],w['cp_end']]},
           'provenance':{'agent':'cf11-eval-ar-h3','started_at':START,'finished_at':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'files_opened':[{'path':f'packets/{s.d}/source.wikitext','sha256':s.p['source_sha256']},{'path':f'packets/{s.d}/render.html','sha256':s.p['html_sha256']},
               {'path':f'packets/{s.d}/packet.json','sha256':hashlib.sha256(open(f'{BASE}/packets/{s.d}/packet.json','rb').read()).hexdigest()},
               {'path':'ANNOTATION_GUIDE_v1.1.md','sha256':'2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e'}],
             'tools':'python3 -I (stdlib + lxml) snippets for text search, HTML element listing and quote verification; helper scripts in tools/; bash/cat for reading',
             'unresolved':s.unres},
           'definitions':s.defs,'uses':s.uses,'identifiers':s.ids,'unresolved_notes':s.un}
        json.dump(o,open(f"{BASE}/out/{s.p['wiki']}-{s.p['revision_id']}.json",'w'),ensure_ascii=False,indent=1)
        print(s.d,'defs',sum(d['in_window'] for d in s.defs),'(total',len(s.defs),') uses',len(s.uses),'ids',len(s.ids))
