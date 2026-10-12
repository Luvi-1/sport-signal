# Baseball pitch-outcome/count reconstruction

Status: stage-one descriptive measurement module. No fitted model, predictive
score, tuning run, calibration fit, physical pitch-type inference or coaching
recommendation is authorized by this module.

## Reproduce

From the repository root, using Python 3.11+ and the standard library:

```sh
python -m unittest discover -s tests -p 'test_tactical_baseball*.py' -v
python -m experiments.tactical.baseball --fetch-missing
```

Omit `--fetch-missing` for a strictly offline run. `--years 2025` performs only
2025 source/eligibility QA and creates no development target distributions.
The default processes 2023–2025. Downloads use the official URLs below, verify
hard-coded SHA-256 pins, and never overwrite an existing source version. A
changed upstream archive stops reproduction until its replacement is reviewed.

Raw inputs are read from `data/raw/tactical_research` when already cached;
otherwise missing sources go to `data/tactical/baseball/sources`. Local compressed
pitch, event and issue JSONL files go to `data/tactical/baseball`. The local
aggregate interface is `reports/tactical/baseball/summary.json`. Both areas are
excluded from the distributable repository. Incomplete outputs retain a
`.partial` suffix; the complete summary is replaced only after every requested
season passes validation. Gzip timestamps are fixed for deterministic row files.

## What an observation means

The observation is a recorded delivered pitch, with reconstructed pre-delivery
count, active players, inferred/adjusted handedness, inning, batting side, base
occupancy, outs, runs and previous delivered-pitch outcomes. This is a
retrospective annual-archive representation. It does not establish an online
data feed or when an analyst could actually receive the annotation.

The primary descriptive target is swing among eligible conventional identified
pitch outcomes. The second target is bat-ball contact among those eligible
swings. Foul tips count as bat-ball contact even though they are strikes.

| Source symbols | Delivered? | Count effect | Target handling |
|---|---|---|---|
| B, C | Yes | Ball, strike | Take, eligible swing denominator |
| S | Yes | Strike | Swing, no contact |
| F | Yes | Strike only below two | Swing, contact |
| T | Yes | Strike, including strike three | Swing, contact |
| X | Yes | PA-dependent | Swing/contact unless the current pitch is a bunt or interference |
| L, M, O | Yes | Strike, including strike three | Bunt category, excluded from conventional targets |
| P, Q, R, Y | Yes | Ball; strike; foul rule; in play | Pitchout category, excluded |
| H | Yes | No ordinary count increment | HBP category, excluded |
| I | Yes | Ball | Delivered intentional ball, excluded |
| K | Yes | Strike | Unknown strike type, target excluded; subsequent count remains usable |
| U | Recorded unknown delivery | Unknown | Target excluded; subsequent PA counts become unknown |
| A, V | No | Automatic strike/ball | Count changes, no delivered row |
| N | No | None | No delivered row |
| 1, 2, 3, +, *, ., > | No | None | Pickoff and event/modifier notation, never pitches |

Eligibility is conditional on the current realized category; it is not a
known-before-delivery all-pitch population. In-play bunts and interference are
checked using the current terminal event, in the target namespace only. Earlier
ordinary pitches in the same PA remain eligible. A future bunt never filters
an entire PA. No pitch type, plate location, velocity, release angle, stance,
joint motion, catcher target or intended action is invented.

## State machine and conservative exceptions

1. Read raw EV records in source order. Raw `start`/`sub` records determine the
   active pitcher and batter replacement; rosters supply hand metadata. Apply
   `badj`/`padj` at their recorded boundary. A switch hitter defaults to the side
   opposite the current pitcher's hand, with an explicit inference-method flag.
2. Align official parsed rows sequentially by game, event, inning, batting side,
   batter and cumulative string. A raw NP consumes a parsed row only when the
   next parsed NP's batter and exact string match. Omitted NP still advances
   the emitted prefix and count before the following substitution.
