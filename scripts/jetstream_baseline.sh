#!/usr/bin/env bash
set -uo pipefail

# scripts/jetstream_baseline.sh
# Jetstream2 VM baseline environment characterization and LLM connectivity collector.
# Intended to be run after bootstrap_env.sh on the Jetstream2 VM.
# Does NOT modify system packages or store credentials.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"

if [ ! -x "${VENV_PYTHON}" ]; then
    echo "ERROR: Virtual environment interpreter not found at ${VENV_PYTHON}." >&2
    echo "Please run './scripts/bootstrap_env.sh' first to prepare the environment." >&2
    exit 1
fi

REPORTS_DIR="${REPO_ROOT}/runtime_reports"
mkdir -p "${REPORTS_DIR}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="${REPORTS_DIR}/jetstream_baseline_${TIMESTAMP}.txt"

echo "Collecting Jetstream2 baseline report to: ${REPORT_FILE}"

run_collector() {
    echo "================================================================================"
    echo "                      JETSTREAM2 SYSTEM BASELINE REPORT                         "
    echo "================================================================================"
    echo "Report generated at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "Host: $(hostname 2>/dev/null || echo 'unknown')"
    echo "Repository Root: ${REPO_ROOT}"
    echo "================================================================================"
    echo ""

    echo ">>> STEP 1: Linux & OS Environment Diagnostics"
    echo "--------------------------------------------------------------------------------"
    if [ -x "${SCRIPT_DIR}/check_environment.sh" ]; then
        bash "${SCRIPT_DIR}/check_environment.sh" || echo "WARNING: check_environment.sh exited with non-zero status"
    else
        echo "WARNING: scripts/check_environment.sh not found or not executable"
    fi
    echo ""

    echo ">>> STEP 2: Portable Python System Probe (inside .venv)"
    echo "--------------------------------------------------------------------------------"
    "${VENV_PYTHON}" "${SCRIPT_DIR}/system_probe.py" || echo "WARNING: system_probe.py exited with non-zero status"
    echo ""

    echo ">>> STEP 3: Jetstream2 Hosted LLM Connectivity Test"
    echo "--------------------------------------------------------------------------------"
    "${VENV_PYTHON}" "${SCRIPT_DIR}/test_jetstream_llm.py" || echo "WARNING: test_jetstream_llm.py reported failure"
    echo ""

    echo "================================================================================"
    echo "                      BASELINE DATA COLLECTION COMPLETE                         "
    echo "================================================================================"
    echo "Report file saved at: ${REPORT_FILE}"
}

# Run and output both to stdout and the report file
run_collector 2>&1 | tee "${REPORT_FILE}"

echo ""
echo "Baseline run finished."
echo "Baseline report path: ${REPORT_FILE}"
