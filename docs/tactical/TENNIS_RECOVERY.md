# Interrupted tennis development recovery

This is a separately reviewed orchestration layer. The original protocol, parser,
metrics, gates, model code and development binding
`38d558b3d1847367cacf76a7e314e16fc85fb062b38c4f2d9c0a4c661210c7b6`
remain unchanged. Creating this wrapper does not approve execution.

## Fixed scope

- Keep the first twelve shared operation-journal records byte-identical
- Keep all eleven completed fit ledger entries and the A1-men/A1-women selected
  bundles, reports and predictions unchanged
- Snapshot the original fit ledger and shared journal before changing any state
- Only after explicit lead approval plus independent review, mark A2-men L C=0.1
  `interrupted_no_result`; its twelfth slot remains consumed. Never repeat it,
  convergence-retry it, reconstruct its score, or infer convergence from process loss
- Reuse the original resource-probe admission without rerunning its probe
- Run only A2-men L C=1/10 and N leaves=15/31, and A2-women L C=.1/1/10 and N
  leaves=15/31. Only an actual original convergence warning permits one existing
  max_iter=1000 L retry. This is nine initial fits and at most five retries
- Freeze all four selected cells before any calibration label/source read. Up to
  sixteen original family-temperature fits remain allowed. No family reselection,
  alternate calibration, expanded grid or evaluation is authorized
- Preserve the four original sport forecasts and the five completed tactical freezes

## Read-only preparation and approval

`python -m experiments.tactical.tennis_recovery inspect --root ROOT
--process-absence-utc 2026-10-11T10:46:00+00:00
--absence-evidence-path artifacts/tactical/tennis/interruption_evidence.json`

`inspect` hashes bytes and reads bookkeeping JSON; it never creates a Dataset,
reads source target payloads, unpickles models, fits or changes working state.
`prepare` has the same inputs and creates only immutable recovery metadata and
pre-recovery snapshots. Preparation binds:

- This wrapper, its tests and this document by SHA-256
- Original development binding and exact original development approval
- Immutable original journal/fit ledger snapshots
- Completed A1 artifacts, development rows/history/training actors and probe
- Original forecasts and existing completed tactical freezes
- Saved interruption evidence, conservative debit and exact 30-entry allowlist

Preparation must follow independent code review; production execution must await
review of the exact prepared recovery binding and explicit lead approval.

The lead creates `artifacts/tactical/tennis/recovery/RECOVERY_APPROVAL.json` with:
`schema_version=1`, `status="approved"`, `recovery_binding_sha256`,
`original_binding_sha256`, timezone-aware `approved_at_utc`, `approval_reference`,
`review_manifest_path` and `review_manifest_sha256`.

The independently authored review manifest must contain `schema_version=1`,
`review_type="tennis_recovery_review"`, `status="cleared"`, the same recovery and
original binding hashes, `cleared_stages=["development"]`, and timezone-aware
`reviewed_at_utc`. The wrapper never creates either approval or review.

Run `verify` to validate the prepared snapshot and both approvals without fitting.
Only the explicit `run` command applies the lost-attempt disposition and resumes
approved development. The original development gate is required throughout.

## Conservative accounting

Use shared journal UTC timestamps, never the naive fit ledger timestamps (which
were local PDT). Start the uncertain interval at the shared reservation for the
last *completed* attempt, 2026-10-11T10:30:35.996016+00:00. Charge four times elapsed
wall time through the saved conservative process-absence bound
2026-10-11T10:46:00+00:00, plus the last recorded 223.448918327 CPU seconds.
The result is 3919.464854327 budget-charged CPU seconds, leaving 1480.535145673
seconds from the unchanged 5400-second cap. Overlapping execution is deliberately
double-charged. The actual current-executor process check was 10:45:51 UTC; the
rounded bound is not a claimed death time or a historical host-wide PID proof.

Resource reports separate measured pre-restart CPU, measured recovery CPU, total
measured completed CPU, conservative unobserved debit
and total budget-charged CPU. The original `cpu_seconds` resource-total and
`stage_cpu_seconds` attempt-total compatibility fields mean budget-charged CPU in
recovery, explicitly labeled as such. Individual completed attempt `cpu_seconds`
remains measured. The lost fit receives no invented measured duration or score.

The original four-thread, 4 GiB RSS/address-space and 49-reservation guards remain.
All preprocessing/scoring/calibration execution in this wrapper's active session
is charged in addition to the initial conservative debit. Budget exhaustion stops
further work and cannot silently increase the cap.

## Durable results and another interruption

Each candidate estimator/status is durably checkpointed before selection scoring
or another optimizer starts. Each scalar temperature/status is checkpointed before
another calibration starts. Checkpoints include the exact operation identity,
recovery binding, completion time, charged CPU, and an external byte hash. A clean
resume reloads them; it never duplicates a reserved fit or calibration.

An exclusive file lock prevents concurrent wrapper executors. A write-ahead session
marker remains `running` after abrupt process loss. Such a second interruption
fails closed: obtain fresh process-absence evidence and reviewed additional CPU
accounting/disposition before resumption. Never delete the marker to bypass it.
A shared reserved operation without a committed result also fails closed and is
never automatically repeated. A partial calibration row build fails closed under
the original row-writer checks. These safeguards prioritize no duplication and
honest budgets over unattended recovery from another unknown process loss.

Final candidate and selection freezes carry the recovery binding and the missing
candidate explicitly; they bind the approval/disposition and original snapshots.
The candidate freeze binds all completed candidate checkpoints. The final freeze
also binds every result checkpoint and the complete final shared
journal. This wrapper has no evaluation command and never requests 2025 rows.

## Tests

`python -m unittest discover -s tests -p 'test_tactical_tennis_recovery.py' -v`

Tests use temporary synthetic bookkeeping and mocked estimators/calibration,
cover byte preservation, exact allowlists, permanent missing-candidate bar,
approval/hash failures, conservative CPU limits, durable no-repeat resumes,
unclean-session refusal, and all-four-cell calibration barrier. The end-to-end mock
runs nine candidate fits and sixteen calibrations, preserving A1 byte identity and
finishing with 37 consumed shared slots. It opens no real target rows.