3. Remove the already observed alphabetic prefix and emit only new deliveries.
   Automatic counts are advanced but do not produce pitch rows. A disappearing
   `N` may be normalized only when all count-changing/delivered symbols remain
   a valid prefix. Other prefix changes stop the entire season.
4. Validate each parsed pre-state against the maintained raw-timestamped state.
   Only after processing the event apply its official post-state and runs.
   Raw pinch runners and `radj` update baserunners at the actual boundary.
5. Retain count across a runner event, substitution or interrupted PA; reset on
   PA completion or inning end. Some games end with a right-censored PA; its
   observed pitches remain observations. Raw `suspended,YYYYMMDD,...` boundaries
   supply resumed source-record dates and are checked against matched parsed
   dates. Such a record can materialize a previously unrecorded pre-suspension
   pitch prefix: its physical delivery dates are not established by the parsed
   record date. Conservatively exclude newly emitted deliveries in the first
   post-boundary record, retaining `event_date=null`, the original/resume date
   interval, source-record date and an explicit ambiguity status. Already emitted
   prefixes keep their earlier dates/counts; subsequent dated records continue
   from the observed prefix. No additional pitches or count resets are invented.
6. Preserve source-count disagreements, impossible counts and exceptional
   three-ball walk adjudications as explicit PA-quality exclusions. Never clip
   a four-ball pre-pitch count to three. Unknown `U` excludes only its unknown
   current label and count-uncertain suffix, not otherwise known prior pitches.

Parsed records sometimes express official statistical responsibility rather
than the active actor. Narrow exceptions are accepted only with raw proof:

- A two-strike pinch hitter's strikeout can remain credited to the replaced
  batter. The parsed string may equal a proven prior raw prefix or the current
  raw string. Require the recorded two-strike substitution; retain the actual
  batter on every delivered row
- A reliever's walk can retain the responsible former pitcher and old prefix.
  Require an exact prior batter/string/pitcher tuple. Pitcher identity and hand
  still come from the current raw lineup
- Three 2023 inherited-strikeout records add a parsed-only NP bookkeeping row.
  Consume it only immediately after the proven attribution case, with the
  actual hitter/string/inning/side/date and an exactly unchanged post-state
- Retrosheet's parsed `bip` excludes home runs and can include a batter-
  interference out. Check `hr`, `xi` and the explicit BINT modifier separately;
  never equate that one flag with physical bat contact
- Four automatic intentional balls followed by an appeal/out can have no walk
  credit. Such an administrative event has no delivered-pitch target

Any unproved attribution exception, source hash disagreement, roster conflict,
unmatched parsed row, state discrepancy, unsupported character or game coverage
change raises an error. No silently skipped game or guessed state is allowed.

## Audited source accounting

| Season | Games | Aligned parsed rows | Delivered symbols | Retained raw NP | Omitted raw NP |
|---|---:|---:|---:|---:|---:|
| 2023 | 2,430 | 191,073 | 717,944 | 654 | 26,792 |
| 2024 | 2,429 | 189,536 | 709,510 | 599 | 59,203 |
| 2025 | 2,430 | 189,939 | 710,079 | 628 | 26,906 |

Final target-specific QA denominators are 713,338 / 704,671 / 705,223 eligible
swing observations and 338,840 / 337,665 / 336,314 eligible swing-conditioned
contact observations for 2023 / 2024 / 2025 respectively. Count/adjudication QA
quarantines 23 / 13 / 15 deliveries in 3 / 2 / 2 PAs. These later-year values
describe eligibility only, not target-by-context patterns or model performance.
Separately, suspension-date ambiguity excludes 10 / 3 / 0 deliveries in the
first post-boundary records of 2 / 2 / 0 games. These preserve their source
order, counts and observed outcomes but have no asserted exact physical date.

2023 aligned rows include three verified generated parsed-only NP rows. The
2025 expansion independently reproduces the research audit: 15,251 duplicate
prefix symbols removed, 64 multi-pitcher PAs and 171 subsequent delivered pitches
after their mid-PA pitcher changes. The known SEA202503280/pn42 count anomaly is
quarantined explicitly. Missing strings are not treated as takes. The 2024
2,429-game total reflects the source season, not an invented missing game.

