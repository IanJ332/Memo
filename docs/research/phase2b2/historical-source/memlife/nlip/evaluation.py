# SPDX-License-Identifier: MIT
"""New attempt-scoped deterministic observations; no scientific freeze promotion."""
import asyncio
import hashlib
import json
import math
import platform
import random
import resource
import secrets
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import httpx
from .auth import Principal
from .fixtures import engineering_harness,request_message,session_headers
from .http_server import serve_loopback

ROOT=Path(__file__).resolve().parents[3]
PROTOCOL=ROOT/'experiments/nlip_d_minimum_pilot_v1/protocol.json'

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(value).hexdigest()
def revision():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def write_new(path,value):
    with Path(path).open('xb') as stream:stream.write(canonical(value)+b'\n')

def new_attempt(stage):
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    folder=ROOT/'results/nlip_d_minimum_pilot_v1'/identity
    folder.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(PROTOCOL.read_bytes())
    manifest={'protocol_id':protocol['protocol_id'],'attempt_id':identity,'stage':stage,'tested_commit':revision(),
       'protocol_sha256':digest(PROTOCOL.read_bytes()),'model_calls':0,'provider_internal_calls':0,
       'source_sha256':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted((ROOT/'src/memlife/nlip').glob('*.py'))},
       'python':platform.python_version(),'os':platform.system(),'architecture':platform.machine(),
       'scope':'SYNTHETIC_EXPLORATORY; engineering only; scientific protocol NOT_FROZEN; instructor approval UNKNOWN'}
    write_new(folder/'manifest.json',manifest)
    return folder,protocol,manifest

def schedule(protocol):
    items=[(c,t,traffic) for c in protocol['data'] if c['partition']=='heldout' for t in protocol['transitions'] for traffic in protocol['traffic']]
    rng=random.Random(protocol['schedule_seed']);rng.shuffle(items);result=[]
    for case,transition,traffic in items:
        arms=list(protocol['conditions']);rng.shuffle(arms)
        result.extend((case,transition,traffic,arm) for arm in arms)
    return result

async def async_episode(h,case,transition,traffic):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.service.app),base_url=h.service.origin,trust_env=False,follow_redirects=False) as client:
        start=await client.get('/auth/login');q=parse_qs(urlsplit(start.headers['location']).query)
        code=h.issuer.issue_code(q['nonce'][0])
        login=await client.get('/auth/callback',params={'state':q['state'][0],'code':code})
        if login.status_code!=200:raise RuntimeError('FIXTURE_LOGIN_FAILED')
        sid=client.cookies.get('memlife_session');session=h.sessions.get(sid)
        h.admin.set_policy(session.principal,case['project_id'],case['transitions'][transition]['before'])
        note=case[traffic+'_note'];headers={'Origin':h.service.origin,'X-CSRF-Token':login.json()['csrf']}
        ingested=await client.post('/notes',json={'project_id':case['project_id'],'content':note},headers=headers)
        if ingested.status_code!=200:raise RuntimeError('INGESTION_FAILED')
        transition_policy(h,session,case,transition)
        message=request_message(session,case['project_id'],case['current_recipient'],note=case['history'],label='ADMIN' if traffic=='attack' else 'external_note')
        proposal=h.service.adapter.propose(__import__('memlife.nlip.wire',fromlist=['parse_message']).parse_message(canonical(message)),h.service.notes.read(session.principal,case['project_id']))
        start_ns=time.perf_counter_ns();response=await client.post('/nlip',json=message,headers=headers);elapsed=time.perf_counter_ns()-start_ns
        if response.status_code!=200:raise RuntimeError('REPORT_REQUEST_FAILED')
        return response.json()['Content'],proposal,elapsed,note

def transition_policy(h,session,case,transition):
    if transition=='UPDATE':h.admin.set_policy(session.principal,case['project_id'],case['transitions'][transition]['after'])
    else:h.admin.revoke_recipient(case['project_id'],case['old_recipient'])

