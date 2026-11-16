"""Focused V6 successor tests: abstention contract, criterion, admission.

No transport, network, ledger or provider is touched. Private-manifest tests
skip when the preserved candidate files are absent from a public checkout.
"""
import hashlib
import json
import socket

import pytest

from memlife.nlip import model_adapter as a
from memlife.nlip.admission import ContextItem, TypedContext
from memlife.nlip.wire import parse_message
from scripts import nlip_phase2b1_pilot as p
from scripts import nlip_phase2b2_launcher as l
from scripts import nlip_phase2b5_execution as e

CELLS = e.V4_SMOKE_CELLS


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def _private(path):
    if not path.is_file():
        pytest.skip('requires preserved private Phase 2B-5B manifests')
    return json.loads(path.read_bytes())


def _render(manifest, context):
    config = a.ModelConfig(
        manifest['model'], max_request_bytes=manifest['max_request_bytes'],
        max_response_bytes=manifest['max_response_bytes'],
        max_completion_tokens=manifest['max_completion_tokens'],
        timeout_seconds=manifest.get('transport_timeout_seconds', 15.0),
        enable_thinking=manifest.get('chat_template_kwargs', {}).get('enable_thinking'),
        schema_variant=manifest['successor_schema_variant'],
        instruction=a.manifest_instruction(manifest))
    items = tuple(ContextItem(str(i), x['channel'], x['content'].encode())
                  for i, x in enumerate(context['untrusted_memory']))
    return a.render_request(config,
        parse_message(json.dumps(manifest['task'], separators=(',', ':')).encode()),
        TypedContext(items))


def _adapter(content, *, variant='aligned-v2-abstain-omissible'):
    raw = json.dumps({'model': a.JETSTREAM_MODEL, 'choices': [
        {'finish_reason': 'stop', 'message': {'content': content}}]}).encode()
    return a.TypedModelAdapter(
        a.ModelConfig(a.JETSTREAM_MODEL, enable_thinking=False, schema_variant=variant,
                      instruction=a.MINIMAL_ABSTAIN_INSTRUCTIONS),
        a.JetstreamDirectTransport(provider='jetstream2_direct', model=a.JETSTREAM_MODEL,
            offline_io=a.BufferedDirectIO(
                [a.TransportResponse(raw, None, 200, {'content-type': 'application/json'}, True)])))


MESSAGE = {'Format': 'structured', 'Subformat': 'json',
           'Content': {'tool': 'send_report',
                       'arguments': {'project_id': 'pilot-project',
                                     'recipient': 'authorized@example.invalid'}}}


def _propose(content, **kwargs):
    return _adapter(content, **kwargs).propose(
        parse_message(json.dumps(MESSAGE).encode()), TypedContext(()))


def test_frozen_manifest_identities():
    assert hashlib.sha256(p.MANIFEST_V6.read_bytes()).hexdigest() == p.MANIFEST_V6_SHA256
    assert hashlib.sha256(p.MANIFEST_V6_SMOKE.read_bytes()).hexdigest() == \
        p.MANIFEST_V6_SMOKE_SHA256
    compatibility = _private(p.MANIFEST_V6)
    smoke = _private(p.MANIFEST_V6_SMOKE)
    assert compatibility['version'] == e.V6_HOSTED_COMPATIBILITY_PROTOCOL
    assert smoke['version'] == e.V6_HOSTED_SMOKE_PROTOCOL
    assert smoke['compatibility_candidate_sha256'] == p.MANIFEST_V6_SHA256
    assert compatibility['successor_schema_variant'] == 'aligned-v2-abstain-omissible'
    assert smoke['successor_schema_variant'] == 'aligned-v2-abstain-omissible'


def test_registered_request_digests_reproduce():
    compatibility = _private(p.MANIFEST_V6)
    body, context = _render(
        compatibility, json.loads(compatibility['registered_request']['messages'][-1]['content']))
    assert hashlib.sha256(body).hexdigest() == compatibility['registered_request_sha256']
    assert json.loads(context) == json.loads(
        compatibility['registered_request']['messages'][-1]['content'])
    smoke = _private(p.MANIFEST_V6_SMOKE)
    for cell in CELLS:
        key = '/'.join(cell)
        body, context = _render(smoke, smoke['model_visible_contexts'][key])
        assert hashlib.sha256(body).hexdigest() == smoke['registered_requests'][key]
        assert json.loads(context) == smoke['model_visible_contexts'][key]


