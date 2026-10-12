# Five-sport research synthesis and build decisions

11 October 2026 · Independent noncommercial research · AI-assisted development

This research-planning synthesis preserves the evidence and decisions that preceded
implementation. All seven prespecified numerical studies are now complete and
independently numerically verified; see [the final benchmark](../tactical/BENCHMARK_RESULTS.md)
and [model cards](../tactical/model_cards/). Links to detailed source audits may refer
to private-only evidence deliberately omitted from the source distribution for
participant privacy; the included release notes identify those omissions.

## Executive finding

A meaningful five-sport workbench is feasible. Its strongest form is a collection
of carefully defined analyses of real sporting situations, supported by separate
mechanics studies where actual physical measurements exist. A larger algorithm
cannot recover a stance angle, intended target or injury state that the source
never measured.

The first implementation stage now covers source validation, event reconstruction
and development-data descriptive views. Numerical tactical models require a
separate, exact protocol and independent check before fitting. The completed
four-sport match-outcome experiments remain preserved research results; they do
not establish tactical or biomechanical competence.

## What was researched

The linked reviews cover player skill, body mechanics/equipment, positions and
movement, team coordination, opponent response, environment, workload/recovery,
injury-information limits, game context, rules, coaching/intention and time/provider
change. They also examine neglected roles: goalkeepers; basketball rebounders and
ball handlers; baseball catchers, fielders and baserunners; NFL receivers and
special teams; tennis returners and recovery movement.

This is a targeted narrative review with primary papers, official methodology,
data documentation and hands-on source audits. It is not a systematic review or
meta-analysis. Sources differ in population, measurement quality and experimental
control. Factor counts describe the breadth of an inventory, not the number of
independent causal findings. The inventories overlap and should not be summed.

- [Soccer and basketball review](SOCCER_BASKETBALL_RESEARCH.md) and
  [94-factor inventory](SOCCER_BASKETBALL_FACTOR_INVENTORY.csv)
- [Baseball and NFL research](baseball_football/README.md),
  [70-factor core inventory](baseball_football/factor_inventory.csv), focused
  [baseball mechanics](baseball_football/baseball_biomechanics_review.md),
  [NFL mechanics](baseball_football/football_mechanics_review.md),
  [catching/fielding/baserunning](baseball_football/baseball_other_roles_review.md)
  and [receiving/special teams](baseball_football/football_other_roles_review.md)
- [Tennis mechanics review](tennis/biomechanics_factor_review.md),
  [tactical literature](tennis/tactical_literature_review.md) and
  [audited measurement contract](tennis/data_contract.md)
- [Independent methodological challenge](INDEPENDENT_METHOD_REVIEW.md)

Each underlying review provides primary links, measured definitions, study
populations, confounders and limits. A laboratory manipulation, a professional-game
association, a simulation and a provider's marketing claim receive different
weight. Private tracking studies inform design; their results are not reproducible
benchmarks for this project without the same data and evaluation contract.

## The five analyses and what they can establish

| Sport | Useful analyst question | Actual evidence | Initial valid interpretation |
|---|---|---|---|
| Soccer | How does recorded defensive context change the description of a shot? | WSL event shots and partial goalkeeper/defender snapshots | Shot-conditioned scoring associations on a fixed cohort; geometry-only versus context must use identical rows |
| Basketball | How do location and opponent proximity characterize recorded releases? | Ten ACB games with at-release event/tracking geometry | Small-sample release-context analysis and, later, a prespecified five-game forward evaluation |
| Baseball | How do count and prior pitch outcomes shape the next observed event? How do measured body mechanics relate to laboratory contact? | Retrosheet sequence/state reconstruction; separate OpenBiomechanics instrumented machine-hitting task | Two distinct analyses: game anticipation from coded events, and unseen-athlete laboratory execution associations |
| American football | Which realized tendencies accompany the final observed at-snap setup? | NFL play state, FTN formation/personnel/motion and source-normalized charting | Retrospective scouting of dropback versus rush, with sacks/scrambles included in dropbacks |
| Tennis | Which serve directions accompany prior tendencies and score? How does execution differ from stated aim? | MCP charted points; separate eight-player collegiate aiming experiment | Opponent tendency scouting and a small measured spatial-execution study with censoring |

