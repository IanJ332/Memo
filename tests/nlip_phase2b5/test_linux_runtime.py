"""Offline controls for disposable Linux qualification tooling."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[2] / 'scripts/nlip_phase2b5_runtime.py'
SPEC = importlib.util.spec_from_file_location('phase2b5_runtime', SOURCE)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class Distribution:
    def __init__(self, base, record):
        self.base, self.record = base, record
    def read_text(self, name):
        assert name == 'RECORD'
        return self.record
    def locate_file(self, name):
        return self.base / name


def record_line(name, body):
    encoded = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode()
    return f'{name},sha256={encoded},{len(body)}\n'


def test_record_checks_bytes_not_only_record_metadata(tmp_path):
    p = tmp_path / 'module.py'; p.write_bytes(b'good')
    distribution = Distribution(tmp_path, record_line('module.py', b'good'))
    assert runtime.verify_record(distribution, tmp_path)['hashed_files_verified'] == 1
    p.write_bytes(b'evil')
    with pytest.raises(runtime.QualificationError, match='RECORD_HASH_MISMATCH'):
        runtime.verify_record(distribution, tmp_path)


def test_record_rejects_escape_and_symlink(tmp_path):
    prefix = tmp_path / 'venv'; prefix.mkdir()
    outside = tmp_path / 'outside.py'; outside.write_bytes(b'x')
    dist = Distribution(prefix, record_line('../outside.py', b'x'))
    with pytest.raises(runtime.QualificationError, match='RECORD_ESCAPE'):
        runtime.verify_record(dist, prefix)
    (prefix / 'link.py').symlink_to(outside)
    with pytest.raises(runtime.QualificationError, match='RECORD_ESCAPE'):
        runtime.verify_record(Distribution(prefix, record_line('link.py', b'x')), prefix)


def test_record_rejects_unhashed_source(tmp_path):
    (tmp_path / 'module.py').write_bytes(b'')
    with pytest.raises(runtime.QualificationError, match='UNHASHED_NON_BYTECODE'):
        runtime.verify_record(Distribution(tmp_path, 'module.py,,\n'), tmp_path)


def test_record_rejects_size_and_duplicates(tmp_path):
    (tmp_path / 'module.py').write_bytes(b'x')
    row = record_line('module.py', b'x')
    with pytest.raises(runtime.QualificationError, match='RECORD_SIZE_MISMATCH'):
        runtime.verify_record(Distribution(tmp_path, row.replace(',1\n', ',2\n')), tmp_path)
    with pytest.raises(runtime.QualificationError, match='RECORD_DUPLICATE_OR_MISSING'):
        runtime.verify_record(Distribution(tmp_path, row + row), tmp_path)


def test_disposable_storage_exclusion_and_interruption_recovery(tmp_path):
    directory = tmp_path / 'fresh-probes'
    result = runtime.storage_probes(directory)
    assert result['killed_process_recovery'] == 'PASS'
    assert result['sqlite_cross_process_lock'] == 'PASS'
    assert result['fcntl_cross_process_lock'] == 'PASS'
    assert result['power_loss_durability'] == 'NOT_TESTED'
    assert result['scientific_attempts_consumed'] == 0
    for p in directory.iterdir():
        assert stat.S_IMODE(p.stat().st_mode) & 0o077 == 0
    with pytest.raises(runtime.QualificationError, match='MUST_BE_FRESH'):
        runtime.storage_probes(directory)


def test_no_global_or_wrong_interpreter_is_qualified(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.sys, 'platform', 'linux')
    monkeypatch.setattr(runtime, 'safe_ancestors', lambda *a, **k: None)
    with pytest.raises(runtime.QualificationError, match='ISOLATED_NO_BYTECODE_REQUIRED|REPOSITORY_VENV_REQUIRED|EXECUTABLE_SELECTION'):
        runtime.runtime_metadata(tmp_path)


def no_site_venv(tmp_path, monkeypatch):
    root = tmp_path / 'source'; root.mkdir(mode=0o700)
    prefix = root / '.venv'; prefix.mkdir(mode=0o700)
    binary = prefix / 'bin' / 'python'; binary.parent.mkdir(mode=0o700)
    base_binary = tmp_path / 'base-python'; base_binary.write_bytes(b'fake-selection-only')
    binary.symlink_to(base_binary)
    (prefix / 'pyvenv.cfg').write_text(
        'include-system-site-packages = false\n' +
        'version = ' + runtime.platform.python_version() + '\n' +
        'executable = ' + str(base_binary) + '\n')
    directory = prefix / 'lib' / f'python{runtime.sys.version_info.major}.{runtime.sys.version_info.minor}' / 'site-packages'
    directory.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(runtime, 'safe_ancestors', lambda *a, **k: None)
    monkeypatch.setattr(runtime.sys, 'executable', str(binary))
    monkeypatch.setattr(runtime.sys, 'prefix', runtime.sys.base_prefix)
    monkeypatch.setattr(runtime.sys, 'flags', SimpleNamespace(no_site=True))
    monkeypatch.setattr(runtime.sys, 'path', ['/usr/lib/python3.12'])
    monkeypatch.setattr(runtime.site, 'ENABLE_USER_SITE', None)
    for name in ('sitecustomize', 'usercustomize'):
        monkeypatch.delitem(runtime.sys.modules, name, raising=False)
    return root, prefix, directory


def test_no_site_selects_explicit_venv_and_reports_actual_base_prefix(tmp_path, monkeypatch):
    with monkeypatch.context() as m:
        root, prefix, directory = no_site_venv(tmp_path, m)
        selected, directories, isolation = runtime.selected_venv(root)
        assert selected == prefix and directories == [directory]
        assert isolation['prefix'] == runtime.sys.base_prefix
        assert isolation['selected_venv_prefix'] == str(prefix)
        assert isolation['no_site'] is True
        assert isolation['selection'] == 'INVOKED_EXECUTABLE_AND_CONFIG'


def test_no_site_rejects_config_disagreement_and_package_path(tmp_path, monkeypatch):
    with monkeypatch.context() as m:
        root, prefix, directory = no_site_venv(tmp_path, m)
        m.setattr(runtime.sys, 'path', [str(directory)])
        with pytest.raises(runtime.QualificationError, match='NO_SITE_PACKAGE_PATH'):
            runtime.selected_venv(root)
        m.setattr(runtime.sys, 'path', ['/usr/lib/python3.12'])
        config = prefix / 'pyvenv.cfg'
        config.write_text(config.read_text().replace('= false', '= true'))
        with pytest.raises(runtime.QualificationError, match='GLOBAL_SITE_ENABLED'):
            runtime.selected_venv(root)


def test_no_site_still_rejects_hook_files(tmp_path, monkeypatch):
    with monkeypatch.context() as m:
        root, _, directory = no_site_venv(tmp_path, m)
        (directory / 'sitecustomize.py').write_text('raise RuntimeError("must never run")')
        with pytest.raises(runtime.QualificationError, match='SITE_HOOK_PRESENT'):
            runtime.selected_venv(root)


def test_selected_venv_directory_symlink_is_rejected(tmp_path):
    actual = tmp_path / 'external'; actual.mkdir()
    link = tmp_path / '.venv'; link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(runtime.QualificationError, match='PATH_NOT_ABSOLUTE_CANONICAL'):
        runtime.safe_ancestors(link)


def test_builtin_native_identity_binds_actual_interpreter():
    import sys
    result = runtime.native_identity('sys', sys)
    assert result['kind'] == 'BUILTIN'
    assert result['module'] == 'sys'
    assert result['interpreter_sha256'] == runtime.digest(Path(sys.executable).resolve())
    assert 'path' not in result and 'sha256' not in result


def test_builtin_native_identity_rejects_unregistered_or_missing_origin():
    fake = SimpleNamespace(__name__='unregistered_native',
        __spec__=SimpleNamespace(name='unregistered_native', origin='built-in',
                                loader=runtime.importlib.machinery.BuiltinImporter))
    with pytest.raises(runtime.QualificationError, match='NATIVE_BUILTIN_IDENTITY'):
        runtime.native_identity('unregistered_native', fake)
    fake.__spec__.origin = None
    with pytest.raises(runtime.QualificationError, match='NATIVE_MODULE_ORIGIN'):
        runtime.native_identity('unregistered_native', fake)


def test_extension_native_identity_hashes_actual_native_file():
    import _sqlite3
    result = runtime.native_identity('_sqlite3', _sqlite3)
    if _sqlite3.__spec__.origin == 'built-in':
        assert result['kind'] == 'BUILTIN'
    else:
        assert result['kind'] == 'EXTENSION'
        assert result['sha256'] == runtime.digest(_sqlite3.__file__)
