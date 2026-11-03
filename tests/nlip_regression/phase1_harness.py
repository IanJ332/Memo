# SPDX-License-Identifier: MIT
"""Explicit synthetic engineering issuer and bootstrap; never real Keycloak."""
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qs
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey
from memlife.nlip.agent import DeterministicAdapter
from memlife.nlip.custody import Database, Notes
from memlife.nlip.admission import AdmissionService, SpyAdapter
from memlife.nlip.app import ReportApplication
from memlife.nlip.auth import OIDCConfig, OIDCLogin, Principal, SessionAuthority, TokenVerifier
from memlife.nlip.dispatcher import ProtectedDispatcher
from memlife.nlip.policy import PolicyAdmin, PolicyStore

class EngineeringIssuer:
    def __init__(self,clock=time.time):
        self.clock=clock;self.codes={};self.exchanges=0
        private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.key=RSAKey.import_key(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()),parameters={"kid":"synthetic-key"})
        self.config=OIDCConfig("https://issuer.invalid/realms/synthetic","report-web","report-api","https://agent.invalid/auth/callback",development_loopback=True)
        public=self.key.as_dict(private=False);public["kid"]="synthetic-key"
        self.jwks={"keys":[public]}
    def tokens(self,nonce,subject="synthetic-user",*,id_overrides=None,access_overrides=None,key=None):
        now=int(self.clock());common={"iss":self.config.issuer,"sub":subject,"iat":now-1,"exp":now+900}
        idc={**common,"aud":self.config.client_id,"nonce":nonce,**(id_overrides or {})}
        access={**common,"aud":self.config.resource_audience,"typ":"Bearer","scope":"openid report:send",**(access_overrides or {})}
        sign=lambda claims:jwt.encode({"alg":"RS256","kid":"synthetic-key"},claims,key or self.key,algorithms=["RS256"])
        return {"id_token":sign(idc),"access_token":sign(access),"token_type":"Bearer","expires_in":900}
    def issue_code(self,nonce,subject="synthetic-user",**overrides):
        code=secrets.token_urlsafe(24);self.codes[code]=(nonce,subject,overrides);return code
    def exchange(self,request):
        self.exchanges+=1
        assert request.method=="POST" and str(request.url)==self.config.issuer+"/protocol/openid-connect/token"
        values=parse_qs(request.content.decode());entry=self.codes.pop(values.get("code",[""])[0],None)
        if entry is None or values.get("grant_type")!=["authorization_code"] or not values.get("code_verifier"):
            return httpx.Response(400,json={"error":"invalid_grant"})
        nonce,subject,overrides=entry
        return httpx.Response(200,json=self.tokens(nonce,subject,**overrides))

@dataclass
class EngineeringHarness:
    admin: PolicyAdmin
    policy: PolicyStore
    sessions: SessionAuthority
    issuer: EngineeringIssuer
    login: OIDCLogin
    service: ReportApplication
    def identity_session(self,subject="synthetic-user"):
        tokens=self.issuer.tokens("engineering-nonce",subject)
        identity=self.login.verifier.login_identity(tokens["id_token"],tokens["access_token"],"engineering-nonce")
        return self.sessions.issue(identity)

def engineering_harness(directory,*,defense=True,extensions=(),clock=time.time):
    from pathlib import Path
    from memlife.nlip.security import SecurityRegistry
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    admin=PolicyAdmin.create(directory/"policy.sqlite")
    policy=PolicyStore(admin.path);sessions=SessionAuthority(clock);issuer=EngineeringIssuer(clock)
    verifier=TokenVerifier(issuer.config,issuer.jwks,clock)
    login=OIDCLogin(issuer.config,verifier,sessions,httpx.MockTransport(issuer.exchange),clock)
    dispatcher=ProtectedDispatcher(policy,SecurityRegistry(extensions),sessions=sessions,engineering_defense_off=not defense)
    database=Database.create(directory/"notes.sqlite", "regression-store")
    notes=Notes(database)
    admission=AdmissionService(database,sessions,policy,dispatcher,SpyAdapter(DeterministicAdapter()))
    service=ReportApplication(sessions,policy,dispatcher,notes,admission,origin="https://agent.invalid",login=login)
    return EngineeringHarness(admin,policy,sessions,issuer,login,service)

def request_message(session,project,recipient,*,note="Synthetic report sharing.",label="external_note"):
    return {"Format":"text","Subformat":"English","Content":"Share the synthetic report with the current approved recipient.",
        "Submessages":[{"Format":"structured","Subformat":"json","Content":{"tool":"send_report","arguments":{"project_id":project,"recipient":recipient}}},
        {"Format":"text","Subformat":"English","Content":note,"Label":label},
        {"Format":"token","Subformat":"conversation_memlife","Content":session.conversation}]}

def session_headers(session,origin):
    return {"Origin":origin,"X-CSRF-Token":session.csrf,"Cookie":"memlife_session="+session.sid}
