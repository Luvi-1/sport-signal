# Tennis A1/A2 parser and descriptive stage

Status: source/parser/measurement validation, 11 October 2026. This is a local, descriptive research implementation. No numerical models have been fitted, recalibrated, compared or scored. Approval of an exact fit/evaluation protocol and independent review remain prerequisites for fitting.

## Run and outputs

From the repository root:

```sh
python -m experiments.tactical.tennis --root .
python -m unittest discover -s tests -p 'test_tactical_tennis*.py' -v
```

The parser uses only Python's standard library, including SQLite for disk-backed grouping and numeric point sorting. It does not import the application's ML stack. The input cache must already contain the exact pinned files; the CLI does not download data, run workbook macros or execute downloaded binaries.

- `reports/tactical/tennis/summary.json`: compact workbench-facing source pins, scope, counts, denominators, exclusions, coverage, player-support aggregates and development-only coded-direction counts
- `reports/tactical/tennis/quality_report.json`: the same information with nonexclusive exclusion reasons in every target/corpus/surface/year cell
- `data/tactical/tennis/source_index.sqlite3`: local source index, including raw point cells and original source-file/record provenance
- `data/tactical/tennis/duplicate_provenance.jsonl`: every discarded duplicate's original file, CSV record number, row digest and exact/conflicting classification
- `data/tactical/tennis/match_quality.jsonl`: private match-level validation/quarantine details

An optional `--write-development-rows` flag writes `data/tactical/tennis/development_prediction_rows.jsonl.gz`. Those rows carry separate `features`, `target`, `quality`, `exclusions`, cutoff, source provenance and partial serve/let events. Only dates in 2010–2022 are emitted. Gzip has a fixed timestamp and no embedded filename. Features never contain the full point strings, Notes, current point winner or current target outcome. Raw data and row-level derivatives are ignored locally; both report files are local research outputs, not authorized for public deployment.

Reports and row streams are deterministic for the same code and pinned inputs. Summary publication uses a temporary file and atomic replacement. The intermediate SQLite file is a scratch index and may be partially rebuilt if processing is interrupted; rerunning rebuilds it from the verified source. SQLite physical file bytes are not a reproducibility claim.

## Source and rights contract

