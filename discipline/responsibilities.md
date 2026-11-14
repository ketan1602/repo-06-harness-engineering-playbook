# Responsibility Ledger

The seven responsibilities of harness engineering (ENG-09), where each was established, and how strong the evidence is.
Evidence is stated conservatively. Every demonstration in this series runs on authored cases written by the repo author.

Evidence levels:

- **L1** argument: reasoned case, no executable demonstration
- **L2** demo on authored cases: runs, but cases are written by the same author as the solution
- **L3** unanticipated cases with real models: cases the author did not write, run against real models
- **L4** field data: observed in real use

| Responsibility | Established in | Evidence level | Still open |
|---|---|---|---|
| Specify | ENG-05; this repo's spec (`specification/harness-spec-v1.0.md`) | L2 at most (spec checked by an authored compatibility suite) | Unanticipated failures |
| Enforce outside the agent | ENG-04 / ENG-05 | L2 at most (not re-verified here) | Enforcement vs reporting |
| Prove via behavioural conformance | ENG-05 | L2 at most (not re-verified here) | Scale |
| Keep swappable | ENG-06 | L2 at most (not re-verified here) | Other frameworks |
| Price | ENG-07 | L2 at most (not re-verified here) | Real cost data |
| Roll out across a fleet | ENG-08 (repo-05 control plane) | L1/L2: rollout confirmations were simulated; repo-05's `measurements/fleet_metrics.json` has every measurement field at 0 (only `agents_in_fleet` is 7) | Drift in production |
| Evolve: version, detect, migrate | This repo (ENG-09) | L2: authored cases, signature-level detection only | Behavioural regression across releases |

Notes:

- No row reaches L3 or L4. This ledger makes no claim beyond what the named articles and repos support.
- Articles and repos are referenced by name only (ENG-04 to ENG-08, repo-05, this repo).
