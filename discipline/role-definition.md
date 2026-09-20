# Harness Engineer — Role Definition

## What This Role Is

The Harness Engineer is a platform engineering role, not an agent author role.
They own the infrastructure that all agent teams depend on.

## Responsibilities

| Responsibility | Description |
|---|---|
| **Version governance** | Maintain semver discipline; no breaking changes without a major bump and migration guide |
| **Compatibility suite** | Keep the suite passing across all downstream repos; own the CI gate |
| **Breaking-change detection** | Own and improve `breaking_change_detector.py`; add new check types as the API grows |
| **Migration support** | Write migration guides for every major version; support downstream teams during the window |
| **On-call** | Own `harness-engineering-playbook` incidents; runbook in `runbook_docs/` |
| **Spec authorship** | Maintain `specification/harness-spec-vN.md`; the spec is the contract |

## What This Role Is NOT

- Not responsible for agent business logic
- Not responsible for LLM prompt engineering
- Not responsible for individual agent performance

## Success Metrics

- Compatibility suite pass rate: **100%** across all downstream repos
- Breaking change detection time: **< 5 minutes** (CI gate)
- Upgrade success rate: **> 95%** of downstream repos on current major within migration window
- Zero breaking changes reaching production undetected

## Relationship to Agent Teams

The Harness Engineer is a service provider to agent teams.
Agent teams are customers of the harness API contract.
When the contract changes, the Harness Engineer owns the migration — not the agent teams.
