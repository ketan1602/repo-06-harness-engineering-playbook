# Harness Engineering Team Runbook

## On-Call Scope

The Harness Engineering on-call owns:
- `agent-harness-core` package stability and versioning
- CI pipeline for breaking-change detection
- Compatibility suite pass rate across all agent repos
- Upgrade coordination when a new major version ships

## Alert: Compatibility Suite Failure

**Signal**: CI job `compatibility-check` fails on a downstream agent repo after a harness release.

**Steps**:
1. Run `python -c "from compatibility.suite import run; import json; print(json.dumps(run(), indent=2))"`
2. Identify failing checks (`"passed": false` entries)
3. Determine if this is a breaking change (major bump needed) or a missing re-export (patch)
4. If breaking: open a migration guide PR before merging the harness change
5. If missing re-export: add to `harness_core/__init__.py` and `__all__`

## Alert: Breaking-Change Detector Regression

**Signal**: `test_breaking_changes.py` fails in `repo-06`.

**Steps**:
1. Read the failing test — it names the exact case
2. Run `pytest tests/test_breaking_changes.py -v` locally
3. Check `versioning/breaking_change_detector.py` for the regression
4. Fix the AST parsing logic; all 8 test cases must pass before merging

## Upgrade Process (New Major Version)

1. Update `specification/harness-spec-v1.0.md` → new spec file for the new major
2. Run the detector against v(N-1) → vN to enumerate all breaking changes
3. Write migration guide from `migration/template.md`
4. Notify all downstream repo owners with the guide link
5. Give 2-week migration window before deprecating the old version
6. Monitor compatibility suite pass rate daily during migration window
