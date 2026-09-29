#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'CONVERSATION: START NEW'
printf '%s\n' 'MODEL: future explicitly authorized provider-internal VLM only'
printf '%s\n' 'EXECUTION TARGET: ONE controlled Jetstream2 session'
printf '%s\n' 'JETSTREAM ACTION: managed unshelve/work/collect/owned-FIP-delete/shelve'

test "${MEMLIFE_AUTHORIZE_PHASE05_LIVE:-}" = YES

REPO=/home/exouser/Memo
LIVE_CONFIG="$REPO/.local/phase05_openviking.env"
test -f "$LIVE_CONFIG"
LIVE_CONFIG_MODE="$(stat -c %a "$LIVE_CONFIG")"
test "$LIVE_CONFIG_MODE" = 600 || {
    printf '%s\n' 'Phase 05 live config must have mode 600' >&2
    exit 42
}
set -a
. "$LIVE_CONFIG"
set +a
: "${PHASE05_OPENVIKING_VLM_PROVIDER:?future VLM provider is required}"
: "${PHASE05_OPENVIKING_VLM_MODEL:?future VLM model is required}"
: "${PHASE05_OPENVIKING_VLM_API_BASE:?future VLM endpoint is required}"
: "${PHASE05_OPENVIKING_VLM_API_KEY:?future VLM credential is required}"

LEGACY_VENV="$REPO/.venv"
LIVE_VOLUME_MOUNT="$(findmnt -n -o TARGET /dev/sdb)"
test -n "$LIVE_VOLUME_MOUNT"
test -d "$LIVE_VOLUME_MOUNT"
MEMLIFE_DATA_ROOT="$LIVE_VOLUME_MOUNT/memlife"
HARNESS_VENV="$MEMLIFE_DATA_ROOT/venvs/memlife-harness-phase04"
HARNESS_PYTHON="$HARNESS_VENV/bin/python"
OPENVIKING_VENV="$MEMLIFE_DATA_ROOT/venvs/openviking-0.4.22"
OPENVIKING_PYTHON="$OPENVIKING_VENV/bin/python"
OPENVIKING_SERVICE="$OPENVIKING_VENV/bin/openviking-server"
PROVIDER_STATE="$MEMLIFE_DATA_ROOT/providers/openviking"
MODEL_CACHE="$MEMLIFE_DATA_ROOT/model_cache/openviking"
RUN_ROOT="$MEMLIFE_DATA_ROOT/runs/phase-05-openviking"
CONFIG="$PROVIDER_STATE/ov.conf"
RESULT="$RUN_ROOT/phase-05-result.json"
OPENVIKING_REQUIREMENTS="$REPO/requirements/providers/openviking.txt"
LLAMA_CPU_WHEEL_INDEX="https://abetlen.github.io/llama-cpp-python/whl/cpu"
PLAN_REPORT="$RUN_ROOT/openviking-pip-plan.json"
PLAN_RESULT="$RUN_ROOT/openviking-dependency-plan-result.json"

emit_result() {
    printf 'PHASE05_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT")"
}

blocked_result() {
    stage="$1"
    blocker_type="$2"
    diagnostic_file="${3:-}"
    if [ -n "$diagnostic_file" ]; then
        "$HARNESS_PYTHON" "$REPO/scripts/jetstream/phase05_openviking.py" blocked-result \
            --output "$RESULT" --stage "$stage" --type "$blocker_type" \
            --diagnostic-file "$diagnostic_file"
    else
        "$HARNESS_PYTHON" "$REPO/scripts/jetstream/phase05_openviking.py" blocked-result \
            --output "$RESULT" --stage "$stage" --type "$blocker_type" \
            --message "$stage failed"
    fi
    emit_result
    exit 0
}

test "$HARNESS_VENV" != "$LEGACY_VENV"
test -x "$HARNESS_PYTHON"
ROOT_FREE_BEFORE="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_BEFORE="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
test "$ROOT_FREE_BEFORE" -ge 1073741824
test "$VOLUME_FREE_BEFORE" -ge 8589934592
mkdir -p "$MEMLIFE_DATA_ROOT/venvs" "$PROVIDER_STATE" "$MODEL_CACHE/pip" "$RUN_ROOT"

