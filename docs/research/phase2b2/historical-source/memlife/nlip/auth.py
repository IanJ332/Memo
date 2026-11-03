# SPDX-License-Identifier: MIT
"""Keycloak-compatible code/PKCE integration and server-owned sessions."""
from __future__ import annotations
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx
from authlib.integrations.httpx_client import OAuth2Client
from joserfc import jwt
from joserfc.jwk import KeySet

class AuthError(ValueError): pass

def safe_equal(left,right):
    if not isinstance(left,str) or not isinstance(right,str): return False
    try: return secrets.compare_digest(left.encode(),right.encode())
    except (UnicodeError,ValueError): return False

@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str

@dataclass(frozen=True)
class Identity:
    principal: Principal
    expires_at: int

@dataclass(frozen=True)
class Session:
    sid: str = field(repr=False)
    principal: Principal
    expires_at: int
    conversation: str = field(repr=False)
    csrf: str = field(repr=False)
    authority: object = field(repr=False,compare=False)

class SessionAuthority:
    def __init__(self,clock=time.time):
        self.clock=clock;self._sessions={};self._lock=threading.RLock()
    def issue(self,identity):
        if not isinstance(identity,Identity) or identity.expires_at<=self.clock(): raise AuthError("INVALID_IDENTITY")
        with self._lock:
            session=Session(secrets.token_urlsafe(32),identity.principal,
                min(identity.expires_at,int(self.clock())+900),secrets.token_urlsafe(32),secrets.token_urlsafe(32),self)
            self._sessions[session.sid]=session
            return session
    def get(self,sid):
        with self._lock:
            session=self._sessions.get(sid)
            if session is None or not self.live(session.principal,session): raise AuthError("UNAUTHENTICATED")
            return session
    def live(self,principal,session):
        with self._lock:
            return (isinstance(session,Session) and session.authority is self and
                self._sessions.get(session.sid) is session and session.principal is principal and
                session.expires_at>self.clock())
    @contextmanager
    def guard(self,principal,session):
        with self._lock: yield self.live(principal,session)
    def logout(self,sid):
        with self._lock: self._sessions.pop(sid,None)

@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    client_id: str
    resource_audience: str
    redirect_uri: str
    client_secret: str | None = field(default=None,repr=False)
    development_loopback: bool = False
    def __post_init__(self):
        for value in (self.issuer,self.redirect_uri):
            u=urlsplit(value)
            if u.username or u.password or u.query or u.fragment or not u.hostname: raise ValueError("INVALID_OIDC_URL")
            loopback=self.development_loopback and u.hostname in {"127.0.0.1","localhost","::1"}
            if u.scheme!="https" and not (loopback and u.scheme=="http"): raise ValueError("OIDC_HTTPS_REQUIRED")
        if not self.client_id or not self.resource_audience: raise ValueError("INVALID_OIDC_AUDIENCE")

class TokenVerifier:
    """Only a trusted bootstrap keyset; token-provided key URLs are never followed."""
    def __init__(self,config,jwks,clock=time.time):
        self.config=config;self.clock=clock
        keys=jwks.get("keys",[]) if isinstance(jwks,dict) else []
        if not isinstance(keys,list) or not keys or len(keys)>8 or any(not isinstance(k,dict) for k in keys): raise ValueError("INVALID_TRUSTED_JWKS")
        kids=[k.get("kid") for k in keys]
        if any(not isinstance(k,str) or not k for k in kids) or len(set(kids))!=len(kids): raise ValueError("AMBIGUOUS_TRUSTED_KEYS")
        if any("d" in k for k in keys): raise ValueError("UNSUPPORTED_TRUSTED_KEY")
        # A real issuer publishes encryption and alternative-algorithm keys too.
        # Only public RS256 signing keys enter the verification trust set.
        signing=[k for k in keys if k.get("kty")=="RSA" and k.get("use","sig")=="sig" and k.get("alg","RS256")=="RS256"
                 and ("key_ops" not in k or k["key_ops"]==["verify"])]
        if not signing: raise ValueError("UNSUPPORTED_TRUSTED_KEY")
        self.keys=KeySet.import_key_set({"keys":signing});self.kids=frozenset(k["kid"] for k in signing)
    def _claims(self,value,audience,nonce=None,access=False):
        try:
            if not isinstance(value,str) or len(value)>16384: raise ValueError()
            # joserfc verifies the signature against the pinned keyset and algorithm.
            token=jwt.decode(value,self.keys,algorithms=["RS256"])
            if token.header.get("kid") not in self.kids or set(token.header)-{"alg","kid","typ"}: raise ValueError()
            c=token.claims;now=int(self.clock())
            for name in ("exp","iat"):
                if type(c.get(name)) is not int: raise ValueError()
            if c["exp"]<=now or c["iat"]>now or c["iat"]>=c["exp"]: raise ValueError()
            if "nbf" in c and (type(c["nbf"]) is not int or c["nbf"]>now): raise ValueError()
            if c.get("iss")!=self.config.issuer or not isinstance(c.get("sub"),str) or not c["sub"]: raise ValueError()
            aud=c.get("aud")
            audiences=[aud] if isinstance(aud,str) else aud
            if not isinstance(audiences,list) or not audiences or any(not isinstance(a,str) for a in audiences) or audience not in audiences: raise ValueError()
            if not access:
                if (len(audiences)>1 and c.get("azp")!=self.config.client_id) or ("azp" in c and c["azp"]!=self.config.client_id): raise ValueError()
                if not isinstance(c.get("nonce"),str) or nonce is None or not safe_equal(c["nonce"],nonce): raise ValueError()
            elif c.get("typ")!="Bearer" or "report:send" not in c.get("scope","").split(): raise ValueError()
            return c
        except Exception as exc:
            raise AuthError("INVALID_TOKEN") from exc
    def login_identity(self,id_token,access_token,nonce):
        idc=self._claims(id_token,self.config.client_id,nonce)
        access=self._claims(access_token,self.config.resource_audience,access=True)
        if idc["sub"]!=access["sub"]: raise AuthError("TOKEN_PRINCIPAL_MISMATCH")
        if "at_hash" in idc:
            from authlib.oidc.core.util import create_half_hash
            expected=create_half_hash(access_token,"RS256").decode()
            if not isinstance(idc["at_hash"],str) or not secrets.compare_digest(idc["at_hash"],expected): raise AuthError("INVALID_TOKEN")
        return Identity(Principal(idc["iss"],idc["sub"]),min(idc["exp"],access["exp"]))

