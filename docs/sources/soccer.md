# Soccer source: English Premier League results

## Provenance and license

The adapter reads the ten `en.1.json` season files for **2015–16 through
2024–25** from [OpenFootball's football.json repository](https://github.com/openfootball/football.json).
It pins commit
[`e6744429ee395bc86f247348c6184bb08d4eb361`](https://github.com/openfootball/football.json/commit/e6744429ee395bc86f247348c6184bb08d4eb361),
dated 2026-09-22, rather than following a changing branch.

The upstream [LICENSE.md](https://github.com/openfootball/football.json/blob/e6744429ee395bc86f247348c6184bb08d4eb361/LICENSE.md)
contains **CC0 1.0 Universal**. The repository explicitly applies its public-domain
dedication to its schema, data, and scripts. This source-data dedication is
separate from this project's MIT software license. Attribution is retained for
provenance; no league affiliation or endorsement is implied. No paid API,
account, betting odds, logo, or private personal data is used.

Raw URL template:

```text
https://raw.githubusercontent.com/openfootball/football.json/e6744429ee395bc86f247348c6184bb08d4eb361/{season}/en.1.json
```

`download(raw_dir)` saves files as `en.1-{season}.json`, retains the upstream
license and the date-audit source described below, and uses the project's
shared fetcher to record SHA256 provenance. The original bytes are never edited.
Raw downloaded data is a local cache, not code to commit or publish.

## Coverage

The pinned source contains **3,800 scored fixtures**, 380 in each season, with
20 clubs per season and **34 distinct normalized clubs** across the decade.
The normalized match-date range is **2015-08-08 through
2025-05-25**. Each ordered home/away pair appears once per season.

| Season | Completed fixtures | First date | Last date |
| --- | ---: | --- | --- |
| 2015–16 | 380 | 2015-08-08 | 2016-05-17 |
| 2016–17 | 380 | 2016-08-13 | 2017-05-21 |
| 2017–18 | 380 | 2017-08-11 | 2018-05-13 |
| 2018–19 | 380 | 2018-08-10 | 2019-05-12 |
| 2019–20 | 380 | 2019-08-09 | 2020-07-26 |
| 2020–21 | 380 | 2020-09-12 | 2021-05-23 |
| 2021–22 | 380 | 2021-08-13 | 2022-05-22 |
| 2022–23 | 380 | 2022-08-05 | 2023-05-28 |
| 2023–24 | 380 | 2023-08-11 | 2024-05-19 |
| 2024–25 | 380 | 2024-08-16 | 2025-05-25 |

## Audited date correction: July 2020

The pinned 2019–20 JSON mislabels **66 matches** in matchdays 32–38 as July
**2019**. Using those dates unchanged would place end-of-season outcomes before
the season began and invalidate chronological features and evaluation.

The source's original [2019–20 Football.TXT file](https://github.com/openfootball/england/blob/b17e8f01707d83d2ce1790c14d4a5eeb35987825/2019-20/1-premierleague.txt)
explicitly specifies the season range as August 2019–July 2020, and its July
weekday labels match 2020. That evidence is pinned separately at England-source
commit `b17e8f01707d83d2ce1790c14d4a5eeb35987825`. The Premier League's
[official updated fixture list](https://www.premierleague.com/en/news/1240976)
and [Newcastle–Liverpool final-day report](https://www.premierleague.com/en/news/1733122)
also establish the July 2020 chronology.

The adapter changes the year only when all conditions hold:

- Season is `2019-20`
- Original date is between `2019-07-01` and `2019-07-26`, inclusive
- Round is exactly `Matchday 32` through `Matchday 38`

The month, day, teams, and scores remain unchanged. This is an explicit
source-data correction, not inferred or simulated match data. Tests cover both
the correction and rejection of unrelated out-of-season dates. The dataframe's
`corrected_july_2020_dates` attribute reports the applied count; original source
bytes and the audit TXT remain available locally. Changing the source pin
requires re-auditing this exception rather than assuming it remains appropriate.

## Schema and normalization

- `team1` becomes home `side_a`; `team2` becomes away `side_b`
- Only complete `score.ft` pairs are outcomes; halftime scores are never substituted
- Unplayed and incomplete fixtures are omitted; malformed or negative, fractional,
  nonnumeric, boolean, or nonfinite scores cause an error
- Teams lose an exact trailing ` FC` to bridge the source's naming change in
  2020–21; `AFC Bournemouth` and trailing `AFC` names remain intact
- Match dates and `available_date` are normalized pandas datetimes at day precision
- `available_date = date` is a modeling convention, **not a claim about the
  original provider's historical publication timestamp**
- `neutral = False` represents nominal home/away league scheduling. It is not
  an assertion about attendance, crowd advantage, or individual venue changes
- Event IDs combine the league, season, and a deterministic SHA256 digest of the
  normalized ordered team pair. They survive score/date correction and distinguish
  home and away legs. Duplicate identities cause an error
- The loader returns chronological rows but does not derive any features

The dataframe also records source commit, license, loaded files, skipped
incomplete-record count, and date-correction count in `attrs`. Load only the
configured file names; license files, provenance sidecars, and unrelated seasons
cannot accidentally become observations.

## Limitations and responsible interpretation

This is a community-maintained historical fixture/result source, not an official
live feed. A complete fixture count does not guarantee error-free historical
data. The documented 2019–20 issue illustrates why validation is required.
No historical "as-of" snapshots are supplied, so later provider corrections
cannot be reconstructed as they would have appeared on the original match date.

The dataset has no player availability, injuries, lineups, expected goals,
possession, coaching-change, transfer, weather, or market features. Club history
is limited to these Premier League seasons; promoted teams have incomplete or
absent prior history. The COVID interruption and matches without ordinary
attendance are real regime changes, not neutral-site labels.

Because only date-level availability is used, features for all games on the
same day must be frozen before any of that day's results are incorporated.
Predictions and reported metrics should be retrospective, held-out research
results. They do not establish profitability, causal effects, or reliable
current-season forecasts. No prediction should be described as certain.

## Verification

All **14 offline unit tests** in `tests/test_soccer_adapter.py` passed. They cover the adapter
contract, complete-score filtering, invalid records, team alias normalization,
stable IDs, reverse fixtures, chronological sorting, duplicate rejection,
missing files, pinned download URLs, and the bounded July-2020 correction.

An independent source audit matched all **66 corrected July fixtures** to the
pinned original TXT on home team, away team, full-time goals, month/day, and
2020 weekday labels, with no unmatched records.

The real downloaded-data audit verified 380 unique fixtures and 20 clubs in
every season, exactly 19 home and 19 away fixtures per club per season, and no
club appearing twice on one date. No incomplete-score matches were dropped
from these pinned files. All 13 downloaded source/evidence files have URL,
retrieval-time, byte-count, and SHA256 sidecars. Both retained JSON-source and
England-source license files identify CC0 1.0 Universal.

Research/source inspection date: **2026-10-11 UTC**.