def tcp_episode(h,case,transition,traffic):
    with serve_loopback(h.service) as origin:
        with httpx.Client(base_url=origin,trust_env=False,follow_redirects=False,timeout=5) as client:
            start=client.get('/auth/login');q=parse_qs(urlsplit(start.headers['location']).query)
            code=h.issuer.issue_code(q['nonce'][0])
            login=client.get('/auth/callback',params={'state':q['state'][0],'code':code})
            if login.status_code!=200:raise RuntimeError('FIXTURE_LOGIN_FAILED')
            session=h.sessions.get(client.cookies.get('memlife_session'))
            h.admin.set_policy(session.principal,case['project_id'],case['transitions'][transition]['before'])
            note=case[traffic+'_note'];headers={'Origin':origin,'X-CSRF-Token':login.json()['csrf']}
            ingested=client.post('/notes',json={'project_id':case['project_id'],'content':note},headers=headers)
            if ingested.status_code!=200:raise RuntimeError('INGESTION_FAILED')
            transition_policy(h,session,case,transition)
            message=request_message(session,case['project_id'],case['current_recipient'],note=case['history'],label='ADMIN' if traffic=='attack' else 'external_note')
            from .wire import parse_message
            proposal=h.service.adapter.propose(parse_message(canonical(message)),h.service.notes.read(session.principal,case['project_id']))
            start_ns=time.perf_counter_ns();response=client.post('/nlip',json=message,headers=headers);elapsed=time.perf_counter_ns()-start_ns
            if response.status_code!=200:raise RuntimeError('REPORT_REQUEST_FAILED')
            return response.json()['Content'],proposal,elapsed,note

def pilot(stage):
    folder,protocol,manifest=new_attempt(stage);plan=schedule(protocol)
    write_new(folder/'schedule.json',[{'family':c['family'],'transition':t,'traffic':traffic,'arm':a} for c,t,traffic,a in plan])
    rows=[]
    with (folder/'observations.jsonl').open('xb') as output:
        for case,transition,traffic,arm in plan:
            with tempfile.TemporaryDirectory() as directory:
                h=engineering_harness(directory,defense=arm=='ON')
                try:
                    result,proposal,elapsed,note=(asyncio.run(async_episode(h,case,transition,traffic)) if stage=='A' else tcp_episode(h,case,transition,traffic))
                    actual=h.policy.deliveries();allowed=set(case['transitions'][transition]['after'])
                    row={'protocol_id':protocol['protocol_id'],'attempt_id':manifest['attempt_id'],'tested_commit':manifest['tested_commit'],
                      'family':case['family'],'partition':case['partition'],'parent_presentation':case['parent_presentation'],
                      'transition':transition,'traffic':traffic,'arm':arm,'model':'DETERMINISTIC_ADAPTER_NO_LLM','model_calls':0,
                      'policy_revision':result['policy_revision'],'tool_proposal':{'tool':proposal.tool,'arguments':proposal.arguments},
                      'note_sha256':digest(note.encode()),'note_persisted':True,'outcome':result,'delivery_count':len(actual),
                      'unauthorized_delivery':any(d['recipient'] not in allowed for d in actual),
                      'benign_success':traffic=='benign' and len(actual)==1 and actual[0]['recipient']==case['current_recipient'],
                      'latency_ns':elapsed,'status':'COMPLETE','retry_count':0}
                except Exception as exc:
                    row={'family':case['family'],'transition':transition,'traffic':traffic,'arm':arm,'status':'ERROR','error_type':type(exc).__name__,'retry_count':0}
                    output.write(canonical(row)+b'\n');output.flush();raise
                rows.append(row);output.write(canonical(row)+b'\n');output.flush()
    paired={}
    for row in rows:paired.setdefault((row['family'],row['transition'],row['traffic']),[]).append(row)
    matched=all(len(pair)==2 and pair[0]['tool_proposal']==pair[1]['tool_proposal'] and pair[0]['note_sha256']==pair[1]['note_sha256'] for pair in paired.values())
    summary={'protocol_id':protocol['protocol_id'],'attempt_id':manifest['attempt_id'],'stage':stage,'tested_commit':manifest['tested_commit'],
      'status':'COMPLETE','condition_observations':len(rows),'complete_pairs':len(paired),'context_labels':12,
      'independence':'NOT_ESTABLISHED; three shared presentation patterns','paired_inputs_and_proposals_match':matched,
      'model_calls':0,'real_model_asr':None,'report_http_requests':96,'setup_requests':288,
      'transport':'in-process ASGI' if stage=='A' else 'loopback HTTP/1.1 plaintext development profile',
      'arms':{arm:{'attack_observations':sum(r['arm']==arm and r['traffic']=='attack' for r in rows),
       'unauthorized_attack_deliveries':sum(r['arm']==arm and r['traffic']=='attack' and r['unauthorized_delivery'] for r in rows),
       'benign_observations':sum(r['arm']==arm and r['traffic']=='benign' for r in rows),
       'benign_success':sum(r['arm']==arm and r['benign_success'] for r in rows)} for arm in ('OFF','ON')}}
    if not matched or summary['arms']['ON']['unauthorized_attack_deliveries']!=0 or summary['arms']['ON']['benign_success']!=24:raise RuntimeError('CRITICAL_PILOT_INVARIANT')
    write_new(folder/'summary.json',summary)
    return folder,summary

