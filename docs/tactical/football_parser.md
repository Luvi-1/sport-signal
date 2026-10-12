# NFL stage-one source and descriptive module

Status: implemented 11 October 2026. **Descriptive only. No model has been fitted,
scored, selected or calibrated.** The predictive gate is unconditionally closed in
this module. Prior research proposals are not an approved numerical protocol.

## What this answers

For recorded NFL regular-season run/pass plays, what final-at-snap context,
formation, personnel and motion do the licensed files actually contain? In the
2023 development population only, how often was the recorded play a realized
dropback within explicitly counted context groups?

The row unit is a play. The denominator is REG, down 1–4, recorded `run` or `pass`,
with observed false kneel, spike and deleted flags. Nullified `no_play` rows,
special teams, postseason, invalid downs and unknown eligibility flags are
excluded. The word “competitive” describes this operational cohort; it does not
exclude blowouts or all late-game situations. Sequential exclusions partition all
PBP records, rather than double-counting records failing several conditions.

Realized dropback is the union of `qb_dropback == 1`, `sack == 1` and
`qb_scramble == 1`. It includes sacks and scrambling rushes. It is not offensive
play intent or an RPO's original read. Eligibility itself is retrospectively
observed, so this is not an all-called-plays pre-action forecast.

## Three clocks and limits

1. **Physical event:** final observable physical state at the ball snap
2. **Observation/publication:** after-game FTN charting; 2023-onward participation
   is released after the postseason. The preserved download timestamp is a third
   record of acquisition, not evidence of historical real-time availability
3. **Decision:** the offense chose its play earlier. This supports subsequent
   film-review/scouting associations; it cannot prescribe the earlier play call
   or establish that motion or formation caused an outcome

