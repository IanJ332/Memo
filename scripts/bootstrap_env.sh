#!/usr/bin/env bash
set -euo pipefail

# Determine repository root relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=== Bootstrapping Local Python Environment ==="
echo "Repository root: ${REPO_ROOT}"

# Verify python3 exists
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 command not found on PATH." >&2
    echo "Please install Python 3 using your operating system's standard package manager." >&2
    exit 1
fi

SYSTEM_PYTHON="$(command -v python3)"
echo "Detected system Python: ${SYSTEM_PYTHON}"
echo "System Python version: $("${SYSTEM_PYTHON}" --version 2>&1)"

# Check and create .venv
VENV_DIR="${REPO_ROOT}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"

if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating repository-local virtual environment at: ${VENV_DIR}"
    if ! "${SYSTEM_PYTHON}" -m venv "${VENV_DIR}" 2>/dev/null; then
        echo "" >&2
        echo "ERROR: Failed to create virtual environment with '${SYSTEM_PYTHON} -m venv ${VENV_DIR}'." >&2
        echo "On Debian/Ubuntu systems, the venv module is often split into a separate package." >&2
        echo "You may need to manually install it (for example: sudo apt update && sudo apt install -y python3-venv)." >&2
        echo "This script does NOT automatically modify system packages." >&2
        exit 1
    fi
else
    echo "Existing virtual environment found at: ${VENV_DIR}"
fi

if [ ! -x "${VENV_PYTHON}" ]; then
    echo "ERROR: Virtual environment interpreter not found at ${VENV_PYTHON}." >&2
    exit 1
fi

echo "Using virtual environment interpreter: ${VENV_PYTHON}"
echo "Virtual environment Python version: $("${VENV_PYTHON}" --version 2>&1)"

echo "Upgrading pip inside .venv..."
"${VENV_PYTHON}" -m pip install --upgrade pip

if [ -f "${REPO_ROOT}/requirements.txt" ]; then
    echo "Installing requirements inside .venv from ${REPO_ROOT}/requirements.txt..."
    "${VENV_PYTHON}" -m pip install -r "${REPO_ROOT}/requirements.txt"
else
    echo "WARNING: requirements.txt not found at ${REPO_ROOT}/requirements.txt"
fi

echo ""
echo "Environment ready."
echo "Python: ${VENV_PYTHON}"
echo "Next command: ${VENV_PYTHON} scripts/system_probe.py"
