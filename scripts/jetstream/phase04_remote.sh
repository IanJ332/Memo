#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'CONVERSATION: START NEW'
printf '%s\n' 'MODEL: gpt-oss-120b (Hindsight internal only)'
printf '%s\n' 'EXECUTION TARGET: LOCAL orchestration + ONE controlled Jetstream2 session'
printf '%s\n' 'JETSTREAM ACTION: managed unshelve/work/collect/FIP-delete/shelve'

REPO=/home/exouser/Memo
HARNESS_PYTHON="$REPO/.venv/bin/python"
LIVE_VOLUME_MOUNT="$(findmnt -n -o TARGET /dev/sdb)"
LIVE_VOLUME_SOURCE="$(findmnt -n -o SOURCE /dev/sdb)"
LIVE_VOLUME_FSTYPE="$(findmnt -n -o FSTYPE /dev/sdb)"

test -n "$LIVE_VOLUME_MOUNT"
test -d "$LIVE_VOLUME_MOUNT"
MEMLIFE_DATA_ROOT="$LIVE_VOLUME_MOUNT/memlife"
HINDSIGHT_VENV="$MEMLIFE_DATA_ROOT/venvs/hindsight-0.10.1"
HINDSIGHT_PYTHON="$HINDSIGHT_VENV/bin/python"
HINDSIGHT_SERVICE="$HINDSIGHT_VENV/bin/hindsight-api"
PROVIDER_ROOT="$MEMLIFE_DATA_ROOT/providers/hindsight"
MODEL_CACHE="$MEMLIFE_DATA_ROOT/model_cache/hindsight"
RUN_ROOT="$MEMLIFE_DATA_ROOT/runs/phase-04-hindsight"
ARTIFACT_ROOT="$MEMLIFE_DATA_ROOT/artifacts"
PG0_ROOT="$PROVIDER_ROOT/pg0"
mkdir -p "$MEMLIFE_DATA_ROOT/venvs" "$PROVIDER_ROOT" "$MODEL_CACHE" "$RUN_ROOT" "$ARTIFACT_ROOT" "$PG0_ROOT"

ROOT_FREE_BEFORE="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_BEFORE="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
df -h /
df -h "$LIVE_VOLUME_MOUNT"
findmnt -n -o TARGET,SOURCE,FSTYPE /dev/sdb
if [ "$ROOT_FREE_BEFORE" -lt 1073741824 ]; then
    printf '%s\n' 'Root disk has less than 1 GiB free; refusing harness validation.' >&2
    exit 30
fi
if [ "$VOLUME_FREE_BEFORE" -lt 4294967296 ]; then
    printf '%s\n' 'Persistent volume has less than 4 GiB free; refusing provider setup.' >&2
    exit 31
fi

PG0_LINK=/home/exouser/.pg0
if [ -L "$PG0_LINK" ]; then
    test "$(readlink -f "$PG0_LINK")" = "$(readlink -f "$PG0_ROOT")"
elif [ -e "$PG0_LINK" ]; then
    printf '%s\n' 'Existing /home/exouser/.pg0 is not the managed persistent-volume link.' >&2
    exit 32
else
    ln -s "$PG0_ROOT" "$PG0_LINK"
fi