[FTN loader](https://nflreadr.nflverse.com/reference/load_ftn_charting.html),
[participation loader](https://nflreadr.nflverse.com/reference/load_participation.html),
[FTN dictionary](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html),
and [participation dictionary](https://nflreadr.nflverse.com/articles/dictionary_participation.html)
are the official measurement/source documentation used in the research brief.
This parser validates representation, not independent physical truth.
Inter-rater reliability, whether later frames informed a present-state annotation,
position-label errors and historical delivery latency are not established here.

## Pinned acquisition and rights

`experiments/tactical/football.py` hard-pins ten SHA-256 values: participation and
FTN charting for 2022–2025, plus 2023 and 2025 PBP. It checks bytes, source URL,
retrieval timestamp and sidecar hash against the actual file before parsing.
Changed sources, missing provenance and unreviewed source names fail closed.
Nothing refreshes a pin automatically.

Previously inspected sources remain in ignored `data/raw/tactical_research`.
The newly retrieved official 2023 PBP and its provenance are in ignored
`data/tactical/football`:

- URL: https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2023.csv.gz
- Retrieved: 2026-10-11T09:07:24.520360+00:00
- Bytes: 19,169,807
- SHA-256: `4649804ee0f0a40b41e51ec75a1ce921949d7fab5459213488656b92f78560e8`

Default execution is offline. Explicit `--download-missing` fetches only the
already reviewed official release paths and accepts bytes only if their hash
matches the existing pin. A changed upstream release requires review and a new
explicit pin; mirrors, accounts and paid data are not used.

Credit **nflverse** for PBP, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit **FTN Data via
nflverse** for FTN charting and 2023+ participation, and **Next Gen Stats via
nflverse** for 2022 participation, under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The report preserves attribution and license links per input. Source-specific
notices and the project's `RIGHTS_AND_DATA.md` govern adapted data; the code
license does not relicense it. Raw observations and row derivatives stay local.
Publication of aggregates or other artifacts still needs source-specific review.

## Join and feature contract

The canonical key is `(game_id, play_id)`. Source-specific IDs are renamed
explicitly. Null, fractional, negative, cross-season and duplicate keys are
rejected before joins, including duplicate rows outside the final cohort. Joins
are left, one-to-one; unmatched rows remain in the denominator, with missing
source fields. Unmatched counts are reported by season and offensive team.
A recorded-play-category breakdown is permitted only for 2023 development. Supplemental rows cannot enlarge the cohort.

Feature construction uses a fixed semantic allowlist, never all numeric fields
or a target-column denylist:

| Feature | Source and transformation | Unit / caveat |
|---|---|---|
| down, ydstogo, yardline_100 | PBP pre-play fields | down; yards; yards to opponent goal |
| qtr, quarter_seconds_remaining, half_seconds_remaining, game_seconds_remaining | PBP pre-play clocks; range-checked | quarter and seconds; overtime retains its quarter |
| score_differential | PBP pre-play field | offense minus defense points; never post-play/final score |
| posteam_timeouts_remaining, defteam_timeouts_remaining | PBP pre-play state | integer 0–3 |
| no_huddle | PBP | strict binary; unknown is missing |
| offense_is_home | PBP posteam_type | home=1, away=0; unknown missing |
| formation, formation_era | 2023+ FTN qb_location; 2022 participation formation | canonical source fixed by era |
| motion | FTN is_motion | occurrence only, not trajectory or assignment |
| defenders_in_box | FTN n_defense_box | integer 1–11; zero conservatively quarantined |
| offense_backfield | FTN n_offense_backfield | integer 0–10; zero is valid |
| starting_hash | FTN starting_hash | left, middle, right; 0/invalid missing |
| offense_rb, offense_te, offense_wr, offense_ol, offense_qb, offense_other | normalized participation personnel | stated positions, not alignment |
| defense_dl, defense_lb, defense_db, defense_other | normalized participation personnel | stated positions, not actual rushers |

Metadata (keys, season, week, team and game date), raw pre-snap source fields and
targets are separate objects; none is accidentally selected as an input through
numeric-dtype discovery. Unknown added columns are ignored. No player IDs, names
or player-derived missingness flags are included.

Excluded current-play information includes coverage, pressure, pass rushers,
blitzers, passer/receiver ID and their missingness, time-to-throw, routes, play
action, RPO labels, thrown read, yards, EPA, provider xPass, final scores and future
drive summaries. Pressure analysis is not implemented at this stage.

### Era and sentinel decisions

- 2022 NGS formation keeps `EMPTY`, `SINGLEBACK`, `I_FORM`, `JUMBO` and `WILDCAT`.
  These are not silently mapped to shotgun/under-center. The later FTN taxonomy
  mainly records QB alignment; the difference is a measurement-era change
- Whitespace and case are normalized. QB-location `0` and hash `0` become missing
- FTN box count is the single canonical box source. Participation disagreement is
  audited over paired raw valid-range values, including zeros; no averaging or
  source-dependent fallback is used
- Box `0` is ambiguous. Its raw value and count are retained, but the candidate
  feature becomes missing. Backfield `0` is a meaningful empty backfield and stays
  zero. This is a conservative measurement policy, not proof that every zero box
  value is a charting error
- RB groups RB+FB; OL groups OL+C+G+T; DL groups DL+DE+DT+NT; LB groups LB+ILB+MLB+OLB;
  DB groups DB+CB+FS+SS+S. Other stated positions stay in an explicit other count
- Legacy offensive strings often omit OL and QB: those counts remain missing,
  rather than assuming five linemen and one quarterback. Missing personnel does
  not mean zero players
- FTN strings are expected to enumerate eleven positions. Non-11 totals,
  unrecognized positions, duplicate position tokens or malformed syntax quarantine
  the whole corresponding personnel feature block. They can reflect source
  coding, nonstandard participation or measurement problems; the parser does not
  invent a correction. Raw strings remain available locally

## Actual stage-one QA

The output reproduces the earlier 2025 eligibility audit while keeping its
outcomes unread. These figures are source/measurement QA, not model performance.

| Check | 2023 development | 2025 source/eligibility QA |
|---|---:|---:|
| PBP source records | 49,665 | 48,771 |
| Eligible plays | 33,836 | 32,813 |
| Games | 272 | 272 |
| Participation matched | 33,836 / 33,836 | 32,813 / 32,813 |
| FTN matched | 33,836 / 33,836 | 32,813 / 32,813 |
| Formation missing after normalization | 88 | 56 |
| Hash zero sentinel | 66 | 48 |
| Box zero quarantined | 75 | 52 |
| Non-11 offensive personnel strings | 4 | 9 |
| Non-11 defensive personnel strings | 21 | 28 |
| Participation vs FTN box disagreements | 14 | 80 |
| Participation vs FTN formation disagreements, paired observed | 9 / 33,745 | 1 / 32,756 |

For 2023 only, the realized-dropback union contains 20,693 dropbacks and 13,143
other recorded rushes. It includes 1,410 sacks and 1,035 scrambles. The union agrees
with the PBP dropback flag on all eligible development rows.

The primary descriptive report gives 2022 and 2024 file/schema/era QA only.
A subsequent protocol-support audit acquired 2024 PBP solely for source/cohort QA,
without loading target columns; see `FOOTBALL_PROTOCOL_DRAFT.md`. It establishes
16,824 selection and 16,511 calibration eligible rows. 2024 numerical selection
and calibration work remain unstarted; 2022 PBP was not acquired.

## Workbench-facing output and reproducibility

Run from the repository root:

```sh
python -m experiments.tactical.football
python -m experiments.tactical.football --output reports/tactical/football/summary.json
python -m unittest discover -s tests -p 'test_tactical_football*.py' -v
```

The Python API is `build_summary(raw_dir=None, cache_dir=None,
download_missing=False)`. `build_panel(pbp, participation, ftn, season)` produces
separate features, metadata, raw pre-snap fields, target and QA, suitable for local
inspection. No row-level data is written by the CLI.

The JSON has `sport="american_football"`, `phase="descriptive"`, source hashes and
licenses, population/time scope, denominators, sequential exclusions, schema
inventories, joins, feature coverage, personnel validation, clocks, units and
measurement caveats. `development_distributions.tables` supplies count-labelled
2023 tables grouped by down, formation, motion, down×distance band,
down×distance×formation and formation×motion. Each cell contains `n`, dropback
count, other-rush count and the unsmoothed observed fraction. Missing categories
stay in the denominator. Small cells remain visibly small; there is no smoothing,
trained forecast, claimed calibration or performance score.

2025 PBP is read using `usecols` that omits dropback, sack and scramble labels.
`build_panel` rejects target access outside 2023; `development_distributions`
rejects other seasons and mixed-season metadata. The report contains no 2025
outcome frequencies, target-by-context profiles or performance. Previous research
already inspected some 2025 outcomes for QA, so future evaluation can be described
as performance-blind after QA, not wholly human-blind.

The future proposal (2023 train; 2024 weeks 1–9 selection and 10–18 calibration;
2025 test) remains a proposal. Exact estimand, feature choices, numerical search
budget, calibration procedure, missingness/support policy and independent review
plus owner approval are required before fitting. `predict()` always raises.

Tests cover source tampering, provenance errors, malformed/duplicate joins,
missing joins, all exclusions, nullable/sentinel handling, era-aware personnel and
formation, sacks/scrambles, empty cohorts, denominator conservation, forbidden
outcome/missingness mutation, future-row mutation and appending, shuffled joins,
2024/2025 target locks and actual cached-source reproduction. All 19 currently
pass, including the separate target-blind 2024 protocol-support audit; real-source
checks skip when their local caches are absent.

### Source-read firewall revision

The source basename, permitted season/role and pinned bytes/provenance are validated
before any header/body dataframe read. Wrong-season, unpinned and hash-mismatched
inputs cannot use a caller-supplied 2023 role to read later target columns. Join QA
contains team-only missingness outside 2023; it does not expose later play-category
counts. Read-spy and output-schema regression tests cover both boundaries. The local
summary binds the exact generator SHA-256.
