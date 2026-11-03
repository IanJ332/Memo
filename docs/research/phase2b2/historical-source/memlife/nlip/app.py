# SPDX-License-Identifier: MIT
"""NLIP development endpoint; identities and authority are never taken from content."""
import time
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from .agent import request_proposal
from .auth import AuthError
from .jetstream import ModelOutcomeError
from .policy import identifier
from .wire import MAX_BODY, Message, Part, WireError, encode, parse_message, strict_json

class ReportApplication:
    def __init__(self,sessions,policy,dispatcher,notes,adapter,*,origin,login=None):
        u=urlsplit(origin)
        if u.scheme not in {"https","http"} or not u.hostname or u.path or u.query or u.fragment or u.username:
            raise ValueError("INVALID_APP_ORIGIN")
        if u.scheme=="http" and u.hostname not in {"127.0.0.1","localhost","::1"}: raise ValueError("DEVELOPMENT_LOOPBACK_ONLY")
        self.sessions=sessions;self.policy=policy;self.dispatcher=dispatcher
        self.notes=notes;self.adapter=adapter;self.origin=origin;self.login=login
        self.secure=u.scheme=="https"
        self.app=Starlette(debug=False,routes=[Route("/nlip",self.nlip,methods=["POST"]),
            Route("/notes",self.ingest,methods=["POST"]),Route("/auth/login",self.begin,methods=["GET"]),
            Route("/auth/callback",self.callback,methods=["GET"]),Route("/auth/logout",self.logout,methods=["POST"])])
    def identity(self,request):
        # Reject duplicate credential/authority-relevant headers before normalization.
        for key in ("cookie","origin","host","x-csrf-token"):
            if len(request.headers.getlist(key))!=1: raise AuthError("INVALID_REQUEST_BINDING")
        if request.headers["origin"]!=self.origin or request.headers["host"]!=urlsplit(self.origin).netloc:
            raise AuthError("INVALID_REQUEST_ORIGIN")
        session=self.sessions.get(request.cookies.get("memlife_session"))
        from .auth import safe_equal
        if not safe_equal(request.headers["x-csrf-token"],session.csrf): raise AuthError("INVALID_CSRF")
        return session
    async def body(self,request):
        size=0;chunks=[]
        async for chunk in request.stream():
            size+=len(chunk)
            if size>MAX_BODY: raise WireError("BODY_LIMIT")
            chunks.append(chunk)
        return b"".join(chunks)
    def reply(self,message,content,status=200,text=False):
        return Response(encode(message.response(content,text)),status_code=status,media_type="application/json",
                        headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})
    async def nlip(self,request):
        message=None;start=time.perf_counter_ns()
        try:
            identity_start=time.perf_counter_ns();session=self.identity(request);identity_ns=time.perf_counter_ns()-identity_start
            if len(request.headers.getlist("content-type"))!=1 or request.headers["content-type"].split(";")[0].strip().casefold()!="application/json":
                raise WireError("JSON_CONTENT_TYPE_REQUIRED")
            parse_start=time.perf_counter_ns();message=parse_message(await self.body(request));parse_ns=time.perf_counter_ns()-parse_start
            binding_start=time.perf_counter_ns()
            conversations=[p for p in message.parts if p.kind=="token" and p.subtype=="conversation_memlife"]
            from .auth import safe_equal
            if len(conversations)!=1 or not safe_equal(conversations[0].content,session.conversation): raise AuthError("CONVERSATION_SESSION_MISMATCH")
            auth_ns=identity_ns+time.perf_counter_ns()-binding_start
            if message.is_control:
                return self.reply(message,"Text English and structured JSON sharing supported; optional uploads unavailable.",text=True)
            if any(p.kind not in {"text","structured","token"} or (p.kind=="structured" and p.subtype!="json") or (p.kind=="text" and p.subtype!="english") for p in message.parts):
                return self.reply(message,"Unsupported application content; no tool action was proposed.",text=True)
            requested=request_proposal(message)
            current=self.policy.current(session.principal,requested.arguments["project_id"])
            if not current.known_project or not current.principal_allowed:
                return self.reply(message,{"action":"DENY","reason":"PRINCIPAL_UNAUTHORIZED","delivered":False,"policy_revision":current.revision},403)
            proposal_start=time.perf_counter_ns()
            proposal=self.adapter.propose(message,self.notes.read(session.principal,requested.arguments["project_id"]))
            proposal_ns=time.perf_counter_ns()-proposal_start
            result=self.dispatcher.dispatch(session.principal,session,proposal.tool,proposal.arguments)
            return self.reply(message,{**result.decision.as_dict(),"delivered":result.delivered,
                "timing_ns":{"session":auth_ns,"security":result.security_ns,"dispatch":result.total_ns,"parse":parse_ns,"proposal":proposal_ns,"sink_commit":result.sink_ns}})
        except ModelOutcomeError as exc:
            # No proposal means no dispatcher invocation; this is a model outcome,
            # not a fabricated authorization DENY or a successful defense.
            return self.reply(message,{"model_status":exc.status,"delivered":False,
                "security_decision":None},200 if exc.status in {"REFUSAL","NO_TOOL_CALL","MALFORMED"} else 503)
        except AuthError:
            return self.reply(message or Message(Part("text","English",""),()),{"action":"DENY","reason":"AUTHENTICATION_FAILED","delivered":False},401)
        except (WireError,ValueError):
            return self.reply(message or Message(Part("text","English",""),()),{"action":"DENY","reason":"MALFORMED_REQUEST","delivered":False},400)
        except Exception:
            return self.reply(message or Message(Part("text","English",""),()),{"action":"DENY","reason":"APPLICATION_UNAVAILABLE","delivered":False},503)
    async def ingest(self,request):
        try:
            session=self.identity(request);value=strict_json(await self.body(request))
            if not isinstance(value,dict) or set(value)!={"project_id","content"} or not identifier(value["project_id"],64): raise ValueError()
            policy=self.policy.current(session.principal,value["project_id"])
            if not policy.known_project or not policy.principal_allowed: raise AuthError("PRINCIPAL_UNAUTHORIZED")
            self.notes.append(session.principal,value["project_id"],value["content"])
            return JSONResponse({"stored":True},headers={"Cache-Control":"no-store"})
        except AuthError: return JSONResponse({"stored":False,"reason":"AUTHENTICATION_FAILED"},401)
        except (ValueError,WireError): return JSONResponse({"stored":False,"reason":"MALFORMED_NOTE"},400)
        except Exception: return JSONResponse({"stored":False,"reason":"APPLICATION_UNAVAILABLE"},503)
    async def begin(self,request):
        if self.login is None: return JSONResponse({"reason":"OIDC_RUNTIME_NOT_CONFIGURED"},503)
        if request.headers.get("host")!=urlsplit(self.origin).netloc: return JSONResponse({"reason":"INVALID_HOST"},400)
        browser,url=self.login.begin();response=RedirectResponse(url,302)
        response.set_cookie("memlife_login",browser,secure=self.secure,httponly=True,samesite="lax",max_age=300,path="/auth")
        response.headers["Cache-Control"]="no-store"
        return response
    async def callback(self,request):
        try:
            if self.login is None or request.headers.get("host")!=urlsplit(self.origin).netloc: raise AuthError("INVALID_CALLBACK")
            keys=set(request.query_params)
            if not {"state","code"}<=keys or keys-{"state","code","session_state","iss"} or any(len(request.query_params.getlist(k))!=1 for k in keys): raise AuthError("INVALID_CALLBACK")
            if "iss" in keys and request.query_params["iss"]!=self.login.config.issuer: raise AuthError("ISSUER_MISMATCH")
            session=self.login.callback(request.cookies.get("memlife_login"),request.query_params["state"],request.query_params["code"])
            response=JSONResponse({"authenticated":True,"csrf":session.csrf,"conversation":session.conversation},headers={"Cache-Control":"no-store"})
            response.set_cookie("memlife_session",session.sid,secure=self.secure,httponly=True,samesite="strict",max_age=max(0,session.expires_at-int(self.sessions.clock())),path="/")
            response.delete_cookie("memlife_login",path="/auth")
            return response
        except Exception: return JSONResponse({"authenticated":False,"reason":"LOGIN_FAILED"},401,headers={"Cache-Control":"no-store"})
    async def logout(self,request):
        try:
            session=self.identity(request);self.sessions.logout(session.sid)
            response=JSONResponse({"logged_out":True},headers={"Cache-Control":"no-store"})
            response.delete_cookie("memlife_session",path="/")
            return response
        except AuthError: return JSONResponse({"reason":"AUTHENTICATION_FAILED"},401)
