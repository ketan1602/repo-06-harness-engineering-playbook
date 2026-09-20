# Harness Changelog

## [1.0.0] — 2026-09-20

Initial stable release. All names in `specification/harness-spec-v1.0.md` are locked.

### Added
- `AgentHarness` — core wrapper class
- `LifecycleManager` — state machine (INITIALISING → READY → RUNNING → COMPLETED/FAILED)
- `RetryPolicy` + `with_retry` — linear/exponential/jittered backoff
- `ContractValidator` — Pydantic I/O validation
- `AuditEmitter` — structured audit trail with SHA256 content hashing
- `CostTracker` — token cost accumulator fed by `_HarnessMetricsCallback`
- `load_config` — YAML config with `${VAR:-default}` interpolation
- `get_logger` — structlog structured logging
