"""Validate Experiment Freeze v1 and optionally enforce the Phase 06B gate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.runner.freeze import (  # noqa: E402
    FREEZE_SHA256,
    load_freeze_from_git,
)

DEFAULT_FREEZE = REPO_ROOT / "experiments" / "freeze" / "experiment-freeze-v1.json"
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "phase-06a-mem0-calibration-freeze.json"
EXPECTED_PROVIDERS = {"mem0": "2.2.1", "hindsight": "0.10.1", "openviking": "0.4.22"}
EXPECTED_SCENARIOS = {f"S{index}" for index in range(6)}
EXPECTED_EXACT = {"CURRENT_ONLY", "CURRENT_AND_STALE", "STALE_ONLY", "ABSENT", "UNSUPPORTED", "ERROR"}
EXPECTED_AUTHORITY = {"AUTHORITATIVE_ONLY", "AUTHORITATIVE_AND_NONAUTHORITATIVE", "NONAUTHORITATIVE_ONLY", "NONE", "UNKNOWN_PROVENANCE"}
EXPECTED_MODELS = {"llama-4-scout", "gpt-oss-120b", "muse-glimmer"}
SUSPICIOUS_KEY = re.compile(r"(?i)(api.?key|password|private.?key|access.?token|refresh.?token|credential)")


def _all_numbers(value: Any) -> Iterable[float]:
    if isinstance(value, dict):
        for nested in value.values():
            yield from _all_numbers(nested)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def _suspicious_paths(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            child = f"{path}.{key}" if path else key
            if SUSPICIOUS_KEY.search(key):
                found.append(child)
            found.extend(_suspicious_paths(nested, child))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_suspicious_paths(nested, f"{path}[{index}]"))
    return found


def validate_freeze(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    providers = payload.get("providers", [])
    provider_versions = {item.get("id"): item.get("version") for item in providers}
    if provider_versions != EXPECTED_PROVIDERS:
        errors.append(f"provider set/version mismatch: {provider_versions!r}")
    if len(providers) != 3:
        errors.append("freeze must contain exactly three providers")

    scenarios = payload.get("scenarios", [])
    scenario_ids = [item.get("id") for item in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)) or set(scenario_ids) != EXPECTED_SCENARIOS:
        errors.append("scenario IDs must be unique S0 through S5")

    matrix = payload.get("capability_matrix", {})
    if set(matrix) != set(EXPECTED_PROVIDERS):
        errors.append("capability matrix provider set is incomplete")
    for provider in EXPECTED_PROVIDERS:
        cells = matrix.get(provider, {})
        if set(cells) != EXPECTED_SCENARIOS:
            errors.append(f"{provider} capability matrix is incomplete")
        invalid = set(cells.values()) - {"SUPPORTED", "UNSUPPORTED"}
        if invalid:
            errors.append(f"{provider} has unresolved/invalid cells: {sorted(invalid)}")

    if payload.get("repetitions_per_supported_provider_scenario") != 3:
        errors.append("repetitions must equal 3")
    if payload.get("storage_batch_downstream_decision_calls") != 0:
        errors.append("storage batch downstream decision calls must equal 0")
    if not payload.get("run_id_template"):
        errors.append("run ID template is required")
    if not payload.get("namespace_template"):
        errors.append("namespace template is required")
    if payload.get("run_order", {}).get("ordering") != "provider -> scenario -> repetition":
        errors.append("deterministic provider/scenario/repetition order is required")
    timeout_values = list(_all_numbers(payload.get("timeouts_seconds", {})))
    if not timeout_values or any(value <= 0 for value in timeout_values):
        errors.append("all centralized timeout values must be positive")
    if set(payload.get("exact_visibility_outcomes", {})) != EXPECTED_EXACT:
        errors.append("exact visibility outcomes are incomplete")
    if set(payload.get("authority_exposure_outcomes", {})) != EXPECTED_AUTHORITY:
        errors.append("authority exposure outcomes are incomplete")
    if not payload.get("residual_advancement_rule"):
        errors.append("residual advancement rule is required")
    if not payload.get("root_cause_advancement_rule"):
        errors.append("root-cause advancement rule is required")
    if len(payload.get("rq3_advancement_rule", [])) != 4:
        errors.append("RQ3 advancement rule must have four gates")
    future = payload.get("future_rq3", {})
    if set(future.get("models", [])) != EXPECTED_MODELS:
        errors.append("future RQ3 model set mismatch")
    if future.get("decision_call_planning_cap") != 54:
        errors.append("future RQ3 call cap must equal 54")
    if set(payload.get("defense_conditions", {})) != {"D0", "D1", "D2"}:
        errors.append("D0/D1/D2 definitions are required")
    if _suspicious_paths(payload):
        errors.append(f"suspicious secret fields: {_suspicious_paths(payload)!r}")
    return errors


def validate_phase06b_gate(
    payload: dict[str, Any],
    *,
    expected_repo_commit: str,
    runtime_evidence: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=REPO_ROOT, check=True,
        text=True, capture_output=True,
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
        text=True, capture_output=True,
    ).stdout.strip()
    if branch != "phase-06-experiment-freeze":
        errors.append("Phase 06B branch mismatch")
    if head != expected_repo_commit:
        errors.append("Phase 06B commit mismatch")
    frozen = {item["id"]: item for item in payload["providers"]}
    runtime_providers = runtime_evidence.get("providers", {})
    if set(runtime_providers) != set(frozen):
        errors.append("runtime provider set mismatch")
    for provider_id, provider in frozen.items():
        runtime = runtime_providers.get(provider_id, {})
        if runtime.get("version") != provider["version"]:
            errors.append(f"{provider_id} runtime version mismatch")
        if runtime.get("configuration_hash") != provider["configuration_hash"]:
            errors.append(f"{provider_id} runtime configuration hash mismatch")
    if runtime_evidence.get("repetitions") != 3:
        errors.append("runtime repetitions mismatch")
    if runtime_evidence.get("downstream_decision_calls") != 0:
        errors.append("runtime downstream decision calls must equal 0")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--phase06b-preflight", action="store_true")
    parser.add_argument("--expected-repo-commit")
    parser.add_argument("--runtime-evidence", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        materialization = load_freeze_from_git(args.freeze)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    payload = materialization.payload
    errors = validate_freeze(payload)
    digest = materialization.sha256
    if digest != FREEZE_SHA256:
        errors.append(f"freeze canonical SHA-256 mismatch: {digest}")
    if args.manifest.exists():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if manifest.get("experiment_freeze_sha256") != digest:
            errors.append("freeze SHA-256 does not match Phase 06A manifest")
    if args.phase06b_preflight:
        if not args.expected_repo_commit or args.runtime_evidence is None:
            errors.append("Phase 06B preflight requires exact commit and runtime evidence")
        else:
            runtime = json.loads(args.runtime_evidence.read_text(encoding="utf-8"))
            errors.extend(
                validate_phase06b_gate(
                    payload,
                    expected_repo_commit=args.expected_repo_commit,
                    runtime_evidence=runtime,
                )
            )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS experiment-freeze-v1 sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
