"""Focused V4 package-boundary tests. No network, no real manifests or ledger."""
import ast
import json
import socket
import sys
from pathlib import Path

import pytest

from scripts import nlip_phase2b2_launcher as l
from scripts import nlip_phase2b5_bootstrap as b
from scripts import nlip_phase2b5_execution as e


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw):
        raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def test_v4_inventory_is_versioned_and_distinct():
    assert l.V4_INVENTORY.name == 'inventory-v4-linux-v1.json'
    assert l.V4_INVENTORY != l.INVENTORY
    assert 'phase2b5e' in str(l.V4_INVENTORY)


def test_default_inventory_unchanged_for_v1_v2_v3():
    assert l.INVENTORY.name == ('inventory-smoke-v2.json' if sys.platform == 'linux'
                                else 'inventory-phase2b5-macos-v1.json')


def test_v4_package_format_is_recognised():
    assert 'phase2b5e-v4-linux-package-v1' in b.INVENTORY_FORMATS
    assert 'phase2b5a-linux-package-v1' in b.INVENTORY_FORMATS


def test_runtime_reuse_covers_v4_package_format():
    source = Path(e.__file__).read_text()
    tree = ast.parse(source)
    reuse = [node for node in ast.walk(tree)
             if isinstance(node, ast.Assign) and any(
                 isinstance(t, ast.Name) and t.id == 'reuse' for t in node.targets)]
    assert reuse, 'REUSE_SELECTION_MISSING'
    rendered = ast.unparse(reuse[0])
    assert 'phase2b5a-linux-package-v1' in rendered
    assert 'phase2b5e-v4-linux-package-v1' in rendered


def test_bootstrap_rejects_unlisted_inventory_name():
    """An unlisted inventory path fails closed before any bytes are read."""
    source = Path(b.__file__).read_text()
    assert "need(inventory_name in (INVENTORY_V3, INVENTORY_V4), 'PACKAGE_INVENTORY_SELECTION')" in source


def test_bootstrap_v3_inventory_name_is_unchanged():
    assert b.INVENTORY_V3 == 'docs/research/phase2b5a/inventory-smoke-v2.json'
    assert b.INVENTORY_V4 == 'docs/research/phase2b5e/inventory-v4-linux-v1.json'


def test_bootstrap_exposes_only_bounded_hosted_actions():
    """Hosted execution must be reachable only through the genuine-transport actions."""
    source = Path(b.__file__).read_text()
    assert "'v4-hosted-first-cell','v4-hosted-smoke'" in source
    assert "protocol='v4-hosted')" in source and "protocol='v4-hosted-smoke')" in source
    # Those actions must never accept offline I/O.
    branch = source.split("args.action in ('v4-hosted-first-cell','v4-hosted-smoke')")[1]
    branch = branch.split('    else:')[0]
    assert 'offline_io' not in branch


def test_v4_hosted_rejects_v3_default_inventory(monkeypatch):
    monkeypatch.setattr(l, 'INVENTORY', l.ROOT / 'docs/research/phase2b5a/inventory-smoke-v2.json')
    with pytest.raises(l.GateError, match='V4_PACKAGE_INVENTORY_MISMATCH'):
        l._first_cell_orchestration(Path('/nonexistent'), [], authorization_window=(0, 1),
                                    package_digest='0' * 64, protocol='v4-hosted', direct=True)


def test_synthetic_v4_is_not_blocked_by_inventory_guard(monkeypatch):
    monkeypatch.setattr(l, 'INVENTORY', l.ROOT / 'docs/research/phase2b5a/inventory-smoke-v2.json')
    with pytest.raises(l.GateError) as error:
        l._first_cell_orchestration(Path('/nonexistent'), [], authorization_window=(0, 1),
                                    package_digest='0' * 64, protocol='v4', direct=True)
    assert 'V4_PACKAGE_INVENTORY_MISMATCH' not in str(error.value)