- Source: [Jeff Sackmann's Match Charting Project](https://github.com/JeffSackmann/tennis_MatchChartingProject)
- Immutable commit: `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf`, committed 18 September 2026, 08:35:54 UTC
- Exact files: the six men's/women's `points-to-2009`, `points-2010s` and `points-2020s` CSVs; both match CSVs; README; `data_dictionary.txt`; and `MatchChart 0.3.2.xlsm`
- The checked-in [source manifest](../research/tennis/source_manifest.json) supplies every expected SHA-256 and byte count. The parser checks all 11 files, their immutable official URLs, the exact file set, commit, license and both CSV schemas before reporting results. The output also records the manifest and parser-code hashes
- Terms: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), verified in the [pinned README](https://github.com/JeffSackmann/tennis_MatchChartingProject/blob/1813a1309b7ed7ebf1c7e884b32bf675d00e4edf/README.md). Credit Jeff Sackmann / Tennis Abstract and Match Charting Project contributors; identify the parser transformation. The repository software license does not replace these data terms
- This implementation is bounded to local noncommercial research and descriptive QA. It makes no claim that recruiting, hosted/public or commercial use has been cleared. Distribution of raw/derived data or fitted artifacts needs its own terms review

The pinned workbook's instruction sheet supplies the code and score-rule meanings. It was inspected as document/XML content only. The old data dictionary lists additional computed columns absent from the actual 14-column point CSV and is not used as the actual schema. The [research contract](../research/tennis/data_contract.md) documents that distinction.

## Exact population and timing

The source comprises 1,877,757 raw point rows across 11,785 point-bearing matches in men's and women's source files. These are source-corpus labels; they do not represent an inferred physiological category. Dates span historical and modern voluntary charting samples, not a census of professional tennis. Popularity, broadcast availability, round, era and surface selection are uneven.

Only 2010–2022 produces target-by-context distributions. Other years receive pin/schema/parser/quality checks and eligibility/player-support counts. In particular, no 2025 target-by-context scouting profile or predictive performance is produced before approval and freezing of the proposed evaluation protocol. No training, calibration or test split is claimed to have been frozen by this parser.

Date is an event date, not the chart's publication or ingestion date. No live-feed timing or historical as-of-availability claim is made. A1 means before first-serve motion; A2 means after a completed first fault and before second-serve motion. These timing contracts are implemented as a feature allowlist, not a claim that MCP was a contemporaneous live feed.

## Source-key and score validation

1. Validate numeric positive point ordinals and exact CSV headers/row widths
2. Resolve exact duplicate rows with provenance. Group by `(corpus, match_id, numeric Pt)`, never raw file order or lexicographic point order
3. Quarantine the entire match if any point-key variants conflict, including conflicts in Notes or serve strings. A deterministic first representative is kept only for diagnostics; none of its match enters eligible distributions
4. Validate metadata date/ID agreement, player names, surface, best-of, hands, row width and supported rule flags. Metadata conflicts and malformed records are not repaired or realigned
5. Require point ordinals to be consecutive from one. Reconstruct state starting with player 1 as first server, from previous point winners only
6. Check every available pre-point `Set1`, `Set2`, `Gm1`, `Gm2`, `Pts`, `Gm#`, `Svr`, `TbSet` and `Pt` against replay. A discrepancy quarantines the match, rather than resetting to the inconsistent row
7. Check winner consistency for directly parsed aces, unreturnables, double faults, unobserved awards and penalty awards. Full-rally terminal/striker parity is explicitly not implemented

`Pts` is server-relative; sets/games are player-relative. `TbSet` is a set-rule flag, never the current-tie-break indicator. Current tie-break state is reconstructed from the validated score and rule. Service-side alternation includes points awarded by penalties. A completed tie-break preserves its original first server to establish who serves the next set.

Supported workbook rule flags:

- `1`: 7-point tie-break at 6-all
- `0`: advantage final set, with ordinary tie-breaks in earlier sets
- `A`: 10-point tie-break at 6-all in the final set
- `T`: 7-point tie-break at 12-all in the final set
- `W`: 7-point tie-break at 8-all
- `V`: all advantage sets

`N` (Next Gen/no-ad), `S` (replacement final match tie-break), blank and other rule codes are quarantined. No-ad deciding-point side cannot be recovered from ordinary parity; free-text Notes are not used to infer it. Historical rule variants that fail replay are quarantined even when a broad metadata flag looks standard. A last point need not finish a match, since partial charts/retirements exist; such validated prefixes are counted separately from completed matches. No match outcome is invented.

Whole-match QA uses retrospective information to define an eligible research cohort. Its pass/fail result is not a pre-point predictor or a claim about prospective real-time acceptance. On quarantined matches, court side and validated features are unavailable.

## Narrow serve-prefix grammar

The parser preserves the raw cell in local source storage and preserves the parsed prefix and original character offsets in derived records.

- `c*` records zero or more lets, each a separate partial-stream event. A let direction is unrecorded, not body/unknown code 0
- `4`, `5`, `6` mean observed wide, body and T. `0` is explicit unknown direction
- `+` and `;` preserve documented serve-and-volley/net-cord modifiers; repeated modifiers and trimmed whitespace are quality flags and fail strict target eligibility
- `n/w/d/x/g/e/!` mean net/wide/deep/wide-and-deep/foot fault/unknown/shank faults. Bare fault codes are retained as an observed omission extension: fault type known, direction omitted. They cannot supply A1's direction label; they can establish a known first fault for A2
- `*` and `#` are direct ace/unreturnable endings
- A documented shot-family start or `C` starts a deliberately unparsed suffix. Its tokens are not ingested as features and no rally length, return category, full-rally parity or geometry is asserted
- `S/R` are unobserved server/receiver awards; `P/Q` are penalties against server/receiver; `V` is loss of first serve for a time violation. These are non-contact events, not zero-length rallies
- Unsupported starts, malformed terminal/fault tails and unknown modifiers remain unsupported; they are not silently coerced into a familiar serve class

The source's coded directions are categorical. They do not establish intent, bounce coordinates, physical angles, ball speed, spin, stance, player positions or biomechanics. No fake coordinates or measured-looking angles are generated.

### Let policy

The direction recorded after leading `c` codes belongs to a selected replayed delivery, while the directions of the preceding physical let attempts are absent. This stage excludes let-prefixed target deliveries from strict A1/A2. It does not pretend the selected delivery is the first physical attempt. The lets, selected delivery and explicit exclusion survive in local QA rows. A1 and A2 eligibility remain target-specific: first-service lets need not exclude an otherwise valid second-service target after a known fault; second-service lets do not change an already observed first-service direction.

### A1/A2 eligibility and denominators

A1 begins with one potential first-service target per distinct point. Known direction on a fault remains a valid direction target. Unobserved/penalty/time-violation points, missing or unsupported prefixes, unknown direction, selected-delivery lets and match-level QA failures are reported as exclusions.

A2 begins with a parsed completed first fault. A loss of first serve for time violation is not relabeled a fault. An in-play first-service rally cannot be mistaken for first-fault information even if its suffix ends in an error. Unexpected second-field content or a missing second field after a first fault is reported. Unknown or omitted first-fault direction is retained as unknown/omitted, not filled; it does not exclude an otherwise observed second-service direction.

The report distinguishes all candidate point rows, parsed target opportunities before match QA, entry opportunities after match QA, eligible rows, exclusions after entry and structural A2 nonentry. Candidate entry counts for quarantined conflicting matches describe the deterministic diagnostic representative, not an adjudicated physical fact; they never contribute eligible targets. Nonexclusive reasons may overlap and must not be summed. A separate primary-exclusion table partitions excluded candidate rows exactly (match quarantine first, structural A2 nonentry second, otherwise the first alphabetically ordered target reason).

## Strict feature contract

A1 inputs contain only validated metadata and replayed pre-point state: source corpus, event date, surface, server/returner and handedness, serve period/side, server-relative sets/games/point score, point/game ordinal, current tie-break and set tie-break rule.

A2 adds only completed first-fault direction, direction-observation status and fault type. It cannot inspect the second-service string to build its features. No historical player aggregates or fitted encodings are computed at this stage.

`quality`, `target`, `serve_events`, Notes-presence and exclusion decisions are retrospective audit/label fields, not part of the feature mapping. Notes may refer to later between-point events and must never become health, strategy or outcome predictors. Presence of a note is flagged, but its prose is not interpreted; unmarked guessed/reconstructed charting cannot be detected. Eligible rows with notes are counted explicitly.

Tests mutate current/future serve strings, suffixes, Notes and winner while requiring earlier feature mappings to stay identical. They verify that altering first-fault information can affect A2 but not A1, and that a current point winner changes only subsequent replayed state. Full nested records are not suitable model matrices; future work must consume the explicit feature mapping only after its own approved protocol.

## QA coverage and remaining gates

The implementation tests include exact hash/schema rejection, malformed metadata, numeric sorting, exact/conflicting duplicates, ordinary deuce/advantage, service alternation, 7- and 10-point tie-breaks, historical rule thresholds, unsupported no-ad/match tie-breaks, penalties, first faults with second aces/rallies/double faults, repeated lets, left-handed returners, unknown/unobserved/omitted directions, prefix mutation and deterministic development-only output.

The workbench summary contains:

- Target-specific counts and overlapping plus primary exclusions
- Corpus/surface/year coverage without held-out target distributions
- Eligible server support summarized by number of players, threshold counts, match appearances and concentration; these are retrospective coverage counts, never lagged predictive features
- Development-only direction counts by task/corpus/surface/service side, with explicit eligible denominators
- Source-quality flags, notes counts and score-check totals
- Exact source terms/pins and absent measurements

The BYU measured-serve companion is not implemented here. Neither a full-rally parser nor independently adjudicated manual stratified samples are claimed complete. These, the exact model/evaluation protocol, independent gate review and any distribution approval remain open. Successful source QA is not permission to fit, score, choose a model or claim calibrated predictions or causal coaching advice.


## Independent date review amendment

The source match `20210701-M-Wimbledon-QF-Hubert_Hurkacz-Roger_Federer`
is now quarantined for a verified date contradiction. The official
[completed Wimbledon Day9 schedule](https://www.wimbledon.com/en_GB/scores/2021/schedule/pdf/schedulePDF17.pdf)
places that quarterfinal on 7 July 2021; the source says 1 July. No corrected date is
silently substituted. The refreshed report has 11,654 accepted and 131 quarantined
matches; development support is 809,576 A1 and 307,497 A2 observations before any
numerical-stage embargo exclusions.

The proposed history helper applies source Date + 21 days as a conservative embargo,
not a verified completion/publication timestamp. Histories require that assumed
availability date strictly precede the analysis date. The numerical draft applies
the same rule to year-end fitting/selection/calibration labels. Regression tests
cover a known multi-day match, the embargo boundary and year-end admission. No
numerical history features or model have yet been fitted from those functions.