@dataclass(frozen=True)
class LoginTransaction:
    state: str = field(repr=False)
    nonce: str = field(repr=False)
    verifier: str = field(repr=False)
    expires: float

class OIDCLogin:
    def __init__(self,config,verifier,sessions,transport=None,clock=time.time):
        self.config=config;self.verifier=verifier;self.sessions=sessions
        self.transport=transport;self.clock=clock;self._pending={};self._lock=threading.Lock();self._exchanges=0
    def _client(self,state=None):
        return OAuth2Client(self.config.client_id,client_secret=self.config.client_secret,
            redirect_uri=self.config.redirect_uri,scope="openid report:send",state=state,
            code_challenge_method="S256",trust_env=False,follow_redirects=False,timeout=5,transport=self.transport)
    def begin(self):
        browser=secrets.token_urlsafe(32)
        transaction=LoginTransaction(secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(48),self.clock()+300)
        with self._lock:
            self._pending={k:v for k,v in self._pending.items() if v.expires>self.clock()}
            if len(self._pending)>=64: raise AuthError("LOGIN_CAPACITY")
            self._pending[browser]=transaction
        with self._client() as client:
            url,_=client.create_authorization_url(self.config.issuer+"/protocol/openid-connect/auth",
                state=transaction.state,code_verifier=transaction.verifier,nonce=transaction.nonce)
        return browser,url
    def callback(self,browser,state,code):
        with self._lock:
            transaction=self._pending.pop(browser,None)
            if (transaction is None or transaction.expires<=self.clock() or not isinstance(state,str) or
                not safe_equal(state,transaction.state) or not isinstance(code,str) or not 0<len(code)<=2048):
                raise AuthError("INVALID_LOGIN_TRANSACTION")
            if self._exchanges>=4: raise AuthError("LOGIN_EXCHANGE_LIMIT")
            self._exchanges+=1
        try:
            with self._client(transaction.state) as client:
                token=client.fetch_token(self.config.issuer+"/protocol/openid-connect/token",code=code,
                    grant_type="authorization_code",code_verifier=transaction.verifier)
            if token.get("token_type","").casefold()!="bearer": raise AuthError("INVALID_TOKEN")
            identity=self.verifier.login_identity(token.get("id_token"),token.get("access_token"),transaction.nonce)
            return self.sessions.issue(identity)
        except Exception as exc:
            raise AuthError("LOGIN_FAILED") from exc

def discover_verifier(config,transport=None):
    """One explicit bootstrap discovery and JWKS fetch; never a per-request lookup."""
    with httpx.Client(transport=transport,trust_env=False,follow_redirects=False,timeout=5) as client:
        def fetch(url,limit):
            u=urlsplit(url);base=urlsplit(config.issuer)
            if (u.scheme,u.netloc)!=(base.scheme,base.netloc) or u.username or u.query or u.fragment: raise AuthError("UNTRUSTED_DISCOVERY_URL")
            with client.stream("GET",url) as response:
                if response.status_code!=200: raise AuthError("DISCOVERY_FAILED")
                chunks=[];size=0
                for chunk in response.iter_bytes():
                    size+=len(chunk)
                    if size>limit: raise AuthError("DISCOVERY_LIMIT")
                    chunks.append(chunk)
            from .wire import strict_json
            return strict_json(b"".join(chunks))
        metadata=fetch(config.issuer+"/.well-known/openid-configuration",16384)
        if metadata.get("issuer")!=config.issuer: raise AuthError("ISSUER_MISMATCH")
        expected=config.issuer+"/protocol/openid-connect/"
        if metadata.get("authorization_endpoint")!=expected+"auth" or metadata.get("token_endpoint")!=expected+"token": raise AuthError("ENDPOINT_MISMATCH")
        return TokenVerifier(config,fetch(metadata["jwks_uri"],131072))
