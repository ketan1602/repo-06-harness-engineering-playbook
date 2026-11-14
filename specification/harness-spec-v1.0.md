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

The detector (`versioning/breaking_change_detector.py`) implements a signature-level subset of this definition.
Examples of each row are authored cases in `eval/cases.py` (see `versioning/detection-scenarios.md`).

| Change type | Breaking | Detected by the current detector |
|---|---|---|
| Name removed from `__all__` or public surface | **Yes** | Yes (`removed_name`) |
| Class or function renamed | **Yes** | Yes, as removal of the old name |
| Parameter removed from a function or method | **Yes** | Yes (`changed_signature`) |
| Public method removed from a class | **Yes** | Yes (`removed_method`) |
| Required parameter added | **Yes** | Yes, directly (`required_param_added`) |
| Optional parameter became required | **Yes** | Yes (`optional_to_required`) |
| Positional parameters reordered, or a parameter inserted before existing positional ones | **Yes** | Yes (`positional_reorder`) |
| Constructor changed (explicit `__init__`, dataclass fields, pydantic `BaseModel` fields) | **Yes** | Yes (`ctor_change`) |
| `async` function became sync, or the reverse | **Yes** | Yes (`async_flip`) |
| Parameter made keyword-only or positional-only | **Yes** | Yes (`kwonly_posonly_change`) |
| `property`, `staticmethod`, `classmethod`, `cached_property` added or removed | **Yes** | Yes (`decorator_change`) |
| Base class removed (same-file bases only) | **Yes** | Yes (`base_removed`) |
| Default value changed | **Yes** (callers relying on it change behaviour) | **No, by design** |
| Behavioural change (e.g. a newly raised exception) | **Yes** | **No, by design** |
| Imported base class changed, return or annotation semantics, runtime-generated APIs | **Yes** | **No, by design** |
| Optional parameter appended (`param=None`) | **No** | Not reported |
| New name added to public surface | **No** | Not reported |
| Docstring, comment, whitespace changed | **No** | Not reported |
| Private name changed (`_name`) | **No** | Not reported |

Behavioural changes require behavioural conformance testing; a structural check cannot substitute for it.

---

## Detection Algorithm

`breaking_change_detector.detect(v1_source, v2_source)` parses both sources with `ast.parse()` (stdlib only, no imports, no execution) and returns a list of `BreakingChange(kind, name, detail)`.
A syntax error in either source returns a single `parse_error` entry instead of raising.

1. **Public names.** `__all__` string elements if defined, otherwise top-level non-underscore names. Names in v1 missing from v2 emit `removed_name`.
2. **Top-level functions.** For each public function in both versions, compare signatures (`signature_model.compare`): removed parameters, added required parameters, optional-to-required, positional order (including insertion before existing positional parameters), keyword-only/positional-only narrowing, async flips and calling-convention decorators.
3. **Classes.** For each public class in both versions (`class_model`): removed methods, per-method signature comparison, constructor comparison (explicit `__init__`, dataclass fields, pydantic `BaseModel` fields) and removed same-file base classes.

Appending an optional parameter, adding names or methods, and reformatting are not reported.
Measured behaviour on authored cases: `measurements/detector_before_after.json` (reproduce with `python -m eval.before_after`).

---

## Compatibility Suite

`compatibility/suite.py` verifies the **live installed** package against this spec.
It uses Python `inspect` and `dataclasses` introspection — not AST — because the package is already installed and importable.

Three check groups:
1. **Export checks** — `hasattr(harness_core, name)` for all 13 names above
2. **Signature checks** — `inspect.signature(AgentHarness.__init__)` for 5 init params
3. **Field checks** — `HarnessResult.__dataclass_fields__` for 7 result fields

Total: 25 checks (13 exports + 5 init params + 7 result fields, verified by running `compatibility/suite.py` against the installed package). Pass rate must be 100% before a release ships.

---

## Version Policy

- **Major version**: any breaking change per the table above
- **Minor version**: new optional params, new exported names, new config keys with defaults
- **Patch version**: bug fixes, log improvements, no behaviour change

Automated enforcement (PROPOSED, NOT IMPLEMENTED): running the detector in CI on every PR that touches `harness_core` and blocking merge on a non-empty result. This repo contains no CI workflow; the detector is only run by tests, the dashboard and `python -m eval.before_after`.
