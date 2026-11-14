"""Class-level model: methods, calling-convention decorators, bases, and synthesised constructors."""
from __future__ import annotations

import ast
from dataclasses import dataclass

from versioning.signature_model import EMPTY, Param, Sig, signature

FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)
CALL_STYLE = {"property", "staticmethod", "classmethod", "cached_property"}


@dataclass(frozen=True)
class ClassInfo:
    methods: dict[str, Sig]
    styles: dict[str, frozenset[str]]
    bases: tuple[str, ...]
    ctor: Sig


def visible_method(name: str) -> bool:
    return not name.startswith("_") or (name.startswith("__") and name.endswith("__"))


def _dec_name(node: ast.expr) -> str:
    node = node.func if isinstance(node, ast.Call) else node
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")


def _has_default(value: ast.expr | None) -> bool:
    if value is None:
        return False
    if isinstance(value, ast.Call) and _dec_name(value) in ("field", "Field"):
        keywords = {k.arg for k in value.keywords}
        ellipsis = bool(value.args) and isinstance(value.args[0], ast.Constant) and value.args[0].value is Ellipsis
        return bool({"default", "default_factory"} & keywords) or (bool(value.args) and not ellipsis)
    return True


def _fields(node: ast.ClassDef, kind: str) -> tuple[Param, ...]:
    return tuple(
        Param(item.target.id, kind, not _has_default(item.value))
        for item in node.body
        if isinstance(item, ast.AnnAssign)
        and isinstance(item.target, ast.Name)
        and not item.target.id.startswith("_")
        and "ClassVar" not in ast.unparse(item.annotation)
    )


def _synth_ctor(node: ast.ClassDef, bases: tuple[str, ...]) -> Sig | None:
    deco = next((d for d in node.decorator_list if _dec_name(d) == "dataclass"), None)
    if deco is not None:
        kw_only = isinstance(deco, ast.Call) and any(
            k.arg == "kw_only" and getattr(k.value, "value", False) is True for k in deco.keywords
        )
        return Sig(False, _fields(node, "kwonly" if kw_only else "normal"))
    if any(b.rsplit(".", 1)[-1] == "BaseModel" for b in bases):
        return Sig(False, _fields(node, "kwonly"))
    return None


def class_info(node: ast.ClassDef) -> ClassInfo:
    bases = tuple(ast.unparse(b) for b in node.bases)
    funcs = [i for i in node.body if isinstance(i, FUNCS) and visible_method(i.name)]
    methods = {f.name: signature(f, True) for f in funcs}
    styles = {f.name: frozenset(n for n in map(_dec_name, f.decorator_list) if n in CALL_STYLE) for f in funcs}
    ctor = methods.get("__init__") or _synth_ctor(node, bases) or EMPTY
    return ClassInfo(methods, styles, bases, ctor)
