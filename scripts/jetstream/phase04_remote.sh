#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'CONVERSATION: START NEW'
printf '%s\n' 'MODEL: gpt-oss-120b (Hindsight internal only)'
printf '%s\n' 'EXECUTION TARGET: LOCAL orchestration + ONE controlled Jetstream2 session'
printf '%s\n' 'JETSTREAM ACTION: managed unshelve/work/collect/FIP-delete/shelve'

REPO=/home/exouser/Memo
LEGACY_HARNESS_VENV="$REPO/.venv"
LEGACY_HARNESS_PYTHON="$LEGACY_HARNESS_VENV/bin/python"
LIVE_VOLUME_MOUNT="$(findmnt -n -o TARGET /dev/sdb)"
LIVE_VOLUME_SOURCE="$(findmnt -n -o SOURCE /dev/sdb)"
LIVE_VOLUME_FSTYPE="$(findmnt -n -o FSTYPE /dev/sdb)"

test -n "$LIVE_VOLUME_MOUNT"
test -d "$LIVE_VOLUME_MOUNT"
MEMLIFE_DATA_ROOT="$LIVE_VOLUME_MOUNT/memlife"
CLEAN_HARNESS_VENV="$MEMLIFE_DATA_ROOT/venvs/memlife-harness-phase04"
HARNESS_PYTHON="$CLEAN_HARNESS_VENV/bin/python"
HARNESS_FINGERPRINT="$CLEAN_HARNESS_VENV/.memlife-phase04-fingerprint.json"
HINDSIGHT_VENV="$MEMLIFE_DATA_ROOT/venvs/hindsight-0.10.1"
HINDSIGHT_PYTHON="$HINDSIGHT_VENV/bin/python"
HINDSIGHT_SERVICE="$HINDSIGHT_VENV/bin/hindsight-api"
PROVIDER_ROOT="$MEMLIFE_DATA_ROOT/providers/hindsight"
MEM0_PROVIDER_ROOT="$MEMLIFE_DATA_ROOT/providers/mem0/phase-04-clean-harness-gate"
MODEL_CACHE="$MEMLIFE_DATA_ROOT/model_cache"
HINDSIGHT_MODEL_CACHE="$MODEL_CACHE/hindsight"
RUN_ROOT="$MEMLIFE_DATA_ROOT/runs/phase-04-hindsight"
ARTIFACT_ROOT="$MEMLIFE_DATA_ROOT/artifacts"
PG0_ROOT="$PROVIDER_ROOT/pg0"
mkdir -p "$MEMLIFE_DATA_ROOT/venvs" "$MEM0_PROVIDER_ROOT" "$MODEL_CACHE/pip" "$MODEL_CACHE/huggingface" "$MODEL_CACHE/torch" "$RUN_ROOT" "$ARTIFACT_ROOT"

if [ "$HARNESS_PYTHON" = "$LEGACY_HARNESS_PYTHON" ]; then
    printf '%s\n' 'Legacy contaminated harness was selected; refusing Phase 04.' >&2
    exit 29
fi

ROOT_FREE_BEFORE="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_BEFORE="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
df -h /
df -h "$LIVE_VOLUME_MOUNT"
findmnt -n -o TARGET,SOURCE,FSTYPE /dev/sdb
if [ "$ROOT_FREE_BEFORE" -lt 1073741824 ]; then
    printf '%s\n' 'Root disk has less than 1 GiB free; refusing harness validation.' >&2
    exit 30
fi
if [ "$VOLUME_FREE_BEFORE" -lt 8589934592 ]; then
    printf '%s\n' 'Persistent volume has less than 8 GiB free; refusing clean runtime setup.' >&2
    exit 31
fi

export MEMLIFE_DATA_ROOT
export MEMLIFE_MEM0_PROVIDER_INSTANCE=phase-04-clean-harness-gate
export PIP_CACHE_DIR="$MODEL_CACHE/pip"
export HF_HOME="$MODEL_CACHE/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$MODEL_CACHE/huggingface"
export TORCH_HOME="$MODEL_CACHE/torch"
export MEM0_TELEMETRY=false
export TOKENIZERS_PARALLELISM=false

