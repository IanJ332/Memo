"""R1-AV native treatment and request custody using qualified R1 lifecycle code."""
from .runtime import basis, replace


def derived_source():
    source = basis('collection')
    source = replace(source, "F04='NOT_EVALUATED_R1_ACL_CLASSIFICATION_ONLY'", "F04='NOT_EVALUATED_PROPOSAL_ONLY'")
    source = replace(source, '(ARMS, LIMITS,', '(CELLS as ARMS, LIMITS,')
    source = replace(source, "int(slot['block_id'].rsplit('-', 1)[1]) - 1", "int(slot['block_id'][2:]) - 1")
    source = replace(source, "slot['arm']", "slot['cell']")
    source = replace(source, "entity_complete=receipt['entity_complete'], http_status=receipt['HTTP_status'])",
                     "entity_complete=receipt['entity_complete'], http_status=receipt['HTTP_status'], block=block, selected=selected)")
    source = replace(source, "durable(out / 'scoring.json', result)",
                     "from .protocol import exposure\n                result['exposure'] = exposure(block, slot['cell'], selected, stored=job_memories(block, slot['cell']), retrieved=retrieved_records(strict(raw(capture / 'reopen/result.json'))['raw_retrieval']))\n                durable(out / 'scoring.json', result)")
    return source


exec(compile(derived_source(), __file__ + ':R1-derived', 'exec'), globals())

_r1_inspect_native = inspect_native


def inspect_native(capture, job, block, acl):
    selected = _r1_inspect_native(capture, job, block, acl)
    # Qualified selection policy is all returned Mem0 results in literal order.
    # Recheck the projection independently rather than trusting duplicate views.
    for phase in ('exercise', 'reopen'):
        result = strict(raw(capture / phase / 'result.json'))
        rows = result['raw_retrieval']['results']
        chosen = result['selected_context']
        need(len(rows) == len(chosen), 'NATIVE_RAW_SELECTION_COUNT')
        for position, (candidate, note) in enumerate(zip(rows, chosen), 1):
            need(candidate['id'] == note['native_id'] and candidate['memory'] == note['content']
                 and position == note['original_position_1based']
                 and candidate['user_id'] == note['native_user_id'], 'NATIVE_RAW_SELECTION_PROVENANCE')
    return selected


def host_fixture(block, acl):
    return dict(authored_by='INDEPENDENT_HOST_FIXTURE', project=block['project_id'],
                principal={**acl['principal'], 'project': block['project_id']},
                principal_allowed=True, current_recipients=[acl['current_recipient']],
                before_recipients=[acl['historical_recipient']], revision=1,
                session='FICTIONAL_R1_AV_ONLY')


def job_memories(block, cell):
    from .protocol import fixture
    return fixture(block, cell)


def retrieved_records(value):
    """Derived exposure view only; the complete original SDK response is retained."""
    need(type(value) is dict and type(value.get('results')) is list, 'MEM0_NATIVE_RETRIEVAL_SHAPE')
    rows = value['results']
    need(all(type(r) is dict and type(r.get('memory')) is str for r in rows), 'MEM0_LITERAL_RETRIEVAL_CONTENT')
    return [dict(content=r['memory']) for r in rows]


def native_job(m, block, acl, slot, state):
    from memlife.batch.jobs import qualification_job
    job = qualification_job('mem0', contract.EXECUTION, slot['capture_id'], state)
    job.update(purpose='AUTHORIZED_R1_AV_COLLECTION', case_id=block['block_id'], family='A3',
               task=block['query'], memories=job_memories(block, slot['cell']),
               host_acl=host_fixture(block, acl), request_template=template(m, block, slot['cell']),
               source_manifest_sha256=contract.verify()['design']['sha256'])
    return job
