# Jetstream2 Setup & Environment Guide

This document covers VM creation guidelines, cross-platform local environment bootstrapping, and the baseline collection workflow for the CS 598 SAO Track 3 project.

---

## Jetstream2 VM Provisioning (Manual)

> [!IMPORTANT]
> VM provisioning and ACCESS credential creation remain manual. The narrow
> `scripts/jetstream/jetstreamctl.py` controller may manage only the already
> verified `jisheng3` instance lifecycle after local authentication is configured.

### Course VM Baseline Configuration
When launching your VM in Exosphere ([https://jetstream2.exosphere.app/](https://jetstream2.exosphere.app/)):

- **Instance Name**: Use your NetID (e.g., `netid`)
- **Flavor**: `m3.small` (course standard allocation)
- **Number of instances**: `1`
- **Root disk size**: Default
- **Web Desktop**: Optional (terminal / SSH access is sufficient)
- **SSH key**: Optional (recommended for direct terminal access)

---

## Resource Lifecycle & Service Unit (SU) Conservation

> [!CAUTION]
> **Closing the browser DOES NOT stop Service Unit (SU) consumption!**
> While the instance is in the `Active` state, it burns allocation credits continuously, even if idle.

### How to Stop Burning SUs
When you are done with a work session on Jetstream2:
1. Navigate to your instance in Exosphere.
2. Click **Instance → Actions → Shelve**.
3. **Shelved status**: The instance consumes **0 SUs** while shelved, and your disk contents/files are preserved.

### How to Resume
When you are ready to resume work:
1. Navigate to your instance in Exosphere.
2. Click **Instance → Actions → Unshelve**.
3. Wait for the VM status to return to `Active` before reconnecting.

---

## Environment Setup & Reproducibility

### Hard Rule: Isolated Virtual Environments (`.venv`)
All project work across all platforms (Windows, macOS, Linux/Jetstream2) must use a repository-local `.venv`:
- **Never** install project packages globally (`sudo pip`, `pip install --user`, or unvirtualized `pip`).
- **Never** copy `.venv` folders across different machines or operating systems.
- Automation scripts and instructions must use the explicit virtual environment Python interpreter:
  - Linux / macOS: `.venv/bin/python`
  - Windows: `.venv\Scripts\python.exe`

---

## First Use Instructions

### 1. Jetstream2 Linux VM
After creating and logging into your Jetstream2 VM:

```bash
git clone <PRIVATE_REPOSITORY_URL>
cd Memo

# Grant execution permissions to shell scripts
chmod +x scripts/*.sh

# Bootstrap the repository-local .venv and install requirements
./scripts/bootstrap_env.sh

# Run the portable system probe
.venv/bin/python scripts/system_probe.py

# Run the full baseline characterization and LLM connectivity test
./scripts/jetstream_baseline.sh
```

> [!NOTE]
> For interactive work, you may optionally activate the virtual environment with `source .venv/bin/activate`. However, all reproducible commands and automated scripts explicitly reference `.venv/bin/python` to prevent accidental contamination from system Python.

---

### 2. macOS Development Machine
Each machine must create its own isolated `.venv`:

```bash
git clone <PRIVATE_REPOSITORY_URL>
cd Memo

# Grant execution permissions to shell scripts
chmod +x scripts/*.sh

# Bootstrap the repository-local .venv
./scripts/bootstrap_env.sh

# Verify system probe inside .venv
.venv/bin/python scripts/system_probe.py
```

---

### 3. Windows Development Machine
Run the non-invasive PowerShell bootstrap script:

```powershell
git clone <PRIVATE_REPOSITORY_URL>
cd Memo

# Bootstrap using a temporary execution policy bypass (does NOT modify system settings)
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_env.ps1

# Verify system probe inside .venv
.venv\Scripts\python.exe scripts\system_probe.py
```

> [!TIP]
> Do not permanently alter your Windows PowerShell execution policy. The `-ExecutionPolicy Bypass` flag is the least-invasive way to run the bootstrap script safely without modifying global system state.

---

## Returning to an Existing Environment

When returning to an already bootstrapped environment after pulling changes:

### Linux / macOS:
```bash
git pull
.venv/bin/python -m pip install -r requirements.txt
```
*(Optional interactive activation: `source .venv/bin/activate`)*

### Windows:
```powershell
git pull
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Jetstream2 LLM Service Connectivity

The course provides access to a hosted model service on Jetstream2:
- **Base URL**: `https://llm.jetstream-cloud.org/llama-4-scout/v1/`
- **Model**: `llama-4-scout`
- **API Key**: `empty` (standard course mock key; not a private secret)

To test connectivity at any time:
- Linux / macOS: `.venv/bin/python scripts/test_jetstream_llm.py`
- Windows: `.venv\Scripts\python.exe scripts\test_jetstream_llm.py`
