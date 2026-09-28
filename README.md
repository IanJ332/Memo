# CS 598 SAO — Track 3 Project Environment

This repository hosts the development environment, tooling, and artifacts for the **CS 598 SAO Track 3** project across multiple platforms:
- Windows development workstation
- macOS development workstation
- Jetstream2 Linux VM (cloud experiment runtime)
- Clean Linux reproduction environments

**Current research direction:** MemLife-NLIP

**Current implementation status:** Phase 02A — local Mem0 OSS bring-up

- [Phase 01 — MemLife Bootstrap](docs/phases/PHASE_01_MEMLIFE_BOOTSTRAP.md)
- [Phase 02 — Provider Bring-up](docs/phases/PHASE_02_PROVIDER_BRINGUP.md)
- [Mem0 OSS 2.2.1 characterization](docs/providers/MEM0_2_2_1.md)

---

## Environment Isolation Philosophy

To guarantee reproducible, non-destructive workflows across heterogeneous machines:
- **Strict Virtual Environment Isolation**: All Python dependencies are installed strictly into a repository-local `.venv/`. No packages are ever installed into global or user Python environments.
- **Explicit Interpreter Execution**: Commands and automation scripts invoke the local virtual environment interpreter explicitly:
  - Linux/macOS: `.venv/bin/python`
  - Windows: `.venv\Scripts\python.exe`
- **Zero Secret Commits**: Passwords, API tokens, `.env` files, and private keys are never committed. Machine characterization reports (`runtime_reports/`) are gitignored.

---

## Repository Structure

```
Memo/
├── README.md                  # Project overview and quick start
├── .gitignore                 # Excludes .venv/, runtime_reports/, caches, and secrets
├── requirements.txt           # Includes deterministic common requirements
├── requirements/core.txt      # Pinned environment and Phase 01 dependencies
├── src/memlife/               # Provider-independent models, adapters, and utilities
├── tests/                     # Offline unit and reusable provider contract tests
├── configs/                   # Non-secret experiment configuration guidance
├── manifests/                 # Reproducibility manifest guidance
├── docs/
│   ├── JETSTREAM2_SETUP.md    # Jetstream2 VM provisioning, lifecycle, and setup guide
│   └── phases/                # Phase completion and handoff records
└── scripts/
    ├── setup/prepare_runtime.py # Idempotent runtime storage setup
    ├── bootstrap_env.sh       # POSIX bootstrap script for Linux, Jetstream2, macOS
    ├── bootstrap_env.ps1      # PowerShell bootstrap script for Windows
    ├── check_environment.sh   # Read-only Linux system inspection
    ├── system_probe.py        # Portable, read-only system and hardware probe
    ├── test_jetstream_llm.py  # Jetstream2 hosted LLM connectivity verification
    └── jetstream_baseline.sh  # Master baseline characterization runner on Jetstream2
```

---

## Quick Start

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_env.ps1
.venv\Scripts\python.exe scripts\system_probe.py
```

### macOS / Linux / Jetstream2
```bash
chmod +x scripts/*.sh
./scripts/bootstrap_env.sh
.venv/bin/python scripts/system_probe.py
```

---

## Jetstream2 Characterization & Workflow

For instructions on manual VM provisioning (`m3.small` flavor), Service Unit (SU) conservation (`Shelve` / `Unshelve`), and running baseline reports, refer to [docs/JETSTREAM2_SETUP.md](docs/JETSTREAM2_SETUP.md).

## Phase 01 Validation

Run the deterministic offline suite with the repository-local interpreter:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

```bash
.venv/bin/python -m pytest -q
```
