# SPDX-License-Identifier: MIT
"""Durable conservative model admission. No model endpoint is configured here."""
import hashlib
import os
import sqlite3
import threading
import uuid
from pathlib import Path

class ModelGateError(RuntimeError): pass

class ModelRequestLedger:
    def __init__(self,path):
        self.path=Path(path)
        fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        with sqlite3.connect(self.path) as db:
            db.executescript("CREATE TABLE requests(split TEXT,item TEXT,status TEXT,input_hash TEXT,PRIMARY KEY(split,item)); CREATE TABLE gate(closed INTEGER); INSERT INTO gate VALUES(0); CREATE TABLE request_usage(split TEXT,item TEXT,input_tokens INTEGER,output_tokens INTEGER,provider_internal_requests INTEGER,provider_internal_tokens INTEGER,PRIMARY KEY(split,item)); CREATE TABLE binding(key TEXT PRIMARY KEY,value TEXT NOT NULL);")

    @classmethod
    def for_study(cls,path,*,study_id,dataset_sha256):
        """Reopen the same bound budget without replacing its requests or capacity."""
        path=Path(path)
        if path.is_symlink() or not isinstance(study_id,str) or not study_id or not isinstance(dataset_sha256,str) or len(dataset_sha256)!=64 or any(c not in '0123456789abcdef' for c in dataset_sha256):
            raise ModelGateError('INVALID_STUDY_BINDING')
        try:
            ledger=cls(path)
        except FileExistsError:
            ledger=cls.__new__(cls);ledger.path=path
        else:
            with sqlite3.connect(path) as db:
                db.executemany('INSERT INTO binding VALUES(?,?)',[
                    ('study_id',study_id),('dataset_sha256',dataset_sha256),('ledger_uuid',str(uuid.uuid4()))])
        try:
            with sqlite3.connect(path) as db:
                binding=dict(db.execute('SELECT key,value FROM binding'))
                if set(binding)!={'study_id','dataset_sha256','ledger_uuid'} or binding['study_id']!=study_id or binding['dataset_sha256']!=dataset_sha256:
                    raise ModelGateError('STUDY_BINDING_MISMATCH')
                uuid.UUID(binding['ledger_uuid'])
                gates=db.execute('SELECT closed FROM gate').fetchall()
                if len(gates)!=1 or gates[0][0] not in (0,1):raise ModelGateError('INVALID_LEDGER_GATE')
                counts=dict(db.execute('SELECT split,COUNT(*) FROM requests GROUP BY split'))
                if set(counts)-{'development','heldout'} or counts.get('development',0)>32 or counts.get('heldout',0)>96 or sum(counts.values())>128:
                    raise ModelGateError('INVALID_LEDGER_CAPACITY')
                if db.execute("SELECT 1 FROM requests WHERE status NOT IN ('RESERVED','SENT','COMPLETE','ERROR')").fetchone():
                    raise ModelGateError('INVALID_LEDGER_STATUS')
            return ledger
        except (sqlite3.Error,ValueError) as exc:
            raise ModelGateError('INVALID_STUDY_LEDGER') from exc

    def identity(self):
        with sqlite3.connect(self.path) as db:return dict(db.execute('SELECT key,value FROM binding'))
    def reserve(self,split,item,input_bytes):
        if split not in {"development","heldout"} or not isinstance(item,str) or not item: raise ModelGateError("INVALID_MODEL_SLOT")
        with sqlite3.connect(self.path,timeout=2) as db:
            db.execute("BEGIN IMMEDIATE")
            count=db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            group=db.execute("SELECT COUNT(*) FROM requests WHERE split=?",(split,)).fetchone()[0]
            if db.execute("SELECT 1 FROM requests WHERE status='SENT'").fetchone(): raise ModelGateError("MODEL_SEND_UNRESOLVED")
            if db.execute("SELECT closed FROM gate").fetchone()[0] or count>=128 or group>=(32 if split=="development" else 96): raise ModelGateError("MODEL_ADMISSION_CLOSED")
            if db.execute("SELECT 1 FROM requests WHERE split=? AND item=?",(split,item)).fetchone(): raise ModelGateError("MODEL_RETRY_FORBIDDEN")
            db.execute("INSERT INTO requests VALUES(?,?,?,?)",(split,item,"RESERVED",hashlib.sha256(input_bytes).hexdigest()))
    def sent(self,split,item):
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT closed FROM gate").fetchone()[0] or db.execute("SELECT 1 FROM requests WHERE status='SENT'").fetchone(): raise ModelGateError("MODEL_ADMISSION_CLOSED")
            if db.execute("UPDATE requests SET status='SENT' WHERE split=? AND item=? AND status='RESERVED'",(split,item)).rowcount!=1: raise ModelGateError("INVALID_MODEL_RESERVATION")
    def finish(self,split,item,usage_known):
        if type(usage_known) is not bool:
            self.fail(split,item)
            raise ModelGateError("INVALID_USAGE_ATTESTATION")
        with sqlite3.connect(self.path) as db:
            if db.execute("UPDATE requests SET status=? WHERE split=? AND item=? AND status='SENT'",("COMPLETE" if usage_known else "ERROR",split,item)).rowcount!=1: raise ModelGateError("INVALID_MODEL_COMPLETION")
            if not usage_known: db.execute("UPDATE gate SET closed=1")

    def complete_with_usage(self,split,item,*,input_tokens,output_tokens,
                            provider_internal_requests=0,provider_internal_tokens=0):
        """Future real transports must supply exact usage; booleans are insufficient."""
        values=(input_tokens,output_tokens,provider_internal_requests,provider_internal_tokens)
        if any(type(value) is not int or value<0 for value in values):
            self.fail(split,item)
            raise ModelGateError("MODEL_USAGE_UNQUALIFIED")
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            internal=provider_internal_requests!=0 or provider_internal_tokens!=0
            if db.execute("UPDATE requests SET status=? WHERE split=? AND item=? AND status='SENT'",('ERROR' if internal else 'COMPLETE',split,item)).rowcount!=1:
                raise ModelGateError("INVALID_MODEL_COMPLETION")
            db.execute("INSERT INTO request_usage VALUES(?,?,?,?,?,?)",(split,item,*values))
            if internal: db.execute("UPDATE gate SET closed=1")
        if internal: raise ModelGateError("PROVIDER_INTERNAL_USAGE_UNAUTHORIZED")

    def usage_totals(self):
        with sqlite3.connect(self.path) as db:
            names=("input_tokens","output_tokens","provider_internal_requests","provider_internal_tokens")
            values=db.execute("SELECT COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),COALESCE(SUM(provider_internal_requests),0),COALESCE(SUM(provider_internal_tokens),0) FROM request_usage").fetchone()
            result=dict(zip(names,values))
            result['known_usage_requests']=db.execute("SELECT COUNT(*) FROM request_usage").fetchone()[0]
            result['unknown_usage_requests']=db.execute("SELECT COUNT(*) FROM requests r LEFT JOIN request_usage u ON r.split=u.split AND r.item=u.item WHERE r.status!='RESERVED' AND u.item IS NULL").fetchone()[0]
            return result
    def counts(self):
        with sqlite3.connect(self.path) as db:
            return dict(db.execute("SELECT status,COUNT(*) FROM requests GROUP BY status"))

    def fail(self,split,item):
        """Close admission even when an interruption bypasses normal completion."""
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE requests SET status='ERROR' WHERE split=? AND item=? AND status IN ('RESERVED','SENT')",(split,item))
            db.execute("UPDATE gate SET closed=1")

