# Agent onboarding

1. Verify repository root, branch, HEAD and worktree status.
2. Read root `AGENTS.md`, then `MODEL_HANDOFF.md`.
3. Read `PROJECT_STATE.md` and the relevant current experiment report as needed.
4. For remote work, consult `JETSTREAM2_RUNTIME_BASELINE.md` and ignored local
   runtime context; confirm exact owner and platform scope before real operations.
5. Make targeted source-first changes and run focused tests. Preserve evidence.
6. Return a self-contained Cloud Reviewer Handoff.

Codex reads root `AGENTS.md`; Gemini CLI reads `GEMINI.md`, which imports the
same policy and this onboarding guide. Use `/memory show` in Gemini CLI to verify
what was actually loaded; file presence alone is insufficient. A generic coding
agent should read these files directly.

Switching the coding assistant does not change an experiment. Changing the
scientific model/provider requires a new registered identity, request/response
qualification, separate evidence and fresh authorization. Do not automatically
change Qwen or the registered endpoint.
