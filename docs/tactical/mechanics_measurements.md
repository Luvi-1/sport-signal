# Measured laboratory companions: descriptive stage

These bounded adapters add actual source-measured body/pitch or target/bounce
measurements to the educational workbench. They do not pool laboratory rows with
professional event records, train or score a model, mine target-feature correlations,
or turn an observed association into a technique recommendation.

## Reproduce locally

From the repository root:

```sh
python -m experiments.tactical.mechanics
python -m unittest discover -s tests -p 'test_tactical_mechanics*.py' -v
```

The adapter reads only the previously inspected small pinned source files. It does
not download full signals/C3Ds, execute source scripts/binaries, load fitted outputs
or expose a model API. Optional `--sport baseball` or `--sport tennis` restricts the
build. Unknown options such as `--fit` fail at argument parsing. Missing/changed
source bytes fail closed. No source rows are copied into tracked files.

## Verified source and population contract

### Baseball

[OpenBiomechanics, pinned 44b98dae05cceb016f080ab39d105c85b8639084](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084).
Credit OpenBiomechanics Project, Driveline Baseball Research & Development. Its
[data/documentation terms](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md)
are CC BY-NC-SA 4.0 plus the professional-sports/financial-analysis affiliation
exclusion. MIT applies separately to software. Local eligibility was confirmed for
independent noncommercial research; preserve attribution, modification disclosure,
share-alike and additional terms. Source-derived documentation/aggregates retain
these obligations. This note does not relicense unrelated project code or imply
endorsement. Public distribution needs its own source-specific review.

The source reports informed consent, de-identification and Western IRB/WCG WB-DLR-115.
The chosen **adult paired-context cohort has 571 swings from 82 athletes**. Start
with 677/98, exclude 34 under-18 swings/5 athletes, retain 643/93 adults, then remove
5 absent exit velocities (638/92), then 67 observed-outcome swings without paired
context (571/82). These are different denominators, not interchangeable samples.
There is one session per athlete; no future-session evaluation is possible here.

Four explicit body-angle fields are exposed as candidate definitions: lead knee
flexion, rear hip flexion, rear elbow flexion and relative torso-pelvis axial rotation,
all at source foot plant in degrees. The first three use source joint x; relative
axial angle uses physical z even though its POI field ends in x. Foot plant is the
100% bodyweight lead-force threshold, distinct from 10% foot contact. Generic POI
suffixes are not an anatomical dictionary. These are source-processed kinematics,
not an independently calibrated camera-free angle sensor. The source applies some
handedness/sign changes; the adapter never mirrors them again.

Incoming pitch speed is mph, descent angle degrees, and horizontal/vertical zone
center offsets inches. Marker contact bat speed and Blast contact bat speed remain
separate descriptive outcomes; recorded ball exit speed is another outcome. Bat
attack angle is a bat-path quantity, ball launch angle a ball quantity. None of these
outcomes enters the body's feature allowlist. Metadata/POI duplicated target copies
are checked, and all 13 reviewed exact duplicate-column pairs are verified without
exposing unsafe aliases as candidate features. Outcome-bearing trial filenames and
arbitrary IDs/text never appear in candidate metadata or reports.

Machine setup is approximately 65 mph from 40 ft. Marker-derived signals: 360 Hz,
20 Hz filtering; forces: 1080 Hz, 40 Hz filtering. Whole-trial offline processing is
not online feature availability. The small hitting summaries have **no verified
elapsed event-time measurements** or pre-pitch stance width/orientation, so these
are explicitly absent. No injury/health/readiness or athlete-selection outputs.

### Tennis

