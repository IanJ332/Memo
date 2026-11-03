"""Negative trust-boundary and terminal-classification tests; no provider I/O."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import nlip_phase2b5_bootstrap as bootstrap
from scripts import nlip_phase2b5_execution as execution
from scripts import nlip_phase2b2_launcher as launcher


def test_default_and_untyped_hosted_admission_stay_closed():
    for supplied in (None, True, object(), {'approved': True}):
        with pytest.raises(launcher.GateError, match='HOSTED_ADMISSION_UNAVAILABLE'):
            launcher.require_hosted_admission(supplied)


def test_no_compatible_promotion_for_http_schema_identity_or_unknown():
    assert execution.compatibility({'error':'PROVIDER_HTTP_ERROR'})=='PROVIDER_HTTP_ERROR'
    assert execution.compatibility({'error':'MALFORMED_RESPONSE'})=='MALFORMED_RESPONSE'
    assert execution.compatibility({'error':'MODEL_IDENTITY_MISMATCH'})=='MODEL_IDENTITY_MISMATCH'
    assert execution.compatibility({'error':'TIMEOUT'})=='TIMEOUT'
    assert execution.compatibility({'error':'EVIDENCE_WRITE_FAILURE'})=='EVIDENCE_FAILURE'
    assert execution.compatibility({})=='UNKNOWN'


@pytest.fixture
def selected(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir(mode=0o700)
    for sub in ('scripts','src','docs/research/phase2-provider-v2','.venv/bin','.venv/lib/python3.12/site-packages'):
        (root/sub).mkdir(parents=True,exist_ok=True)
    script=root/'scripts/nlip_phase2b5_bootstrap.py';script.write_bytes(b'# frozen bootstrap fixture\n')
    interpreter=root/'.venv/bin/python';interpreter.write_bytes(b'interpreter fixture')
    (root/'.venv/pyvenv.cfg').write_text('include-system-site-packages = false\n')
    trust=root/'trust.pem';trust.write_bytes(b'trust fixture')
    installed=root/'.venv/lib/python3.12/site-packages/module.py';installed.write_bytes(b'# dependency fixture\n')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inventory={'format':'phase2b5-linux-package-v1','root':str(root),
      'python':{'sha256':digest(interpreter),'version':'fixture-version'},
      'files':{'scripts/nlip_phase2b5_bootstrap.py':digest(script)},
      'installed_files':{str(installed):digest(installed)},'mapped_shared_libraries':{},
      'native_modules':{},'trust':{'cafile':str(trust),'cafile_sha256':digest(trust)}}
    path=root/'docs/research/phase2-provider-v2/inventory-phase2b5-linux-v1.json'
    path.write_text(json.dumps(inventory))
    monkeypatch.setattr(bootstrap,'__file__',str(script))
    monkeypatch.setattr(bootstrap,'sys',SimpleNamespace(platform='linux',flags=SimpleNamespace(isolated=1,no_site=1),
      dont_write_bytecode=True,executable=str(interpreter),version='fixture-version',path=[],prefix='base',exec_prefix='base'))
    monkeypatch.setattr(bootstrap,'os',SimpleNamespace(environ={},geteuid=os.geteuid))
    return root,path,digest(path),installed


def test_preimport_rejects_changed_source_before_dependency_selection(selected):
    root,path,digest,installed=selected
    (root/'scripts/nlip_phase2b5_bootstrap.py').write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='SOURCE_BYTES'):bootstrap.preimport(root,digest)
    assert bootstrap.sys.path==[]


def test_preimport_rejects_changed_dependency_and_extra_source(selected):
    root,path,digest,installed=selected
    installed.write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='INSTALLED_BYTES'):bootstrap.preimport(root,digest)
    assert bootstrap.sys.path==[]


def test_preimport_rejects_unrecorded_source_and_environment(selected,monkeypatch):
    root,path,digest,installed=selected
    (root/'src/unreviewed.py').write_bytes(b'')
    with pytest.raises(RuntimeError,match='EXTRA_SOURCE_FILE'):bootstrap.preimport(root,digest)
    monkeypatch.setattr(bootstrap.os,'environ',{'LD_PRELOAD':'unreviewed'})
    with pytest.raises(RuntimeError,match='UNTRUSTED_LAUNCH_ENVIRONMENT'):bootstrap.preimport(root,digest)
    assert bootstrap.sys.path==[]


def test_preimport_rejects_unrecorded_site_hook(selected):
    root,path,digest,installed=selected
    (installed.parent/'injection.pth').write_bytes(b'import unreviewed\n')
    with pytest.raises(RuntimeError,match='EXTRA_SITE_FILE'):bootstrap.preimport(root,digest)
    assert bootstrap.sys.path==[]

@pytest.fixture
def exact_binding(tmp_path,monkeypatch):
    import time
    deployment=tmp_path/'deployment';deployment.mkdir(mode=0o700)
    source=deployment/'source';source.mkdir(mode=0o700)
    (source/'scripts').mkdir()
    for sub in ('first-cell','governance'):(deployment/sub).mkdir(mode=0o700)
    evidence=deployment/'first-cell/first-cell.sqlite'
    ledger=deployment/'governance/first-cell-reservations.sqlite'
    inventory=source/'inventory.json';inventory.write_bytes(b'exact package fixture')
    monkeypatch.setattr(execution,'DEPLOYMENT',deployment)
    monkeypatch.setattr(execution,'SOURCE',source)
    monkeypatch.setattr(execution,'EVIDENCE',evidence)
    monkeypatch.setattr(execution,'LEDGER',ledger)
    monkeypatch.setattr(execution,'__file__',str(source/'scripts/nlip_phase2b5_execution.py'))
    monkeypatch.setattr(launcher,'ROOT',source)
    monkeypatch.setattr(launcher,'INVENTORY',inventory)
    monkeypatch.setattr(launcher,'PROTOCOL_LEDGER',ledger)
    now=time.time()
    binding={'version':'phase2b5-first-cell-execution-v1','protocol':'phase2-provider-v2-first-cell-2',
      'manifest_sha256':execution.MANIFEST_SHA,'provider':'jetstream2_direct','model':execution.MODEL,
      'endpoint':execution.ENDPOINT,'max_attempts':1,'retries':0,'fallbacks':0,'scenario':'authorized',
      'admission':'ON','external_delivery':'PROHIBITED','evidence':str(evidence),'ledger':str(ledger),
      'package_digest':execution.sha(inventory),'start_utc':now-1,'end_utc':now+60}
    path=deployment/'first-cell-execution-v1.json'
    def prepare(changes=None):
        current=dict(binding);current.update(changes or {})
        path.write_text(json.dumps(current));path.chmod(0o600)
        return execution.Phase2B5Execution(path,execution.sha(path)),current,path
    return prepare,evidence,ledger

@pytest.mark.parametrize('changes',[
 {'model':'other'},{'endpoint':'https://other.invalid'},{'manifest_sha256':'0'*64},
 {'max_attempts':2},{'retries':1},{'fallbacks':1},{'admission':'OFF'},
 {'evidence':'/unbound/evidence'},{'ledger':'/unbound/ledger'},
 {'start_utc':0,'end_utc':1},{'start_utc':0,'end_utc':100000000000},
 {'external_delivery':'ALLOWED'}])
def test_execution_scope_rejects_unbound_or_expired_values(exact_binding,changes):
    prepare,evidence,ledger=exact_binding;obj,b,path=prepare(changes)
    with pytest.raises(launcher.GateError):obj.check(evidence,(b['start_utc'],b['end_utc']),b['package_digest'])
    assert not ledger.exists() and not evidence.exists()


def test_exact_binding_checks_then_rejects_changed_bytes(exact_binding):
    prepare,evidence,ledger=exact_binding;obj,b,path=prepare()
    obj.check(evidence,(b['start_utc'],b['end_utc']),b['package_digest'])
    path.write_text(path.read_text()+' ')
    with pytest.raises(launcher.GateError,match='EXECUTION_BINDING_MISMATCH'):
        obj.check(evidence,(b['start_utc'],b['end_utc']),b['package_digest'])
    assert not ledger.exists() and not evidence.exists()


def test_insecure_or_consumed_ledger_rejects_before_evidence(exact_binding):
    import sqlite3
    prepare,evidence,ledger=exact_binding;obj,b,path=prepare()
    with sqlite3.connect(ledger) as db:
        db.execute('create table reservations(protocol text primary key,cell text)')
        db.execute('insert into reservations values(?,?)',(execution.MANIFEST_SHA,'authorized/ON'))
    ledger.chmod(0o644)
    with pytest.raises(launcher.GateError,match='LEDGER_INVALID'):
        obj.check(evidence,(b['start_utc'],b['end_utc']),b['package_digest'])
    ledger.chmod(0o600)
    with pytest.raises(launcher.GateError,match='FIRST_CELL_ALREADY_RESERVED'):
        obj.check(evidence,(b['start_utc'],b['end_utc']),b['package_digest'])
    assert not evidence.exists()
