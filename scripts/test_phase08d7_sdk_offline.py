"""Exercise installed SDK/HTTPX and scripted HTTPCore with zero real sockets.

MockTransport counts HTTPX dispatches, not HTTPCore physical sends. Scripted
HTTPCore streams exercise real HTTP/1.1 serialization with simulated TLS only.
Run under the deny-network macOS sandbox and the exact SDK-only venv.
"""

from __future__ import annotations

import asyncio
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import sys

from phase08d7_offline_guard import activate, verify_denial, DENIED_EVENTS
from acquire_phase08d7_sdk import ROOT, PLAN_SHA256, load_plan

activate()  # Before SDK/transport imports; no Python socket syscall is allowed.

import httpcore
import httpx
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, APIStatusError
from openai import DefaultAsyncHttpxClient


class PipeEnd:
    def __init__(self, fd: int):
        self.fd = fd
    def fileno(self):
        return self.fd
    def recv(self, size):
        return os.read(self.fd, size)
    def send(self, value):
        return os.write(self.fd, value)
    def close(self):
        os.close(self.fd)


class PipeLoop(asyncio.SelectorEventLoop):
    """Replace asyncio's socketpair wakeup with nonblocking OS pipes."""
    def _make_self_pipe(self):
        read_fd, write_fd = os.pipe()
        os.set_blocking(read_fd, False)
        os.set_blocking(write_fd, False)
        self._ssock, self._csock = PipeEnd(read_fd), PipeEnd(write_fd)
        self._internal_fds += 1
        self._add_reader(read_fd, self._read_from_self)


def completion():
    return {"id": "chatcmpl-offline", "object": "chat.completion", "created": 1,
            "model": "offline-model", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "offline"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


def request_identity(request):
    if request.url.scheme != "https" or not request.url.host.endswith(".test"):
        raise RuntimeError("STOP: unexpected transport destination")
    body = request.content
    try:
        model = json.loads(body).get("model")
    except (ValueError, UnicodeDecodeError):
        model = None
    return {"method": request.method, "url": str(request.url), "model": model,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "authorization_present": "authorization" in request.headers,
            "default_header_present": request.headers.get("x-offline-default") == "yes",
            "extra_header_present": request.headers.get("x-offline-extra") == "yes"}


class CounterTransport(httpx.AsyncBaseTransport):
    def __init__(self, delegate):
        self.delegate, self.requests = delegate, []
    async def handle_async_request(self, request):
        await request.aread()
        self.requests.append(request_identity(request))
        return await self.delegate.handle_async_request(request)
    async def aclose(self):
        await self.delegate.aclose()


class SDKCase:
    def __init__(self, transport, retries=0, follow=None, **options):
        self.transport = CounterTransport(transport)
        client_options = {"transport": self.transport, "trust_env": False}
        if follow is not None:
            client_options["follow_redirects"] = follow
        self.http = DefaultAsyncHttpxClient(**client_options)
        self.sdk = AsyncOpenAI(api_key="synthetic-offline-key", base_url="https://sdk.test/v1/",
                               max_retries=retries, http_client=self.http, **options)
        self.invocations = 0
        self.receipts = 0
    async def call(self, resource=None, **kwargs):
        self.invocations += 1
        create = resource or self.sdk.chat.completions.create
        result = await create(model="offline-model", messages=[{"role": "user", "content": "offline"}],
                              max_tokens=5, **kwargs)
        if getattr(result, "usage", None):
            assert result.usage.total_tokens == 2
            self.receipts += 1
        return result
    async def close(self):
        await self.sdk.close()
        assert self.http.is_closed
    def result(self, name, layer="HTTPX_MOCKTRANSPORT", **extra):
        return {"name": name, "status": "PASS", "layer": layer,
                "sdk_invocations": self.invocations, "transport_requests": len(self.transport.requests),
                "usage_receipts": self.receipts, "requests": self.transport.requests,
                "actual_socket_transmissions": 0, **extra}


async def expect_error(operation, kind):
    try:
        await operation
    except kind:
        return
    raise AssertionError(f"expected {kind.__name__}")


def mock_sequence(actions):
    actions = deque(actions)
    async def handler(request):
        if not actions:
            raise RuntimeError("STOP: unexpected extra transport request")
        action = actions.popleft()
        if isinstance(action, str):
            if action == "connect":
                raise httpx.ConnectError("synthetic", request=request)
            if action == "timeout":
                raise httpx.ReadTimeout("synthetic", request=request)
            if action == "cancel":
                raise asyncio.CancelledError()
            raise AssertionError(action)
        status, headers = action
        return httpx.Response(status, headers=headers, json=completion() if status == 200 else
                              {"error": {"message": "synthetic", "type": "offline"}})
    return httpx.MockTransport(handler)


class ScriptedStream(httpcore.AsyncNetworkStream):
    def __init__(self, backend, response):
        self.backend, self.response = backend, response
        self.closed = False
    async def read(self, max_bytes, timeout=None):
        if self.response == "timeout":
            raise httpcore.ReadTimeout("synthetic")
        value, self.response = self.response[:max_bytes], self.response[max_bytes:]
        return value
    async def write(self, buffer, timeout=None):
        self.backend.raw_writes += 1
        if buffer.startswith((b"POST ", b"GET ")):
            self.backend.request_starts += 1
    async def aclose(self):
        self.closed = True
    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        if not server_hostname.endswith(".test"):
            raise RuntimeError("STOP: unexpected simulated TLS destination")
        self.backend.tls_starts += 1
        return self  # Explicit simulation; no TLS/socket qualification claim.
    def get_extra_info(self, info):
        return False if info == "is_readable" else None


class ScriptedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, actions):
        self.actions = deque(actions)
        self.connect_attempts = self.raw_writes = self.request_starts = self.tls_starts = 0
        self.retry_sleeps = 0
        self.streams = []
    async def connect_tcp(self, host, port, **kwargs):
        if not host.endswith(".test") or port != 443:
            raise RuntimeError("STOP: unexpected scripted connection destination")
        self.connect_attempts += 1
        if not self.actions:
            raise RuntimeError("STOP: unexpected scripted connection attempt")
        action = self.actions.popleft()
        if action == "connect":
            raise httpcore.ConnectError("synthetic")
        stream = ScriptedStream(self, action)
        self.streams.append(stream)
        return stream
    async def connect_unix_socket(self, *args, **kwargs):
        raise RuntimeError("STOP: Unix sockets are forbidden")
    async def sleep(self, seconds):
        self.retry_sleeps += 1  # Deterministic transport retry; no wall-clock delay.


