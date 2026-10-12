# Tennis research-first tactical upgrade

Research completed: 11 October 2026. This package supports the sports-analytics portfolio with a tennis-specific evidence base, audited public-data options and a bounded predictive design. It does not claim an exhaustive search of all published work or a trained model.

## Main finding

The strongest feasible combination is a **professional categorical shot-pattern study** using a pinned Match Charting Project snapshot, plus a **separate small measured serve-execution study** using the BYU experiment. Keep the measurement levels explicit: MCP zones are coded directions, while BYU bounce coordinates are measured meters. Neither supplies professional full-body biomechanics.

## Read in this order

1. [Tactical literature and context factors](tactical_literature_review.md): documented search, 21 selected tactical/statistical/context studies, official rules and original data-owner definitions; 32 operational factors
2. [Mechanics and perception evidence](biomechanics_factor_review.md): 30 selected sources, including reviews, primary studies and one laboratory dataset publication; 52 operational factors
3. [Data contracts and actual inspection](data_contract.md): licenses, immutable pins, schema/units/timing, full MCP row audit, actual alternative samples and blockers
4. [Bounded model and evaluation design](tactical_model_design.md): exact prediction moments, baseline ladder, chronological/two-player grouping, calibration, leakage tests and readiness gates
5. [Source manifest](source_manifest.json), [mechanics bibliography](biomechanics_sources.json), [tactical bibliography](tactical_sources.json): machine-readable provenance/bibliographic facts, with no raw point or participant rows

The literature lists overlap on the return-impact paper. Source counts must not be added as independent evidence, and related biomechanical papers can reuse participants. The 52 + 32 factor rows include related concepts, not 84 independent or automatically model-ready predictors.

## Verified scale and limits

- MCP: 1,877,757 raw point rows, 11,785 point-bearing matches, men's and women's files; pinned 18 September 2026 snapshot. Includes 2,625 extra duplicate rows and 496 conflicting point keys requiring resolution/quarantine. CC BY-NC-SA 4.0
- BYU: 567 experimental serve attempts, eight NCAA men, 32 stated targets. MIT-labelled author repository. After removing 19 lets: 437 observed bounce pairs and 111 net-censored attempts; no completed-point outcomes
- Slam speed/placement fork: a real 2023 Wimbledon sample exists, but more than half its valid point rows have zero speed and exact match dates are unavailable in the inspected metadata. Secondary only
- Public Hawk-Eye scrape: useful schema evidence, no identified data reuse license. SportsPose requires academic outreach; TRACE annotations are not yet released. Neither is silently substituted into the project

## Intended first result

First/second-serve direction tendencies with development-only calibration and,
only after parser validation, retrospective annotated-prefix response distributions.
Report support and uncertainty and compare against strong shrunk-frequency/Markov
baselines. Designate the main model using development data, retain all locked-test
comparisons and report negative findings without selecting a new champion from the
test. The small BYU companion has no separate recalibration claim and initially
studies execution conditional on a recorded non-let attempt, with excluded lets
disclosed. Never label categorical plots as measured angles or observational
associations as causal coaching advice.

## Work status

Research documents and aggregate provenance are complete. Raw downloads, diagnostic scripts and paper caches remain in ignored research storage. No core application code, production parser, model weights, final benchmark or deployment was created by this research pass. The next step is the explicit data-quality/rights gate in the design, followed by implementation only once the cross-sport research review is accepted.
