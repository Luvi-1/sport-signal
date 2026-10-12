# American football: NFL regular-season results

## Source and rights

The adapter uses the **official nflverse-data schedules release**, maintained by
nflverse from Lee Sharpe's game/schedule data:

- [Release and maintainer attribution](https://github.com/nflverse/nflverse-data/releases/tag/schedules)
- [CSV download](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv)
- [Schedule data dictionary](https://nflreadr.nflverse.com/articles/dictionary_schedules.html)
- [Official Python loader using this release](https://github.com/nflverse/nflreadpy/blob/main/src/nflreadpy/load_schedules.py)

**Dataset license: CC BY 4.0 as published by the distribution repository.** The
[nflverse-data license](https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md)
contains the Creative Commons Attribution 4.0 International terms. The official
[nflreadpy data-license statement](https://github.com/nflverse/nflreadpy/blob/main/README.md#license)
also distinguishes broadly CC BY 4.0 data from its MIT software. No FTN charting
data is used here.

Retain attribution, a [CC BY 4.0 license link](https://creativecommons.org/licenses/by/4.0/),
and a description of changes when sharing covered material. The license is not
an endorsement, trademark grant, or warranty of third-party rights. Commercial
deployment should assess its own rights requirements. This project's MIT license
applies to its original code, not to downloaded data.

Suggested attribution:

> NFL game/schedule data: Lee Sharpe and nflverse, distributed through the
> nflverse-data schedules release under CC BY 4.0. Retrieved 2026-10-11.
> Changes: selected 2010–2024 regular seasons, removed tied/uncompleted results,
> normalized relocated franchises, and retained only schedule/result fields.
> No endorsement by the data providers is implied.

The downloader deliberately uses this licensed distribution. The separate
upstream `nflverse/nfldata` repository did not expose a repository license in our
2026-10-11 check; do not independently label that repository MIT or infer its
rights solely from another repository. This project does not redistribute the
upstream CSV or publish anything automatically.

## Snapshot and reproduction

Verified download on 2026-10-11 at 06:18:33 UTC:

- Local file: `data/raw/football/games.csv`
- Size: 2,184,000 bytes
- SHA256: `ab8580e05d7469154c3948e56730e6bdf028dd6e4757fa16aa4663759e4b244b`
- Published asset update: 2026-10-11 at 05:16:34 UTC
- Entire downloaded file: 7,548 rows; the model parser restricts seasons/types
- Provenance: the shared downloader writes URL, byte count, timestamp and SHA256
  to `games.csv.source.json`, and verifies the cached bytes on reuse

The release tag is mutable: the release description says assets update when
upstream changes. A Git tag does **not** pin these asset bytes. Preserve the raw
file and sidecar privately, and check the repository's snapshot lock for an exact
reproduction. A future fresh download may differ and must be treated as a new
snapshot, not silently described as reproducing these results.

For a source cross-check only, the nine allowed fields matched the corresponding
CSV at upstream commit
[`e53b7a78ada20761759cbc7102f7b645e6b729ad`](https://github.com/nflverse/nfldata/commit/e53b7a78ada20761759cbc7102f7b645e6b729ad).
The adapter does not use that upstream URL as a fallback.

## Scope and observed coverage

The analysis selects **season** 2010 through 2024 inclusive and `game_type=REG`.
January dates stay attached to their NFL season rather than their calendar year.
Playoffs and preseason are excluded. These counts were computed from the actual
download, not generated fixtures:

| Season | Completed regular-season games | Binary-model games |
| --- | ---: | ---: |
| 2010 | 256 | 256 |
| 2011 | 256 | 256 |
| 2012 | 256 | 255 |
| 2013 | 256 | 255 |
| 2014 | 256 | 255 |
| 2015 | 256 | 256 |
| 2016 | 256 | 254 |
| 2017 | 256 | 256 |
| 2018 | 256 | 254 |
| 2019 | 256 | 255 |
| 2020 | 256 | 255 |
| 2021 | 272 | 271 |
| 2022 | 271 | 269 |
| 2023 | 272 | 272 |
| 2024 | 272 | 272 |
| **Total** | **3,903** | **3,891** |

The selected dates run from **2010-09-09 to 2025-01-05**. All 3,903 selected
rows have final scores. Twelve tied games are excluded, including one neutral
game; 52 neutral games remain. There are 32 franchise identities after alias
normalization. The 2022 total is one lower than the usual expanded schedule:
the [NFL cancelled Buffalo–Cincinnati](https://www.nfl.com/_amp/week-17-buffalo-cincinnati-game-will-not-be-resumed-neutral-afc-championship-gam).
That event is absent from the completed-result snapshot and is not imputed.

## Parsing contract and exclusions

`download(raw_dir)` returns the path(s) downloaded through the shared provenance
helper. `load(raw_dir)` returns the common event schema, chronologically sorted:

| Output | Derivation |
| --- | --- |
| `event_id` | Original `game_id`, unique string |
| `date` | `gameday` parsed to normalized date |
| `season` | NFL season year, string |
| `side_a`, `side_b` | Designated home, away franchise |
| `score_a`, `score_b` | Home and away final scores as floats |
| `neutral` | `location == "Neutral"` |
| `available_date` | Same date as `date`; see timing limitation below |

Franchise continuity mappings are STL/LA → LAR, OAK → LV, and SD → LAC.
Source event IDs are preserved unchanged. Designated home does not imply home
advantage at a neutral venue. The loader rejects duplicate event IDs, unknown
locations, missing identities, invalid dates, self-matches and invalid scores.
Rows without both final scores are excluded.

Only these source columns are parsed: `game_id`, `season`, `game_type`,
`gameday`, `home_team`, `away_team`, `home_score`, `away_score`, `location`.
The raw distribution includes extra fields. All prices, moneylines, spreads,
totals lines and market odds are excluded via a parser allowlist, as are player,
coach, weather and play-by-play fields. The tests verify the output schema
using invented data; they do not redistribute real source rows.

## Modeling limitations

- The binary target is a home win **conditional on the game not being tied**.
  Ties are also absent from this baseline's historical feature updates; this
  small but explicit selection should not be mistaken for unconditional win
  probability. A three-class/draw-aware extension would address it.
- `available_date` is a date-level convention, not a verified data-publication
  timestamp. Downstream features must use strictly earlier result dates; all
  games on the same date must be predicted before any of their scores update
  history. This prevents fictitious within-day information availability.
- This is a retrospective snapshot. Corrections, location designations and
  franchise mappings are not historical point-in-time archives. A strict
  deployment backtest requires archived as-of data and actual publication times.
- The 16-to-17-game schedule change, relocations and neutral fixtures mean that
  season length and home-advantage assumptions need monitoring.
- Sparse games per team, major roster turnover and unmodeled injuries limit a
  results-only model. These findings are research, not operational forecasts.
