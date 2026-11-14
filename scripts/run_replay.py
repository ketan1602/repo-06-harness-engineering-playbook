"""Replay stored raw model decisions through harness releases. No model call is made.

Usage: python3 scripts/run_replay.py   (paths via HARNESS_REPO and MEASUREMENTS_ROOT env vars)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import replay, replay_data, tag_env

TAGS = ["v1.4.0", "v1.5.0", "v1.5.1"]
CHANGELOG_CLAIMS = {
    "v1.5.0": "Additive; the changelog says nothing in 1.4.0 changes behaviour or public API.",
    "v1.5.1": ("Additive fix; same sentence about 1.4.0. Adds two strict normalisation rules, a "
               "fail-closed approval rule, first-JSON-object parsing, and recorded normalisations."),
}


NOTES = [
    ("Stored `decision` in 1.5.1-era files is POST-normalisation: live_model and the framework seam "
     "write the normalised choice into the trace, and `direct_decision` is normalised the same way. "
     "See stored_decision_provenance: records with applied rules never retain a prefixed tool name."),
    "1.5.0-era files have no `normalizations` field and 1.5.0 has no rules, so their decisions are raw.",
    ("Replayed: raw decisions only (1.5.0-era files; 1.5.1-era records with an empty normalizations "
     "list). Records with applied rules are excluded, never reconstructed."),
    ("Replay runs each tag's own live_model with the network client replaced by a fake; a mismatch "
     "between harness_core.__version__ and the tag aborts that tag."),
]


def datasets(root: Path) -> list[tuple[str, Path, str]]:
    p = root / "_unpublished"
    return [("first_pass_v1.5.0", p / "first_pass_v1.5.0/gateway_arm", replay_data.PRE_NORMALISATION),
            ("first_pass_v1.5.1", p / "first_pass_v1.5.1/gateway_arm", replay_data.RECORDS_NORMALISATION),
            ("published_v1.5.1", root / "gateway_arm", replay_data.RECORDS_NORMALISATION)]


def run_tag(harness: Path, tag: str, items: list[dict], work: Path) -> tuple[list[dict] | None, str]:
    src = work / tag
    if error := tag_env.extract(harness, tag, src):
        return None, f"extract failed: {error}"
    items_path, out_path = work / f"{tag}_in.json", work / f"{tag}_out.json"
    items_path.write_text(json.dumps(items))
    proc = tag_env.run_script(REPO / "eval" / "replay_worker.py",
                              [str(items_path), str(out_path), tag[1:]], src)
    if proc.returncode:
        return None, f"worker exit {proc.returncode}: {proc.stderr.strip()[-400:]}"
    return json.loads(out_path.read_text())["results"], ""


def main() -> None:
    harness = Path(os.environ["HARNESS_REPO"])
    root = Path(os.environ["MEASUREMENTS_ROOT"])
    items, excluded, provenance = [], {}, {}
    for name, path, mode in datasets(root):
        got, skipped = replay_data.load_dataset(name, path, mode)
        items += got
        excluded[name] = skipped
        provenance[name] = replay_data.provenance(path)
    cases = json.loads((harness / "src/harness_core/scenarios/support/cases.json").read_text())
    categories = {c["id"]: c["category"] for c in cases}
    results, tag_status = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for tag in TAGS:
            out, why = run_tag(harness, tag, items, Path(tmp))
            tag_status[tag] = "ran" if out is not None else f"not run: {why}"
            if out is not None:
                results[tag] = out
    comparisons = {}
    if "v1.5.0" in results and "v1.5.1" in results:
        comparisons["v1.5.0_to_v1.5.1"] = replay.compare(results["v1.5.0"], results["v1.5.1"], categories)
    doc = {"labels": "Cases are AUTHORED by the repo author; decisions are stored from past live runs.",
           "notes": NOTES, "stored_decision_provenance": provenance, "tag_status": tag_status, "stored_items_replayable": len(items),
           "exclusions_by_dataset_model_reason": excluded,
           "replayed_per_tag": {t: replay.count_by_model(r) for t, r in results.items()},
           "errors_per_tag": {t: sum("error" in x for x in r) for t, r in results.items()},
           "normalisation_per_tag": {t: replay.normalisation_counts(r) for t, r in results.items()},
           "comparisons": comparisons, "changelog_claimed": CHANGELOG_CLAIMS,
           "replay_measured_1_5_0_to_1_5_1": {k: comparisons[k]["breakdown"] for k in comparisons},
           "limits": ["Cases are authored by the repo author, not drawn from real traffic.",
                      "Decisions are held fixed, so prompt or context changes between releases are invisible.",
                      "Three to five models per dataset; see replayed_per_tag.",
                      "One day of recorded data (2026-10-23/24); replay is not a live run.",
                      "Replay goes through the plain-client path, not the five framework adapters."]}
    (REPO / "measurements" / "replay_across_versions.json").write_text(json.dumps(doc, indent=1))
    print(json.dumps({"tag_status": tag_status, "replayed": doc["replayed_per_tag"],
                      "flips": {k: v["breakdown"] for k, v in comparisons.items()}}, indent=1))


if __name__ == "__main__":
    main()
