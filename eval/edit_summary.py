"""Summarise per-edit guard results: counts per guard, per edit type, and the catch matrix."""
from __future__ import annotations

GUARDS = ("g1_signature", "g2_compat", "g3_replay", "g4_tests")


def _tally(rows: list[dict], guard: str) -> dict:
    caught = [r["guards"][guard]["caught"] for r in rows]
    measured = [c for c in caught if c is not None]
    return {"caught": sum(measured), "denominator": len(rows), "unmeasured": len(caught) - len(measured)}


def summarise(results: list[dict]) -> dict:
    intended = [r for r in results if r["intended_behaviour_change"]]
    benign = [r for r in results if not r["intended_behaviour_change"]]
    by_type = {}
    for t in sorted({r["edit_type"] for r in results}):
        rows = [r for r in results if r["edit_type"] == t]
        by_type[t] = {"edits": len(rows), **{g: _tally(rows, g) for g in GUARDS}}
    matrix = [{"id": r["id"], "edit_type": r["edit_type"], "intended": r["intended_behaviour_change"],
               "import_ok": r["import_ok"], **{g: r["guards"][g]["caught"] for g in GUARDS}}
              for r in results]
    return {"intended_change_edits_caught": {g: _tally(intended, g) for g in GUARDS},
            "benign_edits_false_alarms": {g: _tally(benign, g) for g in GUARDS},
            "by_edit_type": by_type, "catch_matrix": matrix}


def table(matrix: list[dict]) -> str:
    sym = {True: "CAUGHT", False: "-", None: "null"}
    lines = [f'{"edit":38}{"type":24}{"intent":7}' + "".join(f"{g[:2].upper():8}" for g in GUARDS)]
    for r in matrix:
        lines.append(f'{r["id"]:38}{r["edit_type"]:24}{r["intended"]!s:7}'
                     + "".join(f"{sym[r[g]]:8}" for g in GUARDS))
    return "\n".join(lines)
