# Tennis A1/A2 numerical protocol draft

**Approval status: draft, not approved. Fitting and predictive scoring are closed.**

Prepared 11 October 2026 for one batch methodological/independent review. This document specifies a possible next experiment; none of these methods, grids, calibration steps or performance estimates has been run. It does not waive the source/rights, parser-adjudication or implementation-review gates.

## 1. Fixed task, population and source

Use the exact MCP pin, transformations and strict eligibility in [tennis_parser.md](tennis_parser.md) and the current local `summary.json`. No substitute source, new parser leniency, synthetic measurements or optional BYU cohort is included. First-pass parser QA reports 809,750 development-eligible A1 and 307,565 development-eligible A2 rows in 2010–2022. Those are support counts, not training results.

- A1: observed wide/body/T direction immediately before first-service motion, including known-direction faults
- A2: observed wide/body/T direction after a verified completed first fault and before second-service motion
- Let-prefixed target deliveries, unobserved/penalty/time-violation observations, unknown target direction, unsupported prefixes/rules, and quarantined matches retain the parser's explicit exclusions
- For A2, a known fault with unknown/omitted first-fault direction can enter, using its observation-status category. A time-violation loss is not first-fault entry
- The target classes are permanently ordered `wide`, `body`, `T`; unknown target is an excluded observation, never a fourth direction or the body class
- The feature target is an annotated direction, not intended placement, bounce coordinates, physical angle, biomechanical state or causal coaching response

Fit **four independent task/corpus cells**: A1-men's source corpus, A1-women's source corpus, A2-men's source corpus and A2-women's source corpus. Do not choose pooled versus separate models after seeing results. No corpus label is an inferred biological measure. A later pooled model would require a separately approved comparison.

A cell may proceed only with at least 1,000 training labels per direction and, in 2023, at least 200 per direction and 50 matches overall. If a cell fails, keep it descriptive. Do not move its cutoff, pool corpora, merge direction classes or claim a calibrated result to rescue it. These support checks can be performed only after this protocol is approved; none is claimed complete here.

## 2. Calendar boundaries and visibility

- Parameter training: event dates 2010-01-01 through 2022-12-31
- Candidate/hyperparameter selection: 2023 only
- Probability calibration: 2024 only
- Primary evaluation: 2025 only, performance-blind after source QA until all four designated pipelines and analysis rules are frozen
- 2026: parser/eligibility/drift-input QA only in this experiment; no 2026 target-by-context or predictive performance output
- Pre-2010: historical QA only; no initialization of training histories from these labels

All points and prefixes of a match share the match-date partition. Both participants travel with their match. No random point split, server-only grouping or reconstruction from final match outcomes is allowed.

The snapshot has already received source/score/eligibility QA, including reading point-winner fields to validate scoring. Therefore 2025 is **not represented as untouched data**. Its restricted status is performance-blind after source QA: no candidate scores, target-by-context profiles, calibration choices or model selection are permitted until the freeze. Record that prior QA exposure in the eventual report.

MCP chart-publication timestamps are unavailable. This is retrospective event-date generalisation, not a historical as-of-publication backtest or a live coaching feed. Same-date cross-match order is unverified and must not be guessed.

## 3. Exact availability and history policy

**Review amendment before fitting:** MCP dates are not verified completion dates.
The source includes the multi-day Isner–Mahut match, and independent inspection
also found a Wimbledon quarterfinal with a questionable source date. Same-day
batching alone cannot make full-match history timestamp-safe.

Define the sole history/label availability rule as
`available_date = parsed source match Date + 21 calendar days`. This is a fixed,
conservative research embargo, conditional on source-date accuracy and completion
within that interval. It does not verify actual completion, annotation publication
or historical ingestion. Known contradicted dates are quarantined unless an exact
primary-source correction is independently reviewed; do not invent corrected dates.
Any known match finishing after the embargo is excluded from this experiment.
Unknown violations remain a measurement limitation, not a guaranteed absence.

The primary analysis uses **day-start frozen, embargoed histories**. At source
analysis date D, all historical directional counts come only from eligible matches
whose `available_date` is strictly less than D. Every match on D sees the same
history. Queue each complete accepted match until this rule admits it. No
within-match update of directional-history features is used in the primary analysis.
Decay age for B1 is `(D - source match Date)` in days, and an observation has zero
history weight until its availability gate opens. The same gate applies to B0,
server histories and returner-facing histories.

