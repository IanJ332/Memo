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
case "$LIVE_CONFIG_MODE" in
    400|600) ;;
    *) printf '%s\n' 'Phase 05 live config must have mode 400 or 600' >&2; exit 42 ;;
esac
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
    "$OPENVIKING_PYTHON" -m pip install --dry-run --report "$RUN_ROOT/openviking-pip-plan.json" 'openviking==0.4.22'
    if "$HARNESS_PYTHON" -c 'import json,sys; p=json.load(open(sys.argv[1])); n=[str(x.get("metadata",{}).get("name","")).lower() for x in p.get("install",[])]; raise SystemExit(0 if any(x.startswith(("nvidia-","cuda-")) for x in n) else 1)' "$RUN_ROOT/openviking-pip-plan.json"; then
        printf '%s\n' 'OpenViking plan includes unexpected CUDA/NVIDIA packages' >&2
        exit 44
    fi
    "$OPENVIKING_PYTHON" -m pip install --no-cache-dir 'openviking==0.4.22'
fi

"$OPENVIKING_PYTHON" -m pip check
"$OPENVIKING_PYTHON" -c 'import importlib.metadata as m; assert m.version("openviking") == "0.4.22"'
test -x "$OPENVIKING_SERVICE"
if "$OPENVIKING_PYTHON" -m pip list --format=json | "$HARNESS_PYTHON" -c 'import json,sys; n=[p["name"].lower() for p in json.load(sys.stdin)]; raise SystemExit(0 if any(x.startswith(("nvidia-","cuda-")) for x in n) else 1)'; then
    printf '%s\n' 'OpenViking environment contains unexpected CUDA/NVIDIA packages' >&2
    exit 45
fi

cd "$REPO"
"$HARNESS_PYTHON" scripts/jetstream/phase05_openviking.py write-config --output "$CONFIG"
"$HARNESS_PYTHON" scripts/jetstream/phase05_openviking.py validate --output "$RESULT"
printf 'PHASE05_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT")"
