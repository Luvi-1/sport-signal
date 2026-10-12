# SportsLab external model comparison

Research checked 2026-10-11 UTC. This report covers pre-event match outcomes, not player props, in-play prediction, season standings, or betting returns. It is separate from the sealed v2 experiment and must not be used to tune against its final holdout.

## Bottom line

1. The existing models have reproducible held-out results, but there is no verified evidence here that they beat commercial forecasting systems.
2. A matched, third-party-preserved MLB archive provides a useful diagnostic: on 969 games, SportsLab v1 has 55.11% accuracy and 0.6817 log loss; FiveThirtyEight's pitcher-adjusted probabilities have 58.00% and 0.6766. The paired uncertainty interval includes no difference. Archival provenance is weaker than authenticated, timestamped forecasts.
3. The strongest practical next comparators are sport-specific probabilistic baselines and CPU tabular models: Dixon–Coles for soccer, published NFL Elo, surface/blended Elo for tennis, and regularized tree/linear models trained on identical permitted features. Their strength must be established on this project's chronological tests, not imported from unrelated benchmarks.
4. Opta, ESPN FPI, and FanGraphs are credible commercial/proprietary references. Their exact 2023–2025 matched-test accuracy, log loss, Brier score, and calibration are **not verified** here. Do not fill those cells with guessed or cross-cohort percentages.

## Subsequent V2 comparison

The preregistered V2 benchmark has now completed on a newer period. It measures
extended logistic models, histogram boosting, random forests, Extra Trees and an
independent lightweight Dixon–Coles-style soccer implementation, plus a frozen
ensemble and refitted baselines. See [all actual results](../reports/v2/RESULTS.md).
The goal model is not claimed to reproduce penaltyblog exactly. XGBoost,
CatBoost and TabPFN were researched as alternatives but were not run here; no
performance is invented for them. The commercial diagnostic below remains a
separate older-period comparison, not a V2 tuning set or full vendor ranking.

## Existing v1 reference cohort

These numbers are read from the repository's evaluation JSON and saved per-event predictions. Soccer class order is away/draw/home. Binary Brier scores use one positive-class squared error; soccer uses the sum across three classes, so Brier values must not be compared between sports.

| Sport and target | Exact test date span | Games | Accuracy | Log loss | Brier |
|---|---|---:|---:|---:|---:|
| EPL, regulation home/draw/away | 2023-08-11–2025-05-25 | 760 | 54.47% | 0.9576 | 0.5685 |
| MLB regular season, designated home win | 2023-03-30–2024-09-30 | 4,859 | 54.83% | 0.6836 | 0.2453 |
| NFL regular season, designated home win; ties excluded | 2023-09-07–2025-01-05 | 544 | 64.34% | 0.6395 | 0.2244 |
| ATP men's singles, canonical player A win | 2023-01-02–2024-12-18 | 5,856 | 65.22% | 0.6145 | 0.2137 |

Tennis dates are source tournament-start dates, not verified individual match starts. Tennis exclusions and the 21-day availability delay must be preserved or explicitly harmonized before a comparison. The project uses retrospectively corrected snapshots, not an immutable live data feed. The final v1 holdout has already been inspected; any newly chosen improvement needs a new untouched evaluation era.

## Comparator table

“Not verified” means no suitable auditable evaluation was obtained in this research; it does not mean the vendor never evaluated its model. Public documentation, an open algorithm, and open prediction data are different things.