[BYU serve experiment, pinned fd435d9158ad5671c819bee3c47a47d7161a42cb](https://github.com/nsandholtz/byu_tennis_serves/tree/fd435d9158ad5671c819bee3c47a47d7161a42cb).
MIT is stated in its README and [LICENSE](https://github.com/nsandholtz/byu_tennis_serves/blob/fd435d9158ad5671c819bee3c47a47d7161a42cb/LICENSE).
Credit copyright (c) 2026 Nate Sandholtz and authors Nathan Sandholtz, Ryan Hanson,
Ron Hager, Stephanie Kovalchik and Gilbert Fellingham; retain the complete notice
for covered distributed material. This adapter only transforms local licensed
source bytes. Neither source compiled software nor source fitted outputs are used.

**567 attempts from eight collegiate players across eight sessions**, 32 stated
targets. Exclude 19 lets, including five with missing coordinates; preserve **548
non-lets = 437 observed bounces + 111 net-censored attempts**. Raw source contains
451 observed bounces, including 14 lets. `NA` is parsed as missing. Speeds have 23
missing values in the full source and are not silently clipped. Several players
recur across sessions; 14 player/session and 64 player/period/region cells occur in
the non-let cohort. Shared sessions and few participants limit independence.

Exact target coordinates join by player and region. Coordinates are meters with
origin at net/center service line, x depth into returner's half, y positive toward
deuce. Signed errors are bounce minus the exact stated target on each axis; radial
error is their Euclidean norm, also meters. No body/joint angles are observed here.
Bounce water marks were measured with tape distance/angle finder and converted to
coordinates; mph comes from radar after impact. The [primary paper, Section 3
footnote 4](https://arxiv.org/html/2607.28500v2), reports a nominal ±3% radar accuracy
specification, not an independently validated per-attempt error bar. Coordinate
error and live availability remain unverified. Body mechanics cannot be inferred
from bounce.

Net bounces remain absent, never zero-imputed. The full-key join preserves 21
repeated shorter `(session, player, index)` keys; they are not duplicate serves or
verified point pairs. Supplied serve period is retained without inventing a match
transition. Simulated point-win surfaces from the source project are not observed
collegiate outcomes and never enter this adapter. The [primary paper, Section 3
footnote 2](https://arxiv.org/html/2607.28500v2), reports a BYU IRB #2025-487 determination
that the study fell outside the regulatory human-subjects-research definition and
thus outside IRB oversight. This is not a claim of IRB approval. Ages and individual
consent remain unverified; collegiate membership does not prove adult status. Coded
identities and individual target geometry are not exposed.

## Aggregate output schema for the workbench

Files, ignored and local:

- `reports/tactical/mechanics/baseball_summary.json`
- `reports/tactical/mechanics/tennis_summary.json`

Each is a standalone UTF-8 JSON object:

| Field | Meaning |
|---|---|
| `schema_version`, `adapter_version` | Contract and implementation version |
| `sport`, `phase` | `baseball`/`tennis`, always `descriptive` |
| `predictive_gate` | `{ "status": "closed", "fitting_allowed": false }` |
| `fit_status` | Explicit no-fit/no-score/no-correlation status |
| `source` | Official repository, immutable commit, notices, transformation, seven baseball or five BYU file hashes/URLs, source-manifest/code hashes |
| `population` | Cohort, unit, task, denominator and exclusion counts |
| `measurement_frame` | Actual method, coordinate frame, units, event/censoring and timing/accuracy limitations |
| `measurements` | Aggregate objects: `key`, `label`, `unit`, `definition`, `role`, `denominator`, `observed`, `missing`, then mean/q10/median/q90 when supported |
| `observed_outcomes` | Baseball-only separate bat/ball measurements, each explicitly not a future predictor |
| `geometry` | Fixed marginal histogram objects: key/unit/definition/denominator/observed/missing, and bins with lower/upper/count/suppressed |
| `condition_support` | Tennis-only assigned period/region attempt counts, not conditional performance estimates |
| `validation`, `limitations`, `privacy` | Passed structural checks and honest unresolved measurement/privacy issues |
| `split_description` | Outcome-independent group plan method/count and private-membership hash only |
| `protocol` | Hashed NO-FIT draft, still pending independent review and approval |

No row IDs, athlete IDs, names, per-participant records, source individual filenames,
raw trial measurements, raw body-health data or per-person rankings enter these
files. Body candidate metadata is allowlisted; prohibited bat-velocity aliases are
never included in the feature inventory. Constant source-table filenames in official
provenance URLs do not encode individual outcomes.

Geometry contains marginal body-angle/pitch-location coverage (baseball) and
marginal bounce coverage/error distributions (tennis). Every histogram has explicit
missingness and denominator. Fixed bins are lower-inclusive/upper-exclusive; null
endpoints mean open tails. Occupied cells with fewer than ten observations or three
participants are suppressed; if exactly one occupied cell is suppressed, a second
occupied cell is also suppressed when available. This modest precaution is not a
formal anonymization guarantee or public-release approval. Histograms do not cross
body features with outcomes. Quantiles use linear interpolation between sorted
observations, with no single-observation min/max display.

Private ignored `data/tactical/mechanics/*_split_manifest.json` files contain
opaque group memberships only. They are deterministic, outcome-independent draft
plans; never serve them through the workbench. They are not fitted artifacts or
permission to train. Public summaries record their hashes for later review.

## Predictive drafts, deliberately unexecuted

- [Baseball NO-FIT protocol](BASEBALL_MECHANICS_PROTOCOL_DRAFT.md): adult paired cohort; pitch-context-only versus body-plus-context weighted ridge, five outer/four inner athlete folds, four fixed alpha values, primary equal-athlete MAE and paired cluster uncertainty; no calibration fit
- [BYU NO-FIT protocol](TENNIS_EXECUTION_PROTOCOL_DRAFT.md): fixed eight-player leave-one-out comparison of two low-complexity net/bounce distributions, singleton regularization/shrinkage choices, all non-lets retained, no outer tuning or recalibration

Neither an attractive marginal picture nor this protocol text clears a numerical
experiment. Exact definitions, source rights/participant-use conditions, independent
review and explicit approval remain gates. The present artifact is useful as a
measured-source explorer even if no future model is approved.
