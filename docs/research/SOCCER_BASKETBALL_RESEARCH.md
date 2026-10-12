# Soccer and basketball tactical modeling: research and data audit

Research date: 11 October 2026 (UTC). Status: research/data audit complete; candidate protocols are pending parent/reviewer approval; no tactical model has been fitted in this work. This is a scoped literature-and-source audit, not a claim to have found every paper or every determinant of performance.

## Decision summary

1. **Soccer: build a shot-quality model with an explicit defensive-context ablation.** StatsBomb's shot freeze frames make goalkeeper position and recorded defenders available at shot time. The first deliverable should distinguish geometry-only xG from geometry plus visible defensive context, and quantify the incremental value on identical held-out shots. A snapshot is not continuous tracking, complete pitch occupancy, body orientation, or a tactical intervention.
2. **Basketball: use SkillCorner's official ACB release for a small, honest at-release shot-context demonstrator.** Actual shots, nearest-defender distance, linked events and raw 25 Hz tracking are available. There are only 10 independent games, so this cannot establish reliable generalization to another league or a modern NBA model. A larger public shot-chart model is a different, lower-context task with unresolved upstream reuse questions for many commonly copied NBA sources.
3. **Keep motion, passing options and off-ball value as distinct extensions.** They require trajectories, visibility checks, action timing, turnover/foul/rebound outcomes, and sufficient independent games. Do not rename a make-probability model “optimal shot selection” or make the match-outcome engine appear to observe defensive assignments that it does not contain.

These recommendations follow the source inspections below. They are engineering judgments, not results of a model comparison.

## Prediction moments and estimands

- **Pre-match:** historical information available before tip-off/kick-off. Current-match shots, defenders and eventual lineups cannot be inputs.
- **Action start:** a state before a pass, drive, screen or shot choice. Only earlier observations are available; the eventual chosen action and its endpoint may already be future information.
- **At release/contact:** the player has chosen to shoot; geometry and prior motion may be used to predict this shot's outcome. This is the preferred first tactical estimand.
- **Post-release:** flight, block, save, landing position and entry angle can support a separate execution model. They cannot improve a pre-release prediction without leakage.
- **Retrospective availability:** all inspected datasets are historical, processed releases. “At-release state” describes what the attributes represent, not a verified real-time data delivery guarantee.

For soccer, the primary outcome is the probability of a goal conditional on a recorded, valid non-penalty shot. For basketball, it is the probability of a make conditional on a recorded field-goal release, **including fouled misses**. The basketball quantity `(2 or 3) × P(make)` is expected immediate field-goal points, not full expected possession value. It excludes free-throw rewards and future rebounds/continuation.

## 1. Search method and evidence hierarchy

The search used public web search, publisher full text, arXiv author manuscripts, official provider GitHub repositories, Figshare record APIs, and source-file byte inspection. Search date was 2026-10-11. Promising papers were followed backward through their references and forward to named extensions (e.g., soccer EPV to the 2025 replication benchmark; soccer OBSO to basketball BMOS/BIMOS; defensive tracking to trajectory-based contest analysis). The 2021 basketball review was used to identify primary studies, not as a substitute for them.

Included: original empirical or methodological papers about shot quality, spatial opportunity, defensive geometry, action value, motion, matchups, possession decisions or relevant data quality; official data releases with auditable scope and reuse terms. Peer-reviewed articles, conference work and preprints are distinguished. Excluded from substantive evidence: anonymous claims, betting tips, unsourced performance leaderboards, synthetic data presented as real, and downstream repositories that could not establish their data provenance. Paywalled abstracts may identify gaps but do not establish uninspected methods. This is a structured scoping review, **not a PRISMA systematic review**: screening counts and exhaustive database coverage are not claimed.

Representative exact search queries executed:

- `soccer expected goals freeze frame goalkeeper defenders shot angle peer reviewed model open data`
- `soccer "expected goals" Anzer Bauer 2021 tracking data`
- `football VAEP pitch control EPV TacticAI papers Pappalardo Spearman`
- `site.arxiv.org soccer "Actions Speak Louder than Goals"`
- `site.arxiv.org soccer "SoccerMap"`
- `site.arxiv.org soccer "expected possession value" Fernández`
- `soccer "Beyond Expected Goals" Spearman 2018 pdf`
- `soccer tactical positioning compactness scoring opportunity tracking "systematic review"`
- `soccer set pieces corners delivery zone defensive marking goal research open access`
- `Bauer Anzer Data-driven detection counterpressing 2021 10.1007`
- `"The dual problem of space" "Raabe"`
- `"Wide Open Gazes" soccer 2026`
- `"Valuing La Pausa" soccer 2026`
- `soccer open tracking datasets PFF World Cup 2022 license official`
- `site.zenodo.org basketball play-by-play shot coordinates`
- `basketball open data license CC BY shot locations`
- `basketball expected possession value shot selection defensive pressure paper Cervone Bornn 2014`
- `basketball optimal shot selection Skinner Rao 2010 shot clock quality defensive distance`
- `basketball defensive pressure nearest defender distance shot efficiency tracking study open access`
- `basketball shot selection spatial angle shooter velocity body orientation expected points research paper`
- `basketball screens pick roll defense tracking data deep learning research`
- `basketball space creation offball movement expected possession value open paper`
- `"Quantifying Shot Quality" NBA Chang 2014 pdf`
- `"The hot hand" "defender" basketball 2014 Bocskocsky`
- `"basketball" "Replaying" "Sandholtz" "Bornn"`
- `"basketball" "Statistical" "tracking" "Terner" "Franks" review`
- `"basketball" "Cut attributes" Supola Hoch Baca 2023 drives`
- `"Mathematical models for off-ball scoring prediction in basketball" code data`
- `"basketball" "fatigue" "shooting" professional systematic review`
- `"basketball" "dataset" "Creative Commons" "shot"`
- `"NBA" "SportVU" "data" "License" github neilmj`

### What this search deliberately does not imply

No open-data search can establish all causal determinants of scoring. Important unmeasured variables include intent, communication, coaching instructions, unobserved physical condition, ball spin, gaze, and aspects of body posture. A well-cited model using private tracking data does not make that training data public. A method's reported score on its own split is not a comparable benchmark for this portfolio.

## 2. Soccer: primary methods and their practical meaning

### S1. Synchronized tracking xG: Anzer and Bauer (2021)

The [published study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2021.624475/full) combines 105,627 shots with tracking, using shot/keeper geometry, line-of-shot defenders, pressure, ball control and shooter motion. Crucially, event timestamps alone misrepresent the release state; a separately evaluated synchronization procedure was necessary. **Transferable lesson:** defender geometry is worth testing, but trustworthy event alignment comes before sophisticated modeling. Its proprietary training set and different evaluation design prevent a direct performance comparison with this project.

### S2. Event-only xG and contextual covariates: Mead et al. (2023)

[Expected goals in football: Improving model performance and demonstrating value](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282295) studies public Wyscout event data, including location and contextual/player information. **Transferable lesson:** start with interpretable distance/angle/body-part baselines, then test additional information. Player ability and team-quality variables require a strict as-of history; final-season summaries are not legal pre-shot inputs. Event data alone cannot establish defender positions.

### S3. Player/position partial pooling: Bayes-xG

