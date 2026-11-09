import json,hashlib,sys,re
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/ar-h2'
GUIDE='2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
def build(d, defs, uses, idspecs, unresolved, started, win_override=None):
    pk=json.load(open(f'{BASE}/packets/{d}/packet.json'))
    t=open(f'{BASE}/packets/{d}/source.wikitext',encoding='utf-8').read()
    ss=sha(f'{BASE}/packets/{d}/source.wikitext'); hs=sha(f'{BASE}/packets/{d}/render.html')
    assert ss==pk['source_sha256'] and hs==pk['html_sha256']
    w0,w1=pk['window']['cp_start'],pk['window']['cp_end']
    def L(cp,n=60):
        q=t[cp:cp+n]; assert t[cp:cp+len(q)]==q; return {'cp':cp,'quote':q}
    outd=[];idx={}
    for i,(cp,kind,name,tm,unstr,nid,notes) in enumerate(defs,1):
        assert t.startswith('<ref',cp)
        outd.append({'id':f'd{i}','at':L(cp),'in_window':w0<=cp<w1,'kind':kind,'name':name,'group':'',
          'templates':[{'at':L(c)} for c in tm],'unstructured':unstr,'render_note_id':nid,
          'marker':'none','marker_text':None,'notes':notes}); idx[cp]=1
    outu=[]
    for i,(cp,b,sup,notes) in enumerate(uses,1):
        assert t.startswith('<ref',cp); assert b in idx
        outu.append({'id':f'u{i}','at':L(cp),'binds_to':L(b),'render_ref_id':sup,'notes':notes})
    outi=[]
    for (anchor,occ,length,scheme,role,key,notes) in idspecs:
        p=-1
        for _ in range(occ+1): p=t.find(anchor,p+1)
        assert p>=0 and w0<=p<w1
        q=t[p:p+length]
        outi.append({'at':{'cp':p,'quote':q},'scheme':scheme,'role':role,'key':key,'notes':notes})
    out={'format':'citerift-stage03-annotation-v1',
     'article':{'wiki':pk['wiki'],'revision_id':pk['revision_id'],'source_sha256':ss,'html_sha256':hs,'window':[w0,w1]},
     'provenance':{'agent':'cf11-eval-ar-h2','started_at':started,'finished_at':__import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
       'files_opened':[{'path':'ANNOTATION_GUIDE_v1.1.md','sha256':GUIDE},
         {'path':f'packets/{d}/packet.json','sha256':sha(f'{BASE}/packets/{d}/packet.json')},
         {'path':f'packets/{d}/source.wikitext','sha256':ss},{'path':f'packets/{d}/render.html','sha256':hs}],
       'tools':'Python 3 standard library and lxml, run from stdin or from tools/: regex search of source.wikitext, listing of sup[typeof~mw:Extension/ref] and li[id^=cite_note] in render.html, string-slice verification of every location.',
       'unresolved':'; '.join(unresolved) if unresolved else 'nothing undecided beyond unresolved_notes'},
     'definitions':outd,'uses':outu,'identifiers':outi,'unresolved_notes':unresolved}
    json.dump(out,open(f'{BASE}/out/{pk["wiki"]}-{pk["revision_id"]}.json','w'),ensure_ascii=False,indent=1)
    print(d,len(outd),len(outu),len(outi),sum(1 for x in outd if x['in_window']))
