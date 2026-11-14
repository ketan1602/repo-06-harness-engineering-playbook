"""Run every curated edit through four guards on a fresh temp copy of the harness at one tag."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from eval import edit_apply, edit_coverage, edit_summary, tag_env
from eval import edit_guards as guards
from eval.edits import EDITS

TAG = "v1.5.1"
PATHS = ("src", "tests", "pyproject.toml")  # pyproject carries the harness's pytest config
LIMITS = [
    "Edits are authored by the repo author; labels (intended_behaviour_change) are the author's.",
    "Replay uses only the 16 authored cases and one day of stored decisions (2026-10-23/24).",
    "The signature detector cannot see logic edits by construction.",
    ("Replay holds the model's decisions fixed, so it only sees edits that change how the harness "
     "judges a stored decision, through the plain-client reference-adapter path."),
    "The harness test suite is the harness authors' own, not independent.",
    "G4 compares failing test ids with the unpatched control; the control itself has failures.",
]


def fresh_copy(harness: Path, work: Path, name: str) -> Path:
    root = work / name
    if error := tag_env.extract(harness, TAG, root, PATHS):
        raise RuntimeError(f"extract failed: {error}")
    return root


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def run_one(edit: dict, ctx: dict) -> dict:
    root = fresh_copy(ctx["harness"], ctx["work"], edit["id"])
    original, patched = edit_apply.patch_file(root, edit)
    ok, err = guards.import_ok(root, edit["file"])
    rep, why = guards.replay_items(ctx["items"], root, ctx["work"], edit["id"])
    res = guards.run_tests(root)
    row = {k: edit[k] for k in ("id", "edit_type", "file", "rationale", "intended_behaviour_change")}
    row |= {"import_ok": ok, "import_error": err or None, "guards": {
        "g1_signature": guards.g1_signature(root, edit["file"], original, patched),
        "g2_compat": guards.g2_compat(root),
        "g3_replay": guards.g3_replay(ctx["base"], rep, why, ctx["categories"]),
        "g4_tests": guards.g4_tests(res, ctx["control_failing"])}}
    shutil.rmtree(root)
    _log(f'{edit["id"]}: import_ok={ok} ' + str({g: v["caught"] for g, v in row["guards"].items()}))
    return row


def no_edit_control(ctx: dict, control_b: dict, control_a: dict) -> dict:
    root = fresh_copy(ctx["harness"], ctx["work"], "no_edit")
    rep, why = guards.replay_items(ctx["items"], root, ctx["work"], "no_edit")
    new_vs_a = sorted(set(control_b["failing"]) - set(control_a["failing"])) if control_b["ran"] else None
    flaky = (sorted(set(control_a["failing"]) ^ set(control_b["failing"]))
             if control_a["ran"] and control_b["ran"] else None)
    return {"g2_compat": guards.g2_compat(root),
            "g3_replay": guards.g3_replay(ctx["base"], rep, why, ctx["categories"]),
            "g4_tests": {"caught": None if new_vs_a is None else bool(new_vs_a),
                         "new_failing_tests_vs_first_control_run": new_vs_a,
                         "flaky_tests_between_control_runs": flaky}}


def run(harness: Path, items: list[dict], out_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        base_root = fresh_copy(harness, work, "unpatched")
        base, why = guards.replay_items(items, base_root, work, "unpatched")
        if base is None:
            raise RuntimeError(f"unpatched replay failed: {why}")
        cases = json.loads((base_root / "src/harness_core/scenarios/support/cases.json").read_text())
        control_a, control_b = guards.run_tests(base_root), guards.run_tests(base_root)
        _log(f"control tests: {control_a.get('summary_line')} | {control_b.get('summary_line')}")
        if not control_a["ran"]:
            raise RuntimeError(f"harness tests cannot run on unpatched {TAG}: {control_a['reason']}")
        failing = set(control_a["failing"]) | set(control_b.get("failing") or [])
        ctx = {"harness": harness, "work": work, "items": items, "base": base,
               "categories": {c["id"]: c["category"] for c in cases}, "control_failing": failing}
        results = [run_one(e, ctx) for e in EDITS]
        control = no_edit_control(ctx, control_b, control_a)
    doc = {"harness_tag": TAG, "replayed_items": len(items), "replay_coverage": edit_coverage.coverage(items),
           "g4_control": {"first_run": control_a, "second_run": control_b,
                          "failing_union_count": len(failing),
                          "note": "Run without -x so failing ids are comparable; edits count only "
                                  "failures outside the union of both control runs."},
           "no_edit_control": control, "edits": results,
           "summary": edit_summary.summarise(results), "limits": LIMITS}
    out_path.write_text(json.dumps(doc, indent=1))
    print(edit_summary.table(doc["summary"]["catch_matrix"]))
    return doc
