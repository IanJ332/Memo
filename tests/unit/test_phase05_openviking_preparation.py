from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTHON_SCRIPT = ROOT / "scripts" / "jetstream" / "phase05_openviking.py"
REMOTE_SCRIPT = ROOT / "scripts" / "jetstream" / "phase05_openviking_remote.sh"
REQUIREMENT = ROOT / "requirements" / "providers" / "openviking.txt"


def _module():
    spec = importlib.util.spec_from_file_location("phase05_openviking", PYTHON_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_future_execution_is_disabled_without_separate_authorization(monkeypatch) -> None:
    monkeypatch.delenv("MEMLIFE_AUTHORIZE_PHASE05_LIVE", raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        _module().require_live_authorization()


def test_remote_script_has_isolation_and_resource_guards() -> None:
    text = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert "findmnt -n -o TARGET /dev/sdb" in text
    assert "openviking-0.4.22" in text
    assert "http://127.0.0.1:1933" in text
    assert "requirements/providers/openviking.txt" in text
    assert "llama-cpp-python" in text
    assert "memlife-harness-phase04" in text
    assert "nvidia-" in text and "cuda-" in text
    assert "https://abetlen.github.io/llama-cpp-python/whl/cpu" in text
    assert '.local/phase05_openviking.env' in text
    assert 'test "$LIVE_CONFIG_MODE" = 600' in text
    assert "/media/volume/sdb" not in text
    assert "sleep 30" not in text


def test_remote_script_reuses_retained_provider_environment_fail_closed() -> None:
    text = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert "REUSE_EXISTING_ENV=0" in text
    assert 'if [ -e "$OPENVIKING_VENV" ]' in text
    assert "environment_reuse DistributionMetadataError" in text
    assert 'phase05_provider_env_reused=%s' in text
    assert 'pip check' in text
    assert 'nvidia-' in text and 'cuda-' in text
    assert 'rm -rf "$OPENVIKING_VENV"' not in text
    assert 'rm -rf "$MODEL_CACHE"' not in text


def test_local_embedding_requirement_is_exact() -> None:
    assert REQUIREMENT.read_text(encoding="utf-8").strip() == (
        "openviking[local-embed]==0.4.22"
    )


@pytest.mark.parametrize(
    "raw", ["llama-cpp-python", "llama_cpp_python", "llama.cpp.python"]
)
def test_distribution_names_use_pep503_canonicalization(raw: str) -> None:
    assert _module().canonicalize_distribution_name(raw) == "llama-cpp-python"


def test_dependency_plan_accepts_normalized_local_embed_fixture() -> None:
    module = _module()
    report = {
        "install": [
            {"metadata": {"name": "openviking", "version": "0.4.22"}},
            {"metadata": {"name": "llama_cpp_python", "version": "0.3.35"}},
        ]
    }
    old_names = {
        item["metadata"]["name"].lower() for item in report["install"]
    }
    assert "llama-cpp-python" not in old_names
    result = module.validate_dependency_plan(report)
    assert result["status"] == "PASS"
    assert result["llama_cpp_python_version_candidate"] == "0.3.35"
    assert "llama-cpp-python" in result["normalized_distributions"]


def test_dependency_plan_blocks_missing_and_forbidden_distributions() -> None:
    module = _module()
    missing = module.validate_dependency_plan(
        {"install": [{"metadata": {"name": "openviking", "version": "0.4.22"}}]}
    )
    assert missing["status"] == "BLOCKED"
    assert missing["blocker_type"] == "MissingRequiredDistribution"
    assert missing["required"] == "llama-cpp-python"
    forbidden = module.validate_dependency_plan(
        {
            "install": [
                {"metadata": {"name": "openviking", "version": "0.4.22"}},
                {"metadata": {"name": "llama_cpp_python", "version": "0.3.35"}},
                {"metadata": {"name": "NVIDIA_CUBLAS", "version": "1"}},
            ]
        }
    )
    assert forbidden["status"] == "BLOCKED"
    assert forbidden["forbidden_distributions"] == ["nvidia-cublas"]


def test_local_orchestrator_import_is_stdlib_only() -> None:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(PYTHON_SCRIPT.parent)!r}); "
        "import phase05_openviking; "
        "assert 'memlife' not in sys.modules; "
        "assert 'pydantic' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_generated_config_uses_pinned_v0422_schema(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    cache = tmp_path / "model-cache" / "openviking"
    values = {
        "PHASE05_OPENVIKING_VLM_PROVIDER": "openai",
        "PHASE05_OPENVIKING_VLM_MODEL": "gpt-oss-120b",
        "PHASE05_OPENVIKING_VLM_API_BASE": (
            "https://llm.jetstream-cloud.org/gpt-oss-120b/v1/"
        ),
        "PHASE05_OPENVIKING_VLM_API_KEY": "empty",
        "PHASE05_PROVIDER_STATE": str(tmp_path / "provider-state"),
        "PHASE05_MODEL_CACHE": str(cache),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    output = tmp_path / "ov.conf"
    config_hash = module.write_config(output)
    config = json.loads(output.read_text(encoding="utf-8"))
    assert set(config) >= {"server", "storage", "embedding", "vlm", "memory"}
    assert config["server"] == {"host": "127.0.0.1", "port": 1933, "auth_mode": "dev"}
    assert config["storage"]["workspace"] == values["PHASE05_PROVIDER_STATE"]
    assert config["storage"]["agfs"]["backend"] == "local"
    assert config["storage"]["vectordb"]["backend"] == "local"
    dense = config["embedding"]["dense"]
    assert dense == {
        "provider": "local",
        "model": "bge-small-zh-v1.5-f16",
        "dimension": 512,
        "input": "text",
        "cache_dir": str(cache / "embedding"),
    }
    assert "backend" not in dense
    assert config["vlm"] == {
        "provider": "openai",
        "model": "gpt-oss-120b",
        "api_base": "https://llm.jetstream-cloud.org/gpt-oss-120b/v1/",
        "api_key": "empty",
        "temperature": 0.0,
        "max_concurrent": 1,
        "max_retries": 1,
        "thinking": False,
    }
    assert config["memory"]["extraction_enabled"] is True
    assert (cache / "embedding").is_dir()
    assert config_hash == hashlib.sha256(output.read_bytes()).hexdigest()


def test_managed_controller_provisions_mode_600_config_before_run(monkeypatch) -> None:
    module = _module()
    monkeypatch.setenv(module.LIVE_AUTH_ENV, "YES")
    expected = "a" * 40
    payload = {
        "status": "BLOCKED",
        "blocker_type": "ProviderCompatibilityError",
        "blocker": "course endpoint rejected extraction request",
        "git_commit_tested": expected,
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    calls: list[list[str]] = []

    def ssh_builder(address: str, command: str) -> list[str]:
        return [address, command]

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = f"{module.RESULT_PREFIX}{encoded}\n" if len(calls) == 3 else "ok\n"
        return subprocess.CompletedProcess(command, 0, stdout, "")

    received = module.run_remote_validation(
        address="example.invalid",
        facts={"resolved_volume_mount": "/volume"},
        expected_commit=expected,
        ssh_builder=ssh_builder,
        runner=runner,
    )
    assert received["status"] == "BLOCKED"
    assert len(calls) == 3
    provision = calls[1][1]
    assert calls[2][1].find("phase05_openviking_remote.sh") >= 0
    assert "phase05_openviking.env" in provision
    assert "chmod 600" in provision
    assert "stat -c %a" in provision and "stat -c %U" in provision
    decoded_config = base64.b64decode(
        provision.split("printf '%s' '", 1)[1].split("' | base64", 1)[0]
    ).decode()
    assert decoded_config.splitlines() == [
        f"{name}={value}" for name, value in module.LIVE_CONFIG_VALUES.items()
    ]
    serialized = json.dumps(received)
    assert "api_key" not in serialized.lower()
    assert "PHASE05_OPENVIKING_VLM_API_KEY" not in serialized


class _FakeOwnedProcess:
    def __init__(self, pid: int = 4321) -> None:
        self.pid = pid
        self.return_code = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.return_code

    def terminate(self):
        self.terminated = True
        self.return_code = 0

    def wait(self, timeout=None):
        return self.return_code

    def kill(self):
        self.killed = True
        self.return_code = -9


def _owned_controller(tmp_path: Path, monkeypatch, process: _FakeOwnedProcess):
    module = _module()
    executable = tmp_path / "openviking-server"
    config = tmp_path / "ov.conf"
    executable.write_text("fake", encoding="utf-8")
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("PHASE05_OPENVIKING_SERVICE", str(executable))
    monkeypatch.setenv("PHASE05_OPENVIKING_CONFIG", str(config))
    monkeypatch.setenv("PHASE05_RUN_ROOT", str(tmp_path / "run"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: process)
    return module, module.OpenVikingServiceController()


@pytest.mark.parametrize("exit_code", [0, 19])
def test_owned_controller_reports_alive_and_exact_exit_code(
    tmp_path: Path, monkeypatch, exit_code: int
) -> None:
    process = _FakeOwnedProcess()
    _, controller = _owned_controller(tmp_path, monkeypatch, process)
    controller.start()
    assert controller.service_pid == process.pid
    assert controller.is_running() is True
    assert controller.exit_code() is None
    process.return_code = exit_code
    assert controller.is_running() is False
    assert controller.exit_code() == exit_code
    controller.stop()
    assert not controller.pid_path.exists()


def test_strict_liveness_requires_real_status_and_healthy_flag() -> None:
    module = _module()
    assert module.strict_liveness_passes(
        {"health_status": "ok", "health_healthy": True}
    )
    assert not module.strict_liveness_passes(
        {"health_status": None, "health_healthy": True}
    )


def test_runtime_evidence_serializes_reuse_versions_pid_and_config_hash(
    tmp_path: Path, monkeypatch
) -> None:
    process = _FakeOwnedProcess(pid=9876)
    module, controller = _owned_controller(tmp_path, monkeypatch, process)
    controller.start()
    monkeypatch.setenv("PHASE05_PROVIDER_ENV_REUSED", "true")
    monkeypatch.setenv("PHASE05_OPENVIKING_VERSION", "0.4.22")
    monkeypatch.setenv("PHASE05_LLAMA_CPP_PYTHON_VERSION", "0.3.35")
    evidence = module._runtime_evidence(controller)
    assert evidence == {
        "provider_environment_reused": True,
        "openviking_version": "0.4.22",
        "llama_cpp_python_version": "0.3.35",
        "service_pid": 9876,
        "config_sha256": hashlib.sha256(controller.config.read_bytes()).hexdigest(),
    }
    assert "api_key" not in json.dumps(evidence).casefold()
    controller.stop()


def test_canary_result_fields_promote_complete_correlation() -> None:
    module = _module()
    fields = module._canary_result_fields(
        {
            "session_id": "session-1",
            "archive_uri": "viking://archive/1",
            "task_id": "task-1",
            "task_final_status": "completed",
            "task_submitted_at": "2026-09-29T00:00:00Z",
            "task_completed_at": "2026-09-29T00:00:02Z",
            "quiescence_seconds": 2.0,
            "provider_memory_uri_count": 1,
            "memory_diff_add_count": 1,
            "memory_diff_update_count": 0,
            "memory_diff_delete_count": 0,
            "memory_diff_skipped_count": 0,
        }
    )
    assert fields["canary_session_id"] == "session-1"
    assert fields["canary_task_final_status"] == "completed"
    assert fields["canary_quiescence_seconds"] == 2.0
    assert fields["canary_memory_diff_add_count"] == 1


def test_owned_controller_preserves_pid_ownership_and_uses_bounded_log_tail(
    tmp_path: Path, monkeypatch
) -> None:
    process = _FakeOwnedProcess()
    module, controller = _owned_controller(tmp_path, monkeypatch, process)
    controller.start()
    controller.pid_path.write_text("9999\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="PID ownership changed"):
        controller.stop()

    controller.log_path.write_text(
        "\n".join(f"line-{index}" for index in range(60)), encoding="utf-8"
    )
    tail = module._service_log_tail(controller.log_path)
    assert len(tail) == 40
    assert tail[0] == "line-20"
    source = PYTHON_SCRIPT.read_text(encoding="utf-8")
    assert "pkill" not in source and "killall" not in source


def test_process_exit_serializes_startup_blocker(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    monkeypatch.setenv(module.LIVE_AUTH_ENV, "YES")
    log_path = tmp_path / "openviking.log"
    log_path.write_text("lifespan failed\n", encoding="utf-8")

    class FakeController:
        def __init__(self):
            self.log_path = log_path

        def start(self):
            raise module.ServiceExitedBeforeReady(23)

        def stop(self):
            return None

        def restart(self):
            return None

        def is_running(self):
            return False

        def exit_code(self):
            return 23

        def log_tail(self, *, lines=40):
            return module._service_log_tail(self.log_path, lines=lines)

    class FakeAdapter:
        @staticmethod
        def from_environment(**kwargs):
            return object()

    fake_modules = {
        "memlife.adapters.openviking": {
            "OpenVikingMemoryAdapter": FakeAdapter,
            "ServiceExitedBeforeReady": RuntimeError,
        },
        "memlife.models.memory": {"QueryCommand": object, "WriteCommand": object},
        "memlife.runner.provenance": {"ProvenanceTraceRunner": object},
        "memlife.scenarios.canonical": {"canonical_scenarios": lambda: []},
    }
    for name, attributes in fake_modules.items():
        fake = types.ModuleType(name)
        for attribute, value in attributes.items():
            setattr(fake, attribute, value)
        monkeypatch.setitem(sys.modules, name, fake)
    monkeypatch.setattr(module, "OpenVikingServiceController", FakeController)
    output = tmp_path / "result.json"
    module.validate_remote(output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "BLOCKED"
    assert result["stage"] == "service_startup"
    assert result["blocker_type"] == "ServiceExitedBeforeReady"
    assert result["service_process_alive"] is False
    assert result["service_exit_code"] == 23
    assert result["service_log_tail"] == ["lifespan failed"]


def test_provider_failure_serializes_blocked_result_and_sanitized_log(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    monkeypatch.setenv(module.LIVE_AUTH_ENV, "YES")
    monkeypatch.setenv("PHASE05_OPENVIKING_VLM_API_KEY", "actual-secret")
    log_path = tmp_path / "openviking.log"
    log_path.write_text(
        'startup\n{"api_key": "actual-secret", "host": "203.0.113.8"}\nprovider failed\n',
        encoding="utf-8",
    )

    class FakeController:
        def __init__(self):
            self.log_path = log_path

        def start(self):
            raise RuntimeError("provider failed with api_key=actual-secret at 203.0.113.8")

        def stop(self):
            return None

        def restart(self):
            return None

        def is_running(self):
            return False

        def exit_code(self):
            return 1

        def log_tail(self, *, lines=40):
            return module._service_log_tail(self.log_path, lines=lines)

    class FakeAdapter:
        @staticmethod
        def from_environment(**kwargs):
            return object()

    class FakeAdapterServiceExitedBeforeReady(RuntimeError):
        pass

    fake_modules = {
        "memlife.adapters.openviking": ("OpenVikingMemoryAdapter", FakeAdapter),
        "memlife.models.memory": ("QueryCommand", object),
        "memlife.runner.provenance": ("ProvenanceTraceRunner", object),
        "memlife.scenarios.canonical": ("canonical_scenarios", lambda: []),
    }
    for name, (attribute, value) in fake_modules.items():
        fake = types.ModuleType(name)
        setattr(fake, attribute, value)
        if name == "memlife.adapters.openviking":
            fake.ServiceExitedBeforeReady = FakeAdapterServiceExitedBeforeReady
        if name == "memlife.models.memory":
            fake.WriteCommand = object
        monkeypatch.setitem(sys.modules, name, fake)
    monkeypatch.setattr(module, "OpenVikingServiceController", FakeController)
    output = tmp_path / "result.json"
    module.validate_remote(output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "BLOCKED"
    assert result["blocker_type"] == "RuntimeError"
    assert result["blocker"]
    encoded = base64.b64encode(output.read_bytes())
    assert json.loads(base64.b64decode(encoded))["status"] == "BLOCKED"
    serialized = json.dumps(result)
    assert "actual-secret" not in serialized
    assert "203.0.113.8" not in serialized
    assert "api_key" not in result
    assert result["service_log_tail"][-1] == "provider failed"


def test_prevalidator_blocked_result_is_bounded_and_sanitized(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    monkeypatch.setenv("PHASE05_OPENVIKING_VLM_API_KEY", "do-not-record")
    diagnostic = tmp_path / "install.log"
    diagnostic.write_text(
        "x" * 9000
        + " api_key=do-not-record token=also-secret at 203.0.113.9",
        encoding="utf-8",
    )
    output = tmp_path / "result.json"
    result = module.write_blocked_result(
        output,
        stage="provider_install",
        blocker_type="Compiler/Toolchain Error!",
        diagnostic_file=diagnostic,
    )
    assert result["status"] == "BLOCKED"
    assert result["stage"] == "provider_install"
    assert result["blocker_type"] == "CompilerToolchainError"
    assert len(result["blocker"]) <= 8000
    serialized = output.read_text(encoding="utf-8")
    assert "do-not-record" not in serialized
    assert "also-secret" not in serialized
    assert "203.0.113.9" not in serialized


def test_remote_shell_emits_serialized_result_before_exit_check() -> None:
    text = REMOTE_SCRIPT.read_text(encoding="utf-8")
    assert "|| VALIDATOR_STATUS=$?" in text
    assert text.index("PHASE05_RESULT_B64=") < text.index('test "$VALIDATOR_STATUS" -eq 0')
    for stage in (
        "dependency_dry_run",
        "dependency_plan",
        "provider_install",
        "pip_check",
        "executable_validation",
        "config_generation",
    ):
        assert stage in text
    assert "PHASE05_PROVIDER_ENV_REUSED" in text
    assert "PHASE05_OPENVIKING_VERSION" in text
    assert "PHASE05_LLAMA_CPP_PYTHON_VERSION" in text
    assert "importlib.metadata" in text


def test_result_payload_rejects_api_key_fields() -> None:
    module = _module()
    assert module._contains_sensitive_result_key({"api_key": "redacted"}) is True
    assert module._contains_sensitive_result_key({"nested": {"secret": "x"}}) is True
    assert module._contains_sensitive_result_key({"nested": [{"status": "BLOCKED"}]}) is False


def test_future_validator_runs_canonical_and_provenance_once() -> None:
    text = PYTHON_SCRIPT.read_text(encoding="utf-8")
    assert "ProvenanceTraceRunner(adapter).run_scenario" in text
    assert "LifecycleRunner(adapter).run_suite" not in text


def test_managed_controller_owns_fip_cleanup_and_shelving() -> None:
    controller = (ROOT / "scripts" / "jetstream" / "jetstreamctl.py").read_text(
        encoding="utf-8"
    )
    assert "run_phase05" in controller
    assert "cleanup_owned_floating_ip" in controller
    assert 'server_action(credentials, "shelve")' in controller
