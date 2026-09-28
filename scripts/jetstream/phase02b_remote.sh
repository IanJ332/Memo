#!/usr/bin/env bash
set -euo pipefail

REPO=/home/exouser/Memo
PYTHON="$REPO/.venv/bin/python"
LIVE_VOLUME_MOUNT="$(findmnt -n -o TARGET /dev/sdb)"
LIVE_VOLUME_SOURCE="$(findmnt -n -o SOURCE /dev/sdb)"
LIVE_VOLUME_FSTYPE="$(findmnt -n -o FSTYPE /dev/sdb)"

test -n "$LIVE_VOLUME_MOUNT"
test -d "$LIVE_VOLUME_MOUNT"
MEMLIFE_DATA_ROOT="$LIVE_VOLUME_MOUNT/memlife"
PROVIDER_ROOT="$MEMLIFE_DATA_ROOT/providers/mem0/phase-02b"
MODEL_CACHE="$MEMLIFE_DATA_ROOT/model_cache"
RUN_ROOT="$MEMLIFE_DATA_ROOT/runs/phase-02b-mem0"
LOG_ROOT="$MEMLIFE_DATA_ROOT/logs"
ARTIFACT_ROOT="$MEMLIFE_DATA_ROOT/artifacts"
mkdir -p "$PROVIDER_ROOT/qdrant" "$PROVIDER_ROOT/history" "$PROVIDER_ROOT/scratch"
mkdir -p "$MODEL_CACHE/pip" "$MODEL_CACHE/huggingface" "$MODEL_CACHE/torch"
mkdir -p "$RUN_ROOT" "$LOG_ROOT" "$ARTIFACT_ROOT"

export MEMLIFE_DATA_ROOT
export MEMLIFE_MEM0_PROVIDER_INSTANCE=phase-02b
export PIP_CACHE_DIR="$MODEL_CACHE/pip"
export HF_HOME="$MODEL_CACHE/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$MODEL_CACHE/huggingface"
export TORCH_HOME="$MODEL_CACHE/torch"
export MEM0_TELEMETRY=false
export TOKENIZERS_PARALLELISM=false

ROOT_FREE_BEFORE="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_BEFORE="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
df -h /
df -h "$LIVE_VOLUME_MOUNT"
findmnt -n -o TARGET,SOURCE,FSTYPE /dev/sdb

"$PYTHON" --version
"$PYTHON" -m pip --version
"$PYTHON" -m pip check
"$PYTHON" -m pip install -r "$REPO/requirements/core.txt"

DRY_RUN_REPORT="$RUN_ROOT/pip-dry-run.json"
"$PYTHON" -m pip install --dry-run --report "$DRY_RUN_REPORT" -r "$REPO/requirements/providers/mem0.txt" > "$RUN_ROOT/pip-dry-run.log"
DRY_RUN_NVIDIA_PACKAGES="$("$PYTHON" -c 'import json,sys; data=json.load(open(sys.argv[1], encoding="utf-8")); print(",".join(sorted({item.get("metadata", {}).get("name", "") for item in data.get("install", []) if item.get("metadata", {}).get("name", "").lower().startswith("nvidia-")})))' "$DRY_RUN_REPORT")"

if "$PYTHON" -c 'import torch; assert torch.version.cuda is None' 2>/dev/null; then
    printf '%s\n' 'Existing CPU-only torch installation accepted.'
else
    "$PYTHON" -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.7.1+cpu'
fi

if "$PYTHON" -m pip list --format=json | "$PYTHON" -c 'import json,sys; names=[p["name"] for p in json.load(sys.stdin) if p["name"].lower().startswith("nvidia-")]; raise SystemExit(1 if names else 0)'; then
    true
else
    printf '%s\n' 'NVIDIA packages detected; refusing Phase 02B installation.' >&2
    exit 31
fi

"$PYTHON" -m pip install -r "$REPO/requirements/providers/mem0.txt"
"$PYTHON" -m pip show pytest mem0ai sentence-transformers qdrant-client torch
"$PYTHON" -m pip check
"$PYTHON" -c 'import torch; assert torch.version.cuda is None; assert not torch.cuda.is_available()'

"$PYTHON" -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L3-v2", cache_folder="'"$MODEL_CACHE/huggingface"'")'
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

cd "$REPO"
LOCAL_GATE_LOG="$RUN_ROOT/provider-independent-tests.log"
if ! "$PYTHON" -m pytest tests/unit tests/contract -q -p no:cacheprovider > "$LOCAL_GATE_LOG" 2>&1; then
    tail -n 100 "$LOCAL_GATE_LOG" >&2
    exit 41
fi
tail -n 5 "$LOCAL_GATE_LOG"

INTEGRATION_LOG="$RUN_ROOT/mem0-integration.log"
if ! "$PYTHON" -m pytest tests/integration/test_mem0_adapter.py -q -m mem0_integration -p no:cacheprovider > "$INTEGRATION_LOG" 2>&1; then
    tail -n 100 "$INTEGRATION_LOG" >&2
    exit 42
fi
tail -n 5 "$INTEGRATION_LOG"

ROOT_FREE_AFTER="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_AFTER="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
RESULT_FILE="$RUN_ROOT/phase-02b-result.json"
export PHASE02B_LIVE_VOLUME_MOUNT="$LIVE_VOLUME_MOUNT"
export PHASE02B_LIVE_VOLUME_SOURCE="$LIVE_VOLUME_SOURCE"
export PHASE02B_LIVE_VOLUME_FSTYPE="$LIVE_VOLUME_FSTYPE"
export PHASE02B_ROOT_FREE_BEFORE="$ROOT_FREE_BEFORE"
export PHASE02B_ROOT_FREE_AFTER="$ROOT_FREE_AFTER"
export PHASE02B_VOLUME_FREE_BEFORE="$VOLUME_FREE_BEFORE"
export PHASE02B_VOLUME_FREE_AFTER="$VOLUME_FREE_AFTER"
export PHASE02B_CONTRACT_SUMMARY="$(tail -n 1 "$LOCAL_GATE_LOG")"
export PHASE02B_INTEGRATION_SUMMARY="$(tail -n 1 "$INTEGRATION_LOG")"
export PHASE02B_DRY_RUN_NVIDIA_PACKAGES="$DRY_RUN_NVIDIA_PACKAGES"
"$PYTHON" scripts/jetstream/phase02b_mem0_validate.py --output "$RESULT_FILE"

cp "$RESULT_FILE" "$ARTIFACT_ROOT/phase-02b-mem0-jetstream.json"
printf 'PHASE02B_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT_FILE")"
