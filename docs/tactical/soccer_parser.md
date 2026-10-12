# Soccer: stage-one recorded shot context

Status: local descriptive research. No tactical model is fitted, scored, calibrated,
or selected. Model protocols and source-specific publication remain separate gates.
This adapter does not alter the preserved match forecasters.

## Reproduce

From the repository root:

```sh
python -m experiments.tactical.soccer --fetch
python -m unittest discover -s tests -p 'test_tactical_soccer*.py' -v
```

Without `--fetch`, the adapter uses only available verified local files and fails
if any required source is missing. It accepts `--root` and bounded `--workers`
(default six, maximum eight). Downloads use ordinary official pinned raw URLs;
no upstream code is executed. Existing research cache files are read, never changed.
The adapter streams Git SHA-1 and SHA-256 checks, downloads missing events into
`data/tactical/soccer/source/`, and verifies every blob against the complete pinned
Git tree before parsing. Integrity errors fail closed. Source pins are not a
substitute for source-use permission.

## Population and information boundary

- Source: [StatsBomb/Hudl Open Data](https://github.com/statsbomb/open-data), commit
  `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`
- Women's Super League competition 37; development seasons 4, 42, 90 contain
  107, 87, 131 games respectively, 325 total
- Season 281 has 132 games. The 60 games before 2024-01-01 are calibration QA only;
  the other 72 are test QA only. Later shots contribute eligibility/source checks,
  never outcome-by-context patterns, sample points or target files
- Unit: recorded valid non-penalty shot, including every recorded miss category
- Exclude penalties, shootout period 5, invalid period, missing shot/type, or
  missing/nonfinite/out-of-grid shot locations. Unknown outcomes produce missing
  development labels, not feature changes or silently fabricated misses
- Physical reference is recorded shot state. These are offline historical
  annotations; observation/publication latency and live contact alignment are not
  independently established

`extract_context` is a semantic allowlist; `extract_target` is a separate function
called only for development seasons. `shot.outcome`, `end_location`, provider xG,
assists, pressure annotation, future saves/blocks/rebounds and unrelated events
cannot affect context. Mutation tests change these fields while preserving
identical context. IDs/times/cohort metadata stay outside the `features` object.

## Geometry and partial snapshots

The grid is standardized **120 × 80 native units, not metres**. Goal centre is
(120,40), posts are (120,36) and (120,44). Distance is Euclidean in that grid;
angular width is `atan2(abs(cross(post vectors)), dot(post vectors))`. This avoids
incorrect goalpost coordinates, angle wrapping and near-goal cancellation.
Bearing is the vector from shot to goal centre. Exactly coincident goal-centre
bearing and post-coincident angular width are undefined (`null`), not zero.

Defensive features refer to **recorded opponents**. They include nearest recorded
opponent, counts inside the finite shooter-to-goalposts triangle, and unique
recorded opposition goalkeeper depth/lateral offset. A missing frame yields
missing counts, not zero defenders. Invalid player coordinates and unknown
teammate flags are counted separately. Multiple recorded opposing keepers make
keeper geometry undefined. These fields do not establish complete defense,
visibility, a strict physical bound, motion or joint mechanics. WSL has no 360
visibility polygons at this pin. No body-pose or SPL data are blended into this
shot-context adapter.

## Outputs

All generated raw and row-derived data remain local/ignored:

- `data/tactical/soccer/contexts.jsonl`: context, eligibility cohort and quality,
  without targets for any season
- `data/tactical/soccer/development_targets.jsonl`: development goal labels only
- `data/tactical/soccer/source_manifest.json`: pinned blob and SHA-256 evidence
- `reports/tactical/soccer/summary.json`: `sport`, `task`, `phase="descriptive"`,
  hashes, population, units, denominators, exclusions and quality; development-only
  distance, angular-width, nearest-recorded-opponent and body-part bins with shot
  count, label denominator and observed goals. These are sample descriptions,
  not predicted probabilities or causal effects
- `development_plot` in the local summary: at most 200 development locations,
  chosen by fixed SHA-256(event UUID) order, with observed-goal and recorded-context
  availability flags. This outcome-independent subset is for a local pitch plot;
  the full development count remains visible

Test fixtures are invented. Tests cover native units/goalposts, mirrored bearing,
finite triangle, degenerate angles, outliers, all misses, missing/partial frames,
keeper ambiguity, outcome/future mutation, protected cohorts, deterministic sample,
and source-hash tampering.

## Attribution and publication

Data: StatsBomb Open Data; modified through original local descriptive parsing.
The source has a custom noncommercial research agreement, not a general MIT or
CC-BY grant. Its exact local agreement and the verified original provider logo
are recorded by hash in the summary. The logo is the source's actual
`img/SB - Icon Lockup - Colour positive.png`; it is not invented or redrawn.
The local workbench owner must display the supplied logo and attribution where
appropriate; no general brand permission or external publication is implied.
No raw rows, row derivatives, weights, figures or public report are released by
this adapter. See the research publication policy before any separate release.