capture_harness_health() {
    label="$1"
    log="$RUN_ROOT/harness-${label}.log"
    if ! {
        "$HARNESS_PYTHON" --version
        "$HARNESS_PYTHON" -m pip --version
        "$HARNESS_PYTHON" -m pip show mem0ai protobuf openai sentence-transformers torch qdrant-client
        if "$HARNESS_PYTHON" -m pip show litellm >/dev/null 2>&1; then
            "$HARNESS_PYTHON" -m pip show litellm
        else
            printf '%s\n' 'litellm: NOT INSTALLED'
        fi
        "$HARNESS_PYTHON" -m pip check
    } > "$log" 2>&1; then
        printf 'Clean harness environment check failed (%s).\n' "$label" >&2
        tail -n 100 "$log" >&2
        exit 33
    fi
}

HARNESS_VENV_CREATED_BY_THIS_RUN=false
if [ ! -e "$CLEAN_HARNESS_VENV" ]; then
    python3 -m venv "$CLEAN_HARNESS_VENV"
    HARNESS_VENV_CREATED_BY_THIS_RUN=true
elif [ ! -d "$CLEAN_HARNESS_VENV" ] || [ ! -x "$HARNESS_PYTHON" ]; then
    printf '%s\n' 'Existing clean harness path is incomplete; refusing automatic rebuild.' >&2
    exit 34
fi

HARNESS_DRY_RUN_REPORT="$RUN_ROOT/harness-pip-dry-run.json"
HARNESS_DRY_RUN_LOG="$RUN_ROOT/harness-pip-dry-run.log"
if [ "$HARNESS_VENV_CREATED_BY_THIS_RUN" = true ]; then
    "$HARNESS_PYTHON" -m pip install --dry-run --report "$HARNESS_DRY_RUN_REPORT" \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r "$REPO/requirements/core.txt" \
        -r "$REPO/requirements/providers/mem0.txt" > "$HARNESS_DRY_RUN_LOG"
    HARNESS_DRY_RUN_SUMMARY="$("$HARNESS_PYTHON" - "$HARNESS_DRY_RUN_REPORT" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
packages = {
    item.get("metadata", {}).get("name", "").lower(): item.get("metadata", {}).get("version")
    for item in data.get("install", [])
}
wanted = ("mem0ai", "protobuf", "openai", "litellm", "sentence-transformers", "torch")
selected = {name: packages.get(name) for name in wanted}
flagged = sorted(name for name in packages if name.startswith("nvidia-") or name.startswith("cuda-"))
print(json.dumps({"selected": selected, "flagged": flagged}, separators=(",", ":")))
if flagged:
    raise SystemExit(9)
PY
)" || {
        printf '%s\n' 'Clean harness dry run would install CUDA/NVIDIA packages; refusing installation.' >&2
        exit 35
    }
    "$HARNESS_PYTHON" -m pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r "$REPO/requirements/core.txt" \
        -r "$REPO/requirements/providers/mem0.txt"
else
    HARNESS_DRY_RUN_SUMMARY='{"status":"REUSED_EXACT_FINGERPRINT"}'
fi

capture_harness_health before-hindsight
"$HARNESS_PYTHON" -c 'import importlib.metadata as m; assert m.version("mem0ai") == "2.2.1"; assert m.version("sentence-transformers") == "6.1.0"'
"$HARNESS_PYTHON" -c 'import torch; assert torch.version.cuda is None; assert not torch.cuda.is_available()'
if ! "$HARNESS_PYTHON" -m pip list --format=json | "$HARNESS_PYTHON" -c 'import json,sys; names=[p["name"] for p in json.load(sys.stdin) if p["name"].lower().startswith(("nvidia-","cuda-"))]; raise SystemExit(1 if names else 0)'; then
    printf '%s\n' 'CUDA/NVIDIA packages detected in clean harness; stopping Phase 04.' >&2
    exit 36
fi

HARNESS_FINGERPRINT_FILE="$RUN_ROOT/memlife-harness-environment-fingerprint.json"
HARNESS_FINGERPRINT_CANDIDATE="$RUN_ROOT/memlife-harness-environment-fingerprint.candidate.json"
"$HARNESS_PYTHON" "$REPO/scripts/jetstream/phase04_runtime.py" fingerprint \
    --kind harness --output "$HARNESS_FINGERPRINT_CANDIDATE"
