# Data rights and attribution

The MIT license covers original project code. It does not relicense datasets,
provider documentation, or covered adaptations. This repository distributes code,
provenance hashes, aggregate research reports, and one explicitly CC-BY-4.0
normalized NFL input snapshot under snapshots/. Original raw records, per-game derived
features/predictions, and trained weights are ignored by Git and recreated locally.

| Sport | Provider | Published rights | Details |
| --- | --- | --- | --- |
| Soccer | OpenFootball | CC0 1.0 Universal | [Source audit](docs/sources/soccer.md) |
| Baseball | Retrosheet | Copyright retained; broad reuse subject to required attribution | [Source audit](docs/sources/baseball.md) |
| American football | Lee Sharpe / nflverse, nflverse-data schedules release | CC BY 4.0 as published by distribution repository | [Source audit](docs/sources/football.md) |
| Tennis | Jeff Sackmann / Tennis Abstract; preserved Kadantte archive | CC BY-NC-SA 4.0 | [Source audit](docs/sources/tennis.md) |

## Required Retrosheet acknowledgment

The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

[Retrosheet notice](https://www.retrosheet.org/notice.txt)

## NFL attribution

NFL game/schedule data: Lee Sharpe and nflverse, distributed through the
[nflverse-data schedules release](https://github.com/nflverse/nflverse-data/releases/tag/schedules)
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Retrieved 2026-10-11.
Changes: regular-season and year filtering, exclusion of tied/uncompleted results,
franchise alias normalization, outcome-only schema, historical features and
aggregate evaluations. No endorsement by the provider or NFL is implied.

## Tennis restrictions

Tennis data is by [Jeff Sackmann / Tennis Abstract](https://www.tennisabstract.com/),
based on the originally published tennis_atp repository and preserved at
[Kadantte/tennis_atp](https://github.com/Kadantte/tennis_atp).
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) requires
attribution, non-commercial use and share-alike for covered adaptations.
Changes here include completed-score filtering, canonical player ordering,
conservative delayed availability, derived pre-tournament features and evaluation.

As a conservative project policy, tennis-derived reports and locally trained
tennis artifacts are designated CC BY-NC-SA 4.0, including reports/tennis and the
tennis portions of combined reports. Commercial deployment needs a separately
cleared source or permission from the rights holder. Do not treat the code's MIT
license as permission to commercialize these data or covered adaptations.

Licenses do not grant trademarks, player likeness rights, endorsement, or a
warranty of accuracy. Check the source's current terms before any broader reuse.

## Bundled normalized NFL snapshot

`snapshots/nfl_regular_2010_2025.csv.gz` is a licensed filtered/normalized data
representation, not an original download. Its JSON provenance distinguishes
compressed/uncompressed hashes from the full nflverse source hash, states the
retrieval date and transformations, and credits Lee Sharpe/nflverse. The complete
provider CC BY 4.0 license is retained beside it. No odds or private user data are
included. This does not authorize bundling tennis data under the NFL license.
