"""One-parameter successor contract; scripted provider I/O only."""
import hashlib,io,json,socket,sqlite3,time,urllib.error
from pathlib import Path
import pytest
from scripts import nlip_phase2b2_launcher as l
from scripts import nlip_phase2b1_pilot as p
from scripts import nlip_phase2b5_execution as execution
from memlife.nlip import model_adapter as a
from memlife.nlip.admission import TypedContext
from memlife.nlip.wire import parse_message

ROOT=Path(__file__).resolve().parents[2]
NEW_SHA='6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc'

def response(kind='valid'):
    value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
    if kind=='abstain':value={'outcome':'ABSTAIN','tool':None,'arguments':None}
    return json.dumps({'model':'wrong' if kind=='identity' else a.JETSTREAM_MODEL,
       'choices':[{'finish_reason':'length' if kind=='length' else 'stop',
          'message':{'content':None if kind=='null' else json.dumps(value)}}],
       'usage':{'prompt_tokens':85,'completion_tokens':30,'total_tokens':115}}).encode()

@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args,**kwargs):raise AssertionError('NETWORK_PROHIBITED')
    monkeypatch.setattr(socket,'socket',denied);monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(a.urllib.request,'build_opener',denied)

@pytest.fixture
def operator(tmp_path,monkeypatch):
    if not (ROOT/'docs/research/phase2-provider-v2/inventory-phase2b5-macos-v1.json').is_file():
        pytest.skip('requires private historical execution artifacts')
    old=json.loads((ROOT/'docs/research/phase2-provider-v2/inventory-phase2b5-macos-v1.json').read_bytes())
    names=set(old['files'])|{'docs/research/phase2b5a/compatibility-v1.json','tests/nlip_phase2b5a/test_nonthinking.py'}
    current=dict(old,format='phase2b5a-macos-offline-test',files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)})
    inventory=tmp_path/'current-inventory.json';inventory.write_text(json.dumps(current))
    ledger=tmp_path/'shared-reservations.sqlite'
    with sqlite3.connect(ledger) as db:
        db.execute('create table reservations(protocol text primary key,cell text not null)')
        db.execute('insert into reservations values(?,?)',(l.MANIFEST_V2_SHA,'authorized/ON'))
    monkeypatch.setattr(l,'INVENTORY',inventory);monkeypatch.setattr(l,'PROTOCOL_LEDGER',ledger)
    def invoke(kind='valid',window=None):
        fake=a.ScriptedDirectIO([response(kind)])
        original=a.ScriptedDirectIO.read
        def read(self,*args):
            with sqlite3.connect(ledger) as db:
                assert set(db.execute('select protocol from reservations'))=={(l.MANIFEST_V2_SHA,),(NEW_SHA,)}
            if kind=='http':raise urllib.error.HTTPError(a.JETSTREAM_ENDPOINT,400,'synthetic',{},io.BytesIO(b'{"error":"unsupported synthetic"}'))
            if kind=='timeout':raise a.ModelError('TIMEOUT')
            return original(self,*args)
        monkeypatch.setattr(a.ScriptedDirectIO,'read',read)
        now=time.time()
        row=l.hosted_first_cell_operator(tmp_path/'new-evidence.sqlite',package_digest=l.digest(inventory),
              authorization_window=window or (now-1,now+60),offline_io=fake,protocol='v3')
        return row,fake,ledger
    return invoke,tmp_path,ledger


