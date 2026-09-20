"""Tests for the compatibility suite — verifies harness_core v1.0 exports."""
from __future__ import annotations

from compatibility.suite import run


def test_compatibility_suite_passes():
    result = run()
    assert result["passed"], (
        "Compatibility suite failed. Failing checks: "
        + str([c for c in result["checks"] if not c["passed"]])
    )


def test_all_expected_names_present():
    result = run()
    export_checks = [c for c in result["checks"] if c["check"].startswith("export:")]
    assert all(c["passed"] for c in export_checks), (
        "Missing exports: " + str([c["check"] for c in export_checks if not c["passed"]])
    )


def test_harness_init_params_present():
    result = run()
    init_checks = [c for c in result["checks"] if "AgentHarness.__init__:" in c["check"]]
    assert len(init_checks) > 0, "No AgentHarness.__init__ param checks found"
    assert all(c["passed"] for c in init_checks), (
        "Missing init params: " + str([c for c in init_checks if not c["passed"]])
    )


def test_result_fields_present():
    result = run()
    field_checks = [c for c in result["checks"] if c["check"].startswith("HarnessResult:")]
    assert len(field_checks) > 0, "No HarnessResult field checks found"
    assert all(c["passed"] for c in field_checks), (
        "Missing fields: " + str([c for c in field_checks if not c["passed"]])
    )


def test_pass_rate_is_100():
    result = run()
    assert result["pass_rate_pct"] == 100.0, (
        f"Expected 100% pass rate, got {result['pass_rate_pct']}%"
    )