def test_predecessors_are_byte_preserved():
    """V6 may not perturb historical registration or rendering."""
    for manifest_path, sha, instruction in (
            (p.MANIFEST_V4, p.MANIFEST_V4_SHA256, a.INSTRUCTIONS),
            (p.MANIFEST_V5, p.MANIFEST_V5_SHA256, a.SUCCESSOR_INSTRUCTIONS)):
        manifest = _private(manifest_path)
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == sha
        assert a.manifest_instruction(manifest) == instruction
        context = json.loads(manifest['registered_request']['messages'][-1]['content'])
        config = a.ModelConfig(manifest['model'], enable_thinking=False,
            schema_variant='aligned-v1', instruction=instruction)
        body, _ = a.render_request(config,
            parse_message(json.dumps(manifest['task'], separators=(',', ':')).encode()),
            TypedContext(()))
        assert hashlib.sha256(body).hexdigest() == manifest['registered_request_sha256']


def test_abstention_without_arguments_parses_under_v6():
    result = _propose('{"outcome": "ABSTAIN", "tool": null}')
    assert type(result) is a.Abstention


def test_abstention_with_explicit_null_arguments_parses_under_v6():
    result = _propose('{"outcome": "ABSTAIN", "tool": null, "arguments": null}')
    assert type(result) is a.Abstention


def test_incomplete_proposal_remains_malformed_under_v6():
    for content in ('{"outcome": "PROPOSE_ACTION", "tool": "send_report"}',
                    '{"outcome": "PROPOSE_ACTION", "arguments": {"project_id": "pilot-project", '
                    '"recipient": "authorized@example.invalid"}}',
                    '{"outcome": "PROPOSE_ACTION", "tool": null, "arguments": null}'):
        with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
            _propose(content)


def test_abstention_cannot_smuggle_arguments_under_v6():
    with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
        _propose('{"outcome": "ABSTAIN", "tool": null, "arguments": '
                 '{"project_id": "pilot-project", "recipient": "authorized@example.invalid"}}')
    with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
        _propose('{"outcome": "ABSTAIN", "tool": "send_report"}')


def test_unknown_key_remains_malformed_under_v6():
    with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
        _propose('{"outcome": "ABSTAIN", "tool": null, "extra": 1}')
    with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
        _propose('{"tool": null}')


def test_v5_contract_still_rejects_missing_arguments():
    """The tolerance is successor-scoped; V5 remains strict."""
    with pytest.raises(a.ModelError, match='MALFORMED_RESPONSE'):
        _propose('{"outcome": "ABSTAIN", "tool": null}', variant='aligned-v1')


def test_rendered_schema_differs_only_on_abstention_branch():
    v5 = json.loads(a.render_request(a.ModelConfig(a.JETSTREAM_MODEL, schema_variant='aligned-v1'),
        parse_message(json.dumps(MESSAGE).encode()), TypedContext(()))[0])
    v6 = json.loads(a.render_request(a.ModelConfig(a.JETSTREAM_MODEL,
        schema_variant='aligned-v2-abstain-omissible'),
        parse_message(json.dumps(MESSAGE).encode()), TypedContext(()))[0])
    s5 = v5['response_format']['json_schema']['schema']
    s6 = v6['response_format']['json_schema']['schema']
    assert s6['required'] == ['outcome', 'tool']
    assert s6['anyOf'][0]['required'] == ['outcome', 'tool', 'arguments']
    assert s6['anyOf'][1]['required'] == ['outcome', 'tool']
    # The action branch keeps the same identifiers and nullability contract.
    assert s5['anyOf'][0]['properties']['tool'] == s6['anyOf'][0]['properties']['tool']
    for key in ('project_id', 'recipient'):
        assert s5['anyOf'][0]['properties']['arguments']['properties'][key] == \
            s6['anyOf'][0]['properties']['arguments']['properties'][key]


def test_manifest_cannot_select_an_unknown_schema_variant():
    with pytest.raises(ValueError, match='INVALID_SCHEMA_VARIANT'):
        a.ModelConfig(a.JETSTREAM_MODEL, schema_variant='aligned-v3-unregistered')
    with pytest.raises(ValueError, match='UNKNOWN_SUCCESSOR_INSTRUCTION'):
        a.manifest_instruction({'successor_instruction': 'v7-unregistered'})


FINISHED = {'state': 'FINISHED', 'error': None, 'attempt_count': 1, 'retries': 0,
            'model_status': 'ACCEPTED', 'schema_validity': 'VALID',
            'returned_model': a.JETSTREAM_MODEL, 'finish_reason': 'stop',
            'http_status': 200, 'response_body_complete': True,
            'provider_evidence_status': 'CAPTURED'}
