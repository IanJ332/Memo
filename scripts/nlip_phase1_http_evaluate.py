# SPDX-License-Identifier: MIT
"""Verify every frozen case through the authenticated NLIP HTTP route."""
import base64
import json
import sys
import tempfile
from pathlib import Path
from starlette.testclient import TestClient
from memlife.nlip.admission import AdmissionService, SpyAdapter
from memlife.nlip.agent import DeterministicAdapter
from memlife.nlip.app import ReportApplication
from nlip_phase1_evaluate import PIN, load, setup_case


def run(output, service_results):
    cases, oracles, catalog = load()
    oracle = {x['case_id']: x for x in oracles['cases']}
    service = {x['case_id']: x for x in json.loads(service_results.read_bytes())['cases']}
    results = []
    for case in cases['cases']:
        if not case['executable']:
            continue
        cid = case['case_id']; expected = oracle[cid]; arms = {}
        for mode in ('OFF', 'DIAGNOSTIC', 'ON'):
            with tempfile.TemporaryDirectory() as tmp:
                d,n,h,p,sessions,session,policy,dispatcher,message = setup_case(case, expected, catalog, Path(tmp))
                spy = SpyAdapter(DeterministicAdapter())
                app = ReportApplication(sessions, policy, dispatcher, n, AdmissionService(d,sessions,policy,dispatcher,spy,mode), origin='http://localhost')
                with TestClient(app.app, base_url='http://localhost') as client:
                    response = client.post('/nlip', content=json.dumps(message.as_dict()).encode(), headers={'origin':'http://localhost','host':'localhost','x-csrf-token':session.csrf,'cookie':'memlife_session='+session.sid,'content-type':'application/json'})
                assert response.status_code == 200, (cid, mode, response.text)
                assert len(spy.captures) == 1
                payload, sha = spy.captures[0]
                with d.lease(), d.transaction() as db:
                    audit = [json.loads(row[0]) for row in db.execute('SELECT payload FROM audit ORDER BY seq')]
                assert [a['phase'] for a in audit] == ['PRE_HANDOFF','ADAPTER_RETURNED']
                pre = audit[0]
                decisions = [{k:v for k,v in x.items() if k in ('record_id','classification','reason')} for x in pre['decisions']]
                expected_decisions = [{k:v for k,v in x.items() if k in ('record_id','classification','reason')} for x in expected['decisions']]
                if mode == 'OFF':
                    assert all(x['classification'] == 'UNASSESSED' for x in decisions)
                else:
                    assert decisions == expected_decisions, (cid,mode,decisions,expected_decisions)
                ids = [x['record_id'] for x in pre['context']]
                assert ids == expected['expected_delivered_ids' if mode == 'ON' else 'expected_input_ids']
                if mode == 'ON':
                    assert payload == base64.b64decode(expected['expected_adapter_input_base64'])
                    assert sha == expected['expected_adapter_input_sha256']
                baseline = service[cid]['arms'][mode]
                assert base64.b64encode(payload).decode() == baseline['adapter_envelope_base64']
                result = response.json()['Content']
                assert (result['action'],result['reason'],result['delivered']) == (baseline['tool_gate']['action'],baseline['tool_gate']['reason'],baseline['delivered'])
                arms[mode] = {'status_code':response.status_code, 'decisions':decisions, 'context':pre['context'], 'adapter_envelope_base64':base64.b64encode(payload).decode(), 'adapter_sha256':sha, 'tool_gate':{k:result[k] for k in ('action','reason','delivered')}, 'timing_ns':result['timing_ns']}
        results.append({'case_id':cid,'arms':arms})
    assert len(results) == 9
    with output.open('x') as f:
        json.dump({'manifest_sha256':PIN,'cases':results,'audit_only':['A01','A02']},f,indent=2); f.write('\n')
    print('PASS 9 cases, 27 authenticated HTTP executions:',output)

if __name__ == '__main__':
    run(Path(sys.argv[1]),Path(sys.argv[2]))
