import json, hashlib, sys
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-h1/'
class Art:
    def __init__(s, aid):
        s.aid=aid
        s.pk=json.load(open(BASE+f'packets/{aid}/packet.json'))
        s.text=open(BASE+f'packets/{aid}/source.wikitext',encoding='utf-8').read()
        s.defs=[]; s.uses=[]; s.ids=[]; s.unres=[]
        s.w=(s.pk['window']['cp_start'],s.pk['window']['cp_end'])
    def L(s, start_anchor, n=0, ql=40, frm=0):
        """location of n-th (0-based) occurrence of start_anchor after frm"""
        i=frm-1
        for _ in range(n+1):
            i=s.text.find(start_anchor,i+1)
            assert i>=0,(start_anchor,n)
        q=s.text[i:i+ql]
        assert s.text[i:i+len(q)]==q
        return {"cp":i,"quote":q}
    def Lq(s, cp, ql=40):
        q=s.text[cp:cp+ql]; return {"cp":cp,"quote":q}
    def D(s, id, at, kind='note', name=None, group='', templates=(), unstructured=False, nid=None, marker='none', mtext=None, notes='', inw=None):
        if inw is None: inw = s.w[0]<=at['cp']<s.w[1]
        s.defs.append(dict(id=id,at=at,in_window=inw,kind=kind,name=name,group=group,templates=[{"at":t} for t in templates],unstructured=unstructured,render_note_id=nid,marker=marker,marker_text=mtext,notes=notes))
    def U(s,id,at,bind,rid,notes=''):
        s.uses.append(dict(id=id,at=at,binds_to=bind,render_ref_id=rid,notes=notes))
    def I(s,at,scheme,role,key,notes=''):
        s.ids.append(dict(at=at,scheme=scheme,role=role,key=key,notes=notes))
    def write(s, started, tools, unresolved, extra_files=()):
        import datetime
        for x in s.defs+s.uses+s.ids:
            for loc in [x['at']]+([x['binds_to']] if isinstance(x.get('binds_to'),dict) else [])+[t['at'] for t in x.get('templates',[])]:
                assert s.text[loc['cp']:loc['cp']+len(loc['quote'])]==loc['quote'],loc
        pk=s.pk
        out={"format":"citerift-stage03-annotation-v1",
         "article":{"wiki":pk['wiki'],"revision_id":pk['revision_id'],"source_sha256":pk['source_sha256'],"html_sha256":pk['html_sha256'],"window":[s.w[0],s.w[1]]},
         "provenance":{"agent":"cf11-eval-en-h1","started_at":started,"finished_at":datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           "files_opened":[{"path":f"packets/{s.aid}/source.wikitext","sha256":pk['source_sha256']},{"path":f"packets/{s.aid}/render.html","sha256":pk['html_sha256']},{"path":f"packets/{s.aid}/packet.json","sha256":hashlib.sha256(open(BASE+f'packets/{s.aid}/packet.json','rb').read()).hexdigest()},{"path":"ANNOTATION_GUIDE_v1.1.md","sha256":"2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e"}],
           "tools":tools,"unresolved":unresolved},
         "definitions":s.defs,"uses":s.uses,"identifiers":s.ids,"unresolved_notes":s.unres}
        json.dump(out,open(BASE+f"out/{s.aid}.json","w"),ensure_ascii=False,indent=1)
        print(s.aid,len(s.defs),len(s.uses),len(s.ids))