The embargo also applies to parameter-stage labels, not only history features:

- Training rows have source dates in 2010–2022 and available_date < 2023-01-01
- Selection rows have source dates in 2023 and available_date < 2024-01-01
- Calibration rows have source dates in 2024 and available_date < 2025-01-01
- Final evaluation rows have source dates in 2025; their labels are scored only
  after their available_date, even when that date falls in January 2026

Late-December observations that fail a parameter-stage cutoff remain excluded
from that stage, with counts reported. They may later enter histories when their
availability gate opens; they are not reassigned to another parameter partition.
All support thresholds and numeric denominators are checked on these embargo-
adjusted, date-QA-accepted populations. Earlier parser development counts were
pre-embargo source support and are not promised model-fit counts.

Current pre-point sets, games, score, server, side and tie-break state are still reconstructed from prior completed points in the current match, as the parser already does. A2 additionally uses only the current completed first fault. Neither task reads the current target's direction, outcome or suffix to construct its inputs.

Model weights, preprocessing and hyperparameters are frozen after 2022/2023 selection; they do not update on 2024 or 2025. Historical count features may update only after the fixed embargoed availability rule admits earlier matches in these years. This distinction must appear in the report. A history-frozen-at-2022 secondary variant is not part of this first protocol; no post-hoc variant is selected from evaluation results.

At training time, construct each row's history with the same day-start walk beginning from empty 2010 histories. Do not give a 2010 row a full-2010, full-career or end-of-training summary. No source charter ID, rank, guessed ranking, full-career style cluster, retrospective Notes or tournament result is a feature.

Whole-match quality acceptance is a retrospective cohort filter, not a prediction input. A match contributes to later-date histories only if its full parser/date QA has passed and its available_date gate has opened. Never transfer a current match's eventual QA status, winner, final length or future rows into a current feature. Future-perturbation tests must verify this at the feature/history API boundary; accepted-cohort selection is reported separately.

## 4. Predeclared model families and grids

All methods use the same eligible rows within each cell. No class weighting, outcome-dependent subsampling, point duplication, SMOTE or case-specific model eligibility is permitted. Model-specific numerical failure is not a reason to quietly change the comparison denominator.

### B0: context backoff, fixed

For each historical date, construct three-class counts independently within the task/corpus cell:

1. Global probability: `(global_count[k] + 1) / (global_n + 3)`
2. Surface probability: `(surface_count[k] + 100 * global_probability[k]) / (surface_n + 100)`
3. Surface × service-side probability: `(cell_count[k] + 30 * surface_probability[k]) / (cell_n + 30)`

B0 uses step 3. No parameters are selected for B0. Counts are ordinary cumulative prior-date observations beginning in 2010, not final source totals.

### B1: server tendency with partial pooling, four candidates

For each candidate, apply exponential date decay to the server-specific history; weight an observation of age a days by `2 ** (-a / h)` when h is finite, otherwise weight 1. B0 remains cumulative and fixed as above.

- Half-life h: 365 days or infinity
- Smoothing alpha: 50 or 200 effective observations
- Grid: the four Cartesian combinations, no additional window or smoothing search

First smooth server × service-side counts toward B0, using alpha. Then smooth server × surface × service-side counts toward that server-side probability, using the same alpha. Empty server histories fall back exactly to B0. This is the primary historical-frequency comparator. Record effective count and actual prior match support separately; decayed count is not an independent sample size.

### L: regularized multinomial logistic regression, three candidates

Use the explicit features below, with no player-name one-hot columns. Fit one multinomial model per cell with L2 regularization, `solver='saga'`, intercept enabled, class weighting disabled, `tol=1e-5`, `max_iter=300`, and seed 20261011.

- C grid: 0.1, 1.0, 10.0
- A convergence warning permits one prespecified retry of the same C with `max_iter=1000`
- A repeated convergence/numerical failure disqualifies that candidate and is reported; it does not authorize a new solver/grid, less stringent tolerance or silent truncation
- Prefer a sparse feature matrix; there is no dense high-cardinality player or matchup matrix

### N: bounded nonlinear comparator, two candidates if the budget gate passes

