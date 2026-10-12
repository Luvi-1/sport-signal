# Baseball source: Retrosheet game logs

> The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

## Source and rights

- Publisher: [Retrosheet](https://www.retrosheet.org/)
- Official [game-log download catalog](https://www.retrosheet.org/gamelogs/index.html)
- Official [161-field format guide](https://www.retrosheet.org/gamelogs/glfields.txt)
- Official [data-use notice](https://www.retrosheet.org/notice.txt)
- Sources and rights checked on **2026-10-11**

Retrosheet permits reuse, redistribution, and commercial products, subject to prominently displaying the acknowledgment above. Retrosheet retains copyright; this dataset is **not licensed under the project's MIT code license**. The publisher does not guarantee accuracy and can revise historical records. This is an attribution-based permission notice, not a claim that the data has a CC or OSI license. Preserve the acknowledgment in any downstream report, dashboard, data transfer, or product using the data.

The repository does not include downloaded archives. The reproducible downloader retrieves public, account-free official files and uses the common fetch helper to record SHA-256 provenance locally. No paid data, credentials, betting lines, logos, or personal/private information are required by this adapter.

## Frozen scope and files

The experiment uses **2015–2024 inclusive**, from the individual annual regular-season archives. Later seasons are intentionally outside this experiment's fixed scope. The official catalog lists postseason and All-Star downloads separately; those files are not requested or parsed.

| Season | Official ZIP |
| --- | --- |
| 2015 | https://www.retrosheet.org/gamelogs/gl2015.zip |
| 2016 | https://www.retrosheet.org/gamelogs/gl2016.zip |
| 2017 | https://www.retrosheet.org/gamelogs/gl2017.zip |
| 2018 | https://www.retrosheet.org/gamelogs/gl2018.zip |
| 2019 | https://www.retrosheet.org/gamelogs/gl2019.zip |
| 2020 | https://www.retrosheet.org/gamelogs/gl2020.zip |
| 2021 | https://www.retrosheet.org/gamelogs/gl2021.zip |
| 2022 | https://www.retrosheet.org/gamelogs/gl2022.zip |
| 2023 | https://www.retrosheet.org/gamelogs/gl2023.zip |
| 2024 | https://www.retrosheet.org/gamelogs/gl2024.zip |

## Schema and inclusion rules

The loader reads exactly one `GLYYYY.TXT` member per annual ZIP, case-insensitively, without extracting archive members. Unexpected fields, invalid dates/team IDs/game numbers, and duplicate event IDs cause explicit errors rather than silently changing the training sample.

| Output | Retrosheet field(s), one-based |
| --- | --- |
| `event_id` | `retrosheet:` + home team (7) + original date (1) + game number (2) |
| `date` | Original game-start date (1), normalized to midnight |
| `season` | Annual archive year, string; checked against date |
| `side_a`, `side_b` | Designated home (7), visiting (4) Retrosheet team codes |
| `score_a`, `score_b` | Final home (11), visiting (10) runs, floats |
| `neutral` | `False`, a designated-home convention, **not verified venue neutrality** |
| `available_date` | Completion date from field 14 when present; otherwise original date |

- Tied final scores are excluded because the shared prediction target is binary, home win versus away win
- Missing, nonnumeric, nonfinite, negative, or noninteger scores are excluded
- Forfeits and no-decisions (nonempty field 15) are excluded, because scores alone can conflict with the official winner
- Official annual-file membership defines the regular-season scope; this also retains any regular-season tiebreaker games contained there
- Numbered doubleheaders remain separate games with stable IDs. No row-order suffix is used
- Counts of every exclusion category, source rows, and delayed completions are attached to the returned frame's `attrs`
- `load()` can read a subset of cached annual archives for development; `download()` always requests all ten years. Inspect `attrs['years_loaded']` before claiming full coverage

## Chronological validity and limitations

A suspended game's final outcome is not available on its original start date. The adapter therefore retains the original event date while delaying its result availability to the documented completion date. The feature builder must require **historical `available_date` strictly earlier than the predicted `date`**, so neither suspended games nor an earlier game of a same-day doubleheader leaks into a prediction without actual start/end times.

The dataset does not provide an immutable, timestamped historical snapshot of when every correction was published. `available_date` models game completion, not publication latency. The source's current corrected records are suitable for a retrospective experiment, not proof of a deployable point-in-time trading/backtesting feed. Historical box-score fields, winning pitchers, and other postgame information are deliberately absent from the modeling schema. Designated home advantage may be misrepresented for international or other neutral-site games. Team IDs are retained as published, and season-to-season roster, rules, and schedule shifts remain modeling limitations.

## Verification

Synthetic unit tests are offline and do not redistribute any source rows. They cover home/away mapping, types, doubleheaders, exclusion counts, delayed completion, duplicate IDs, malformed rows/dates, wrong ZIP members, and path-safe ZIP reading. Real-data counts and coverage are recorded below after running the downloader and loader.

### Observed snapshot, 2026-10-11

All ten URLs downloaded successfully. **22,763 source rows → 22,762 modeled games**, covering 2015-04-05 through 2024-09-30. One tied game was excluded; there were no invalid-score or forfeit/no-decision exclusions. All modeled event IDs were unique, and **31 games** had result availability delayed to a later completion date. The observed overall home-win rate is 53.251%; it is descriptive only and is not an out-of-sample performance metric.

| Season | Included games | First original date | Last original date |
| --- | ---: | --- | --- |
| 2015 | 2,429 | 2015-04-05 | 2015-10-04 |
| 2016 | 2,427 | 2016-04-03 | 2016-10-02 |
| 2017 | 2,430 | 2017-04-02 | 2017-10-01 |
| 2018 | 2,431 | 2018-03-29 | 2018-10-01 |
| 2019 | 2,429 | 2019-03-20 | 2019-09-29 |
| 2020 | 898 | 2020-07-23 | 2020-09-27 |
| 2021 | 2,429 | 2021-04-01 | 2021-10-03 |
| 2022 | 2,430 | 2022-04-07 | 2022-10-05 |
| 2023 | 2,430 | 2023-03-30 | 2023-10-01 |
| 2024 | 2,429 | 2024-03-20 | 2024-09-30 |

Archive SHA-256 values for this observed snapshot (future upstream corrections can change these):

| Archive | SHA-256 |
| --- | --- |
| gl2015.zip | `3e5e02b2fc5cf4b0efc210ea461a7370d9f95ee02054109f5a8448a5408c060e` |
| gl2016.zip | `c447193bc9d0084c95e1d3f3b5b8e68770b4e69f370082d29c58649e4f151819` |
| gl2017.zip | `9612a0200236c9661761ae33819ed0d0782450bbf38e4af95930ab2e8a75d933` |
| gl2018.zip | `7c1cc0348444b003152d86b585bf660746ae9f52ecc628ef31916a059987b779` |
| gl2019.zip | `af624738230530f2f59e141c84cb31a97c2298727301e4be8308266f6e49d229` |
| gl2020.zip | `c5138dcda34809223085f036354e61a743958337c9e19a86036406819cfe9752` |
| gl2021.zip | `19cc610732f3b15f69dbcfb72e048e512adcc8f38c39ae33f2d5fe4feb9a50bb` |
| gl2022.zip | `c1d5416ed28b172c70fb88e8afdfbccfddddd204d9dcb8e326c4052b3d2d7aa2` |
| gl2023.zip | `c1461a3ed965c428406f288201b7021fcf051e5b43cca9143c8f1f0b78c072e1` |
| gl2024.zip | `3089e0a895e70a6fd244d31fe822bc4d856d0987458e86b5acc5df1aa297d250` |

Verification command: `python -m unittest discover -s tests -p test_baseball_adapter.py -v` — **12/12 tests passed**. The real downloader and loader also completed successfully with the counts above.
