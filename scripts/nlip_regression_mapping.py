# SPDX-License-Identifier: MIT
"""Verify unchanged test bodies and map every collected historical item."""
import ast, hashlib, json, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/research/nlip-context-admission-phase1-20261029/regression-closure'
REV='b179e2dfdbf0d00d118f4a1c320a53530ff1a3cc'
original=subprocess.check_output(['git','show',REV+':tests/nlip/test_security.py'],cwd=ROOT).decode()
adapted=(ROOT/'tests/nlip_regression/test_historical_adapted.py').read_text()
def functions(source):
    return {n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
a=functions(original); b=functions(adapted)
assert set(a)-set(b)=={'test_off_on_same_proposal_local_sink'} and not set(b)-set(a)
for name,node in b.items(): assert ast.dump(node,include_attributes=False)==ast.dump(a[name],include_attributes=False),name
properties={
 'test_formats_preserved':'NLIP format/subformat/content preserved',
 'test_order_labels_and_case':'ordered parts, untrusted labels and case preserved',
 'test_malformed_messages':'malformed, duplicate, oversized or invalid NLIP rejected',
 'test_control_compatibility_and_token_echo':'control compatibility and token echo preserved',
 'test_deep_message_rejected':'excessive nesting rejected',
 'test_token_validation':'invalid identity/access claims rejected',
 'test_expiration_equal_now_rejected':'token expiry equal to current time rejected',
 'test_invalid_signature_and_id_access_swap':'invalid signatures and swapped token types rejected',
 'test_oidc_config_rejects_external_plaintext':'external plaintext OIDC rejected',
 'test_state_rejection_before_exchange':'bad OAuth state rejected before token exchange',
 'test_callback_replay_and_nonce':'OAuth callback replay and wrong nonce rejected',
 'test_discovery_rejects_cross_host':'cross-host JWKS discovery rejected',
 'test_authorized_send_and_safe_audit':'authorized synthetic dispatch and redacted policy audit',
 'test_unauthorized_recipient':'recipient absent from current policy denied',
 'test_malformed_arguments':'malformed tool arguments denied',
 'test_unknown_tools':'unknown tool denied without synthetic delivery',
 'test_project_principal_and_session_isolation':'project, principal, session and logout isolation',
 'test_update_revoke_and_unrelated_revision':'policy revisions and recipient updates/revocations enforced',
 'test_policy_failure_and_inconsistent_revision':'unavailable or inconsistent policy fails closed',
 'test_direct_dispatch_bypass_rejected':'direct sink and invalid extension registry rejected',
 'test_extension_registration_and_fail_closed':'extension error vetoes and does not leak its message',
 'test_invalid_or_deny_extension':'invalid, stale and denied extension decisions veto',
 'test_transaction_prevents_revocation_window':'policy transaction serializes dispatch and revocation',
 'test_session_expiry_during_extension':'session expiry before commit prevents dispatch',
 'test_http_boundaries':'HTTP credential, origin, session, syntax and tool boundary denies',
 'test_http_persisted_note_attack_labels_and_logout':'persisted ordinary note proposal denied by current policy; logout/isolation',
 'test_http_oidc_callback_and_replay':'OIDC callback cookie security, token secrecy and replay denial',
 'test_off_on_same_proposal_local_sink':'historical defense-off versus defense-on synthetic dispatch',
 'test_model_limits_and_no_retries':'isolated model ledger enforces budgets and no retry',
 'test_unqualified_model_and_unknown_usage_close':'isolated model gate closes on missing qualification/usage',
 'test_model_interface_omits_session_credentials':'legacy flat model serialization omits session credentials and slot cannot be reused',
 'test_null_optional_message_type_rejected':'null optional message type rejected',
 'test_persisted_note_survives_victim_session_change':'persisted same-principal note and updated recipient policy survive session change',
}
assert set(properties)==set(a)
def outcomes(filename):
    nodes=ET.parse(OUT/filename).getroot().findall('.//testcase')
    assert all(not any(x.tag in ('failure','error','skipped') for x in n) for n in nodes)
    return {x.attrib['name'] for x in nodes}
r0=outcomes('r0.xml');r1=outcomes('r1.xml');r4=outcomes('r4.xml')
assert len(r0)==83 and len(r1)==82 and r0-r1=={'test_off_on_same_proposal_local_sink'}
rows=[]
for name in sorted(r0):
    fn=name.split('[',1)[0];node=a[fn]
    uses_harness=any(x in {'harness','authorized'} for x in [z.arg for z in node.args.args]) or any(isinstance(x,ast.Name) and x.id=='engineering_harness' for x in ast.walk(node))
    model=fn=='test_model_interface_omits_session_credentials'
    if fn=='test_off_on_same_proposal_local_sink':
        category='C'; dependency='legacy defense-off harness'; successor=['test_legacy_defense_off_profile_rejected','test_legacy_off_successor_current_gate_denies_old_in_service','test_direct_protected_dispatch_and_recipient_denied']; status='LEGACY_PASS_AND_SUCCESSORS_PASS'; path='Phase 1 rejects tool-gate OFF; reference note proposal passes admission and current tool gate denies old recipient.'; applicable='Gate remains applicable; defense-off experimental outcome is prohibited.'
        assert all(x in r4 for x in successor)
    elif fn in ('test_model_limits_and_no_retries','test_unqualified_model_and_unknown_usage_close'):
        category='C';dependency='isolated historical model ledger';successor=[name];status='ISOLATED_LEGACY_PASS';path='Unchanged test runs against copied test-only legacy ledger; it is not a Phase 1 adapter or service path.';applicable='No model collection is supported in this profile; preserve this property for a later model integration.'
        assert name in r1
    elif model:
        category='C';dependency='legacy flat model adapter and authenticated harness';successor=[name,'test_legacy_flat_model_adapter_cannot_consume_typed_context'];status='ISOLATED_LEGACY_PASS_AND_PROHIBITION_PASS';path='Exact historical assertion runs only with local fake sender; Phase 1 service rejects incompatible flat adapter before sender; no model adapter is supported.';applicable='Credential omission remains a requirement for any future model adapter; no such Phase 1 model path is claimed.'
        assert name in r1 and successor[1] in r4
    else:
        category='B' if uses_harness or fn in ('test_model_limits_and_no_retries','test_unqualified_model_and_unknown_usage_close') else 'A'
        dependency=('phase1_harness: OIDC, SQLite Notes, AdmissionService, typed spy, ProtectedDispatcher' if uses_harness else ('test-only pinned legacy ledger import' if category=='B' else 'unchanged direct primitive test'))
        successor=[name];status='PASS';path=('unchanged original test function against adapted Phase 1 fixture' if uses_harness else 'unchanged original test function against selected Phase 1 primitive or isolated historical ledger')
        applicable='yes';assert name in r1
    rows.append({'original_nodeid':'tests/nlip/test_security.py::'+name,'original_function_line':node.lineno,'original_security_property':properties[fn],
     'original_assertions':[ast.unparse(x.test) for x in ast.walk(node) if isinstance(x,ast.Assert)],'category':category,'fixture_dependency':dependency,
     'applicability':applicable,'required_adaptation':path,'successor_nodeids':[('tests/nlip_regression/test_historical_adapted.py::' if x==name else 'tests/nlip_regression/test_prohibited_paths.py::')+x for x in successor], 'status':status})
result={'historical_revision':REV,'original_source_sha256':hashlib.sha256(original.encode()).hexdigest(),'adapted_source_sha256':hashlib.sha256(adapted.encode()).hexdigest(),
 'original_test_count':len(r0),'adapted_test_count':len(r1),'test_function_ast_identical':True,'rows':rows}
destination=Path(sys.argv[1]) if len(sys.argv)>1 else OUT/'test-mapping.json'
with destination.open('x') as stream: stream.write(json.dumps(result,indent=2,ensure_ascii=True)+'\n')
from collections import Counter
print('mapped',len(rows),dict(Counter(x['category'] for x in rows)))