def wire_response(status=200, location=None):
    body = json.dumps(completion() if status == 200 else {"error": {"message": "synthetic"}}).encode()
    header = f"HTTP/1.1 {status} Synthetic\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: {len(body)}\r\n"
    if location:
        header += f"Location: {location}\r\n"
    return header.encode() + b"\r\n" + body


async def tests():
    results = []
    # Inspect a genuine SDK-owned HTTP client before replacing nothing or sending.
    native = AsyncOpenAI(api_key="synthetic-offline-key", base_url="https://sdk.test/v1/", max_retries=0)
    defaults = {"sdk_max_retries": native.max_retries,
                "httpx_follow_redirects": native._client.follow_redirects,
                "httpx_trust_env": native._client._trust_env}
    assert defaults == {"sdk_max_retries": 0, "httpx_follow_redirects": True, "httpx_trust_env": True}
    await native.close()
    results.append({"name": "sdk_owned_client_defaults", "status": "PASS", "configuration": defaults,
                    "sdk_invocations": 0, "transport_requests": 0})
    case = SDKCase(mock_sequence([(200, {})]))
    await case.call(tools=[{"type": "function", "function": {"name": "offline", "parameters": {"type": "object"}}}])
    assert case.invocations == len(case.transport.requests) == case.receipts == 1
    await case.close()
    results.append(case.result("chat_tools_success"))
    for action, kind in [(429, APIStatusError), (500, APIStatusError), ("connect", APIConnectionError),
                         ("timeout", APITimeoutError)]:
        for retries in (0, 1):
            failure = (action, {"retry-after-ms": "1"}) if isinstance(action, int) else action
            actions = [failure] + ([(200, {})] if retries else [])
            case = SDKCase(mock_sequence(actions), retries=retries)
            if retries:
                await case.call()
            else:
                await expect_error(case.call(), kind)
            assert case.invocations == 1 and len(case.transport.requests) == retries + 1
            assert case.receipts == retries
            await case.close()
            results.append(case.result(f"sdk_{action}_retries_{retries}"))
    for status in (307, 308):
        for other in (False, True):
            for follow in (None, False):
                destination = "https://other.test/v1/chat/completions" if other else "https://sdk.test/v1/moved"
                actions = [(status, {"location": destination})] + ([(200, {})] if follow is None else [])
                case = SDKCase(mock_sequence(actions), follow=follow)
                if follow is False:
                    await expect_error(case.call(), APIStatusError)
                    assert len(case.transport.requests) == 1
                else:
                    await case.call()
                    assert len(case.transport.requests) == 2
                    assert case.transport.requests[1]["authorization_present"] is (not other)
                    assert case.transport.requests[1]["method"] == "POST"
                await case.close()
                results.append(case.result(f"redirect_{status}_{'cross' if other else 'same'}_{'default' if follow is None else 'disabled'}"))
    os.environ["HTTPS_PROXY"] = "http://proxy.test:8080"
    case = SDKCase(mock_sequence([(200, {})]), default_query={"tenant": "offline"},
                   default_headers={"X-Offline-Default": "yes"})
    try:
        assert case.http._trust_env is False and not any(case.http._mounts.values())
        case.sdk.base_url = "https://sdk.test/prefix/v1/"
        await case.call(extra_query={"mode": "test"}, extra_headers={"X-Offline-Extra": "yes"})
        request = case.transport.requests[0]
        assert request["url"] == "https://sdk.test/prefix/v1/chat/completions?tenant=offline&mode=test"
        assert request["default_header_present"] and request["extra_header_present"]
    finally:
        del os.environ["HTTPS_PROXY"]
        await case.close()
    results.append(case.result("routing_defaults_overrides_proxy_disabled"))
    case = SDKCase(mock_sequence([(200, {})]))
    await case.call(extra_body={"model": "overridden-model"})
    assert case.transport.requests[0]["model"] == "overridden-model"
    await case.close()
    results.append(case.result("extra_body_changes_wire_model"))
    case = SDKCase(mock_sequence([(200, {}), (200, {})]))
    retained = case.sdk.chat.completions
    copied = case.sdk.with_options(base_url="https://other.test/v1/")
    assert copied._client is case.sdk._client
    await case.call(resource=copied.chat.completions.create)
    await case.call(resource=retained.create)
    assert [r["url"] for r in case.transport.requests] == ["https://other.test/v1/chat/completions", "https://sdk.test/v1/chat/completions"]
    await copied.close()
    assert case.sdk.is_closed()
    results.append(case.result("copy_retained_resource_shared_client_close", shared_client=True))
    owner = SDKCase(mock_sequence([(200, {})]))
    replacement = SDKCase(mock_sequence([(200, {})]))
    replacement.sdk.base_url = "https://other.test/v1/"
    retained = owner.sdk.chat.completions
    owner.sdk.chat.completions = replacement.sdk.chat.completions
    await owner.call()
    await owner.call(resource=retained.create)
    assert len(owner.transport.requests) == len(replacement.transport.requests) == 1
    await owner.close()
    await replacement.close()
    results.append({"name": "resource_replacement_reroutes_client", "status": "PASS",
                    "layer": "HTTPX_MOCKTRANSPORT", "sdk_invocations": owner.invocations,
                    "transport_requests": 2, "original_transport_requests": 1,
                    "replacement_transport_requests": 1, "actual_socket_transmissions": 0})
    case = SDKCase(mock_sequence(["cancel"]))
    await expect_error(case.call(), asyncio.CancelledError)
    assert len(case.transport.requests) == 1 and case.receipts == 0
    await case.close()
    results.append(case.result("cancellation_cleanup_no_usage_receipt"))
    async def resources(request):
        path = request.url.path
        if path.endswith("responses"):
            payload = {"id": "resp_offline", "object": "response", "created_at": 1,
                       "model": "offline-model", "output": []}
        elif path.endswith("files"):
            payload = {"id": "file_offline", "object": "file", "created_at": 1, "bytes": 1,
                       "filename": "offline.txt", "purpose": "batch"}
        elif path.endswith("batches"):
            payload = {"id": "batch_offline", "object": "batch", "created_at": 1,
                       "endpoint": "/v1/chat/completions", "input_file_id": "file_offline",
                       "completion_window": "24h", "status": "validating"}
        else:
            raise AssertionError("unexpected resource")
        return httpx.Response(200, json=payload)
    case = SDKCase(httpx.MockTransport(resources))
    for operation in (lambda: case.sdk.responses.create(model="offline-model", input="offline"),
                      lambda: case.sdk.files.create(file=("offline.txt", b"x"), purpose="batch"),
                      lambda: case.sdk.batches.create(input_file_id="file_offline", endpoint="/v1/chat/completions", completion_window="24h")):
        case.invocations += 1
        await operation()
    assert [r["url"] for r in case.transport.requests] == ["https://sdk.test/v1/responses", "https://sdk.test/v1/files", "https://sdk.test/v1/batches"]
    await case.close()
    results.append(case.result("alternate_http_resources_not_inference_counts"))
    core_cases = [
        ("core_success", [wire_response()], 0, None, 1, 1),
        ("core_connect_no_retry", ["connect"], 0, APIConnectionError, 1, 0),
        ("core_connect_retry_control", ["connect", wire_response()], 1, None, 2, 1),
        ("core_read_timeout", ["timeout"], 0, APITimeoutError, 1, 1),
        ("core_same_host_redirect", [wire_response(307, "https://sdk.test/v1/moved"), wire_response()], 0, None, 2, 2),
        ("core_cross_host_redirect", [wire_response(308, "https://other.test/v1/chat/completions"), wire_response()], 0, None, 2, 2),
    ]
    for name, actions, retries, error, connections, starts in core_cases:
        backend = ScriptedBackend(actions)
        transport = httpx.AsyncHTTPTransport(trust_env=False, retries=retries)
        assert isinstance(transport._pool, httpcore.AsyncConnectionPool)
        transport._pool._network_backend = backend  # Pinned, owned pool only.
        case = SDKCase(transport)
        if error:
            await expect_error(case.call(), error)
        else:
            await case.call()
        assert case.invocations == 1 and backend.connect_attempts == connections
        assert backend.request_starts == starts
        assert len(case.transport.requests) == (2 if "redirect" in name else 1)
        if "cross_host" in name:
            assert not case.transport.requests[1]["authorization_present"]
        await case.close()
        assert all(stream.closed for stream in backend.streams)
        results.append(case.result(name, layer="REAL_HTTPCORE_SCRIPTED_BACKEND_SIMULATED_TLS",
                                   connection_attempts=connections, serialized_http_request_starts=starts,
                                   raw_stream_writes=backend.raw_writes, transport_retry_sleeps=backend.retry_sleeps,
                                   simulated_tls_starts=backend.tls_starts, all_streams_closed=True))
    return results


