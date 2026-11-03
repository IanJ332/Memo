# SPDX-License-Identifier: MIT
"""Bounded loopback-only HTTP/1.1 development bridge to the real ASGI app.

Uses the standard-library HTTP parser; no production server/TLS claim.
"""
import asyncio
import threading
import socket
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .wire import MAX_BODY

class LoopbackServer(ThreadingHTTPServer):
    daemon_threads=True
    block_on_close=True

@contextmanager
def serve_loopback(application):
    class Handler(BaseHTTPRequestHandler):
        protocol_version="HTTP/1.1"
        def log_message(self,*args): pass
        def setup(self):
            super().setup();self.connection.settimeout(5);self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        def handle_request(self):
            lengths=self.headers.get_all("Content-Length",[])
            if self.headers.get("Transfer-Encoding") or len(lengths)>1:
                self.send_error(400);self.close_connection=True;return
            try:
                length=int(lengths[0]) if lengths else 0
                if length<0 or length>MAX_BODY: raise ValueError()
            except ValueError:
                self.send_error(413);self.close_connection=True;return
            body=self.rfile.read(length)
            if len(body)!=length: self.close_connection=True;return
            u=urlsplit(self.path)
            if not self.path.startswith("/") or u.scheme or u.netloc:
                self.send_error(400);self.close_connection=True;return
            scope={"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","scheme":"http",
                "method":self.command,"path":u.path,"raw_path":u.path.encode(),"query_string":u.query.encode(),
                "headers":[(k.lower().encode(),v.encode('latin-1')) for k,v in self.headers.items()],
                "client":self.client_address,"server":self.server.server_address,"root_path":""}
            events=[];received=False
            async def receive():
                nonlocal received
                if received: return {"type":"http.disconnect"}
                received=True;return {"type":"http.request","body":body,"more_body":False}
            async def send(event): events.append(event)
            try: asyncio.run(application(scope,receive,send))
            except Exception:
                self.send_error(503);self.close_connection=True;return
            start=next(e for e in events if e["type"]=="http.response.start")
            payload=b"".join(e.get("body",b"") for e in events if e["type"]=="http.response.body")
            self.send_response(start["status"])
            for key,value in start.get("headers",[]):
                if key.lower()!=b"content-length": self.send_header(key.decode(),value.decode())
            self.send_header("Content-Length",str(len(payload)));self.end_headers();self.wfile.write(payload)
        do_GET=handle_request
        do_POST=handle_request
    server=LoopbackServer(("127.0.0.1",0),Handler)
    origin=f"http://127.0.0.1:{server.server_port}"
    if hasattr(application,"origin"):
        application.origin=origin
        application.secure=False
        if application.login is not None:
            from dataclasses import replace
            if not application.login.config.development_loopback: raise ValueError("EXPLICIT_DEVELOPMENT_PROFILE_REQUIRED")
            application.login.config=replace(application.login.config,redirect_uri=origin+"/auth/callback")
    app=application.app if hasattr(application,"app") else application
    # Handler closes over the callable, while the host application's origin is updated before requests.
    application=app
    thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.02),daemon=True);thread.start()
    try: yield origin
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
