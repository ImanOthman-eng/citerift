import json,hashlib,re
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c2'
class Art:
    def __init__(s,d):
        s.d=d; s.p=json.load(open(f'{BASE}/packets/{d}/packet.json'))
        s.t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
        assert hashlib.sha256(s.t.encode()).hexdigest()==s.p['source_sha256']
        w=s.p['window']; s.a,s.b=w['cp_start'],w['cp_end']
        s.defs=[];s.uses=[];s.ids=[];s.unres=[]
    def loc(s,cp,n=40):
        q=s.t[cp:cp+n]
        assert s.t[cp:cp+len(q)]==q
        return {'cp':cp,'quote':q}
    def inw(s,cp): return s.a<=cp<s.b
    def find(s,snip,start=0):
        i=s.t.find(snip,start); assert i>=0,snip; return i
    def adddef(s,cp,kind,name,group,templates,unstructured,note_id,marker='none',marker_text=None,notes='',n=40):
        d={'id':f'd{len(s.defs)+1}','at':s.loc(cp,n),'in_window':s.inw(cp),'kind':kind,'name':name,'group':group,
           'templates':[{'at':s.loc(c,n)} for c in templates],'unstructured':unstructured,'render_note_id':note_id,
           'marker':marker,'marker_text':marker_text,'notes':notes}
        s.defs.append(d); return d
    def adduse(s,cp,bind,rid,notes='',n=40):
        s.uses.append({'id':f'u{len(s.uses)+1}','at':s.loc(cp,n),'binds_to':s.loc(bind,n) if isinstance(bind,int) else bind,
                       'render_ref_id':rid,'notes':notes})
    def addid(s,cp,raw,scheme,role,key,notes=''):
        assert s.t[cp:cp+len(raw)]==raw
        s.ids.append({'at':{'cp':cp,'quote':raw},'scheme':scheme,'role':role,'key':key,'notes':notes})
    def write(s,start,files,tools,unresolved,unres_notes=None):
        import datetime
        out={'format':'citerift-stage03-annotation-v1',
         'article':{'wiki':s.p['wiki'],'revision_id':s.p['revision_id'],'source_sha256':s.p['source_sha256'],'html_sha256':s.p['html_sha256'],'window':[s.a,s.b]},
         'provenance':{'agent':'cf11-eval-en-c2','started_at':start,'finished_at':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           'files_opened':files,'tools':tools,'unresolved':unresolved},
         'definitions':s.defs,'uses':s.uses,'identifiers':s.ids,'unresolved_notes':unres_notes or []}
        json.dump(out,open(f'{BASE}/out/{s.d}.json','w'),ensure_ascii=False,indent=1)
        nd=sum(d['in_window'] for d in s.defs); nu=sum(s.inw(int(u['at']['cp'])) for u in s.uses)
        print(s.d,'defs in window',nd,'(total',len(s.defs),') uses in window',nu,'(total',len(s.uses),') ids',len(s.ids))
def sha(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()
def files(a):
    return [{'path':f'packets/{a.d}/{n}','sha256':sha(f'{BASE}/packets/{a.d}/{n}')} for n in ('packet.json','source.wikitext','render.html')]+[{'path':'ANNOTATION_GUIDE_v1.1.md','sha256':sha(f'{BASE}/ANNOTATION_GUIDE_v1.1.md')}]
