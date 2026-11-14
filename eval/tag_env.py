"""Extract a harness release from git and run a script against exactly that release."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def extract(harness: Path, tag: str, dest: Path) -> str:
    """Unpack `src` of a tag under dest (never touches the checkout). Returns '' or an error."""
    dest.mkdir(parents=True)
    archive = subprocess.Popen(["git", "-C", str(harness), "archive", tag, "src"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    untar = subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive.stdout,
                           capture_output=True, check=False)
    err = archive.stderr.read().decode().strip()
    archive.wait()
    if archive.returncode or untar.returncode:
        return err or untar.stderr.decode().strip() or "git archive | tar failed"
    return ""


def run_script(script: Path, args: list[str], src_root: Path) -> subprocess.CompletedProcess:
    """Run a script in a subprocess whose first PYTHONPATH entry is the tag's src directory."""
    env = {**os.environ, "PYTHONPATH": str(src_root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, str(script), *args], env=env, cwd=src_root,
                          capture_output=True, text=True, check=False)


def show(harness: Path, tag: str, path: str) -> str | None:
    """File text at a tag via `git show`, or None when the path does not exist there."""
    out = subprocess.run(["git", "-C", str(harness), "show", f"{tag}:{path}"],
                         capture_output=True, text=True, check=False)
    return out.stdout if out.returncode == 0 else None
