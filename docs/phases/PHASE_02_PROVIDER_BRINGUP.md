# Phase 02 — Provider Bring-up

> **PHASE 02 HAS NOT STARTED.**

This document is a handoff plan only. Phase 01 installs and configures no memory
provider.

## Objective

Introduce the first real memory provider behind the provider-independent adapter
contract while preserving its native capability and lifecycle differences.

## First Target: Mem0

The planned validation sequence is:

```text
Mem0 adapter
    ↓
reset
    ↓
write
    ↓
query
    ↓
update / supersede
    ↓
query
    ↓
delete
    ↓
query
```

Before installation, select and pin an exact Mem0 package version, document its
runtime prerequisites, and create a non-secret provider configuration. The
adapter must explicitly declare unsupported operations; it must not synthesize
provider behavior merely to satisfy a test.

## Planned Work

1. Add a pinned Mem0 dependency in a provider-specific requirements file.
2. Implement a Mem0 adapter using Phase 01 commands and normalized records.
3. Record observed native capabilities and lifecycle semantics.
4. Apply the reusable provider contract/smoke workflow in an isolated namespace.
5. Capture a manifest containing the exact installed version, Git commit,
   platform, data-root mode, and non-secret configuration hash.
6. Document provider setup, cleanup, limitations, and reproducible commands.

## Exit Criterion

Phase 02 completes only when the real Mem0 adapter passes the reusable provider
contract/smoke workflow and its exact installed version and configuration are
captured in reproducibility records. Any unsupported capability must remain
explicit and must be reflected in the test outcome and documentation.

## Later Extension Points

After Mem0 is complete and reviewed, separate adapters may be evaluated for:

- Hindsight
- RetainDB
- OpenViking
- Honcho

These providers are not installed, configured, or started by Phase 01. Each must
receive its own version pin, capability declaration, storage isolation, manifest,
and contract results when its work is explicitly authorized.

## Out of Scope Until Authorized

- Memory Authority Gateway enforcement
- OAuth or identity-provider integration
- Attack campaigns
- Provider Docker services
- Provider comparisons or benchmarks
- Additional providers beyond the approved Phase 02 target
