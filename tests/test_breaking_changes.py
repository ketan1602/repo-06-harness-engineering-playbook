"""Tests for the breaking-change detector — pure Python, no API calls."""
from __future__ import annotations

import pytest

from eval.cases import CASES
from versioning.breaking_change_detector import detect


def test_removed_public_name_is_breaking():
    v1 = '__all__ = ["AgentHarness", "HarnessConfig"]\nclass AgentHarness: pass\nclass HarnessConfig: pass'
    v2 = '__all__ = ["AgentHarness"]\nclass AgentHarness: pass'
    changes = detect(v1, v2)
    assert any(c.kind == "removed_name" and c.name == "HarnessConfig" for c in changes)


def test_added_name_is_not_breaking():
    v1 = '__all__ = ["AgentHarness"]\nclass AgentHarness: pass'
    v2 = '__all__ = ["AgentHarness", "NewHelper"]\nclass AgentHarness: pass\nclass NewHelper: pass'
    changes = detect(v1, v2)
    assert len(changes) == 0


def test_removed_method_param_is_breaking():
    v1 = "class AgentHarness:\n    def run(self, input_data, timeout): pass"
    v2 = "class AgentHarness:\n    def run(self, input_data): pass"
    changes = detect(v1, v2)
    assert any(c.kind == "changed_signature" for c in changes)
    assert any("timeout" in c.detail for c in changes)


def test_added_optional_param_is_not_breaking():
    v1 = "class AgentHarness:\n    def run(self, input_data): pass"
    v2 = "class AgentHarness:\n    def run(self, input_data, timeout=None): pass"
    changes = detect(v1, v2)
    assert len(changes) == 0


def test_removed_method_is_breaking():
    v1 = "class AgentHarness:\n    def run(self, input_data): pass\n    def reset(self): pass"
    v2 = "class AgentHarness:\n    def run(self, input_data): pass"
    changes = detect(v1, v2)
    assert any(c.kind == "removed_method" and "reset" in c.name for c in changes)


def test_identical_apis_produce_no_changes():
    src = "def run(input_data, config): pass"
    assert detect(src, src) == []


def test_top_level_func_param_removal_is_breaking():
    v1 = "def run(input_data, config, timeout): pass"
    v2 = "def run(input_data, config): pass"
    changes = detect(v1, v2)
    assert any(c.kind == "changed_signature" and "timeout" in c.detail for c in changes)


def test_syntax_error_returns_parse_error():
    changes = detect("def run(: pass", "def run(): pass")
    assert len(changes) == 1
    assert changes[0].kind == "parse_error"


def _ids(role: str) -> list:
    return [pytest.param(*c, id=c[0]) for c in CASES if c[2] == role]


@pytest.mark.parametrize(("cid", "cls", "role", "v1", "v2", "kind"), _ids("positive"))
def test_positive_case_reports_expected_kind(cid, cls, role, v1, v2, kind):
    assert kind in {c.kind for c in detect(v1, v2)}


@pytest.mark.parametrize(("cid", "cls", "role", "v1", "v2", "kind"), _ids("negative") + _ids("benign"))
def test_safe_case_reports_nothing(cid, cls, role, v1, v2, kind):
    assert detect(v1, v2) == []


def test_every_change_class_has_positive_negative_and_benign_cases():
    classes = {c[1] for c in CASES if c[2] == "positive"}
    assert {"required_param_added", "optional_to_required", "positional_reorder", "ctor_change",
            "async_flip", "kwonly_posonly_change", "decorator_change", "base_removed",
            "synthesised_ctor"} <= classes
    assert all(any(c[1] == k and c[2] == "negative" for c in CASES) for k in classes)
    assert sum(1 for c in CASES if c[2] == "benign") >= 10
