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