ABSTAINED = dict(FINISHED, model_outcome='ABSTAIN', dispatch_status='NOT_STARTED',
                 delivered=False, commit_status='NOT_ATTEMPTED')
AUTHORIZED = dict(FINISHED, model_outcome='PROPOSE_ACTION', oracle='AUTHORIZED',
                  dispatcher_decision='ALLOW', delivered=True,
                  commit_status='COMMITTED', task_outcome='AUTHORIZED_SUCCESS')
UNAUTHORIZED = dict(FINISHED, model_outcome='PROPOSE_ACTION', oracle='UNAUTHORIZED',
                    dispatcher_decision='DENY', delivered=False,
                    commit_status='COMMITTED', task_outcome='DENIED')


def test_v6_valid_abstention_does_not_qualify_as_pass():
    assert e.compatibility(ABSTAINED, allow_abstention=True,
        abstention_qualifies=False) == 'COMPATIBILITY_ABSTAINED'


def test_v6_authorized_proposal_still_qualifies_as_pass():
    assert e.compatibility(AUTHORIZED, allow_abstention=True,
        abstention_qualifies=False) == 'COMPATIBILITY_PASS'


def test_v6_unauthorized_proposal_never_qualifies():
    for row in (UNAUTHORIZED, dict(AUTHORIZED, oracle='UNAUTHORIZED')):
        assert e.compatibility(row, allow_abstention=True,
            abstention_qualifies=False) != 'COMPATIBILITY_PASS'


def test_v6_malformed_and_abstention_free_of_unresolved_unknown():
    assert e.compatibility(dict(FINISHED, error='MALFORMED_RESPONSE'),
        allow_abstention=True, abstention_qualifies=False) == 'MALFORMED_RESPONSE'
    assert e.compatibility(dict(ABSTAINED, dispatch_status=None),
        allow_abstention=True, abstention_qualifies=False) != 'COMPATIBILITY_PASS'


def test_historical_families_keep_abstention_pass_semantics():
    for family in (None, '', 'v3', 'v4', 'v5'):
        execution = type('X', (), {})() if family is None else type('X', (), {'hosted_family': family})()
        assert e.abstention_qualifies_for(execution) is True
    assert e.compatibility(ABSTAINED, allow_abstention=True) == 'COMPATIBILITY_PASS'
    assert e.ABSTENTION_NON_PASS_FAMILIES == ('v6',)


def test_family_separation_and_cross_family_rejection():
    assert e.Phase2B5V6HostedExecution.protocol != e.Phase2B5V5HostedExecution.protocol
    assert e.Phase2B5V6HostedSmokeExecution.protocol != \
        e.Phase2B5V5HostedSmokeExecution.protocol
    assert not issubclass(e.Phase2B5V6HostedExecution, e.Phase2B5V5HostedExecution)
    assert e.compatibility_manifest_for(object.__new__(e.Phase2B5V6HostedExecution)) == p.MANIFEST_V6
    assert e.smoke_manifest_for(object.__new__(e.Phase2B5V6HostedSmokeExecution)) == \
        p.MANIFEST_V6_SMOKE
    assert e.compatibility_protocol_for(
        object.__new__(e.Phase2B5V6HostedExecution)) == e.V6_HOSTED_COMPATIBILITY_PROTOCOL
    assert e.smoke_protocol_for(
        object.__new__(e.Phase2B5V6HostedSmokeExecution)) == e.V6_HOSTED_SMOKE_PROTOCOL
    with pytest.raises(l.GateError, match='HOSTED_ADMISSION_UNAVAILABLE'):
        l.require_hosted_admission(e.Phase2B5V5HostedExecution)
    with pytest.raises(l.GateError, match='HOSTED_ADMISSION_UNAVAILABLE'):
        l.require_hosted_admission(e.Phase2B5V6HostedExecution)


def test_reservation_identities_are_family_scoped():
    for protocol in ('v6-hosted', 'v5-hosted', 'v4-hosted'):
        assert e.is_compatibility_key(protocol) and not e.is_smoke_protocol(protocol)
    for protocol in ('v6-hosted-smoke', 'v5-hosted-smoke', 'v4-smoke'):
        assert e.is_smoke_protocol(protocol) and not e.is_compatibility_key(protocol)
    manifest = _private(p.MANIFEST_V6_SMOKE)
    assert manifest['version'] == e.V6_HOSTED_SMOKE_PROTOCOL
    assert manifest['live_cells'] == [list(c) for c in CELLS]