Use histogram gradient boosting on the same low-dimensional features and cases, with native fixed-vocabulary categorical features, `learning_rate=0.05`, `max_iter=120`, `min_samples_leaf=200`, `l2_regularization=10`, `max_bins=63`, `early_stopping=False`, and seed 20261011.

- `max_leaf_nodes`: 15 or 31
- No depth, iteration, learning-rate or seed search
- Numeric inputs are float64; categorical vocabularies are fit/fixed without validation/calibration/evaluation labels
- No image, transformer, recurrent or unrestricted sequence model is in this experiment

Run N only if an approved training-only resource probe shows the complete two-candidate, four-cell work can stay within the budget in section 10. If it cannot, record N as not run. Do not reduce its data, prune cases, substitute a new model or tune a smaller candidate using 2023/2025 performance. The resource probe itself would be fitting and must wait for approval.

## 5. Exact feature/preprocessing contract

Names of server and returner are keys for past-count lookup only. Raw identity strings, charting identity, current serve strings, source row number, Notes, current point winner, current serve outcome, current speed, rally length and current target direction are excluded.

Fixed categorical inputs:

- Surface: hard/clay/grass
- Service side: deuce/ad
- Server and returner hand separately: R/L/U, with blank mapped to the explicit U category
- Current tie-break flag
- Ordinary server and returner point score separately: 0/15/30/40/AD; use a distinct not-applicable category during tie-breaks
- A2 only: first-fault direction wide/body/T/unknown, its explicit-known/explicit-unknown/omitted observation status, and fault type net/wide/deep/wide-and-deep/foot-fault/unknown/shank

Fixed numeric inputs:

- Server and returner sets and games; game number; point ordinal
- Tie-break server and returner points, with zero plus the tie-break flag outside tie-breaks (structural zero, not an imputed measurement)
- Three historical B0 probabilities
- Three historical server tendency probabilities and three returner-facing tendency probabilities, each computed by the B1 hierarchical formula with **fixed** half-life 730 days and alpha 100, independent of the B1 candidate grid
- `log1p` of those server and returner effective counts and prior eligible match counts

Returner-facing counts mean observed serve directions faced in prior eligible points, using the returner identity as the key. They are not return ability, a causal opponent effect or data from the current target. Do not use exact-pair histories in this first version; tiny head-to-head cells would add unnecessary selection and support problems.

Do not use event year/date as a direct predictor; date serves partitioning/history-decay purposes only. Serve period and source corpus are fixed by cell. No unapproved interactions or feature selection is performed. Unknown players inherit the contextual probabilities and zero support, without inventing rank or style.

For L: fixed categorical vocabularies feed `OneHotEncoder(handle_unknown='ignore', sparse_output=True)`; fit numeric mean/scale parameters on training only and use a sparse-compatible scaler. Preserve an explicit unknown category rather than turning missing categorical data into a known class. All required numeric inputs are either observed/replayed or structurally defined; unexpected missing/nonfinite inputs fail the contract rather than triggering ad hoc imputation.

For N: use the same semantic fields, with a training/fixed-vocabulary category map and native categorical indicators. There is no ordinal meaning implied by category codes. Preprocessing artifacts, vocabularies and scaling are saved per cell and remain unchanged during selection, calibration and evaluation.

## 6. Selection and designation, 2023 only

Primary selection score is point-weighted mean natural-log multiclass log loss on the identical eligible 2023 cases. Clip each probability to at least 1e-12 and renormalize for all models before logarithms; log clipping is fixed and not fitted.

Within each family, select its lowest-loss candidate. For losses within 0.002 nats per eligible point, prefer:

- B1: alpha 200 before 50, then infinity half-life before 365 days
- L: smaller C
- N: 15 leaves before 31

Designate the main family using the best family candidates plus B0: find the minimum family loss, then choose the simplest family whose loss is no more than 0.002 nats above that minimum. Simplicity order: B0, B1, L, N. The same tie rule applies independently to all four fixed cells. No metric weighted average, accuracy override or handpicked slice can replace it.

Freeze the selected B1 comparator, best L and N candidates if run, B0, designated main family, preprocessing, history logic and data/feature hashes before touching calibration outcomes. Train model parameters on 2010–2022 only; do not refit weights on 2023 after selection in this first experiment.

## 7. Calibration, 2024 only

Fit a single scalar temperature independently for each cell and each frozen family candidate using its 2024 probabilities. For a three-class probability vector p, calibrate `softmax(log(p) / T)`, using the same 1e-12 clipping rule.

