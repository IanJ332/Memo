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


def preimport(root, expected_digest):
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
    path=root/'docs/research/phase2b5a/inventory-smoke-v2.json'
    need(not path.is_symlink() and sha(path)==expected_digest,'PACKAGE_IDENTITY')
    inventory=json.loads(path.read_bytes())
    need(inventory['format']=='phase2b5a-linux-package-v1' and inventory['root']==str(root),
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
    parser.add_argument('action',choices=('verify','fake-qualify','fake-qualify-v3','fake-qualify-smoke','first-cell','first-cell-v3','smoke'))
    parser.add_argument('--package-digest',required=True)
    parser.add_argument('--binding-sha256')
    args=parser.parse_args(argv)
    os.umask(0o077)
    root=Path(__file__).resolve().parents[1]
    preimport(root,args.package_digest)
    from scripts import nlip_phase2b2_launcher as launcher
    inventory=launcher.verify_package(args.package_digest)
    from scripts.nlip_phase2b1_pilot import Pilot
    launcher.verify_loaded_sources(inventory)
    if args.action=='verify':
        print(json.dumps({'status':'LINUX_PACKAGE_VERIFIED','model_requests':0}))
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