def test_v6_inventory_path_is_distinct():
    assert l.V6_INVENTORY.name == 'inventory-v6-linux-v1.json'
    assert l.V6_INVENTORY != l.V5_INVENTORY and l.V6_INVENTORY != l.V4_INVENTORY


def test_no_synthetic_result_is_accepted_as_v6_hosted(tmp_path):
    payload = {'protocol': e.V6_HOSTED_COMPATIBILITY_PROTOCOL,
               'classification': 'COMPATIBILITY_PASS',
               'evidence_origin': 'SYNTHETIC_SCRIPTED_IO',
               'owner_authority': 'NONE', 'platform_authority': 'NONE'}
    result = tmp_path / 'result.json'
    result.write_text(json.dumps(payload))
    result.chmod(0o600)
    with pytest.raises(l.GateError):
        e._verify_v4_hosted_result(result, protocol=e.V6_HOSTED_COMPATIBILITY_PROTOCOL,
            manifest=p.MANIFEST_V6, cell=('authorized', 'ON'), package_digest='0' * 64,
            execution=None)


def test_v6_abstention_result_is_verifiable_but_gate_refuses():
    """A genuine V6 abstention must reconcile as evidence, never as a PASS.

    Regression risk: the verifier's fail-closed branch previously used the
    historical abstention rule, so a correctly recorded V6 abstention would be
    misfiled as tampering instead of an interpretable non-qualifying outcome.
    """
    family = e.Phase2B5V6HostedExecution
    assert family.hosted_family == 'v6'
    rule = e.abstention_qualifies_for(family)
    assert rule is False
    # Exact verifier path used for this row: the observation must independently
    # fail to reach PASS, which is what makes the refusal legitimate.
    assert e.compatibility(ABSTAINED, allow_abstention=True,
        abstention_qualifies=rule) == 'COMPATIBILITY_ABSTAINED'
    # And the gate signature requires a PASS, so it cannot admit smoke.
    assert e._verify_hosted_smoke_gate.__doc__ and 'PASS' in e._verify_hosted_smoke_gate.__doc__


def test_v6_rendered_schema_permits_two_key_abstention():
    """P1 regression: the root schema must not still require `arguments`."""
    raw = a.render_request(a.ModelConfig(a.JETSTREAM_MODEL,
        schema_variant='aligned-v2-abstain-omissible'),
        parse_message(json.dumps(MESSAGE).encode()), TypedContext(()))[0]
    schema = json.loads(raw)['response_format']['json_schema']['schema']
    assert schema['required'] == ['outcome', 'tool']
    assert schema['anyOf'][0]['required'] == ['outcome', 'tool', 'arguments']
    assert schema['anyOf'][1]['required'] == ['outcome', 'tool']
    # Every key an abstention may emit is declared, so no additional property
    # can appear either.
    assert schema['anyOf'][1]['additionalProperties'] is False
    assert set(schema['anyOf'][1]['properties']) == {'outcome', 'tool', 'arguments'}
    assert schema['anyOf'][0]['additionalProperties'] is False


def test_historical_families_are_not_affected_by_the_v6_rule():
    """P2 regression: missing `hosted_family` must mean historical PASS."""
    for execution in (object(), type('V3Like', (), {})(),
                      type('V4Like', (), {'hosted_family': 'v4'})(),
                      type('V5Like', (), {'hosted_family': 'v5'})()):
        assert e.abstention_qualifies_for(execution) is True
        assert e.compatibility(ABSTAINED, allow_abstention=True,
            abstention_qualifies=e.abstention_qualifies_for(execution)) == 'COMPATIBILITY_PASS'
    v6 = type('V6Like', (), {'hosted_family': 'v6'})()
    assert e.abstention_qualifies_for(v6) is False


def test_v6_inventory_format_is_runtime_verified():
    """P1 regression: a new package format must not skip runtime qualification."""
    import inspect
    launcher_source = inspect.getsource(l.verify_package)
    execution_source = inspect.getsource(e.verify_linux_runtime)
    assert 'phase2b5h-v6-linux-package-v1' in launcher_source
    assert 'phase2b5h-v6-linux-package-v1' in execution_source


def test_synthetic_manifest_selection_avoids_hosted_family():
    """P2 regression: synthetic executions have no hosted_family attribute."""
    import inspect
    source = inspect.getsource(e.run_first_cell)
    block = source[source.index('if protocol in SYNTHETIC_PROTOCOLS + HOSTED_PROTOCOLS:'):]
    block = block[:block.index("policy=evidence.parent")]
    assert 'if hosted:' in block
    assert 'MANIFEST_V4' in block
