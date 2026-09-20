# Harness Specification v1.0

## Public API Contract

All names listed below are guaranteed stable across minor versions.
Removal of any name, or a change to a positional parameter, is a **breaking change**
and requires a major version bump and a migration guide.

### Exported Names

| Name | Type | Description |
|---|---|---|
| `AgentHarness` | class | Main wrapper — call `.run(input_dict)` |
| `HarnessResult` | dataclass | Returned by every `.run()` call |
| `HarnessConfig` | Pydantic model | Configuration object |
| `LifecycleManager` | class | State machine |
| `AgentLifecycleState` | enum | States: INITIALISING, READY, RUNNING, COMPLETED, FAILED, SHUTDOWN |
| `RetryPolicy` | class | Retry configuration |
| `with_retry` | async function | Retry executor |
| `ContractValidator` | class | Pydantic I/O validator |
| `ContractViolationError` | exception | Raised on schema mismatch |
| `AuditEmitter` | class | Structured audit logger |
| `CostTracker` | class | Per-run cost accumulator |
| `get_logger` | function | Structured logger |
| `load_config` | function | YAML config loader |

### `AgentHarness.__init__` Signature

```python
AgentHarness(
    graph: Any,
    agent_name: str,
    agent_version: str,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
    config: HarnessConfig | None = None,
    config_path: str = "config/harness.yaml",
)
```

### `AgentHarness.run` Signature

```python
async def run(self, input_data: dict) -> HarnessResult
```

Always returns — never raises. On failure, returns `HarnessResult(success=False, ...)`.

### `HarnessResult` Fields

| Field | Type | Description |
|---|---|---|
| `run_id` | str | UUID per run |
| `success` | bool | Whether the run completed without error |
| `output` | Any | Validated output model instance, or None |
| `error` | str | Error message if failed |
| `error_type` | str | Exception class name |
| `duration_ms` | int | Wall-clock duration |
| `token_usage` | dict | Token counts from all LLM calls |
| `cost_usd` | float | Estimated cost |
| `lifecycle_states` | list[dict] | State machine history |
| `retry_attempts` | int | Number of retry attempts made |
| `audit_events` | list[dict] | Structured audit trail |

---

## What Constitutes a Breaking Change

A change is **breaking** if it causes any existing, correct caller to fail at import time or runtime without the caller changing its own code.

| Change type | Breaking | Detection method |
|---|---|---|
| Name removed from `__all__` or public surface | **Yes** | Pass 2: set difference `v1_names - v2_names` |
| Class or function renamed | **Yes** | Detected as removal of old name |
| Positional parameter removed from a function | **Yes** | Pass 3: param list diff on top-level funcs |
| Positional parameter removed from a method | **Yes** | Pass 4: param list diff per class method |
| Public method removed from a class | **Yes** | Pass 4: method presence check |
| Required parameter added | **Yes** | Detected as removed in the reverse direction — use detector bidirectionally if needed |
| Optional parameter added (`param=None`) | **No** | Absent from v1 param list; v1 callers unaffected |
| New name added to public surface | **No** | Additive; existing callers unaffected |
| Docstring, comment, whitespace changed | **No** | Not present in AST semantic surface |
| Private name changed (`_name`) | **No** | Filtered at extraction; not in public contract |

---

## Detection Algorithm

`breaking_change_detector.detect(v1_source, v2_source)` runs 4 passes over Python AST:

### Pass 1 — Public name resolution

```python
# Priority 1: __all__ is the authoritative public surface
__all__ = ["AgentHarness", "HarnessConfig"]

# Fallback (no __all__): all top-level non-underscore names
class AgentHarness: ...   # included
class _Internal: ...      # excluded
def run(): ...            # included
```

### Pass 2 — Removed public names

```python
for name in sorted(v1_names - v2_names):
    emit BreakingChange(kind="removed_name", name=name)
```

### Pass 3 — Top-level function signatures

```python
# Extract: posonlyargs + args + kwonlyargs, excluding self/cls
for name in v1_funcs:
    if name in v2_funcs:
        removed_params = [p for p in v1_params if p not in v2_params]
        if removed_params:
            emit BreakingChange(kind="changed_signature")
```

### Pass 4 — Class method signatures

```python
for cls in v1_classes:
    for method in v1_methods:
        if method not in v2_methods:
            emit BreakingChange(kind="removed_method")
        elif params removed:
            emit BreakingChange(kind="changed_signature")
```

All passes operate on `ast.parse()` output — no imports, no execution, no environment setup.

---

## Compatibility Suite

`compatibility/suite.py` verifies the **live installed** package against this spec.
It uses Python `inspect` and `dataclasses` introspection — not AST — because the package is already installed and importable.

Three check groups:
1. **Export checks** — `hasattr(harness_core, name)` for all 13 names above
2. **Signature checks** — `inspect.signature(AgentHarness.__init__)` for 5 init params
3. **Field checks** — `HarnessResult.__dataclass_fields__` for 7 result fields

Total: 25 checks. Pass rate must be 100% before a release ships.

---

## Version Policy

- **Major version**: any breaking change per the table above
- **Minor version**: new optional params, new exported names, new config keys with defaults
- **Patch version**: bug fixes, log improvements, no behaviour change

Automated enforcement: the breaking-change detector runs in CI on every PR that touches `harness_core`. A non-zero `detect()` result blocks merge.
