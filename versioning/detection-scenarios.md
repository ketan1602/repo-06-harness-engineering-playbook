# Breaking-Change Detection Scenarios

This document catalogs all 14 scenarios used to validate `breaking_change_detector.py`.
Each scenario states: the v1 surface, the v2 surface, whether it is breaking, what the detector emits, and the rationale.

Scenarios 1–8 correspond to `tests/test_breaking_changes.py`.
Scenarios 9–14 correspond to the `DETECTOR_CASES` in `eval/runner.py`.

---

## Framework Build Logic

### Public name resolution (Pass 1)

```python
# If __all__ is defined, its string elements ARE the public surface.
# Everything outside __all__ is invisible to callers and not checked.
__all__ = ["AgentHarness", "HarnessConfig"]  # only these two matter

# If __all__ is absent, all top-level non-underscore names are public.
class AgentHarness: ...   # public
class _Internal: ...      # private — ignored
def run(): ...            # public
def _helper(): ...        # private — ignored
```

### Removed-name detection (Pass 2)

`v1_names - v2_names` → each missing name emits one `BreakingChange(kind="removed_name")`.

### Signature check (Passes 3 & 4)

For functions (top-level and methods):
- Extract `posonlyargs + args + kwonlyargs` excluding `self`/`cls`
- Any param present in v1 but absent from v2 → `BreakingChange(kind="changed_signature")`
- Params added in v2 are ignored (they may be optional)

---

## Scenarios

### Scenario 1 — Remove a name from `__all__`  *(breaking)*

**v1:**
```python
__all__ = ["AgentHarness", "HarnessConfig"]
class AgentHarness: pass
class HarnessConfig: pass
```
**v2:**
```python
__all__ = ["AgentHarness"]
class AgentHarness: pass
```
**Expected:** `BreakingChange(kind="removed_name", name="HarnessConfig")`

**Rationale:** Any downstream `from harness_core import HarnessConfig` raises `ImportError` immediately. This is the most common harness-versioning mistake — renaming `HarnessConfig` without adding a re-export shim.

---

### Scenario 2 — Add a name to `__all__`  *(not breaking)*

**v1:**
```python
__all__ = ["AgentHarness"]
class AgentHarness: pass
```
**v2:**
```python
__all__ = ["AgentHarness", "NewHelper"]
class AgentHarness: pass
class NewHelper: pass
```
**Expected:** no changes

**Rationale:** Additive changes never break existing callers. Adding to the public API is always a minor-version bump, not major.

---

### Scenario 3 — Remove a positional parameter from a method  *(breaking)*

**v1:**
```python
class AgentHarness:
    def run(self, input_data, timeout): pass
```
**v2:**
```python
class AgentHarness:
    def run(self, input_data): pass
```
**Expected:** `BreakingChange(kind="changed_signature", name="AgentHarness.run", detail="Parameters removed from 'AgentHarness.run': ['timeout']")`

**Rationale:** All callers passing `timeout=120` break with `TypeError: run() got an unexpected keyword argument 'timeout'`. The error is silent in the harness but loud in the caller.

---

### Scenario 4 — Add an optional parameter to a method  *(not breaking)*

**v1:**
```python
class AgentHarness:
    def run(self, input_data): pass
```
**v2:**
```python
class AgentHarness:
    def run(self, input_data, timeout=None): pass
```
**Expected:** no changes

**Rationale:** Existing callers do not pass `timeout`; they continue to work. The new parameter has a default — no caller is forced to change.

---

### Scenario 5 — Remove a public method from a class  *(breaking)*

**v1:**
```python
class AgentHarness:
    def run(self, input_data): pass
    def reset(self): pass
```
**v2:**
```python
class AgentHarness:
    def run(self, input_data): pass
```
**Expected:** `BreakingChange(kind="removed_method", name="AgentHarness.reset")`

**Rationale:** Any caller doing `harness.reset()` after an error-recovery loop gets `AttributeError`. Methods in the public contract are as load-bearing as exported names.

---

### Scenario 6 — Identical APIs  *(not breaking)*

**v1 = v2:**
```python
def run(input_data, config): pass
```
**Expected:** no changes

**Rationale:** Baseline check — the detector must produce zero output for unchanged surfaces. If this fires, the detector has a false-positive bug.

---

### Scenario 7 — Remove a parameter from a top-level function  *(breaking)*

**v1:**
```python
def run(input_data, config, timeout): pass
```
**v2:**
```python
def run(input_data, config): pass
```
**Expected:** `BreakingChange(kind="changed_signature", name="run", detail="Parameters removed from 'run': ['timeout']")`

**Rationale:** Same logic as Scenario 3, applied to module-level functions rather than class methods.

---

### Scenario 8 — Syntax error in source  *(parse_error)*

**v1:** `def run(: pass`  (invalid Python)

**v2:** `def run(): pass`

**Expected:** `BreakingChange(kind="parse_error", name="", detail="<SyntaxError message>")`

**Rationale:** The detector must never raise an unhandled exception. Malformed input — a paste error in the dashboard, a truncated file — returns a structured error rather than crashing the CI step.

---

### Scenario 9 — Removed name is detected  *(breaking)*
*(eval/runner.py — `DETECTOR_CASES[0]`)*

Same as Scenario 1. Confirms the eval runner produces `expect_breaking=True` correctly against a live detector invocation.

---

### Scenario 10 — Added name is not breaking  *(not breaking)*
*(eval/runner.py — `DETECTOR_CASES[1]`)*

Same as Scenario 2. Confirms the eval runner produces `expect_breaking=False` for an additive change.

---

### Scenario 11 — Removed method parameter is breaking  *(breaking)*
*(eval/runner.py — `DETECTOR_CASES[2]`)*

Same as Scenario 3. Validates the eval harness round-trip: detector → eval case → dashboard `/eval` route → structured JSON output.

---

### Scenario 12 — Added optional parameter is not breaking  *(not breaking)*
*(eval/runner.py — `DETECTOR_CASES[3]`)*

Same as Scenario 4. Validates that the eval route correctly classifies this as `passed=True` when `expect_breaking=False`.

---

### Scenario 13 — Removed method is breaking  *(breaking)*
*(eval/runner.py — `DETECTOR_CASES[4]`)*

Same as Scenario 5. Included separately in the eval runner so the `/eval` dashboard shows a `removed_method` result alongside `removed_name` and `changed_signature` in one run.

---

### Scenario 14 — Identical APIs produce no changes  *(not breaking)*
*(eval/runner.py — `DETECTOR_CASES[5]`)*

Same as Scenario 6. The eval runner's baseline — confirms all three passes (names, functions, class methods) produce zero output when there is nothing to report.

---

## Coverage Summary

| Breaking-change kind | Covered by scenarios |
|---|---|
| `removed_name` | 1, 9 |
| `changed_signature` (method) | 3, 11 |
| `changed_signature` (function) | 7 |
| `removed_method` | 5, 13 |
| `parse_error` | 8 |
| Not breaking — additive name | 2, 10 |
| Not breaking — optional param | 4, 12 |
| Not breaking — identical | 6, 14 |

All 4 detector output kinds and all 4 non-breaking patterns are covered.