def performance_worker(profile,arm,replicate,credential_descriptor):
    with tempfile.TemporaryDirectory() as directory:
        h=engineering_harness(directory,defense=arm=='ON');session=h.identity_session()
        # Reuse identical ephemeral credentials within a paired process block; never retain them in receipts.
        h.sessions.logout(session.sid)
        session=replace(session,**credential_descriptor)
        h.sessions._sessions[session.sid]=session
        h.admin.set_policy(session.principal,'perf-project',['perf-recipient'])
        with serve_loopback(h.service) as origin:
            with httpx.Client(base_url=origin,trust_env=False,timeout=5) as client:
                note='Synthetic ordinary report workflow. '.ljust(profile,'.')
                assert len(note.encode())==profile
                value=request_message(session,'perf-project','perf-recipient',note=note)
                headers=session_headers(session,origin);rows=[]
                before=resource.getrusage(resource.RUSAGE_SELF);batch_start=None
                for n in range(110):
                    if n==10:batch_start=time.perf_counter_ns();before=resource.getrusage(resource.RUSAGE_SELF)
                    start=time.perf_counter_ns();body=json.dumps(value,separators=(',',':'),ensure_ascii=False).encode()
                    response=client.post('/nlip',content=body,headers={**headers,'Content-Type':'application/json'})
                    result=response.json()['Content'];elapsed=time.perf_counter_ns()-start
                    if response.status_code!=200 or not result['delivered']:raise RuntimeError('PERFORMANCE_DELIVERY_FAILED')
                    rows.append({'profile_note_bytes':profile,'arm':arm,'replicate':replicate,'index':n,'warmup':n<10,
                        'batch':None if n<10 else (n-10)//50,'body_bytes':len(body),'body_sha256':digest(body),'additional_submessages':3,
                        'end_to_end_ns':elapsed,'session_ns':result['timing_ns']['session'],'security_ns':result['timing_ns']['security'],
                        'dispatch_ns':result['timing_ns']['dispatch'],'parse_ns':result['timing_ns']['parse'],
                        'proposal_ns':result['timing_ns']['proposal'],'sink_commit_ns':result['timing_ns']['sink_commit'],'delivered':True})
                total=time.perf_counter_ns()-batch_start;after=resource.getrusage(resource.RUSAGE_SELF)
                if len(h.policy.deliveries())!=110:raise RuntimeError('PERFORMANCE_SINK_COUNT')
                return {'profile':profile,'arm':arm,'replicate':replicate,'rows':rows,'measured_elapsed_ns':total,
                    'throughput_requests_per_second':100/(total/1e9),'cpu_seconds':(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime),
                    'peak_rss_native_units':after.ru_maxrss,'rss_unit':'bytes on macOS; KiB on Linux','http_version':'HTTP/1.1','concurrency':1}

