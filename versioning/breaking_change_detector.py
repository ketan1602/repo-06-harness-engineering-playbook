"""Detects breaking changes between two harness API surfaces (stdlib only).

A change is breaking if it makes an existing, correct caller fail. Signature level only:
removed names/methods/params, added required params, optional->required, positional reorder,
constructor changes (explicit, dataclass or pydantic), async<->sync flips, keyword-only/
positional-only narrowing, calling-convention decorators, and removed base classes.
"""
from __future__ import annotations

import ast

from versioning.class_model import FUNCS, ClassInfo, class_info
from versioning.signature_model import BreakingChange, Sig, compare, signature

__all__ = ["BreakingChange", "detect"]


def _public_names(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(node.value, ast.List | ast.Tuple):
                    return {
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    }
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (*FUNCS, ast.ClassDef)) and not node.name.startswith("_"):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith("_"))
    return names


def _top_level_funcs(tree: ast.Module) -> dict[str, Sig]:
    return {
        node.name: signature(node, False)
        for node in tree.body
        if isinstance(node, FUNCS) and not node.name.startswith("_")
    }


def _classes(tree: ast.Module) -> dict[str, ClassInfo]:
    return {
        node.name: class_info(node)
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    }


def _method_changes(cls: str, old: ClassInfo, new: ClassInfo) -> list[BreakingChange]:
    changes: list[BreakingChange] = []
    for method, sig in old.methods.items():
        name = f"{cls}.{method}"
        if method == "__init__":
            continue
        if method not in new.methods:
            changes.append(BreakingChange("removed_method", name, f"Method '{method}' removed from class '{cls}'"))
            continue
        changes += compare(name, sig, new.methods[method])
        before, after = sorted(old.styles[method]), sorted(new.styles[method])
        if before != after:
            changes.append(BreakingChange("decorator_change", name, f"Calling convention changed for '{name}': {before} -> {after}"))
    return changes


def _compare_class(cls: str, old: ClassInfo, new: ClassInfo) -> list[BreakingChange]:
    changes = _method_changes(cls, old, new)
    lost = [b for b in old.bases if b not in new.bases]
    if lost:
        changes.append(BreakingChange("base_removed", cls, f"Base classes removed from '{cls}': {lost}"))
    return changes + compare(f"{cls}.__init__", old.ctor, new.ctor, "ctor_change")


def detect(v1_source: str, v2_source: str) -> list[BreakingChange]:
    """Compare two Python source strings and return all breaking changes found."""
    try:
        v1, v2 = ast.parse(v1_source), ast.parse(v2_source)
    except SyntaxError as exc:
        return [BreakingChange("parse_error", "", str(exc))]

    changes = [
        BreakingChange("removed_name", name, f"'{name}' removed from public API")
        for name in sorted(_public_names(v1) - _public_names(v2))
    ]
    funcs2 = _top_level_funcs(v2)
    for name, sig in _top_level_funcs(v1).items():
        if name in funcs2:
            changes += compare(name, sig, funcs2[name])
    classes2 = _classes(v2)
    for cls, info in _classes(v1).items():
        if cls in classes2:
            changes += _compare_class(cls, info, classes2[cls])
    return changes
