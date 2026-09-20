"""Eval runner — runs the compatibility suite and breaking-change detector test cases."""
from __future__ import annotations

from compatibility.suite import run as run_compat
from versioning.breaking_change_detector import detect

DETECTOR_CASES = [
    {
        "name": "removed_name_is_detected",
        "v1": '__all__ = ["AgentHarness", "HarnessConfig"]\nclass AgentHarness: pass\nclass HarnessConfig: pass',
        "v2": '__all__ = ["AgentHarness"]\nclass AgentHarness: pass',
        "expect_breaking": True,
    },
    {
        "name": "added_name_is_not_breaking",
        "v1": '__all__ = ["AgentHarness"]\nclass AgentHarness: pass',
        "v2": '__all__ = ["AgentHarness", "NewHelper"]\nclass AgentHarness: pass\nclass NewHelper: pass',
        "expect_breaking": False,
    },
    {
        "name": "removed_method_param_is_breaking",
        "v1": "class AgentHarness:\n    def run(self, input_data, timeout): pass",
        "v2": "class AgentHarness:\n    def run(self, input_data): pass",
        "expect_breaking": True,
    },
    {
        "name": "added_optional_param_is_not_breaking",
        "v1": "class AgentHarness:\n    def run(self, input_data): pass",
        "v2": "class AgentHarness:\n    def run(self, input_data, timeout=None): pass",
        "expect_breaking": False,
    },
    {
        "name": "removed_method_is_breaking",
        "v1": "class AgentHarness:\n    def run(self, input_data): pass\n    def reset(self): pass",
        "v2": "class AgentHarness:\n    def run(self, input_data): pass",
        "expect_breaking": True,
    },
    {
        "name": "identical_apis_produce_no_changes",
        "v1": "def run(input_data, config): pass",
        "v2": "def run(input_data, config): pass",
        "expect_breaking": False,
    },
]


def run_eval() -> dict:
    """Run all eval cases and return a structured results dict."""
    compat = run_compat()

    detector_results = []
    for case in DETECTOR_CASES:
        changes = detect(case["v1"], case["v2"])
        is_breaking = len(changes) > 0
        detector_results.append({
            "name": case["name"],
            "passed": is_breaking == case["expect_breaking"],
            "expected_breaking": case["expect_breaking"],
            "got_breaking": is_breaking,
            "changes": [c.detail for c in changes],
        })

    passed_det = sum(1 for r in detector_results if r["passed"])
    total_det = len(detector_results)
    return {
        "compatibility_suite": compat,
        "detector_cases": detector_results,
        "detector_passed": passed_det,
        "detector_total": total_det,
        "all_passed": compat["passed"] and passed_det == total_det,
    }
