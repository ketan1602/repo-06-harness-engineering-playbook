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

## Version Policy

- **Major version**: any breaking change per the rules above
- **Minor version**: new optional params, new exported names, new config keys
- **Patch version**: bug fixes, doc improvements, no behaviour change