### Soccer

Goal opening, distance, body part, restart context and goalkeeper/defender geometry
are operational factors in the selected shot study. Relevant defenders are not
necessarily all defenders; a missing position cannot become an empty space.
A shot-only model cannot identify the best pass instead, off-ball causal value or
complete goalkeeper quality.

A separate SkillCorner sample contains two professional matches with
provider-estimated 3-D joints. It can demonstrate relative segment/joint-angle
measurement. Pose and XY tracking have different frame rates, and a shot-ending
possession annotation is not a verified ball-contact timestamp. Per-joint predicted
error is not a calibrated angle interval. Contact alignment must clear a separate
gate before any impact-labelled mechanics analysis.

### Basketball

The ACB source supports actual court geometry and nearest-defender context at
recorded release. Court units and hoop location are source-specific. Same-provider
event/tracking agreement is a consistency check, not independent physical accuracy.
Some tracking is extrapolated, and sparse non-release coverage prevents claiming a
complete possession model from the excellent release-frame coverage.

The final primary denominator is 708 geometry-supported releases across five
sequential evaluation games; the 719 all-release cases, including fixed fallbacks
for absent geometry, are a prespecified sensitivity analysis. Fouled releases are
retained. Official field-goal-attempt accounting is a different denominator; successful
and-ones must not be discarded. Immediate field-goal points exclude foul rewards,
rebounds and subsequent possessions. Ten sampled ACB games do not validate NBA
transfer or individual rankings. The separate [nonprofessional free-throw audit](SPL_BOUNDED_SCHEMA_ADDENDUM.md)
found different pose completeness and sampling rates across sessions, unknown ages
and no verified release-frame label. Those gaps constrain it to measurement/schema
exploration until alignment and output-safety gates are resolved.

### Baseball

Count, base/out/score state, handedness and prior outcomes provide genuine game
context. Retrosheet pitch strings are cumulative across interrupted plate
appearances. A reliable parser must deduplicate emitted prefixes, retain raw
pitcher substitutions and handle automatic count events without inventing delivered
pitches. These codes do not measure pitch shape, location or batting stance.

The [OpenBiomechanics audit](baseball_football/OPENBIOMECHANICS_AUDIT.md) confirms
actual body angles/timing, marker bat speed, independent Blast readings and contact
measurements. Hitting used a machine around 65 mph from about 40 feet. There is one
session per athlete. The recommended adult-only primary population contains 643
swings from 93 athletes; 638 have recorded exit velocity, and 571 have paired
HitTrax context. These are different eligible populations.

Body-only versus pitch-context analysis is scientifically useful, but current
bat-velocity components nearly reconstruct marker speed. Duplicated columns,
outcome-bearing filenames and downstream launch/carry/simulated-result fields are
excluded from relevant predictors. Marker and Blast speeds retain separate names;
neither is automatically ground truth. Offline-filtered event summaries support
retrospective execution associations, not verified real-time foot-plant forecasts.
Athlete-grouped validation asks about unseen athletes, not future sessions or MLB
live pitching. No stance prescription, injury estimate or recruitment ranking is
supported. Athlete-level source records remain local; reports are aggregate.

Measured professional-pitch analysis through Statcast is scientifically valuable,
but the intended automated collection/publication route still has unresolved rights.
That gap is not a technical failure and is not hidden by renaming sequence counts.

### American football

Formation, personnel, motion, box/backfield counts, field position, down/distance,
clock and score are useful contextual factors. Provider changes require normalized
personnel counts and stable categories. Full joins can still contain sentinel
values, impossible personnel totals and disagreeing measurement sources.