def test_exact_successor_body_only_adds_top_level_thinking_switch():
    if not p.MANIFEST_V3.is_file():
        pytest.skip('requires private historical execution manifest')
    m=json.loads(p.MANIFEST_V3.read_bytes());assert hashlib.sha256(p.MANIFEST_V3.read_bytes()).hexdigest()==NEW_SHA
    message=parse_message(json.dumps(m['task']).encode());context=TypedContext(())
    old,_=a.render_request(a.ModelConfig(a.JETSTREAM_MODEL),message,context)
    new,_=a.render_request(a.ModelConfig(a.JETSTREAM_MODEL,enable_thinking=False),message,context)
    old_json=json.loads(old);expected=dict(old_json,chat_template_kwargs={'enable_thinking':False})
    assert json.loads(new)==expected==m['registered_request']
    assert 'extra_body' not in expected and expected['max_completion_tokens']==256
    assert expected['response_format']==old_json['response_format']
    assert hashlib.sha256(old).hexdigest()=='e8249582f15842a4f5b9ece4654ec2a315296a64eac7589387c7a1dcb845ea93'
    assert hashlib.sha256(new).hexdigest()==m['registered_request_sha256']
    assert a.JETSTREAM_ENDPOINT==m['endpoint'] and a.JETSTREAM_MODEL==m['model']
    with pytest.raises(ValueError):a.ModelConfig(a.JETSTREAM_MODEL,enable_thinking=True)


def test_new_reservation_precedes_send_and_old_remains_consumed(operator):
    invoke,tmp,ledger=operator;row,fake,_=invoke()
    assert row['manifest_sha256']==NEW_SHA and row['delivered'] is True
    assert len(fake.calls)==1 and fake.calls[0][0]==a.JETSTREAM_ENDPOINT
    assert json.loads(fake.calls[0][2])['chat_template_kwargs']=={'enable_thinking':False}
    with pytest.raises(l.GateError,match='ALREADY_RESERVED'):l.reserve_first_cell('v2')
    with pytest.raises(l.GateError,match='ALREADY_RESERVED'):l.reserve_first_cell('v3')
    with sqlite3.connect(ledger) as db:assert db.execute('select count(*) from reservations').fetchone()==(2,)
    assert not (tmp/'second.sqlite').exists()

@pytest.mark.parametrize('kind,error',[('http','PROVIDER_HTTP_ERROR'),('null','MALFORMED_RESPONSE'),
  ('length','MALFORMED_RESPONSE'),('identity','MODEL_IDENTITY_MISMATCH'),('timeout','TIMEOUT')])
def test_failures_consumed_once_no_dispatch_or_fallback(operator,kind,error):
    invoke,tmp,ledger=operator;row,fake,_=invoke(kind)
    assert row['error']==error and row['retries']==0 and row['attempt_count']==1
    assert row['dispatch_status']=='NOT_STARTED' and row['delivered'] is False
    assert len(fake.calls)<=1
    if kind=='http':assert row['http_status']==400
    with sqlite3.connect(ledger) as db:assert db.execute('select count(*) from reservations').fetchone()==(2,)


def test_expired_window_rejects_before_new_reservation(operator):
    invoke,tmp,ledger=operator;now=time.time()
    with pytest.raises(l.GateError,match='AUTHORIZATION_EXPIRED'):invoke(window=(now-20,now-10))
    with sqlite3.connect(ledger) as db:assert db.execute('select protocol from reservations').fetchall()==[(l.MANIFEST_V2_SHA,)]
    assert not (tmp/'new-evidence.sqlite').exists()


def test_valid_abstention_has_no_dispatch_and_is_not_utility_success(operator):
    invoke,tmp,ledger=operator;row,fake,_=invoke('abstain')
    assert row['model_outcome']=='ABSTAIN' and row['proposal_validity']=='VALID'
    assert row['task_outcome']=='INAPPROPRIATE_ABSTENTION' and row['dispatch_status']=='NOT_STARTED'
    assert row['delivered'] is False


def test_evidence_write_failure_stops_before_protected_dispatch(operator,monkeypatch):
    original=p.Pilot._private_artifact
    def fail(self,directory,name,body):
        if name=='response.body':raise OSError('synthetic write failure')
        return original(self,directory,name,body)
    monkeypatch.setattr(p.Pilot,'_private_artifact',fail)
    invoke,tmp,ledger=operator;row,fake,_=invoke()
    assert row['error']=='EVIDENCE_WRITE_FAILURE' and row['dispatch_status']=='NOT_STARTED'
    assert row['delivered'] is False
