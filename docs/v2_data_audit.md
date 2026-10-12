# V2 data audit and frozen staging

Audit date: **2026-10-11 UTC**. This is a structural source audit, performed before V2 development training or holdout scoring. It computes no prediction, model metric, target rate, or model-selection statistic. Outcome fields are parsed only to preserve the existing completed-result rules and to validate score representation.

The preregistered test boundaries are in [V2 protocol](v2/PROTOCOL.md). V1's original source records, normalized data, adapters, features, models, predictions, and reports were not modified. Original-source-year normalized rows compare exactly with V1. **114 V1 files** are protected by before/after SHA256 checks. Separate actively running Laya experiment JSONL outputs are intentionally outside that V1 guard.

## Coverage and test boundaries

| Sport | New annual/season source rows | Retained in new source season | V2 target rows | Actual target date span |
|---|---:|---:|---:|---|
| MLB | 2,430 | 2,430 | 2,430 | 2025-03-18 to 2025-09-28 |
| NFL regular season | 272 | 271 | 271 | 2025-09-04 to 2026-01-04 |
| EPL | 380 | 380 | 380 | 2025-08-15 to 2026-05-24 |
| ATP singles | 2,944 | 2,805 | 2,728 | 2025-01-06 to 2025-12-17 |

MLB and ATP targets use dates in `[2025-01-01, 2026-01-01)`. NFL uses `[2025-03-01, 2026-03-01)`, which selects its 2025 regular season. EPL uses `[2025-07-01, 2026-07-01)`, selecting 2025–26.

ATP's annual 2025 source file includes **77 retained matches with tournament-start proxies in December 2024**. They are staged as pre-target history, not as target rows. At the January 1 boundary, **91 historical labels** are unavailable under the unchanged 21-day delay: those 77 rows plus 14 from the 2024 source file. The cutoff-safe development file contains 40,882 rows; ordinary pre-target history contains 40,973. These historical labels may update sequential state only after their availability dates, never fit boundary-crossing training/calibration labels. All sports still need the protocol's separate training and calibration embargoes.

Full normalized totals, including prior history, are MLB 25,192; NFL 4,162; EPL 4,180; ATP 43,701.

## Coverage, duplicates, dates, and exclusions

