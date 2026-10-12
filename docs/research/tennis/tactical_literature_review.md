# Tennis tactical analytics: research map and operational factors

Date: 11 October 2026. Read together with `biomechanics_factor_review.md` (30 sources and 52 mechanics/perception/environment factors), `data_contract.md`, and `tactical_model_design.md`.

## 1. What the research supports

A useful professional-tennis portfolio should answer a narrow scouting question: **given this player, opponent, score and observed shot prefix, what serve or response patterns are plausible, and how uncertain is that estimate?** That is more defensible than predicting a generic match winner or presenting a preferred shot as a proven intervention.

The literature separates several problems that are often conflated:

1. **Tendency:** which action a player is likely to choose
2. **Execution:** where the ball actually goes relative to a stated or unobserved intention
3. **State value:** the conditional chance of a subsequent outcome, given the observed state
4. **Policy:** which intervention would improve results against an adapting opponent
5. **Mechanics:** the body/racket/ball processes that constrain execution

The first three can be investigated observationally with suitable data and timing. The fourth needs stronger counterfactual assumptions or experiments. The fifth needs actual measurements. Neither a three-category direction code nor a player's historical win rate supplies missing geometry or mechanics.

## 2. Documented search and scope

### Search date, channels and inclusion

Public searches were run on 11 October 2026. Discovery covered general web scholarly indexing, arXiv, PubMed/PMC, journal originals, authors' university manuscripts, conference proceedings, GitHub and Hugging Face repositories, official ITF rules, and Tennis Abstract's original documentation. This was a broad, targeted evidence map, **not** a registered systematic review, database census, or a claim to have found every published paper. No fabricated PRISMA result counts or inaccessible database searches are reported.

Primary work was prioritised if it measured or modelled professional/advanced tennis serve, return, shot selection, placement, rally transitions, movement or execution; introduced relevant uncertainty/validation methods; or clarified a necessary factor unavailable in open match data. Laboratory and collegiate work was retained with explicit transfer limits. Reviews were used for backward citation discovery rather than counted as independent confirmation. Generic winner-prediction papers without a tactical measurement contribution, unverifiable dataset marketing, and tutorials without primary methods were not the basis for design.

Reading labels below: **FT** = public full text/author manuscript inspected; **A** = original abstract/record inspected; **FT-indexed** = relevant full-text passages indexed, but direct retrieval incomplete. A paper being public does not mean its data is downloadable or licensed. Bibliographic dates refer to the work, not the date a copy appeared on arXiv or was crawled.

### Query families actually used

- tennis serve direction Bayesian hierarchical models; tennis serve direction machine learning Match Charting Project
- tennis next shot location prediction tracking memory generative; tennis expected shot value VON CRAMM
- tennis intention execution Markov process optimal aiming; stated realized optimal serve targets experimental
- tennis return impact position spatial mixture latent style; tennis return depth direction quality decay
- tennis rally length player characteristics shot-level stochastic model; tennis unforced errors rally survival
- tennis mixed strategy equilibrium serve direction; disequilibrium play dynamic tennis
- tennis tactical diversity entropy; serve plus one short points professional men women surface
- tennis serve speed placement quality metric; public CourtVision Hawk-Eye tennis tracking license
- Match Charting Project schema codes license; tennis point-by-point Grand Slam serve width depth
- tennis video rally tactical annotations TRACE TennisVAR; TrackNet ACE-Rallies; 3D tennis motion dataset
- tennis pressure previous errors serve performance; professional tennis coaching effectiveness
- tennis travel sleep time zones professional cohort; tennis injury surveillance Wimbledon
- ITF off-court coaching rules 2025; current ITF rules and event-specific scoring

The companion mechanics review records additional searches for stance, kinetic sequencing, spin, split-step timing, anticipation, running strokes, fatigue, heat and ball/surface physics.

### Citation chaining and unresolved leads

