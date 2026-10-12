# Working integration plan: five-sport contextual analytics

Status: **research and source validation**, not a completed tactical benchmark.
The delivered four-sport pre-match research release remains preserved. This new
work addresses a different question: how measured event context relates to shot,
pitch, play or point outcomes. A broader factor inventory does not imply that
all factors are observable or that their causal effects can be identified.

The common methodological gate and primary-method references are in
[Measurement and evaluation](MEASUREMENT_AND_EVALUATION.md). The sport-specific
evidence and source briefs are still being assembled; this plan is not permission
to skip them and fit another generic model.

## Preservation and architecture

- Keep `sportslab/**`, `experiments/v2/**`, their frozen protocols, selected models,
  predictions and existing reports unchanged
- Place new work in separate sport-specific tactical modules, using one repository
- Keep historical NBA game-result ingestion separate from granular basketball
  event/tracking analysis; the former cannot generate the latter
- Publish code, permitted aggregate evidence and measurement contracts. Restricted
  raw data, row-level derivatives and local trained artifacts stay excluded
- Update the existing delivered archive only after source, model and release review

## Research contract required before implementation

Each sport's primary-source research must provide:

1. Exact source URL/version/hash, rights and attribution, redistribution restrictions,
   access route, real sample/game coverage and known selection biases
2. Field definitions and units, coordinate origins/directions, time conventions,
   identity keys, duplicate/quarantine rules and changes between source versions
3. A factor inventory separated into **directly measured**, **provider-estimated**,
   **defensibly derived**, and **unavailable** quantities
4. The proposed prediction moment and target. A realized action at release/contact
   must not be described as information known before the action was chosen
5. An explicit feature allowlist with availability justification for every field;
   outcome, post-event and opaque provider-quality fields are excluded unless
   independently justified as a separately reported archived comparator
6. Literature and existing-model evidence for relevant mechanisms, with uncertainty,
   competing explanations and a distinction between association and causal effect
7. A bounded practical analysis plus a feasible validation protocol chosen from
   structural coverage, before inspecting model performance

## Examples of distinctions the design must preserve

- Basketball court-location bearing is not ball launch angle; nearest-defender
  distance is not defender orientation; a small ACB sample is not NBA-wide evidence
- Soccer event/360 positions are snapshots, not complete player trajectories or
  measured body pose. Visibility limits must not be interpreted as empty space
- A Statcast pitch-location or contact-quality variable is realized event context,
  not necessarily pre-pitch information. Definitions can change across seasons
- NFL pressure, coverage outcomes, completion location and yards after catch are
  not automatically pre-snap variables merely because they appear in one row
- Tennis charted shot-direction categories are not observed coordinates, bounce
  locations or physical angles. Coarse human annotations need their own quality
  and sampling limitations

The sport-specific source briefs determine which of these examples are actually
available. No tracking or stance variable will be invented from match scores.

## Evaluation requirements

- Split by whole game/match and chronology where the source supports it; no random
  mixing of events from the same match across development and final evaluation
- For very small game samples, use a clearly labeled exploratory analysis and
  prespecified grouped validation rather than claiming an untouched large test
- Fit transformations, candidate choices, ensembles and calibration only in the
  designated development partitions; freeze them before final evaluation
- Compare an interpretable sport-specific baseline with resource-conscious stronger
  models on identical rows and information, retaining failed comparisons
- Report probability log loss, Brier, reliability/bin counts and accuracy where
  applicable; use game-cluster uncertainty only when enough groups support it
- Keep a measurement/provenance audit and adversarial leakage tests, including
  current/future outcome mutation and mislabeled event-stage checks
- Evaluate published vendor predictions only when target, cohort, timing and source
  rights are established. Otherwise mark the comparison unavailable or diagnostic

## Interpretation and interface

The interface should show the observed context, estimated conditional outcome,
reliability, sample support and missing information. Any sensitivity view must stay
within the observed data support and label held-fixed assumptions. Changing a
correlated input in a statistical model does not establish that changing an
athlete's action will cause the predicted improvement.

A shot-only model also needs to state what it omits, such as fouls, rebounds,
turnovers, downstream possession value and selection into recorded shot attempts.
No universal coaching prescription, live-service guarantee or numerical claim of
commercial superiority follows from an attractive plot or one favorable score.

## Research-to-build gate

Implementation begins only after the sport-specific source/factor brief and
measurement contract are reviewed. Date splits, target definitions and candidate
sets are then recorded before scoring. Insufficient or restricted data can justify
a bounded descriptive tool, an exploratory model or an explicit unavailable
factor; it never justifies fabricated observations or an unsupported substitute.