- MLB: 30 teams each have 162 games, yielding 2,430 distinct games. Doubleheaders are retained. There are no 2025 exclusions for missing/invalid scores, ties, forfeits, or no-decisions. Four suspended games retain their later completion dates. [MLB's schedule announcement](https://www.mlb.com/press-release/press-release-mlb-announces-2025-regular-season-schedule) confirms the March 18–September 28 endpoints
- NFL: all 272 regular-season fixtures have final scores, with 32 teams each appearing 17 times. One tied result is excluded under the unchanged conditional binary target. No duplicate IDs or same-team/same-date duplicates were found. [NFL schedule construction](https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule) confirms the 272-game, 18-week structure
- EPL: 380 unique ordered home/away pairs, 20 clubs, 19 home and 19 away games per club, and no club appearing twice on a date. No incomplete results were excluded. The [official fixture-release guide](https://www.premierleague.com/en/news/4324273) confirms 380 fixtures and August 15–May 24 endpoints
- ATP: 132 retirement/walkover/default/abandoned records and seven incomplete, ambiguous, unsupported, or inconsistent-score records are excluded, unchanged from V1's rules. The file contains 141 tournament IDs, with source level counts A=48, D=78, F=2, G=4, M=9. Its proxy-date coverage runs 2024-12-27 to 2025-12-17. The [official calendar](https://www.atptour.com/en/news/what-is-the-2025-atp-tour-calendar) provides a date reference, but **independent match-by-match completeness has not been established**. Team competitions and knockout draws do not imply a fixed match total

All final normalized datasets have zero duplicate event IDs, zero out-of-order dates, zero result-availability dates before event dates, and zero target/history event-ID overlap. Existing strict parsers reject malformed identities, dates, or completed scores rather than guessing. The absence of detected errors does not establish that retrospective provider corrections match historically available information.

The original July 2020 EPL correction remains exactly bounded to the same 66 historical records. No new-date correction was required. All 380 new EPL dates agree with the pinned original text; its weekday labels also agree with the calendar.

## Two audited V2-only normalizations

### EPL score representation

The pinned 2025–26 JSON contains 353 score objects and **27 bare two-integer arrays**. V1 accepts only score objects. V2 wraps a bare array as `score.ft` in process and passes it through the unchanged strict score validator. Before permitting this normalization, the audit compares **all 380** JSON fixtures against the separately pinned original Football.TXT on normalized ordered clubs, dates, and full-time score representation. There are zero missing pairs, date differences, score-representation differences, or weekday errors. This comparison validates the schema; it does not derive outcome distributions or model statistics.

The evidence is [the pinned 2025–26 original text](https://github.com/openfootball/england/blob/b17e8f01707d83d2ce1790c14d4a5eeb35987825/2025-26/1-premierleague.txt). Text-comparison aliases only bridge Bournemouth/AFC Bournemouth and Sunderland/Sunderland AFC; they do not alter normalized model identities. Original JSON and text bytes are preserved.

### Athletics franchise continuity

The [official Retrosheet team table](https://www.retrosheet.org/teams.zip) gives OAK/Oakland/Athletics through 2024 and ATH/Sacramento/Athletics from 2025. [MLB announced the temporary Sacramento home before 2025](https://www.mlb.com/press-release/press-release-sutter-health-park-in-west-sacramento-to-host-a-s-for-2025-2027-seasons).

V2 maps **ATH → OAK only in participant IDs**, affecting 162 new-season rows. Original event IDs, scores, dates, and V1 records remain unchanged. This preserves franchise history; it does not assume the new ballpark has the same characteristics. The decision was made from identity evidence before development training, without inspecting performance. Preliminary pre-alias staging bytes are retained locally only as an audit trail and are not model inputs.

## Provenance and rights

- Baseball uses [Retrosheet's official 2025 game logs](https://www.retrosheet.org/gamelogs/gl2025.zip). The [Retrosheet notice](https://www.retrosheet.org/notice.txt) permits reuse with its required prominent acknowledgment. The acknowledgment is preserved in [DATA_LICENSES.md](../DATA_LICENSES.md)
- NFL defaults to the **licensed normalized snapshot** at `snapshots/nfl_regular_2010_2025.csv.gz`, derived from the exact original V1 `games.csv` download from the [nflverse schedules release](https://github.com/nflverse/nflverse-data/releases/tag/schedules). It is explicitly **not the original provider bytes**. Although the original raw file already contained 2025, V1's adapter excluded it. The [CC BY 4.0 license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) and Lee Sharpe/nflverse attribution are retained. The bundled snapshot includes only normalized historical schedule/results; no market columns, odds, or private user data are included
- EPL retains OpenFootball JSON commit `e6744429ee395bc86f247348c6184bb08d4eb361` and original-text commit `b17e8f01707d83d2ce1790c14d4a5eeb35987825`. The pinned [license](https://github.com/openfootball/football.json/blob/e6744429ee395bc86f247348c6184bb08d4eb361/LICENSE.md) is CC0-1.0. It is a community source, not a league-certified feed
- ATP retains Kadantte archive commit `712be0c5ade693cdab9e69c23a71a0edf5a23c44`, preserving Jeff Sackmann / Tennis Abstract attribution and the [CC BY-NC-SA 4.0 notice](https://github.com/Kadantte/tennis_atp/blob/712be0c5ade693cdab9e69c23a71a0edf5a23c44/README.md). Non-commercial and share-alike restrictions remain; MIT covers original code only. The mirror is not an official ATP data feed

All source/evidence downloads are public and require no paid API keys or login. No access denial was bypassed. Mutable source objects and rights evidence are frozen by SHA256; future byte changes fail staging rather than silently updating the benchmark. The authorized private repository includes the compact 56,737-byte CC-BY-4.0 normalized NFL snapshot with attribution and provenance. Other raw/normalized data and derived per-event artifacts remain local ignored files. Dataset licenses remain separate from the code license.

Public fixture/franchise-source searches incidentally surfaced unsolicited EPL/MLB result snippets. They were not extracted or used to design models. The experiment claims an unused model-development/evaluation holdout, **not perfect human outcome blindness**.

## Files and reproducibility

Run from the project root:

```sh
python scripts/stage_v2_data.py --offline --frozen-nfl
```

`--frozen-nfl` is the default. Its helper validates both compressed and uncompressed snapshot hashes and the normalized 2010–2024/2010–2025 cohort hashes. Staging verifies the original-provider URL/hash as lineage, records the compressed normalized hash separately, and checks all four NFL output-table hashes against the original audit. It does not require either `data/raw/football/games.csv` or a previously generated NFL processed file. The original 272-row/one-tie/zero-unfinished audit is preserved as **recorded upstream evidence**, not falsely reconstructed from a filtered snapshot.

To use the original provider-byte branch instead:

```sh
python scripts/stage_v2_data.py --offline --original-nfl
```

That branch requires the exact original `games.csv` and its provenance sidecar; it fails when they are absent or changed. Both branches produce byte-identical normalized tables.

Omit `--offline` only to retrieve missing pinned additions/evidence. For the other three sports, V1 must already have been reproduced under its original source lock. Their original `data_manifest.json` checks are unchanged and mandatory. Staging verifies cached source sidecars, uses original parser functions with temporary restored configuration, and verifies the existing V1 guard again afterward. The added-source expected hashes are frozen directly in the staging script. Existing staged CSV bytes cannot be silently overwritten.

`--output` can target a separate directory inside `--root` for a clean reproduction check. A fresh miniature checkout was tested without any raw or processed NFL file: all 16 normalized output hashes matched the authoritative datasets exactly. The strict-original mode failed as expected in that same checkout, and deliberately mismatched upstream lineage was rejected.

- `data/v2/processed/{sport}.csv`: full normalized history plus new target period; authoritative V2 modeling inputs
- `data/v2/development/{sport}.csv`: events dated before the protocol target boundary; may still include embargoed labels
- `data/v2/pre_holdout_development/{sport}.csv`: pre-target events whose labels are strictly available before that boundary
- `data/v2/sealed/{sport}.csv`: target-only normalized rows, reserved for preregistered scoring
- `data/v2/raw/`: original source bytes and SHA256/URL/time sidecars
- `data/v2/evidence/`: immutable text-schema, rights, and franchise-identity evidence
- `data/v2/manifest.json`: exact source URLs, bytes, hashes, retrieval times, all output hashes, source pins, coverage/exclusions, boundary rules, and V1 guard; frozen mode lists 47 original source/evidence files plus one separately identified normalized NFL artifact, its provenance/loader hashes, and original-upstream lineage

“Sealed” is an explicit workflow boundary, **not filesystem encryption or access control**. Development code must avoid using target labels for candidate selection, calibration, or ensemble weights. Sequential historical feature updates must still follow strictly earlier availability. Freeze selected models and input hashes before scoring.

## Verified hashes

The complete local manifest has SHA256:

`877569be9e4a5af5264e40dbecaaaff9f36a57f9584569b9e86afb94c2107772`

### Authoritative normalized files

| Sport | All-history-plus-target SHA256 | Target-only SHA256 |
|---|---|---|
| baseball | `71e2379da9805fe296f81d737074f1d4322c6bd3d42d6a1072bbfe2fb4ebed26` | `f4b5ce821d9875446226f07b96632d9b389578c57371c3fd87fa9cec4f7aa12e` |
| football | `b0d565c308f62f0fc7bd6239b15784c2e34204f5c1ed4a58a5b063d5a643c206` | `59030c6f5d178e1e853771a8379b6ee8eacc6659d3a9ee55cb72c41b842103a7` |
| soccer | `c809a16cbbce18bfb962bb8cccf6dfa81d366180608b1fcb31ae4d827ab9208f` | `afaa60bed33ce7be6aaf836c4fe8df114d9956ee5293dd732d2f0169db514303` |
| tennis | `1123803e156fdbb4a08a31520101788575706854051231ab251c6a0e92756094` | `74ed61d14f72dd82d36dbc263e3d4677260fe769a9adac8ba97f4d7fc828dbdf` |

### New source/evidence hashes and original NFL lineage

| File | Bytes | SHA256 |
|---|---:|---|
| `gl2025.zip` | 466,269 | `f8a36120bc5f6925ffc914f964167f745e61a3421be9318e2ee24a576392693a` |
| `games.csv` | 2,184,000 | `ab8580e05d7469154c3948e56730e6bdf028dd6e4757fa16aa4663759e4b244b` |
| `en.1-2025-26.json` | 108,493 | `d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1` |
| `atp_matches_2025.csv` | 617,154 | `78c356ef9328b89ae58a17564d61c02cdad2a3a007f6b8af5cfc17992b11bb2d` |
| `2025-26-source-schema-audit.txt` | 51,782 | `38c1de56c9e9b6662c7efc1420b7e1fe00dddbb502fe72d8f759e773ba3c093b` |
| `LICENSE.nflverse.md` | 18,651 | `2a82ac9bbc3e3ee066908381e8d373896db5a6025d083fbd59692fe9ccfb9111` |
| `LICENSE.retrosheet.txt` | 971 | `2218abe680e21d3308de06352c394baefbffc7618d36a821d38ed6e97c24105d` |
| `teams.retrosheet.zip` | 4,115 | `8b71744e56df36cf3de00ceeab1808bed8ab0ec0f29a30c0f70b95d0f971b2b8` |

The `games.csv` hash above identifies the original upstream download. In default frozen mode, that download is **not a required input**. The separately bundled normalized gzip has SHA256 `734a5950bc0e1c3db5e4e95fb0d854f2f4702b6ed624601d4558efbba661616b`; its uncompressed normalized CSV hash is `b0d565c308f62f0fc7bd6239b15784c2e34204f5c1ed4a58a5b063d5a643c206`. These are different representations and are never presented as the same downloaded bytes.

The other original-year source hashes remain in `data_manifest.json` and are repeated in the local V2 manifest. Reproduction checks the exact bytes, not just a branch name or a URL.

## Verification performed

- Full project unittest discovery at the audit checkpoint: **90 tests passed** (including the then-present V2 feature tests)
- Eight additional synthetic checks passed for array/object score equivalence, incomplete scores, invalid booleans/fractions/negatives/length, and configuration restoration after errors
- Repeated offline staging produced identical normalized outputs, retained the same source snapshots, and preserved all guarded V1 bytes
- The Athletics normalization was applied and re-audited before development training; 162 participant changes, original event IDs retained
- No features, predictions, target rates, or model metrics were computed by the staging script

- Durability follow-up: four frozen-snapshot unit tests passed; fresh-root V2 staging without raw/processed NFL data reproduced all 16 exact dataset hashes; strict-original missing-file and wrong-lineage checks failed closed as expected
