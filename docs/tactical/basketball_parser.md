# Basketball: stage-one ACB release context

Status: local descriptive research, no predictive fits, scores, recalibration or
model selection. Source quality agreement is not predictive performance.

## Reproduce

```sh
python -m experiments.tactical.basketball
python -m unittest discover -s tests -p 'test_tactical_basketball*.py' -v
```

`--root` selects the project root. The adapter requires the already acquired
pinned official event, game metadata and compressed tracking files. It verifies
actual byte sizes and SHA-256 against the prior acquisition manifests, including
the commit in each URL. Conflicting/missing hashes fail closed. It never changes
research source files or executes upstream code. Tracking JSON Lines is streamed
from gzip once per game; only requested release frames remain in memory. No
multi-gigabyte decompression or all-frame DataFrame is made.

## Population, units and clocks

Source: [SkillCorner official basketball data](https://github.com/SkillCorner/opendata-basketball),
MIT, commit `4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66`.
All 1,459 recorded field-goal releases from ten sampled Liga ACB 2025/26 games
remain in the population, **including fouled misses**. The 1,433 event-geometry
rows are a separately reported available-data cohort. No box-score FGA filter is
used. Features describe the release state, not the preceding decision whether to
shoot. This is retrospective processed data, with no verified live publication
latency.

Coordinates/distances are feet, with normalized offensive hoop **(-40.75,0)**.
Tracking is 25 Hz. `startFrame` selects the exact release frame; wall clock is
milliseconds since video origin, and game/shot clock is seconds remaining. Period
and wall-clock equality are checked independently. Hoop bearing is absolute
`atan2(y, x + 40.75)`; distance is recomputed from the normalized event location.
The provider's distance is retained only as a consistency diagnostic.

Missing/nonfinite coordinates, malformed three/frame/period fields and negative
or missing defender distance are ineligible for the geometry cohort, but remain
recorded releases. Absolute coordinates beyond 100 ft are a fixed coarse
corruption guard. The separate 94×50-foot reference-rectangle flag is diagnostic,
not a FIBA boundary or accuracy test, and does not exclude shots. Invalid shot
clocks become missing with a visible flag, not a tuned imputation. No empirical
coordinate trimming or winsorization is performed.

## Orientation and raw-frame quality

Raw player xyz is camera-oriented; event coordinates are offense-normalized.
No inspected field declares the attack direction. The adapter infers one 180°
rotation per game/offense-team/period, using no outcome fields:

1. A vote requires the better rotation to match event/raw shooter position within
   1 ft and beat the other rotation by more than 1 ft
2. At least two decisive votes and at least 80% agreement are required
3. Ambiguous cells abstain; both x and y are rotated together

This is retrospective metadata inference and can use later releases in the same
period. It is **not asserted to be a live-available predictor**. Already normalized
event features do not depend on that inference. Rotations, counts and uncertainty
are retained in the ignored `orientation_qa.json`.

For each release, the parser records frame coverage, unique-player/team counts,
team/role checks, directly detected flags, provider error estimates and residuals
for shooter location, named defender distance and nearest recorded opponent.
The primary consistency cohort uses **0.1 ft** for both location and named-defender
agreement; **1 ft** is a separate prespecified sensitivity. A second primary
sensitivity requires both players directly detected. These tests establish
same-provider representation/frame agreement, **not independent physical accuracy**.
Incomplete frames are flagged, not interpreted as empty space or complete defense.
This stage derives no motion windows or joint mechanics.

## Development boundary and outputs

Development games, in order: 114243, 114234, 114169, 114099, 114086. Later games
178442, 179612, 184439, 188630, 191313 supply source/eligibility QA only. Their
outcomes are never passed to the target extractor, bins or plot sampler. A later
predictive experiment requires exact protocol review and parent approval.

The semantic feature allowlist includes normalized geometry, three flag, shot
clock and nearest-defender distance. Outcome, end frame/clocks, assisted/assist
opportunity, blocked/blocker, foul outcome, contest/contestLevel, shotQuality and
season aggregates are denied as features. `extract_target` is separate from
`extract_context`; mutation tests establish that post-release changes cannot
alter features.

Ignored outputs under `data/tactical/basketball/` include context JSONL, separate
development-target JSONL, verified source manifest, orientation diagnostics and
the exact MIT notice. `reports/tactical/basketball/summary.json` has phase
`descriptive`, population, units, source/contract/parser hashes, denominators,
quality and exclusions. Development-only distance, hoop bearing, three and
nearest-defender bins report release counts, target denominators and observed
makes. A bounded `development_plot` contains at most 200 location-valid
development releases chosen by SHA-256(shot ID) order, with observed/missing and
raw-quality flags. Neither is a fitted probability or coaching intervention.

Tests use invented observations and cover coordinate orientation/units, nonfinite
outliers, shot-clock missingness, fouled misses, outcome mutation, partial and
wrong-team frames, direct-detection sensitivity, fixed tolerances, grouped
orientation abstention, streaming selection, future-frame mutation and later-game
locks.

## Interpretation and rights

Data: SkillCorner; original local descriptive parsing modified from source.
Retain the MIT notice and source pin for any separately approved redistribution.
No third-party match video, team logo or unlicensed branding is imported.
This task performs no external publication. Ten sampled games cannot establish
NBA transfer, league-wide superiority, stable defender rankings, joint mechanics,
or optimal shot selection. Immediate field-goal points omit free throws,
rebounds, turnovers and possession continuation.
