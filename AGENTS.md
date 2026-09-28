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
- **Storage Tiering**: Place source code and scripts under `/home/exouser/Memo`. Resolve the current `/dev/sdb` mountpoint with `findmnt -n -o TARGET /dev/sdb`, then direct datasets, model caches, logs, traces, and large experiment artifacts to `<mount>/memlife`. Never hardcode a historic mountpoint.
- **Prompt Declaration**: Every execution prompt should declare `CONVERSATION`, `MODEL`, `EXECUTION TARGET`, and `JETSTREAM ACTION`.
- **Lifecycle Default**: Treat Jetstream as `SHELVED` by default. Unshelve only for required remote execution and use `scripts/jetstream/jetstreamctl.py` after its validation.
- **Opened-By-Run Cleanup**: If automation opened the VM, shelve it after work. Never automatically shelve a VM that was already `ACTIVE` before the run.
- **Dynamic Networking**: Never cache or hardcode a numeric public IP. Resolve current networking from OpenStack for each lifecycle run.
- **Local Secrets**: Keep OpenStack credentials, SSH private keys, generated local state, and caches under ignored `.local/` paths and outside Git.
