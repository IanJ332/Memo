#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'CONVERSATION: explicit future Phase 06B supplement authorization required'
printf '%s\n' 'MODEL: declared by authorizing prompt'
printf '%s\n' 'EXECUTION TARGET: JETSTREAM2 supplement lifecycle'
printf '%s\n' 'JETSTREAM ACTION: managed lifecycle, only after explicit authorization'

test "${MEMLIFE_AUTHORIZE_PHASE06B_SUPPLEMENT_LIVE:-}" = YES
: "${PHASE06B_EXPECTED_COMMIT:?exact prepared commit is required}"
: "${PHASE06B_SUPPLEMENT_ATTEMPT_ID:?unique supplement attempt ID is required}"
case "$PHASE06B_SUPPLEMENT_ATTEMPT_ID" in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) printf '%s\n' 'invalid supplement attempt ID' >&2; exit 43 ;;
esac
test "$PHASE06B_SUPPLEMENT_ATTEMPT_ID" != 20261001T183940Z-1fc4c4929532

REPO=/home/exouser/Memo
LEGACY_VENV="$REPO/.venv"
LIVE_VOLUME_MOUNT="$(findmnt -n -o TARGET /dev/sdb)"
LIVE_VOLUME_SOURCE="$(findmnt -n -o SOURCE /dev/sdb)"
test -n "$LIVE_VOLUME_MOUNT"
test -d "$LIVE_VOLUME_MOUNT"
test "$LIVE_VOLUME_SOURCE" = /dev/sdb

MEMLIFE_DATA_ROOT="$LIVE_VOLUME_MOUNT/memlife"
HARNESS_SELECTION_ARGS=(--repo "$REPO" --data-root "$MEMLIFE_DATA_ROOT")
if [ -n "${PHASE06B_HARNESS_VENV:-}" ]; then
    HARNESS_SELECTION_SOURCE=explicit
    HARNESS_SELECTION_ARGS+=(--explicit-venv "$PHASE06B_HARNESS_VENV")
else
    HARNESS_SELECTION_SOURCE=persistent-default
fi
HARNESS_VENV="$(python3 "$REPO/scripts/jetstream/phase06b_harness.py" "${HARNESS_SELECTION_ARGS[@]}")"
HARNESS_PYTHON="$HARNESS_VENV/bin/python"
OPENVIKING_VENV="$MEMLIFE_DATA_ROOT/venvs/openviking-0.4.22"
OPENVIKING_PYTHON="$OPENVIKING_VENV/bin/python"
OPENVIKING_SERVICE="$OPENVIKING_VENV/bin/openviking-server"
OPENVIKING_STATE="$MEMLIFE_DATA_ROOT/providers/openviking"
OPENVIKING_CONFIG="$OPENVIKING_STATE/ov.conf"
OPENVIKING_CACHE="$MEMLIFE_DATA_ROOT/model_cache/openviking"
RUN_PARENT="$MEMLIFE_DATA_ROOT/runs/phase06b/supplements/attempts"
RUN_ROOT="$RUN_PARENT/$PHASE06B_SUPPLEMENT_ATTEMPT_ID"
RESULT="$RUN_ROOT/supplement-result.json"

test "$HARNESS_VENV" != "$LEGACY_VENV"
test -x "$HARNESS_PYTHON"
test -x "$OPENVIKING_PYTHON"
test -x "$OPENVIKING_SERVICE"
test -f "$OPENVIKING_CONFIG"
ROOT_FREE_BEFORE="$(df -B1 --output=avail / | tail -n 1 | xargs)"
VOLUME_FREE_BEFORE="$(df -B1 --output=avail "$LIVE_VOLUME_MOUNT" | tail -n 1 | xargs)"
test "$ROOT_FREE_BEFORE" -ge 1073741824
test "$VOLUME_FREE_BEFORE" -ge 8589934592
mkdir -p "$RUN_PARENT"
mkdir "$RUN_ROOT"
mkdir "$RUN_ROOT/openviking"

LIVE_CONFIG="$REPO/.local/phase05_openviking.env"
test -f "$LIVE_CONFIG"
case "$(stat -c %a "$LIVE_CONFIG")" in
    400|600) ;;
    *) printf '%s\n' 'protected OpenViking config must have mode 400 or 600' >&2; exit 42 ;;
esac
set -a
. "$LIVE_CONFIG"
set +a

export MEMLIFE_AUTHORIZE_PHASE06B_SUPPLEMENT_LIVE=YES
export PHASE06B_EXPECTED_COMMIT
export MEMLIFE_DATA_ROOT
export PHASE06B_HARNESS_VENV="$HARNESS_VENV"
export PHASE06B_HARNESS_SELECTION_SOURCE="$HARNESS_SELECTION_SOURCE"
export PHASE06B_LIVE_VOLUME_MOUNT="$LIVE_VOLUME_MOUNT"
export PHASE06B_SUPPLEMENT_RUN_ROOT="$RUN_ROOT"
export PHASE06B_OPENVIKING_PYTHON="$OPENVIKING_PYTHON"
export PIP_CACHE_DIR="$MEMLIFE_DATA_ROOT/model_cache/pip"
export HF_HOME="$MEMLIFE_DATA_ROOT/model_cache/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$MEMLIFE_DATA_ROOT/model_cache/huggingface"
export TORCH_HOME="$MEMLIFE_DATA_ROOT/model_cache/torch"
export TOKENIZERS_PARALLELISM=false
export MEMLIFE_OPENVIKING_BASE_URL=http://127.0.0.1:1933
export PHASE05_OPENVIKING_SERVICE="$OPENVIKING_SERVICE"
export PHASE05_OPENVIKING_CONFIG="$OPENVIKING_CONFIG"
export PHASE05_PROVIDER_STATE="$OPENVIKING_STATE"
export PHASE05_MODEL_CACHE="$OPENVIKING_CACHE"
export PHASE05_RUN_ROOT="$RUN_ROOT/openviking"

cd "$REPO"
"$HARNESS_PYTHON" scripts/jetstream/phase06b_supplement_remote.py \
    --output-dir "$RUN_ROOT" \
    --result "$RESULT"
test -s "$RESULT"
printf 'PHASE06B_SUPPLEMENT_RESULT_B64=%s\n' "$(base64 -w0 "$RESULT")"
