# Frozen baseline snapshot of versioning/breaking_change_detector.py at commit 429d5440596c56269db12b26f3e37b53dfe08dda.
# Used only as the "before" side of measurements/detector_before_after.json. Do not edit.
"""Detects breaking changes between two harness API surfaces.

A breaking change is:
- Removal of a name from the public API
- Removal or renaming of positional parameters in a function/method
- Removal of a public method from a class
"""
from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass
class BreakingChange:
    kind: str
    name: str
    detail: str


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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)
    return names


def _func_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = func.args
    all_args = args.posonlyargs + args.args + args.kwonlyargs
    return [a.arg for a in all_args if a.arg not in ("self", "cls")]


def _top_level_funcs(tree: ast.Module) -> dict[str, list[str]]:
    return {
        node.name: _func_params(node)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def _class_methods(tree: ast.Module) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = {
                item.name: _func_params(item)
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not item.name.startswith("_")
            }
            result[node.name] = methods
    return result


def _check_signature(name: str, v1_params: list[str], v2_params: list[str]) -> BreakingChange | None:
    removed = [p for p in v1_params if p not in v2_params]
    if removed:
        return BreakingChange("changed_signature", name, f"Parameters removed from '{name}': {removed}")
    return None


def detect(v1_source: str, v2_source: str) -> list[BreakingChange]:
    """Compare two Python source strings and return all breaking changes found."""
    try:
        v1 = ast.parse(v1_source)
        v2 = ast.parse(v2_source)
    except SyntaxError as exc:
        return [BreakingChange("parse_error", "", str(exc))]

    changes: list[BreakingChange] = []

    v1_names = _public_names(v1)
    v2_names = _public_names(v2)
    for name in sorted(v1_names - v2_names):
        changes.append(BreakingChange("removed_name", name, f"'{name}' removed from public API"))

    v1_funcs = _top_level_funcs(v1)
    v2_funcs = _top_level_funcs(v2)
    for name, params in v1_funcs.items():
        if name in v2_funcs and (change := _check_signature(name, params, v2_funcs[name])):
            changes.append(change)

    v1_classes = _class_methods(v1)
    v2_classes = _class_methods(v2)
    for cls, methods in v1_classes.items():
        if cls not in v2_classes:
            continue
        v2_methods = v2_classes[cls]
        for method, params in methods.items():
            if method not in v2_methods:
                changes.append(BreakingChange(
                    "removed_method", f"{cls}.{method}",
                    f"Method '{method}' removed from class '{cls}'",
                ))
            elif change := _check_signature(f"{cls}.{method}", params, v2_methods[method]):
                changes.append(change)

    return changes