def main():
    plan = load_plan()
    if Path(sys.prefix) != Path(plan["runtime"]):
        raise RuntimeError("STOP: wrong SDK test environment")
    # macOS adds __CF_USER_TEXT_ENCODING at process startup even after env -i.
    # It is encoding metadata, not a proxy/credential/network setting. The OS
    # sandbox and socket/DNS audit guard stay unchanged.
    if {k: v for k, v in os.environ.items() if k not in {"PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE", "LC_CTYPE", "__CF_USER_TEXT_ENCODING"}}:
        raise RuntimeError("STOP: inherited test environment")
    guard = verify_denial()
    initial_denials = len(DENIED_EVENTS)
    with asyncio.Runner(loop_factory=PipeLoop) as runner:
        results = runner.run(tests())
    if len(DENIED_EVENTS) != initial_denials:
        raise RuntimeError("STOP: SDK tests attempted a real socket or DNS operation")
    if any(name.startswith("hindsight") for name in sys.modules):
        raise RuntimeError("STOP: provider import")
    receipt = {"phase": "08D-7", "scope": "SDK_ONLY", "status": "OFFLINE_TESTS_PASS",
               "authorized_plan_sha256": PLAN_SHA256, "cases_passed": len(results),
               "guard": guard, "sdk_test_socket_or_dns_attempts": 0,
               "actual_socket_transmissions": 0, "event_loop_wakeup": "NONBLOCKING_OS_PIPE_NO_SOCKETPAIR",
               "mocktransport_proves_httpcore_physical_sends": False,
               "core_backend": "SCRIPTED_STREAMS_AND_SIMULATED_TLS_NO_REAL_NETWORK",
               "D3": "PARTIAL", "D4": "BLOCKED", "D5": "PARTIAL", "cases": results}
    with (ROOT / ".local/phase08d7/sdk-offline-tests.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"PASS: {len(results)} offline SDK/HTTPX/HTTPCore cases; zero real socket/DNS attempts")


if __name__ == "__main__":
    main()
