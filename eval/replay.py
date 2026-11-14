"""Compare replay outcomes of the same stored decisions across two harness versions."""
from __future__ import annotations

from collections import Counter

KEY = ("dataset", "model", "framework", "case", "repeat")
FIELDS = ("status", "violated", "effects")


def _key(rec: dict) -> tuple:
    return tuple(rec[k] for k in KEY)


def changed_fields(before: dict, after: dict) -> list[str]:
    return [f for f in FIELDS if before[f] != after[f]]


def compare(before: list[dict], after: list[dict], categories: dict[str, str]) -> dict:
    """Flips between two result lists, matched on (dataset, model, framework, case, repeat)."""
    after_by_key = {_key(r): r for r in after}
    flips, paired, unpaired = [], 0, 0
    rule_no_flip = Counter()
    for b in before:
        a = after_by_key.get(_key(b))
        if a is None or "error" in a or "error" in b:
            unpaired += 1
            continue
        paired += 1
        fields = changed_fields(b, a)
        if a["normalizations"] and not fields:
            rule_no_flip[categories.get(b["case"])] += 1
        if fields:
            flips.append({**dict(zip(KEY, _key(b), strict=True)),
                          "category": categories.get(b["case"]), "changed": fields,
                          "before_status": b["status"], "before_effects": b["effects"],
                          "after_status": a["status"], "after_effects": a["effects"],
                          "before_violated": b["violated"], "after_violated": a["violated"],
                          "after_normalizations": a["normalizations"]})
    return {"paired": paired, "unpaired_or_errored": unpaired, "flips": flips,
            "breakdown": breakdown(flips),
            "rule_applied_but_outcome_unchanged_by_category": dict(rule_no_flip)}


def breakdown(flips: list[dict]) -> dict:
    by_rule = Counter(r for f in flips for r in (f["after_normalizations"] or ["none_recorded"]))
    return {"flip_count": len(flips),
            "by_model": dict(Counter(f["model"] for f in flips)),
            "by_dataset": dict(Counter(f["dataset"] for f in flips)),
            "by_category": dict(Counter(f["category"] for f in flips)),
            "by_normalisation_rule": dict(by_rule),
            "by_changed_field": dict(Counter(x for f in flips for x in f["changed"]))}


def normalisation_counts(results: list[dict]) -> dict:
    """How many replayed decisions had at least one rule applied, per model; None if unmeasured."""
    if any(r.get("normalizations") is None for r in results if "error" not in r):
        return {"measured": False, "needing_normalisation": None, "by_rule": None}
    ok = [r for r in results if "error" not in r]
    return {"measured": True, "needing_normalisation": sum(bool(r["normalizations"]) for r in ok),
            "by_rule": dict(Counter(x for r in ok for x in r["normalizations"]))}


def count_by_model(results: list[dict]) -> dict:
    return dict(Counter(f'{r["dataset"]}/{r["model"]}' for r in results))
