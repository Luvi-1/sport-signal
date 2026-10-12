# Production boundaries and monitoring design

This repository applies production-style habits to a research system. It is not
a production service, has no uptime guarantee, and has not been validated for
live operational decisions. There are no automated account actions or wagers.

## Already implemented

- Narrow provider adapters, deterministic schemas, provenance hashes and source locks
- Result-availability guards, same-day batching, suspended-match and tournament handling
- Train-only transformations and model selection; separate calibration and holdout
- Versioned local artifacts, seeded runs and full candidate-result reporting
- Offline unit, leakage and end-to-end save/load/inference tests; GitHub Actions definition
- Unknown-participant and pre-calibration-date rejection; stale-data and missing-rank warnings
- Explicit license/attribution separation; raw datasets and checkpoints excluded from Git

## Required before a live pilot

1. Secure rights for the intended use, particularly tennis's non-commercial data
2. Use a versioned, timestamped feed for schedules, corrected results and pre-event
   context. Record ingestion time and event completion time separately
3. Build incremental idempotent ingestion with reconciliation and publication-lag
   checks. Do not silently accept changed historical hashes
4. Evaluate prospectively in shadow mode. Define thresholds before viewing results
5. Add domain features only when their historical availability can be established:
   starters, lineups, injury status, player/roster strength and schedule context
6. Calibrate on recent, distinct data and compare with incumbent baselines. Require
   uncertainty-supported improvement rather than a single better point estimate
7. Add authenticated artifact storage, signed/verified releases, safe model loading,
   dependency/security maintenance and rollback. Never serve untrusted pickle files
8. Define an API, load/resource limits, observability, on-call ownership, incident
   handling, access controls and retention before claiming an SLA

## Proposed monitoring, not an active service

| Signal | Proposed check | Action before serving more predictions |
| --- | --- | --- |
| Data freshness | Provider's expected cadence and publication lag | Stop affected predictions; investigate |
| Schema/source drift | New fields, changed hashes, duplicates, unknown labels | Quarantine new snapshot; review adapter |
| Missingness/cold starts | Rates versus locked training and recent references | Flag estimates; investigate source/roster changes |
| Feature drift | Rolling quantiles and population stability by sport | Review distributions; never auto-retrain solely on a flag |
| Performance | Delayed log loss/Brier/accuracy vs prior and Elo on fixed windows | Investigate with confidence intervals and sample-size limits |
| Calibration | Classwise reliability and ECE with bin counts | Recalibrate using a separately approved recent partition |
| Fair coverage | League/surface/season/newcomer slices | Scope down unsupported or poorly covered populations |
| Artifact drift | Data/code/config/checkpoint hashes | Block mixed-version inference; restore last reviewed artifact |

Thresholds need real operational cost and prospective data, so no invented
universal alert limits are supplied. Logging must avoid unnecessary personal data.
Any automation would require deployment-specific authorization and ownership.

## Responsible interpretation

A fixed-label model can avoid free-form invented prose and still make wrong,
miscalibrated predictions. A 65% historical classification rate is not 65%
certainty about a specific future match, and neither implies profitable decisions.
Explanations of input differences are descriptive, not causal player evaluations.
No model here should affect employment, education, medical, or financial decisions.
