# SPDX-License-Identifier: MIT
"""Reusable Type-3 pre-tool authorization; no message text or model reasoning."""
from dataclasses import dataclass
from .auth import Principal, Session
from .policy import PolicySnapshot, ToolArguments

@dataclass(frozen=True)
class SecurityDecision:
    action: str
    reason: str
    policy_revision: int | None
    def as_dict(self):
        return {"action":self.action,"reason":self.reason,"policy_revision":self.policy_revision}

def authorize_tool_call(principal,session_context,tool_name,structured_arguments,policy_store):
    revision=None
    try:
        if not isinstance(principal,Principal) or not isinstance(session_context,Session) or not session_context.authority.live(principal,session_context):
            return SecurityDecision("DENY","INVALID_SESSION",None)
        if tool_name!="send_report": return SecurityDecision("DENY","UNKNOWN_TOOL",None)
        try: arguments=ToolArguments.parse(structured_arguments)
        except ValueError: return SecurityDecision("DENY","MALFORMED_ARGUMENTS",None)
        policy=policy_store.current(principal,arguments.project_id)
        if not isinstance(policy,PolicySnapshot) or type(policy.revision) is not int or policy.revision<0:
            return SecurityDecision("DENY","INCONSISTENT_POLICY",None)
        revision=policy.revision
        if not policy.known_project: return SecurityDecision("DENY","UNKNOWN_PROJECT",revision)
        if not policy.principal_allowed: return SecurityDecision("DENY","PRINCIPAL_UNAUTHORIZED",revision)
        if arguments.recipient not in policy.recipients: return SecurityDecision("DENY","RECIPIENT_UNAUTHORIZED",revision)
        return SecurityDecision("ALLOW","AUTHORIZED_CURRENT_RECIPIENT",revision)
    except Exception:
        return SecurityDecision("DENY","POLICY_UNAVAILABLE",revision)

class CurrentRecipientSecurity:
    name="current-recipient-v1"
    def authorize_tool_call(self,*args): return authorize_tool_call(*args)

class SecurityRegistry:
    """Mandatory current-policy gate plus composable additional trusted checks."""
    def __init__(self,extensions=()):
        self.primary=CurrentRecipientSecurity()
        self.extensions=tuple(extensions)
        if any(not callable(getattr(x,"authorize_tool_call",None)) for x in self.extensions): raise ValueError("INVALID_SECURITY_EXTENSION")
    def decide(self,principal,session,tool,arguments,policy):
        decision=self.primary.authorize_tool_call(principal,session,tool,arguments,policy)
        if decision.action!="ALLOW": return decision
        for extension in self.extensions:
            try:
                result=extension.authorize_tool_call(principal,session,tool,arguments,policy)
                if not isinstance(result,SecurityDecision) or result.policy_revision!=decision.policy_revision or result.action not in {"ALLOW","DENY"}:
                    return SecurityDecision("DENY","INVALID_EXTENSION_DECISION",decision.policy_revision)
                if result.action=="DENY":
                    # Never retain arbitrary plugin reason strings in security audits.
                    return SecurityDecision("DENY","ADDITIONAL_EXTENSION_DENY",decision.policy_revision)
            except Exception: return SecurityDecision("DENY","SECURITY_ERROR",decision.policy_revision)
        return decision