The physical instant is the final setup at the snap, while charting is published
retrospectively. This supports later film study/scouting; it does not reproduce
information available before the offense selected a play. Realized dropback differs
from called intent. Coverage, pressure, rushers, routes, time-to-throw and pass-player
missingness can reveal later action and must not enter the at-snap feature set.
Pressure conditional on a dropback is a separate task. Literature on leverage,
blocking, throwing, catching and kicking does not supply those physical quantities
in the selected event table.

### Tennis

Serve number, score, handedness and prior tendencies are valid first targets.
The implemented history uses source Date plus a fixed 21-day availability assumption;
it is not verified match-completion or historical publication timing. MCP offers extensive professional match coverage but volunteer
selection and popular-player bias. Raw rows require point sorting, conflict-aware
deduplication and score-rule replay. Notes and full rally suffixes can contain
future information. Wide/body/T and coarse rally directions must remain categories;
they are neither intended aim nor meter-accurate trajectories.

The separate collegiate experiment actually records stated targets, radar speeds
and bounce coordinates. It contains eight players and 567 attempts. The proposed
non-let execution study explicitly conditions on 548 recorded non-let attempts:
437 observed bounces plus 111 net-censored attempts. The 19 lets are disclosed;
net failures receive no invented bounce. Repeated indices are not verified
first/second-serve pairs. Leave-player-out evidence cannot establish future-session
or professional-match transfer. Paper-simulated win surfaces are not observed point
outcomes.

## Cross-sport gaps that remain important

1. **Intention and coaching.** Executed location does not reveal a called target or
   chosen strategy. Coaching effects require recorded interventions and a design
   addressing selection and adaptation.
2. **True readiness.** Exposure, rest and within-session order can be measured in
   some sources. They do not diagnose fatigue, injury or readiness. This project
   has no individualized medical or health-risk task.
3. **Complete physical state.** Partial snapshots, broadcast-estimated pose,
   laboratory instruments and categorical annotations are different evidence.
   Force, gaze, spin and contact timing cannot be filled by plausible guesses.
4. **Opponent and opportunity selection.** A recorded shot, contacted ball or
   dropback cohort answers a conditional question. Better prediction inside that
   cohort does not establish the best unchosen action.
5. **Environment and eras.** Venue, rules, equipment and provider definitions may
   change. Exact source-era definitions precede pooling or transfer claims.
6. **Population transport.** More repeated rows do not create more independent
   athletes or games. Student/laboratory, ACB, WSL and professional-tour populations
   require named limits and group-aware evaluation.

## Build priorities and scientific gates

The approved first stage is an executable local workbench with audited sources,
correct event-state reconstruction, measurement definitions, aggregate support and
development-period descriptive views. Sources with restrictive terms remain local;
release decisions are source-specific. Opening a view performs no hidden download,
training, holdout unlock or network publication.

Before each numerical experiment, freeze the exact population/denominator, target,
physical and information cutoff, feature allowlist, exclusions/censoring, history,
chronological or participant-group splits, candidate grid, selection tie-break,
calibration method and update budget. Then review the contract independently.
Model choice uses development only. Test results, including failures, remain fixed.
Later-year source QA already occurred, so the valid description is performance-blind
after QA, not an entirely human-blind or historically live evaluation.

Large event sources can support calibrated probability comparisons if the chosen
cohorts provide adequate independent support. ACB's five forward games and BYU's
eight players instead require restrained fixed models and reliability diagnostics
without claims of general calibration. BYU participant/fold diagnostics remain
private and local; the public release contains only cleared pooled aggregates. Mechanics regression
requires unit-aware error, simple baselines, grouped uncertainty and measurement-
coupling checks. No blended five-sport accuracy or universal superiority ranking
will summarize these different questions.

The workbench's value is therefore inspectable reasoning: what was observed, which
patterns the data support, what was missing, and how an analyst can test the next
question. It is an educational research instrument, with claims proportional to
its evidence.
