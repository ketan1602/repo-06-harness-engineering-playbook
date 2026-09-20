"""Compatibility suite — verifies the installed harness_core exports its full v1.0 API."""
from __future__ import annotations

import importlib
import inspect

EXPECTED_NAMES = [
    "AgentHarness",
    "HarnessResult",
    "HarnessConfig",
    "LifecycleManager",
    "AgentLifecycleState",
    "RetryPolicy",
    "with_retry",
    "ContractValidator",
    "ContractViolationError",
    "AuditEmitter",
    "CostTracker",
    "get_logger",
    "load_config",
]

HARNESS_INIT_PARAMS = ["graph", "agent_name", "agent_version", "input_schema", "output_schema"]
RESULT_FIELDS = ["run_id", "success", "output", "error", "error_type", "cost_usd", "duration_ms"]


def _check(label: str, passed: bool, detail: str = "") -> dict:
    return {"check": label, "passed": passed, "detail": detail}


def run() -> dict:
    """Run all compatibility checks and return a results dict."""
    checks: list[dict] = []

    try:
        mod = importlib.import_module("harness_core")
    except ImportError as exc:
        return {"passed": False, "error": str(exc), "checks": [], "pass_count": 0, "total": 0, "pass_rate_pct": 0}

    for name in EXPECTED_NAMES:
        present = hasattr(mod, name)
        checks.append(_check(f"export:{name}", present, "" if present else f"'{name}' missing"))

    harness_cls = getattr(mod, "AgentHarness", None)
    if harness_cls:
        try:
            sig = inspect.signature(harness_cls.__init__)
            params = list(sig.parameters.keys())
            for p in HARNESS_INIT_PARAMS:
                present = p in params
                checks.append(_check(f"AgentHarness.__init__:{p}", present, "" if present else f"'{p}' missing"))
        except (ValueError, TypeError):
            checks.append(_check("AgentHarness.__init__", False, "cannot inspect signature"))

    result_cls = getattr(mod, "HarnessResult", None)
    if result_cls and hasattr(result_cls, "__dataclass_fields__"):
        fields = list(result_cls.__dataclass_fields__.keys())
        for field in RESULT_FIELDS:
            present = field in fields
            checks.append(_check(f"HarnessResult:{field}", present, "" if present else f"'{field}' missing"))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    return {
        "passed": all(c["passed"] for c in checks),
        "pass_count": passed,
        "total": total,
        "pass_rate_pct": round(passed / total * 100, 1) if total else 0,
        "checks": checks,
    }
