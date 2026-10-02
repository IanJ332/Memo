"""Fail-closed, copy-only recovery of the three Phase 07B Hindsight rows.

This module deliberately has no Hindsight application dependency. A future
authorized run must execute it with the retained Hindsight provider virtualenv
so that the already-installed pg0 and PostgreSQL driver are used.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import stat
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence

EXPECTED_SHA = "f0c061e0f9331bc4811d783d5c69ac4ce87720eee1e43da13fd729fa5818e2e6"
ORIGINAL_ATTEMPT_ID = "20261001T183940Z-1fc4c4929532"
ORIGINAL_INSTANCE_NAME = "memlife-phase04"
REQUIRED_HINDSIGHT_VERSION = "0.10.1"
RECOVERY_RUN_DIRECTORY = Path("runs") / "phase07-hindsight-recovery"
SAFETY_MARGIN_MINIMUM_BYTES = 1024**3
SAFETY_MARGIN_PERCENT = 10
ATTEMPT_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
REQUIRED_COLUMNS = {
    "id",
    "bank_id",
    "text",
    "fact_type",
    "source_memory_ids",
    "document_id",
}
TARGET_SELECT = (
    "SELECT id, bank_id, text, fact_type, source_memory_ids, document_id "
    "FROM public.memory_units "
    "WHERE id = %s::uuid AND bank_id = %s AND fact_type = 'observation';"
)

ALLOWED_TARGETS: dict[str, dict[str, str]] = {
    "memlife-freeze-v1-hindsight-S1-r1": {
        "id": "d21e1d56-8224-4f7b-b144-9e7124fe4ef4",
        "parent_source": "bacf3934-5a34-48da-9580-80606d5b9c33",
    },
    "memlife-freeze-v1-hindsight-S1-r2": {
        "id": "5adc67dd-1658-4ddf-a5e7-7b40e00d84a7",
        "parent_source": "b2fa69b9-d719-4531-86e9-06c69fc739bb",
    },
    "memlife-freeze-v1-hindsight-S1-r3": {
        "id": "ea22a6bc-15be-4639-8060-c9eae4fcc5e5",
        "parent_source": "dfa63b99-ac6d-467b-b25e-bbc104545a2d",
    },
}


class RecoveryError(RuntimeError):
    """Base error for a fail-closed recovery guard."""


class TargetError(RecoveryError):
    pass


class HashMismatchError(RecoveryError):
    pass


class SchemaVerificationError(RecoveryError):
    pass


class ReadOnlyTransactionError(RecoveryError):
    pass


class OriginalSourceGuardError(RecoveryError):
    pass


class ProcessInspectionError(RecoveryError):
    pass


class DiskCapacityError(RecoveryError):
    pass


@dataclass(frozen=True)
class RecoveryResult:
    namespace: str
    provider_memory_id: str
    recovery_method: Literal["EXACT_ID_DATABASE_SELECT"]
    fact_type: str
    raw_db_text: str
    normalized_candidate_text: str
    phase06b_exact_content_sha256: str
    expected_sha256: str
    sha_match: bool
    source_memory_ids: list[str]
    expected_parent_source_id: str
    expected_parent_present: bool
    document_id: str
    original_attempt_id: str
    database_transaction_read_only: bool
    recovered_at: str
    status: Literal["RECOVERED_EXACT"]


@dataclass(frozen=True)
class TreeIdentity:
    root: str
    algorithm: str
    tree_sha256: str
    regular_file_bytes: int
    entries: list[dict[str, Any]]


@dataclass(frozen=True)
class ProcessSnapshot:
    pid: int
    comm: str
    argv: tuple[str, ...]
    cwd: str | None = None
    pgdata: str | None = None
    open_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptPaths:
    root: Path
    integrity_before: Path
    integrity_after: Path
    copy_root: Path
    copy_data_dir: Path
    pg0_home: Path
    result: Path
    ledger: Path


def validate_target(namespace: str, memory_id: str) -> dict[str, str]:
    target = ALLOWED_TARGETS.get(namespace)
    if target is None:
        raise TargetError(f"namespace {namespace!r} is not in the fixed allowlist")
    if target["id"] != memory_id:
        raise TargetError(
            f"memory ID {memory_id!r} does not match the fixed ID for {namespace!r}"
        )
    return target


def validate_attempt_id(attempt_id: str) -> str:
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise ValueError(
            "attempt_id must match YYYYMMDDTHHMMSSZ- followed by 12 lowercase hex characters"
        )
    return attempt_id


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_sha256(sha: str) -> None:
    if sha != EXPECTED_SHA:
        raise HashMismatchError(f"hash mismatch: expected {EXPECTED_SHA}, got {sha}")


def _canonical_path(path: Path, *, strict: bool) -> Path:
    try:
        return path.resolve(strict=strict)
    except (OSError, RuntimeError) as exc:
        raise OriginalSourceGuardError(f"cannot resolve guarded path {path}: {exc}") from exc


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def guard_recovery_data_dir(
    candidate_data_dir: Path, original_evidence_root: Path, original_data_dir: Path
) -> Path:
    """Reject the original data directory and every path resolving into its tree."""

    original_root = _canonical_path(original_evidence_root, strict=True)
    original_data = _canonical_path(original_data_dir, strict=True)
    candidate = _canonical_path(candidate_data_dir, strict=True)
    if not _is_within(original_data, original_root):
        raise OriginalSourceGuardError(
            "fixed original data directory resolves outside the original evidence tree"
        )
    if candidate == original_data or _is_within(candidate, original_root):
        raise OriginalSourceGuardError(
            "recovery PostgreSQL data_dir resolves into the original evidence tree"
        )
    return candidate


def _file_digest_without_following(path: Path) -> tuple[int, str]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise OriginalSourceGuardError(f"cannot safely open source file {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OriginalSourceGuardError(f"source entry changed type while hashing: {path}")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        before_signature = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_signature = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if before_signature != after_signature:
            raise OriginalSourceGuardError(f"source file changed while hashing: {path}")
        return before.st_size, digest.hexdigest()
    finally:
        os.close(descriptor)


def compute_tree_identity(root: Path) -> TreeIdentity:
    """Hash file path, size and bytes; record symlinks without following them."""

    if root.is_symlink() or not root.is_dir():
        raise OriginalSourceGuardError(
            "tree identity root must be an existing, non-symlink directory"
        )
    root = _canonical_path(root, strict=True)
    entries: list[dict[str, Any]] = []
    total = 0
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(directory_names):
            path = directory_path / name
            if path.is_symlink():
                entries.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "type": "symlink",
                        "target": os.readlink(path),
                    }
                )
                directory_names.remove(name)
        for name in file_names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                entries.append(
                    {"path": relative, "type": "symlink", "target": os.readlink(path)}
                )
            elif stat.S_ISREG(mode):
                size, digest = _file_digest_without_following(path)
                total += size
                entries.append(
                    {
                        "path": relative,
                        "type": "file",
                        "size": size,
                        "sha256": digest,
                    }
                )
            else:
                raise OriginalSourceGuardError(
                    f"unsupported special entry in source evidence tree: {relative}"
                )
    entries.sort(key=lambda entry: entry["path"])
    canonical = b"".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        + b"\n"
        for entry in entries
    )
    return TreeIdentity(
        root=str(root),
        algorithm="sha256(canonical-jsonl(path,type,size,sha256|target))",
        tree_sha256=hashlib.sha256(canonical).hexdigest(),
        regular_file_bytes=total,
        entries=entries,
    )


def _read_process_snapshot(proc_entry: Path) -> ProcessSnapshot | None:
    try:
        pid = int(proc_entry.name)
        comm = (proc_entry / "comm").read_text(encoding="utf-8").strip()
        raw = (proc_entry / "cmdline").read_bytes()
        argv = tuple(
            part.decode("utf-8", errors="surrogateescape")
            for part in raw.split(b"\0")
            if part
        )
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ProcessInspectionError(f"cannot inspect process {proc_entry.name}: {exc}") from exc

    cwd: str | None = None
    pgdata: str | None = None
    open_paths: list[str] = []
    is_postgres = comm.casefold() in {"postgres", "postmaster"} or any(
        Path(argument).name.casefold() in {"postgres", "postmaster"}
        for argument in argv[:1]
    )
    if is_postgres:
        try:
            cwd = os.readlink(proc_entry / "cwd")
            environment = (proc_entry / "environ").read_bytes().split(b"\0")
            for value in environment:
                if value.startswith(b"PGDATA="):
                    pgdata = value.removeprefix(b"PGDATA=").decode(
                        "utf-8", errors="surrogateescape"
                    )
            for fd in (proc_entry / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except FileNotFoundError:
                    continue
                if target.startswith("/"):
                    open_paths.append(target.removesuffix(" (deleted)"))
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ProcessInspectionError(
                f"cannot prove PostgreSQL process {pid} is separate from original evidence: {exc}"
            ) from exc
    return ProcessSnapshot(pid, comm, argv, cwd, pgdata, tuple(open_paths))


def inspect_linux_processes(proc_root: Path = Path("/proc")) -> list[ProcessSnapshot]:
    if not sys.platform.startswith("linux") or not proc_root.is_dir():
        raise ProcessInspectionError("offline process proof requires Linux /proc")
    snapshots: list[ProcessSnapshot] = []
    for entry in sorted(proc_root.iterdir(), key=lambda path: path.name):
        if not entry.name.isdigit():
            continue
        snapshot = _read_process_snapshot(entry)
        if snapshot is not None:
            snapshots.append(snapshot)
    return snapshots


def _snapshot_is_postgres(snapshot: ProcessSnapshot) -> bool:
    if snapshot.comm.casefold() in {"postgres", "postmaster"}:
        return True
    return bool(snapshot.argv) and Path(snapshot.argv[0]).name.casefold() in {
        "postgres",
        "postmaster",
    }


def _snapshot_is_hindsight_api(snapshot: ProcessSnapshot) -> bool:
    tokens = [snapshot.comm, *snapshot.argv]
    normalized = " ".join(tokens).casefold().replace("_", "-")
    return "hindsight-api" in normalized


def _postgres_path_arguments(snapshot: ProcessSnapshot) -> Iterable[str]:
    if snapshot.cwd:
        yield snapshot.cwd
    if snapshot.pgdata:
        yield snapshot.pgdata
    yield from snapshot.open_paths
    arguments = iter(snapshot.argv[1:])
    for argument in arguments:
        if argument in {"-D", "--data-directory"}:
            try:
                yield next(arguments)
            except StopIteration:
                return
        elif argument.startswith("--data-directory="):
            yield argument.split("=", 1)[1]


def assert_original_offline(
    original_evidence_root: Path,
    *,
    snapshots: Sequence[ProcessSnapshot] | None = None,
) -> None:
    """Fail if the provider is active or PostgreSQL references original evidence."""

    original_root = _canonical_path(original_evidence_root, strict=True)
    observed = list(snapshots) if snapshots is not None else inspect_linux_processes()
    api_pids = [item.pid for item in observed if _snapshot_is_hindsight_api(item)]
    if api_pids:
        raise OriginalSourceGuardError(
            f"hindsight-api appears active (pid(s): {api_pids}); original evidence is not offline"
        )
    for snapshot in observed:
        if not _snapshot_is_postgres(snapshot):
            continue
        for raw_path in _postgres_path_arguments(snapshot):
            path = Path(raw_path)
            if not path.is_absolute():
                continue
            try:
                resolved = path.resolve(strict=False)
            except (OSError, RuntimeError) as exc:
                raise ProcessInspectionError(
                    f"cannot resolve path reported by PostgreSQL pid {snapshot.pid}: {exc}"
                ) from exc
            if _is_within(resolved, original_root):
                raise OriginalSourceGuardError(
                    f"PostgreSQL pid {snapshot.pid} references original evidence at {resolved}"
                )
    for pid_file in original_root.rglob("postmaster.pid"):
        try:
            recorded = int(pid_file.read_text(encoding="ascii").splitlines()[0])
        except (OSError, ValueError, IndexError) as exc:
            raise OriginalSourceGuardError(
                f"cannot validate PostgreSQL lock file in original evidence: {pid_file}"
            ) from exc
        if any(item.pid == recorded and _snapshot_is_postgres(item) for item in observed):
            raise OriginalSourceGuardError(
                f"original evidence postmaster.pid identifies running PostgreSQL pid {recorded}"
            )
        raise OriginalSourceGuardError(
            f"original evidence contains postmaster.pid ({pid_file}); clean offline state is unproven"
        )


def required_disk_bytes(source_size: int) -> int:
    margin = max(
        SAFETY_MARGIN_MINIMUM_BYTES,
        (source_size * SAFETY_MARGIN_PERCENT + 99) // 100,
    )
    return source_size + margin


def assert_disk_capacity(
    filesystem_path: Path,
    source_size: int,
    *,
    disk_usage: Callable[[Path], Any] = shutil.disk_usage,
) -> dict[str, int]:
    usage = disk_usage(filesystem_path)
    required = required_disk_bytes(source_size)
    if usage.free < required:
        raise DiskCapacityError(
            f"insufficient free space: need {required} bytes, have {usage.free} bytes"
        )
    return {
        "source_regular_file_bytes": source_size,
        "safety_margin_bytes": required - source_size,
        "required_free_bytes": required,
        "observed_free_bytes": usage.free,
    }


def attempt_filesystem_anchor(data_root: Path) -> Path:
    """Return the nearest existing ancestor of the future attempt directory."""

    candidate = data_root / RECOVERY_RUN_DIRECTORY
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise RecoveryError("cannot identify the attempt-root filesystem")
        candidate = parent
    return _canonical_path(candidate, strict=True)


def create_attempt_paths(data_root: Path, attempt_id: str) -> AttemptPaths:
    validate_attempt_id(attempt_id)
    data_root = _canonical_path(data_root, strict=True)
    parent = data_root / RECOVERY_RUN_DIRECTORY
    prospective_parent = _canonical_path(parent, strict=False)
    if not _is_within(prospective_parent, data_root):
        raise RecoveryError("attempt parent resolves outside MEMLIFE_DATA_ROOT")
    parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = _canonical_path(parent, strict=True)
    if not _is_within(resolved_parent, data_root):
        raise RecoveryError("attempt parent resolves outside MEMLIFE_DATA_ROOT")
    root = parent / attempt_id
    root.mkdir(mode=0o700, exist_ok=False)
    copy_root = root / "pg0-copy"
    pg0_home = root / "pg0-home"
    copy_root.mkdir(mode=0o700)
    pg0_home.mkdir(mode=0o700)
    return AttemptPaths(
        root=root,
        integrity_before=root / "source-integrity-before.json",
        integrity_after=root / "source-integrity-after.json",
        copy_root=copy_root,
        copy_data_dir=copy_root / "actual-data-dir",
        pg0_home=pg0_home,
        result=root / "recovery-result.json",
        ledger=root / "recovery-ledger.json",
    )


def copy_database_tree(source_data_dir: Path, destination_data_dir: Path) -> None:
    if destination_data_dir.exists():
        raise FileExistsError(destination_data_dir)
    shutil.copytree(
        source_data_dir,
        destination_data_dir,
        symlinks=True,
        copy_function=shutil.copy2,
    )


def write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def verify_schema(cur: Any) -> None:
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'memory_units';"
    )
    if cur.fetchone()[0] != 1:
        raise SchemaVerificationError("public.memory_units was not found exactly once")
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'memory_units';"
    )
    columns = {row[0] for row in cur.fetchall()}
    if not REQUIRED_COLUMNS.issubset(columns):
        missing = sorted(REQUIRED_COLUMNS - columns)
        raise SchemaVerificationError(
            f"public.memory_units is missing required columns: {missing}"
        )


def begin_read_only_transaction(conn: Any) -> Any:
    cur = conn.cursor()
    cur.execute("BEGIN TRANSACTION READ ONLY;")
    cur.execute("SHOW transaction_read_only;")
    row = cur.fetchone()
    if not row or str(row[0]).casefold() != "on":
        raise ReadOnlyTransactionError("SHOW transaction_read_only did not return on")
    return cur


def verify_read_only(cur: Any) -> None:
    """Compatibility helper for independently checking an existing transaction."""

    cur.execute("SHOW transaction_read_only;")
    row = cur.fetchone()
    if not row or str(row[0]).casefold() != "on":
        raise ReadOnlyTransactionError("transaction is not read-only")


def _normalize_source_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TargetError("source_memory_ids is not valid JSON") from exc
    if value is None:
        return []
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, (str, uuid.UUID)) for item in value
    ):
        raise TargetError("source_memory_ids is not a sequence of UUID values")
    return [str(item) for item in value]


def select_target(cur: Any, namespace: str, memory_id: str) -> dict[str, Any]:
    target = validate_target(namespace, memory_id)
    cur.execute(TARGET_SELECT, (memory_id, namespace))
    rows = cur.fetchall()
    if not rows:
        raise TargetError("exact target SELECT returned zero rows")
    if len(rows) != 1:
        raise TargetError("exact target SELECT returned multiple rows")
    row_id, bank_id, text, fact_type, source_ids, document_id = rows[0]
    if str(row_id) != memory_id:
        raise TargetError("returned row ID does not match the requested fixed ID")
    if bank_id != namespace:
        raise TargetError("returned bank_id does not match the requested fixed bank")
    if fact_type != "observation":
        raise TargetError("returned fact_type is not observation")
    if not isinstance(text, str):
        raise TargetError("returned database text is not a string")
    normalized_source_ids = _normalize_source_ids(source_ids)
    if target["parent_source"] not in normalized_source_ids:
        raise TargetError(
            f"expected parent source {target['parent_source']} is absent"
        )
    return {
        "text": text,
        "fact_type": fact_type,
        "document_id": document_id,
        "source_memory_ids": normalized_source_ids,
        "expected_parent_source_id": target["parent_source"],
    }


def _recovery_result(
    namespace: str, memory_id: str, data: Mapping[str, Any], *, recovered_at: str
) -> RecoveryResult:
    raw_db_text = data["text"]
    normalized_candidate_text = raw_db_text.strip()
    sha = compute_sha256(normalized_candidate_text)
    verify_sha256(sha)
    return RecoveryResult(
        namespace=namespace,
        provider_memory_id=memory_id,
        recovery_method="EXACT_ID_DATABASE_SELECT",
        fact_type=data["fact_type"],
        raw_db_text=raw_db_text,
        normalized_candidate_text=normalized_candidate_text,
        phase06b_exact_content_sha256=sha,
        expected_sha256=EXPECTED_SHA,
        sha_match=True,
        source_memory_ids=list(data["source_memory_ids"]),
        expected_parent_source_id=data["expected_parent_source_id"],
        expected_parent_present=True,
        document_id=str(data["document_id"] or ""),
        original_attempt_id=ORIGINAL_ATTEMPT_ID,
        database_transaction_read_only=True,
        recovered_at=recovered_at,
        status="RECOVERED_EXACT",
    )


def pg_select_recovery(conn: Any, namespace: str, memory_id: str) -> dict[str, Any]:
    """Single-target compatibility entrypoint that creates its own RO transaction."""

    try:
        cur = begin_read_only_transaction(conn)
        verify_schema(cur)
        return select_target(cur, namespace, memory_id)
    finally:
        conn.rollback()


def run_recovery_db(conn: Any, namespace: str, memory_id: str) -> RecoveryResult:
    data = pg_select_recovery(conn, namespace, memory_id)
    return _recovery_result(
        namespace,
        memory_id,
        data,
        recovered_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )


def recover_all_targets(conn: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Read all fixed targets in one explicit transaction; never commit it."""

    recovered: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        cur = begin_read_only_transaction(conn)
        verify_schema(cur)
        for namespace, target in ALLOWED_TARGETS.items():
            try:
                data = select_target(cur, namespace, target["id"])
                result = _recovery_result(
                    namespace,
                    target["id"],
                    data,
                    recovered_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                )
                recovered.append(asdict(result))
            except Exception as exc:  # preserve partial evidence, but fail atomically
                errors.append(f"{namespace}: {type(exc).__name__}: {exc}")
    finally:
        conn.rollback()
    return recovered, errors


