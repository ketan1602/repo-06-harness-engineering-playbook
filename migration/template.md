# Migration Guide Template: vX.Y → vA.B

## Breaking Changes

List each breaking change with its detection signal (ruff rule, CI check, runtime error):

| Change | Affected Call Sites | Migration Step |
|---|---|---|
| Removed: `FunctionName` | `grep -r "FunctionName" .` | Replace with `NewName(...)` |
| Removed param: `old_param` from `ClassName.method` | `grep -r "old_param" .` | Remove argument |

## Step-by-Step Migration

1. Update `pyproject.toml` pin: `agent-harness-core @ ...@vA.B`
2. Run `pip install -e .` to pull the new version
3. Run the compatibility suite: `python -c "from compatibility.suite import run; print(run())"`
4. Fix each failing check per the table above
5. Run `pytest tests/ -v` — must pass with zero failures
6. Run `ruff check .` — must be clean

## Rollback

Pin back to `vX.Y` in `pyproject.toml` and reinstall. No data migration required.
