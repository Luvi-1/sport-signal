# V2 protocol, fixed before new-holdout scoring

Recorded 2026-10-11. V1's 2023/24 (EPL 2023–25) final scores have been inspected.
They are now development information; they will never be described as fresh test
evidence for V2. V1 remains frozen separately with its original reports and hashes.

## New test period

Subject to source-quality audit: MLB calendar 2025, NFL season 2025, ATP
tournament-start dates in calendar 2025, and EPL season 2025–26. The source audit
may inspect schema, score validity, dates, counts and completeness, but may not
compute model metrics or target rates. Development fitting parses only the cutoff-purged pre-holdout file; the full
processed source is hashed for integrity but its new-period rows are not parsed
by development. Full sequential holdout features are built only after explicit
evaluation unlock. The new test is not used to invent features,
select candidates, fit calibration, set ensemble weights or pick a winner.
Public result snippets incidentally seen during source verification are not model
inputs; do not claim perfect human outcome blindness.

## Development periods

For MLB/tennis: training before 2024-01-01, calibration during 2024, new test 2025.
For NFL: training before 2024-03-01, calibration through 2025-03-01, test through
2026-03-01. For soccer: training before 2024-07-01, calibration through
2025-07-01, test through 2026-07-01. Embargo labels whose availability crosses a
training or calibration boundary. Three one-year expanding-window development
folds immediately precede the training cutoff.

## Prespecified features

V1's finite pre-event features plus longer-horizon strength/form: batch-updated
fast/slow Elo, surface rating, exponentially time-weighted results/scoring with
30/90/365-day half-lives, opponent-strength history, role-specific historical form,
season form with shrinkage, counts, surface form, log absence (capped at three
years) and ranking transformations.
All outcomes remain strictly earlier-available than the predicted date. New
batch ratings sum updates calculated from the same availability-bucket snapshot,
so they do not invent within-tournament chronology. Time-weighted features do not
require a last-match ordering within tournament dates.

Features are deliberately results-only plus verified tournament-start rankings;
no unverified lineup/injury timestamps, odds, free-form web opinions or later
match statistics are introduced. Coverage and exclusions match V1 unless a
source-schema normalization is documented in the V2 audit.

## Prespecified comparisons

- Training class-frequency prior, Elo, calibrated Elo, and rating-only logistic model
- Extended logistic regression C=0.1, 1, 10
- Histogram gradient boosting: 7/15/31 leaves, 160 iterations, learning rate .05,
  L2=5/10/20, minimum leaf size30
- Random forest: 300 trees, depth6/12, minimum leaf20/10, max_features=.7
- Extra Trees: 300 trees, depth10/unlimited, minimum leaf10/20, max_features=.8
- Soccer Dixon–Coles-style baseline: team attack/defense one-hot Poisson
  regression, ridge alpha=.1, home indicator, 365-day recency half-life; a low-score
  correlation rho in [-.1,.1] is fitted on training goals only. Parameters remain
  fixed at the training cutoff; this is a lightweight implementation, not a claim
  to duplicate a commercial or published package exactly
- The frozen V1 winning recipe refitted on the V2 training/calibration periods,
  so architectural improvement is distinguished from simply adding newer data
- One ensemble: best development-CV member of extended logistic, histogram
  boosting, random forest, Extra Trees, and (soccer only) Dixon–Coles. Rating-only
  logistic and the V1 recipe are comparison baselines, excluded from the ensemble.
  Weights fit
  only to chronological out-of-fold predictions with nonnegative simplex weights
  and an L2-to-uniform penalty=.02. This is a learned stacking layer, so its fitted
  OOF loss is not an unbiased performance estimate

Development-CV log loss selects family configurations. The ensemble is the
prespecified main V2 model; report every base family, all baselines and all
negative findings on the new holdout. Temperature for each final comparison is
fit on calibration data only. No replacement champion is selected after test
results are seen. Accuracy is secondary; log loss, Brier, reliability curves,
ECE and paired calendar-week bootstrap intervals are required.

## Stopping and reproducibility

Freeze configuration, code, selected configurations, ensemble weights, calibrated
parameters and input hashes in a selection manifest before unlocking test labels
for scoring. Retain every development comparison. One new-holdout run produces
all prespecified comparisons. Bug repairs must be disclosed; new improvement
ideas after that run require another future or explicitly exploratory evaluation.

No paid APIs or account-gated checkpoints. Moderate CPU usage is sufficient.
Closed-source comparisons require actual archived probabilities on identical
matches with a verified pre-event timestamp; marketing accuracy is not comparable.