The machine-readable report provides complete stage denominators, mutually
exclusive current-pitch taxonomy exclusions, nonexclusive PA-quality reasons,
source/postseason exclusions and source hashes. A QA reason attached to a whole
PA is counted on every delivery excluded by that PA, so reason totals must not
be added together. Only 2023 has observed target-by-context arrays. The 2024/2025
objects expose eligibility/exclusion and measurement QA, with empty target-
distribution arrays. Source QA is not predictive performance validation.

## Features, targets and lineage stay separate

`features` is an exact allowlist, independently testable without terminal events.
It contains no full pitch string, raw event, post-state, next player, final score,
current target, future aggregate or parsed responsibility actor. `target`
contains the current symbol, conventional swing/contact label and current-pitch
exclusion annotations. `eligibility` is the explicit target-specific gate.

`lineage` records game, PA, source-record date, event-date status and interval,
exact event date when supportable, raw member/row/symbol offset, cumulative
position and the matched parsed member/row/pn. Omitted raw NP has no invented
parsed match. Separate event rows retain the full source string, raw count,
reconstructed checkpoint and terminal consistency check. Source archive hashes
allow every derivative to be traced back to its original bytes.

Tests cover grammar, two-strike fouls, bunt strike three, pitchouts, HBP,
intentional/automatic events, unknowns, interruptions, retained/omitted/generated
NP, pitcher and hitter changes, credited responsibility, hand adjustments,
pinch runners, extra innings, baserunner inning ends, suspended dates, invalid
counts and structural failures. Future-suffix and terminal-bunt mutation tests
assert byte-equivalent current feature dictionaries. This demonstrates prefix
integrity, not independent physical accuracy of Retrosheet's annotation.

## Rights and source pins

Official documentation: [event-file specification](https://www.retrosheet.org/eventfile.htm),
[parsed-play downloads](https://www.retrosheet.org/downloads/plays.html),
[reuse notice](https://www.retrosheet.org/notice.txt).

For each year 2023–2025, the exact source routes are
`https://www.retrosheet.org/events/{year}eve.zip` and
`https://www.retrosheet.org/downloads/plays/{year}plays.zip`.
All six immutable SHA-256 pins are in `SOURCE_PINS` in the parser and are copied
with URL, retrieval time and byte size into the summary. Raw and row-level data
remain local. A code license does not replace the source copyright notice.

The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

The separate `BASEBALL_PROTOCOL_DRAFT.md` is a proposed numerical contract for
review, not approval to run it. Statistical model fitting remains closed.

## Frozen reference-review packet

The prespecified 2023 reference sample is selected and rendered in separate
steps, before independent adjudication:

```sh
python -m experiments.tactical.baseball_reference_sample select
python -m experiments.tactical.baseball_reference_sample packet
```

Selection uses the protocol's SHA-256 rule. The per-PA anchor is its minimum
delivery-key hash; a PA with no delivered pitches uses index zero. Those exact
implementation definitions are recorded before inspection in the immutable
local membership file. A changed membership, source, parser, protocol or
selection implementation blocks regeneration rather than silently reselecting.

The frozen union contains 133 PAs in 126 games and 641 recorded deliveries: all
48 supported count × hand cells, ten PAs per available stratum except the six
available suspension boundaries, plus all three count/adjudication-excluded
PAs. The membership SHA-256 is
`3d5b30035926ad1c9c94e319de1dfdd9f120a270c76a65b38f5bddf4f7b421c9`.

`data/tactical/baseball/reference_sample/index.md` links human-readable raw,
official-parsed and reconstructed PA windows; adjacent JSON retains complete
row lineage and matched-field checks. The machine packet records 8,193 field
comparisons with zero failures. This is mechanical agreement, not manual or
independent adjudication. The packet has been handed to the independent
reviewer; no acceptance is claimed by its generator. The aggregate-only report
is `reports/tactical/baseball/reference_sample.json`. No source-row excerpts are
placed in reports or documentation, and the predictive gate remains closed.
