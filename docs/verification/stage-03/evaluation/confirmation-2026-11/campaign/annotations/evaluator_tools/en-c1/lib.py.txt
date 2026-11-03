import json, hashlib, sys
BASE='/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval/en-c1'
class Art:
    def __init__(s, key):
        s.key=key; s.dir=f'{BASE}/packets/{key}'
        s.pk=json.load(open(s.dir+'/packet.json'))
        s.text=open(s.dir+'/source.wikitext',encoding='utf-8',newline='').read()
        assert len(s.text)==s.pk['source_code_points'], (len(s.text), s.pk['source_code_points'])
        s.w0=s.pk['window']['cp_start']; s.w1=s.pk['window']['cp_end']
    def loc(s, quote, anchor=None, nth=0, after=0):
        """find quote; if anchor, first find anchor (from `after`) then quote at/after anchor start"""
        start=after
        if anchor is not None:
            a=s.text.find(anchor,start)
            assert a>=0, ('anchor missing',anchor)
            start=a
        p=start
        for _ in range(nth+1):
            q=s.text.find(quote,p)
            assert q>=0, ('quote missing',quote,anchor)
            p=q+1
        cp=q
        assert s.text[cp:cp+len(quote)]==quote
        return {'cp':cp,'quote':quote}
    def check(s, o):
        if isinstance(o,dict):
            if 'cp' in o and 'quote' in o:
                assert s.text[o['cp']:o['cp']+len(o['quote'])]==o['quote'], o
            for v in o.values(): s.check(v)
        elif isinstance(o,list):
            for v in o: s.check(v)

import datetime, os
def now(): return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
GUIDE_SHA='2b40bb323c2254f8c12e40f9de39e759abae6b89aba8ffcc916b8abcb648cf2e'
def finish(a, defs, uses, idents, started, unresolved_prov, unresolved_notes=()):
    pk=a.pk
    out={'format':'citerift-stage03-annotation-v1',
      'article':{'wiki':pk['wiki'],'revision_id':pk['revision_id'],'source_sha256':pk['source_sha256'],'html_sha256':pk['html_sha256'],'window':[a.w0,a.w1]},
      'provenance':{'agent':'cf11-eval-en-c1','started_at':started,'finished_at':now(),
        'files_opened':[{'path':'ANNOTATION_GUIDE_v1.1.md','sha256':GUIDE_SHA},
                        {'path':f'packets/{a.key}/packet.json','sha256':hashlib.sha256(open(a.dir+'/packet.json','rb').read()).hexdigest()},
                        {'path':f'packets/{a.key}/source.wikitext','sha256':pk['source_sha256']},
                        {'path':f'packets/{a.key}/render.html','sha256':pk['html_sha256']}],
        'tools':'python3 standard library and lxml (stdin/tools scripts) for str.find location checks and listing HTML sup/li elements; every location verified text[cp:cp+len(quote)]==quote',
        'unresolved':unresolved_prov},
      'definitions':defs,'uses':uses,'identifiers':idents,'unresolved_notes':list(unresolved_notes)}
    a.check(out)
    # sanity: sha of files
    assert hashlib.sha256(open(a.dir+'/source.wikitext','rb').read()).hexdigest()==pk['source_sha256']
    assert hashlib.sha256(open(a.dir+'/render.html','rb').read()).hexdigest()==pk['html_sha256']
    json.dump(out,open(f'{BASE}/out/{a.key}.json','w'),ensure_ascii=False,indent=1)
    nd=sum(1 for d in defs if d['in_window']); nu=sum(1 for u in uses); ni=len(idents)
    print(a.key,'defs in window',nd,'defs total',len(defs),'uses',nu,'idents',ni)

def D(a,id,at,kind,templates,render,name=None,group='',unstructured=False,marker='none',marker_text=None,notes='',in_window=True):
    return {'id':id,'at':at,'in_window':in_window,'kind':kind,'name':name,'group':group,
            'templates':[{'at':t} for t in templates],'unstructured':unstructured,
            'render_note_id':render,'marker':marker,'marker_text':marker_text,'notes':notes}
def U(id,at,binds,render=None,notes=''):
    return {'id':id,'at':at,'binds_to':binds,'render_ref_id':render,'notes':notes}
def I(at,scheme,role,key,notes=''):
    return {'at':at,'scheme':scheme,'role':role,'key':key,'notes':notes}

import re
def fields(a,lo=None,hi=None):
    """locate |doi= / |pmid= parameter values (locator only; roles are decided by hand)"""
    lo=a.w0 if lo is None else lo; hi=a.w1 if hi is None else hi
    out=[]
    for m in re.finditer(r'(?<![\w-])(doi|pmid)\s*=\s*([^|}\n]*?)\s*(?=[|}\n])',a.text):
        if lo<=m.start()<hi and m.group(2):
            out.append((m.group(1),m.start(2),m.group(2)))
    return out
def dkey(v):
    return v.lower()
