# repo-06-harness-engineering-playbook

Article 06 of the **Beyond the Model** series — Harness Engineering as a Discipline.

> **The agent code is the easy part. Keeping the harness stable across a growing fleet of agents is the discipline.**

---

## What This Is

This repo treats `agent-harness-core` as a versioned product. It demonstrates:

| Tool | Purpose |
|---|---|
| `breaking_change_detector.py` | AST-based comparison of two API surfaces — catches breaking changes before CI ships them |
| `compatibility/suite.py` | Programmatic verification that the installed harness exports every name in the v1.0 spec |
| `specification/harness-spec-v1.0.md` | Authoritative contract — what the harness guarantees to all downstream agents |
| `migration/` | Templates and a worked example for major-version migrations |
| `discipline/role-definition.md` | Defines the Harness Engineer role |
| Dashboard (`/demo`, `/metrics`, `/eval`) | Interactive demo of the detector; live compatibility suite results |

---

## Quick Start

```bash
pip install -e ".[dev]"
uvicorn dashboard.app:app --reload --port 8000
```

Then open `http://localhost:8000/demo`, paste two API surfaces, and click **Detect Breaking Changes**.

---

## Run Tests

```bash
pytest tests/ -v
```

All tests pass with zero API calls.

---

## Key Finding

> Breaking changes caught in CI in under 5 minutes. Before: discovered in production.

---

## Foundation Package

```
agent-harness-core @ git+https://github.com/ketan1602/agent-harness-core.git@v1.0.0
```

This repo installs and verifies the foundation package — it does not reimplement any harness code.
