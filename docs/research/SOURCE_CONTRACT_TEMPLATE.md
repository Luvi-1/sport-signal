# Tactical source and model contract template

Status: design checklist, 2026-10-11. Fill this for each distinct source and
prediction moment after its literature/factor review. Do not silently merge
incompatible contracts because records concern the same sport.

The dataset documentation approach is motivated by
[Gebru et al., *Datasheets for Datasets*](https://arxiv.org/abs/1803.09010), which
calls for documenting collection, composition and appropriate use. The specific
fields below are this project's sports-focused design.

## Research purpose

- Sport, league, population and era
- Analyst's question and practical use
- Unit: pitch, play, point, shot, possession, player-session or match
- Descriptive, predictive or causal claim; causal identification if applicable
- Physical prediction instant and actual historical/publication latency
- Exact target, denominator, class order, horizon and censoring rule
- What is deliberately outside the target, such as foul rewards or later play
- Important factors researched but not observable in this source

## Source identity and rights

- Provider, canonical URL, pinned version/commit and retrieval UTC
- File names, byte sizes and SHA-256 hashes, including schema and terms evidence
- Actual data license/terms, separate from downloader-code licensing
- Attribution and logo obligations, permitted purposes and redistribution limits
- Permissions for raw data, row-level derivatives, aggregates, plots and weights
- Allowed access route; authentication, cost or authorization blockers
- Original bytes versus normalized/transformed bytes and their separate hashes
- Fail-closed behaviour when content changes or downloads return an HTML page

## Population and data quality

- Games, dates, competitions, players and eligible events before exclusions
- Sampling process, selection biases and unavailable groups
- Unique keys and exact, conflicting or cross-file duplicate handling
- Event order, substitutions, interrupted actions, corrections and replay rules
- Missing, unknown, censored and unobserved are distinct values
- Units, reference dimensions, coordinate origins and attack-direction transforms
- Sensor rate, clock drift, synchronization and detected/interpolated flags
- Measurement plausibility and consistency rules chosen without model outcomes
- Quarantine counts by reason and game, including overlap among reasons
- Outcome or test information already inspected during source-quality research

## Feature inventory

For every proposed field record:

| Field | Physical meaning and unit | Source/version | Measurement class | Earliest physical time | Available to whom and when | Quality/missing policy | Feature or excluded, with reason |
|---|---|---|---|---|---|---|---|
| To be specified | Do not substitute a proxy's name for the quantity | Exact field(s) | Measured/charted, estimated, derived or absent | Defined relative to action | Historical annotation may not be live | Explicit flags | Default excluded until justified |

Prior-history features also require the grouping key, window, completion cutoff,
minimum support, shrinkage and cold-start rule. A participant ID is not evidence
that measurements of their current fitness or physical state exist.

## Evaluation freeze

- Development, calibration and evaluation games/dates; no shared match windows
- Intended generalization: later games, new players, new teams or a different league
- Candidate families, hyperparameter budgets and feature-group ablations
- Same-row comparator policy and baseline definitions
- Selection metric, tie-break rule, calibration procedure and designated main model
- Label mapping, probability checks and score definitions
- Reliability bins, subgroup minimum support and uncertainty method
- Small-game-sample restrictions and remaining player/team dependence
- Frozen code, source, partitions, transformations and artifact hashes
- Independent review before test unlock and complete reporting after evaluation

## Use limits and change control

- Supported input ranges and combinations, missing-data behaviour and refusal cases
- Association versus intervention warning, including held-fixed assumptions
- Rules, provider, competition, equipment and measurement changes to monitor
- Retest trigger, versioned refresh route and rollback to a reproducible snapshot
- New data cannot silently replace the frozen training or evaluation snapshot
- Release allowlist, source-specific notices and no accidental row-level exports

Distribution changes can degrade performance despite success on a development
benchmark, as demonstrated across varied applications by
[Koh et al., *WILDS*](https://proceedings.mlr.press/v139/koh21a.html). That is a
general methodological warning, not evidence of a measured sports-specific drift
effect in this repository. Any such claim needs its own comparison.