[Bayes-xG](https://arxiv.org/abs/2311.13707) develops hierarchical logistic models on StatsBomb data. It explores whether player/position differences persist as context is enriched. **Transferable lesson:** use shrinkage and distinguish chance creation from finishing; do not rank sparse player residuals as stable skill. The manuscript's broader dataset is heterogeneous and some competitions are player-selected, so this project must define a more explicit sampling population.

### S4. Action value rather than only shots: Decroos et al., VAEP

[Actions Speak Louder Than Goals](https://arxiv.org/abs/1802.07127) values actions through changes in short-horizon scoring and conceding probabilities. **Transferable lesson:** passes, carries and defensive actions can contribute without producing an immediate shot. Action value measured after an action is an evaluation target, not information available before choosing that action. Full event sequences and possession/team orientation are essential.

### S5. Pitch control and off-ball opportunity: Spearman (2018)

[Beyond Expected Goals](https://static.hudl.com/craft/downloads/SSAC2018_Beyond_Expected_Goals.pdf) models off-ball scoring opportunity from space control, ball movement and scoring probability. **Transferable lesson:** a player can create a valuable receiving position without touching the ball. This requires motion assumptions and tracking; event locations cannot substitute for the positions of all players. Parameters such as reaction time and movement speed are modeling assumptions that need sensitivity analysis.

### S6. Space creation: Fernández and Bornn (2018)

[Wide Open Spaces](https://www.sloansportsconference.com/research-papers/wide-open-spaces-a-statistical-technique-for-measuring-space-creation-in-professional-soccer) separates occupying valuable space from creating it for teammates. **Transferable lesson:** off-ball runs can alter nearby defenders and teammates' options. A static shot freeze frame cannot establish the preceding movement or credit the runner who created it.

### S7. Spatial pass surfaces: SoccerMap

[SoccerMap](https://arxiv.org/abs/2010.10202) learns pass-probability surfaces from 740 EPL matches and 433,295 passes using player locations, velocities and contextual channels. It uses match-level random splits, not forward-time evaluation. **Transferable lesson:** compare simple engineered features with spatial models on identical matches, but do not equate selected-pass accuracy with validated predictions for every unchosen destination. The reported private-data result is not a target this small open-data project can promise to reproduce.

### S8. Decomposed soccer EPV: Fernández, Bornn and Cervone

The [EPV framework](https://arxiv.org/abs/2011.09426) decomposes scoring/conceding value into action choice, action success and subsequent value. Its 633 matches are separated by match, with calibration on validation data. **Transferable lesson:** distinguish the probability of choosing an action from its success and downstream reward. The paper's finite reward horizon is an explicit approximation, not a literal value of every future consequence.

### S9. Replication and domain plausibility: Overmeer et al. (2025)

[Revisiting Expected Possession Value](https://arxiv.org/abs/2502.02565) reports difficulty reproducing the earlier EPV approach, proposes U-Net-based models and a curated state-pair benchmark, and studies ball height. Aggregate loss/calibration can miss implausible local value surfaces. **Transferable lesson:** combine held-out proper scoring rules with prespecified football sanity cases; report replication failures. A curated plausibility benchmark supplements, rather than replaces, representative prospective validation.

### S10. Body orientation: Arbués-Sangüesa et al. (2020)

[Using Player's Body-Orientation to Model Pass Feasibility](https://arxiv.org/abs/2004.07209) adds pose-derived facing direction to pass feasibility. **Transferable lesson:** movement bearing, torso orientation and gaze are different quantities. The first two cannot be interchanged; neither proves the third. StatsBomb event/360 data lack pose. SkillCorner's two-match soccer body-pose sample supports a limited measurement demonstration, not a validated orientation-effect model.

### S11. Corner structure: TacticAI (2024)

[TacticAI](https://www.nature.com/articles/s41467-024-45965-x) predicts corner receivers and shots and generates positional variants with graph networks. The study retained 7,176 aligned corners and used random splits; coach preference evaluated usefulness. **Transferable lesson:** corner receiver/shot occurrence is a distinct target, with all-player positions and velocities at delivery. Preference for generated tactics is not an experimental estimate of additional goals. No equivalent open training corpus was verified here.

### S12. Pressing and transition detection: Bauer and Anzer (2021)

[Data-driven detection of counterpressing](https://link.springer.com/article/10.1007/s10618-021-00763-7) combines expert annotations with positional features. **Transferable lesson:** proximity alone is not a full pressing strategy. Features observed seconds after losing possession can classify the realized response, but would leak when predicting a decision at the turnover. The published transition-level split is not a substitute for match-grouped chronological evaluation.

### S13. Tactical context and formation

[In-game formation changes](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.914915/full) and [playing tactics with contextual variables](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0226978) motivate separating attack/defense phase, score state and opponent quality. **Transferable lesson:** nominal formation is not a measurement of real-time spacing. Teams choose tactics in response to the match, so observational formation associations are not causal prescriptions.

### S14. Emerging pose-aware perception (2026 preprint)

[Wide Open Gazes](https://arxiv.org/abs/2602.18519) combines head/shoulder pose with probabilistic visibility and pitch-control surfaces. **Transferable lesson:** visual access is a meaningful future factor, but inferred head direction is not eye tracking. Its 32-game pose-enhanced dataset and derived-value outcome do not establish an effect on actual goals. Treat as an emerging measurement approach, not a ready feature in the current event model.

## 3. Basketball: primary methods and their practical meaning

### B1. Continuous expected possession value: Cervone et al.

[A Multiresolution Stochastic Process Model](https://arxiv.org/abs/1408.0777) models continuous movement and discrete possession events with hierarchical spatiotemporal transitions. **Transferable lesson:** pass, dribble and shot value must consider continuation and turnover risk. Expected points at a state is different from the probability of making a chosen shot. The author's [demonstration repository](https://github.com/dcervone/EPVDemo) provides a small example; no standalone redistribution license was found in its inspected tree.

### B2. Who shoots, where, and against whom: Franks et al. (2015)

[Characterizing defensive skill](https://arxiv.org/abs/1405.0231) infers defensive assignments and models shot frequency separately from efficiency, with hierarchical shrinkage. Its analysis excludes several complicated possession types. **Transferable lesson:** defense may deter shots as well as alter conversion. The nearest defender at release is not always the assigned defender, and a defender's observed opponent make rate is confounded by assignments and shot selection.

### B3. Optimal stopping under the clock: Skinner (2012)

[The problem of shot selection](https://arxiv.org/abs/1107.5793) shows how the threshold for taking a shot depends on remaining opportunities and turnover risk in a theoretical model. **Transferable lesson:** the same make probability can imply a different decision with different time remaining. This does not make a distance-only shot chart an optimal policy; opportunity distributions and possession dynamics must also be estimated.

### B4. Policy simulation: Sandholtz and Bornn (2018)

[Replaying the NBA](https://www.lukebornn.com/papers/sandholtz_ssac_2018.pdf) simulates team-specific, clock-dependent possession transitions under altered shot policies. **Transferable lesson:** a decision model needs pass/turnover/foul branches and repeated states. Counterfactual results depend on the transition model remaining appropriate when the policy changes; they are not evidence from actually changing the team's strategy.

### B5. Short-window micro-action value: DeepHoops

[DeepHoops](https://arxiv.org/abs/1902.08081) uses trajectory windows to predict terminal actions, explicitly including fouls, turnovers and no terminal action. **Transferable lesson:** sample many non-shot moments and preserve rare-event prevalence when estimating probabilities. Overlapping windows from one possession must never cross validation boundaries. Its aggregate point mapping is a modeling choice, not the full value of every individual shot.

### B6. Pass/dribble paths and interception: Kono and Fujii

[BMOS/BIMOS](https://arxiv.org/abs/2406.08749) extends soccer off-ball opportunity models to basketball, including interception along the ball's path. The study uses 630 historical NBA games with a 580/50 game split. **Transferable lesson:** a passing lane's risk is not determined only by who controls the destination. Movement/ball-speed assumptions and incomplete sequences matter. Its large SportVU source is not equivalent to the ten-game ACB release.

### B7. Defensive gaps for cuts: Supola et al. (2023)

[Cutting on a teammate's drive](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0281467) models defender depth and perpendicular distance from the cutter-to-basket path, plus past changes. **Transferable lesson:** relational geometry offers an interpretable tactical target. However, the training examples were qualitatively selected cut/spot-up actions, so predicted cut feasibility is not a population scoring probability. The public supplement contains selected movement attributes, not a complete independently reusable NBA tracking season.

### B8. Ball-screen defensive coverage

[Recognizing and Analyzing Ball Screen Defense](https://www.sloansportsconference.com/research-papers/recognizing-and-analyzing-ball-screen-defense-in-the-nba) uses tracking to identify coverage schemes. **Transferable lesson:** screen angle, defender routes and switching are sequential interactions. A completed screen's coverage label may be a valid retrospective classification but is not automatically available at screen initiation. SkillCorner's action annotations offer examples, with limited game diversity.

### B9. Contest geometry versus execution trajectory: Daly-Grafstein and Bornn

[In-game shot trajectories](https://arxiv.org/abs/1905.00822) relates defensive context to trajectory-derived shot quality using more than 50,000 shots. **Transferable lesson:** defender location, contest angle and height are distinct from ball entry angle and depth. Flight-derived features are post-release and must not enter the at-release model. Our ACB player tracking keeps player z at zero and does not measure hand reach or jump height.

### B10. Adaptive shot selection and apparent hot hands

[Heat Check](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2481494) considers changes in shot difficulty and defensive response after recent performance. **Transferable lesson:** streak-based make rates mix changing opportunity selection with player performance. If recent history is tested, compute it strictly before the shot and control for current opportunity quality; a short run of makes is not proof of a changed underlying skill.

### B11. Measured pressure and shot distance in game observation

[Performance factors in women's basketball](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2022.1042718/full) analyzes defensive pressure and shot distance in a small observational sample spanning U19 and senior competition. **Transferable lesson:** pressure and distance are concrete candidate variables, while null results for clock/quarter or physiological measures in a small sample are not evidence of universal irrelevance. Population and measurement differences prevent direct NBA/ACB transfer claims.

### B12. Fatigue and biomechanics as explicit gaps

[Basketball-induced fatigue and three-point kinematics](https://www.mdpi.com/2075-4663/12/3/63) illustrates that physical condition and shooting mechanics can be measured in designed studies. **Transferable lesson:** elapsed minutes or distance run are exposure proxies, not direct measurements of fatigue. The inspected public game datasets do not provide the physiological or joint-level measurements needed to make individualized fatigue claims.

### B13. Review-guided boundaries

[Terner and Franks' review](https://arxiv.org/abs/2007.10550) connects spatial shot models, player evaluation, hierarchy and team strategy, and emphasizes causal challenges. It guides the breadth of this review. **Project implication:** retain skill/selection separation, opponent context, regularization and uncertainty; do not use an attractive court visualization as a substitute for an identified decision target.

## 4. Broader determinants, contrary findings and evidence boundaries

The companion [factor inventory](SOCCER_BASKETBALL_FACTOR_INVENTORY.csv) contains **94 factors: 45 soccer and 49 basketball**, with definitions, actual measurement routes, prediction cutoffs, target relevance, confounders, feasibility and primary-source URLs. Evidence codes distinguish methodological prediction studies (M), bounded experiments (E), observational studies (O), source documentation (D), and a measurement/evidence gap (G). These are evidence types, not a numerical quality score or a claim of causal certainty. A factor can be important in the sport yet unavailable or unjustified as a predictor here.

### Additional primary studies followed during the gap search

- **Finishing skill and model bias:** [Biases in Expected Goals Models Confound Finishing Ability](https://arxiv.org/abs/2401.09940) is an author preprint directly relevant to interpreting goals-minus-xG. Residual differences can reflect omitted context and model bias as well as finishing. This argues for partial pooling, repeatability checks and restrained player rankings, rather than adding current-season goals to an at-shot model.
- **Kicking measurement reliability:** [Lees and Rahnama (2013)](https://pubmed.ncbi.nlm.nih.gov/24245053/) tested repeated maximal instep kicks by ten skilled amateur/semi-professional players with optoelectronic measurement. Trial-to-trial variation matters even in a controlled setup. A single broadcast-estimated knee angle is therefore a descriptive observation, not a stable player trait.
- **Foot–ball contact mechanics:** [Ball impact dynamics of instep soccer kicking](https://pubmed.ncbi.nlm.nih.gov/19276844/) used ultrahigh-speed observation of contact. This is a different measurement scale from 10/25 Hz broadcast tracking. Foot contact point, deformation, stiffness and spin remain real mechanisms that the proposed match models do not observe.
- **Soccer fatigue is not a universal accuracy penalty:** [Ferraz and colleagues' randomized repeated-measures study](https://www.sciencedirect.com/science/article/pii/S2095254616000247) involved 24 semi-professional players. Their protocol affected maximal ball speed without a significant accuracy change. This is useful contrary evidence against automatically labeling later shots less accurate because players must be tired; laboratory protocols and real matches differ.
- **Basketball fatigue results depend on protocol and population:** [Slawinski et al. (2018)](https://researchonline.ljmu.ac.uk/7364/14/10.1515_hukin-2017-0156.pdf) did not find the anticipated changes in the measured three-point kinematics in its young elite sample, whereas the [2024 high-level-player experiment](https://www.mdpi.com/2075-4663/12/3/63) found changes under a different simulation protocol. Neither establishes a universal game-clock-to-fatigue conversion. The 2018 release variables were partly model-estimated, which must not be confused with directly tracked flight.
- **Physics does not imply one ideal angle for everyone:** [Hamilton and Reinschmidt (1997)](https://pubmed.ncbi.nlm.nih.gov/9386207/) model free-throw success as a function of launch angle, speed and spin under explicit physical constraints. Their optimum depends on release height and variability. It is a theoretical sensitivity model, not evidence that a generic angle recommendation improves every player's shooting.
- **Spatial shot allocation:** [Sandholtz, Mortensen and Bornn (2020)](https://arxiv.org/abs/1912.05129) compare spatial shooting ability and attempt allocation within lineups. This sharpens the opportunity-cost question, but an unchosen teammate's observed shooting percentage is not automatically the value of passing to them in the current defended state.
- **Player style versus ability:** [Miller et al. (2014)](https://arxiv.org/abs/1401.0942) use spatial point processes and low-rank representations to summarize shooting patterns. [Williams et al. (revised 2025)](https://arxiv.org/abs/2405.10453) use hierarchical modeling for propensity/ability comparisons. These support shrinkage and separating shot diet from conversion skill, not estimating hundreds of player interactions from ten games.
- **Weather and match context:** [The five-season Bundesliga study](https://pubmed.ncbi.nlm.nih.gov/33690609/) analyzes 1,530 matches and position-specific physical/technical activity. [The 2015 Chinese Super League study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6862007/) uses 240 matches and mixed modeling. These are observational match-performance analyses; their findings do not establish a universal coefficient for individual-shot xG. Venue-time measurements, opponent strength and seasonal confounding matter.
- **Crowd and venue are separable:** [The European no-spectator study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0248590) examines changes in match processes and home advantage. A nominal home team in a neutral tournament is not proof of home-venue familiarity or crowd support.
- **Travel and circadian exposure:** [Eastward jet lag in the NBA](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2022.892681/full) is an observational schedule/performance study. Travel direction and schedule are not direct sleep measurements. Ten sampled ACB games omit intervening games, so their date gaps cannot be used as actual rest periods.
- **Coaching decisions respond to the game:** [The timeout study](https://arxiv.org/abs/2011.11691) explicitly tackles selection and regression-to-the-mean problems. The [soccer formation-change study](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.914915/full) finds coach-specific usage patterns. Neither licenses a simple before/after coaching-effect claim from these small public samples.
- **Injury information is a separate, incomplete information stream:** [The NBA ACL case-control study](https://pubmed.ncbi.nlm.nih.gov/24427434/) illustrates why comparison with aging/role-matched controls matters when interpreting performance changes. It does not provide a usable current injury feed or justify diagnosis from tracking. No injury-status predictor is approved in the present data contract.

Additional exact queries executed for these gaps included: `soccer shooting biomechanics ball spin foot orientation goalkeeper pressure goal scoring original study`; `basketball shooting biomechanics release angle spin skill expert novice fatigue original study`; `soccer weather temperature shot accuracy expected goals original study home advantage no crowd natural experiment`; `basketball shot accuracy sleep travel altitude schedule congestion original research`; `soccer instep kick accuracy speed tradeoff biomechanics experiment pubmed supporting foot trunk 2013`; `soccer shot accuracy fatigue experiment skilled players kicking mechanics primary study`; `soccer temperature humidity technical performance professional match study shooting accuracy`; `basketball injury return shot shooting performance NBA anterior cruciate ligament study`; `soccer finishing skill repeatability expected goals player random effects Bayesian paper`; `basketball coach timeout effect shot quality scoring run study causal`; `soccer coach formation tactical flexibility performance substitutions tracking observational paper`; and `basketball shot selection opponent lineup spacing synergies expected points player skill regularized paper`. Some database/publisher pages returned browser challenges; accessible author manuscripts, indexed abstracts or publisher pages were used instead, with no access-control bypass. Abstract-only evidence is identified by its limited methodological detail.

## 5. Audited soccer sources and data contracts

### 5.1 StatsBomb/Hudl Open Data: preferred scalable shot-context source, conditional on permitted use

**Origin/version:** [official repository](https://github.com/hudl/open-data), formerly `statsbomb/open-data`; pinned commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` (7 September 2026). Inspected official Events v4.0.0, Open Data Specification v1.1, Matches v3.0.0 and 360 Frames v1.0.0 documents, plus actual match/event/frame JSON bytes.

**License gate:** the actual [Public Data User Agreement](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/LICENSE.pdf) is a custom research/noncommercial agreement, not CC-BY. It includes attribution/logo and redistribution restrictions. Keep raw data and row-level derivatives out of a redistributed repository; publish permitted credited analysis and source-loading code only after confirming the intended use. Do not assume trained weights or commercial services have separate permission. No registration, personal-data submission or outreach was performed. This is an operational rights check, not legal advice.

**Exact download patterns:**

- `https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/competitions.json`
- `.../data/matches/{competition_id}/{season_id}.json`
- `.../data/events/{match_id}.json`
- `.../data/three-sixty/{match_id}.json`

The ellipsis means the identical pinned base above, not a different API. These are ordinary unauthenticated downloads. Store URL, commit, size and SHA-256 in the acquisition manifest.

**Measured fields and units:** event UUID/index, period and event timestamp, match date, actor/team, shot location, body part, technique, shot type and play pattern; shot freeze-frame player locations/IDs/teammate flags. The standard grid is **120 × 80 native units**, attacking toward `(120,40)` with goalposts `(120,36)` and `(120,44)`. It is not a measured metre coordinate system. Distances and goal angles are standardized-pitch features unless true pitch dimensions are independently supplied. Do not silently impose a “one metre” pressure radius on the native grid. Retain period with time: stoppage time and extra time make naive clock concatenation unsafe.

**Snapshot meaning:** `shot.freeze_frame` is recorded context at the shot, with relevant players; it is not a guarantee that all 22 players are present. `three-sixty` joins on `event_uuid` and adds `visible_area`, actor/teammate/keeper flags and visible locations. It does not supply continuous trajectories or all player identities. Missing players must not imply empty space. With exact coordinates and a genuine subset, nearest-visible distance would bound the full-set minimum from above and visible counts would bound full-set counts from below. Here, annotation selection, missing identities and coordinate errors mean these are **not strict physical bounds**: label them nearest recorded opponent and recorded shooting-cone occupancy, not complete-defense geometry. Even a recorded keeper requires team/role sanity checks. Some frames/actors/polygons are absent. Offline annotation time is not a verified live-feed service guarantee.

**Observed coverage at the pinned version:** 3,961 listed matches; 426 matching 360 files, with one AFCON file essentially empty. Coverage is highly selected, not “every match in each named competition.” Examples from the complete match-index audit:

| Cohort | Matches | 360 files | Event bytes, approximately | Important limitation |
|---|---:|---:|---:|---|
| EPL 2015/16 | 380 | 0 | 1.13 GB | Historical season |
| La Liga 2015/16 | 380 | 0 | 1.12 GB | Other La Liga seasons are often selected-player games |
| Serie A 2015/16 | 380 | 0 | 1.16 GB | Historical season |
| Ligue 1 2015/16 | 377 | 0 | 1.16 GB | Three fewer than a full 380-match season |
| Bundesliga 2023/24 | 34 | 34 | 119 MB | Selected-team season, not the full league |
| Men's World Cup 2018 | 64 | 0 | 192 MB | National-team tournament domain |
| Men's World Cup 2022 | 64 | 64 | 200 MB | Additional 460 MB of 360 data |
| Men's Euro 2020 | 51 | 51 | 163 MB | Actually played in 2021; 378 MB additional 360 |
| Men's Euro 2024 | 51 | 51 | 160 MB | 399 MB additional 360 |
| Women's World Cup 2023 | 64 | 64 | 198 MB | 423 MB additional 360 |
| WSL 2018/19, 2019/20, 2020/21, 2023/24 | 107, 87, 131, 132 | 0 | 1.37 GB total | Uneven coverage, interrupted season and a multi-year gap |

The reproducible coverage report includes every competition-season, actual dates, metadata versions and byte counts. A nonrandom first/middle/last sample of 42 matches from 14 cohorts contained 1,039 shots, 127 goals, 46 penalties and 27 shootout shots; 40 shots lacked freeze frames/opposing keepers. Fifteen sampled 360 files supplied frames for 354 sampled shots. These are **source-QA counts**, not representative missingness estimates for all data and not model evaluation.

**Target and prohibited fields:** ordinary valid non-penalty shots, goal=1 and every other shot outcome=0; exclude shootouts (`period=5`) and keep penalties as a separate descriptive cohort. Do not select only on-target shots. Exclude `shot.outcome`, `end_location`, save/block results, goal-assist flags, future rebounds and future events from predictors. `shot.statsbomb_xg` is an optional external benchmark only, never an input; its training population and timing are unknown, so it is not a fair independently trained competitor by default. `under_pressure` is a provider annotation that can depend on event-duration overlap; treat it as annotated-context sensitivity rather than proof of strictly instantaneous measurement.

### 5.2 Wyscout/Pappalardo event data: clear open license, weaker defensive measurement

[Official Figshare collection v5](https://figshare.com/collections/Soccer_match_event_dataset/4415000/5), DOI `10.6084/m9.figshare.c.4415000.v5`, with the [Scientific Data paper](https://www.nature.com/articles/s41597-019-0247-7). The inspected Events and Matches records explicitly use **CC BY 4.0**.

- Events archive: `https://ndownloader.figshare.com/files/14464685`, 77,323,413 bytes; SHA-256 `877e015b716ffdeea18f04418e3f24fed307ed03c37ff305cabe1f47c4822a45`
- Matches archive: `https://ndownloader.figshare.com/files/14464622`, 645,097 bytes; SHA-256 `c8f92bb7533e5c127e043cee764c991b5c25b4f5e70a65be931baae0b1765ce9`

Actual match files contain 1,941 matches: England/France/Italy/Spain 380 each, Germany 306, Euro 2016 51 and World Cup 2018 64. Events expand to about 956 MB. Inspected records contain event/subevent IDs/names, player/team/match IDs, period, `eventSec`, tags, and start/end `positions` on a 0–100 percentage grid. End coordinates and goal/accuracy tags can be post-outcome. The dataset supports distance/angle/body-part/event-sequence models but does not measure all defenders, goalkeeper geometry or body orientation. This is the preferred event-only fallback when StatsBomb's intended-use terms do not fit; it is not a substitute for actual defensive tracking. Coordinate attacking-direction handling must be checked against the provider specification in the implementation adapter before deriving physical angles.

### 5.3 SkillCorner soccer tracking and pose: strongest directly licensed mechanics demonstration

[Official soccer repository](https://github.com/SkillCorner/opendata), pinned commit `4340d274572876239c154c90bc507a9b3250a656` (14 September 2026), **MIT**. Although its opening README paragraph says ten games, actual `matches.json` and file tree contain **20 A-League 2024/25 matches**. Tracking is 10 Hz in metres, origin at pitch centre, long-axis x; match files contain actual pitch dimensions. Broadcast-estimated positions include `is_detected` and projected visible-image corners. Off-camera extrapolation and player-identity errors are explicitly acknowledged. Full-season physical aggregates are future information for earlier games and are not usable as as-of ability or fatigue inputs.

Actual dynamic-event sample `data/matches/1925299/1925299_dynamic_events.csv` contains 5,222 rows across passing options, player possessions, on-ball engagements and off-ball runs. It supplies start/end frames, direction, locations, contextual pressure categories and many model-derived EPV/difficulty fields. Numerous columns encode future outcomes (`lead_to_goal`, end state, next phase, received/targeted, maxima and deltas). Those are labels or retrospective summaries, not action-start features. `fully_extrapolated` and event-matching flags require inspection. There is no basis for treating provider EPV scores as ground-truth scoring probabilities.

**Pose version/license:** [official Hugging Face release](https://huggingface.co/datasets/SkillCorner/opendata-bodypose), revision `a62e1ec1e3b82952042a7f7fa9dafd77c0e0822a`, explicitly MIT matching the repository. Two matches: Brisbane Roar–Perth Glory, 21 December 2024 (1925299), and Sydney FC–Adelaide United, 1 February 2025 (1996435). These are professional matches but only two independent games.

- Pinned full file: `https://huggingface.co/datasets/SkillCorner/opendata-bodypose/resolve/a62e1ec1e3b82952042a7f7fa9dafd77c0e0822a/raw/1925299.jsonl.zip`
- Inspected download: 623,408,231 bytes; SHA-256 `0415665098d594fb5681815000f7a6312037788a3237910a9f41bb8de5c336a0`, exactly matching the official manifest
- Other match manifest: 644,327,811 bytes; SHA-256 `64bcab2be9776172d062521d9a97e0e6f391fc9cacb331f9e42a6fe88cf8434b` (manifest verified; full second file not downloaded in this audit)
- Committed sample: `data/bodypose/sample_1925299_phase406.jsonl.gz`, 309 frames spanning 12.32 seconds; actual inspected timestamps 01:17:34.48–01:17:46.80

Each player can have 29 named joint `xyz` positions in metres and `p90_mae_cm`, a provider-predicted joint-position error radius in centimetres. Body pose is **25 Hz**, while tracking/dynamic events are **10 Hz**: `pose_frame = 2.5 × tracking_frame`. Use exact common frames or a documented past-only alignment; never join identical frame numbers. Player z is meaningful relative to that player's centroid, not necessarily ground-calibrated height. Joint and XY pipelines are independent and can be slightly misaligned. Pose/face points do not measure eye gaze, intent, muscle activation, force or ball spin.

**Independent full-file audit:** 153,252 frames; 106,757 frames with any pose; 4,902,560 player records; 1,540,715 player-records with joints; 44,680,735 joint observations. Every resolved pose has 29 joints. Two pose-bearing records have `is_detected=false`, consistent with the documented independent-pipeline caveat. Forty-seven frames have no period. The record denominator includes roster entries and must not be treated as exactly 22 active players per frame. At the most recent pose frame no later than each annotated shot-ending possession, **29 of 30 candidate endpoints have the shooter's pose**. This does not independently prove that the event endpoint equals true ball contact.

**Feasible mechanics output:** a provider-estimated skeleton and derived time-series demonstration of knee/elbow segment angles, shoulder/hip axes and approach motion, with source uncertainty and missing frames displayed. Three-point joint angles are translation invariant, so a common vertical offset cancels; this does not resolve joint-local errors. Shoulder-axis bearing has front/back ambiguity unless independently disambiguated. Near-degenerate projected vectors should be marked undefined. Require segment lengths comfortably larger than their reported endpoint errors; display those errors rather than claiming a calibrated angle confidence interval. Do not prescribe an “optimal” pose or estimate a causal scoring benefit from two matches. Contact-level validation and outcome linkage are still prerequisites for a shooting-mechanics prediction model.

### 5.4 IDSSE/DFL: well-licensed synchronization and geometry testbed

[Primary dataset paper](https://www.nature.com/articles/s41597-025-04505-y), [official processing repository](https://github.com/spoho-datascience/idsse-data), [Figshare v1](https://doi.org/10.6084/m9.figshare.28196177), **CC BY 4.0** with DFL-authorized release. Seven 2022/23 matches (two Bundesliga, five second division), 25 Hz tracking, events and metadata. The paper reports 171 shots/19 goals, 1,002,644 frames and 207 players. Seven position XMLs total approximately 2.62 GB.

Exact example file URLs from the record API: metadata `https://ndownloader.figshare.com/files/51643475` (11,930 bytes), events `https://ndownloader.figshare.com/files/51643493` (776,578 bytes), positions `https://ndownloader.figshare.com/files/51643514` (418,524,833 bytes). Metadata and file lists were inspected; this audit did not parse the full XML position corpus. Units include metres for position, km/h for speed and m/s² for acceleration. Raw event/tracking timestamps need alignment: the authors report meaningful offsets, including large outliers. A million frames do not create a million independent matches. Use it to test synchronization and geometry methods, not to fit a high-dimensional scoring model on 171 shots.

### 5.5 Alternatives that do not resolve the primary problem

- [Metrica sample data](https://github.com/metrica-sports/sample-data): valuable synchronized teaching examples, three anonymous games and normalized coordinates. The inspected repository requested credit but did not establish a full formal data-license grant; do not assume downstream code licenses resolve this.
- [PFF's World Cup release announcement](https://www.blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data): potentially rich professional tracking/events, but access requires a request form and the exact supplied rights/schema were not verified. No personal information was submitted.
- [SoccerTrack v2](https://arxiv.org/abs/2508.01802): a promising recent full-pitch vision/event research release, but its university population and exact implementation license/versions need a separate audit before selection.
- SoccerNet/vision clips are useful for detector evaluation, not automatically complete scoring-opportunity cohorts. A public video or a skeleton-estimation repository does not establish permission to redistribute the underlying match broadcast.

## 6. Audited basketball sources and data contracts

### 6.1 SkillCorner ACB: preferred public professional tactical source

[Official repository](https://github.com/SkillCorner/opendata-basketball), pinned commit `4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66` (10 September 2026), **MIT** with SkillCorner attribution/license retention. Ten Liga ACB 2025/26 matches from 11 October 2025 to 29 May 2026; processing/publication occurred later, so this is a historical analysis release, not evidence that the features were delivered live during those games.

**Exact routes:**

- Events: `https://raw.githubusercontent.com/SkillCorner/opendata-basketball/4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66/data/matches/{id}/{id}_dynamic_events.json`
- Metadata: same base and directory, `{id}_game_data.json`
- Actual tracking bytes: `https://media.githubusercontent.com/media/SkillCorner/opendata-basketball/4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66/data/matches/{id}/{id}_tracking_data.jsonl.gz`

The ordinary raw tracking URL returns a Git LFS pointer, not tracking JSON; use the verified media route. All ten event/metadata files and all ten tracking archives were downloaded and inspected. Tracking gzip total is about 361 MB; process JSONL in a stream rather than constructing millions of nested Python objects.

**Schema/timing:** shots have `id`, `gameId`, `period`, `chanceId`, `possessionId`, `startFrame`, `startWallClock`, `startGameClock`, `location`, `region`, `shotClock`, `shooterId`, team IDs, `three`, `distance`, `closestDefDist`, `closestDefId`, prior-touch/dribble fields and outcome annotations. Raw frames use `frameIdx`, player `xyz`, `speed`, `predError`, `isDetected`, ball and clocks. Frame rate is **25 Hz**; wall-clock fields are **milliseconds from the video origin** (`frame × 40` in inspected records), while game and shot clocks are **seconds remaining**. Wall time is not elapsed live playing time. Overtime appears as period 5.

**Coordinate audit:** event locations are offense-normalized toward the negative-x hoop, centred court, in feet; source convention puts the offensive hoop at **(-40.75,0)**. This was verified numerically against reported shot distance, not borrowed from NBA court diagrams. Raw tracking can require a 180° rotation by offense/team/period despite documentation suggesting a common orientation. Estimate/verify one transformation per team-period from multiple geometry observations, never independently flip each player or use shot outcome. Player z is always zero in the inspected ACB tracking: it cannot measure jumping, joints or arm position. Ball z is an estimated height and occasionally has calibration noise. `predError` is a provider-predicted error radius in feet, not independent ground truth; detected and extrapolated positions have markedly different error profiles.

**Actual sample counts:** 1,459 recorded releases, 606 makes; 535 threes and 924 twos. Twenty-six releases lack location/distance/nearest-defender geometry; 1,433 have it. There are 143 fouled releases: 32 makes and 111 misses. The conventional FGA cohort therefore has 1,348 releases if only fouled misses are omitted. The provider documentation's suggestion to omit all fouled shots would wrongly discard and-ones. Most importantly, that conventional cohort is defined using post-release outcomes: it is not an eligibility rule known before release. Primary make modeling should use all recorded releases with an explicit measurement-availability subset, including fouled misses.

The events also include 2,055 chances, 1,564 possessions, 768 rebounds, 248 turnovers, 430 free throws, 443 fouls, 4,786 passes, 6,662 touches, 13,962 dribbles, 1,520 picks, 1,103 off-ball screens and other action tables. This enables future sequence work but does not make every derived field valid before a decision.

**Leakage exclusions:** do not use `outcome`, end frame/clocks, `assisted`, `assistOpp`, `blocked`, `blockerId`, `fouled`, `foulId`, `contestLevel`, `contested`, full-season aggregates or provider `shotQuality` as at-release predictors. `contestLevel` can encode a block; `assistOpp` combines a prior-pass notion with assisted status; `shotQuality` is an undocumented proprietary score, not a verified probability or independent benchmark. The `passerId`/action-classification fields need their own availability audit before use. `releaseTime` can include long wall-time gaps; it is not automatically live touch duration.

**Source quirks:** full-season aggregates cover 293 of 327 games and include player/team/total rows and aliases; joining them to earlier shots leaks the future. Some pass receiver IDs identify an interceptor rather than intended receiver; self-pass and assist-label inconsistencies occur. Rebound/chance/technical-free-throw bookkeeping needs independent team/score reconciliation before defining possession reward. A chance's supplied points cannot be assumed to belong to the shooting team without checking linked free throws.

### 6.2 Release-level tracking audit and predeclared quality policy

All 1,459 release frame indices exist. Of these, 1,458 have ten players, ball and shooter. There are 1,433 releases with named defender and event geometry; 1,259 have both shooter and named defender directly detected. Across the full 1,472,932-frame files, 643,228 frames have no player records, mostly irrelevant to a shot-release subset. Reporting only that all-frame missingness would wrongly imply most releases lack tracking.

Among geometry-bearing releases:

- Named defender is the nearest raw-tracking opponent within 0.01 ft on **1,425 of 1,433** releases; eight differ
- Event shooter location and named-defender distance both agree with the aligned raw frame within **0.1 ft on 1,347** releases
- Both agree within **1 ft on 1,397** releases
- The stricter 0.1-ft agreement plus both directly detected holds for **1,179** releases
- Shooter exists at release and release-minus-1/-5/-25 frames for **1,430** releases; directly detected at all four for **1,270**

Median geometry discrepancy is zero in each game, but there are large outliers, especially heaves. The worst named-defender distance discrepancy exceeds 27 ft. The audit saves offending shot IDs and distances. Four sampled prior timestamps do not establish a complete valid velocity window.

**Quality rule, fixed before fitting:** treat 0.1 ft as a *same-frame representation-consistency tolerance*, deliberately well below the provider's roughly foot-scale detection uncertainty. It is not a claim of 0.1-ft physical accuracy. Retain a 1-ft tolerance and a directly-detected-only subset as predeclared sensitivities, not thresholds chosen by model score. If deriving release bearing or multiple-defender geometry from raw tracks, use the 1,347 consistent cases and rerun every baseline on those identical cases. The event-only context comparison can additionally retain all 1,433 geometry-bearing releases, clearly labeled as provider-annotated context. Never fill an unseen defender with an empty-space assumption or select quality filters by goal/make outcome.

Velocity extensions must require an uninterrupted prior window, valid identity, monotonic clocks, a documented past-only derivative/smoother and detection/extrapolation reporting. Provider offline smoothing may use future video even when its timestamp represents release; until its latency is documented, call this retrospective state estimation rather than a deployable real-time measurement. Nearest-defender geometry does not identify the assigned matchup, defender facing, hand height or ball launch angle.

### 6.3 Large NBA shot charts: useful scale, reduced context and upstream-rights caveats

[SportsDataverse/hoopR data repository](https://github.com/sportsdataverse/hoopR-nba-data) explicitly licenses its data/code/documentation under CC BY 4.0 (inspected commit `2a98782f7f3c543225fe93c0a48dc000c8cf3047`). Its ESPN-origin shot release is directly downloadable, unlike many broken historical NBA endpoints:

- `https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_shots/shots_2025.parquet` — 3,661,538 bytes, SHA-256 `104aec09798ea58569c45d1183ecb930fbde26b35a67fd8bb64ac5166b3c02d6`
- Same release, `shots_2025.csv` — approximately 35 MB; actual CSV bytes parsed because this environment lacked a Parquet engine

The inspected file has **292,933 rows, 1,324 games and 566 shooters**. It includes free throws and four “No Shot” rows, so the filename is not a ready-made FGA cohort. Twenty columns contain game/season/period/clock, shooter/secondary athlete, shot type, outcome/score and raw/transformed coordinates. It has no defender distances, body joints or complete trajectories, and no actual game-date column in this file. `score_value=0` on a miss does not identify whether that attempt was worth two or three; a separate validated attempt-value source is necessary. Secondary athlete identity can depend on assist/block outcome. Dates must be joined from audited game metadata for chronological validation. Coordinate transformation and basket switching require source-code/specification verification before deriving distances.

The publisher's open license is meaningful but does not independently settle upstream ESPN/NBA rights for every redistribution or commercial use. NBA-origin releases have restrictive reuse terms; third-party licenses do not by themselves resolve upstream data rights. [NBA terms](https://www.nba.com/termsofuse). This source is a possible large **event-only** baseline after rights and schema validation, not evidence that modern NBA defender mechanics are publicly available.

Historical SportVU mirrors, `nba_api`, EPV demo repositories and shot-log copies were also examined. A code MIT/Apache license alone does not establish rights in copied NBA tracking. No verified official broad data grant was found for the common 2015/16 mirrors in this pass, so they were not adopted. Old NBA 2015/16 tracking, modern ACB 2025/26 tracking and a 2006–2015 game-result baseline are different populations and tasks.

### 6.4 SPL basketball free throws: bounded research eligibility clarified

[Official MLSE Sport Performance Lab repository](https://github.com/Sport-Performance-Lab/SPL-Open-Data), commit `a3f9cffbde917b1e1747cedd6ec25dfab18c6051` (20 March 2026). Documentation describes a small **non-professional** free-throw dataset with multiple acquisition versions. This public research summary omits participant/session-linked counts, collection dates and quality cells. The versions differ in sampling rate and available joints; those are schema-transport issues rather than individual performance findings.

**Material rights restriction:** the [actual LICENSE](https://github.com/Sport-Performance-Lab/SPL-Open-Data/blob/a3f9cffbde917b1e1747cedd6ec25dfab18c6051/LICENSE) adds an exclusion for people associated with professional sports organizations or financial-analysis firms beyond its CC BY-NC-SA 4.0 heading. The independent, unaffiliated, noncommercial research scope has now been clarified, permitting a bounded sample/schema audit under the full terms. Raw observations remain local; no fitting or commercial use is cleared by that clarification. Detailed participant/session-linked audit records remain local and are not part of the public research package.

Schema documentation places body/ball xyz in **feet**, hoop-plane depth/lateral coordinates in **inches**, and entry angle in **degrees**. Ball tracking extends only a few frames after release and can be noisy at capture-volume boundaries. Entry angle/depth are post-release outcomes, not features for a pre-release make prediction. The documentation does not yet establish an independently verified release-frame label or error calibration. Actual sample-byte QA now covers 18 trials. Both versions expose 69 keys, but the older sample has only 27 finite markers and 42 structurally absent ones. Older ball coordinates also contain nonstandard NaN tokens. No release frame or per-joint error field is supplied. Ages and individual guardian-consent details are unavailable, so outputs must remain aggregate/deidentified and conservatively treat the data as potentially involving minors. Any later modeling requires separate review, validated release alignment and grouped chronological evaluation. With five people and two sessions, these cannot establish elite-game generalization or an individualized causal coaching prescription. Cross-session analysis must account for 30/60 Hz and changed joint models. A random frame or random-trial split would overstate independence.

### 6.5 Other basketball alternatives

[Supola's published supplements](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0281467) offer CC-BY selected movement attributes; an actual cut-attribute CSV was downloaded and inspected. They are useful for a focused geometric-method demonstration, not a complete NBA season. [TrackID3x3](https://github.com/open-starlab/TrackID3x3) has an explicitly open dataset but a 3×3 vision/identity task, not professional five-on-five shot outcomes. [DeepSport](https://ispgroup.gitlab.io/code/deepsport/) is a limited visual/pose benchmark with noncommercial terms. [BARD](https://github.com/GabrieleGiudic/BARD) provides action clips/labels, but those clips contain post-outcome video and do not by themselves supply calibrated pre-release court mechanics. Synthetic dot-player datasets were excluded from the real-measurement recommendation.

### 6.6 Role-specific mechanics beyond shooting

**Goalkeepers:** [Savelsbergh et al. (2002)](https://www.tandfonline.com/doi/abs/10.1080/026404102317284826) experimentally examined anticipation and eye movements using filmed penalties and joystick responses; [Dicks et al. (2010)](https://www.sciencedirect.com/science/article/pii/S0167945710000266) related real interception behavior to individual action capabilities. These distinguish reading advance cues from physically reaching the ball. [Ibrahim et al. (2019)](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2019.00015/full) measured stance, knee angle and diving performance under controlled conditions; its individual data are explicitly not public. Our soccer pose can describe selected stance/segment geometry but cannot measure gaze or push-off force. A separate save model would need shot trajectory, contact synchronization, keeper movement and a clearly on-target-conditioned target; a parry/rebound-control study needs the subsequent possession sequence. Those post-contact observations cannot become pre-contact xG inputs. Penalty experiments do not establish open-play goalkeeper performance.

**Rebounding and box-outs:** [Maheswaran et al.'s optical-tracking study](https://www.sloansportsconference.com/research-papers/deconstructing-the-rebound-with-optical-tracking-data) separates rebounding location/movement from the final credited rebound. [Ishibashi et al. (2013)](https://www.jstage.jst.go.jp/article/sposun/23/1/23_1_45/_article/-char/en) used eye tracking in seven experienced players during three-on-three box-out situations. This is evidence that perception and positioning deserve their own measurement, not that XY proximity proves physical contact. ACB data can support a limited release-state rebound-probability branch and crash-versus-retreat description; it cannot observe hand reach, contact force, gaze or player jump height. Conditioning the analysis on an eventual miss changes the population and must be stated.

**Ball handling and passing:** [Park and Jeong (2023)](https://www.mdpi.com/1660-4601/20/10/5788) studied arm/finger coordination and dribble consistency in a small static-dribbling experiment. [Li et al. (2021)](https://www.mdpi.com/1660-4601/18/2/700) measured push-pass kinematics and accuracy under a fatigue protocol without defenders. These are bounded skill experiments, not elite-game turnover models. ACB dribble/pass events and ball/player trajectories can describe rhythm, movement and lane geometry; they do not reveal wrist mechanics, finger force or a pass's intended receiver when the recorded receiver is an interceptor. SPL's free-throw source does not fill those passing/dribbling measurement gaps.

These role-specific searches used `soccer goalkeeper diving save biomechanics anticipation visual information penalty kicks original study open access`, `basketball rebounding box out tracking Deconstructing Rebound Sloan 2012 primary paper`, `basketball passing chest pass biomechanics kinematics accuracy original study`, and `basketball dribbling biomechanics hand ball coordination visual control expert novice study`. The resulting eight additional inventory rows are measurement/prioritization guidance, not new implementation promises.

## 7. Recommended bounded studies and validation protocol

This is a candidate research contract, **pending parent/reviewer approval before implementation**. It was chosen from measurement quality, population continuity and data rights, not from model scores. No tactical estimator or hyperparameter search has been run. Aggregate outcomes were inspected for source QA, including some future-test games; this is not a claim of completely human-blind or prospective validation.

### 7.1 Soccer study: chronological WSL shot-context ablation

**Question:** among recorded non-penalty WSL shots, does recorded goalkeeper/defender context improve probability prediction beyond standardized shot geometry and action context?

**Population:** StatsBomb competition 37, seasons 4 (2018/19), 42 (2019/20), 90 (2020/21), 281 (2023/24). This is professional women's English league football, not an NBA-like generic sports task or a claim about men's international football. The source contains 457 matches in these cohorts. Its selection/completeness and the two missing intervening seasons must be disclosed.

**Chronological split, specified from metadata:**

1. Development/training: 325 matches across 2018/19, 2019/20 and 2020/21
2. Calibration: 60 matches dated 1 October–31 December 2023
3. Final test: 72 matches dated 1 January–18 May 2024

For model selection, use expanding-season development folds (2018/19 → 2019/20; 2018/19+2019/20 → 2020/21). Any additional date blocks must keep a whole match and all its shots in one block. Keep the 2023 calibration and 2024 test sets out of feature selection and hyperparameter selection. Fix that the multi-year gap is a transport challenge, not conceal it. If a different population is desired, use a separate prespecified protocol rather than choosing the most flattering held-out result.

**Target:** goal on the recorded shot, including blocked/off-target/saved misses. Penalties and shootouts excluded; own goals are not automatically converted into ordinary Shot labels. Verify shootout/extra-time encodings. Reject impossible/missing location values with explicit counts; do not use outcome to decide data eligibility. For rich context, require documented necessary player observations or represent uncertainty explicitly. A missing keeper must not be placed on the goal line by assumption.

**Models and baselines:**

- Training-only smoothed constant goal rate
- Training-only distance/angle/body-part bins with pooled/shrunk rates and an explicit unseen-bin fallback
- Regularized logistic or spline/GAM-style geometry model: standardized distance, goal angular width, lateral position, broad body part, nonpenalty restart/play-pattern category; add first-time/technique only as a documented action-context block
- Matched-case richer model adding recorded keeper depth/lateral offset, nearest recorded opponent distance and shooting-cone occupancy. Keep feature count modest and regularize
- A small depth-limited boosted-tree sensitivity is reasonable only after the linear/spline baselines; use a short prespecified development grid, not extensive leaderboard search
- Optional StatsBomb xG benchmark, separately caveated for unknown training provenance

Report (a) full eligible event-baseline coverage, (b) common-case geometry versus defensive-context performance, and (c) the distribution of excluded/missing observations. This prevents apparent improvement from comparing an easier rich-data subset with a harder all-shot baseline. Identity/ability effects are a later, separately validated extension with as-of historical counts, partial pooling and cold-start handling.

**Calibration:** choose the calibration family using development only. Fit a simple intercept/slope logistic recalibration on the 60-game calibration block, with sensible shrinkage and numerical clipping fixed beforehand. Retain uncalibrated scores for comparison. Isotonic calibration is not automatically better and should not be selected on the final test. Report calibration intercept/slope, reliability plot, outcome rate and mean prediction, plus proper scores. Do not claim deployment calibration for 2026 or another competition.

**Primary evaluation:** held-out log loss and Brier score; paired differences on identical shots. Also show AUROC as a discrimination summary, reliability by broad shot type/range, coverage, and sample/goals/games per slice. Do not optimize accuracy/F1 for an imbalanced probability task. Use paired match-cluster bootstrap intervals where the number of independent matches supports them; also report equal-game-weighted sensitivity so a few high-shot games do not dominate. Multiple slices are descriptive, not a fishing exercise for significant findings.

**360 extension:** a separate men's tournament experiment can train on Euro 2020/World Cup 2022 and test Euro 2024, with calibration held chronologically within the pre-2024 data. It answers a different population/visibility question and must not be pooled into the WSL model without an explicit transport design. A 360 polygon supports visibility-aware features, not an assumption of complete defense. Full-season male 2015/16 event-only cohorts are another viable, older alternative; selected Bundesliga or Messi-season slices should not be advertised as full-league samples.

### 7.2 Basketball study: expanding-game ACB release-context demonstration

**Question:** in these ten published professional ACB games, how do geometry and measured nearest-defender context relate to make probability at an annotated shot release, and is there any stable out-of-game predictive improvement?

**Target:** make=1, miss=0 among all recorded field-goal releases, including fouled misses. Free throws are a separate event family. `2/3 × P(make)` may be shown only as expected immediate field-goal points conditional on taking the shot; free throws, offensive rebounds, turnovers and future possession value are omitted. Conventional FGA is a secondary retrospective cohort, never a pre-release-known filter.

**Chronological protocol:** use the first five games (114243, 114234, 114169, 114099, 114086) for initial development. Freeze a very small model family/feature contract there. Predict game 6 (178442), then expand training only with the now-past game and predict games 7–10 in order (179612, 184439, 188630, 191313). Record all five forward predictions before inspecting their aggregate performance. Do not use random shots or possessions across train/test; players and repeated possessions in one game are dependent. Repeated Zaragoza/Breogán games and unseen teams/players in later games are part of the generalization challenge, not independent repeated laboratory trials.

**Baselines:** a training-only Beta-smoothed make rate; shrunk two/three-point plus broad distance-zone rates; a compact regularized logistic/spline geometry model; the same model plus nearest-defender distance and a limited predeclared interaction with shot distance/point value. First-time player identities should fall back to pooled behavior; do not fit unregularized shooter/defender interactions. A complex neural network or large hyperparameter search is unjustified by ten games.

**Frozen model and refit schedule:** use four prespecified candidates: (A) a Beta(1,1)-smoothed global make rate; (B) rates by `three` and distance bands `[0,6), [6,14), [14,22), [22,infinity)` feet, shrunk toward the past-training global rate with fixed prior concentration 20; (C) L2 logistic regression with `C=1`, intercept, `log1p(distance)`, `three`, absolute court-location bearing and shot clock; (D) the same logistic model plus `log1p(closestDefDist)` and its interaction with `three`. Absolute bearing is `abs(atan2(y, x + 40.75))` radians for the source's offense-normalized coordinates, retaining valid behind-hoop cases; it is not a body/launch angle. Use no shooter IDs, outcome annotations, balancing/resampling, flexible tree search or extra feature discovery in the outer evaluation. Missing shot clock receives the current training median plus a missingness indicator, clearly labeled as model imputation rather than observed clock; missing geometry uses a separately reported pooled fallback, not invented coordinates.

For each outer game, rebuild the eligible training table from all **strictly earlier** games, recompute training-only medians/scales, fit the same fixed candidates, and write/hash that game's predictions and preprocessing provenance before attaching its labels for scoring. Then admit that game's labels to the next game's training history. Geometry-quality rules, distance cutpoints, transforms, model families, regularization and feature list remain frozen throughout; coefficient/scale refitting is allowed, redesign is not. Do not inspect outer-game scores until all five prediction files are recorded. If a genuine parser bug forces a change, retain the original run, document the correction and label the rerun exploratory rather than silently resetting the test. Later source outcomes were already inspected in aggregate QA, so this is a frozen automated forward evaluation, not a human-blind claim.

**Measurement tiers:**

- Provider-annotated event context: up to 1,433 geometry-bearing releases, comparing identical rows across models
- Raw-derived multi-player/bearing extension: the predeclared 0.1-ft consistent subset, up to 1,347 releases, with matched baseline; 1-ft and directly-detected-only sensitivities reported separately
- Missing geometry: report 26 releases separately and a pooled-prior fallback if an all-release scoring interface is needed; never fabricate defender positions

The cohort mask must be based only on input validity/measurement quality. Include a coverage diagram by game, shot type and range so excluded heaves or difficult camera views are visible. Do not call 0.1 ft a physical error bound.

**Calibration and uncertainty:** main outputs should be probabilities with explicit calibration diagnostics, not a guarantee of calibration. Given the tiny independent sample, use the fixed uncalibrated regularized model as primary. Do not fit a separate recalibrator in this ten-game candidate study. In particular, avoid a one-game calibration split or flexible isotonic fits; report held-out reliability as a diagnostic, not a calibrated-model claim. Show log loss, Brier, coarse reliability, count of games/shots/makes and game-by-game differences. With only five forward-test games, bootstrap intervals are fragile and no reliable league-wide superiority/significance claim is justified. Report sensitivity to leaving out each test game and do not rank individual players from this sample.

**Scope:** this is a tactical measurement and modeling demonstration, not a validated modern NBA forecasting system. A historical NBA results baseline remains a separately labeled artifact. More contemporary ACB games or separately licensed NBA tracking would be needed for broader claims.

### 7.3 Soccer mechanics demonstration: provider-estimated pose, no outcome-effect claim

Use the already audited 1925299 full-match pose plus its official event/metadata files, and the second match only if needed for replication. Pick an action by an input-only rule or identify it as an illustrative selected clip. Show the provider-estimated joints for detected players, coordinate axes, past-only time window, per-joint source error, missing frames, and matching shot/possession endpoint uncertainty. A skeleton animation should distinguish detected pose from extrapolated XY and should never interpolate a missing joint invisibly.

Suitable numerical outputs: knee and elbow segment angles; shoulder/hip axis bearings; relative trunk tilt; descriptive within-action changes. Label a shoulder axis modulo 180° unless facing is defensibly disambiguated. Do not infer eye gaze, muscle force, injury, ball spin or true ground-referenced jump height. Independent contact-timing validation is mandatory before labeling a frame “at impact” or fitting any mechanics-to-outcome model. For model evaluation later, split by game/player/action, not individual adjacent frames; two games do not support a general scoring-effect model.

### 7.4 Decision value and causal questions remain separate

A shots-only sample is selected by the players' actual decisions. Better predicted make probability at a nearby location does not show that moving there is feasible or beneficial. A shot-choice model needs states in which no shot was taken, action probabilities, pass/drive turnover risk, foul rewards, rebound continuation and an explicit reward horizon. Opponents adapt to changed tactics. Observational counterfactual simulations remain assumption-dependent even if a paper uses causal terminology. The current implementation should expose association, measurement and predictive uncertainty; it should not prescribe optimal player movements or claim an intervention would increase points.

## 8. Practical scale, implementation checks and handoff

### Compute and storage

- WSL selected event files: about 1.37 GB raw JSON. Parse match-by-match into a compact shot table; ordinary CPU logistic/spline models are sufficient. Do not load the entire repository's JSON into memory
- ACB: roughly 34 MB of dynamic-event JSON plus approximately 361 MB of gzip tracking. The complete audit streamed 1.47 million frames and retained only needed release/prior frames. A shot table is tiny; no GPU is needed
- Soccer pose: 623 MB compressed for the first match, about 3.3 GB JSON and 44.7 million joint observations. Stream and retain selected players/windows; a full nested-object DataFrame is wasteful. The two-match manifest is roughly 1.27 GB compressed
- Wyscout: 77 MB compressed, about 956 MB expanded event JSON. CPU event models are straightforward
- IDSSE: roughly 2.62 GB position XML. Incremental XML parsing is preferable
- SPL: repository tree has 583 trial JSONs totaling about 1.3 GB; the bounded 18-trial inspection downloaded about 41 MB, kept locally

These are source/audit sizes, not promises of measured training runtime. Network bandwidth and parser implementation determine wall time; the proposed tabular fits should not require expensive infrastructure.

### Required acceptance tests before reporting model results

1. Pin source commits/record versions; retain acquisition hashes, source URLs and license notices. Keep restricted raw data private/ignored
2. Validate unique match/event/shot IDs, linked-team identities, aliases and substitutions. Use IDs rather than team-name strings; separately check neutral venues and competition/gender/era labels
3. Unit-test coordinate orientation, hoop/goal coordinates, point-value boundaries and rotation invariance. Retain native/physical units in column names
4. Validate period/time ordering, halftime/OT resets, video-clock versus game-clock origins and event/tracking alignment; do not silently repair large offsets
5. Audit release coverage, visible area, keeper/defender availability, pose joints and detection/extrapolation separately. Missing space/players are unknown
6. Maintain a feature-availability table and denylist of post-outcome fields. Reconstruct scoreboard/history strictly from earlier events. Fit encoders, scaling, imputation/fallbacks and calibration on the proper past-only partition
7. Reconcile shot/free-throw/rebound/possession labels against team scores without using final scores as predictors. Disclose any unresolved source inconsistencies
8. Keep whole games and all overlapping windows/possessions together. Preserve source-QA versus model-development versus final-test provenance
9. Report proper scores, calibration, coverage, group counts and uncertainty; compare models on identical rows; show failed/unstable results rather than selecting attractive slices
10. Keep measurement demos, event-only prediction, tactical state prediction and causal/decision claims visibly distinct

### Deliverables available for integration

- `docs/research/SOCCER_BASKETBALL_RESEARCH.md`: this sourced brief
- `docs/research/SOCCER_BASKETBALL_FACTOR_INVENTORY.csv`: 94 factor rows with source links and measurement/availability limits
- `docs/research/SOCCER_BASKETBALL_FACTOR_SOURCES.json`: reusable primary-source key map
- `docs/research/TACTICAL_MEASUREMENT_CONTRACT.json`: machine-readable candidate target/split/measurement contract
- `docs/research/RESEARCH_PUBLICATION_POLICY.md`: source-specific release classification and required notices
- `scripts/research/`: original reproducible source-QA scripts; no model fitting
- `reports/research_statsbomb_coverage.json`: all pinned competition-season match counts, dates, versions and sizes
- `reports/research_statsbomb_sample_audit.json`: inspected nonrandom event/360 sample QA
- `reports/research_skillcorner_basketball_audit.json`: all ten ACB event/metadata audits
- `reports/research_skillcorner_all_tracking_audit.json`: all ten release-level tracking audits, geometry discrepancies and quality counts
- `reports/research_skillcorner_soccer_pose_audit.json`: independently streamed full-match pose coverage and candidate shot-end alignment
- `reports/research_hoopr_sample_audit.json`: actual 2025 ESPN-origin shot-chart schema/cohort counts
- `docs/research/SPL_BOUNDED_SCHEMA_ADDENDUM.md` and `reports/research_spl_sample_quality_aggregate.json`: deidentified lab schema/quality audit; no individual identifiers or ranks

Downloaded source documents, papers, manifests and raw data are kept under ignored `data/` paths. No core model code was edited and no tactical model was trained. Remaining gates are the intended-use/license decision for restricted sources, full-cohort soccer QA during the adapter build, actual contact alignment for pose, and any separate as-of external metadata needed for fatigue/weather/injury hypotheses. Those gaps do not prevent delivering the documented MIT-licensed measurement demonstrations and carefully bounded event-context studies.
