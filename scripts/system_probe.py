#!/usr/bin/env python3
"""scripts/system_probe.py

Portable, read-only system and environment characterization probe.
Uses Python standard library and psutil. Does NOT modify the system.
"""

import getpass
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys

# Rule: Windows UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import psutil
except ImportError:
    print("ERROR: 'psutil' is required by system_probe.py but is not installed.", file=sys.stderr)
    print("Run './scripts/bootstrap_env.sh' or 'powershell scripts/bootstrap_env.ps1' to set up .venv.", file=sys.stderr)
    sys.exit(1)


def format_bytes(n_bytes: int) -> str:
    """Format bytes to human-readable GiB/MiB."""
    gib = n_bytes / (1024 ** 3)
    if gib >= 1.0:
        return f"{gib:.2f} GiB ({n_bytes:,} bytes)"
    mib = n_bytes / (1024 ** 2)
    return f"{mib:.2f} MiB ({n_bytes:,} bytes)"


def sanitize_url(url: str) -> str:
    """Sanitize URL to strip sensitive tokens/passwords."""
    # Matches http://user:pass@host or https://token@host
    return re.sub(r"://([^@/:]+)(?::[^@]*)?@", r"://<sanitized-credentials>@", url)


def get_repo_root() -> Path:
    """Resolve repository root relative to this script."""
    return Path(__file__).resolve().parent.parent


