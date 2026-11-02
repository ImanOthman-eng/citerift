#!/bin/bash
# usage: vr.sh <src_dir> <label>  -- verify + replay every final-campaign extraction with the given source tree
cd /home/user/citerift
F=docs/verification/stage-03/evaluation/final
python3 -I - "$1" "$2" <<'PY'
import json,subprocess,sys,os
src,label=sys.argv[1],sys.argv[2]
F='docs/verification/stage-03/evaluation/final'
spec=json.load(open(F+'/run/score_spec_adjudicated.json'))
env=dict(os.environ,PYTHONPATH=src)
rows=[]
for e in spec['splits']['holdout']:
    b=os.path.normpath(os.path.join(F,'run',e['bundle'])); x=os.path.normpath(os.path.join(F,'run',e['extraction']))
    r={'extraction':x}
    for cmd in ('verify','replay'):
        p=subprocess.run(['.venv/bin/python','-I','-c','import sys;sys.path.insert(0,sys.argv[1]);sys.argv=["citerift-wiki"]+sys.argv[2:];from citerift.wiki.cli import main;sys.exit(main())',src,cmd,'--bundle',b,'--extraction',x],capture_output=True,text=True,env=env)
        r[cmd]=p.returncode
    rows.append(r)
print(json.dumps({'label':label,'src':src,'n':len(rows),'verify_exit0':sum(r['verify']==0 for r in rows),'replay_exit0':sum(r['replay']==0 for r in rows),'nonzero':[r for r in rows if r['verify'] or r['replay']]},indent=1))
PY
