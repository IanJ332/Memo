"""Deny Python socket/DNS operations before syscalls; pair with macOS sandbox."""

from __future__ import annotations

import sys

DENIED_EVENTS: list[str] = []


class NetworkDenied(RuntimeError):
    pass


def _audit(event: str, args: tuple) -> None:
    if event.startswith("socket."):
        DENIED_EVENTS.append(event)
        raise NetworkDenied(f"offline qualification forbids {event}")
    if event == "import" and args[0].startswith("hindsight"):
        raise RuntimeError("Hindsight imports are outside SDK-only authorization")


def activate() -> None:
    sys.addaudithook(_audit)


def verify_denial() -> dict:
    import socket
    start = len(DENIED_EVENTS)
    for operation in (lambda: socket.socket(), lambda: socket.getaddrinfo("sdk.test", 443)):
        try:
            operation()
        except NetworkDenied:
            pass
        else:
            raise RuntimeError("STOP: socket/DNS denial failed")
    if len(DENIED_EVENTS) - start != 2:
        raise RuntimeError("STOP: unexpected network-denial event count")
    return {"socket_creation_denied_before_syscall": True, "dns_denied_before_syscall": True,
            "denied_self_test_events": DENIED_EVENTS[start:]}