def probe_git(repo_root: Path) -> dict:
    """Safely gather Git information without exposing credentials."""
    info = {
        "available": False,
        "version": "N/A",
        "branch": "N/A",
        "commit": "N/A",
        "dirty": "N/A",
        "remotes": [],
    }

    git_bin = shutil.which("git")
    if not git_bin:
        return info

    try:
        ver_res = subprocess.run(
            [git_bin, "--version"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if ver_res.returncode == 0:
            info["available"] = True
            info["version"] = ver_res.stdout.strip()
    except Exception:
        return info

    if not info["available"]:
        return info

    # Branch
    try:
        branch_res = subprocess.run(
            [git_bin, "branch", "--show-current"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_res.returncode == 0 and branch_res.stdout.strip():
            info["branch"] = branch_res.stdout.strip()
        else:
            # Fallback for detached HEAD
            ref_res = subprocess.run(
                [git_bin, "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if ref_res.returncode == 0:
                info["branch"] = ref_res.stdout.strip()
    except Exception:
        pass

    # Commit
    try:
        rev_res = subprocess.run(
            [git_bin, "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if rev_res.returncode == 0:
            info["commit"] = rev_res.stdout.strip()
    except Exception:
        pass

    # Dirty status
    try:
        status_res = subprocess.run(
            [git_bin, "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if status_res.returncode == 0:
            info["dirty"] = "DIRTY" if status_res.stdout.strip() else "CLEAN"
    except Exception:
        pass

    # Remotes (sanitized)
    try:
        remote_res = subprocess.run(
            [git_bin, "remote", "-v"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if remote_res.returncode == 0:
            lines = remote_res.stdout.strip().splitlines()
            seen = set()
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    name, raw_url = parts[0], parts[1]
                    clean_url = sanitize_url(raw_url)
                    entry = f"{name} ({clean_url})"
                    if entry not in seen:
                        seen.add(entry)
                        info["remotes"].append(entry)
    except Exception:
        pass

    return info


def probe_gpu() -> dict:
    """Safely detect NVIDIA GPU via nvidia-smi without modifying anything."""
    info = {
        "detected": False,
        "details": "NVIDIA GPU: not detected",
        "model": "N/A",
        "count": 0,
        "vram": "N/A",
        "driver_version": "N/A",
        "cuda_version": "N/A",
    }

    smi_bin = shutil.which("nvidia-smi")
    if not smi_bin:
        return info

    try:
        res = subprocess.run(
            [
                smi_bin,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().splitlines()
            info["detected"] = True
            info["count"] = len(lines)
            models = []
            vrams = []
            drivers = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    models.append(parts[0])
                    vrams.append(parts[1])
                    drivers.append(parts[2])
            info["model"] = ", ".join(models) if models else "N/A"
            info["vram"] = ", ".join(vrams) if vrams else "N/A"
            info["driver_version"] = drivers[0] if drivers else "N/A"

            # Check cuda version from full nvidia-smi text
            full_res = subprocess.run(
                [smi_bin],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if full_res.returncode == 0:
                cuda_match = re.search(r"CUDA\s+(?:UMD\s+)?Version:\s*([0-9.]+)", full_res.stdout, re.IGNORECASE)
                if cuda_match:
                    info["cuda_version"] = cuda_match.group(1)

            info["details"] = (
                f"Count: {info['count']}, Model: {info['model']}, "
                f"VRAM: {info['vram']}, Driver: {info['driver_version']}, "
                f"CUDA: {info['cuda_version']}"
            )
    except Exception as err:
        info["details"] = f"nvidia-smi check failed: {err}"

    return info


def probe_virtualization() -> str:
    """Safely detect VM / container hints on Linux without privileged actions."""
    if platform.system() != "Linux":
        return f"{platform.system()} host (Linux virtualization checks skipped)"

    hints = []

    # 1. systemd-detect-virt
    virt_bin = shutil.which("systemd-detect-virt")
    if virt_bin:
        try:
            res = subprocess.run([virt_bin], capture_output=True, text=True, timeout=3)
            out = res.stdout.strip()
            if out and out != "none":
                return f"VM ({out})"
        except Exception:
            pass

    # 2. Container environment files
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return "container"

    # 3. /proc/1/cgroup inspection
    try:
        if os.path.exists("/proc/1/cgroup"):
            with open("/proc/1/cgroup", "r", encoding="utf-8", errors="ignore") as f:
                cgroup_data = f.read()
                if "docker" in cgroup_data or "kubepods" in cgroup_data or "containerd" in cgroup_data or "lxc" in cgroup_data:
                    return "container"
    except Exception:
        pass

    # 4. DMI / Sysfs inspection (OpenStack / KVM / QEMU / VMware)
    for dmi_path in [
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/sys_vendor",
        "/sys/class/dmi/id/product_version",
    ]:
        try:
            if os.path.exists(dmi_path):
                with open(dmi_path, "r", encoding="utf-8", errors="ignore") as f:
                    val = f.read().strip()
                    lower_val = val.lower()
                    if any(vm_word in lower_val for vm_word in ["openstack", "kvm", "qemu", "bochs", "vmware", "virtualbox"]):
                        return f"VM ({val})"
        except Exception:
            pass

    # 5. /proc/cpuinfo hypervisor flag
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                if "hypervisor" in f.read():
                    return "VM (hypervisor flag present in /proc/cpuinfo)"
    except Exception:
        pass

    return "bare-metal-like (or unknown VM without standard signatures)"


def probe_network() -> dict:
    """Non-secret operational network baseline."""
    res = {
        "hostname_resolution": "NO",
        "outbound_dns": "NO",
    }

    # Hostname resolution
    try:
        h = socket.gethostname()
        socket.gethostbyname(h)
        res["hostname_resolution"] = "YES"
    except Exception:
        res["hostname_resolution"] = "NO"

    # Outbound DNS
    for target in ["jetstream-cloud.org", "github.com", "dns.google"]:
        try:
            socket.gethostbyname(target)
            res["outbound_dns"] = "YES"
            break
        except Exception:
            continue

    return res


def main():
    repo_root = get_repo_root()
    venv_dir = (repo_root / ".venv").resolve()

    # Venv verification
    sys_prefix = Path(sys.prefix).resolve()
    sys_exec = Path(sys.executable).resolve()
    is_inside_repo_venv = (sys_prefix == venv_dir) or (venv_dir in sys_exec.parents)

    # CPU metrics
    phys_cores = psutil.cpu_count(logical=False)
    logical_cpus = psutil.cpu_count(logical=True)
    cpu_util = psutil.cpu_percent(interval=0.5)
    cpu_freq = psutil.cpu_freq()

    # Memory metrics
    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk metrics (repository filesystem)
    disk = psutil.disk_usage(str(repo_root))

    # Git metrics
    git_info = probe_git(repo_root)

    # GPU
    gpu_info = probe_gpu()

    # Virtualization
    virt_info = probe_virtualization()

    # Network
    net_info = probe_network()

    print("==================================================")
    print("           PORTABLE SYSTEM PROBE REPORT           ")
    print("==================================================")

    print("\n--- Platform ---")
    print(f"OS:                   {platform.system()}")
    print(f"OS Version:           {platform.version()}")
    print(f"Platform:             {platform.platform()}")
    print(f"Kernel / Release:     {platform.release()}")
    print(f"Architecture:         {platform.machine()} ({platform.architecture()[0]})")
    print(f"Machine Type:         {platform.uname().machine}")
    print(f"Hostname:             {platform.node()}")
    print(f"Processor:            {platform.processor() or 'N/A'}")
    print(f"Python Version:       {platform.python_version()} ({sys.version.split()[0]})")
    print(f"Python Executable:    {sys.executable}")

    print("\n--- Runtime & Environment Isolation ---")
    try:
        curr_user = getpass.getuser()
    except Exception:
        curr_user = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    print(f"Current User:         {curr_user}")
    print(f"Working Directory:    {os.getcwd()}")
    print(f"Repository Root:      {repo_root}")
    print(f"VIRTUAL_ENV Env Var:  {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    print(f"sys.prefix:           {sys.prefix}")
    print(f"Running inside repository .venv: {'YES' if is_inside_repo_venv else 'NO'}")

    print("\n--- CPU ---")
    print(f"Physical CPU Cores:   {phys_cores if phys_cores is not None else 'N/A'}")
    print(f"Logical vCPUs:        {logical_cpus if logical_cpus is not None else 'N/A'}")
    print(f"Current CPU Usage:    {cpu_util:.1f}%")
    if cpu_freq:
        print(f"CPU Frequency:        current={cpu_freq.current:.1f}MHz, min={cpu_freq.min:.1f}MHz, max={cpu_freq.max:.1f}MHz")
    else:
        print("CPU Frequency:        N/A")

    print("\n--- Memory ---")
    print(f"Total RAM:            {format_bytes(vmem.total)}")
    print(f"Available RAM:        {format_bytes(vmem.available)}")
    print(f"Used RAM:             {format_bytes(vmem.used)}")
    print(f"Memory Utilization:   {vmem.percent:.1f}%")
    print(f"Total Swap:           {format_bytes(swap.total)}")
    print(f"Used Swap:            {format_bytes(swap.used)} ({swap.percent:.1f}%)")

    print("\n--- Disk (Repository Filesystem) ---")
    print(f"Mount / Path:         {repo_root}")
    print(f"Total Storage:        {format_bytes(disk.total)}")
    print(f"Used Storage:         {format_bytes(disk.used)}")
    print(f"Free Storage:         {format_bytes(disk.free)}")
    print(f"Filesystem Usage:     {disk.percent:.1f}%")

    print("\n--- Git ---")
    print(f"Git Available:        {'YES' if git_info['available'] else 'NO'}")
    print(f"Git Version:          {git_info['version']}")
    print(f"Current Branch:       {git_info['branch']}")
    print(f"Current Commit:       {git_info['commit']}")
    print(f"Working Tree Status:  {git_info['dirty']}")
    print("Sanitized Remotes:")
    if git_info["remotes"]:
        for r in git_info["remotes"]:
            print(f"  - {r}")
    else:
        print("  - None")

    print("\n--- GPU ---")
    print(f"NVIDIA GPU Detected:  {'YES' if gpu_info['detected'] else 'NO'}")
    if gpu_info["detected"]:
        print(f"GPU Model:            {gpu_info['model']}")
        print(f"GPU Count:            {gpu_info['count']}")
        print(f"Total VRAM:           {gpu_info['vram']}")
        print(f"Driver Version:       {gpu_info['driver_version']}")
        print(f"CUDA Version:         {gpu_info['cuda_version']}")
    else:
        print("Details:              NVIDIA GPU: not detected")

    print("\n--- Virtualization / Container ---")
    print(f"Classification:       {virt_info}")

    print("\n--- Network Baseline ---")
    print(f"Hostname Resolution:  {net_info['hostname_resolution']}")
    print(f"Outbound DNS:         {net_info['outbound_dns']}")

    print("\n==================================================")
    print("              PROBE COMPLETE                      ")
    print("==================================================")


if __name__ == "__main__":
    main()