Optimize mean 2024 log loss over `log(T)` in [-3, 3] using bounded scalar minimization, `xatol=1e-5`, at most 100 iterations. No isotonic, class-wise, spline or alternate calibration grid is allowed. If optimization fails, preserve identity T=1 and report failure; do not choose a different calibrator from evaluation data.

Calibration requires at least 3,000 eligible points, 50 matches and 200 labels per direction in the cell. If insufficient, use T=1 and state that the cell lacks a separate calibration fit. Do not pool cells or reslice years. Calibration loss is not an independent performance estimate and is not used to reselect the designated family.

Freeze temperatures and the full analysis manifest before unlocking 2025. Store this draft's final approved hash, source/parser hashes, selected hyperparameters, all seeds, exact dependencies and approval record in that manifest. This draft itself is not the approval record.

## 8. Locked 2025 comparisons and uncertainty

For every cell, score B0, selected B1, the best L, the best N if run, and the previously designated main model on exactly the same eligible cases. Report all planned comparisons, even when the designated main model disappoints. Never choose a new champion from the test ranking.

Primary contrast: calibrated designated main model minus calibrated selected B1, on point-weighted log loss. If the main model is B1, record no improvement claim; this does not authorize selecting a different model. Report uncalibrated counterparts as a fixed secondary comparison.

Primary metrics:

- Mean natural-log multiclass log loss
- Multiclass Brier score: mean sum of squared probability-minus-indicator differences across all three classes, without division by three

Secondary metrics: top-1 accuracy, per-class recall, macro recall, match-macro and server-macro log loss, observed support and fallback frequency. Ties in maximum probability are resolved by fixed class order. No accuracy-only improvement claim substitutes for the primary probabilistic contrast.

For each contrast, compute paired cluster bootstraps with 2,000 replicates and seed 20261011, retaining whole matches and pairing the same resampled cases across all methods. Report the point-weighted difference and a match-macro sensitivity. Use 98.75% percentile intervals for the four prespecified primary cell contrasts, explicitly noting this conservative family-level adjustment and the bootstrap's finite-sample limitations. An improvement claim requires mean log-loss reduction at least 0.005 nats and the adjusted interval entirely below zero; otherwise report no demonstrated improvement.

Dependence sensitivities, fixed in advance:

1. Resample whole `(normalized tournament name, calendar year)` blocks, preserving all matches and both actors. Reused names may combine stages of an event; document that conservative grouping
2. Resample four-week contiguous calendar blocks of matches within 2025, with a moving-block bootstrap, retaining complete matches and recomputing the paired aggregate. Include empty calendar weeks. Report the number of distinct populated blocks; small effective block counts weaken inference

These estimates address match/event/time dependence imperfectly and do not turn charted points into independent participants. Do not choose the narrowest interval. Report the match interval as primary and both sensitivities beside it.

Calibration diagnostics: fixed probability bins [0, 0.1, ..., 1] per class, bin support, mean predicted versus observed frequency and Brier/log-loss summaries. Bins with fewer than 20 observations remain visibly sparse; do not merge bins opportunistically. ECE, if reported, is secondary and uses these same fixed bins. No recalibration occurs on 2025.

## 9. Prespecified support and generalisation limits

Report corpus, task, surface, side, hand pairing, note-presence QA strata, prior server support tiers (0, 1–49, 50–199, 200+ eligible observations) and unseen/seen server/returner status. Suppress directional/performance cells with fewer than 200 points or 20 matches; still expose coverage counts. Use the same suppression for all methods. Player identities need not appear in the global workbench.

This primary evaluation measures known-player scouting under chronological use, not independence from player identity. Mark a server or returner cold when they have zero eligible training-period appearances, and report naturally occurring server-cold/returner-cold/both-cold cells only if support permits. Unknown identities get context backoff. These are descriptive stress slices, not an independently powered cold-player claim.

A true two-actor exclusion experiment would remove every training match involving any chosen held-out actor, whether server or returner, and fit again. That separate experiment is **not run or implied here** and needs a further protocol before any claim of cold-player generalisation. Do not use server-only GroupKFold or silently treat an unseen pairing as an unseen player.

No model output becomes a causal recommendation to change stance, direction, angle or technique. Missing intentions, tracked positions and opponent counterfactual responses prevent that claim.

