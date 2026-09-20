"""Tests for the breaking-change detector — pure Python, no API calls."""
from __future__ import annotations

from versioning.breaking_change_detector import detect


def _v1(src: str) -> str:
    return src


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
