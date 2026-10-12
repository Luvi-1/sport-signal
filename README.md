# Sport Signal

**Reproducible sports ML, from pre-event forecasts to tactical evidence.**

Sport Signal asks how much historical results and measured context actually improve a prediction. It combines availability-aware data pipelines, chronological evaluation, calibrated baselines, and a local workbench that makes uncertainty and negative results visible.

[Quick start](#quick-start) · [Results](#results) · [Architecture](#architecture) · [Research guide](START_HERE_FIVE_SPORTS.md) · [Reproduction](docs/v2/REPRODUCE.md) · [Data rights](#data-rights-and-attribution)

An AI-assisted, noncommercial research portfolio. The published evidence is retrospective; the repository does not provide a live forecasting service, betting integration, or guaranteed outcomes.

## Two research tracks

| Track | Scope | Start here |
| --- | --- | --- |
| **Match-outcome forecasting** | Four separately fitted sport ensembles: soccer, baseball, American football, and tennis. V2 covers 77,235 historical events, 50 pre-event features, and 5,809 newer held-out matches | [V2 results](reports/v2/RESULTS.md) · [Fixed protocol](docs/v2/PROTOCOL.md) |
| **Tactical and execution studies** | Seven distinct studies across five sports, including basketball, plus separate baseball and tennis laboratory companions. Reviewed aggregate results are available in a read-only local workbench | [Five-sport guide](START_HERE_FIVE_SPORTS.md) · [Study results](docs/tactical/BENCHMARK_RESULTS.md) |

The tracks have different targets, populations, and evidence requirements. Their scores cannot be combined into a single “five-sport accuracy.”

The package and CLI retain `sportslab`; earlier documents use the SportsLab name.

## Quick start

Python **3.12 is recommended** for the commands below. The core package also declares Python 3.11 support; tactical tennis fitting requires its [reviewed Python 3.12/dependency pins](experiments/tactical/tennis_model.py) and newly reviewed run bindings. Core models need a CPU and internet access, with no API key, paid account, GPU, or LLM.

```bash
git clone https://github.com/Luvi-1/sport-signal.git
cd sport-signal
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m sportslab --help
```

Dependencies are pinned in [pyproject.toml](pyproject.toml). Four tests require intentionally excluded source caches; see the [public test record](PUBLIC_TEST_RUNTIME_AMENDMENT.json).

### Explore the local workbench

```bash
python -m experiments.tactical.workbench index
python -m experiments.tactical.workbench serve --port 8765
```

Open **http://127.0.0.1:8765**. Stop with Ctrl-C.

The included seven audited aggregate snapshots let you inspect matched-case comparisons, reliability bins, support, and study limitations without raw data or trained weights. The workbench uses local assets and has no data acquisition, fitting, telemetry, or background refresh. Missing source summaries are shown as unavailable.

The **aggregate evidence viewer** serves no new tactical predictions. Keep it on loopback; do not expose it through a public tunnel or reverse proxy. [Workbench guide](docs/tactical/WORKBENCH.md) · [Snapshot and integrity contract](docs/tactical/MODEL_VIEWS.md)

### Reproduce the match-outcome benchmark

```bash
bash scripts/reproduce_v2.sh              # V1, then V2 development and evaluation
# For the original smaller experiment only:
# bash scripts/reproduce.sh
```

The script preserves previous V2 outputs, verifies frozen source hashes, and regenerates the published comparisons. The bundled, attributed NFL snapshot supports durable reproduction; other provider revisions deliberately stop at a hash mismatch. Review changed inputs rather than replacing a lock to make a run pass.

This reruns an already published experiment. Further improvement claims need a fresh period. [Stage-by-stage reproduction](docs/v2/REPRODUCE.md) · [Frozen NFL versus refresh](snapshots/README.md)

For a hypothetical matchup after reproduction, use the guarded [analysis entrypoint](scripts/analyze_matchup.py) and the [documented examples](docs/v2/REPRODUCE.md#analyze-a-hypothetical-matchup). It checks benchmark completion and artifact/input hashes, warns about stale history, and preserves participant ordering. Model disagreement is not a confidence interval. Only load locally produced, trusted `joblib` artifacts: pickle-based formats can execute code.

## Results

### Match-outcome forecasting: V2 versus a refitted V1

All four V2 ensembles were frozen before scoring the 2025 periods, including EPL 2025–26. The V1 recipe was refitted on the same training/calibration periods and evaluated on the same matches.

| Sport | Held-out matches | V2 log loss | Refitted V1 log loss | Paired difference, approximate 95% interval |
| --- | ---: | ---: | ---: | --- |
| Soccer | 380 | 1.0265 | 1.0312 | [-0.0145, +0.0037] |
| Baseball | 2,430 | 0.6803 | 0.6794 | [-0.0022, +0.0042] |
| American football | 271 | 0.6310 | 0.6417 | [-0.0231, +0.0033] |
| Tennis | 2,728 | 0.6119 | 0.6160 | [-0.0071, -0.0012] |

Lower log loss is better; negative differences favor V2. Tennis shows the clearest same-game improvement. Soccer and NFL have favorable point estimates with intervals crossing zero; baseball is slightly worse. These unadjusted calendar-week bootstrap intervals are descriptive and omit some source, dependence, and selection uncertainty.

![V2 minus refitted V1 log-loss differences with approximate uncertainty intervals](reports/v2/improvement_intervals.svg)

[Complete V2 results, accuracy, family comparisons, and reliability plots](reports/v2/RESULTS.md) · [V2 model cards](docs/v2/model_cards) · [Preserved V1 results](reports/RESULTS.md)

The ensemble remains the designated model even when another family scores better. V1’s already-inspected holdout is not fresh V2 evidence. Calibration regressions and negative results remain in the reports.

### Tactical and physical-execution research

The [seven-study report](docs/tactical/BENCHMARK_RESULTS.md) preserves fixed comparisons, denominators, uncertainty, and unavailable procedures:

- Soccer: shot geometry and selectively recorded defensive positions
- Basketball: shot-release geometry, clock, and nearest-defender context
- Baseball: swing/contact tendencies from count and observed pitch-outcome sequences
- American football: realized dropback from retrospectively charted at-snap context
- Professional tennis: charted first- and second-serve direction
- Separate laboratory companions: adult baseball exit velocity and collegiate tennis target/bounce execution

Read the [study-specific model cards](docs/tactical/model_cards) before interpreting a score. The report retains useful gains, small or inconclusive changes, a worse baseball-mechanics estimate, and interrupted/nonconvergent procedures. It makes no causal coaching, injury, readiness, or individual-selection claim. Tactical source-derived findings retain the [source-specific terms and credits](docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md).

### LLM and external comparisons

The separate [Laya zero-shot experiment](docs/laya_experiment.md) evaluated 800 frozen V1 cases and had worse log loss than simpler baselines in all four sports. Laya is optional and is not part of the core pipeline.

A partial FiveThirtyEight MLB archive favored its pitcher-adjusted probabilities by a small, uncertain margin. Its limited coverage and weaker archival provenance are documented in [external comparisons](docs/COMPARATORS.md). Complete, verified same-case commercial archives were unavailable; no commercial-superiority claim is made.

## Architecture

```text
Match-outcome research
  Pinned sources → validated events → availability-aware features
    → chronological development → calibration + global freeze
    → held-out evaluation → reports / guarded matchup analysis

Tactical studies, with separate protocols and populations
  Pinned sources → source-specific parsers → fixed evaluations
    → independent numerical and display review → aggregate snapshots
    → read-only local workbench
```

| Layer | Implementation and evidence |
| --- | --- |
| Data contracts | [Provider adapters](sportslab/adapters), [event validation](sportslab/data.py), [source locks](data_manifest.json), [V2 source audit](docs/v2_data_audit.md) |
| Features and models | [Original feature engine](sportslab/features.py), [V2 features](experiments/v2/features.py), [model families and ensemble](experiments/v2/models.py) |
| Evaluation | [V2 run stages](experiments/v2/run.py), [fixed protocol](docs/v2/PROTOCOL.md), [reproduction checker](scripts/check_reproduction.py) |
| Tactical research | [Parsers, models, and gates](experiments/tactical), [execution stages](docs/tactical/EXECUTION_STAGES.md), [research synthesis](docs/research/FIVE_SPORT_RESEARCH_SYNTHESIS.md) |
| Presentation | [Aggregate-view verifier](experiments/tactical/model_views.py), [loopback server](experiments/tactical/workbench.py), [local web assets](experiments/tactical/web) |
| Tests | [Offline test suite](tests), [CI workflow](.github/workflows/tests.yml), [historical validation](reports/VALIDATION.md) |

### Information timing and evaluation discipline

- Match-outcome features use results only when `available_date` is strictly earlier than the predicted event; same-day games share a frozen state
- Suspended baseball games wait for completion. Tennis tournament-start proxies use a conservative 21-day result delay; current-match statistics stay out of the feature matrix
- Candidate selection uses earlier chronological folds. Calibration has its own later partition, followed by a global model/selection freeze before final scoring
- Test-time history may roll forward as earlier held-out results become available; the classifier stays frozen. This evaluates sequential pre-event prediction, not a season forecast made at opening day
- Tests mutate outcomes, append future games, shuffle rows, check embargoes, and exercise artifact serialization. Tactical studies apply their own reviewed timing, cohort, grouping, and fit-budget rules

[Full methodology](docs/methodology.md) · [V2 protocol](docs/v2/PROTOCOL.md) · [Tactical measurement and evaluation](docs/research/MEASUREMENT_AND_EVALUATION.md)

## Verification and limits

**Historical benchmark evidence.** The [2026-10-11 validation record](reports/VALIDATION.md) documents an independent V1/V2 refit and comparison of 90 model variants. V2's maximum probability difference was 2.96e-7, within the predefined 1e-6 tolerance. This historical reproduction is separate from the tactical studies and later source amendments.

**Public-source checks.** The [2026-10-12 test-runtime amendment](PUBLIC_TEST_RUNTIME_AMENDMENT.json) records 594 tests run on Python 3.12, with four intentional skips and no failures or errors. This public-package count is separate from the historical full-research suite. [Native Python 3.11 CI](https://github.com/Luvi-1/sport-signal/actions/runs/38213835518) also passed on revision `edf5bb2`. Later commits have their own [CI results](https://github.com/Luvi-1/sport-signal/actions); these checks do not relax the tactical tennis research runtime guard.

**Tactical replication.** The later [2026-10-11 addendum](docs/tactical/REPLICATION_RESULTS.md) records same-environment source-to-selected-procedure refits for all seven studies: 272 successful operations and zero differences in the compared predictions, scores, and interval endpoints. Independent review was AI-assisted. This was not a full search/failure replay, cross-hardware test, or new holdout. Earlier tactical documents retain their pre-addendum status.

**Public viewer scope.** The [snapshot attestation](docs/tactical/INDEPENDENT_AGGREGATE_SNAPSHOT_REVIEW.json) covers reviewed aggregate views. Raw inputs, row-level predictions, tactical weights, and private run artifacts are excluded; a fresh tactical refit requires separately rights-cleared sources, the reviewed runtime, and new run bindings. The addendum does not make this source/aggregate distribution a turnkey fitted predictor.

**Remaining validation.** Functional and DOM tests were run, but the recorded environment blocked browser-rendered visual QA. Layout, accessibility, and browser compatibility still need local inspection. [Known workbench limits](docs/tactical/WORKBENCH.md#checks-and-known-environment-limitation)

**Use boundaries.** Source QA sometimes exposed later annotations or marginal outcomes; these are retrospective, performance-blind-after-QA studies rather than prospective trials. Missing live feeds, unverified publication latency, omitted injuries/lineups, selective charting, small cohorts, and measurement bias limit transfer. [Deployment gaps](docs/deployment.md) · [Research priorities](docs/research/FIVE_SPORT_GAPS_AND_PRIORITIES.md)

### Release provenance

The original 258-file source release and its manifests remain historical evidence. The current GitHub tree includes [parser compatibility](PUBLIC_COMPATIBILITY_AMENDMENT.json), [test-fixture](PUBLIC_TEST_RUNTIME_AMENDMENT.json), and [presentation/addendum](PUBLIC_PRESENTATION_AMENDMENT.json) amendments; it is no longer byte-identical to that release.

The [original README](https://github.com/Luvi-1/sport-signal/blob/d6ff9db48f5dfdc482f77f9a2d0d768408a06b86/README.md) remains in Git history. Existing reports, protocols, aggregate reviews, and audit identities are unchanged by this presentation revision. The [public-source release notes](docs/tactical/PUBLIC_SOURCE_RELEASE_NOTES.md) explain earlier privacy-safe source copies and why historical execution hashes must not be rebound to edited source.

## AI-assisted authorship

The initial implementation, source investigation, tests, and documentation were produced with substantial AI assistance. This is a learning and research portfolio; personal contribution claims should reflect components actually reproduced, understood, or changed.

The [learning walkthrough](docs/walkthrough.md), [tactical learning guide](docs/tactical/LEARNING_GUIDE.md), and [application/learning record](docs/APPLICATION_NOTE.md) provide concrete exercises for demonstrating that understanding. Generated implementation is not evidence of independent manual authorship or production-operating experience.

## Data rights and attribution

Original software is [MIT-licensed](LICENSE). Third-party data and covered derived material retain separate conditions:

- **Original benchmark:** OpenFootball (CC0), Retrosheet (required attribution), Lee Sharpe/nflverse (CC BY 4.0), and Jeff Sackmann/Tennis Abstract via a preserved archive (CC BY-NC-SA 4.0). Tennis-derived reports and covered adaptations are noncommercial
- **Tactical material:** StatsBomb custom noncommercial terms and logo/credit requirements; FTN/nflverse share-alike conditions; Match Charting Project noncommercial/share-alike terms; SkillCorner and Nate Sandholtz/BYU notices; Retrosheet attribution; and OpenBiomechanics noncommercial/share-alike terms with its additional professional-organization/financial-analysis affiliation exclusion
- **Distribution:** one explicitly licensed, odds-free normalized NFL snapshot is included. Original downloads, row-level derivatives, trained weights, and participant-level laboratory records remain excluded. Aggregate review does not grant broader data access, commercial rights, or permission to redistribute restricted inputs

[Benchmark attribution and licenses](DATA_LICENSES.md) · [Tactical derived-material terms and credits](docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md) · [Source-copy boundaries](docs/tactical/PUBLIC_SOURCE_RELEASE_NOTES.md)

Source-derived portions of this README, including the V2 table and figure, retain the corresponding provider terms above; original source-independent writing remains MIT. No provider endorsement is implied.

**Retrosheet acknowledgment:** The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

## Read next

- **Understand the problem:** [Project guide](docs/PROJECT_GUIDE.md) and [five-sport research synthesis](docs/research/FIVE_SPORT_RESEARCH_SYNTHESIS.md)
- **Audit a result:** [V2 comparisons](reports/v2/RESULTS.md), [tactical studies](docs/tactical/BENCHMARK_RESULTS.md), and [tactical replication](docs/tactical/REPLICATION_RESULTS.md)
- **Run the work:** [Benchmark reproduction](docs/v2/REPRODUCE.md) and [local workbench](docs/tactical/WORKBENCH.md)
- **Plan a defensible extension:** [Measurement gaps](docs/research/FIVE_SPORT_GAPS_AND_PRIORITIES.md) and [deployment requirements](docs/deployment.md)
