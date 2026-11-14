"""Apply and revert one exact find/replace on source text or on a source tree."""
from __future__ import annotations

from pathlib import Path


def apply_edit(source: str, find: str, replace: str) -> str:
    """Source with `find` replaced once. Raises ValueError unless `find` occurs exactly once."""
    count = source.count(find)
    if count != 1:
        raise ValueError(f"find must match exactly once, matched {count} times")
    return source.replace(find, replace)


def revert_edit(patched: str, find: str, replace: str) -> str:
    """Inverse of apply_edit; same exactly-once rule applied to `replace`."""
    if not replace:
        raise ValueError("cannot revert an edit whose replacement is empty")
    return apply_edit(patched, replace, find)


def patch_file(root: Path, edit: dict) -> tuple[str, str]:
    """Patch root/<edit file> in place. Returns (original, patched) text."""
    path = root / edit["file"]
    original = path.read_text()
    patched = apply_edit(original, edit["find"], edit["replace"])
    path.write_text(patched)
    return original, patched