@contextlib.contextmanager
def _scoped_home(home: Path) -> Iterable[None]:
    previous = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous


def _load_pg0_factory(
    provider_venv: Path,
) -> tuple[Callable[..., Any], dict[str, str]]:
    provider_venv = _canonical_path(provider_venv, strict=True)
    if not (provider_venv / "pyvenv.cfg").is_file():
        raise RecoveryError("retained Hindsight provider virtualenv has no pyvenv.cfg")
    active_prefix = _canonical_path(Path(sys.prefix), strict=True)
    if active_prefix != provider_venv:
        raise RecoveryError(
            "controller must run inside the retained Hindsight provider virtualenv"
        )
    hindsight_version = importlib.metadata.version("hindsight-api-slim")
    if hindsight_version != REQUIRED_HINDSIGHT_VERSION:
        raise RecoveryError(
            f"retained provider environment must contain hindsight-api-slim=={REQUIRED_HINDSIGHT_VERSION}; "
            f"found {hindsight_version}"
        )
    pg0_version = importlib.metadata.version("pg0-embedded")
    from pg0 import Pg0

    return Pg0, {
        "hindsight_api_slim_version": hindsight_version,
        "pg0_embedded_version": pg0_version,
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
    }


class Pg0RecoveryRuntime:
    """Own one uniquely named pg0 process whose data directory is the copy."""

    def __init__(
        self,
        *,
        attempt_id: str,
        home: Path,
        data_dir: Path,
        original_evidence_root: Path,
        original_data_dir: Path,
        factory: Callable[..., Any],
    ) -> None:
        suffix = validate_attempt_id(attempt_id).split("-", 1)[1]
        self.instance_name = f"memlife-phase07-recovery-{suffix}"
        if self.instance_name == ORIGINAL_INSTANCE_NAME:
            raise RecoveryError("recovery instance name collides with the original instance")
        self.home = _canonical_path(home, strict=True)
        self.original_evidence_root = _canonical_path(original_evidence_root, strict=True)
        self.original_data_dir = _canonical_path(original_data_dir, strict=True)
        self.data_dir = guard_recovery_data_dir(
            data_dir, self.original_evidence_root, self.original_data_dir
        )
        self.instance = factory(
            name=self.instance_name,
            data_dir=str(self.data_dir),
            config={
                "listen_addresses": "127.0.0.1",
                "default_transaction_read_only": "on",
            },
        )
        self.start_attempted = False
        self.uri: str | None = None

    def start(self) -> None:
        self.data_dir = guard_recovery_data_dir(
            self.data_dir,
            self.original_evidence_root,
            self.original_data_dir,
        )
        self.start_attempted = True
        with _scoped_home(self.home):
            info = self.instance.start()
        observed_data_dir = getattr(info, "data_dir", None)
        if observed_data_dir is None:
            raise RecoveryError("pg0 start did not report its data_dir")
        if _canonical_path(Path(observed_data_dir), strict=True) != self.data_dir:
            raise OriginalSourceGuardError("pg0 started with a data_dir other than the copy")
        self.uri = getattr(info, "uri", None)
        if not self.uri:
            raise RecoveryError("pg0 start did not report a connection URI")

    def stop(self) -> None:
        if not self.start_attempted:
            return
        with _scoped_home(self.home):
            self.instance.stop()
        self.start_attempted = False


