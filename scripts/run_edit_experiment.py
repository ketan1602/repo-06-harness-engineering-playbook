"""Which guard catches which curated harness edit? No model call.

Usage: HARNESS_REPO=<checkout> MEASUREMENTS_ROOT=<repo-03 measurements> python scripts/run_edit_experiment.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import edit_experiment, replay_data
from scripts.run_replay import datasets


def main() -> None:
    harness, root = Path(os.environ["HARNESS_REPO"]), Path(os.environ["MEASUREMENTS_ROOT"])
    items = []
    for name, path, mode in datasets(root):
        items += replay_data.load_dataset(name, path, mode)[0]
    doc = edit_experiment.run(harness, items, REPO / "measurements" / "edit_experiment.json")
    print(json.dumps(doc["summary"]["intended_change_edits_caught"], indent=1))
    print(json.dumps(doc["summary"]["benign_edits_false_alarms"], indent=1))
    print("no-edit control:", json.dumps({k: v.get("caught") for k, v in doc["no_edit_control"].items()}))


if __name__ == "__main__":
    main()
