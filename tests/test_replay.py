"""Replay logic on a tiny synthetic fixture: no data files, no network, no model."""
from __future__ import annotations

from eval import replay, replay_data
from eval.replay_worker import fake_openai


def _rec(case, decision, normalizations=None, **extra):
    actual = {} if normalizations is None else {"normalizations": normalizations}
    return {"case": case, "category": case.split("-")[0], "repeat": 0, "decision": decision,
            "verdict": {"actual": actual}, **extra}


REFUND = {"tool": "issue_refund", "arguments": {"order_id": "O-1", "amount": 150}, "tokens": 9}


def _res(case, status, effects=(), normalizations=None, **over):
    return {"dataset": "d", "model": "m", "framework": "f", "case": case, "repeat": 0,
            "status": status, "effects": list(effects), "violated": False,
            "normalizations": normalizations, **over}


def test_pre_normalisation_records_are_raw_unless_field_present():
    items, skipped = replay_data.select("d", replay_data.PRE_NORMALISATION, "m", "f",
                                        [_rec("a-1", REFUND), _rec("b-1", REFUND, []),
                                         _rec("c-1", None, no_decision=True)])
    assert [i["case"] for i in items] == ["a-1"]
    assert skipped == {"normalisation_field_present": 1, "no_decision": 1}


def test_post_normalisation_records_are_excluded_not_guessed():
    items, skipped = replay_data.select(
        "d", replay_data.RECORDS_NORMALISATION, "m", "f",
        [_rec("a-1", REFUND, []), _rec("b-1", REFUND, ["tool_name_namespace"]), _rec("c-1", REFUND)])
    assert [i["case"] for i in items] == ["a-1"]
    assert skipped == {"post_normalisation": 1, "normalisation_unrecorded": 1}


def test_compare_counts_flips_and_attributes_the_rule():
    before = [_res("refund-1", "blocked"), _res("note-1", "completed")]
    after = [_res("refund-1", "awaiting_approval", normalizations=["tool_name_namespace"]),
             _res("note-1", "completed", normalizations=[])]
    out = replay.compare(before, after, {"refund-1": "refund", "note-1": "note"})
    assert out["paired"] == 2 and out["breakdown"]["flip_count"] == 1
    assert out["breakdown"]["by_normalisation_rule"] == {"tool_name_namespace": 1}
    assert out["flips"][0]["changed"] == ["status"]


def test_zero_flips_is_a_valid_result_and_errors_are_not_paired():
    same = [_res("a-1", "completed", normalizations=[])]
    out = replay.compare(same, same + [], {})
    assert out["breakdown"]["flip_count"] == 0 and out["flips"] == []
    err = replay.compare([_res("a-1", "x", error="boom")], same, {})
    assert err["paired"] == 0 and err["unpaired_or_errored"] == 1


def test_unmeasured_normalisation_is_null_not_zero():
    assert replay.normalisation_counts([_res("a-1", "completed")])["needing_normalisation"] is None
    measured = replay.normalisation_counts([_res("a-1", "completed", normalizations=["numeric_string"])])
    assert measured["needing_normalisation"] == 1


def test_fake_client_returns_stored_decision_as_json_chat_reply():
    import asyncio
    current = {"decision": REFUND}
    client = fake_openai(current)()
    reply = asyncio.run(client.chat.completions.create(model="m"))
    assert '"issue_refund"' in reply.choices[0].message.content
    assert reply.usage.total_tokens == 9