export MEMLIFE_DATA_ROOT
export MEMLIFE_HINDSIGHT_BASE_URL=http://127.0.0.1:8888
export HF_HOME="$MODEL_CACHE/huggingface"
export HUGGINGFACE_HUB_CACHE="$MODEL_CACHE/huggingface/hub"
export TRANSFORMERS_CACHE="$MODEL_CACHE/huggingface"
export TOKENIZERS_PARALLELISM=false
export HINDSIGHT_API_DATABASE_URL=pg0://memlife-phase04
export HINDSIGHT_API_HOST=127.0.0.1
export HINDSIGHT_API_PORT=8888
export HINDSIGHT_API_LLM_PROVIDER=openai
export HINDSIGHT_API_LLM_BASE_URL=https://llm.jetstream-cloud.org/gpt-oss-120b/v1/
export HINDSIGHT_API_LLM_API_KEY=empty
export HINDSIGHT_API_LLM_MODEL=gpt-oss-120b
export HINDSIGHT_API_EMBEDDINGS_PROVIDER=onnx
export HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID=intfloat/multilingual-e5-small
export HINDSIGHT_API_EMBEDDINGS_ONNX_DIMENSIONS=384
export HINDSIGHT_API_EMBEDDINGS_ONNX_QUERY_PREFIX='query: '
export HINDSIGHT_API_EMBEDDINGS_ONNX_PASSAGE_PREFIX='passage: '
export HINDSIGHT_API_RERANKER_PROVIDER=rrf
export HINDSIGHT_API_WORKERS=1
export HINDSIGHT_API_WORKER_MAX_SLOTS=2
export HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS=1
export HINDSIGHT_API_WORKER_GRAPH_MAINTENANCE_RESERVED_SLOTS=1
export HINDSIGHT_API_RETAIN_BATCH_ENABLED=false

capture_harness_health() {
    label="$1"
    log="$RUN_ROOT/harness-${label}.log"
    if ! {
        "$HARNESS_PYTHON" --version
        "$HARNESS_PYTHON" -m pip --version
        "$HARNESS_PYTHON" -m pip show mem0ai
        "$HARNESS_PYTHON" -m pip show protobuf
        "$HARNESS_PYTHON" -m pip check
    } > "$log" 2>&1; then
        printf 'Harness environment check failed (%s).\n' "$label" >&2
        tail -n 100 "$log" >&2
        exit 33
    fi
}

test -x "$HARNESS_PYTHON"
"$HARNESS_PYTHON" -m pip install -r "$REPO/requirements/core.txt"
capture_harness_health before-hindsight

HINDSIGHT_VENV_CREATED_BY_THIS_RUN=false
if [ ! -e "$HINDSIGHT_VENV" ]; then
    python3 -m venv "$HINDSIGHT_VENV"
    HINDSIGHT_VENV_CREATED_BY_THIS_RUN=true
elif [ ! -d "$HINDSIGHT_VENV" ] || [ ! -x "$HINDSIGHT_PYTHON" ]; then
    printf '%s\n' 'Existing Hindsight venv path is incomplete; refusing automatic rebuild.' >&2
    exit 34
fi

DRY_RUN_REPORT="$RUN_ROOT/hindsight-pip-dry-run.json"
DRY_RUN_LOG="$RUN_ROOT/hindsight-pip-dry-run.log"
if [ "$HINDSIGHT_VENV_CREATED_BY_THIS_RUN" = true ]; then
    "$HINDSIGHT_PYTHON" -m pip install --dry-run --report "$DRY_RUN_REPORT" -r "$REPO/requirements/providers/hindsight.txt" > "$DRY_RUN_LOG"
    DRY_RUN_SUMMARY="$("$HINDSIGHT_PYTHON" - "$DRY_RUN_REPORT" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
names = sorted({item.get("metadata", {}).get("name", "") for item in data.get("install", [])})
flagged = [name for name in names if name.lower() == "torch" or name.lower().startswith("nvidia-")]
print(json.dumps({"package_count": len(names), "flagged": flagged}, separators=(",", ":")))
if flagged:
    raise SystemExit(9)
PY
)" || {
        printf '%s\n' 'Provider dry run would install Torch/CUDA/NVIDIA packages; refusing installation.' >&2
        exit 35
    }
    "$HINDSIGHT_PYTHON" -m pip install --no-cache-dir -r "$REPO/requirements/providers/hindsight.txt"
else
    DRY_RUN_SUMMARY='{"status":"REUSED_VALIDATED_ISOLATED_VENV"}'
fi