def _connect_read_only(uri: str) -> Any:
    import psycopg2

    connection = psycopg2.connect(
        uri,
        options="-c default_transaction_read_only=on",
    )
    connection.autocommit = False
    return connection


def _tree_payload(identity: TreeIdentity, **extra: Any) -> dict[str, Any]:
    return {**asdict(identity), **extra}


def run_recovery_controller(
    *,
    data_root: Path,
    attempt_id: str,
    process_snapshots: Sequence[ProcessSnapshot] | None = None,
    disk_usage: Callable[[Path], Any] = shutil.disk_usage,
    pg0_factory: Callable[..., Any] | None = None,
    connect: Callable[[str], Any] = _connect_read_only,
) -> dict[str, Any]:
    """Execute the complete copy-only controller; no network/provider API is used."""

    validate_attempt_id(attempt_id)
    data_root = _canonical_path(data_root, strict=True)
    original_root = data_root / "providers" / "hindsight" / "pg0"
    original_data = original_root / "instances" / ORIGINAL_INSTANCE_NAME / "data"
    if original_root.is_symlink() or not original_root.is_dir():
        raise OriginalSourceGuardError("fixed original pg0 evidence root is unavailable or a symlink")
    if original_data.is_symlink() or not original_data.is_dir():
        raise OriginalSourceGuardError("fixed original pg0 data directory is unavailable or a symlink")
    original_root = _canonical_path(original_root, strict=True)
    original_data = _canonical_path(original_data, strict=True)
    if not _is_within(original_data, original_root):
        raise OriginalSourceGuardError("original data directory escapes original evidence root")

    assert_original_offline(original_root, snapshots=process_snapshots)
    source_before = compute_tree_identity(original_root)
    capacity = assert_disk_capacity(
        attempt_filesystem_anchor(data_root),
        source_before.regular_file_bytes,
        disk_usage=disk_usage,
    )
    paths = create_attempt_paths(data_root, attempt_id)
    write_json_exclusive(
        paths.integrity_before,
        _tree_payload(source_before, measured_at=_utc_now()),
    )

    ledger: dict[str, Any] = {
        "schema_version": "memlife-phase07b-recovery-ledger-v1",
        "attempt_id": attempt_id,
        "status": "FAIL_CLOSED",
        "original_instance_name": ORIGINAL_INSTANCE_NAME,
        "recovery_instance_name": None,
        "original_evidence_root": str(original_root),
        "original_data_dir": str(original_data),
        "copy_data_dir": str(paths.copy_data_dir),
        "pg0_home": str(paths.pg0_home),
        "disk_capacity_guard": capacity,
        "source_tree_sha_before": source_before.tree_sha256,
        "source_tree_sha_after_copy": None,
        "source_tree_sha_after": None,
        "copy_tree_sha_initial": None,
        "transaction_read_only": False,
        "target_success_count": 0,
        "target_required_count": len(ALLOWED_TARGETS),
        "errors": [],
    }
    recovered: list[dict[str, Any]] = []
    runtime: Pg0RecoveryRuntime | None = None
    connection: Any | None = None

    try:
        assert_original_offline(original_root, snapshots=process_snapshots)
        source_data_identity = compute_tree_identity(original_data)
        if any(entry["type"] == "symlink" for entry in source_data_identity.entries):
            raise OriginalSourceGuardError(
                "original PostgreSQL data tree contains symlinks; copy-only write containment is unproven"
            )
        copy_database_tree(original_data, paths.copy_data_dir)
        guard_recovery_data_dir(paths.copy_data_dir, original_root, original_data)
        copy_identity = compute_tree_identity(paths.copy_data_dir)
        if source_data_identity.tree_sha256 != copy_identity.tree_sha256:
            raise RecoveryError("copied PostgreSQL data tree does not match its source")
        ledger["copy_tree_sha_initial"] = copy_identity.tree_sha256

        source_after_copy = compute_tree_identity(original_root)
        ledger["source_tree_sha_after_copy"] = source_after_copy.tree_sha256
        if source_after_copy.tree_sha256 != source_before.tree_sha256:
            raise OriginalSourceGuardError("original source changed during copy")
        assert_original_offline(original_root, snapshots=process_snapshots)

        runtime_metadata: dict[str, str] = {}
        if pg0_factory is None:
            pg0_factory, runtime_metadata = _load_pg0_factory(
                data_root / "venvs" / f"hindsight-{REQUIRED_HINDSIGHT_VERSION}"
            )
        ledger["runtime"] = runtime_metadata
        runtime = Pg0RecoveryRuntime(
            attempt_id=attempt_id,
            home=paths.pg0_home,
            data_dir=paths.copy_data_dir,
            original_evidence_root=original_root,
            original_data_dir=original_data,
            factory=pg0_factory,
        )
        ledger["recovery_instance_name"] = runtime.instance_name
        runtime.start()
        connection = connect(runtime.uri or "")
        try:
            recovered, target_errors = recover_all_targets(connection)
            ledger["transaction_read_only"] = True
            ledger["errors"].extend(target_errors)
        finally:
            connection.close()
            connection = None
    except Exception as exc:
        ledger["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()
        if runtime is not None and runtime.start_attempted:
            try:
                runtime.stop()
            except Exception as exc:
                ledger["errors"].append(
                    f"pg0 cleanup failed: {type(exc).__name__}: {exc}"
                )

    try:
        source_after = compute_tree_identity(original_root)
        ledger["source_tree_sha_after"] = source_after.tree_sha256
        write_json_exclusive(
            paths.integrity_after,
            _tree_payload(source_after, measured_at=_utc_now()),
        )
        if source_after.tree_sha256 != source_before.tree_sha256:
            ledger["errors"].append("original source before/after tree identity mismatch")
    except Exception as exc:
        source_after = None
        ledger["errors"].append(f"final source integrity failed: {type(exc).__name__}: {exc}")

    ledger["target_success_count"] = len(recovered)
    success = (
        len(recovered) == len(ALLOWED_TARGETS)
        and not ledger["errors"]
        and source_after is not None
        and source_after.tree_sha256 == source_before.tree_sha256
        and ledger["transaction_read_only"] is True
    )
    ledger["status"] = "PASS" if success else "FAIL_CLOSED"
    result = {
        "schema_version": "memlife-phase07b-recovery-result-v1",
        "attempt_id": attempt_id,
        "status": ledger["status"],
        "atomic_success": success,
        "targets": recovered,
        "errors": list(ledger["errors"]),
    }
    write_json_exclusive(paths.result, result)
    write_json_exclusive(paths.ledger, ledger)
    return result


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy-only exact-row recovery controller for Phase 07B"
    )
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ["MEMLIFE_DATA_ROOT"])
        if "MEMLIFE_DATA_ROOT" in os.environ
        else None,
    )
    args = parser.parse_args(argv)
    if args.data_root is None:
        parser.error("--data-root or MEMLIFE_DATA_ROOT is required")
    result = run_recovery_controller(
        data_root=args.data_root,
        attempt_id=args.attempt_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
