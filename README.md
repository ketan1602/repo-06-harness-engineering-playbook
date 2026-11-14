# repo-06-harness-engineering-playbook

Article 06 of the **Beyond the Model** series — Harness Engineering as a Discipline.

> **The agent code is the easy part. Keeping the harness stable across a growing fleet of agents is the discipline.**

---

## What This Is

This repo treats `agent-harness-core` as a versioned product with a dedicated engineering discipline. It demonstrates:

| Tool | Purpose |
|---|---|
| `versioning/breaking_change_detector.py` | AST-based comparison of two API surfaces — catches breaking changes before CI ships them |
| `compatibility/suite.py` | Programmatic verification that the installed harness exports every name in the v1.0 spec |
| `specification/harness-spec-v1.0.md` | Authoritative contract — what the harness guarantees to all downstream agents |
| `versioning/detection-scenarios.md` | All 14 detection scenarios with rationale and expected outcomes |
| `migration/` | Templates and a worked example for major-version migrations |
| `discipline/role-definition.md` | Defines the Harness Engineer role |
| Dashboard (`/demo`, `/metrics`, `/eval`) | Interactive demo of the detector; live compatibility suite results |

---

## Framework Logic: How the Breaking-Change Detector Works

The detector (`versioning/breaking_change_detector.py`) is a pure-Python, zero-dependency tool that uses the standard library `ast` module to compare two Python source strings. It makes no LLM calls and requires no imports of the packages under comparison — it works purely on source text.

### Build Rationale

**Why AST, not string diff?**
String diff produces noise — whitespace, comments, docstring rewording. AST parsing extracts semantic structure: which names are exported, which parameters each function declares. Two sources that are textually different but semantically identical produce zero breaking changes. Two sources that differ by removing one parameter name produce exactly one.

**Why source strings, not live inspection?**
The detector runs in CI before a new version is installed. It compares the proposed new API surface against the previous one using only the committed source. No import, no execution, no environment dependency.

### Detection Algorithm (4 passes)

```
Pass 1 — Public name resolution
  If __all__ is defined → use its string elements as the public set
  Else → collect all top-level non-underscore names (classes, functions, assignments)

Pass 2 — Removed public names
  For each name in v1_names that is absent from v2_names → BreakingChange(removed_name)

Pass 3 — Top-level function signature check
  For each public function present in both v1 and v2:
    Extract positional + keyword param names (excluding self/cls)
    Any param in v1 that is absent from v2 → BreakingChange(changed_signature)

Pass 4 — Class method check
  For each public class present in both v1 and v2:
    For each public method in v1:
      If method absent from v2 → BreakingChange(removed_method)
      If method present: run signature check as in Pass 3
```

### What Is and Is Not a Breaking Change

| Change | Breaking? | Reason |
|---|---|---|
| Remove a name from `__all__` / public API | **Yes** | Callers that import it break at import time |
| Rename a class or function | **Yes** | Detected as removal of old name |
| Remove a positional parameter | **Yes** | All callers passing that arg break |
| Add a required parameter | **Yes** | All existing callers missing it break |
| Add an optional parameter (`param=None`) | **No** | Existing callers still work unchanged |
| Add a new public name | **No** | Additive — existing callers unaffected |
| Change a docstring or comment | **No** | Not in the AST semantic surface |
| Rename a private method (`_method`) | **No** | Not in the public contract |

### Compatibility Suite Logic

`compatibility/suite.py` imports the **live installed** `harness_core` package (not source text) and runs three groups of checks:

1. **Export checks** — `hasattr(harness_core, name)` for all 13 names in the v1.0 spec
2. **Signature checks** — `inspect.signature(AgentHarness.__init__)` — verifies all 5 positional init params are present
3. **Dataclass field checks** — `HarnessResult.__dataclass_fields__` — verifies all 7 result fields exist

All checks produce structured pass/fail output consumable by CI and the `/eval` dashboard route.

---

## Detection Scenarios

See [`versioning/detection-scenarios.md`](versioning/detection-scenarios.md) for the full catalogue of 14 scenarios covering all breaking-change kinds, all non-breaking change kinds, and edge cases.

### Summary Table

| Scenario | Breaking? | Kind Detected |
|---|---|---|
| Remove name from `__all__` | Yes | `removed_name` |
| Add name to `__all__` | No | — |
| Remove a positional method parameter | Yes | `changed_signature` |
| Add an optional method parameter | No | — |
| Remove a public method from a class | Yes | `removed_method` |
| Identical APIs | No | — |
| Remove a top-level function parameter | Yes | `changed_signature` |
| Syntax error in either source | Error | `parse_error` |
| Private method removed (`_method`) | No | — |
| Multiple names removed simultaneously | Yes (one per name) | `removed_name` × N |
| Method renamed (old removed, new added) | Yes | `removed_method` |
| Class removed entirely | Yes | `removed_name` (if in `__all__`) |
| Parameter order changed, none removed | No | — |
| `__all__` absent in v1, present in v2 | Depends on diff | detected per above rules |

---

## Quick Start

```bash
pip install -e ".[dev]"
uvicorn dashboard.app:app --reload --port 8000
```

Open `http://localhost:8000/demo`, paste two API surfaces, click **Detect Breaking Changes**.

---

## Run Tests

```bash
pytest tests/ -v
```

21 tests — 8 detector unit tests, 5 compatibility suite tests, 8 dashboard route tests.
Zero API calls, zero environment setup beyond `pip install`.

---

## Key Finding

> Breaking changes caught in CI in under 5 minutes. Before: discovered in production.

---

## Foundation Package

Installed from:
```
file:../agent-harness-core/agent-harness-core  (harness-core 1.5.1, same as repo-05)
```

This repo installs and verifies the foundation package. It does not copy, reimplement, or patch any harness code. Every `from harness_core import` in this repo is a real import of the installed package.
