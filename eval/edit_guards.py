"""The four guards, each run against a source tree (a dir holding `src/`, `tests/`)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from eval import replay, tag_env
from versioning import _baseline_detector, breaking_change_detector

REPO = Path(__file__).resolve().parents[1]
DETECTORS = {"baseline": _baseline_detector.detect, "fixed": breaking_change_detector.detect}
ALWAYS_SCANNED = ["src/harness_core/harness.py", "src/harness_core/schemas.py",
                  "src/harness_core/__init__.py"]
_FAILED = re.compile(r"^(FAILED|ERROR) (.+?)(?: - .*)?$", re.MULTILINE)
_SUMMARY = re.compile(r"(\d+) (failed|passed|skipped|error|errors|xfailed)")


def g1_signature(root: Path, edited_file: str, original: str, patched: str) -> dict:
    """Both detectors on original-vs-patched text of the edited file plus the three standard files."""
    out = {name: [] for name in DETECTORS}
    for path in dict.fromkeys([edited_file, *ALWAYS_SCANNED]):
        after = patched if path == edited_file else (root / path).read_text()
        before = original if path == edited_file else after
        for name, detect in DETECTORS.items():
            out[name] += [{"file": path, "kind": c.kind, "name": c.name} for c in detect(before, after)]
    return {"caught": any(out.values()), "baseline_changes": out["baseline"],
            "fixed_changes": out["fixed"]}


def import_ok(root: Path, file: str) -> tuple[bool, str]:
    module = file[len("src/"):-len(".py")].replace("/", ".")
    code = f"import harness_core, importlib; importlib.import_module({module!r})"
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-c", code], env=env, cwd=root, capture_output=True,
                          text=True, check=False)
    return proc.returncode == 0, proc.stderr.strip()[-300:]


def g2_compat(root: Path) -> dict:
    proc = tag_env.run_script(REPO / "scripts" / "compat_worker.py", [str(REPO)], root)
    if proc.returncode:
        return {"caught": True, "detail": f"worker exit {proc.returncode}: {proc.stderr.strip()[-300:]}"}
    rep = json.loads(proc.stdout.strip().splitlines()[-1])
    failing = [c["check"] for c in rep["checks"] if not c["passed"]]
    caught = bool(rep["import_error"] or failing or not rep["suite"]["passed"])
    return {"caught": caught, "import_error": rep["import_error"], "failing_checks": failing,
            "pass_count": rep["suite"]["pass_count"], "total": rep["suite"]["total"]}


def replay_items(items: list[dict], root: Path, work: Path, name: str) -> tuple[list | None, str]:
    in_path, out_path = work / f"{name}_in.json", work / f"{name}_out.json"
    in_path.write_text(json.dumps(items))
    proc = tag_env.run_script(REPO / "eval" / "replay_worker.py",
                              [str(in_path), str(out_path), "1.5.1"], root)
    if proc.returncode:
        return None, f"worker exit {proc.returncode}: {proc.stderr.strip()[-300:]}"
    return json.loads(out_path.read_text())["results"], ""


def g3_replay(base: list[dict], patched: list[dict] | None, why: str, categories: dict) -> dict:
    if patched is None:
        return {"caught": None, "detail": f"not measured: {why}"}
    cmp = replay.compare(base, patched, categories)
    flips = cmp["breakdown"]
    return {"caught": flips["flip_count"] > 0, "flip_count": flips["flip_count"],
            "paired": cmp["paired"], "errored_or_unpaired": cmp["unpaired_or_errored"],
            "by_category": flips["by_category"], "by_model": flips["by_model"],
            "by_changed_field": flips["by_changed_field"]}


def run_tests(root: Path, timeout: int = 600) -> dict:
    """The harness's own suite, run from `root`. Failing ids are None when it could not run."""
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1",
           "COLUMNS": "400"}
    cmd = [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run(cmd, env=env, cwd=root, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"ran": False, "reason": f"timeout after {timeout}s", "failing": None}
    last = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    failing = sorted({m.group(2) for m in _FAILED.finditer(proc.stdout)})
    if proc.returncode not in (0, 1) or not _SUMMARY.search(last):
        return {"ran": False, "reason": f"exit {proc.returncode}: {last or proc.stderr[-200:]}",
                "failing": None}
    return {"ran": True, "summary_line": last, "exit_code": proc.returncode, "failing": failing}


def g4_tests(result: dict, control_failing: set[str]) -> dict:
    if not result["ran"]:
        return {"caught": None, "detail": f"not measured: {result['reason']}"}
    new = sorted(set(result["failing"]) - control_failing)
    return {"caught": bool(new), "new_failing_tests": new, "summary_line": result["summary_line"]}
