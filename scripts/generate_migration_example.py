"""Regenerate the detector-output block of migration/v1-to-v2-example.md from the real detector.

The v1/v2 sources are HYPOTHETICAL API surfaces mirroring the example document.
Run: python -m scripts.generate_migration_example
"""
from __future__ import annotations

from pathlib import Path

from versioning.breaking_change_detector import detect

DOC = Path("migration/v1-to-v2-example.md")
START, END = "<!-- DETECTOR-OUTPUT:START -->", "<!-- DETECTOR-OUTPUT:END -->"

V1 = (
    '__all__ = ["HarnessConfig", "with_retry"]\n'
    "class HarnessConfig: pass\n"
    "async def with_retry(fn, *args): pass\n"
)
V2 = (
    '__all__ = ["HarnessSettings", "with_retry"]\n'
    "class HarnessSettings: pass\n"
    "async def with_retry(fn, policy, *args): pass\n"
)


def render() -> str:
    lines = [f"{c.kind}: {c.detail}" for c in detect(V1, V2)]
    return f"{START}\n```\n" + "\n".join(lines) + f"\n```\n{END}"


def main() -> None:
    text = DOC.read_text()
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    DOC.write_text(head + render() + tail)


if __name__ == "__main__":
    main()
