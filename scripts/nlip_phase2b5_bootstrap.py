"""Pre-import selection for one separately reviewed Phase 2B-5 Linux release.

Run with the exact repository interpreter -I -S -B. The invocation's accepted
inventory digest is supplied by the supported execution command, never learned
from an adjacent file. This does not authenticate owner/platform permission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def need(condition, code):
    if not condition:raise RuntimeError(code)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


INVENTORY_V3 = 'docs/research/phase2b5a/inventory-smoke-v2.json'
INVENTORY_V4 = 'docs/research/phase2b5e/inventory-v4-linux-v1.json'
INVENTORY_V5 = 'docs/research/phase2b5g/inventory-v5-linux-v1.json'
INVENTORY_FORMATS = {'phase2b5a-linux-package-v1', 'phase2b5e-v4-linux-package-v1',
                     'phase2b5g-v5-linux-package-v1'}


def preimport(root, expected_digest, inventory_name=INVENTORY_V3):
    need(sys.platform=='linux' and sys.flags.isolated and sys.flags.no_site and
         sys.dont_write_bytecode,'ISOLATED_NO_SITE_LINUX_REQUIRED')
    need(set(os.environ)<= {'HOME','PATH','LANG','LC_ALL'},'UNTRUSTED_LAUNCH_ENVIRONMENT')
    root=Path(root)
    need(root.is_absolute() and root.resolve()==root,'SOURCE_SELECTION')
    need(Path(__file__).resolve()==root/'scripts/nlip_phase2b5_bootstrap.py','BOOTSTRAP_SELECTION')
    for node in (root,*root.parents,root/'.venv'):
        need(node.is_dir() and not node.is_symlink() and node.stat().st_uid in (0,os.geteuid()) and
             not stat.S_IMODE(node.stat().st_mode)&0o022,'SOURCE_ANCESTOR')
    # Under -S on Python 3.12 sys.prefix is the base prefix until site runs.
    # Select the venv from sys.executable and pyvenv.cfg before loading any site.
    venv=root/'.venv'
    need(Path(sys.executable).parent==venv/'bin' and
         'include-system-site-packages = false' in (venv/'pyvenv.cfg').read_text(),
         'VENV_SELECTION')
    need(inventory_name in (INVENTORY_V3, INVENTORY_V4, INVENTORY_V5),
         'PACKAGE_INVENTORY_SELECTION')
    path=root/inventory_name
    need(not path.is_symlink() and sha(path)==expected_digest,'PACKAGE_IDENTITY')
    inventory=json.loads(path.read_bytes())
    need(inventory['format'] in INVENTORY_FORMATS and inventory['root']==str(root),
         'PACKAGE_SELECTION')
    need(sha(Path(sys.executable).resolve())==inventory['python']['sha256'] and
         sys.version==inventory['python']['version'],'RUNTIME_SELECTION')
    for name,digest in inventory['files'].items():
        source=root/name
        need(not source.is_symlink() and source.resolve().is_relative_to(root) and sha(source)==digest,
             'SOURCE_BYTES')
    for directory in (root/'src',root/'scripts'):
        for source in directory.rglob('*'):
            need(not source.is_symlink(),'SOURCE_SYMLINK')
            if source.is_file():need(str(source.relative_to(root)) in inventory['files'],'EXTRA_SOURCE_FILE')
    sites=list((venv/'lib').glob('python*/site-packages'))
    need(len(sites)==1 and sites[0].resolve().is_relative_to(venv),'SITE_SELECTION')
    # Owner-authorized reuse of the unchanged, previously qualified installation.
    # Revalidate its qualification/configuration and metadata, without another
    # full 3,038-file sweep. Native/interpreter/trust changes still reject below.
    need(inventory['qualification_sha256']=='d5bb560abe3710645efc4611e7dd272129c3429a9464a42b67044a46c1395dbc' and
         sha(root.parent/'linux-runtime-v3.json')==inventory['qualification_sha256'],
         'PREVIOUS_RUNTIME_BINDING')
    cfg=inventory['isolation']['pyvenv_cfg']
    need(sha(cfg['path'])==cfg['sha256'],'VENV_CONFIG')
    for distribution in inventory['distributions']:
        # Locate only the already qualified metadata records; no site code runs.
        name=distribution['name'].lower().replace('-','_')
        candidates=[p for p in sites[0].glob('*.dist-info') if p.name.lower().startswith(name+'-')]
        need(len(candidates)==1,'DISTRIBUTION_METADATA_SELECTION')
        for filename in distribution['metadata_sha256']:
            metadata=candidates[0]/filename
            need(not metadata.is_symlink() and sha(metadata)==inventory['installed_files'][str(metadata)],
                 'DISTRIBUTION_METADATA_BYTES')
    need(not list(sites[0].glob('*.pth')) and
         not any((sites[0]/name).exists() for name in ('sitecustomize.py','usercustomize.py')),
         'SITE_HOOK')
    for name,digest in inventory['mapped_shared_libraries'].items():need(sha(name)==digest,'NATIVE_BYTES')
    for name,record in inventory['native_modules'].items():
        if record['kind']=='BUILTIN':
            need(name in sys.builtin_module_names and record['module']==name and
                 record['interpreter_realpath']==str(Path(sys.executable).resolve()) and
                 record['interpreter_sha256']==inventory['python']['sha256'],'BUILTIN_IDENTITY')
        else:
            need(record['kind']=='EXTENSION' and sha(record['path'])==record['sha256'],'NATIVE_BYTES')
    need(sha(inventory['trust']['cafile'])==inventory['trust']['cafile_sha256'],'TRUST_BYTES')
    # No site.main(), .pth, user/custom hooks or competing source tree executes.
    sys.prefix=sys.exec_prefix=str(venv)
    sys.path[:0]=[str(root/'src'),str(root),str(sites[0])]
    return inventory


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('verify','fake-qualify','fake-qualify-v3','fake-qualify-smoke',
        'fake-qualify-v4-hosted','first-cell','first-cell-v3','smoke',
        'v4-hosted-first-cell','v4-hosted-smoke',
        'v5-hosted-first-cell','v5-hosted-smoke','fake-qualify-v5-hosted'))
    parser.add_argument('--package-digest',required=True)
    parser.add_argument('--binding-sha256')
    parser.add_argument('--inventory',choices=('v3','v4','v5'),default='v3')
    args=parser.parse_args(argv)
    os.umask(0o077)
    root=Path(__file__).resolve().parents[1]
    inventory_name=(INVENTORY_V5 if args.inventory=='v5' else
                    INVENTORY_V4 if args.inventory=='v4' else INVENTORY_V3)
    preimport(root,args.package_digest,inventory_name)
    from scripts import nlip_phase2b2_launcher as launcher
    if args.inventory=='v4':launcher.INVENTORY=launcher.V4_INVENTORY
    if args.inventory=='v5':launcher.INVENTORY=launcher.V5_INVENTORY
    inventory=launcher.verify_package(args.package_digest)
    from scripts.nlip_phase2b1_pilot import Pilot
    launcher.verify_loaded_sources(inventory)
    if args.action=='verify':
        print(json.dumps({'status':'LINUX_PACKAGE_VERIFIED','model_requests':0}))
    elif args.action=='fake-qualify-v4-hosted':
        import socket,tempfile,time
        from memlife.nlip import model_adapter as m
        need(args.inventory=='v4','V4_INVENTORY_REQUIRED')
        # Buffered HTTP fixtures only. Sockets stay denied, so a genuine
        # transport attempt would fail the qualification rather than send.
        def denied(*a,**kw):raise RuntimeError('QUALIFICATION_NETWORK_DENIED')
        socket.socket=denied;socket.getaddrinfo=denied
        value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{
            'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        raw=json.dumps({'id':None,'model':launcher.DEFAULT_MODEL,'usage':None,
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()
        with tempfile.TemporaryDirectory(prefix='hosted-fake-only-',dir=root.parent) as directory:
            parent=Path(directory);launcher.PROTOCOL_LEDGER=parent/'disposable-reservations.sqlite'
            deployment=parent/'deployment';deployment.mkdir(mode=0o700)
            for name in ('governance','phase2b5d-hosted-compatibility'):
                (deployment/name).mkdir(mode=0o700)
            launcher.PROTOCOL_LEDGER=deployment/'governance/first-cell-reservations.sqlite'
            import sqlite3
            with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
                db.execute('create table reservations(protocol text primary key,cell text not null)')
                db.executemany('insert into reservations values(?,?)',[
                    (launcher.MANIFEST_V2_SHA,'authorized/ON'),
                    ('6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc',
                     'authorized/ON')])
            launcher.PROTOCOL_LEDGER.chmod(0o600)
            from scripts import nlip_phase2b5_execution as execution
            # The retired independent verifier must not be reintroduced; the
            # bounded V2/V3 authority form carries no approval object at all.
            need(not hasattr(execution,'HOSTED_EXECUTION_VERIFIER'),'VERIFIER_UNEXPECTEDLY_INSTALLED')
            need(not hasattr(execution,'HostedExecutionApproval'),'APPROVAL_OBJECT_REINTRODUCED')
            try:
                execution.require_bounded_execution_authority(object())
            except launcher.GateError as error:
                need(str(error)=='HOSTED_EXECUTION_BINDING_REQUIRED','UNEXPECTED_BOUNDED_GATE_ERROR')
            else:raise RuntimeError('BOUNDED_GATE_NOT_ENFORCED')
            try:
                launcher.require_hosted_admission(None)
            except launcher.GateError as error:
                need(str(error)=='HOSTED_ADMISSION_UNAVAILABLE','UNEXPECTED_CLOSED_GATE_ERROR')
            else:raise RuntimeError('CLOSED_GATE_NOT_ENFORCED')
            # A buffered HTTP fixture must never be admitted to the genuine path.
            io=m.BufferedDirectIO([m.TransportResponse(raw,None,200,
                {'content-type':'application/json'},True)])
            try:
                launcher.hosted_first_cell_operator(
                    deployment/'phase2b5d-hosted-compatibility/first-cell.sqlite',
                    authorization_window=(time.time()-1,time.time()+60),
                    package_digest=args.package_digest,offline_io=io,
                    protocol='v4-hosted')
            except launcher.GateError:
                pass
            else:raise RuntimeError('BUFFERED_FIXTURE_ADMITTED')
            with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
                need(db.execute('select count(*) from reservations').fetchone()==(2,),
                     'SIMULATION_CONSUMED_CANONICAL_RESERVATION')
            print(json.dumps({'status':'V4_HOSTED_CLOSED_GATE_QUALIFIED',
                'model_requests':0,'scientific_attempts_consumed':0,
                'closed_gate_enforced':True,'buffered_fixture_classified':True}))
    elif args.action=='fake-qualify-smoke':
        import socket,tempfile,time,sqlite3
        from memlife.nlip.model_adapter import ScriptedDirectIO
        from scripts.nlip_phase2b1_pilot import MANIFEST_SMOKE
        from scripts.nlip_phase2b5_execution import SMOKE_CELLS
        manifest=json.loads(MANIFEST_SMOKE.read_bytes())
        def denied(*a,**kw):raise RuntimeError('QUALIFICATION_NETWORK_DENIED')
        socket.socket=denied;socket.getaddrinfo=denied
        value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        raw=json.dumps({'model':launcher.DEFAULT_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()
        with tempfile.TemporaryDirectory(prefix='smoke-fake-only-',dir=root.parent) as directory:
            parent=Path(directory);launcher.PROTOCOL_LEDGER=parent/'disposable-reservations.sqlite'
            rows={}
            for cell in SMOKE_CELLS:
                io=ScriptedDirectIO([raw]);row=launcher.hosted_first_cell_operator(parent/('-'.join(cell)+'.sqlite'),
                    authorization_window=(time.time()-1,time.time()+60),package_digest=args.package_digest,
                    offline_io=io,protocol='smoke',cell=cell)
                key='/'.join(cell)
                context=json.loads((parent/row['context_evidence']).read_bytes())
                need(context==manifest['model_visible_contexts'][key] and row['admission']==manifest['expected_admission'][key] and len(io.calls)==1,'SMOKE_CONTEXT_QUALIFICATION_FAILED')
                custody=parent/row['policy_evidence'];custody=custody.parent/'custody.sqlite'
                with sqlite3.connect('file:'+str(custody)+'?mode=ro',uri=True) as db:
                    available=[x[0].decode() for x in db.execute('select content from notes')]
                need(available==[x['content'] for x in manifest['available_memory'][cell[0]]],'AVAILABLE_MEMORY_MISMATCH')
                rows[key]={'context':context,'admission':row['admission'],'request_sha256':row['prompt_sha256'],'available_memory':available}
            from memlife.nlip.model_adapter import JetstreamDirectTransport
            offline=Pilot(parent/'offline-OFF.sqlite',JetstreamDirectTransport(provider='jetstream2_direct',model=launcher.DEFAULT_MODEL,offline_io=ScriptedDirectIO([raw])),protocol='smoke').run('misleading','OFF')
            need(offline['prompt_sha256']==rows['misleading/DIAGNOSTIC']['request_sha256'],'OFF_DIAGNOSTIC_NOT_EQUIVALENT')
            print(json.dumps({'status':'FOUR_CELL_CONTEXT_QUALIFICATION_PASS','rows':rows,'OFF_DIAGNOSTIC_equivalent':True,
                'model_requests':0,'scientific_attempts_consumed':0},sort_keys=True))
    elif args.action in ('fake-qualify','fake-qualify-v3'):
        # Disposable process-shared ledger; never the scientific ledger.
        import tempfile,time
        from memlife.nlip.model_adapter import ScriptedDirectIO
        with tempfile.TemporaryDirectory(prefix='fake-only-',dir=root.parent) as directory:
            parent=Path(directory);launcher.PROTOCOL_LEDGER=parent/'disposable-reservations.sqlite'
            proposal={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{
                'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
            response=json.dumps({'model':launcher.DEFAULT_MODEL,'choices':[{'finish_reason':'stop',
                'message':{'content':json.dumps(proposal)}}]}).encode()
            # Deny all socket construction for this qualification process.
            import socket
            def denied(*a,**kw):raise RuntimeError('QUALIFICATION_NETWORK_DENIED')
            socket.socket=denied;socket.getaddrinfo=denied
            io=ScriptedDirectIO([response])
            row=launcher.hosted_first_cell_operator(parent/'fake.sqlite',
                authorization_window=(time.time()-1,time.time()+60),
                package_digest=args.package_digest,offline_io=io,protocol='v3' if args.action.endswith('v3') else 'v2')
            need(row['delivered'] is True and len(io.calls)==1,'FAKE_QUALIFICATION_FAILED')
            try:
                launcher.hosted_first_cell_operator(parent/'second.sqlite',
                    authorization_window=(time.time()-1,time.time()+60),
                    package_digest=args.package_digest,offline_io=io,protocol='v3' if args.action.endswith('v3') else 'v2')
            except launcher.GateError as error:need(str(error)=='FIRST_CELL_ALREADY_RESERVED','WRONG_DUPLICATE_REJECTION')
            else:raise RuntimeError('DUPLICATE_NOT_REJECTED')
            print(json.dumps({'status':'LINUX_FIRST_CELL_FAKE_PASS','model_requests':0,
                'scientific_attempts_consumed':0,'scripted_calls':len(io.calls),
                'duplicate_reservation_rejected':True}))
    elif args.action=='fake-qualify-v5-hosted':
        import socket,tempfile,time
        from memlife.nlip import model_adapter as m
        need(args.inventory=='v5','V5_INVENTORY_REQUIRED')
        def denied(*a,**kw):raise RuntimeError('QUALIFICATION_NETWORK_DENIED')
        socket.socket=denied;socket.getaddrinfo=denied
        value={'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{
            'project_id':'pilot-project','recipient':'authorized@example.invalid'}}
        raw=json.dumps({'id':None,'model':launcher.DEFAULT_MODEL,'usage':None,
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}).encode()
        with tempfile.TemporaryDirectory(prefix='v5-fake-only-',dir=root.parent) as directory:
            parent=Path(directory)
            deployment=parent/'deployment';deployment.mkdir(mode=0o700)
            for name in ('governance','phase2b5g-hosted-compatibility'):
                (deployment/name).mkdir(mode=0o700)
            launcher.PROTOCOL_LEDGER=deployment/'governance/first-cell-reservations.sqlite'
            import sqlite3
            with sqlite3.connect(launcher.PROTOCOL_LEDGER) as db:
                db.execute('create table reservations(protocol text primary key,cell text not null)')
                db.executemany('insert into reservations values(?,?)',[
                    (launcher.MANIFEST_V2_SHA,'authorized/ON'),
                    ('6880f8b21824554b797df6ccaf758ccf7d423e24561aa0f1d9c721f3b1dd94bc',
                     'authorized/ON')])
            launcher.PROTOCOL_LEDGER.chmod(0o600)
            from scripts import nlip_phase2b5_execution as execution
            need(not hasattr(execution,'HOSTED_EXECUTION_VERIFIER'),'VERIFIER_UNEXPECTEDLY_INSTALLED')
            need(not hasattr(execution,'HostedExecutionApproval'),'APPROVAL_OBJECT_REINTRODUCED')
            # The successor must not inherit the consumed V4 protocol identity.
            need(execution.Phase2B5V5HostedExecution.protocol!=
                 execution.Phase2B5V4HostedExecution.protocol,'SUCCESSOR_PROTOCOL_REUSED')
            need(execution.Phase2B5V5HostedSmokeExecution.protocol!=
                 execution.Phase2B5V4HostedSmokeExecution.protocol,'SUCCESSOR_SMOKE_PROTOCOL_REUSED')
            try:
                launcher.require_hosted_admission(None)
            except launcher.GateError as error:
                need(str(error)=='HOSTED_ADMISSION_UNAVAILABLE','UNEXPECTED_CLOSED_GATE_ERROR')
            else:raise RuntimeError('CLOSED_GATE_NOT_ENFORCED')
            # A buffered HTTP fixture must never enter the genuine V5 path.
            io=m.BufferedDirectIO([m.TransportResponse(raw,None,200,
                {'content-type':'application/json'},True)])
            before=sqlite3.connect(launcher.PROTOCOL_LEDGER).execute(
                'select count(*) from reservations').fetchone()[0]
            try:
                launcher.hosted_first_cell_operator(
                    deployment/'phase2b5g-hosted-compatibility/first-cell.sqlite',
                    authorization_window=(time.time()-1,time.time()+60),
                    package_digest=args.package_digest,offline_io=io,protocol='v5-hosted')
            except launcher.GateError:
                pass
            else:raise RuntimeError('BUFFERED_FIXTURE_ADMITTED')
            after=sqlite3.connect(launcher.PROTOCOL_LEDGER).execute(
                'select count(*) from reservations').fetchone()[0]
            need(after==before,'SIMULATION_CONSUMED_CANONICAL_RESERVATION')
            print(json.dumps({'status':'V5_HOSTED_CLOSED_GATE_QUALIFIED',
                'model_requests':0,'scientific_attempts_consumed':0,
                'closed_gate_enforced':True,'successor_protocol':execution.Phase2B5V5HostedExecution.protocol,
                'successor_smoke_protocol':execution.Phase2B5V5HostedSmokeExecution.protocol},
                sort_keys=True))
    elif args.action in ('v5-hosted-first-cell','v5-hosted-smoke'):
        # Bounded V5 successor execution: the successor instruction is the only
        # changed variable, so the same genuine transport, canonical ledger and
        # exact-binding gates apply unchanged.
        need(args.inventory=='v5','V5_INVENTORY_REQUIRED')
        need(args.binding_sha256 is not None,'EXACT_BINDING_DIGEST_REQUIRED')
        from scripts.nlip_phase2b5_execution import (DEPLOYMENT,run_first_cell,run_smoke,
            Phase2B5V5HostedExecution,Phase2B5V5HostedSmokeExecution)
        if args.action=='v5-hosted-first-cell':
            run_first_cell(DEPLOYMENT/Phase2B5V5HostedExecution.binding_name,
                           args.binding_sha256,protocol='v5-hosted')
        else:
            run_smoke(DEPLOYMENT/Phase2B5V5HostedSmokeExecution.binding_name,
                      args.binding_sha256,protocol='v5-hosted-smoke')
    elif args.action in ('v4-hosted-first-cell','v4-hosted-smoke'):
        # Bounded V4 hosted execution: exact binding, canonical ledger and the
        # genuine transport only. No offline I/O is accepted on this path.
        need(args.inventory=='v4','V4_INVENTORY_REQUIRED')
        need(args.binding_sha256 is not None,'EXACT_BINDING_DIGEST_REQUIRED')
        from scripts.nlip_phase2b5_execution import (DEPLOYMENT,run_first_cell,run_smoke,
            Phase2B5V4HostedExecution,Phase2B5V4HostedSmokeExecution)
        if args.action=='v4-hosted-first-cell':
            run_first_cell(DEPLOYMENT/Phase2B5V4HostedExecution.binding_name,
                           args.binding_sha256,protocol='v4-hosted')
        else:
            run_smoke(DEPLOYMENT/Phase2B5V4HostedSmokeExecution.binding_name,
                      args.binding_sha256,protocol='v4-hosted-smoke')
    else:
        need(args.binding_sha256 is not None,'EXACT_BINDING_DIGEST_REQUIRED')
        if args.action=='smoke':
            from scripts.nlip_phase2b5_execution import DEPLOYMENT,run_smoke,Phase2B5SmokeExecution
            run_smoke(DEPLOYMENT/Phase2B5SmokeExecution.binding_name,args.binding_sha256)
            return 0
        from scripts.nlip_phase2b5_execution import DEPLOYMENT,run_first_cell,Phase2B5AExecution
        amended=args.action=='first-cell-v3'
        run_first_cell(DEPLOYMENT/(Phase2B5AExecution.binding_name if amended else 'first-cell-execution-v1.json'),
                       args.binding_sha256,protocol='v3' if amended else 'v2')
    return 0


if __name__=='__main__':raise SystemExit(main())
