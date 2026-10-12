# Tennis source, target, and limitations

## Source and immutable version

- Creator: **Jeff Sackmann / Tennis Abstract**, ATP Tennis Rankings, Results, and Stats
- Original project: <https://github.com/JeffSackmann/tennis_atp>
- Retrieval mirror: [Kadantte/tennis_atp](https://github.com/Kadantte/tennis_atp), a preserved copy retaining the original attribution and license notice; this is not an official ATP data feed
- Pinned commit: [`712be0c5ade693cdab9e69c23a71a0edf5a23c44`](https://github.com/Kadantte/tennis_atp/tree/712be0c5ade693cdab9e69c23a71a0edf5a23c44), dated 2026-06-08
- Retrieved and checked: 2026-10-11 UTC
- Files: `atp_matches_2010.csv` through `atp_matches_2024.csv`, plus the source README and data dictionary
- [Pinned README](https://github.com/Kadantte/tennis_atp/blob/712be0c5ade693cdab9e69c23a71a0edf5a23c44/README.md) and [pinned data dictionary](https://github.com/Kadantte/tennis_atp/blob/712be0c5ade693cdab9e69c23a71a0edf5a23c44/matches_data_dictionary.txt)

The annual files cover men's tour-level main-draw singles, including Davis Cup and other competitions represented in those files. The adapter does not ingest doubles, qualifying/challenger files, futures, or seasons outside 2010–2024. The source is a retrospectively curated snapshot and can contain corrections made after the match; it is not a contemporaneously archived prediction feed.

The shared download helper saves each file's exact URL, byte count, SHA256, and retrieval time in an adjacent `.source.json`. Cached bytes must match their provenance before reuse. The adapter pins the source commit, so a later upstream change cannot silently replace this experiment's inputs. Raw files and sidecars are local cache artifacts, not source-code fixtures.

## License and attribution

The source README licenses the tennis data under **[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/)** and attributes it to **[Jeff Sackmann / Tennis Abstract](https://www.tennisabstract.com/)**. The mirror does not replace that creator attribution.

The project's original implementation code is separately MIT licensed. This does **not** relicense the downloaded tennis data. As a conservative distribution choice, processed tennis data, tennis-specific fitted models, predictions, and derived tennis report artifacts should retain the creator attribution, source commit, change notice, and CC BY-NC-SA 4.0 designation. Do not represent these artifacts as unrestricted commercial assets. No publication or commercial-use permission is implied by this experiment.

Suggested artifact notice:

> Uses ATP tennis data by Jeff Sackmann / Tennis Abstract, preserved in Kadantte/tennis_atp at commit 712be0c5ade693cdab9e69c23a71a0edf5a23c44. Source data and these derived tennis artifacts: CC BY-NC-SA 4.0. Changes: completed-match filtering, outcome-independent participant ordering, conservative result-availability dates, and statistical modeling. Original project code: MIT.

## Prediction target and common schema

The target is **whether side A wins, conditional on the match being completed and the result passing the documented score checks**. It is not a probability covering every scheduled match. Excluding retirements and walkovers creates a conditional sample; an operational model covering those outcomes needs a different target and validation design.

Each output row has:

| Field | Meaning |
|---|---|
| `event_id` | `atp:{tourney_id}:{match_num}`; duplicates fail loudly |
| `date` | Normalized source `tourney_date`, a tournament-start proxy |
| `season` | Annual source-file season, preserved as a string |
| `side_a`, `side_b` | Lexicographically sorted player ID strings, independent of winner, rank, or name |
| `score_a`, `score_b` | Binary outcome values `1.0` and `0.0`, not games or sets won |
| `neutral` | Always `True`, meaning no modeled home-side advantage |
| `available_date` | Tournament-start proxy plus 21 days |
| `surface` | Source court surface; blank becomes `unknown` |
| `rank_a`, `rank_b` | Source pre-tournament ranks remapped to the assigned sides; missing/invalid values become NaN |

The source README and dictionary establish that ranking fields are measured as of the tournament date or the most recent prior ranking date. They can therefore be used as tournament-start information. Missing ranks are not converted to zero. Post-match statistics, minutes, winner/loser labels, and score strings never enter the adapter's feature-facing output. The winner/loser IDs and score are used only to validate the completed result, assign participants, and create outcome labels.

`neutral=True` is a modeling convention, not a claim that every stadium is geographically neutral. In particular, Davis Cup host effects are not represented.

## Conservative timing and leakage prevention

An actual match timestamp is unavailable. A tournament date can place every round on the same nominal day, and the first tournament of a season can start in the previous December. The adapter preserves that date instead of inventing round dates; the file determines `season`.

The implementation delays **all** results by 21 days from the tournament-start proxy. Downstream features must consume a result only when its `available_date` is **strictly before** the prediction row's `date`. This blocks same-tournament results from informing later rounds and also excludes some genuinely available recent history. It produces a deliberately conservative tournament-start-style backtest, not a claim to know the source's publication time or an exact live, match-by-match backtest. Longer or unusually interrupted competitions would require individually verified completion dates.

Train/validation/test boundaries should use chronological dates and respect result availability. The 21-day lag can cross a calendar boundary; file season alone is not evidence that a label was already observable.

## Filtering and quality checks

1. Reject malformed schemas, dates, player IDs, and duplicate event IDs with a clear exception
2. Exclude any result marked retirement, walkover, default, or abandoned, even if the numeric score looks complete
3. Require a complete score consistent with the source `best_of` field and listed winner
4. Support ordinary sets, extended advantage sets, 13–12 tiebreak sets, bracketed ten-point deciding match tiebreaks, and Next Gen four-game sets when consistent with the source format
5. Exclude incomplete sets, ambiguous `[1-0]`/`[0-1]` shorthand, unsupported formats, a score contradicting the listed winner, or extra sets after a match is already won

The source has some `best_of=3` rows with three won sets, including historical Davis Cup and Next Gen matches. Those records are excluded as internally inconsistent rather than silently changing source data. An excluded row is not necessarily a match that failed to finish; the additional quality gate deliberately sacrifices coverage where evidence is ambiguous. No outcome is synthesized, and no player/rank/score corrections are guessed.

## Verified snapshot coverage

The pinned 2010–2024 files contain **42,571 source rows**:

- **40,896 retained completed, score-consistent results**
- **1,520** retirement/walkover/default/abandoned exclusions
- **155** incomplete, ambiguous, unsupported, or inconsistent-score exclusions
- Tournament-start proxy range: **2010-01-03 through 2024-12-18**
- Missing rank A: **328** rows; missing rank B: **546** rows
- Side A win fraction: **0.510197**, a useful check that A is not defined as the winner

| Season | Retained results |
|---|---:|
| 2010 | 2,908 |
| 2011 | 2,890 |
| 2012 | 2,897 |
| 2013 | 2,818 |
| 2014 | 2,773 |
| 2015 | 2,830 |
| 2016 | 2,794 |
| 2017 | 2,749 |
| 2018 | 2,785 |
| 2019 | 2,709 |
| 2020 | 1,427 |
| 2021 | 2,634 |
| 2022 | 2,826 |
| 2023 | 2,887 |
| 2024 | 2,969 |

These are source-season counts, not counts grouped by the calendar year of the tournament-start proxy. The frame's `attrs` additionally records source row count, exclusion counts, loaded seasons, source commit, and result delay for programmatic auditing.

## Offline verification

`python -m unittest discover -s tests -p test_tennis_adapter.py -v`

Tests use entirely synthetic rows. They cover fixed side assignment across opposite outcomes, rank mapping, missing ranks/surface, result delay, prior-December starts, completed-score formats, exclusion behavior, malformed data, duplicate IDs, empty output schemas, and immutable download URLs. The downloaded source rows are never embedded into tests.

## Realized-matchup condition

Evaluation conditions on the matchups that actually occurred, with frozen
pre-tournament information. Later-round opponents are not known at tournament
start. These probabilities are not a forecast of the complete fixture list or
a bracket simulation; the matched-pair sampling condition must be retained.

Equal-availability tournament results update in deterministic event-ID order,
not verified match chronology. Consequently Elo updates and last-ten features
are reproducible historical approximations, not exact within-tournament sequences.
