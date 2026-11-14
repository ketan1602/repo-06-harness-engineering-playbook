# Breaking-Change Detection Scenarios

This document describes what the CURRENT detector (`versioning/breaking_change_detector.py`, with
`signature_model.py` and `class_model.py`) reports. Every example is an AUTHORED case from `eval/cases.py`,
written by the repo author, with hand-labelled expected results. None is real-world evidence.

Definition (from `specification/harness-spec-v1.0.md`): a change is breaking if it causes any existing, correct caller to fail.
Scope: signature-level, stdlib `ast` only. Reproduce the measurement with `python -m eval.before_after`
(output: `measurements/detector_before_after.json`).

## Authored cases per change class

"Positive" cases must be reported; "negative" cases are a safe variant of the same class and must not be reported.

| Class (expected kind) | Positive case ids (authored) | Negative case ids (authored) | Rationale |
|---|---|---|---|
| `removed_name` | `removed_name_pos` | `removed_name_neg` | Removing a name from `__all__` breaks `import`; adding one is additive. |
| `removed_method` | `removed_method_pos` | `removed_method_neg` | Callers of the removed method get `AttributeError`; a new method breaks nobody. |
| `changed_signature` | `removed_param_pos` | `removed_param_neg` | A caller passing a removed parameter gets `TypeError`; appending an optional parameter is safe. |
| `required_param_added` | `req_added_pos_func`, `req_added_pos_kwonly` | `req_added_neg_optional` | Existing callers do not supply the new required argument. Detected directly. |
| `optional_to_required` | `opt_to_req_pos`, `opt_to_req_pos_kwonly` | `opt_to_req_neg` | Callers relying on the default now fail; the reverse (required to optional) is safe. |
| `positional_reorder` | `reorder_pos`, `reorder_pos_insert` | `reorder_neg_kwonly`, `reorder_neg_append` | Positional callers silently bind to the wrong parameter, including when a parameter is inserted before existing positional ones. Reordering keyword-only parameters and appending an optional parameter are safe. |
| `ctor_change` | `ctor_pos_required`, `ctor_pos_removed_param`, `ctor_pos_new_init` | `ctor_neg_optional` | Constructor calls fail when `__init__` gains a required parameter, loses one, or a new explicit `__init__` replaces the default one. |
| `async_flip` | `async_pos_to_async`, `async_pos_to_sync` | `async_neg_unchanged` | `await` on a sync result, or a missing `await` on a coroutine, fails callers. |
| `kwonly_posonly_change` | `kwonly_pos_narrow`, `kwonly_pos_posonly` | `kwonly_neg_widen` | Making a parameter keyword-only or positional-only rejects existing call styles; widening is safe. |
| `decorator_change` | `deco_pos_to_property`, `deco_pos_to_static` | `deco_neg_unchanged` | `property`, `staticmethod`, `classmethod`, `cached_property` change the calling convention. |
| `base_removed` | `base_pos_removed` | `base_neg_added` | Removing a base class (textual, same-file) drops inherited members and `isinstance` behaviour. |
| `ctor_change` via synthesised constructors | `dc_pos_required_field`, `dc_pos_field_removed`, `dc_pos_field_reorder`, `pyd_pos_required_field` | `dc_neg_default_field`, `dc_neg_default_factory`, `pyd_neg_optional_field`, `pyd_neg_field_order` | Dataclass and pydantic `BaseModel` fields define the constructor. Pydantic accepts keywords only, so field order is not breaking there; dataclass field order is. |

Parse errors: the detector is documented to return a structured `parse_error` result for unparseable source instead of raising. No case in `eval/cases.py` exercises it; `tests/test_breaking_changes.py::test_syntax_error_returns_parse_error` does.

## Benign edits (authored, must not be reported)

`benign_docstring`, `benign_comment`, `benign_body_change`, `benign_private_func`, `benign_private_method`,
`benign_private_class`, `benign_new_export`, `benign_new_function`, `benign_new_method`, `benign_annotation_only`,
`benign_add_varargs`, `benign_reformat`. These are changes that cannot make a correct caller fail.

## Out of scope BY DESIGN (breaking, not detected)

| Case id (authored) | Change | Why it is invisible |
|---|---|---|
| `oos_default_value_change` | `def f(a, b=1)` to `def f(a, b=2)` | Signature shape is identical; only behaviour differs. |
| `oos_raises_new_exception` | body now raises `ValueError` | Behavioural change; the signature is unchanged. |

Also not covered: imported base classes (only same-file bases are compared), return and annotation semantics, runtime-generated APIs.
These are expected misses; `measurements/detector_before_after.json` records both out-of-scope cases as caught by neither detector.
Catching them needs behavioural conformance (the ENG-05 principle), not a structural guard.

## Results on these authored cases

From `measurements/detector_before_after.json` (51 in-scope cases, 23 expected breaking):

- Baseline detector (frozen original, `versioning/_baseline_detector.py`): 3 of 23 caught, 0 false positives.
- Fixed detector: 23 of 23 caught, 0 false positives.

The fixed detector's 23/23 is partly circular: the same author wrote the fix and the cases. The baseline's 3/23 on the same cases is the informative number.