if [ "$HARNESS_VENV_CREATED_BY_THIS_RUN" = true ]; then
    cp "$HARNESS_FINGERPRINT_CANDIDATE" "$HARNESS_FINGERPRINT"
elif [ ! -f "$HARNESS_FINGERPRINT" ] || ! cmp -s "$HARNESS_FINGERPRINT" "$HARNESS_FINGERPRINT_CANDIDATE"; then
    printf '%s\n' 'Existing clean harness fingerprint is absent or changed; refusing automatic rebuild.' >&2
    exit 37
fi
cp "$HARNESS_FINGERPRINT" "$HARNESS_FINGERPRINT_FILE"

cd "$REPO"
UNIT_LOG="$RUN_ROOT/unit-contract.log"
if ! "$HARNESS_PYTHON" -m pytest tests/unit tests/contract -q -p no:cacheprovider > "$UNIT_LOG" 2>&1; then
    tail -n 100 "$UNIT_LOG" >&2
    exit 40
fi

MEM0_REGRESSION_FILE="$RUN_ROOT/phase-02b-mem0-regression.json"
if ! "$HARNESS_PYTHON" scripts/jetstream/phase04_mem0_regression.py --output "$MEM0_REGRESSION_FILE"; then
    printf '%s\n' 'Phase 02B Mem0 regression failed; Hindsight setup is forbidden.' >&2
    exit 41
fi

# Hindsight setup begins only after the clean harness and Mem0 regression pass.
mkdir -p "$PROVIDER_ROOT" "$HINDSIGHT_MODEL_CACHE" "$PG0_ROOT"
PG0_LINK=/home/exouser/.pg0
if [ -L "$PG0_LINK" ]; then
    test "$(readlink -f "$PG0_LINK")" = "$(readlink -f "$PG0_ROOT")"
elif [ -e "$PG0_LINK" ]; then
    printf '%s\n' 'Existing /home/exouser/.pg0 is not the managed persistent-volume link.' >&2
    exit 42
else
    ln -s "$PG0_ROOT" "$PG0_LINK"
fi

export MEMLIFE_HINDSIGHT_BASE_URL=http://127.0.0.1:8888
export HF_HOME="$HINDSIGHT_MODEL_CACHE/huggingface"
export HUGGINGFACE_HUB_CACHE="$HINDSIGHT_MODEL_CACHE/huggingface/hub"
export TRANSFORMERS_CACHE="$HINDSIGHT_MODEL_CACHE/huggingface"
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

HINDSIGHT_VENV_CREATED_BY_THIS_RUN=false
if [ ! -e "$HINDSIGHT_VENV" ]; then
    python3 -m venv "$HINDSIGHT_VENV"
    HINDSIGHT_VENV_CREATED_BY_THIS_RUN=true
elif [ ! -d "$HINDSIGHT_VENV" ] || [ ! -x "$HINDSIGHT_PYTHON" ]; then
    printf '%s\n' 'Existing Hindsight venv path is incomplete; refusing automatic rebuild.' >&2
    exit 43
fi

HINDSIGHT_DRY_RUN_REPORT="$RUN_ROOT/hindsight-pip-dry-run.json"
HINDSIGHT_DRY_RUN_LOG="$RUN_ROOT/hindsight-pip-dry-run.log"
if [ "$HINDSIGHT_VENV_CREATED_BY_THIS_RUN" = true ]; then
    "$HINDSIGHT_PYTHON" -m pip install --dry-run --report "$HINDSIGHT_DRY_RUN_REPORT" -r "$REPO/requirements/providers/hindsight.txt" > "$HINDSIGHT_DRY_RUN_LOG"
    HINDSIGHT_DRY_RUN_SUMMARY="$("$HINDSIGHT_PYTHON" - "$HINDSIGHT_DRY_RUN_REPORT" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
names = sorted({item.get("metadata", {}).get("name", "") for item in data.get("install", [])})
flagged = [name for name in names if name.lower() == "torch" or name.lower().startswith(("nvidia-", "cuda-"))]
print(json.dumps({"package_count": len(names), "flagged": flagged}, separators=(",", ":")))
if flagged:
    raise SystemExit(9)
