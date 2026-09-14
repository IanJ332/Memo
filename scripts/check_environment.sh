#!/usr/bin/env bash
set -euo pipefail

# scripts/check_environment.sh
# Read-only diagnostic script for Linux / Jetstream2 environment characterization.
# Does NOT modify any system state, files, or packages.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=================================================="
echo "      LINUX / JETSTREAM2 ENVIRONMENT CHECK        "
echo "=================================================="

echo ""
echo "--- Host and Kernel ---"
echo "Hostname:     $(hostname 2>/dev/null || echo 'N/A')"
echo "Kernel:       $(uname -a 2>/dev/null || echo 'N/A')"
echo "Architecture: $(uname -m 2>/dev/null || echo 'N/A')"
echo "Uptime:       $(uptime 2>/dev/null || echo 'N/A')"

echo ""
echo "--- Operating System Release ---"
if [ -f /etc/os-release ]; then
    cat /etc/os-release
else
    echo "/etc/os-release not found"
fi

echo ""
echo "--- CPU Details ---"
if command -v nproc >/dev/null 2>&1; then
    echo "nproc: $(nproc)"
fi
if command -v lscpu >/dev/null 2>&1; then
    lscpu 2>/dev/null | grep -E "(Architecture|CPU\(s\)|Model name|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|Hypervisor|Virtualization type)" || lscpu
else
    echo "lscpu not available"
fi

echo ""
echo "--- Memory (free -h) ---"
if command -v free >/dev/null 2>&1; then
    free -h 2>/dev/null || free
else
    echo "free command not available"
fi

echo ""
echo "--- Repository Filesystem Storage (df -h) ---"
df -h "${REPO_ROOT}" 2>/dev/null || echo "df command failed"

echo ""
echo "--- Block Devices (lsblk) ---"
if command -v lsblk >/dev/null 2>&1; then
    lsblk 2>/dev/null || echo "lsblk failed"
else
    echo "lsblk not available"
fi

echo ""
echo "--- Python Runtime Environment ---"
if command -v python3 >/dev/null 2>&1; then
    echo "System python3 path:    $(command -v python3)"
    echo "System python3 version: $(python3 --version 2>&1)"
else
    echo "python3: absent"
fi

if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    echo "Repository .venv python: ${REPO_ROOT}/.venv/bin/python"
    echo "Repository .venv version: $("${REPO_ROOT}/.venv/bin/python" --version 2>&1)"
else
    echo "Repository .venv: not initialized"
fi

echo ""
echo "--- Git Repository Status ---"
if command -v git >/dev/null 2>&1; then
    echo "Git version: $(git --version 2>&1)"
    if [ -d "${REPO_ROOT}/.git" ]; then
        cd "${REPO_ROOT}"
        echo "Git branch:  $(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
        echo "Git commit:  $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
    fi
else
    echo "Git: absent"
fi

echo ""
echo "--- Development Tools Inventory ---"
for tool in nvidia-smi curl wget gcc make docker podman; do
    if command -v "$tool" >/dev/null 2>&1; then
        tool_path="$(command -v "$tool")"
        echo "  - ${tool}: present (${tool_path})"
    else
        echo "  - ${tool}: absent"
    fi
done

echo ""
echo "=================================================="
echo "          ENVIRONMENT CHECK COMPLETE              "
echo "=================================================="
