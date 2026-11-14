"""Signature model and comparison rules for the breaking-change detector (stdlib only)."""
from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

POSITIONAL = ("posonly", "normal")
NARROWING = {("normal", "kwonly"), ("normal", "posonly"), ("kwonly", "posonly"), ("posonly", "kwonly")}


@dataclass
class BreakingChange:
    kind: str
    name: str
    detail: str


@dataclass(frozen=True)
class Param:
    name: str
    kind: str
    required: bool


@dataclass(frozen=True)
class Sig:
    is_async: bool
    params: tuple[Param, ...]


EMPTY = Sig(False, ())


def _params(args: ast.arguments) -> list[Param]:
    positional = [*args.posonlyargs, *args.args]
    first_default = len(positional) - len(args.defaults)
    out = [
        Param(a.arg, "posonly" if i < len(args.posonlyargs) else "normal", i < first_default)
        for i, a in enumerate(positional)
    ]
    if args.vararg:
        out.append(Param("*" + args.vararg.arg, "vararg", False))
    out += [Param(a.arg, "kwonly", d is None) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True)]
    if args.kwarg:
        out.append(Param("**" + args.kwarg.arg, "varkw", False))
    return out


def signature(func: ast.FunctionDef | ast.AsyncFunctionDef, in_class: bool) -> Sig:
    params = _params(func.args)
    static = any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in func.decorator_list)
    if in_class and not static and params and params[0].kind in POSITIONAL:
        params = params[1:]
    return Sig(isinstance(func, ast.AsyncFunctionDef), tuple(params))


def _by_name(sig: Sig) -> dict[str, Param]:
    return {p.name: p for p in sig.params}


def _removed(a: Sig, b: Sig) -> str:
    kept, has_varkw = _by_name(b), any(p.kind == "varkw" for p in b.params)
    gone = [p.name for p in a.params if p.name not in kept and not (p.kind == "kwonly" and has_varkw)]
    return str(gone) if gone else ""


def _required_added(a: Sig, b: Sig) -> str:
    old = _by_name(a)
    new = [p.name for p in b.params if p.name not in old and p.required]
    return str(new) if new else ""


def _optional_to_required(a: Sig, b: Sig) -> str:
    new = _by_name(b)
    hit = [p.name for p in a.params if p.name in new and not p.required and new[p.name].required]
    return str(hit) if hit else ""


def _reorder(a: Sig, b: Sig) -> str:
    pa = [p.name for p in a.params if p.kind in POSITIONAL]
    pb = [p.name for p in b.params if p.kind in POSITIONAL]
    common = set(pa) & set(pb)
    ra, rb = [n for n in pa if n in common], [n for n in pb if n in common]
    if ra != rb:
        return f"{ra} -> {rb}"
    last = max((i for i, n in enumerate(pb) if n in common), default=-1)
    shifted = [n for i, n in enumerate(pb) if n not in common and i < last]
    return f"inserted before existing parameters: {shifted}" if shifted else ""


def _async_flip(a: Sig, b: Sig) -> str:
    mode = {True: "async", False: "sync"}
    return f"{mode[a.is_async]} -> {mode[b.is_async]}" if a.is_async != b.is_async else ""


def _kind_change(a: Sig, b: Sig) -> str:
    new = _by_name(b)
    hit = [
        f"{p.name}: {p.kind}->{new[p.name].kind}"
        for p in a.params
        if p.name in new and (p.kind, new[p.name].kind) in NARROWING
    ]
    return str(hit) if hit else ""


RULES: dict[str, tuple[str, Callable[[Sig, Sig], str]]] = {
    "changed_signature": ("Parameters removed from", _removed),
    "required_param_added": ("Required parameters added to", _required_added),
    "optional_to_required": ("Optional parameters made required in", _optional_to_required),
    "positional_reorder": ("Positional order changed in", _reorder),
    "async_flip": ("Sync/async changed for", _async_flip),
    "kwonly_posonly_change": ("Parameter kind narrowed in", _kind_change),
}


def compare(name: str, a: Sig, b: Sig, kind: str | None = None) -> list[BreakingChange]:
    """Apply every rule; `kind` overrides the emitted kind (used for constructors)."""
    found = []
    for rule_kind, (label, rule) in RULES.items():
        payload = rule(a, b)
        if payload:
            found.append(BreakingChange(kind or rule_kind, name, f"{label} '{name}': {payload}"))
    return found
