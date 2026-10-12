# Primary literature and professional methods review

Searched/reviewed 2026-10-11 UTC. This review connects the requested mechanics to measurable factors, estimands and credible evaluation. It is not a systematic review with an exhaustive database search or a meta-analysis. “Reviewed” means the cited methods/results sections or full text were inspected; “screened” means the abstract/official description was inspected and claims are correspondingly limited. Open papers do not confer reuse rights on their underlying sports data.

Evidence strength is question-specific. A precise laboratory measurement can be strong evidence about a mechanism but weak evidence about an MLB/NFL game intervention. An observational predictive model can forecast well without identifying an action's causal effect. A professional deployment description can establish practical relevance without making its proprietary training data public.

## Baseball: decision models, sequence and physical execution

### B01. Yee and Deshpande, *Evaluating plate discipline in Major League Baseball with Bayesian Additive Regression Trees* (2023)

[Primary paper](https://arxiv.org/html/2305.05752); [author code](https://github.com/ryanyee3/plate_discipline_code). Reviewed methods and results.

Uses component probabilities and run consequences to compare swing/take value, with BART uncertainty rather than only a hard good/bad decision. The components separate called-strike probability when taking and contact probability when swinging. Important location/context controls and simplifying conditional-value assumptions remain. The paper's cross-validation is not our prospective temporal test. Adopt the factorization, uncertainty and interpretable location baseline; do not claim identified counterfactual benefit from a plug-in decision surface. Backward citation followed to Vock and Vock.

### B02. Vock and Vock, *Estimating the effect of plate discipline using a causal inference framework* (2018)

[DOI](https://doi.org/10.1515/jqas-2016-0029); [author repository](https://github.com/docvock/G_computation_pitchfx). Screened primary abstract and inspected repository description.

G-computation frames plate discipline as a potential-outcomes problem rather than treating observed swing and take groups as exchangeable. Useful methodological precedent for a future policy study, but sequential exchangeability, measured confounders and support would need defending. The repository's analysis examples and code do not automatically license upstream MLB rows for this portfolio. Do not copy an “optimal” policy without reproducing the estimand and assumptions.

### B03. Powers and Yurko, *Swinging, Fast and Slow* (2025)

[Primary paper](https://arxiv.org/html/2507.01238); [author analysis repository](https://github.com/saberpowers/predictive-pitch-score). Reviewed full main text and methodological sections.

Separates observed bat speed from latent swing intent/timing using hierarchical modeling and instrumental-variable reasoning, then models power/contact tradeoffs. Observed point-of-contact speed is jointly affected by how the hitter intends to swing and how well the ball is timed. This directly warns against reading a speed coefficient as “swing harder and improve.” The paper uses detailed 2024 data and additional outcome-model seasons; full kinetic time series are not generally public. Followed citations into timing/biomechanics and football IV strategy research.

### B04. Takamido and Nakamoto, *Machine learning modeling of hit-into-play probability and quantification of pitch sequence effects* (2026, v2 dated October 5)

[Verified latest version](https://arxiv.org/abs/2606.17345v2). Reviewed PDF methods, validation and findings. Search engines still surfaced the older June title about counterfactual optimization; use v2.

The target is terminal in-play versus swinging strikeout in a selected two-strike PA sample, not all-pitch contact or optimal pitch selection. It uses final/preceding pitch tracking, 2018–2025 excluding 2020, qualified pitchers, prior-year batter statistics, 2025 holdout and expanding-window checks. Earlier pitches add limited predictive value beyond the final pitch in this setting. This supports an honest history ablation, not a general claim that sequencing never matters. Final-pitch measurements are realized execution, and qualified-pitcher/terminal-outcome selection narrows transportability.

### B05. Park and colleagues, *Structure of Pitch-Pattern Motifs* (2026)

[Primary paper](https://arxiv.org/html/2601.11904). Reviewed methods and main findings.

Uses large-scale historical pitch sequences, motifs and entropy to characterize repertoire organization. Structured sequencing can exist without a strong relationship to outcome performance. The main contribution is descriptive organization, not a validated intervention. It motivates sequence-frequency/backoff summaries and null comparisons, but not a promise that a motif ranking identifies the best next pitch.

### B06. Lee and Ko, *Unified Pitch Graphs for Diagnosing Pitching Strategy* (2026)

[Primary paper](https://arxiv.org/html/2609.03810). Reviewed architecture, use cases and limitations.

Builds a hierarchical event graph for multiscale retrospective querying and diagnosis, retaining lineage and sparse-context backoff. The authors distinguish description from causal or forward predictive claims. This is useful for a scout-facing interface that exposes exactly which pitches support a context, but a graph is not itself evidence of superior strategy. Its data span into 2026; our implementation must independently handle that season's measurement changes. Backward references led to game-theoretic and ball-flight work.

### B07. Sidhu and Caffo, *MONEYBaRL: Exploiting pitcher decision-making using reinforcement learning* (2014)

[Primary paper](https://arxiv.org/abs/1407.8392); [DOI](https://doi.org/10.1214/13-AOAS712). Reviewed abstract, assumptions and method sections.

Models count/pitch-selection transitions as an MDP, computes strategies through value iteration, and evaluates against conditional distributions from a different season. That cross-season design is better than evaluating on the fitted transition table, but the result is still governed by model distributions and simplifying Markov/opponent assumptions. Useful as a sequence-aware backoff baseline and policy-simulation reference; not evidence that a real pitcher would remain unchanged after an opponent adopts the suggested strategy.

### B08. Melville and colleagues, *A Game-Theoretical Approach to Optimal Pitch Sequencing* (2023)

[Official Sloan paper page](https://www.sloansportsconference.com/research-papers/a-game-theoretical-approach-to-optimal-pitch-sequencing); [author thesis](https://scholarsarchive.byu.edu/etd/9910/). Screened abstract/official description.

Uses game-theoretic decision structure to represent pitcher–batter interaction rather than assume an unreactive opponent. Relevant future direction for repertoire/command-aware policy simulation. No claim is made here to have reproduced its equations or results; full identification, calibration and achievable command distributions would be necessary before adopting a recommendation. Its numerical performance is not used as a portfolio benchmark.

### B09. Delgado, *Optimal Pitch Sequencing* research thesis (2023)

[Harvard primary repository record](https://dash.harvard.edu/entities/publication/903f2cff-bc66-425a-8eeb-4299c255b687). Screened abstract.

Examines MDP-style policies with empirical game/count context and regularization. This is a useful alternative to deterministic “always throw the best-looking pitch” rules. Simulated improvements under estimated transition models are not field experiments. Treat as a methodological lead requiring deeper reproduction only if a licensed measured-pitch policy task is chosen.

### B10. *SmartPitch* (MIT thesis, 2022)

[Institutional primary record](https://dspace.mit.edu/entities/publication/a980df36-353c-49e1-9d8b-58fff4681d4f). Screened abstract/metadata.

A pitch-selection modeling lead, not a validated comparator in this review. Included to document the broader search rather than imply full replication. The chosen first implementation should remain simpler and auditable unless this or another advanced model demonstrates incremental value on identical information and future seasons.

### B11. *Strategic Pitch Location: The Role of Two-Pitch Sequences in Pitching Success* (SABR, 2023)

[Author research article](https://sabr.org/journal/article/strategic-pitch-location-the-role-of-two-pitch-sequences-in-pitching-success/). Reviewed method and discussion.

Studies two-pitch location transitions with clustering/transition summaries and performance associations. It supports batter-relative location transitions as a candidate feature and the need to reset at PA boundaries. Aggregated cluster differences do not establish what would happen if the same pitcher changed the sequence while everything else remained fixed. Use as a candidate-generating study, with future-season ablation and sparse-cell uncertainty.

### B12. Professional pitch-quality component models

[Stuff+, Location+, Pitching+ author primer](https://library.fangraphs.com/pitching/stuff-location-and-pitching-primer/); [PitchingBot author primer](https://library.fangraphs.com/pitching/pitchingbot-pitch-modeling-primer/). Reviewed official model-author explanations.

These distinguish physical pitch characteristics, realized location/count context, and combined outcome estimation. They motivate component models and pitch-relative normalization. “Location” is not “command,” because intended targets are missing. The public explanations are primary professional methodology references, not full open-source reproductions, and current vendor values cannot be assumed to be historically frozen out-of-sample predictions. Our system should not reuse their branding for a different model.

### B13. Kagan and Nathan, *Statcast and the Baseball Trajectory Calculator* (2017)

[Author-hosted paper](https://baseball.physics.illinois.edu/Statcast-TPT.pdf); [DOI](https://doi.org/10.1119/1.4976652). Reviewed physical framing and source reference.

Provides a ball-flight/trajectory framework grounded in measured tracking. It supports defensible derived flight geometry when the input parameters, coordinate system and approximation are known. It does not allow reconstruction of pitch angles from game scores or reconstruction of a pitcher's body pose from a ball trajectory. A calculated angle must specify its evaluation plane and treatment of gravity/acceleration.

### B14. Smith, seam-shifted-wake research (2021)

[Primary thesis](https://digitalcommons.usu.edu/etd/7903/); [journal DOI](https://doi.org/10.1177/1754337120961609). Reviewed primary description and physical findings.

Seam orientation can alter wake structure and aerodynamic forces, so spin-axis/rate descriptions do not fully capture pitch movement. This is a physically grounded missing factor, not an excuse to impute exact seam orientation from outcome residuals. Controlled experimental conditions differ from game inference; a movement residual may have several causes.

### B15. Cowger, baseball flow-field research (2025)

[UCLA primary thesis](https://escholarship.org/uc/item/6mz24386). Screened institutional abstract and methods description.

Controlled flow measurements expand the aerodynamic mechanism inventory: seam placement, spin and airflow interact. This supports explicit physics limits in an execution model but supplies neither a professional game cohort nor causal pitch-selection effects. Included as a mechanism source, not as a predictive benchmark.

### B16. Nakashima and colleagues, bat-path and temporal accuracy study (2025)

[Open primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11985794/). Reviewed main measurement/design description.

A controlled collegiate batting sample investigates how swing geometry and timing relate. Its measurement is closer to actual mechanics than pitch-outcome strings, but the sample and batting conditions limit MLB transport. It informs definitions of bat path and timing rather than a universal stance/angle prescription. A focused companion review assesses this alongside other kinetic-chain and batting studies.

### B17. Contact-depth mechanics study (2026)

[Open primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13517717/). Reviewed main design and findings.

Uses a collegiate sample with many batted-ball observations to relate contact depth and swing variables. Contact location, attack angle and exit outcome have joint structure; a one-variable “optimal contact depth” is not established. Repeated observations within hitters require grouped analysis, and conditioning on batted balls omits misses and takes. Treat this as observational mechanics evidence for a separate contact-stage model.

The focused `baseball_biomechanics_review.md` adds primary work on professional joint loading, fatigue, injury, release-metric inference, stance/perception and environment, with explicit population and evidence-strength labels. It should be read before deciding that a public-event-only model covers the requested mechanics.

## American football: anticipation, value and tracking mechanics

### F01. Fernandes and colleagues, *Predicting plays in the National Football League* (2019/2020)

[Primary journal record](https://journals.sagepub.com/doi/abs/10.3233/JSA-190348); [DOI](https://doi.org/10.3233/JSA-190348). Screened abstract/official description.

Uses historical play context for pass/run prediction and compares predictive performance with simpler interpretable models. It establishes the task as a genuine football analytics use case. Historical headline accuracy is not a fair modern baseline without matching cohort, decision moment, season split and class balance. Our comparison uses proper probability scores and identical information across simple and stronger models.

### F02. Teich, Lutz and Kassarnig, *NFL Play Prediction* (2016)

[Primary paper](https://arxiv.org/abs/1601.00574). Reviewed PDF feature/target/evaluation sections.

Despite its broad title, this paper predicts play success, yards and a progress measure using features that include realized pass direction/depth and QB run. It removes several consequential outcomes, including sacks/fumbles. It is therefore **not** a valid pre-snap pass/run benchmark. Useful as a caution about titles, post-action information, outcome selection and majority-class accuracy. We do not adopt its play-choice optimization interpretation without a causal design.

### F03. Yurko, Ventura and Horowitz, *nflWAR* (2018/2019)

[Primary paper](https://arxiv.org/abs/1802.00998). Reviewed method framing.

Builds expected-points/win-probability and multilevel player valuation from public play-by-play, including football-aware uncertainty. Important precedent for separating context from individual contribution and shrinking noisy player effects. PBP cannot fully allocate credit for off-ball coverage or line protection without additional measurements; a public-event model's precision should not be mistaken for complete causal player value.

### F04. Brill, Yee, Deshpande and Wyner, *Moving from Machine Learning to Statistics: The Case of Expected Points in American Football* (2024)

[Primary paper](https://arxiv.org/html/2409.04889). Reviewed main methodological critique.

Explains selection effects from team quality and unequal possession/drive contributions, correlated outcomes within scoring sequences, and the role of uncertainty and smoothness in EP modeling. This is a reason to use grouped evaluation and carefully defined value targets, not simply feed EPA into every task. A prediction target can be well modeled yet still unsuitable for comparing causal play-call alternatives.

### F05. Baldwin, nflfastr EP/WP/CP and xPass methods (2020 onward)

[Author model documentation](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/); [official xPass reference](https://nflfastr.com/reference/add_xpass.html). Reviewed feature and target descriptions.

Provides practical baselines and separates probability models for different stages. xPass uses a dropback concept rather than only successful pass attempts, making sack/scramble handling important. A provider's current model may have been refit on later years, so stored scores are not automatically an honest historical holdout comparator. Prefer a locally frozen context baseline unless training provenance is established.

### F06. Nguyen, Yurko and Matthews, STRAIN (2023)

[Primary paper](https://arxiv.org/html/2305.10262). Reviewed methods and data description.

Measures dynamic rusher pressure through closing speed relative to distance from the QB, with opponent/context adjustment. Uses frame-level tracking and blocking/rushing role information on a selected passing-play cohort. This demonstrates why binary sacks miss meaningful pressure mechanics, but the metric cannot be reconstructed from number of defenders in the box or a final pressure flag. It motivates a future licensed dynamic task with an explicit frame-time cutoff.

### F07. Hong and colleagues, *Feeling the Pressure: A Unified Framework for Automating Pass-Rushing Statistics in NFL Games* (2024)

[Amazon Science primary publication page](https://www.amazon.science/publications/feeling-the-pressure-a-unified-framework-for-automating-pass-rushing-statistics-in-nfl-games). Reviewed full downloaded paper.

Builds role/engagement and pressure models from tracking with expert labels, using graph and tabular approaches. Its train/test seasons differ, a useful temporal precedent. It relies on rich NGS/PFF-style information rather than public box-count aggregates. Whole-play labeling, instantaneous pressure and pre-snap susceptibility are different tasks; a graph's later-frame inputs must not enter the at-snap benchmark.

### F08. Yurko and colleagues, *Going Deep: Models for Continuous-Time Within-Play Valuation of Game Outcomes in American Football with Tracking Data* (2019/2020)

[Primary paper](https://arxiv.org/html/1906.01760). Reviewed main method framing.

Tracks evolving value within a play rather than assigning all credit at the final event. Useful for running-space, movement and dynamic opportunity analysis, but requires real player trajectories. The conceptual value surface cannot be manufactured from match scores or sparse event summaries. Evaluation must keep frames of the same play/game together.

### F09. Deshpande and Evans, expected hypothetical completion probability (2019/2020)

[Primary paper](https://arxiv.org/abs/1910.12337). Reviewed abstract and method framing.

Models completion difficulty and hypothetical unchosen receiver options, addressing missing counterfactual covariates rather than pretending unthrown routes have observed outcomes. It motivates uncertainty about QB alternatives and careful target-selection bias. Receiver separation at catch time is not available at the snap, and even a throw-time model requires a new information cutoff and measurements absent from the audited FTN/PBP cohort.

### F10. Nguyen and Yurko, pre-snap timing and motion (2025/2026)

[Primary preprint](https://arxiv.org/abs/2502.16313); [research-lab paper](https://cmsac-research-lab.github.io/papers/snap-timing/snap-timing.html); [journal version](https://academic.oup.com/jrsssa/article/189/3/1988/8315856); [author code](https://github.com/qntkhvn/timing). Reviewed models and measurement design.

Uses detailed pre-snap tracking to model snap timing heterogeneity and motion patterns. A binary `is_motion` flag is only a coarse shadow of these trajectories. Associations with defensive disruption can motivate film review but do not identify the causal effect of adding motion to an otherwise unchanged play. A real timing model needs formation-set and snap timestamps, movement histories and QB/team variation.

### F11. Michels and colleagues, integrated unsupervised/supervised defensive scheme modeling (2026)

[Primary paper, v2](https://arxiv.org/html/2602.10784v2). Reviewed method and validation sections.

Uses a nonhomogeneous HMM for latent guarding assignments around motion, then supervised man/zone classification. Nested/random cross-validation and team-held-out checks answer different questions from future-season deployment. Adopt the careful distinction between alignment and responsibility; do not call FTN personnel counts a substitute for guarding trajectories. Future work should add chronological transport evaluation.

### F12. NFL/Amazon, *Decoding Defensive Coverage Responsibilities* (2026)

[Primary paper](https://arxiv.org/html/2603.25901v1). Reviewed architecture, data split and observation window.

Factorized attention models coverage assignments/matchups using rich tracking and expert labels, with 2020–2023 training and 2024 testing. Some observation windows extend beyond the snap toward the throw. Its performance therefore does not establish pre-snap scheme prediction from public data. Useful for defining latent responsibilities and minimum tracking needs; not an implementable open-data benchmark under the current constraints.

### F13. Putman and Tolhurst, *Tackling Endogeneity: Optimal Pass Rate ... Instrumental Variables* (2025)

[Primary SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5159158); [DOI](https://doi.org/10.2139/ssrn.5159158). Screened primary abstract; found through a backward citation from the batting-intent paper.

Important because observed pass/run choices are endogenous: personnel, defensive response, game state and information known to coaches affect both the choice and outcome. An instrumental-variable study is not assumption-free, but it makes the identification problem explicit. This portfolio should forecast tendency and describe conditional risk, not infer an optimal pass rate from raw EPA differences.

### F14. Official Big Data Bowl examples and professional finalists

[Official repository](https://github.com/nfl-football-ops/Big-Data-Bowl); [2024 official finalist descriptions](https://operations.nfl.com/gameday/analytics/big-data-bowl/2024-big-data-bowl-winner-and-finalists/). Reviewed README/FAQ/schema and official descriptions.

Demonstrate professional relevance of frame-level tackle, pressure, movement and coverage questions. Competition descriptions are not peer-reviewed causal evidence, and the data-access terms vary by release. The surviving tiny official example cannot support a broad modern NFL benchmark. Do not substitute a competition mirror for required signup/terms or imply that a code license grants data reuse.

The companion `football_mechanics_review.md` extends this set with blocking assignments/opponent adjustment, tackle geometry, QB biomechanics, health/workload, environment and rule/coaching effects. Its source-specific limitations are part of the research gate.

## Synthesis: what the literature changes in the design

- **Mechanics must have a measurement source.** Physical flight, joint kinetics, bat motion, player trajectories, formation categories and event outcomes are different modalities. No single public table supplies all of them.
- **Prediction time matters as much as model family.** Actual pitch location can validly describe execution but is not a perfectly known pre-pitch choice. Actual rushers and route outcomes leak an at-snap forecast.
- **Component models are scientifically useful.** Separate swing, contact, called strike and downstream run value; separate play tendency, pressure and completion. A single match-win model cannot answer each question.
- **Strategic selection is a recurring confounder.** Better players receive different opportunities, and coaches/players react to opponents. The best observed action is not automatically the best intervention.
- **Sequence value is empirical.** Rich motifs and a compelling mechanics story do not guarantee incremental held-out predictive gain. Prespecify a same-information ablation and retain null results.
- **Simple baselines remain mandatory.** Context tables, regularized regression/GAMs and calibrated trees establish what tracking or history actually adds. Do not compare an advanced full-feature model only to a constant.
- **Generalization has several axes.** Future season, unseen player/team, different tracking system and laboratory-to-game transport are distinct. Label which one was actually tested.
- **Uncertainty is part of the result.** Repeated pitches/plays/frames are clustered. Sparse matchups and rare formations need shrinkage, support counts and honest intervals rather than a confident heatmap.
