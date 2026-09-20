# Agent Operating Guidelines — Memo (CS 598 SAO Track 3)

This document outlines repository conventions and environment guidelines for AI agents working in this codebase.

## Repository Conventions & Environment Isolation

1. **Virtual Environment Isolation**: All Python dependencies are strictly installed in `.venv/`. Never install dependencies into the global or user Python environment (`sudo pip`, `pip install --user`).
2. **Explicit Interpreter Invocation**: Always invoke commands using the virtual environment interpreter:
   - Linux / Jetstream2 / macOS: `.venv/bin/python` and `.venv/bin/python -m pip`
   - Windows: `.venv\Scripts\python.exe` and `.venv\Scripts\python.exe -m pip`
3. **Secret & Credential Safety**: Never commit passwords, API keys, tokens, or SSH private keys.
4. **Git Hygiene**: Always run `git status` before modifying files. Never force-push (`git push --force`).

## Local Jetstream2 Context

Before performing Jetstream2 or remote-environment work, check for:

`.local/jetstream_context.md`

If present, treat it as the authoritative machine-local infrastructure context and avoid repeating full hardware/environment discovery unless the infrastructure may have changed.

This file is intentionally local and gitignored.

## Remote Environment Rules (Jetstream2)

- **Do Not Re-Probe Unchanged Infrastructure**: Do not run broad hardware/disk audits (`lscpu`, `free -h`, `lsblk`, `du -xhd1 /`, `docker system df`) unless infrastructure changes are suspected. Use targeted checks (e.g., `findmnt /dev/sdb`).
- **Preserve Exosphere Containers**: Never execute `docker system prune`, `docker image prune`, or stop Exosphere-managed Guacamole containers.
- **Storage Tiering**: Place source code and scripts under `/home/exouser/Memo`. Direct datasets, model caches, logs, traces, and large experiment artifacts to the persistent volume at `/media/volume/sdb`.
