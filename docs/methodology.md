# Methodology and inference contract

## The question

Given two known participants and information available before an event, estimate
its outcome distribution. The common layer supports four separate estimators;
it is not a universal model pretending the sports are interchangeable.

Soccer predicts away/draw/home at full time. Baseball/NFL predict designated-home
wins conditional on non-tied completed games. Tennis predicts canonical player A
winning conditional on a complete supported score. Selection exclusions matter:
these are not unconditional probabilities of every scheduled event outcome.

## Information boundary

Every row has an event date and a result-availability date. All features at date
t use only outcomes with available_date < t. Same-day scores never update other
same-day predictions. Baseball suspended games become available on completion.
Tennis lacks match dates: the source tournament-start date is retained and results
are delayed 21 days. This loses legitimate within-tournament information but avoids
assuming an arbitrary row or round order reveals results at the correct time.

Tennis evaluation is conditional on realized matchups, using frozen pre-tournament
features. Later-round opponents are not necessarily known at tournament start,
so this is not a forecast of a known complete tournament-start fixture list or
a tournament/bracket simulation. Equal-availability results are updated in
deterministic event-ID order. Within tennis tournaments this is not verified
match chronology, so Elo update order and last-ten history are approximations.
No unavailable results enter a prediction, but those features should not be
described as exact last-ten-match sequences.

This is an availability model, not a claim that the current provider snapshot
records exact historical publication time. Retrospective corrections remain a
limitation. Team aliases and tournament metadata also come from corrected sources.

Tennis ranking fields are snapshots as of the tournament date or most recent prior
ranking date, per the upstream dictionary. Winner/loser rank fields are remapped to
IDs sorted without looking at who won. Raw winner/loser statistics, scorelines,
IDs and dates are never passed to the estimator as predictors.

## Features

| Field | Meaning and units |
| --- | --- |
| elo_diff | Prior overall Elo A minus B, divided by 400 |
| surface_elo_diff | Prior surface-specific Elo A minus B, divided by 400; same as overall for team sports |
| form_diff | Last-ten completed result mean A minus B; win=1, draw=.5, loss=0 |
| margin_diff | Last-ten score margin mean A minus B |
| scoring_diff / conceding_diff | Last-ten score-for / score-against mean differences |
| experience_diff | log(1+known games A) minus log(1+known games B) |
| rest_diff | Known previous-event rest, capped at 30 days, difference divided by 30 |
| neutral | Provider neutral designation; baseball only uses designated-home convention |
| cold_a / cold_b | No usable history indicator |
| log_rank_diff | log(rank B / rank A), tennis; missing rank uses 1000 plus explicit missing flag |
| rank_missing_a / rank_missing_b | Missing/invalid ranking indicator |

For tennis score_a/b encode match outcome, not games won; score-margin features
are consequently redundant with form and should not be read as serving strength.
Tennis rest is tournament-start spacing, not actual days since the previous match.
For newcomers, Elo starts at 1500, history means use fixed defaults, and rest is
30 days with cold-start flags. These defaults are stated assumptions, not imputed
knowledge about the player. Elo K=20, home adjustment=55, window=10, and the
21-day tennis delay are preset; they were not tuned on the final holdout.

## Selection, fitting and calibration

Two expanding chronological folds, each with a one-year validation window, lie
entirely inside the training era. Compare five fixed candidates by mean fold log
loss: standardized logistic regression C=0.1,1,10; histogram gradient boosting
with 7 or 15 leaves, learning rate .06,120 iterations and stated regularization.
No randomized early stopping is used. Scaling is fitted only on each fold's fit
partition.

The selected configuration is fitted once on the full training partition. A
single temperature in [0.5,5] minimizes log loss on the following validation
partition. Separate calibration is applied to the Elo baseline. Calibration
partition metrics are in-sample for temperature fitting and explicitly labeled
that way. The next two years are the final holdout. Model parameters never update
there, although strictly earlier completed outcomes update historical features.

Training/calibration labels with availability crossing a partition boundary are
embargoed. The holdout remains untouched by model selection. Once its results have
been inspected, future feature improvements need a new prospective or nested
holdout; repeated optimization against these dates would invalidate the claim.

## Metric conventions

Log loss is the main proper probability score. Binary Brier uses positive-class
squared error; soccer Brier sums squared error over all three classes before
averaging. Accuracy uses argmax. Top-label ECE has ten fixed-width confidence bins;
classwise reliability plots show mean predicted probability versus observed class
frequency. Raw bin counts are in evaluation.json. Small bins and varying targets
make comparisons of ECE/Brier across sports unreliable.

Four hundred paired calendar-week bootstrap replicates estimate approximate
log-loss and improvement intervals. Resampling whole weeks captures some local
dependence, but not all season/team dependence, source revision, or tuning
uncertainty. These are aggregate sampling intervals, not per-match certainty.

## Reproducibility and failure behavior

The exact bytes of all input and evidence files are recorded in data_manifest.json.
Immutable GitHub commits are used where possible; mutable provider downloads fail
verification if they change. Download failure is an error: the pipeline never
falls back to synthetic matches. Synthetic fixtures occur only in tests and have
explicit synthetic IDs. Failed schema checks, duplicate IDs, impossible dates and
unknown neutral designations fail closed.

Each report records seed, software versions, code hash, processed-data hash,
model-file hash, artifact ID, complete candidate results and split counts.
Dependency/platform numerical differences can still alter the last digits.

## Inference contract

Input: sport, known participant IDs, ISO forecast date, neutral designation if
applicable, and tennis surface plus positive pre-tournament ranks when known.
The local historical snapshot must use the same adapter schema. Output: class
probabilities in documented order, artifact ID, source availability upper bound,
historical input differences and warnings. Tennis input order is canonicalized
internally and remapped to the requested A/B order. Dates before the calibration
cutoff are rejected. Unknown participants require explicit cold-start opt-in.

The model is not supplied a fixture feed. Example scenarios do not assert that a
match existed. No forecast after the historical snapshot should be presented as
a verified current forecast. Loading joblib from an untrusted party is unsafe.
