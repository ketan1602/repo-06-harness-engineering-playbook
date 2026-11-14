"""Detects breaking changes between two harness API surfaces (stdlib only).

A change is breaking if it makes an existing, correct caller fail. Signature level only:
removed names/methods/params, added required params, optional->required, positional reorder,
constructor changes, async<->sync flips, and keyword-only/positional-only narrowing.
"""
from __future__ import annotations

import ast

from versioning.signature_model import EMPTY, BreakingChange, Sig, compare, signature

__all__ = ["BreakingChange", "detect"]

FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


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


def _visible_method(name: str) -> bool:
    return not name.startswith("_") or (name.startswith("__") and name.endswith("__"))


def _top_level_funcs(tree: ast.Module) -> dict[str, Sig]:
    return {
        node.name: signature(node, False)
        for node in tree.body
        if isinstance(node, FUNCS) and not node.name.startswith("_")
    }


def _class_methods(tree: ast.Module) -> dict[str, dict[str, Sig]]:
    return {
        node.name: {
            item.name: signature(item, True)
            for item in node.body
            if isinstance(item, FUNCS) and _visible_method(item.name)
        }
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    }


def _compare_class(cls: str, old: dict[str, Sig], new: dict[str, Sig]) -> list[BreakingChange]:
    changes = []
    for method, sig in old.items():
        if method == "__init__":
            continue
        if method not in new:
            changes.append(BreakingChange(
                "removed_method", f"{cls}.{method}", f"Method '{method}' removed from class '{cls}'",
            ))
        else:
            changes += compare(f"{cls}.{method}", sig, new[method])
    if "__init__" in old or "__init__" in new:
        changes += compare(f"{cls}.__init__", old.get("__init__", EMPTY), new.get("__init__", EMPTY), "ctor_change")
    return changes


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
    classes2 = _class_methods(v2)
    for cls, methods in _class_methods(v1).items():
        if cls in classes2:
            changes += _compare_class(cls, methods, classes2[cls])
    return changes
