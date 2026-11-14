# Exclusions and things that could not run

All cases are AUTHORED by the repo author. Stored model decisions come from past live runs
(repo-03 measurements); no model was called here.

## Replay (measurements/replay_across_versions.json)

- Stored decisions in 1.5.1-era files are post-normalisation. Records with a non-empty
  `normalizations` list are excluded (counts per dataset and model are in the JSON under
  `exclusions_by_dataset_model_reason`, reason `post_normalisation`). They are not reconstructed.
- Records with no stored decision (`no_decision`) are excluded; counts are in the same field.
- 1.5.0-era files carry no `normalizations` field; 1.5.0 has no rules, so those decisions are raw.
- v1.4.0 was not replayed: the tag has no `harness_core.scenarios` package (the 16-case scenario and
  `run_harnessed` first appear in 1.5.0), so the replay worker fails at import. The JSON records the
  exact error under `tag_status`.
- Replay uses the plain-client path (the tag's own `live_model` with the network client faked), not the
  five framework adapters. Each stored framework decision is replayed, but not through its adapter.

## Release history (measurements/release_history.json)

- Nothing excluded: all seven tags extracted, imported and ran the suite (harness_core.__version__
  matched each tag). Detectors ran on harness.py, schemas.py and __init__.py only; every file exists
  at every tag. The suite checks only the v1.0 export/signature surface, so it cannot see
  behaviour changes (for example the 1.4.0 fail-open fix in ToolRegistry, or the 1.5.1 normalisation).

## Curated edit experiment (measurements/edit_experiment.json)

- G4 (the harness's own tests) was run exactly as specified except that `-x` was dropped. On
  unpatched v1.5.1 the control itself fails 92 tests (91 in `tests/kit/test_frameworks.py` and
  `test_gateway_arm.py`, 1 in `test_probes.py`; both control runs fail the same 92), so stopping at the
  first failure would make failing-test comparison meaningless. Causes seen on the control:
  `ModuleNotFoundError: No module named 'langchain_openai'` (optional extra not installed) and
  `ImportError: cannot import name 'Agent' from 'agents'` (the `openai-agents` extra is not installed and a
  different `agents` package from repo-05 shadows it on this machine). An edit counts as caught by G4
  only through failing test ids outside the union of both control runs.
- The harness `pyproject.toml` is copied alongside `src` and `tests` into each temp tree, because it holds
  the harness's `asyncio_mode = "auto"`; without it 380 async tests fail on the control for a config reason.
- Records excluded from replay are the same as in the replay section above. The replayed raw decisions
  contain no `suspended_agent` item, no string refund amounts, no tool name with a dot, and over-budget
  items all carry the same token value; see `replay_coverage` in the JSON. Edits on those paths cannot flip.
- Nothing else could not run: every edit imported, and all four guards ran for every edit.