Backward/forward chains included: serve-direction modelling → Tea/Swartz → CourtVision and handedness/anticipation studies; return mixture modelling → tracking/state-value models → VON CRAMM and execution-error MDPs → the September 2026 aiming experiment; short-point/rally studies → phase-specific transitions and unforced-error modelling; biomechanical reviews → original marker, force, radar and video studies. Exact-title searches checked newer work and corrections. The 2025 tactical-diversity correction changes affiliations, not the article's inconsistent match count. The serve-spin paper has a linked corrigendum in the mechanics review.

Some original publisher pages were unavailable or paywalled; accessible author manuscripts or original abstracts were used and labelled. The original Sackmann Slam repository is now 404, an OSF pressure-study link returned 403, and the 3DTennisDS site could not be verified. These are explicit gaps, not inferred permission to use mirrors or undocumented endpoints.

## 3. Primary tactical and statistical studies

### Serve choice and shot response

**T01. Zhu & Naikar, “Predicting Tennis Serve Directions with Machine Learning” (MLSA 2022; proceedings 2023).** [Conference paper](https://dtai.cs.kuleuven.be/events/MLSA22/papers/MLSA22_paper_7402.pdf), [later arXiv copy](https://arxiv.org/html/2602.22527v1). DOI 10.1007/978-3-031-27527-2_7. FT. MCP: 3,424 men's and 1,916 women's matches before selecting players with at least 30 matches. Player-specific models use score/history and other engineered variables. Reported accuracy near 49%/44% uses random 70/30 point splits within players, not chronological whole-match tests. Adopt the serve-choice question and lagged context, not those numbers as deployment expectations. Engineered “run” and “anxiety” indices are not measured movement or mental state. The 2026 arXiv upload is not a new 2026 experiment.

**T02. Tea & Swartz, “The Analysis of Serve Decisions in Tennis using Bayesian Hierarchical Models” (2023).** [Author manuscript](https://www.sfu.ca/~tswartz/papers/tennis1.pdf). DOI 10.1007/s10479-021-04481-7. FT. Uses 82 men's/81 women's Roland Garros matches in 2019–2020, with 23,588/14,862 serves. Multinomial hierarchical modelling pools player effects and considers serve number, court side, handedness, match state and impact information. It includes faults by assigning nearest zones or projecting net-fault paths. The authors acknowledge imputation bias and nonlinear-flight limitations. Borrow shrinkage and all-attempt denominators; do not relabel imputed directions as known intentions, or impact coordinates as pre-motion inputs.

**T03. Kovalchik & Albert, “A Statistical Model of Serve Return Impact Patterns in Professional Tennis” (2022).** [Primary preprint](https://arxiv.org/abs/2202.00583). FT. Uses 142,803 returns by 141 ATP players, 2018–2020, and a Bayesian latent-style spatial mixture. Context-conditioned player distributions outperform simpler mixture alternatives in the reported predictive comparison. Six styles provide a useful model of heterogeneity. Return-contact location is not pre-serve positioning, and style membership is uncertain rather than a fixed player identity. The underlying row-level release/license was not verified. This source also appears in the mechanics review and must not be counted twice as independent evidence.

**T04. Kovalchik, Ingram, Weeratunga & Goncu, “Space-Time VON CRAMM: Evaluating Decision-Making in Tennis with Variational generatiON of Complete Resolution Arcs via Mixture Modeling” (2020).** [Primary preprint](https://arxiv.org/abs/2005.12853). FT. Models functional 3-D ball and 2-D player trajectories using scalable Gaussian-mixture methods, trained on roughly 125,000 men's and 80,000 women's Australian Open shots. A 20% holdout and calibration checks support conditional trajectory/state-value modelling; the inspected text does not establish a chronological match-grouped split. Its measurements are substantially richer than MCP. A categorical prefix-value model can be inspired by this work, but cannot claim to reproduce its continuous spatial state or ball physics.

**T05. Fernando, Denman, Sridharan & Fookes, “Memory Augmented Deep Generative Models for Forecasting the Next Shot Location in Tennis” (2019).** [Primary preprint](https://arxiv.org/abs/1901.05123). FT. Australian Open 2012 data supplies 8,780 shots from Djokovic, Nadal and Federer. Models use tracking-derived context and player adaptation for next-shot location and winner/error/continuation classification. The paper allocates chronological shots 70%/25%/5% to train/test/validation, without a clear whole-match boundary guarantee. Three famous players and spatial-error metrics are inadequate evidence of calibrated generalisation to the full tour. This is a useful sequence-model precedent, not justification for a complex network before frequency baselines.

**T06. Srinivasan, Subramanian & Knottenbelt, “Thinking the GOAT: Imitating Tennis Styles” (2023).** [Sloan paper page](https://www.sloansportsconference.com/research-papers/thinking-the-goat-imitating-tennis-styles), [institutional record](https://spiral.imperial.ac.uk/entities/publication/c2b93941-ee68-421b-8693-bcfff732dc12). A/selected public paper description. Tracking-based imitation learning models multimodal, player-specific responses. Its FFT-supplied data is not a verified open training source here. Behavioural imitation describes what players do; it does not establish which action would be optimal. Retain as an advanced-method lead, not a reproduced benchmark.

### Intention, execution and strategic optimisation

**T07. Chan, Fearing, Fernandes & Kovalchik, “A Markov process approach to untangling intention versus execution in tennis” (2021 preprint; journal DOI 10.1515/jqas-2021-0077).** [Primary manuscript](https://arxiv.org/abs/2110.01527). FT. Uses a tracking-derived generative environment and many simulated shots to distinguish action selection from execution uncertainty in a Markov model. This is a valuable conceptual separation, but intended targets are not directly observed in match data and simulator assumptions determine counterfactual results. Do not present model-generated optimal actions as experimentally demonstrated coaching improvements.

**T08. Sandholtz, Hanson, Hager, Kovalchik & Fellingham, “Stated, Realized, and Optimal Aiming Strategies for the Tennis Serve” (2026 preprint, v2).** [Primary text](https://arxiv.org/html/2607.28500v2), [author repository](https://github.com/nsandholtz/byu_tennis_serves). FT. Eight NCAA men explicitly marked targets; 567 attempts supply measured bounce locations and radar speed. Hierarchical execution-error models account for net censoring; point-value surfaces are imported from a generative professional model. This directly distinguishes stated aim and realised distribution centres. It does not observe completed points, freely adapting returners or professional-match outcomes. The preprint is not peer-reviewed evidence of causal tactical improvement. It also contains a 57-versus-56 count discrepancy between introduction/results; do not repeat a precise headline count without resolving it.

**T09. Nübel, Dockhorn & Mostaghim, “Match Point AI: A Novel AI Framework for Evaluating Data-Driven Tennis Strategies” (2024).** [Primary preprint](https://arxiv.org/html/2408.05960v1), [official code](https://github.com/cnuebel98/Match_Point_AI_Public). FT. Uses 295,354 men's MCP rallies from 2017–2023 to inform a discrete tennis simulation and Monte Carlo tree search. Special shots are simplified/omitted and depth is not an actively selected, outcome-driving variable in the described environment. Valuable as a transparent planning sandbox; not evidence that an agent has learned real court geometry or validated optimal professional tactics. Any future simulator needs its own held-out transition and rollout checks.

**T10. Gauriot, Page & Wooders, “Expertise, gender, and equilibrium play” (2023).** [Original journal](https://onlinelibrary.wiley.com/doi/full/10.3982/QE1563). FT-indexed. Uses detailed professional serve data and a test designed to address heterogeneity in mixed-strategy equilibrium assessment. Findings depend on expertise, grouping and equilibrium assumptions. A predictable serve distribution is not automatically an exploitable policy: the returner's response, payoff variation and adaptation matter. Tracking data described in the study is not a verified licensed open source for this implementation.

**T11. Anderson, Rosen, Rust & Wong, “Disequilibrium Play in Tennis” (2025; online 2024).** [Journal DOI](https://doi.org/10.1086/732529), [author manuscript](https://axelanderson.georgetown.domains/DynamicTennis.pdf). FT author version. MCP-based dynamic serve-strategy analysis accounts for service-game state and action history and reaches a different equilibrium assessment. The disagreement with T10 is a reason to examine estimands and assumptions, not select the most dramatic recommendation. Observational direction/outcome frequencies omit intention, receiver expectations and tactical adaptation. Replication DOI [10.7910/DVN/RQ6JVL](https://doi.org/10.7910/DVN/RQ6JVL) was located, but its files/rights were not independently audited here.

### Rally phase, errors, diversity and serve quality

**T12. Epasinghege Dona, Gill & Swartz, “What does rally length tell us about player characteristics in tennis?” (2025; online 2024).** [Author manuscript](https://www.sfu.ca/~tswartz/papers/tennis_rally.pdf), [journal](https://doi.org/10.1093/jrsssa/qnae027). FT. MCP serve-attempt data, 1970–2022, supports player-specific rally-length distributions and changing serve advantage across touches. The reported WAIC comparison on recent serves is not a chronological prospective evaluation. The paper carefully distinguishes touches including errors from rally counts. Borrow phase-specific transition/hazard modelling and shrinkage; do not interpret long-rally success among survivors as evidence that deliberately extending a rally causes success.

**T13. Peiris, Epasinghege Dona & Swartz, “Analysis of the Impact of Unforced Errors in Tennis” (2024 preprint).** [Author manuscript](https://www.sfu.ca/~tswartz/papers/unforced.pdf), [arXiv](https://arxiv.org/abs/2407.19321). FT. Uses a large MCP corpus to study error/winner patterns by touch and model hypothetical error reductions. Useful for distinguishing consistency from attacking outcomes. Forced/unforced labels are subjective, and changing an error label in a model does not simulate the pace, placement and opportunity tradeoffs of a real technique change. Bootstrap uncertainty does not remove those counterfactual assumptions.

**T14. Prieto-Lage et al., “Match analysis and probability of winning a point in elite men's singles tennis” (2023).** [Open original](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0286076). FT. Observational analysis of 4,669 points in the quarterfinals onward of three 2021 Slams links serve/rally patterns to outcomes across surfaces and reports observer agreement. The later-round male sample and post-outcome rally grouping limit transfer and causal interpretation. Its supplementary aggregate table is not a verified downloadable point-level dataset. Final rally length must not enter a pre-point prediction.

**T15. Fitzpatrick et al., “Investigating the most important aspect of elite grass court tennis: Short points” (2021).** [Original journal](https://journals.sagepub.com/doi/10.1177/1747954121999593). FT-indexed. Analyses 211 men's and 209 women's Wimbledon matches from 2015–2017 with IBM data. Different short-point lengths have different relationships with match outcomes; the findings do not justify a universal “serve-plus-one wins tennis” rule. The contribution is a precisely defined short-point comparison, not randomised evidence for allocating training time or choosing a shot. Grass, radar availability and match exclusions constrain coverage.

**T16. Li, Balajee, Wieand & Pipping-Gamon, “A unified server quality metric for tennis” (2026).** [Original journal](https://journals.sagepub.com/doi/full/10.1177/22150218261444537). FT-indexed. Uses Wimbledon/US Open serve speed, placement and variation with crossed server/returner effects, separating first/second serves and men's/women's play. A serve-proximal outcome and temporal appendix test are more relevant to tactical quality than generic match accuracy. Zero-speed and missing-placement exclusions risk court/player selection; aggregate serve descriptors must be computed from training history only. A short-point target still reflects return and serve-plus-one skill, not isolated causal serve quality.

**T17. Zhao et al., “Quantifying the technical-tactical diversity of elite tennis players during match-play” (2025).** [Original article](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1634573/full), [correction](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1738474/full). FT. MCP shot/serve entropy and mixed models describe diversity in 2023 Australian/US Open play. The abstract says 236 matches while methods say 266; the published correction addresses affiliations. Avoid treating either count as verified. Entropy measures variety at a chosen resolution, not automatic tactical quality; sample size, available opportunities and rare categories affect it. Estimate history-only, support-adjusted profiles rather than “more variety is better.”

### Pressure, coaching, readiness and rules

**T18. Harris, Vine, Eysenck & Wilson, “Psychological pressure and compounded errors during elite-level tennis” (2021).** [Original abstract/method passages](https://www.sciencedirect.com/science/article/pii/S1469029221001059), [author manuscript](https://ore.exeter.ac.uk/repository/bitstream/handle/10871/125808/ORE.pdf). A/FT-indexed. Studies 658,068 points across 3,552 matches at 12 Slams, 2016–2019. A score-derived pressure index and preceding errors are associated with subsequent errors in mixed models. The index is situational leverage, not measured anxiety, and prior-error effects can reflect changing difficulty or latent state. Include lagged context as a hypothesis; do not label players as psychologically fragile. Linked OSF data was not accessible in this pass.

**T19. Maynard et al., “Effect of Travel on Sleep Patterns and Athletic Performance in Female Professional Tennis Players…” (2026; online November 2025).** [Original PubMed record](https://pubmed.ncbi.nlm.nih.gov/41272436/). A. Fifty-two adult WTA professionals provided wearable data. Travel/time-zone changes were associated with altered sleep, especially the first night, but the study found no significant correlation between sleep disruption and competition performance. This directly cautions against a deterministic jet-lag penalty. Tournament locations do not reveal actual flight/arrival dates, sleep, acclimation or recovery, and individual biometric data is not publicly available for this portfolio.

**T20. Zhu et al., “Elite tennis player's perceptions of coaching effectiveness” (2024).** [Author-hosted manuscript](https://www.mcgill.ca/sportpsych/files/sportpsych/zhu-et-al-2024-elite-tennis-player-s-perceptions-of-coaching-effectiveness-cover.pdf). FT-indexed. Interviews/documents from six elite Chinese players identify planning, teaching, strategy and interpersonal relationships as relevant. These qualitative reports expand the factor inventory; they do not supply a numerical causal coaching coefficient or in-match intervention estimate. Coaching changes can respond to poor form and coincide with other changes. An accurate public coach start date would still be a context marker, not proof of its effect.

**T21. McCurdie et al., “Tennis injury data from The Championships, Wimbledon, from 2003 to 2012” (2017; online 2016).** [Original open article](https://pmc.ncbi.nlm.nih.gov/articles/PMC5384430/). FT-indexed. Retrospective medical-presentation surveillance highlights definition and exposure-denominator problems. A medical encounter, time-loss injury, retirement and reduced performance are distinct events. This does not provide a public, prospectively timestamped health registry for individual predictions. Do not infer an injury from a slower serve or extract a diagnosis from casual notes; any later use needs verified public statements and strict known-at-time handling.

**O01. ITF coaching/rules change.** [Official explanation](https://www.itftennis.com/en/news-and-media/articles/explained-off-court-coaching-to-be-allowed-from-2025/), [2025 amendments](https://www.itftennis.com/media/7224/2025-amendments-to-the-rules-of-tennis-and-beach-tennis.pdf), [current rules index](https://www.itftennis.com/en/about-us/governance/rules-and-regulations/). Off-court coaching became permitted under the rules from 2025 subject to sanctioning-body/event conditions, after earlier trials. A simple pre/post-2025 dummy is not a randomised coaching experiment and misses prior adoption. Rules must be versioned by event/date, including no-ad, final-set tie-breaks, serve clocks, let handling and player-analysis-technology permissions.

### Original data-owner interpretation

**D01. Tennis Abstract documentation and return-quality analysis.** [Serve glossary](https://www.tennisabstract.com/blog/2019/08/17/match-charting-project-serve-stats-glossary/), [rally glossary](https://www.tennisabstract.com/blog/2019/08/17/match-charting-project-rally-stats-glossary/), [tactics glossary](https://www.tennisabstract.com/blog/2019/08/17/match-charting-project-tactics-stats-glossary/), [7 October 2026 return-quality analysis](https://www.tennisabstract.com/blog/2026/10/07/how-long-does-return-quality-matter/). These are primary data-owner definitions/analysis, not peer-reviewed intervention evidence. Return depth and direction have phase-dependent associations, while longer-rally cohorts change composition. Definitions of serve-and-volley, net approaches, inside-out and short-point denominators require care. Use them to define transparent summaries, not to claim an optimal coaching prescription.

## 4. Additional operational factor inventory

The 52-factor mechanics matrix covers body/racket/ball measurements, stance, contact, incoming-ball constraints, split-step, movement, fatigue, surface and weather. The following **32 complementary tactical/context factors** complete the inventory for design; related concepts overlap intentionally and are not 84 statistically independent predictors.

Availability: **M** = directly/derivably available in MCP after validation; **H** = only from strictly prior charted history; **E** = separate external measurement/source needed; **G** = material gap. Prediction times: **P0** before serve motion; **P1** after first fault/before second serve; **Pk** after a specified observed prefix, before the next action. A field observed at Pk cannot be moved back to P0.

| ID / factor | Operational measurement and time | Tactical relevance / confounders | Feasibility |
|---|---|---|---|
| C01 Server identity/experience | Stable name ID; prior match count at P0 | Individual repertoire; charting frequency is not true tour experience | M/H; partial pooling |
| C02 Returner identity/skill | Stable opponent ID and prior return outcomes at P0 | Opponent constraints and mutual adaptation; opponent quality/selection | M/H; two-actor grouping |
| C03 Handedness pairing | R/L/unknown for both players at P0 | Serve-side geometry and nominal FH/BH targeting; run-around strokes break simple mapping | M; preserve unknown |
| C04 Stroke-specific repertoire | Prior FH/BH/slice/volley/drop/lob distributions | Available shot family versus all-purpose skill; opportunity bias | H; stage-conditioned |
| C05 Serve period | First/second attempt at P0/P1 | Risk and continuation value; second serves follow selected first faults | M; separate targets |
| C06 Service side | Deuce/ad before motion | Direction/hand interaction; nonstandard rules and penalties | M only after reconstruction |
| C07 Prior first-fault location | Observed categorical direction/error before P1 | Conditional second-serve response; execution versus intent | M at P1, unavailable P0 |
| C08 Current serve location | Wide/body/T after current serve observed | Return preparation/response; speed/spin/receiver position omitted | M at return-stage query |
| C09 Current return family/hand | Coded actual return after it occurs | Serve-plus-one opportunity; survivor cohort | M at Pk, not P0 |
| C10 Return direction/depth | Optional coded zones after return | Early point structure; no exact position, missingness by charter | M with observation flags |
| C11 Incoming shot sequence | Last one/two or full prior coded strokes | Pattern dependence; current endpoint labels can leak | M with strict prefix masking |
| C12 Rally phase/contact count | Number of already attempted contacts | Serve advantage decay; final length is future information | M; explicit convention |
| C13 Net/approach state | Coded +/−/= and type-based defaults | Transition to volley/pass; opportunity quality and selection | M coarse state, not coordinates |
| C14 Point ending/hazard | Next winner/error/continuation | Avoid dropping terminal responses; subjective forced/unforced | M as target only |
| C15 Score | Pre-point points/games/sets, server-relative | Risk context and state leverage; post-point score leakage | M after transition validation |
| C16 Tie-break/rules state | Event/date-specific format and tie-break progress | Serve order, sides, terminal conditions | M partial + E rules; quarantine ambiguity |
| C17 Score leverage | Change in game/set value under explicit model | Situational stakes; model dependent, not measured anxiety | Derived M, train-only parameters |
| C18 Prior error/outcome | Completed previous point/shot, never current label | Short-memory tendencies; latent difficulty/score adaptation | M/H; associative |
| C19 Serve-direction history | Smoothed prior counts by side/period/context | Opponent-specific preparation; look-ahead aggregation | H with cutoff and backoff |
| C20 Pattern variety/entropy | Bias-aware prior categorical entropy with support | Predictability; class resolution/opportunity distribution | H; uncertainty required |
| C21 Matchup history | Prior meetings available before cutoff | Familiarity and response patterns; sparse samples and aging | H, heavily shrink; no future head-to-head |
| C22 Surface/event conditions | Categorical surface at P0; measured court pace separately | Bounce/time constraints; season and player-selection confounding | M surface; E pace, roof, balls |
| C23 Event/round/format | Verified metadata and rules at P0 | Competition context and sample selection; event ID can memorise era | M partial; grouping/sensitivity |
| C24 Longitudinal change | Date/era and recency weighting of prior observations | Development, equipment, coaching, aging and drift | M/H; mechanism not identified |
| C25 Prior workload | Past points/sets/minutes/matches before P0 | Exposure/recovery hypothesis; MCP is an incomplete schedule | H partial; E complete schedule/durations |
| C26 Rest/arrival/travel | Actual prior end time, arrival time, distance/time zones | Recovery/circadian hypotheses; calendar location is not itinerary | E/G; do not invent travel or fatigue |
| C27 Current physical readiness | Consented/reliably measured sleep, RPE, HRV etc before event | Within-player physiological context; device/selection variation | G for public portfolio |
| C28 Verified injury/availability | Timestamped official report with known-at-time flag | Participation/technique constraints; selective disclosure/reverse inference | G currently; never diagnose from errors |
| C29 Coaching relationship | Verified start/end dates and relevant role | Strategy/development context; selection into coaching changes | E/G; no causal coefficient |
| C30 In-match instruction | Timestamp, content, delivery and compliance | Potential tactical intervention; coach acts after trouble | G; rules permission is not evidence instruction occurred |
| C31 Opponent anticipation/adaptation | Measured movement/position or elicited belief before action | Strategic payoffs depend on responses; hidden intentions | G in MCP; tracking/experiment needed |
| C32 Annotation/provider process | Charter/source, year, visibility and missing-code rates | Measurement drift and selection; may proxy player/popularity | M for audit/stratification, not default predictive shortcut |

## 5. Important interactions and unresolved questions

- **Hand × side × serve period × opponent:** a natural low-dimensional interaction, with shrinkage for rare left-handed matchups
- **Incoming shot × stroke family × phase:** shot choice is constrained by the ball already received; compare like opportunities, not all forehands against all backhands
- **Position × movement × contact mechanics:** professionally relevant but absent from MCP. No categorical proxy recovers the missing interaction
- **Pace × spin × placement × surface:** separately measured or unavailable; “slice” and “clay” do not determine rpm, bounce height or time pressure
- **Score × prior errors × individual:** a hypothesis about observable choices, not an anxiety detector or a stable “clutch gene”
- **Workload × rest × weather × readiness:** prior point counts alone do not identify physiological fatigue, and incomplete charting undercounts exposure
- **Coaching × rules × era:** policy permission, actual coaching, player response and resulting performance are distinct quantities
- **Intent × execution × opponent response:** the BYU experiment measures the first two on a small domain; ordinary match charting does not identify all three

Priority evidence gaps are professional women's continuous tracking, routine early-round/lower-ranked coverage, true pre-contact receiver positioning, intended shot targets, calibrated spin/height/time measurements, annotation reliability across volunteers, complete point-level timestamps, verified data-publication histories, and longitudinal coaching/readiness interventions. A strong portfolio can make these gaps explicit instead of filling them with persuasive labels.

No reviewed study licenses the conclusion that every available factor should enter one large model. Feature groups require an availability test, a measurement-validity test, and an out-of-time incremental-value test. A simpler model that survives those tests is preferable to a large model with unmeasured concepts hidden behind proxy names.