## 10. CPU budget, reproducibility and stop conditions

Proposed budget after approval: at most four CPU threads, 4 GiB resident memory and 90 CPU-minutes for the complete candidate fit stage; no GPU. Fixed seeds and thread limits must be recorded. The low-dimensional feature matrices and their memory estimates are checked before fitting; no dense identity one-hot matrix is permitted. Do not launch parallel candidate fits that exceed the joint memory budget.

Maximum candidates per cell: B0 fixed; four B1 settings; three L settings with only the specified same-setting convergence retry; two N settings if feasible. Family freezing means one selected candidate per family proceeds to calibration/evaluation. Do not spend leftover budget on additional variants. If budget or convergence blocks a family, report the exact unrun/failed candidates and continue only with the prespecified valid families.

Before any fit, require:

- Independent review of this exact protocol and explicit approval
- Independent/manual stratified adjudication of serve prefixes, quality exclusions and score-rule reconstruction across both corpora, surfaces, eras, rare tokens, first faults, lets, penalties and parser failures; document disagreement and any revised parser hash
- Availability tests covering the known three-day Isner–Mahut match, source-date anomalies/quarantine, 21-day embargo boundaries, year-end fit/selection/calibration eligibility, same-day ordering, future point/outcome mutations, future match removal/mutation, both actor roles and training-only preprocessing
- Deterministic feature and candidate-row digests with all duplicates/conflicts quarantined
- Numerical tests proving valid three-class distributions and common-case scoring before loading 2025 outcomes
- An executable guard that refuses training/evaluation without the approved/frozen protocol identifiers

A parser change affecting eligibility or labels invalidates candidate hashes and requires renewed review before a first fit. A change after 2025 scoring is a new experiment, not a silent repair of the supposedly locked evaluation. Report unsupported/absent methods, failed candidates and negative findings. If the gates cannot be met, the completed outcome remains the descriptive workbench.


### Exact resource probe and fit-attempt ceiling, pre-approval amendment

Use float64 numeric features and probabilities for L and N. Fixed categorical
codes are int32, with explicitly saved category maps. Actual runtime is CPython
3.12 in this workspace; record its full patch version and platform before the
freeze. Use the project's existing NumPy2.3.5, pandas2.2.3, SciPy1.17.0 and
scikit-learn1.8.0 pins. One process and at most four BLAS/OpenMP threads; record
the exact thread settings. A version or dtype change requires review before fit.

There is exactly **one** optional training-only resource probe, counted as a fit:
A1 men's corpus, earliest 100,000 eligible embargo-adjusted training observations
ordered by source date, match key and point; N's 15-leaf specification, but 20
iterations. Use no evaluation labels or metric. Discard the probe model. Record
CPU seconds, wall seconds and peak RSS. If fewer than 100,000 eligible rows exist,
use all training rows, still one probe. No alternate probe is permitted.

Estimate full nonlinear CPU cost as
`2 * (120/20) * (2 * sum(four cell training row counts) / probe row count) * probe CPU seconds`.
The leading 2 is a fixed safety factor, and the other 2 counts two N candidates.
Admit N only if this estimate is at most 30 CPU-minutes, measured probe peak RSS
is at most 2 GiB, and explicit full-cell feature/matrix plus estimator memory
estimate is at most 3 GiB. These are conservative admission estimates, not a
runtime guarantee. The overall 4 GiB/90 CPU-minute cap remains binding. A cap
failure is an unrun/failed method disclosure, not an alternate grid search.

Maximum optimizer attempts across all four cells: 12 initial L fits + at most
12 prescribed L convergence retries + 8 N fits + 1 resource probe + 16 scalar
calibration fits = **49**. Without N, at most 24 L attempts + 12 calibration fits
= **36**, plus the single probe if it was attempted (37). A missing-support cell
reduces this budget; it does not transfer attempts to other cells. There are also
four fixed B0 and sixteen B1 historical-count candidate evaluations, plus four
fixed shared feature-history construction passes, which are deterministic count
operations rather than trained optimizers. No separate infrastructure retries
are added to these ceilings: restore an interrupted operation from its unchanged
checkpoint or report it uncompleted. Report the exact attempted/succeeded/failed
counts. Calibration support failures use the predeclared identity transform and
consume no fitted calibration attempt.
