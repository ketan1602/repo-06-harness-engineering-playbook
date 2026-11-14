"""Subprocess worker: run this repo's compatibility suite against whichever harness_core is first
on PYTHONPATH and print one JSON object. Stdlib + this repo only.

Usage: compat_worker.py <repo_root>
"""
from __future__ import annotations

import json
import sys


def main(repo_root: str) -> int:
    sys.path.append(repo_root)  # appended: the tag's src stays first, so its harness_core wins
    report: dict = {"harness_version": None, "import_error": None}
    try:
        import harness_core
        report["harness_version"] = getattr(harness_core, "__version__", None)
        report["harness_file"] = harness_core.__file__
    except Exception as exc:  # noqa: BLE001 - the exact import error is the datum
        report["import_error"] = f"{type(exc).__name__}: {exc}"
    from compatibility.suite import run
    result = run()
    report["suite"] = {k: result.get(k) for k in ("passed", "pass_count", "total", "error")}
    report["checks"] = result["checks"]
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