PROVIDER_CHECK_LOG="$RUN_ROOT/hindsight-environment-check.log"
if ! {
    "$HINDSIGHT_PYTHON" --version
    "$HINDSIGHT_PYTHON" -m pip --version
    "$HINDSIGHT_PYTHON" -m pip show protobuf
    "$HINDSIGHT_PYTHON" -m pip show hindsight-api-slim
    "$HINDSIGHT_PYTHON" -m pip check
    "$HINDSIGHT_PYTHON" -c 'import importlib.metadata as m; assert m.version("hindsight-api-slim") == "0.10.1"'
    test -x "$HINDSIGHT_SERVICE"
} > "$PROVIDER_CHECK_LOG" 2>&1; then
    printf '%s\n' 'Existing Hindsight venv is incomplete or inconsistent; refusing automatic rebuild.' >&2
    tail -n 100 "$PROVIDER_CHECK_LOG" >&2
    exit 36
fi
if "$HINDSIGHT_PYTHON" -m pip show hindsight-client > /dev/null 2>&1; then
    printf '%s\n' 'Unneeded hindsight-client package found in service-only provider venv.' >&2
    exit 37
fi
if ! "$HINDSIGHT_PYTHON" -m pip list --format=json | "$HINDSIGHT_PYTHON" -c 'import json,sys; names=[p["name"] for p in json.load(sys.stdin) if p["name"].lower().startswith("nvidia-")]; raise SystemExit(1 if names else 0)'; then
    printf '%s\n' 'NVIDIA packages detected in provider venv; stopping Phase 04.' >&2
    exit 38
fi

FINGERPRINT_FILE="$RUN_ROOT/hindsight-environment-fingerprint.json"
"$HINDSIGHT_PYTHON" "$REPO/scripts/jetstream/phase04_runtime.py" fingerprint --output "$FINGERPRINT_FILE"
capture_harness_health after-hindsight

cd "$REPO"
UNIT_LOG="$RUN_ROOT/unit-contract.log"
if ! "$HARNESS_PYTHON" -m pytest tests/unit tests/contract -q -p no:cacheprovider > "$UNIT_LOG" 2>&1; then
    tail -n 100 "$UNIT_LOG" >&2
    exit 40
fi

export PHASE04_REPO="$REPO"
export PHASE04_HARNESS_PYTHON="$HARNESS_PYTHON"
export PHASE04_HINDSIGHT_PYTHON="$HINDSIGHT_PYTHON"
export PHASE04_HINDSIGHT_VENV="$HINDSIGHT_VENV"
export PHASE04_HINDSIGHT_SERVICE="$HINDSIGHT_SERVICE"
export PHASE04_RUN_ROOT="$RUN_ROOT"
export PHASE04_ARTIFACT_ROOT="$ARTIFACT_ROOT"
export PHASE04_LIVE_VOLUME_MOUNT="$LIVE_VOLUME_MOUNT"
export PHASE04_LIVE_VOLUME_SOURCE="$LIVE_VOLUME_SOURCE"
export PHASE04_LIVE_VOLUME_FSTYPE="$LIVE_VOLUME_FSTYPE"
export PHASE04_ROOT_FREE_BEFORE="$ROOT_FREE_BEFORE"
export PHASE04_VOLUME_FREE_BEFORE="$VOLUME_FREE_BEFORE"
export PHASE04_DRY_RUN_SUMMARY="$DRY_RUN_SUMMARY"
export PHASE04_UNIT_SUMMARY="$(tail -n 1 "$UNIT_LOG")"
export PHASE04_ENVIRONMENT_FINGERPRINT="$FINGERPRINT_FILE"
export PHASE04_HINDSIGHT_VENV_CREATED_BY_THIS_RUN
export PHASE04_HARNESS_PIP_CHECK_BEFORE=PASS
export PHASE04_HINDSIGHT_PIP_CHECK=PASS
export PHASE04_HARNESS_PIP_CHECK_AFTER=PASS

RESULT_FILE="$RUN_ROOT/phase-04-result.json"
"$HARNESS_PYTHON" scripts/jetstream/phase04_hindsight_validate.py --output "$RESULT_FILE"
cp "$RESULT_FILE" "$ARTIFACT_ROOT/phase-04-hindsight-result.json"
printf 'PHASE04_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT_FILE")"