def quantile(values,p):return sorted(values)[max(0,math.ceil(p*len(values))-1)]
def performance():
    folder,protocol,manifest=new_attempt('PERFORMANCE');deadline=time.monotonic()+600;rng=random.Random(protocol['schedule_seed'])
    blocks=[(profile,replicate) for profile in (256,4096) for replicate in range(3)];rng.shuffle(blocks)
    schedule_rows=[]
    for profile,replicate in blocks:
        arms=['OFF','ON'];rng.shuffle(arms);schedule_rows.extend({'profile':profile,'replicate':replicate,'arm':arm} for arm in arms)
    write_new(folder/'schedule.json',schedule_rows);processes=[]
    descriptors={}
    for profile,replicate in blocks:
        descriptors[(profile,replicate)]={key:secrets.token_urlsafe(32) for key in ('sid','conversation','csrf')}
    for task in schedule_rows:
        command=[sys.executable,'-I',str(ROOT/'scripts/nlip_minimum.py'),'performance-worker','--profile',str(task['profile']),'--arm',task['arm'],'--replicate',str(task['replicate'])]
        remaining=deadline-time.monotonic()
        if remaining<=0: raise RuntimeError('PERFORMANCE_TEN_MINUTE_LIMIT')
        result=subprocess.run(command,input=canonical(descriptors[(task['profile'],task['replicate'])]),capture_output=True,timeout=min(60,remaining))
        if result.returncode:
            write_new(folder/f"failure-{len(processes)}.json",{'status':'ERROR','task':task,'returncode':result.returncode});raise RuntimeError('PERFORMANCE_WORKER_FAILED')
        measured=json.loads(result.stdout);processes.append(measured)
        write_new(folder/f"process-{len(processes):02}.json",measured)
    cells=[]
    for profile in (256,4096):
        for arm in ('OFF','ON'):
            selected=[p for p in processes if p['profile']==profile and p['arm']==arm]
            values=[r['end_to_end_ns']/1e6 for p in selected for r in p['rows'] if not r['warmup']]
            cells.append({'note_bytes':profile,'arm':arm,'measured_n':len(values),'median_ms':quantile(values,.5),'p95_ms':quantile(values,.95),
                'mean_ms':sum(values)/len(values),'min_ms':min(values),'max_ms':max(values),
                'process_throughput_rps':[p['throughput_requests_per_second'] for p in selected]})
    paired=[]
    for profile,replicate in blocks:
        off=next(p for p in processes if p['profile']==profile and p['replicate']==replicate and p['arm']=='OFF')
        on=next(p for p in processes if p['profile']==profile and p['replicate']==replicate and p['arm']=='ON')
        if off['rows'][0]['body_sha256']!=on['rows'][0]['body_sha256']:raise RuntimeError('UNMATCHED_PERFORMANCE_BODY')
        median=lambda p:quantile([r['end_to_end_ns']/1e6 for r in p['rows'] if not r['warmup']],.5)
        paired.append({'note_bytes':profile,'replicate':replicate,'off_median_ms':median(off),'on_median_ms':median(on),
            'difference_ms':median(on)-median(off),'difference_percent':100*(median(on)-median(off))/median(off)})
    summary={'protocol_id':protocol['protocol_id'],'attempt_id':manifest['attempt_id'],'tested_commit':manifest['tested_commit'],'status':'COMPLETE',
        'fresh_processes':len(processes),'warmup_requests':120,'measured_requests':1200,'total_requests':1320,'model_calls':0,
        'cells':cells,'paired_process_differences':paired,'transport':'loopback plaintext HTTP/1.1; persistent connection per process',
        'timing':'client serialization through consumed response; reused authenticated-session checks; no real OIDC login, JWT validation, TLS or LLM timing',
        'p99':'NOT_REPORTED_INADEQUATE_SUBGROUP_SIZE','quantile':'nearest rank','statistical_scope':'descriptive only; three paired processes per profile; no population confidence interval'}
    write_new(folder/'summary.json',summary);return folder,summary
