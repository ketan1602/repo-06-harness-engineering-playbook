# repo-06-harness-engineering-playbook

Article 06 of the **Beyond the Model** series — Harness Engineering as a Discipline.

**ENG-09 · Season 2**

> **The agent code is the easy part. Keeping the harness stable across a growing fleet of agents is the discipline.**

---

## What This Is

This repo treats `agent-harness-core` as a versioned product with a dedicated engineering discipline. It demonstrates:

| Tool | Purpose |
|---|---|
| `versioning/breaking_change_detector.py` | Stdlib-only, signature-level comparison of two API surfaces (fixed detector; frozen original in `versioning/_baseline_detector.py`) |
| `compatibility/suite.py` | Programmatic verification that the installed harness exports every name in the v1.0 spec |
| `specification/harness-spec-v1.0.md` | Authoritative contract — what the harness guarantees to all downstream agents |
| `versioning/detection-scenarios.md` | Authored detection cases per change class, with rationale |
| `migration/` | Templates and a worked example for major-version migrations |
| `discipline/role-definition.md` | Defines the Harness Engineer role (success metrics are targets, not measurements) |
| `discipline/responsibilities.md` | Seven-responsibility ledger with evidence levels |
| Dashboard (`/demo`, `/metrics`, `/eval`) | Interactive demo of the detector; live compatibility suite results |

---

## Framework Logic: How the Breaking-Change Detector Works

The detector (`versioning/breaking_change_detector.py`) is a pure-Python, zero-dependency tool that uses the standard library `ast` module to compare two Python source strings. It makes no LLM calls and requires no imports of the packages under comparison — it works purely on source text.

### Build Rationale

**Why AST, not string diff?**
String diff produces noise — whitespace, comments, docstring rewording. AST parsing extracts semantic structure: which names are exported, which parameters each function declares. Two sources that are textually different but semantically identical produce zero breaking changes. Two sources that differ by removing one parameter name produce exactly one.

**Why source strings, not live inspection?**
It is designed to run before a new version is installed (as a CI step; proposed, not wired up here). It compares the proposed new API surface against the previous one using only the committed source. No import, no execution, no environment dependency.

### Detection Scope

Signature level only. Detected: removed names/methods/parameters, required parameter added, optional to required,
positional reorder (including inserting before existing positional parameters), constructor changes (explicit `__init__`,
dataclass fields, pydantic `BaseModel` fields), async/sync flips, keyword-only/positional-only narrowing,
calling-convention decorators (`property`, `staticmethod`, `classmethod`, `cached_property`) and removed same-file base classes.
Not detected by design: changed default values, behavioural changes (e.g. a newly raised exception), imported base classes,
return/annotation semantics, runtime-generated APIs. Details: `versioning/detection-scenarios.md`.

### What Is and Is Not Reported

| Change | Reported? |
|---|---|
| Remove a name from `__all__` / public API, rename a class or function | Yes |
| Remove a parameter or method | Yes |
| Add a required parameter | Yes (`required_param_added`) |
| Reorder positional parameters, or insert one before existing positional ones | Yes (`positional_reorder`) |
| Add an optional parameter at the end | No |
| Add a new public name | No |
| Change a docstring or comment | No |
| Rename a private method (`_method`) | No |
| Change a default value; raise a new exception | No (out of scope by design) |

### Compatibility Suite Logic

`compatibility/suite.py` imports the **live installed** `harness_core` package (not source text) and runs three groups of checks:

1. **Export checks** — `hasattr(harness_core, name)` for all 13 names in the v1.0 spec
2. **Signature checks** — `inspect.signature(AgentHarness.__init__)` — verifies all 5 positional init params are present
3. **Dataclass field checks** — `HarnessResult.__dataclass_fields__` — verifies all 7 result fields exist

All checks produce structured pass/fail output consumable by the `/eval` dashboard route.

---

## Detection Scenarios

See [`versioning/detection-scenarios.md`](versioning/detection-scenarios.md) for every change class with its authored example case ids, expected kind and rationale.

| Scenario (authored) | Breaking? | Kind Detected |
|---|---|---|
| Remove name from `__all__` | Yes | `removed_name` |
| Add name to `__all__` | No | — |
| Remove a method parameter | Yes | `changed_signature` |
| Add a required parameter | Yes | `required_param_added` |
| Add an optional parameter at the end | No | — |
| Remove a public method | Yes | `removed_method` |
| Reorder positional parameters, none removed | Yes | `positional_reorder` |
| Insert a parameter before existing positional ones | Yes | `positional_reorder` |
| Syntax error in either source | Error | `parse_error` |
| Private method removed (`_method`) | No | — |
| Change a default value | Yes (not detected) | — (out of scope) |

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
python3 -m pytest tests/ -q
```

Last run: 74 passed. No API calls.

---

## Measured Result: Baseline vs Fixed Detector

Reproduce with one command:

```bash
python -m eval.before_after
```

It writes `measurements/detector_before_after.json` (raw per-class table). All cases are AUTHORED by the repo author (`eval/cases.py`) with hand-labelled expected results.

| On 51 authored in-scope cases (23 expected breaking, 28 expected not breaking) | Baseline (frozen original) | Fixed |
|---|---|---|
| Breaking changes caught | 3 of 23 | 23 of 23 |
| False positives | 0 | 0 |
| Median runtime per run | 9.71 us | 14.4 us |

Two further authored out-of-scope cases (default value change, newly raised exception) are caught by neither detector, by design.

Caveat: the fixed detector's 23/23 is partly circular, because the same author wrote the fix and the cases. The baseline's 3/23 on the same cases is the informative number. These are not real-world results.

---

## Behavioural replay across releases

<!-- REPLAY-RESULTS -->
Pending: see measurements/replay_across_versions.json when present.

---

## Limitations

- Authored cases only; no real-world or third-party change history was used.
- Signature-level detection only. Behavioural change (changed defaults, new exceptions) is invisible to it.
- One small harness (`agent-harness-core`).
- A structural guard cannot substitute for behavioural conformance (the ENG-05 principle).
- Same-file base classes only; imported bases are not compared.
- The CI gate described in the spec is proposed; no CI workflow exists in this repo.
- Role success metrics are targets; `measurements/discipline_metrics.json` records them as `null` (not measured).

---

## Foundation Package

Installed from:
```
file:../agent-harness-core/agent-harness-core  (harness-core 1.5.1, same as repo-05)
```

This repo installs and verifies the foundation package. It does not copy, reimplement, or patch any harness code. Every `from harness_core import` in this repo is a real import of the installed package.
