import copy,hashlib,json,socket
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from memlife.nlip import model_adapter as a
from memlife.nlip.admission import TypedContext
from memlife.nlip.wire import parse_message

ROOT=Path(__file__).resolve().parents[2]
if not (ROOT/'docs/research/phase2b5b/compatibility-candidate-v5.json').is_file():
 pytest.skip('requires private immutable Phase 2B-5B execution artifacts', allow_module_level=True)
M=json.loads((ROOT/'docs/research/phase2b5b/compatibility-candidate-v5.json').read_bytes())
VALID={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
ABSTAIN={'outcome':'ABSTAIN','tool':None,'arguments':None}
CAPTURED=json.loads((ROOT/'tests/nlip_phase2b5b/captured_invalid.json').read_bytes())
CASES=[(CAPTURED,False),({'outcome':'ABSTAIN','tool':'send_report','arguments':None},False),
 (ABSTAIN,True),({**VALID,'arguments':None},False),({**VALID,'tool':'other'},False),(VALID,True),
 ({**VALID,'outcome':'UNKNOWN'},False),({**VALID,'extra':1},False),
 ({**VALID,'arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid','extra':1}},False)]
for field, limit in [('project_id',64),('recipient',128)]:
 for identifier in ('', 'x'*(limit+1), 'x y', 'x/y', 'x\n'):
  CASES.append(({**VALID,'arguments':{**VALID['arguments'],field:identifier}},False))

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
 def deny(*args,**kwargs):raise AssertionError('NETWORK_FORBIDDEN')
 monkeypatch.setattr(socket,'socket',deny);monkeypatch.setattr(socket,'getaddrinfo',deny)
 monkeypatch.setattr(a.urllib.request,'build_opener',deny)

@pytest.mark.parametrize('value,accepted',CASES)
def test_schema_and_actual_adapter_agree(value,accepted):
 Draft202012Validator.check_schema(a.ALIGNED_SCHEMA)
 assert Draft202012Validator(a.ALIGNED_SCHEMA).is_valid(value)==accepted
 envelope=json.dumps({'model':a.JETSTREAM_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()
 io=a.ScriptedDirectIO([envelope]);transport=a.JetstreamDirectTransport(provider='jetstream2_direct',model=a.JETSTREAM_MODEL,offline_io=io)
 adapter=a.TypedModelAdapter(a.ModelConfig(a.JETSTREAM_MODEL,enable_thinking=False,schema_variant='aligned-v1'),transport)
 msg=parse_message(json.dumps(M['task']).encode())
 if accepted:
  assert adapter.propose(msg,TypedContext(())) is not None
 else:
  with pytest.raises(a.ModelError,match='MALFORMED_RESPONSE'):adapter.propose(msg,TypedContext(()))
 assert len(io.calls)==1
 request=io.calls[0][2]
 assert hashlib.sha256(request).hexdigest()==M['registered_request_sha256']
 payload=json.loads(request)
 assert payload['response_format']['json_schema']['schema']==a.ALIGNED_SCHEMA
 assert M['output_schema']==a.ALIGNED_SCHEMA
 assert M['request_schema']['response_format']['json_schema']['schema']==a.ALIGNED_SCHEMA
 assert M['registered_request']==payload
 assert payload['chat_template_kwargs']=={'enable_thinking':False} and payload['max_completion_tokens']==256
 assert io.calls[0][0]==a.JETSTREAM_ENDPOINT


def test_predecessor_frozen_and_old_request_unchanged():
 raw=(ROOT/'docs/research/phase2-provider-v2/manifest-v2-final-r1.json').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='08a142369630fd8d80b49387d259677d9cf7455337dad726e881bb789a240685'
 assert M['predecessor_v3_compatibility_sha256']=='6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc'
 assert M['predecessor_v3_smoke_sha256']=='ac94d2a732d604e03d45d0ec5e3ee9932303c26ea235820869aac43834613da7'
 for path,expected in [('docs/research/phase2b5a/compatibility-v1.json',M['predecessor_v3_compatibility_sha256']),('docs/research/phase2b5a/smoke-v2.json',M['predecessor_v3_smoke_sha256'])]:
  assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected
 msg=parse_message(json.dumps(M['task']).encode())
 old,_=a.render_request(a.ModelConfig(a.JETSTREAM_MODEL,enable_thinking=False),msg,TypedContext(()))
 assert hashlib.sha256(old).hexdigest()=='76d31918876ab6094ed9e35338eff2752f1dffeee3c35896dc150c2a94e3bd3a'
