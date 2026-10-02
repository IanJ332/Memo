"""Independent coverage for the complete Phase 07B recovery controller."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import scripts.phase07_hindsight_recovery as recovery


ATTEMPT = "20261002T120000Z-0123456789ab"
RAW_TEXT = "  recovered candidate text\n"
SYNTHETIC_USERNAME = "synthetic_phase04_user"
SYNTHETIC_PASSWORD = "synthetic-only-password-value"
SYNTHETIC_DATABASE = "synthetic_phase04_database"
SYNTHETIC_VERSION = "17.6"


class ScriptedCursor:
    def __init__(self, *, read_only="on", columns=None, row_overrides=None):
        self.read_only = read_only
        self.columns = columns or sorted(recovery.REQUIRED_COLUMNS | {"extra_col"})
        self.row_overrides = row_overrides or {}
        self.calls = []
        self._one = None
        self._all = None

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if query == "BEGIN TRANSACTION READ ONLY;":
            self._one = None
        elif query == "SHOW transaction_read_only;":
            self._one = (self.read_only,)
        elif "information_schema.tables" in query:
            self._one = (1,)
        elif "information_schema.columns" in query:
            self._all = [(column,) for column in self.columns]
        elif query == recovery.TARGET_SELECT:
            memory_id, namespace = params
            override = self.row_overrides.get(namespace, "default")
            target = recovery.ALLOWED_TARGETS[namespace]
            default = [
                (
                    memory_id,
                    namespace,
                    RAW_TEXT,
                    "observation",
                    [target["parent_source"]],
                    "document-1",
                )
            ]
            self._all = default if override == "default" else override
        else:  # pragma: no cover - catches unexpected SQL during failures
            raise AssertionError(f"unexpected SQL: {query}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class ScriptedConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self._cursor

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def expected_text_hash(monkeypatch):
    monkeypatch.setattr(recovery, "EXPECTED_SHA", recovery.compute_sha256(RAW_TEXT.strip()))


@pytest.fixture(autouse=True)
def clear_fresh_cleanup_process_proof(monkeypatch):
    """Unit tests inject a deterministic post-stop proof instead of host /proc."""

    monkeypatch.setattr(recovery, "inspect_linux_processes", lambda: [])


@pytest.fixture
def evidence_tree(tmp_path):
    data_root = tmp_path / "memlife-data"
    data_dir = (
        data_root
        / "providers"
        / "hindsight"
        / "pg0"
        / "instances"
        / recovery.ORIGINAL_INSTANCE_NAME
        / "data"
    )
    (data_dir / "base").mkdir(parents=True)
    (data_dir / "PG_VERSION").write_text("18\n", encoding="ascii")
    (data_dir / "base" / "1").write_bytes(b"database bytes")
    (data_dir.parent / "instance.json").write_text(
        json.dumps(
            {
                "name": recovery.ORIGINAL_INSTANCE_NAME,
                "data_dir": str(data_dir.resolve()),
                "username": SYNTHETIC_USERNAME,
                "password": SYNTHETIC_PASSWORD,
                "database": SYNTHETIC_DATABASE,
                "version": SYNTHETIC_VERSION,
            }
        ),
        encoding="utf-8",
    )
    return data_root, data_dir


class FakePg0:
    def __init__(self, state, **kwargs):
        self.state = state
        self.kwargs = kwargs
        state["kwargs"] = kwargs

    def start(self):
        self.state["start_home"] = Path(recovery.os.environ["HOME"])
        self.state["started"] = True
        callback = self.state.get("on_start")
        if callback:
            callback()
        return SimpleNamespace(
            data_dir=self.kwargs["data_dir"],
            uri="postgresql://postgres:postgres@127.0.0.1:54321/postgres",
            username=self.state.get("reported_username", self.kwargs["username"]),
            database=self.state.get("reported_database", self.kwargs["database"]),
        )

    def stop(self):
        self.state["stop_home"] = Path(recovery.os.environ["HOME"])
        self.state["stopped"] = True
        callback = self.state.get("on_stop")
        if callback:
            callback(self)


def fake_factory(state):
    return lambda **kwargs: FakePg0(state, **kwargs)


def ample_disk(_path):
    return SimpleNamespace(total=10**12, used=0, free=10**12)


@pytest.mark.parametrize("namespace,target", recovery.ALLOWED_TARGETS.items())
def test_all_three_allowlisted_pairs_are_accepted(namespace, target):
    assert recovery.validate_target(namespace, target["id"]) == target


@pytest.mark.parametrize(
    "namespace,memory_id",
    [
        (
            "memlife-freeze-v1-hindsight-S1-r1",
            recovery.ALLOWED_TARGETS["memlife-freeze-v1-hindsight-S1-r2"]["id"],
        ),
        (
            "memlife-freeze-v1-hindsight-S1-r2",
            recovery.ALLOWED_TARGETS["memlife-freeze-v1-hindsight-S1-r3"]["id"],
        ),
        ("wrong-bank", "d21e1d56-8224-4f7b-b144-9e7124fe4ef4"),
    ],
)
def test_cross_paired_or_unknown_targets_are_rejected(namespace, memory_id):
    with pytest.raises(recovery.TargetError):
        recovery.validate_target(namespace, memory_id)


@pytest.mark.parametrize("attempt_id", ["../escape", "ABC", "20261002T120000Z-ABC", ""])
def test_unsafe_attempt_id_is_rejected(attempt_id):
    with pytest.raises(ValueError):
        recovery.validate_attempt_id(attempt_id)


def test_attempt_directory_must_not_preexist(tmp_path):
    original_root = tmp_path / "providers" / "hindsight" / "pg0"
    original_root.mkdir(parents=True)
    (tmp_path / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        recovery.create_attempt_paths(
            tmp_path,
            ATTEMPT,
            original_evidence_root=original_root,
        )


def test_attempt_parent_symlink_escape_is_rejected(tmp_path):
    data_root = tmp_path / "data"
    outside = tmp_path / "outside"
    data_root.mkdir()
    outside.mkdir()
    original_root = data_root / "providers" / "hindsight" / "pg0"
    original_root.mkdir(parents=True)
    try:
        (data_root / "runs").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(recovery.RecoveryError, match="outside MEMLIFE_DATA_ROOT"):
        recovery.create_attempt_paths(
            data_root,
            ATTEMPT,
            original_evidence_root=original_root,
        )
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("link_target", ["root", "data"])
def test_attempt_parent_symlink_into_original_is_rejected_before_mutation(
    evidence_tree, link_target
):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    target = original_root if link_target == "root" else original_data
    before = recovery.compute_tree_identity(original_root)
    before_listing = sorted(
        path.relative_to(original_root).as_posix() for path in original_root.rglob("*")
    )
    try:
        (data_root / "runs").symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(recovery.OriginalSourceGuardError, match="not disjoint"):
        recovery.create_attempt_paths(
            data_root,
            ATTEMPT,
            original_evidence_root=original_root,
        )

    after = recovery.compute_tree_identity(original_root)
    after_listing = sorted(
        path.relative_to(original_root).as_posix() for path in original_root.rglob("*")
    )
    assert after.tree_sha256 == before.tree_sha256
    assert after_listing == before_listing


def test_attempt_parent_ancestor_of_original_is_rejected_before_mutation(evidence_tree):
    data_root, _ = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    runs = data_root / "runs"
    runs.mkdir()
    try:
        (runs / "phase07-hindsight-recovery").symlink_to(
            data_root,
            target_is_directory=True,
        )
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    before = recovery.compute_tree_identity(original_root)
    with pytest.raises(recovery.OriginalSourceGuardError, match="not disjoint"):
        recovery.create_attempt_paths(
            data_root,
            ATTEMPT,
            original_evidence_root=original_root,
        )
    assert recovery.compute_tree_identity(original_root).tree_sha256 == before.tree_sha256


def test_ordinary_sibling_attempt_path_is_accepted(evidence_tree):
    data_root, _ = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    paths = recovery.create_attempt_paths(
        data_root,
        ATTEMPT,
        original_evidence_root=original_root,
    )
    assert paths.root.parent == data_root / recovery.RECOVERY_RUN_DIRECTORY
    assert paths.copy_root.is_dir()
    assert paths.pg0_home.is_dir()


def test_original_data_dir_is_rejected(evidence_tree):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    with pytest.raises(recovery.OriginalSourceGuardError):
        recovery.guard_recovery_data_dir(original_data, original_root, original_data)


def test_symlink_alias_into_original_is_rejected(evidence_tree, tmp_path):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(original_data, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(recovery.OriginalSourceGuardError):
        recovery.guard_recovery_data_dir(alias, original_root, original_data)


def test_provider_running_guard(evidence_tree):
    data_root, _ = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    running = recovery.ProcessSnapshot(12, "hindsight-api", ("hindsight-api",))
    with pytest.raises(recovery.OriginalSourceGuardError, match="appears active"):
        recovery.assert_original_offline(original_root, snapshots=[running])


def test_postgres_using_original_guard(evidence_tree):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    running = recovery.ProcessSnapshot(
        42, "postgres", ("postgres", "-D", str(original_data))
    )
    with pytest.raises(recovery.OriginalSourceGuardError, match="references original"):
        recovery.assert_original_offline(original_root, snapshots=[running])


def test_stale_postmaster_pid_fails_closed(evidence_tree):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    (original_data / "postmaster.pid").write_text("99999\n", encoding="ascii")
    with pytest.raises(recovery.OriginalSourceGuardError, match="clean offline state"):
        recovery.assert_original_offline(original_root, snapshots=[])


def test_tree_hash_is_deterministic_and_ignores_mtime(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    item = root / "a"
    item.write_bytes(b"same")
    first = recovery.compute_tree_identity(root)
    item.touch()
    second = recovery.compute_tree_identity(root)
    assert first.tree_sha256 == second.tree_sha256
    assert first.regular_file_bytes == 4


def test_tree_hash_changes_when_source_content_changes(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    item = root / "a"
    item.write_bytes(b"one")
    before = recovery.compute_tree_identity(root)
    item.write_bytes(b"two")
    after = recovery.compute_tree_identity(root)
    assert before.tree_sha256 != after.tree_sha256


def test_tree_hash_records_symlink_without_following(tmp_path):
    root = tmp_path / "tree"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.write_bytes(b"outside bytes")
    link = root / "link"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    identity = recovery.compute_tree_identity(root)
    assert identity.regular_file_bytes == 0
    assert len(identity.entries) == 1
    assert identity.entries[0]["path"] == "link"
    assert identity.entries[0]["type"] == "symlink"
    assert Path(identity.entries[0]["target"]).samefile(outside)


def test_database_tree_symlink_blocks_controller_start(evidence_tree, tmp_path):
    data_root, original_data = evidence_tree
    outside = tmp_path / "tablespace"
    outside.mkdir()
    try:
        (original_data / "pg_tblspc_link").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    state = {}
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any("contains symlinks" in error for error in result["errors"])
    assert "started" not in state


def test_insufficient_disk_guard():
    usage = lambda _path: SimpleNamespace(total=100, used=99, free=1)
    with pytest.raises(recovery.DiskCapacityError, match="insufficient"):
        recovery.assert_disk_capacity(Path("."), 2, disk_usage=usage)


def test_disk_margin_is_deterministic():
    assert recovery.required_disk_bytes(1) == 1 + 1024**3
    huge = 20 * 1024**3
    assert recovery.required_disk_bytes(huge) == huge + 2 * 1024**3


def test_explicit_read_only_transaction_is_created_and_verified():
    cursor = ScriptedCursor()
    connection = ScriptedConnection(cursor)
    returned = recovery.begin_read_only_transaction(connection)
    assert returned is cursor
    assert [call[0] for call in cursor.calls] == [
        "BEGIN TRANSACTION READ ONLY;",
        "SHOW transaction_read_only;",
    ]


def test_show_transaction_read_only_must_equal_on():
    with pytest.raises(recovery.ReadOnlyTransactionError):
        recovery.begin_read_only_transaction(ScriptedConnection(ScriptedCursor(read_only="off")))


def test_schema_required_subset_allows_extra_columns():
    cursor = ScriptedCursor()
    recovery.verify_schema(cursor)


def test_schema_missing_required_column_fails():
    cursor = ScriptedCursor(columns=sorted(recovery.REQUIRED_COLUMNS - {"text"}))
    with pytest.raises(recovery.SchemaVerificationError, match="text"):
        recovery.verify_schema(cursor)


def test_all_three_exact_select_parameter_pairs(expected_text_hash):
    cursor = ScriptedCursor()
    connection = ScriptedConnection(cursor)
    results, errors = recovery.recover_all_targets(connection)
    assert errors == []
    assert len(results) == 3
    target_calls = [call for call in cursor.calls if call[0] == recovery.TARGET_SELECT]
    assert [call[1] for call in target_calls] == [
        (target["id"], namespace)
        for namespace, target in recovery.ALLOWED_TARGETS.items()
    ]
    assert connection.rollbacks == 1


@pytest.mark.parametrize(
    "rows,message",
    [([], "zero rows"), ([(1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 6)], "multiple rows")],
)
def test_zero_or_multiple_rows_fail(rows, message):
    namespace, target = next(iter(recovery.ALLOWED_TARGETS.items()))
    cursor = ScriptedCursor(row_overrides={namespace: rows})
    with pytest.raises(recovery.TargetError, match=message):
        recovery.select_target(cursor, namespace, target["id"])


@pytest.mark.parametrize(
    "field_index,replacement,message",
    [
        (0, "wrong-id", "row ID"),
        (1, "wrong-bank", "bank_id"),
        (3, "world", "fact_type"),
        (4, ["wrong-parent"], "expected parent"),
    ],
)
def test_wrong_row_identity_fact_type_or_parent_fails(field_index, replacement, message):
    namespace, target = next(iter(recovery.ALLOWED_TARGETS.items()))
    row = [
        target["id"],
        namespace,
        RAW_TEXT,
        "observation",
        [target["parent_source"]],
        "doc",
    ]
    row[field_index] = replacement
    cursor = ScriptedCursor(row_overrides={namespace: [tuple(row)]})
    with pytest.raises(recovery.TargetError, match=message):
        recovery.select_target(cursor, namespace, target["id"])


def test_raw_db_text_is_preserved_and_strip_hash_semantics(expected_text_hash):
    namespace, target = next(iter(recovery.ALLOWED_TARGETS.items()))
    cursor = ScriptedCursor()
    data = recovery.select_target(cursor, namespace, target["id"])
    result = recovery._recovery_result(namespace, target["id"], data, recovered_at="now")
    assert result.raw_db_text == RAW_TEXT
    assert result.normalized_candidate_text == RAW_TEXT.strip()
    assert result.phase06b_exact_content_sha256 == recovery.compute_sha256(RAW_TEXT.strip())


def test_sha_mismatch_fails():
    namespace, target = next(iter(recovery.ALLOWED_TARGETS.items()))
    cursor = ScriptedCursor()
    data = recovery.select_target(cursor, namespace, target["id"])
    with pytest.raises(recovery.HashMismatchError):
        recovery._recovery_result(namespace, target["id"], data, recovered_at="now")


def test_partial_two_of_three_is_overall_failure(expected_text_hash):
    failed_namespace = list(recovery.ALLOWED_TARGETS)[-1]
    cursor = ScriptedCursor(row_overrides={failed_namespace: []})
    results, errors = recovery.recover_all_targets(ScriptedConnection(cursor))
    assert len(results) == 2
    assert len(errors) == 1
    assert failed_namespace in errors[0]


def test_controller_is_attempt_scoped_copy_only_and_atomic(
    evidence_tree, expected_text_hash
):
    data_root, original_data = evidence_tree
    state = {}
    connection = ScriptedConnection(ScriptedCursor())
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: connection,
    )
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    assert result["status"] == "PASS"
    assert len(result["targets"]) == 3
    assert state["stopped"] is True
    assert state["kwargs"]["name"] != recovery.ORIGINAL_INSTANCE_NAME
    assert state["kwargs"]["username"] == SYNTHETIC_USERNAME
    assert state["kwargs"]["password"] == SYNTHETIC_PASSWORD
    assert state["kwargs"]["database"] == SYNTHETIC_DATABASE
    copy_dir = Path(state["kwargs"]["data_dir"])
    assert copy_dir == attempt_root / "pg0-copy" / "actual-data-dir"
    assert copy_dir != original_data
    assert state["start_home"] == attempt_root / "pg0-home"
    assert state["stop_home"] == attempt_root / "pg0-home"
    assert state["kwargs"]["config"]["default_transaction_read_only"] == "on"
    assert {path.name for path in attempt_root.iterdir()} == {
        "source-integrity-before.json",
        "source-integrity-after.json",
        "pg0-copy",
        "pg0-home",
        "recovery-result.json",
        "recovery-ledger.json",
        "recovery-complete.json",
    }
    marker = recovery.validate_recovery_completion(attempt_root)
    assert marker["status"] == "PASS"
    assert set(marker["artifacts"]) == set(recovery.MANDATORY_ARTIFACT_NAMES)
    ledger = json.loads((attempt_root / "recovery-ledger.json").read_text(encoding="utf-8"))
    assert ledger["recovery_pg0_cleanup_verified"] is True
    for path in attempt_root.glob("*.json"):
        assert SYNTHETIC_PASSWORD not in path.read_text(encoding="utf-8")


def test_silent_sdk_stop_failure_is_detected_by_fresh_process_proof(
    evidence_tree, expected_text_hash
):
    data_root, _ = evidence_tree
    state = {}
    inspections = 0

    def still_running_after_normal_stop():
        nonlocal inspections
        inspections += 1
        assert state["stopped"] is True
        copy_data_dir = state["kwargs"]["data_dir"]
        return [
            recovery.ProcessSnapshot(
                707,
                "postgres",
                ("postgres", "-D", copy_data_dir),
                cwd=str(Path(copy_data_dir).parent),
                pgdata=copy_data_dir,
            )
        ]

    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        post_stop_process_inspector=still_running_after_normal_stop,
    )
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    ledger = json.loads((attempt_root / "recovery-ledger.json").read_text(encoding="utf-8"))
    assert inspections == 1
    assert result["status"] == "FAIL_CLOSED"
    assert ledger["recovery_pg0_cleanup_verified"] is False
    assert any("cleanup verification failed" in error for error in result["errors"])
    assert recovery.classify_recovery_attempt(attempt_root) == "FAIL_CLOSED"


def test_successful_stop_requires_and_passes_fresh_cleanup_proof(
    evidence_tree, expected_text_hash
):
    data_root, _ = evidence_tree
    state = {}
    inspections = 0

    def freshly_clear():
        nonlocal inspections
        inspections += 1
        assert state["stopped"] is True
        return []

    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        post_stop_process_inspector=freshly_clear,
    )
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    ledger = json.loads((attempt_root / "recovery-ledger.json").read_text(encoding="utf-8"))
    assert inspections == 1
    assert result["status"] == "PASS"
    assert ledger["recovery_pg0_cleanup_verified"] is True


def test_postmaster_pid_remaining_after_stop_fails_closed(
    evidence_tree, expected_text_hash
):
    data_root, _ = evidence_tree

    def leave_postmaster_pid(instance):
        (Path(instance.kwargs["data_dir"]) / "postmaster.pid").write_text(
            "707\n",
            encoding="ascii",
        )

    state = {"on_stop": leave_postmaster_pid}
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        post_stop_process_inspector=lambda: [],
    )
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    ledger = json.loads((attempt_root / "recovery-ledger.json").read_text(encoding="utf-8"))
    assert result["status"] == "FAIL_CLOSED"
    assert ledger["recovery_pg0_cleanup_verified"] is False
    assert any("postmaster.pid" in error for error in result["errors"])
    assert recovery.classify_recovery_attempt(attempt_root) == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "state_key",
    ["reported_username", "reported_database"],
)
def test_reported_recovery_instance_identity_mismatch_fails_closed(
    evidence_tree, expected_text_hash, state_key
):
    data_root, _ = evidence_tree
    state = {state_key: "wrong-recovery-identity"}
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        post_stop_process_inspector=lambda: [],
    )
    assert result["status"] == "FAIL_CLOSED"
    assert state["stopped"] is True
    assert any("inconsistent" in error for error in result["errors"])


def test_cleanup_stop_runs_after_target_failure(evidence_tree, expected_text_hash):
    data_root, _ = evidence_tree
    failed_namespace = list(recovery.ALLOWED_TARGETS)[-1]
    state = {}
    connection = ScriptedConnection(
        ScriptedCursor(row_overrides={failed_namespace: []})
    )
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: connection,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert len(result["targets"]) == 2
    assert state["stopped"] is True


def test_original_before_after_tree_mismatch_fails(evidence_tree, expected_text_hash):
    data_root, original_data = evidence_tree
    state = {"on_start": lambda: (original_data / "base" / "1").write_bytes(b"changed")}
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any("before/after" in error for error in result["errors"])
    assert state["stopped"] is True


def test_cleanup_precedes_final_artifact_write_failure(
    evidence_tree, expected_text_hash, monkeypatch
):
    data_root, _ = evidence_tree
    state = {}
    real_write = recovery.write_json_exclusive

    def failing_write(path, payload):
        if path.name == "recovery-result.json":
            assert state["stopped"] is True
            raise OSError("simulated artifact failure")
        return real_write(path, payload)

    monkeypatch.setattr(recovery, "write_json_exclusive", failing_write)
    with pytest.raises(OSError, match="artifact failure"):
        recovery.run_recovery_controller(
            data_root=data_root,
            attempt_id=ATTEMPT,
            process_snapshots=[],
            disk_usage=ample_disk,
            pg0_factory=fake_factory(state),
            connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        )
    assert state["stopped"] is True
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    assert not (attempt_root / "recovery-complete.json").exists()


def test_http_and_mutating_provider_functionality_is_absent():
    source = inspect.getsource(recovery).casefold()
    assert not hasattr(recovery, "http_get_recovery")
    assert "memoryengine" not in source
    assert "alembic" not in source
    assert "consolidate" not in source
    assert ".drop(" not in source
    assert "urllib" not in source
    assert "requests" not in source
    assert "http://" not in source and "https://" not in source


def test_pg0_factory_receives_only_copy_and_no_original(evidence_tree):
    data_root, original_data = evidence_tree
    copy = data_root / "runs" / "attempt" / "copy"
    home = data_root / "runs" / "attempt" / "home"
    copy.mkdir(parents=True)
    home.mkdir()
    state = {}
    metadata = recovery.load_original_pg0_metadata(
        data_root / "providers" / "hindsight" / "pg0",
        original_data,
    )
    runtime = recovery.Pg0RecoveryRuntime(
        attempt_id=ATTEMPT,
        home=home,
        data_dir=copy,
        original_evidence_root=data_root / "providers" / "hindsight" / "pg0",
        original_data_dir=original_data,
        original_metadata=metadata,
        factory=fake_factory(state),
    )
    assert Path(state["kwargs"]["data_dir"]) == copy.resolve()
    assert Path(state["kwargs"]["data_dir"]) != original_data.resolve()
    assert state["kwargs"]["username"] == SYNTHETIC_USERNAME
    assert state["kwargs"]["password"] == SYNTHETIC_PASSWORD
    assert state["kwargs"]["database"] == SYNTHETIC_DATABASE
    assert runtime.instance_name != recovery.ORIGINAL_INSTANCE_NAME


def test_original_pg0_metadata_file_must_not_be_a_symlink(evidence_tree, tmp_path):
    data_root, original_data = evidence_tree
    original_root = data_root / "providers" / "hindsight" / "pg0"
    metadata_path = original_data.parent / "instance.json"
    replacement = tmp_path / "replacement-instance.json"
    replacement.write_bytes(metadata_path.read_bytes())
    metadata_path.unlink()
    try:
        metadata_path.symlink_to(replacement)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(recovery.OriginalPg0MetadataError, match="non-symlink"):
        recovery.load_original_pg0_metadata(original_root, original_data)


def test_wrong_original_metadata_data_dir_fails_before_pg0_start(
    evidence_tree, tmp_path
):
    data_root, original_data = evidence_tree
    wrong_data = tmp_path / "wrong-data"
    wrong_data.mkdir()
    metadata_path = original_data.parent / "instance.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["data_dir"] = str(wrong_data)
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")
    state = {}
    with pytest.raises(recovery.OriginalPg0MetadataError, match="does not match"):
        recovery.run_recovery_controller(
            data_root=data_root,
            attempt_id=ATTEMPT,
            process_snapshots=[],
            disk_usage=ample_disk,
            pg0_factory=fake_factory(state),
            connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        )
    assert "started" not in state
    assert "kwargs" not in state


@pytest.mark.parametrize("missing_field", ["username", "password", "database", "version"])
def test_missing_original_pg0_identity_field_fails_closed_before_start(
    evidence_tree, missing_field
):
    data_root, original_data = evidence_tree
    metadata_path = original_data.parent / "instance.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    del payload[missing_field]
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")
    state = {}
    with pytest.raises(recovery.OriginalPg0MetadataError, match=missing_field):
        recovery.run_recovery_controller(
            data_root=data_root,
            attempt_id=ATTEMPT,
            process_snapshots=[],
            disk_usage=ample_disk,
            pg0_factory=fake_factory(state),
            connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        )
    assert "started" not in state
    assert "kwargs" not in state


def test_password_is_redacted_from_failure_artifacts(
    evidence_tree, expected_text_hash
):
    data_root, _ = evidence_tree

    def failing_factory(**_kwargs):
        raise RuntimeError(f"synthetic factory exposed {SYNTHETIC_PASSWORD}")

    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=failing_factory,
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
    )
    assert result["status"] == "FAIL_CLOSED"
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    assert recovery.classify_recovery_attempt(attempt_root) == "FAIL_CLOSED"
    for path in attempt_root.glob("*.json"):
        assert SYNTHETIC_PASSWORD not in path.read_text(encoding="utf-8")


def test_completion_marker_is_written_last(evidence_tree, expected_text_hash, monkeypatch):
    data_root, _ = evidence_tree
    state = {}
    write_order = []
    real_write = recovery.write_json_exclusive

    def recording_write(path, payload):
        write_order.append(path.name)
        real_write(path, payload)

    monkeypatch.setattr(recovery, "write_json_exclusive", recording_write)
    result = recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory(state),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
    )
    assert result["status"] == "PASS"
    assert write_order[-1] == "recovery-complete.json"
    assert set(recovery.MANDATORY_ARTIFACT_NAMES).issubset(write_order[:-1])


@pytest.mark.parametrize(
    "failure_name,raises",
    [
        ("source-integrity-after.json", False),
        ("recovery-result.json", True),
        ("recovery-ledger.json", True),
    ],
)
def test_mandatory_artifact_write_failure_never_creates_completion_marker(
    evidence_tree,
    expected_text_hash,
    monkeypatch,
    failure_name,
    raises,
):
    data_root, _ = evidence_tree
    state = {}
    real_write = recovery.write_json_exclusive

    def failing_write(path, payload):
        if path.name == failure_name:
            raise OSError(f"simulated {failure_name} write failure")
        real_write(path, payload)

    monkeypatch.setattr(recovery, "write_json_exclusive", failing_write)
    if raises:
        with pytest.raises(OSError, match="simulated"):
            recovery.run_recovery_controller(
                data_root=data_root,
                attempt_id=ATTEMPT,
                process_snapshots=[],
                disk_usage=ample_disk,
                pg0_factory=fake_factory(state),
                connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
            )
    else:
        result = recovery.run_recovery_controller(
            data_root=data_root,
            attempt_id=ATTEMPT,
            process_snapshots=[],
            disk_usage=ample_disk,
            pg0_factory=fake_factory(state),
            connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
        )
        assert result["status"] == "FAIL_CLOSED"
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    assert not (attempt_root / "recovery-complete.json").exists()


def test_tampered_mandatory_artifact_fails_completion_validation(
    evidence_tree, expected_text_hash
):
    data_root, _ = evidence_tree
    recovery.run_recovery_controller(
        data_root=data_root,
        attempt_id=ATTEMPT,
        process_snapshots=[],
        disk_usage=ample_disk,
        pg0_factory=fake_factory({}),
        connect=lambda _uri: ScriptedConnection(ScriptedCursor()),
    )
    attempt_root = data_root / recovery.RECOVERY_RUN_DIRECTORY / ATTEMPT
    result_path = attempt_root / "recovery-result.json"
    result_path.write_bytes(result_path.read_bytes() + b"\n")
    with pytest.raises(recovery.CompletionValidationError, match="hash mismatch"):
        recovery.validate_recovery_completion(attempt_root)


def test_pass_result_without_completion_marker_is_incomplete(tmp_path):
    attempt_root = tmp_path / ATTEMPT
    attempt_root.mkdir()
    (attempt_root / "recovery-result.json").write_text(
        json.dumps({"attempt_id": ATTEMPT, "status": "PASS"}),
        encoding="utf-8",
    )
    assert recovery.classify_recovery_attempt(attempt_root) == "INCOMPLETE"
