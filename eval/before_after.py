"""Before/after measurement: baseline detector vs fixed detector over the authored case set.

Run: python -m eval.before_after   (writes measurements/detector_before_after.json)
All cases are authored by the repo author. Timings are measured here, on this machine.
"""
from __future__ import annotations

import json
import platform
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from eval.cases import CASES
from versioning._baseline_detector import detect as baseline_detect
from versioning.breaking_change_detector import detect as fixed_detect

OUT = Path("measurements/detector_before_after.json")
TIMING_REPEATS = 200
BREAKING_ROLES = ("positive", "out_of_scope")


def _flagged(detect, v1: str, v2: str) -> bool:
    return len(detect(v1, v2)) > 0


def _tally(rows: list) -> dict:
    breaking = [c for c in rows if c[2] in BREAKING_ROLES]
    safe = [c for c in rows if c[2] not in BREAKING_ROLES]
    return {
        "cases": len(rows),
        "expected_breaking": len(breaking),
        "caught_by_baseline": sum(_flagged(baseline_detect, c[3], c[4]) for c in breaking),
        "caught_by_fixed": sum(_flagged(fixed_detect, c[3], c[4]) for c in breaking),
        "expected_not_breaking": len(safe),
        "false_positives_baseline": sum(_flagged(baseline_detect, c[3], c[4]) for c in safe),
        "false_positives_fixed": sum(_flagged(fixed_detect, c[3], c[4]) for c in safe),
    }


def _median_us(detect) -> float:
    samples = []
    for c in CASES:
        for _ in range(TIMING_REPEATS):
            start = time.perf_counter_ns()
            detect(c[3], c[4])
            samples.append(time.perf_counter_ns() - start)
    return round(statistics.median(samples) / 1000, 2)


def _baseline_commit() -> str:
    first = Path("versioning/_baseline_detector.py").read_text().splitlines()[0]
    return first.rsplit(" ", 1)[-1].rstrip(".")


def measure() -> dict:
    groups: dict[str, list] = defaultdict(list)
    for case in CASES:
        groups[case[1]].append(case)
    in_scope = [c for c in CASES if c[1] != "out_of_scope"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "label": "authored cases only; hand-labelled expected results; signature-level detection",
        "baseline_commit": _baseline_commit(),
        "python": platform.python_version(),
        "timing_repeats_per_case": TIMING_REPEATS,
        "per_class": {k: _tally(v) for k, v in groups.items() if k != "benign"},
        "benign": _tally(groups["benign"]),
        "overall_in_scope": _tally(in_scope),
        "median_runtime_us": {"baseline": _median_us(baseline_detect), "fixed": _median_us(fixed_detect)},
    }


def render(result: dict) -> str:
    head = f"{'class':<24}{'cases':>6}{'breaking':>9}{'baseline':>9}{'fixed':>7}{'FP base':>8}{'FP fixed':>9}"
    rows = [head, "-" * len(head)]
    entries = {**result["per_class"], "benign": result["benign"], "OVERALL (in scope)": result["overall_in_scope"]}
    for name, t in entries.items():
        rows.append(
            f"{name:<24}{t['cases']:>6}{t['expected_breaking']:>9}{t['caught_by_baseline']:>9}"
            f"{t['caught_by_fixed']:>7}{t['false_positives_baseline']:>8}{t['false_positives_fixed']:>9}"
        )
    rows.append(f"median runtime per run (us): {result['median_runtime_us']}")
    return "\n".join(rows)


def main() -> None:
    result = measure()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(render(result))


if __name__ == "__main__":
    main()
