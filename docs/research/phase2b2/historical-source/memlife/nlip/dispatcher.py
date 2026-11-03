# SPDX-License-Identifier: MIT
"""The only application path to the local synthetic delivery sink."""
import time
import uuid
from dataclasses import dataclass
from .auth import Session
from .policy import ToolArguments
from .security import SecurityDecision, SecurityRegistry

@dataclass(frozen=True)
class DispatchResult:
    decision: SecurityDecision
    delivered: bool
    security_ns: int
    total_ns: int
    sink_ns: int = 0

class ProtectedDispatcher:
    def __init__(self,policy_store,registry=None,*,sessions,engineering_defense_off=False):
        if registry is not None and type(registry) is not SecurityRegistry: raise ValueError("INVALID_SECURITY_REGISTRY")
        self.sessions=sessions
        self.policy=policy_store;self.registry=registry or SecurityRegistry()
        self._engineering_off=engineering_defense_off
    def send_report(self,*args,**kwargs):
        raise PermissionError("DIRECT_DISPATCH_FORBIDDEN")
    def dispatch(self,principal,session,tool,arguments):
        start=time.perf_counter_ns();security_ns=0
        if not isinstance(session,Session) or session.authority is not self.sessions:
            return DispatchResult(SecurityDecision("DENY","INVALID_SESSION",None),False,0,time.perf_counter_ns()-start)
        with session.authority.guard(principal,session) as live:
            if not live: return DispatchResult(SecurityDecision("DENY","INVALID_SESSION",None),False,0,time.perf_counter_ns()-start)
            try:
                if tool!="send_report": raise ValueError("UNKNOWN_TOOL")
                parsed=ToolArguments.parse(arguments)
            except ValueError as exc:
                code="UNKNOWN_TOOL" if str(exc)=="UNKNOWN_TOOL" else "MALFORMED_ARGUMENTS"
                return DispatchResult(SecurityDecision("DENY",code,None),False,0,time.perf_counter_ns()-start)
            try:
                with self.policy._dispatch_transaction() as db:
                    snapshot=self.policy.snapshot(db,principal,parsed.project_id)
                    gate_start=time.perf_counter_ns()
                    if self._engineering_off:
                        if snapshot.known_project and snapshot.principal_allowed:
                            decision=SecurityDecision("ALLOW","SIMULATED_DEFENSE_OFF",snapshot.revision)
                        else: decision=SecurityDecision("DENY","PRINCIPAL_UNAUTHORIZED",snapshot.revision)
                    else:
                        decision=self.registry.decide(principal,session,tool,parsed.as_dict(),snapshot)
                    security_ns=time.perf_counter_ns()-gate_start
                    if not session.authority.live(principal,session):
                        decision=SecurityDecision("DENY","INVALID_SESSION",snapshot.revision)
                    invocation=uuid.uuid4().hex
                    delivered=decision.action=="ALLOW" and decision.policy_revision==snapshot.revision
                    sink_start=time.perf_counter_ns()
                    if delivered:
                        db.execute("INSERT INTO deliveries VALUES(?,?,?,?,1)",(invocation,parsed.project_id,parsed.recipient,snapshot.revision))
                    db.execute("INSERT INTO audit VALUES(?,?,?,?,?)",(invocation,decision.action,decision.reason,decision.policy_revision,int(delivered)))
                return DispatchResult(decision,delivered,security_ns,time.perf_counter_ns()-start,time.perf_counter_ns()-sink_start)
            except Exception:
                return DispatchResult(SecurityDecision("DENY","POLICY_UNAVAILABLE",None),False,security_ns,time.perf_counter_ns()-start)
