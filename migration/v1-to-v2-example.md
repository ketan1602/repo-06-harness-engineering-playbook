# Example Migration: v1.0 → v2.0 (Hypothetical)

This example shows what a v2.0 migration guide would look like if `HarnessConfig`
were renamed to `HarnessSettings` and `with_retry` gained a required `policy` param.

## Breaking Changes in v2.0

| Change | Affected Callers | Migration Step |
|---|---|---|
| `HarnessConfig` renamed to `HarnessSettings` | `from harness_core import HarnessConfig` | Replace with `HarnessSettings` |
| `with_retry(fn, policy, ...)` — `policy` now positional | `await with_retry(fn, ...)` | Pass `policy=` explicitly |

## Detection

The breaking-change detector flags both:

```
removed_name: 'HarnessConfig' removed from public API
changed_signature: Parameters removed from 'with_retry': ['policy']
```

CI fails at `compatibility/suite.py` — the export check for `HarnessConfig` fails.
The breakage is caught in minutes, not discovered in production.

## Fix

```python
# Before (v1)
from harness_core import HarnessConfig
config = HarnessConfig(max_retry_attempts=3)

# After (v2)
from harness_core import HarnessSettings
config = HarnessSettings(max_retry_attempts=3)
```
