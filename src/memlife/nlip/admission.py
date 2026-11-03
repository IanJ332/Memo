# SPDX-License-Identifier: MIT
"""Serialized, offline application-service admission and synthetic dispatch."""
import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from .agent import request_proposal
from .custody import digest, verify_record
from .dispatcher import ProtectedDispatcher

@dataclass(frozen=True)
class ContextItem:
    record_id: str
    channel: str
    content: bytes
    def as_dict(self):
        return {'record_id':self.record_id,'channel':self.channel,'content_base64':base64.b64encode(self.content).decode('ascii')}

@dataclass(frozen=True)
class TypedContext:
    items: tuple[ContextItem, ...]
    def __post_init__(self):
        if type(self.items) is not tuple or any(type(x) is not ContextItem for x in self.items): raise TypeError('TYPED_CONTEXT_REQUIRED')

def envelope(message, context):
    if type(context) is not TypedContext: raise TypeError('TYPED_CONTEXT_REQUIRED')
    return json.dumps({'schema':'nlip-phase0-adapter-input/1','message':message.as_dict(),
        'context':[x.as_dict() for x in context.items]},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

class SpyAdapter:
    def __init__(self, delegate): self.delegate=delegate; self.captures=[]
    def propose(self,message,context):
        if type(context) is not TypedContext: raise TypeError('TYPED_CONTEXT_REQUIRED')
        payload=envelope(message,context)
        self.captures.append((payload,hashlib.sha256(payload).hexdigest()))
        return self.delegate.propose(message,context)

class AdmissionService:
    def __init__(self, database, sessions, policy, dispatcher, adapter, mode='ON'):
        if mode not in ('OFF','DIAGNOSTIC','ON'): raise ValueError('INVALID_ADMISSION_MODE')
        # The provider adapter must never receive the unfiltered diagnostic arms.
        from .model_adapter import TypedModelAdapter
        candidate=adapter
        while type(candidate) is SpyAdapter: candidate=candidate.delegate
        if mode != 'ON':
            # Only the known deterministic offline fixture may receive unfiltered
            # context. Unknown wrappers, including SpyAdapter subclasses, fail closed.
            from .agent import DeterministicAdapter
            allowed = type(adapter) is DeterministicAdapter or (type(adapter) is SpyAdapter and type(adapter.delegate) is DeterministicAdapter)
            if not allowed: raise ValueError('MODEL_REQUIRES_ADMISSION_ON')
        if type(dispatcher) is not ProtectedDispatcher or dispatcher._engineering_off: raise ValueError('MANDATORY_AUTHORIZATION_REQUIRED')
        if dispatcher.sessions is not sessions or dispatcher.policy is not policy: raise ValueError('DISPATCH_CONFIGURATION_MISMATCH')
        self.database=database;self.sessions=sessions;self.policy=policy;self.dispatcher=dispatcher;self.adapter=adapter;self.mode=mode
    def execute(self,session,message):
        with self.sessions.guard(session.principal,session) as live:
            if not live: raise PermissionError('INVALID_SESSION')
            return self._execute_guarded(session,message)
    def _execute_guarded(self,session,message):
        start=time.perf_counter_ns()
        if not self.sessions.live(session.principal,session): raise PermissionError('INVALID_SESSION')
        tokens=[part for part in message.parts if part.kind=='token' and part.subtype=='conversation_memlife']
        from .auth import safe_equal
        if len(tokens)!=1 or not safe_equal(tokens[0].content,session.conversation): raise PermissionError('CONVERSATION_SESSION_MISMATCH')
        requested=request_proposal(message); project=requested.arguments['project_id']; principal=session.principal
        current=self.policy.current(principal,project)
        if not current.known_project or not current.principal_allowed: raise PermissionError('PRINCIPAL_UNAUTHORIZED')
        with self.database.lease():
            with self.database.transaction() as db:
                if not self.sessions.live(principal,session): raise PermissionError('INVALID_SESSION')
                records=self.database.records(db,principal,project)
                generation=db.execute('SELECT generation FROM metadata').fetchone()[0]
                associations=db.execute('SELECT record_id,issuer,subject,project,event,status,confirmation,host_revision FROM associations ORDER BY seq').fetchall()
                sources=[(event,source,digest(body),revision) for event,source,body,revision in db.execute('SELECT event,source,body,revision FROM sources ORDER BY event')]
                confirmations=db.execute('SELECT id,record_id,event,revision,digest FROM confirmations ORDER BY id').fetchall()
                events=db.execute('SELECT seq,kind,details FROM events ORDER BY seq').fetchall()
                decisions=[]; delivered=[]
                for record in records:
                    classification,reason=verify_record(db,record) if self.mode!='OFF' else ('UNASSESSED','ADMISSION_DISABLED')
                    decisions.append({'record_id':record.record_id,'classification':classification,'reason':reason,
                        'content_base64':base64.b64encode(record.content).decode('ascii'),'sha256':digest(record.content),'revision':record.revision,'routing':record.use})
                    if self.mode!='ON' or classification in ('CURRENT','REFERENCE'):
                        channel=('operational' if record.use=='operational' else 'reference')
                        delivered.append(ContextItem(record.record_id,channel,record.content))
                context=TypedContext(tuple(delivered)); payload=envelope(message,context)
                invocation=uuid.uuid4().hex
                snapshot={'generation':generation,'associations':associations,'sources':sources,'confirmations':confirmations,'events':events}
                snapshot_sha256=digest(json.dumps(snapshot,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
                audit={'snapshot_sha256':snapshot_sha256,'invocation':invocation,'phase':'PRE_HANDOFF','mode':self.mode,'store_id':self.database.store_id,'scope':[principal.issuer,principal.subject,project],
                    'generation':generation,'associations':associations,'sources':sources,'confirmations':confirmations,'events':events,'decisions':decisions,'context':[item.as_dict() for item in context.items],
                    'envelope_base64':base64.b64encode(payload).decode('ascii'),'envelope_sha256':digest(payload)}
                db.execute('INSERT INTO audit(payload) VALUES(?)',(json.dumps(audit,sort_keys=True,separators=(',',':')).encode(),))
            # The shared lease remains held after durable audit commit through the
            # actual adapter handoff; publishers and supported note writers wait.
            if not self.sessions.live(principal,session): raise PermissionError('INVALID_SESSION')
            proposal=self.adapter.propose(message,context)
            with self.database.transaction() as db:
                db.execute('INSERT INTO audit(payload) VALUES(?)',(json.dumps({'invocation':invocation,'phase':'ADAPTER_RETURNED'},sort_keys=True).encode(),))
        elapsed=time.perf_counter_ns()-start
        from .model_adapter import Abstention
        if type(proposal) is Abstention:
            from .dispatcher import DispatchResult
            from .security import SecurityDecision
            return DispatchResult(SecurityDecision('DENY','MODEL_ABSTAINED',None),False,0,0), audit, elapsed
        result=self.dispatcher.dispatch(principal,session,proposal.tool,proposal.arguments)
        return result, audit, elapsed
