"""Select raw model decisions from stored live-run files for replay.

A stored decision is RAW only when the harness that recorded it applied no normalisation to it:
either the harness predates normalisation (1.5.0: the field is absent and the rules do not exist)
or it recorded an empty `normalizations` list. A decision recorded with a non-empty list was
rewritten before it was stored, so it is excluded rather than guessed back.
"""
from __future__ import annotations

import json
from pathlib import Path

PRE_NORMALISATION, RECORDS_NORMALISATION = "pre_normalisation", "records_normalisation"


def classify(record: dict, mode: str) -> str:
    """'raw' or the reason this record cannot be replayed from its stored decision."""
    decision = record.get("decision")
    if record.get("no_decision") or not decision or not decision.get("tool"):
        return "no_decision"
    actual = (record.get("verdict") or {}).get("actual") or {}
    if mode == PRE_NORMALISATION:
        return "normalisation_field_present" if "normalizations" in actual else "raw"
    if "normalizations" not in actual:
        return "normalisation_unrecorded"
    return "post_normalisation" if actual["normalizations"] else "raw"


def select(dataset: str, mode: str, model: str, framework: str, records: list[dict]):
    """Split one file's gateway-arm records into replayable items and a reason -> count map."""
    items: list[dict] = []
    excluded: dict[str, int] = {}
    for rec in records:
        verdict = classify(rec, mode)
        if verdict != "raw":
            excluded[verdict] = excluded.get(verdict, 0) + 1
            continue
        d = rec["decision"]
        items.append({"dataset": dataset, "model": model, "framework": framework,
                      "case": rec["case"], "category": rec["category"], "repeat": rec["repeat"],
                      "decision": {"tool": d["tool"], "arguments": d["arguments"],
                                   "tokens": d.get("tokens", 0)}})
    return items, excluded


def load_dataset(name: str, root: Path, mode: str):
    """Every replayable item under root/<model-dir>/<framework>.json, plus exclusion counts."""
    items: list[dict] = []
    excluded: dict[str, dict[str, int]] = {}
    for path in sorted(root.glob("*/*.json")):
        data = json.loads(path.read_text())
        got, skipped = select(name, mode, data.get("model") or path.parent.name,
                              path.stem, data["via_gateway"]["cases"])
        items += got
        for reason, n in skipped.items():
            by_model = excluded.setdefault(data.get("model") or path.parent.name, {})
            by_model[reason] = by_model.get(reason, 0) + n
    return items, excluded


def provenance(root: Path) -> dict:
    """Counts that show whether stored decisions are raw: how many gateway-arm records carry
    applied normalisations, and whether a prefixed tool name or numeric string survives in them."""
    c = {"records": 0, "with_normalizations_field": 0, "normalizations_nonempty": 0,
         "nonempty_but_stored_tool_still_prefixed": 0,
         "nonempty_but_stored_amount_still_string": 0,
         "stored_tool_prefixed": 0, "stored_amount_string": 0}
    for path in sorted(root.glob("*/*.json")):
        for rec in json.loads(path.read_text())["via_gateway"]["cases"]:
            d = rec.get("decision") or {}
            actual = (rec.get("verdict") or {}).get("actual") or {}
            prefixed = str(d.get("tool", "")).startswith("functions.")
            string_amount = isinstance((d.get("arguments") or {}).get("amount"), str)
            c["records"] += 1
            c["with_normalizations_field"] += "normalizations" in actual
            c["stored_tool_prefixed"] += prefixed
            c["stored_amount_string"] += string_amount
            if actual.get("normalizations"):
                c["normalizations_nonempty"] += 1
                c["nonempty_but_stored_tool_still_prefixed"] += prefixed
                c["nonempty_but_stored_amount_still_string"] += string_amount
    return c
