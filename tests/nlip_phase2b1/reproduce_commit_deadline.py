import json, tempfile, time
from pathlib import Path
from scripts.nlip_phase2b1_pilot import Pilot
class Fake:
    def send(self,*args):
        proposal={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(proposal)}}]}).encode()
class DelayedCommit:
    def __init__(self,db): self.db=db
    def __getattr__(self,k): return getattr(self.db,k)
    def commit(self): time.sleep(.15);return self.db.commit()
with tempfile.TemporaryDirectory() as root:
    p=Pilot(Path(root)/'evidence.sqlite',Fake(),request_seconds=.08, protocol='v1'); fixture=p._fixture
    def delayed(s):
        result=fixture(s);policy=result[4];connection=policy._connection
        policy._connection=lambda write=False: DelayedCommit(connection(write)) if write else connection(write)
        return result
    p._fixture=delayed
    result=p.run('authorized','ON')
    print(json.dumps({k:result[k] for k in ('error','delivered','dispatcher_decision','elapsed_ms','task_outcome')},sort_keys=True))
