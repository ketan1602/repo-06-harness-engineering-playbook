"""Edit application and edit-data well-formedness. No harness checkout, no network, no model."""
from __future__ import annotations

from collections import Counter

import pytest

from eval import edit_apply, edit_summary
from eval.edits import EDITS

SRC = "def f(x):\n    return x + 1\n\n\ndef g(y):\n    return y\n"


def test_apply_then_revert_gives_the_original():
    patched = edit_apply.apply_edit(SRC, "return x + 1", "return x + 2")
    assert patched != SRC
    assert edit_apply.revert_edit(patched, "return x + 1", "return x + 2") == SRC


def test_missing_find_raises():
    with pytest.raises(ValueError, match="0 times"):
        edit_apply.apply_edit(SRC, "return z", "return q")


def test_ambiguous_find_raises():
    with pytest.raises(ValueError, match="2 times"):
        edit_apply.apply_edit(SRC, "return", "yield")


def test_empty_replacement_cannot_be_reverted():
    with pytest.raises(ValueError):
        edit_apply.revert_edit(SRC, "return y", "")


def test_patch_file_writes_and_returns_both_texts(tmp_path):
    (tmp_path / "m.py").write_text(SRC)
    edit = {"file": "m.py", "find": "return y", "replace": "return -y"}
    original, patched = edit_apply.patch_file(tmp_path, edit)
    assert original == SRC and (tmp_path / "m.py").read_text() == patched != SRC


def test_edits_are_well_formed():
    keys = {"id", "edit_type", "file", "find", "replace", "rationale", "intended_behaviour_change"}
    assert all(set(e) == keys for e in EDITS)
    assert len({e["id"] for e in EDITS}) == len(EDITS)
    assert all(e["find"] != e["replace"] and e["find"] for e in EDITS)
    assert all(isinstance(e["intended_behaviour_change"], bool) for e in EDITS)


def test_edit_mix_meets_requirements():
    types = Counter(e["edit_type"] for e in EDITS)
    assert types["logic_on_replay_path"] >= 5 and types["logic_off_replay_path"] >= 2
    assert types["signature_visible"] >= 2 and types["benign"] >= 2
    benign = [e for e in EDITS if e["edit_type"] == "benign"]
    assert all(e["intended_behaviour_change"] is False for e in benign)


def _row(caught, intended=True):
    guards = {g: {"caught": c} for g, c in zip(edit_summary.GUARDS, caught, strict=True)}
    return {"id": "x", "edit_type": "t", "intended_behaviour_change": intended, "import_ok": True,
            "guards": guards}


def test_summary_keeps_unmeasured_out_of_the_caught_count():
    out = edit_summary.summarise([_row([True, False, None, True]), _row([False, False, None, True])])
    tally = out["intended_change_edits_caught"]
    assert tally["g3_replay"] == {"caught": 0, "denominator": 2, "unmeasured": 2}
    assert tally["g4_tests"] == {"caught": 2, "denominator": 2, "unmeasured": 0}