class ModelDecisionAdapter:
    """A future single-send client seam; unavailable endpoint/entitlement rejects.

The callable must separately qualify complete send ownership and no retries.
This ledger alone does not qualify arbitrary SDK retries or paid endpoints.
"""
    def __init__(self,ledger,single_send,*,endpoint_verified=False,cost_entitlement_verified=False):
        if not endpoint_verified or not cost_entitlement_verified: raise ModelGateError("MODEL_ENDPOINT_NOT_QUALIFIED")
        self.ledger=ledger;self.single_send=single_send;self._lock=threading.Lock();self._slot=None
    def evaluate(self,split,item,input_bytes):
        with self._lock:
            self.ledger.reserve(split,item,input_bytes);self.ledger.sent(split,item)
            try:
                output,usage_known=self.single_send(input_bytes)
                self.ledger.finish(split,item,usage_known)
                if not usage_known: raise ModelGateError("MODEL_USAGE_UNKNOWN")
                return output
            except BaseException:
                self.ledger.fail(split,item)
                raise

    def bind_slot(self,split,item):
        # Trusted orchestration only; HTTP content cannot select or reallocate slots.
        if self._slot is not None: raise ModelGateError("MODEL_SLOT_ALREADY_BOUND")
        self._slot=(split,item)
    def propose(self,message,notes):
        if self._slot is None: raise ModelGateError("MODEL_SLOT_NOT_BOUND")
        from .agent import Proposal
        from .policy import ToolArguments
        from .wire import strict_json
        import json
        split,item=self._slot;self._slot=None
        payload=json.dumps({"untrusted_client_parts":[p.as_dict() for p in message.parts if p.kind!="token"],
            "untrusted_persisted_notes":list(notes),"task":"Propose one send_report tool call as tool and arguments JSON."},separators=(",",":"),ensure_ascii=False).encode()
        output=self.evaluate(split,item,payload)
        decoded=strict_json(output)
        if not isinstance(decoded,dict) or set(decoded)!={"tool","arguments"} or decoded["tool"]!="send_report": raise ModelGateError("INVALID_MODEL_PROPOSAL")
        args=ToolArguments.parse(decoded["arguments"])
        return Proposal(decoded["tool"],args.as_dict())