PY
)" || {
        printf '%s\n' 'Provider dry run would install Torch/CUDA/NVIDIA packages; refusing installation.' >&2
        exit 44
    }
    "$HINDSIGHT_PYTHON" -m pip install --no-cache-dir -r "$REPO/requirements/providers/hindsight.txt"
else
    HINDSIGHT_DRY_RUN_SUMMARY='{"status":"REUSED_VALIDATED_ISOLATED_VENV"}'
fi

PROVIDER_CHECK_LOG="$RUN_ROOT/hindsight-environment-check.log"
if ! {
    "$HINDSIGHT_PYTHON" --version
    "$HINDSIGHT_PYTHON" -m pip --version
    "$HINDSIGHT_PYTHON" -m pip show protobuf hindsight-api-slim
    "$HINDSIGHT_PYTHON" -m pip check
    "$HINDSIGHT_PYTHON" -c 'import importlib.metadata as m; assert m.version("hindsight-api-slim") == "0.10.1"'
    test -x "$HINDSIGHT_SERVICE"
} > "$PROVIDER_CHECK_LOG" 2>&1; then
    printf '%s\n' 'Existing Hindsight venv is incomplete or inconsistent; refusing automatic rebuild.' >&2
    tail -n 100 "$PROVIDER_CHECK_LOG" >&2
    exit 45
fi
if "$HINDSIGHT_PYTHON" -m pip show hindsight-client > /dev/null 2>&1; then
    printf '%s\n' 'Unneeded hindsight-client package found in service-only provider venv.' >&2
    exit 46
fi
if ! "$HINDSIGHT_PYTHON" -m pip list --format=json | "$HINDSIGHT_PYTHON" -c 'import json,sys; names=[p["name"] for p in json.load(sys.stdin) if p["name"].lower().startswith(("nvidia-","cuda-"))]; raise SystemExit(1 if names else 0)'; then
    printf '%s\n' 'CUDA/NVIDIA packages detected in provider venv; stopping Phase 04.' >&2
    exit 47
fi

HINDSIGHT_FINGERPRINT_FILE="$RUN_ROOT/hindsight-environment-fingerprint.json"
"$HINDSIGHT_PYTHON" "$REPO/scripts/jetstream/phase04_runtime.py" fingerprint --kind provider --output "$HINDSIGHT_FINGERPRINT_FILE"
capture_harness_health after-hindsight

export PHASE04_REPO="$REPO"
export PHASE04_HARNESS_PYTHON="$HARNESS_PYTHON"
export PHASE04_CLEAN_HARNESS_VENV="$CLEAN_HARNESS_VENV"
export PHASE04_LEGACY_HARNESS_VENV="$LEGACY_HARNESS_VENV"
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
export PHASE04_HARNESS_DRY_RUN_SUMMARY="$HARNESS_DRY_RUN_SUMMARY"
export PHASE04_HINDSIGHT_DRY_RUN_SUMMARY="$HINDSIGHT_DRY_RUN_SUMMARY"
export PHASE04_UNIT_SUMMARY="$(tail -n 1 "$UNIT_LOG")"
export PHASE04_HARNESS_FINGERPRINT="$HARNESS_FINGERPRINT_FILE"
export PHASE04_HINDSIGHT_FINGERPRINT="$HINDSIGHT_FINGERPRINT_FILE"
export PHASE04_MEM0_REGRESSION="$MEM0_REGRESSION_FILE"
export PHASE04_HARNESS_VENV_CREATED_BY_THIS_RUN
export PHASE04_HINDSIGHT_VENV_CREATED_BY_THIS_RUN
export PHASE04_HARNESS_PIP_CHECK_BEFORE=PASS
export PHASE04_HINDSIGHT_PIP_CHECK=PASS
export PHASE04_HARNESS_PIP_CHECK_AFTER=PASS

RESULT_FILE="$RUN_ROOT/phase-04-result.json"
"$HARNESS_PYTHON" scripts/jetstream/phase04_hindsight_validate.py --output "$RESULT_FILE"
cp "$RESULT_FILE" "$ARTIFACT_ROOT/phase-04-hindsight-result.json"
printf 'PHASE04_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT_FILE")"
