"""Real release-history check from local git: compatibility suite and both detectors per tag.

Usage: HARNESS_REPO=<checkout> python3 scripts/run_release_history.py. No model, no network.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import tag_env
from versioning import _baseline_detector, breaking_change_detector

TAGS = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v1.4.0", "v1.5.0", "v1.5.1"]
FILES = ["src/harness_core/harness.py", "src/harness_core/schemas.py", "src/harness_core/__init__.py"]
# Paraphrased from the harness CHANGELOG.md, read-only.
CHANGELOG = {
    "v1.1.0": ("unspecified", "Changelog says entries for 1.1.0 to 1.3.0 were not recorded."),
    "v1.2.0": ("unspecified", "Changelog says entries for 1.1.0 to 1.3.0 were not recorded."),
    "v1.3.0": ("unspecified", "Changelog says entries for 1.1.0 to 1.3.0 were not recorded."),
    "v1.4.0": ("breaking", "Marks one change Breaking (LLM evaluator env vars) and one Behaviour "
                           "change (empty allowed_tools list no longer allows everything)."),
    "v1.5.0": ("additive", "Described as additive; says nothing in 1.4.0 changes behaviour or API."),
    "v1.5.1": ("additive", "Described as an additive fix; same statement about 1.4.0."),
}
DETECTORS = {"baseline": _baseline_detector.detect, "fixed": breaking_change_detector.detect}


SOURCE_DIFF_NOTES = {
    "v1.3.0->v1.4.0": (
        "Fixed-detector change checked against `git diff v1.3.0 v1.4.0` on schemas.py: a defaulted "
        "field `eval_result` was inserted in the HarnessResult dataclass before `trace_id` and "
        "`span_id`, so a caller passing those two positionally would bind them to the wrong "
        "parameters. The change is real at signature level; the changelog does not mention it, and "
        "its own Breaking/Behaviour entries (evaluator env vars, empty allowed_tools) live in files "
        "these detectors were not given."),
}


def compat(harness: Path, tag: str, work: Path) -> dict:
    src = work / tag
    if error := tag_env.extract(harness, tag, src):
        return {"error": f"extract failed: {error}"}
    proc = tag_env.run_script(REPO / "scripts" / "compat_worker.py", [str(REPO)], src)
    if proc.returncode:
        return {"error": f"worker exit {proc.returncode}: {proc.stderr.strip()[-600:]}"}
    return json.loads(proc.stdout.strip().splitlines()[-1])


def detect_pair(harness: Path, old: str, new: str) -> dict:
    out: dict = {name: {"changes": 0, "items": []} for name in DETECTORS}
    out["files_skipped"] = []
    for path in FILES:
        before, after = tag_env.show(harness, old, path), tag_env.show(harness, new, path)
        if before is None or after is None:
            out["files_skipped"].append(path)
            continue
        for name, detect in DETECTORS.items():
            for c in detect(before, after):
                out[name]["items"].append({"file": path, "kind": c.kind, "name": c.name,
                                           "detail": c.detail})
    for name in DETECTORS:
        out[name]["changes"] = len(out[name]["items"])
    return out


def main() -> None:
    harness = Path(os.environ["HARNESS_REPO"])
    with tempfile.TemporaryDirectory() as tmp:
        per_tag = {tag: compat(harness, tag, Path(tmp)) for tag in TAGS}
    pairs = {}
    for old, new in zip(TAGS, TAGS[1:], strict=False):
        kind, text = CHANGELOG[new]
        pairs[f"{old}->{new}"] = {"changelog_says": kind, "changelog_paraphrase": text,
                                  **detect_pair(harness, old, new)}
    doc = {"labels": "Real release tags from local git; no model call. Detectors see signatures "
                     "of three files only (harness.py, schemas.py, __init__.py).",
           "compatibility_suite_per_tag": per_tag, "detector_per_release_pair": pairs,
           "source_diff_notes": SOURCE_DIFF_NOTES}
    (REPO / "measurements" / "release_history.json").write_text(json.dumps(doc, indent=1))
    for tag, r in per_tag.items():
        print(tag, r.get("error") or r["import_error"] or r["suite"])
    for pair, r in pairs.items():
        print(pair, r["changelog_says"], "baseline", r["baseline"]["changes"], "fixed", r["fixed"]["changes"])


if __name__ == "__main__":
    main()