| Sport | Comparator and openness | Exact relevant target / evidence | Published accuracy and calibration evidence | Availability, rights, and verdict |
|---|---|---|---|---|
| Soccer | Opta MA21 / Stats Perform; proprietary commercial system | EPL pre-kickoff home/draw/away probabilities are explicitly documented; live updates are a separate state | Matched cohort dates, N, accuracy, log loss, Brier, reliability: not verified | OAuth/licensed feed; request historical as-issued pre-match snapshots if authorized. Do not compare in-play values. [Official feed](https://developers.statsperform.com/feed-ma21-live-win-probability) |
| Soccer | FiveThirtyEight SPI; public historical outputs, not a fully reproducible current service | `prob1`, `probtie`, `prob2` are match outcome probabilities; historical files begin in 2016 | No full v1 holdout comparison: the publisher says sports forecasts stopped 2023-06-13, before this EPL holdout | Default data license CC BY 4.0. Old download endpoint now redirects to ABC HTML. Older-period retraining/backtests could be separate research if an archive is verified. [Schema](https://github.com/fivethirtyeight/data/blob/master/soccer-spi/README.md), [publisher notice/license](https://github.com/fivethirtyeight/data) |
| Soccer | Dixon–Coles / Poisson via penaltyblog; open implementation | Scores converted into a coherent home/draw/away distribution, fitted using preceding match results and time weights | No universal accuracy number; fit and score on identical SportsLab folds. Calibration must be evaluated locally | MIT code; data rights remain separate. High-priority CPU baseline. [Model documentation](https://penaltyblog.readthedocs.io/en/latest/models/overview.html), [license](https://github.com/martineastwood/penaltyblog/blob/master/LICENCE) |
| Baseball | FanGraphs Game Odds, Steamer/ZiPS-based; public display with proprietary projection components | Per-game win probability based on projected pitchers/lineups; distinct from playoff and season probabilities | Exact matched 2023/2024 records, sample count, accuracy and calibration: not verified | No open historical bulk forecast license/complete archive verified. Obtain rights and as-issued game odds before scoring; season odds are the wrong target. [Game Odds explanation](https://library.fangraphs.com/how-to-use-fangraphs-live-scoreboard/), [projection distinctions](https://www.fangraphs.com/standings/playoff-odds/about) |
| Baseball | FiveThirtyEight simple Elo and pitcher-adjusted ratings; public historical outputs | Home-win `elo_prob1` and `rating_prob1`; latter uses starting pitchers and preseason projections | **Locally computed preserved-archive diagnostic**, 969 games, 2023-03-30–2023-06-12: 56.04% / 0.6804 LL simple Elo; 58.00% / 0.6766 LL pitcher-adjusted. See audit below | Default data CC BY 4.0; source is a pinned third-party mirror. Not authenticated as-issued, not full holdout, not evidence of current commercial performance. [Primary field definitions](https://github.com/fivethirtyeight/data/blob/master/mlb-elo/README.md) |
| NFL | ESPN NFL FPI; proprietary | Game/season forecasts using football performance data [methodology](https://www.espn.com/nfl/story/_/id/13539941/how-espn-nfl-football-power-index-was-developed-implemented) | No verified matched NFL 2023/2024 N, accuracy, log loss, Brier, or calibration in this review | Public displays do not establish an open bulk archive/license. Require timestamped pregame forecasts. Do not import college-FPI percentages into NFL results |
| NFL | Opta MA21 American Football; proprietary commercial system | Pre-game and live win predictions; schema includes Home, Away, and OT Draw | Exact NFL coverage years, matched N, accuracy and calibration: not verified | OAuth/licensed. Confirm competition and historical snapshot coverage; harmonize tie handling and isolate pre-game state. [Official feed](https://developers.statsperform.com/feed-ma21-american-football-live-win-probability) |
| NFL | FiveThirtyEight NFL Elo; published runnable model and historical outputs | Basic Elo home-win probabilities; production archive separately documents quarterback-adjusted forecasts | Historical scoring example is not a measured accuracy percentage. No official 2023/2024 NFL holdout forecasts established after cessation | Published NFL Elo-game code is MIT; verify data-specific terms separately. Can run an explicitly labeled reimplementation on current data; do not call it a current FiveThirtyEight forecast. [Code and evaluation](https://github.com/fivethirtyeight/nfl-elo-game), [license](https://github.com/fivethirtyeight/nfl-elo-game/blob/master/LICENSE), [forecast schema](https://github.com/fivethirtyeight/data/blob/master/nfl-elo/README.md) |
| Tennis | Opta Tennis MA21; proprietary commercial system | Match winner probability; the documented `point=0` request selects pre-match predictions; omitted point selects latest state | Exact ATP coverage, historical dates, N, accuracy and calibration: not verified | OAuth/licensed. A genuine candidate if a permitted historical pre-match archive becomes available; never use latest/final probabilities. [Official feed](https://developers.statsperform.com/feed-ma21-tennis-predictions) |
| Tennis | Tennis Abstract Elo; published methodology, public ratings, some linked code | Overall/surface blend and best-of-five conversion; a published author backtest used about 50,000 ATP matches from 2000 through June 2017, excluding retirements/withdrawals | Author-reported 50/50 blended Elo: hard 68.6% accuracy/Brier .202; clay 68.0%/.207; grass 69.8%/.196. Exact per-surface N and strict untouched test selection not established in the post; log loss and reliability not provided | **Different cohort; cannot rank against v1's 65.22%.** Implement a methodology-inspired baseline; do not claim exact replication without all parameters. Existing tennis data remains noncommercial CC BY-NC-SA. [Published results](https://www.tennisabstract.com/blog/2017/06/23/unpredictable-bounces-predictable-results/), [methodology](https://www.tennisabstract.com/blog/2019/12/03/an-introduction-to-tennis-elo/) |
| All four | XGBoost / CatBoost; open training libraries | Binary or multiclass probabilities using identical pre-event features and temporal folds | No transferable sports accuracy. These are candidate learning algorithms, not pretrained sports forecasters | Apache 2.0 code; CPU-capable; actual runtime, calibration and gains must be measured. [XGBoost](https://github.com/dmlc/xgboost), [CatBoost](https://github.com/catboost/catboost) |
| All four | TabPFN; tabular foundation-model family, with version-specific open code/weight terms | Learns from supplied tabular training examples; not a sports-specialist pretrained forecast | Nature paper reports strong generic tabular classification/regression results; those are not sports accuracy or chronological sports calibration | Current repository separates Apache-2.0 code from weight licenses; v2 has attribution terms, newer versions noncommercial terms and license access flow. CPU size/runtime constraints matter. Pin a specific legal checkpoint and version; do not create an account or accept terms just to include a benchmark. [Paper](https://www.nature.com/articles/s41586-024-08328-6), [current code/access/license](https://github.com/PriorLabs/TabPFN) |

## Audited MLB diagnostic

### Data provenance

- Publisher: FiveThirtyEight, with [field definitions](https://github.com/fivethirtyeight/data/blob/master/mlb-elo/README.md) and [CC BY 4.0 default data license](https://github.com/fivethirtyeight/data/blob/master/LICENSE)
- Preservation: [Angelogallardo05/Assignment01, commit 04b528e1d5327aeb112672e39a6eb3a75a3bd4a5](https://github.com/Angelogallardo05/Assignment01/commit/04b528e1d5327aeb112672e39a6eb3a75a3bd4a5), committed 2024-02-04 03:59:36 UTC, file `mlb_elo_latest.csv`
- Downloaded file SHA-256: `12491eafd6e1ef2e97066b6517096381577e79f1db82b5e8cc141afbd6bfbc52`
- A second public preservation, [Megabuster/Data607](https://github.com/Megabuster/Data607/blob/main/data/Assignment1/mlb_elo_latest.csv), returned identical bytes; Git blob `36f84df384e2d772379a534c28b4982d52d23c9b`. Agreement corroborates preservation, not original forecast publication timing
- The primary MLB CSV download redirected to ABC News HTML on this research date. No publisher hash or match-specific issuance timestamps were verified
- The mirror has 2,429 rows, 1,099 with completed scores through June 20, 2023, despite the publisher's June 13 discontinuation notice. Conservatively, only games dated before June 13 were eligible. Later rows were not scored

### Matching and exclusions

The eligible archive has 989 completed pre-cutoff games, versus 992 local results in that date window. Three local matchups lack a completed source record: BOS–STL, OAK–TEX and WAS–NYM on May 14. Ten date/home/away keys represent doubleheaders: all 20 ambiguous rows were dropped rather than using a result to choose the corresponding forecast. The remaining 969 games all match both final scores and winner labels exactly.

All 30 MLB team identities map to valid local identifiers. Explicit changes are CHC→CHN, CHW→CHA, KCR→KCA, LAD→LAN, NYM→NYN, NYY→NYA, SDP→SDN, SFG→SFN, STL→SLN, TBD→TBA, FLA→MIA, WSN→WAS. No fuzzy matching was used. Both probability pairs sum to one within 1e-12, are strictly between zero and one, and contain no missing values.

Only documented probability fields were consumed. No postgame ratings, final scores, or other postgame features were fed into forecasts; final scores were used for outcome verification only. The schema distinguishes pre/post ratings, but cannot authenticate the actual publication time of each probability in this preserved copy.

Coverage is 969/4,859 = **19.94% of the full v1 holdout**. This is a seasonal subset with 12 calendar-week clusters, not a replacement final test.

| Forecaster on the identical 969 games | Accuracy | Log loss | Binary Brier | Top-label ECE, 10 bins |
|---|---:|---:|---:|---:|
| SportsLab v1 selected calibrated model | 55.11% | 0.6817 | 0.2444 | 0.0247 |
| SportsLab v1 calibrated Elo | 55.52% | 0.6829 | 0.2450 | 0.0171 |
| Preserved FiveThirtyEight simple Elo | 56.04% | 0.6804 | 0.2437 | 0.0050 |
| Preserved FiveThirtyEight pitcher-adjusted ratings | 58.00% | 0.6766 | 0.2419 | 0.0172 |

SportsLab minus pitcher-adjusted log loss is +0.00507; paired weekly-bootstrap 95% interval **[-0.00186, +0.01200]**, 2,000 replicates, seed 20261011. Against simple Elo: +0.00133, interval [-0.00157, +0.00402]. Negative favors SportsLab. Small samples, only 12 clusters, archival uncertainty, and unequal information sets prevent a decisive superiority claim. ECE is noisy and bin-dependent; its lowest observed value is not proof of best calibration.

The richer comparator uses starting pitchers and preseason projections. This is a systems comparison on common games, not a controlled test of algorithm quality with identical information. The finding is descriptive; do not select v2 features/hyperparameters from this newly inspected subset.

## Evaluation protocol to implement next

1. **Freeze scope before looking at outcomes.** Keep v1 unchanged. Record the v2 model menu, feature allowlist, historical availability rules, development folds, calibration partition, final untouched period and seed. Preserve a hash of this plan. If any final data were inspected for model selection, call that period development and reserve another test
2. **Two distinct comparison tracks.** A controlled model comparison uses identical pre-event features. A commercial-system comparison uses identical games and forecast cutoffs, while explicitly describing the commercial system's richer or different inputs. Neither should borrow accuracy from another league/era or mix pre-season, pregame and in-play tasks
3. **Required archive contract.** Provider, model/version, fixture ID, contestant IDs, designated home/away, tournament and round, actual start time, forecast issue time, forecast horizon, probability vector, correction/version history, known feature cutoff, source/license and checksum. “Last updated” alone is not proof an archived number existed before kickoff
4. **Align targets and identity.** EPL uses 90-minute result including stoppage time; MLB includes extra innings but only matching regular-season fixtures; NFL uses the project's no-tie cohort, disclosing whether a three-outcome vendor vector is renormalized conditional on no tie; ATP uses completed men's singles with identical retirement/walkover handling. Use event IDs and scheduled order for doubleheaders. For tennis, match by players, tournament, round and match number, not tournament-start date alone
5. **Never silently drop failures.** Report eligible N, available N, matched N, exclusion reasons and coverage by year/competition. Evaluate every comparator on its pairwise intersection and, separately, a common intersection if meaningful. Publish the local-model metric on each exact intersection
6. **Select and calibrate only on earlier data.** Use availability-aware expanding/rolling folds, group whole same-day batches and tennis tournaments, and preserve calibration gaps. Tune any Elo blend, decay, tree depth, ensemble weight or temperature only inside development. No random cross-validation of games across eras
7. **Score probabilities first.** Primary log loss; secondary Brier and accuracy. Report classwise reliability, bin counts, log loss by season and selected predeclared groups. Show paired cluster-bootstrap differences, preferably week/round/tournament blocks appropriate to each sport. Avoid interpreting many searched subgroup wins as confirmed improvements
8. **Publication standards.** Include complete predictions when licenses permit, hashes and reproducibility code. Otherwise provide aggregate results with audit logs. Model and data rights are separate. Do not claim profitable betting, production readiness, or commercial superiority without the necessary evidence

### Practical priority for the current deadline

- Complete CPU reproducibility and sealed new-holdout evaluation before introducing account-gated dependencies
- Test a score-distribution soccer baseline and genuinely stronger tennis Elo variant, plus restrained generic tabular alternatives, using the already permitted sources and earlier validation only
- For baseball, pre-event starting-pitcher quality is a published-methodology motivation; add it only after its identity/availability source is audited. For NFL, verify quarterback/starter and neutral-venue information similarly
- Treat commercial archives as missing inputs, not model failures. A later authorized Opta export could enable proper EPL/NFL/ATP evaluation. FanGraphs requires a verified historical game-odds archive and permitted use

## Closed-source LLMs and leakage

General-purpose closed-source LLMs should not be presented as trained sports predictors merely because they can answer sports questions. Prompting a model is inference, not sport-specific training. This research establishes no comparable GPT/Claude/Gemini sports accuracy and made no paid API calls.

A historical matchup name/date can reveal an outcome the LLM learned during pretraining, even if the prompt says to ignore later knowledge. A reported knowledge cutoff is not a clean-room guarantee. Browsing retrospective pages adds another leakage route. An LLM accuracy on old named games therefore does not measure real pre-event forecasting ability.

For a defensible future experiment, freeze the model version and prompt, supply only a timestamped pre-event feature packet, disable retrospective retrieval, demand a normalized probability vector, preserve raw outputs, predeclare handling of refusals/malformed responses, calibrate only on prior data, and evaluate prospectively after results arrive. An anonymized numeric-only packet can reduce named-event recall but does not itself prove no contamination. A genuinely prospective test is the stronger design. Keep computational cost, latency, output failure rate, training/inference distinction and data-sharing authorization in the report.

## Reproduction files

- `scripts/compare_mlb_archive.py`: local scorer (optional `--download` retrieves the pinned public archive) with source-byte lock, identity checks, paired metrics and bootstrap
- `reports/external/mlb_archive_diagnostic.json`: machine-readable results, source hashes and local v1 artifact identity
- `reports/external/mlb_archive_quality_checks.json`: extra matching and source-preservation audit
- `artifacts/external/mlb_archive_matched_predictions.csv`: local per-game matched outputs; do not republish without retaining source attribution and reviewing the project's data-release policy

Raw preservation files are research inputs kept outside the project release. No model retraining, paid subscription, API-account creation, third-party outreach, or betting action was performed for this report.