export PIP_CACHE_DIR="$MODEL_CACHE/pip"
export HF_HOME="$MODEL_CACHE/huggingface"
export MEMLIFE_OPENVIKING_BASE_URL=http://127.0.0.1:1933
export PHASE05_OPENVIKING_SERVICE="$OPENVIKING_SERVICE"
export PHASE05_OPENVIKING_CONFIG="$CONFIG"
export PHASE05_PROVIDER_STATE="$PROVIDER_STATE"
export PHASE05_MODEL_CACHE="$MODEL_CACHE"
export PHASE05_RUN_ROOT="$RUN_ROOT"

if [ ! -e "$OPENVIKING_VENV" ]; then
    python3 -m venv "$OPENVIKING_VENV"
fi
DRY_RUN_LOG="$RUN_ROOT/openviking-pip-dry-run.log"
if ! "$OPENVIKING_PYTHON" -m pip install --dry-run --ignore-installed \
    --report "$PLAN_REPORT" --extra-index-url "$LLAMA_CPU_WHEEL_INDEX" \
    -r "$OPENVIKING_REQUIREMENTS" >"$DRY_RUN_LOG" 2>&1; then
    blocked_result dependency_dry_run PipDryRunError "$DRY_RUN_LOG"
fi
if ! "$HARNESS_PYTHON" "$REPO/scripts/jetstream/phase05_openviking.py" \
    dependency-plan --report "$PLAN_REPORT" --output "$PLAN_RESULT"; then
    blocked_result dependency_plan DependencyPlanValidationError
fi
if [ "$("$HARNESS_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$PLAN_RESULT")" != PASS ]; then
    cp "$PLAN_RESULT" "$RESULT"
    emit_result
    exit 0
fi

INSTALL_LOG="$RUN_ROOT/openviking-install.log"
if ! "$OPENVIKING_PYTHON" -m pip install --no-cache-dir \
    --extra-index-url "$LLAMA_CPU_WHEEL_INDEX" \
    -r "$OPENVIKING_REQUIREMENTS" >"$INSTALL_LOG" 2>&1; then
    blocked_result provider_install ProviderInstallError "$INSTALL_LOG"
fi

PIP_CHECK_LOG="$RUN_ROOT/openviking-pip-check.log"
if ! "$OPENVIKING_PYTHON" -m pip check >"$PIP_CHECK_LOG" 2>&1; then
    blocked_result pip_check PipCheckError "$PIP_CHECK_LOG"
fi
if ! "$OPENVIKING_PYTHON" -c 'import importlib.metadata as m; assert m.version("openviking") == "0.4.22"; assert m.version("llama-cpp-python")'; then
    blocked_result executable_validation DistributionMetadataError
fi
if [ ! -x "$OPENVIKING_SERVICE" ]; then
    blocked_result executable_validation MissingOpenVikingExecutable
fi
if "$OPENVIKING_PYTHON" -m pip list --format=json | "$HARNESS_PYTHON" -c 'import json,sys; n=[p["name"].lower() for p in json.load(sys.stdin)]; raise SystemExit(0 if any(x.startswith(("nvidia-","cuda-")) for x in n) else 1)'; then
    blocked_result pip_check ForbiddenInstalledDistribution
fi

cd "$REPO"
CONFIG_LOG="$RUN_ROOT/openviking-config.log"
if ! "$HARNESS_PYTHON" scripts/jetstream/phase05_openviking.py write-config \
    --output "$CONFIG" >"$CONFIG_LOG" 2>&1; then
    blocked_result config_generation ConfigGenerationError "$CONFIG_LOG"
fi
VALIDATOR_STATUS=0
"$HARNESS_PYTHON" scripts/jetstream/phase05_openviking.py validate --output "$RESULT" || VALIDATOR_STATUS=$?
if [ -s "$RESULT" ]; then
    emit_result
else
    printf '%s\n' 'Phase 05 validator produced no structured result' >&2
    exit 46
fi
test "$VALIDATOR_STATUS" -eq 0
