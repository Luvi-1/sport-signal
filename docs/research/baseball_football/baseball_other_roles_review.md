# Baseball catching, fielding and baserunning: bounded primary-evidence review

Reviewed 2026-10-11. This supplements `baseball_biomechanics_review.md`; it closes its explicit non-pitching/non-hitting coverage gap. It is a targeted narrative review, not an exhaustive or systematic review. Official measurement documentation establishes what a metric represents; it is not automatically evidence that changing a movement causes better professional performance. Small amateur experiments are identified separately from professional game observations.

No Statcast CSV, proprietary tracking, paid dataset or video collection was downloaded. Public documentation and research were read; the existing local Retrosheet schema was inspected. The unresolved Statcast reuse gate in `RIGHTS_AND_DATA.md` remains in force.

## 1. Main findings

- Catching is several tasks: receiving/framing, stopping loose pitches, preparing and delivering throws, retrieving bunted balls, directing teammates and applying tags. A catcher-level outcome cannot identify the glove path, joint motion or decision that produced it.
- Defensive measurement must separate where the defender began, the opportunity presented, movement toward the ball, acquisition, transfer, throw selection, throw execution and the receiving teammate. These require different timestamps and denominators.
- A stolen-base result belongs to a runner–pitcher–catcher–receiving-fielder interaction. Evaluating only successful attempts ignores deterrence, abandoned attempts and the decision not to run. Batted-ball advancement is a different task from stealing. [R04, R10, R12–R13]
- Public leaderboards provide substantially more role coverage than the standard event tables. They still do not provide a verified, reusable, complete historical player-trajectory dataset.
- Two particularly important implementation boundaries are the plate-crossing conditioning of catcher throwing and the catch-time conditioning of first-base receiving. Both support opportunity-adjusted evaluation; neither supplies information available before that same pitch. [R04, R08]
- Professional body-mechanics evidence remains much thinner here than professional pitching evidence in the companion review. This pass found useful professional catcher measurements, but not a validated universal MLB receiving, blocking, fielding or turning technique prescription. [R05, R07, R14–R15]

## 2. Prediction clock and availability vocabulary

**G** = pregame; **P** = before the pitch/pickoff action; **R** = pitch release or subsequent flight, explicitly distinguished; **C** = contact/early batted-ball flight; **A** = acquisition/throw/arrival during the play; **H** = completed-play or historical evaluation. A historical summary is permissible at G/P only when it contains observations available before the forecast cutoff. A full-season leaderboard downloaded later is not a valid earlier-season feature.

**E** = present in existing public event files, chiefly outcomes and state. **S** = documented Statcast Search event field, with reuse unresolved. **L/V** = public leaderboard/visualization; some surfaces offer play drilldowns, but a complete rights-cleared event export was not established. **T** = full tracking, pose, laboratory or annotated-video measurements not supplied by the audited event files. These classes describe access granularity, not a blanket license.

## 3. Compact factor inventory

| Role/task | Measure and clock | Availability | Confounding, interpretation and next use |
|---|---|---|---|
| Catcher receiving/framing | Glove target and reception coordinates, glove path/orientation, body stability; conditional initial called-strike probability; R/A/H | Calls and identities E/S; location S; framing L/V; complete glove motion T | Pitch location/type, pitcher, batter, count, umpire and era; taking a pitch is selected. Residual catcher effect is not measured glove technique. R01–R02 |
| Catcher setup | Knee status and stance at a declared event; transitions to block/throw; R/A | Stance L/V; joint trajectories T | Runner threat, pitch plan, count and catcher identity affect stance choice. Compare within player/context; pooled differences do not identify a treatment effect. R02 |
| Catcher blocking/recovery | Opportunity difficulty, prevention, ball deflection/retrieval and next-action time; R/A/H | WP/PB E; adjusted blocking L/V; body/glove/deflection traces T | Pitcher miss, pitch flight, handedness, catcher location and advance opportunity. A scorer's WP/PB distinction is not an isolated biomechanical diagnosis. R03 |
| Catcher transfer and throw | Reception-to-release, ball flight, throw location, total pop time and tag completion; A | CS/SB outcomes E; pop/arm/throwing L/V; full synchronized mechanics T | Pitch location, runner progress, pitcher delivery, pitchout, receiving fielder and accuracy. Do not equate hardest throw with quickest completed out. R04–R05 |
| Catcher/pitcher bunt defense and communication | Ball approach, who acquires it, decision latency, chosen base, verbal instruction, release; C/A | Chosen play/fielding sequence partly E; decisions and trajectories T | Team roles, runner speed and ball geometry; hindsight acquisition time must not become an early-decision input. R07 |
| All fielders: positioning | Starting depth/angle, orientation, readiness and assignment; P/R | Identity E/S; broad alignment S; aggregate location L/V; full setup T | Coach positioning, batter tendencies, pitch plan, park and rules. Starting location is distinct from lineup-position code. R06 |
| LF/CF/RF: range and route | Required versus traveled distance, opportunity difficulty, movement components and successful catch; R/C/A/H | Outcome E; OAA/catch/jump L/V; continuous routes T | Starting position, wall, flight, sun/wind and teammate overlap. A dive is not itself evidence of a superior route. R09 |
| 2B/SS/3B: ground-ball acquisition | Approach steps, body/glove position, hop selection, first touch, secure possession and transition; C/A | Ground/fielding/error sequence E; range OAA L/V; joints/hops/footwork T | Surface and spin, ball speed, handedness, charge depth and throw required. No professional optimal shoulder angle follows from an amateur comparison. R06–R07 |
| 1B: receiving and scoops | Throw geometry, bounce, foot-on-bag/reach and acquisition relative to runner arrival; A/H | Putout/error sequence E; dedicated receiving L/V; full reach/scoop motion T | Thrower's accuracy, runner location and opportunity exclusions. Receiving and range require separate targets. R08 |
| All fielders: throwing | Velocity, release delay, trajectory/bounces, accuracy, target and out/hold value; A/H | Assists/outs/advancement E; arm/extra-base prevention L/V; full mechanics T | Position-specific effort selection and runner choices; assists alone omit successful deterrence. R10 |
| Middle infield/relay players: coordinated execution | Feed/pivot time, relay alignment, cutoff choice, base coverage, tag reach/sweep and collision avoidance; C/A | DP/pivot/fielding sequence partly E; synchronized execution T | Multi-player attribution, runner interference, legal constraints and force/tag situations. Keep as explicit measurement gaps, not invented numerical features |
| Runner: lead, return and steal decision | First-movement lead, release lead, movement onset, gained distance, return/pickoff risk; P/R/A | Occupancy/attempt results E; basestealing summaries L/V; exact historical leads/onsets T | Pitcher handedness/delivery, disengagement count, catcher, count and tactics. First-movement and release lead are not interchangeable. R12–R13 |
| Runner: acceleration/sprint | Distance-time splits, acceleration profile and high-speed capacity; R/C/A | Sprint/splits L/V; full trace T | Effort/opportunity selection, starting motion, batter box side and injury/age; top speed alone is not a jump or decision metric. R11 |
| Runner: route/turn | Path around the bag, speed loss, reacceleration, contact foot and route length; C/A | Advances E; complete route T | Destination certainty, ball/fielders, surface and runner capacity. A double is not a direct turning-efficiency measurement. R14 |
| Runner: advance/hold and arrival | Chance taken, hold, tag-up timing, reach/slide, braking and maintaining contact; C/A/H | Advances/outs E; extra-base value L/V; tag/slide trajectories T | Coach instructions, score/outs, throw/receiver and objective. Arrival speed and safe arrival are different outcomes. R10, R15 |

The table is a proposed measurement inventory, not a declaration that every factor has an established causal effect. Catcher game-calling and pitcher fielding can be represented as decisions/execution when measured, but player identity or team ERA must not be relabeled as those abilities.

## 4. Fifteen evidence capsules

### R01. Deshpande & Wyner (2017): hierarchical pitch-framing model

[Author full text, version 2](https://arxiv.org/html/1704.00823v2); [journal DOI](https://doi.org/10.1515/jqas-2017-0027)

- MLB PITCHf/x: 2011–2013 location baselines, 2014 model fitting, 2015 testing. The 2014 analysis used 308,388 taken pitches near the approximated zone, involving 101 catchers and 93 umpires.
- Hierarchical logistic models adjusted location, count and participants, with uncertainty in catcher effects. The next-year evaluation required participants already observed in 2014; additional within-year holdouts examined model complexity.
- This is professional outcome-model evidence, not glove-motion measurement. Observed plate location is required: its same-pitch forecast clock is late, not P. Unmeasured receiving motion, sensor/zone conventions, take selection and changing umpire behavior remain limitations. It supports partial pooling and uncertainty-aware comparisons, not a causal prescription for hand movement.

### R02. Official catcher framing, stance and ABS definitions

[Framing](https://baseballsavant.mlb.com/leaderboard/catcher-framing), [stance](https://baseballsavant.mlb.com/leaderboard/catcher-stance), [ABS metric documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)

- Current framing has park/pitcher adjustments, a 2018-onward model boundary and a separate archived 2015–2017 model. Preserve that boundary rather than concatenating scores as one fixed instrument.
- Stance data start in 2020; knee-down classification uses a knee below nine inches at release. The displayed 2020–2024 group comparison reports 47% versus 45% shadow-zone called strikes and equal 0.6 WP/PB per 100 pitches. These are observational groups, not randomized evidence of the effect of changing a given catcher's stance.
- In 2026 documentation, framing uses the initial umpire call; changes from challenges are valued separately. Replacing initial calls with final ABS-corrected calls changes the target. Stance at release is already R, even if a different pre-release setup measure might someday be available at P.

### R03. Official catcher blocking

[Blocking model description](https://baseballsavant.mlb.com/leaderboard/catcher-blocking)

- MLB pitches receive loose-pitch probabilities using pitch location, speed/movement, catcher location and handedness. Blocks Above Average compares observed WP/PB with the opportunity-adjusted expectation; the displayed run conversion is 0.25 per block.
- This demonstrates why raw passed-ball counts omit pitch difficulty. It does not measure chest angle, glove angle, lateral push-off, rebound distance or recovery time.
- Use as descriptive evaluation or lagged history, subject to rights and coverage checks. Avoid interpreting a WP as solely pitcher failure or a PB as a measured error in catcher technique. The public definition does not provide sufficient model/sensor validation to claim independent replication of the production metric.

### R04. Official catcher throwing and pop time

[Throwing model](https://baseballsavant.mlb.com/leaderboard/catcher-throwing), [pop-time definition](https://baseballsavant.mlb.com/leaderboard/poptime)

- Throwing difficulty uses runner distance and speed, pitch location, handedness and special-play context at plate crossing. Caught Stealing Above Average compares actual with expected outs on attempts; its displayed conversion is 0.65 runs per additional caught stealing.
- Pop Time ends at the fielder's **projected receiving point at the base center** in its dedicated definition. It combines exchange and throw travel; it is not the tag-completion timestamp. Casual descriptions elsewhere use glove reception, so retain the precise source definition when joining metrics.
- Runner progress at plate crossing partly absorbs pitcher/runner contributions; this is a later conditional evaluation. Attempt-only performance still needs an opportunity/deterrence model for a complete running-game assessment. A fast but inaccurate throw may fail to produce an out.

### R05. Professional catcher throw mechanics: two small studies

[Kawabata et al. (2020), publisher abstract](https://journals.sagepub.com/doi/10.1177/1747954120930370); [Suzuki & Maeda (2024), open journal record](https://www.jstage.jst.go.jp/article/rjsp/16/0/16_2212/_article/-char/en)

- Kawabata: four professional and twelve collegiate catchers, three prescribed throwing approaches, high-speed video. Quick-release instructions produced shorter total throwing times than usual or velocity-emphasis instructions. Both movement and airborne phases mattered. Only the publicly accessible abstract was assessed; detailed accuracy, trial-selection and protocol robustness were not independently established here.
- Suzuki/Maeda: one Japan national-team catcher compared with three professional peers using optical 3-D motion analysis and a force plate. The selected catcher had the shortest catch-to-release motion, including a shorter catch-to-pivot-foot-contact phase, and higher center-of-gravity speed at reception.
- These support phase-level measurement and coordination hypotheses. Four professionals in either study cannot establish MLB population norms; selection of an unusually successful catcher is especially vulnerable to case-selection bias. Neither establishes a universally preferable stance or long-term injury effect.

### R06. Official range evaluation and positioning

[OAA](https://baseballsavant.mlb.com/leaderboard/outs_above_average), [location/role breakdown](https://baseballsavant.mlb.com/visuals/statcast-infield-defense), [average starting positions](https://baseballsavant.mlb.com/visuals/fielder-positioning-all)

- OAA accumulates made-play credit and missed-play debit relative to estimated difficulty. Totals therefore combine opportunity volume and performance; compare rates and denominators alongside totals.
- Infield difficulty uses intercept distance/time, distance to the target base and average runner speed on force plays; historical values can be revised. [Definition](https://www.mlb.com/glossary/statcast/outs-above-average)
- The defensive visual distinguishes lineup position from field location. Starting-position summaries expose depth from home and field angle, not every defender's trajectory on each pitch.
- Role assignment, team tactics and the opposition's batted-ball distribution affect exposures. A range metric alone is not a validated replacement for throw accuracy, receiver skill, tags, cutoff decisions or double-play coordination. Whole-defense evaluation must specify exactly which components and excluded plays are included.

### R07. Ground-ball acquisition and cooperative decisions: amateur experiments

[Ogura & Kawamura (2017)](https://www.jstage.jst.go.jp/article/jcoaching/31/1/31_103/_article/-char/en); [Kikumasa & Kokubu (2019)](https://www.jstage.jst.go.jp/article/jjpehss/64/2/64_19007/_article/-char/en)

- Ogura/Kawamura compared higher-level amateur with college infielders using 300-Hz video and 3-D reconstruction. Catching position did not significantly differ; selected shoulder movements did. The English abstract does not give group sample sizes, so no sample count is inferred. This is not a professional experiment or evidence for a universal angle target.
- Kikumasa/Kokubu studied seven collegiate catchers in an on-field sacrifice-bunt scenario. Ball motion and acquisition time/location helped discriminate who fielded and which base received a throw or instruction; a stepwise discriminant analysis reported 84.1% classification.
- That percentage is not established prospective MLB decision accuracy. Small samples, selected tasks and feature selection limit transfer. Using realized catch time to predict an earlier decision would leak later information unless it is replaced with a genuinely available estimate.

### R08. Official first-base receiving, including scoops

[Leaderboard and model scope](https://baseballsavant.mlb.com/leaderboard/first-base-scoops-receiving), [model-author explanation](https://tangotiger.com/index.php/site/article/statcast-1b-scoops-and-more)

- The model evaluates throws from second, short and third using throw placement/bounce plus runner speed and runner distance at the catch. Only throws within eight feet of first base enter; the displayed season options include 2021 onward.
- This isolates a different opportunity from fielding the original batted ball. Do not attribute all successful throws to the thrower, or call this a complete measure of first-base defense.
- The radius/source-position exclusions matter for denominator construction. Catch-time inputs make it A/H; public aggregate receiving value does not supply a pre-contact scoop probability or a full kinematic record of reach, foot contact and glove motion.

### R09. Official outfield catch difficulty and jump

[Catch probability](https://baseballsavant.mlb.com/leaderboard/catch_probability), [jump leaderboard](https://baseballsavant.mlb.com/leaderboard/outfield_jump), [jump glossary](https://www.mlb.com/glossary/statcast/jump), [wall factor](https://www.mlb.com/glossary/statcast/catch-probability)

- Catch difficulty uses required distance, time and direction; the dedicated leaderboard defines opportunity time from pitcher release and uses shortest required distance. Wall proximity also enters catch probability.
- Jump separates reaction and burst across successive 1.5-second windows plus route efficiency; its glossary anchors the three-second window at pitch release.
- The jump leaderboard selects opportunities with catch probability at most 90%. This excludes routine-play behavior and is not a season-wide running-effort sample. The components are spatial performance summaries, not direct sensory reaction latency or joint-level acceleration mechanics.
- Preserve release-versus-contact anchors explicitly. A reimplementation timed only from contact is a different feature until demonstrated equivalent. Raw event outcomes and batted-ball locations cannot reconstruct the path taken.

### R10. Official arm strength and batted-ball advancement/hold value

[Arm strength](https://baseballsavant.mlb.com/leaderboard/arm-strength), [extra-base value](https://baseballsavant.mlb.com/leaderboard/baserunning)

- The arm leaderboard uses selected upper tails: top 1% for first basemen, 5% for other infielders and 10% for outfielders, with different qualification minima. It is not average velocity across every throw or a common-effort laboratory test.
- Extra-base evaluation uses runner/defender geometry and capacities, including chances taken or declined; stolen bases are excluded. It offers runner and outfielder views of the interaction.
- For a new decision model, define the moment of choice and compare feasible hold/advance/throw alternatives using only information then available. Current production metric summaries do not establish the causal value of instructing a runner to go or a fielder to throw elsewhere. Speed, accuracy, release delay, relay use and tag execution should remain distinct.

### R11. Official sprint speed and running splits

[Sprint Speed](https://baseballsavant.mlb.com/leaderboard/sprint_speed), [90-foot splits](https://baseballsavant.mlb.com/leaderboard/running_splits)

- Sprint Speed uses a runner's fastest one-second interval, and the season summary averages roughly the best two-thirds of qualifying runs. Eligible situations are selected; this is not mean speed across all baserunning.
- The separate splits surface is relevant to acceleration profiling, but its public visibility does not establish a complete event-level acceleration export or a standardized instrument error estimate.
- Use prior-period capacity summaries cautiously. Do not derive first-step latency, lead distance, route curvature, limb asymmetry or effort from this speed summary. Running opportunities, home-to-first box position, moving starts and deceleration requirements are measurement-design issues, not nuisance variables that can be assumed absent.

### R12. Official basestealing value and lead distance gained

[Basestealing model/eligibility](https://baseballsavant.mlb.com/leaderboard/basestealing-run-value)

- The metric conditions on the opposing pitcher/catcher and includes successful advances, outs and non-attempt opportunities. Its second-base opportunity definition requires a runner on first with no other runner; the third-base definition requires a runner on second and nobody on third.
- Lead Distance Gained is displacement between pitcher first movement and release. It is not simply the initial lead, not a measured sensory reaction time, and not necessarily a new stolen-base attempt.
- Those eligibility definitions must accompany rates; they do not cover every possible running tactic. Non-attempt valuation is model-based, not direct observation of the counterfactual success of a steal that never happened. Rule-era and opportunity comparisons require care.

### R13. Powers et al. (2026): lead choice under the pickoff limit

[Version 2 full preprint, revised 2026-08-16](https://arxiv.org/html/2601.15608v2), *Strategies under a pickoff limit in baseball: A zero-sum sequential game with multilevel models*

- Uses 722,899 2022 and 726,868 2023 pitch/pickoff plays, public context/capacity summaries and **proprietary MLB first-movement lead distances**. Secondary leads are not supplied by that tracking input.
- Multilevel transition models feed a sequential game; runner/pitcher agency is restricted to first base occupied alone. Version 2 adds 20-fold predictive validation and 100 bootstrap replications propagating uncertainty to policies.
- Prospective intervention success is not demonstrated by cross-validation of observational transition models. The game optimizes its specified objective under its opponent/transition assumptions; simultaneous rule changes and endogenous lead selection limit causal interpretation. Season-level capacities also require cutoff-safe handling in a live forecast.
- This is a strong example of a scientifically meaningful variable that cannot be recreated from the available event table. No tracking permission or universal lead-distance coaching rule follows from access to the paper.

### R14. Imawaka, Yanaka & Tsunoda (2025): base-running route and turning

[Open journal article](https://www.jstage.jst.go.jp/article/jjpehss/70/0/70_007-23067/_article/-char/en)

- Fifteen male collegiate players performed home-to-second running and a 54.86-m straight sprint. Three-dimensional panning DLT measured path and speed before/after first base.
- Home-to-second time was associated with path measures, deceleration and speed in the first-to-second segment. Straight-sprint time related to maximum speeds but not the measured route variables.
- This supports measuring the turn separately from straight-line capacity. It is a small correlation study, not an MLB intervention or proof that a fixed wider route benefits everyone. A known two-base destination differs from deciding whether to advance while reading a live play. No route or body-lean angles should be assigned from a player's doubles total.

### R15. Ficklin, Dapena & Brunfeldt (2016): arrival and sliding

[Author institutional record](https://scholarworks.uni.edu/facpub/1032/), [open full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6188574/)

- Nine intercollegiate players completed counterbalanced run-through, head-first, feet-first and stop-on-base conditions, with video timing/3-D kinematics. A mathematical simulation addressed diving into first base.
- The measured run-through condition was fastest overall; the simulated diving advantage was not statistically established. This is not direct evidence that diving into first is faster in MLB games or a safety-tested intervention.
- Retain the actual objective: touching an overrun-permitted base differs from stopping and staying on a taggable base. Tag avoidance, contact maintenance, throw placement and injury outcomes were not all captured by the timing comparison. It justifies distinguishing arrival tasks, not recommending a risky technique.

## 5. What the available files actually contain

### Existing Retrosheet event/parsed files: usable state and outcomes, not motion

The already-downloaded 2025 parsed-play header was inspected directly, alongside the existing alignment audit and [Retrosheet event specification](https://www.retrosheet.org/eventfile.htm). It includes:

- State/identities: game/play identifiers, inning, count, outs, runners, batter/pitcher and handedness; defensive identities, lineup fields and umpire identifiers
- Running outcomes: `sb2/sb3/sbh`, `cs2/cs3/csh`, `pko1/pko2/pko3`, `bk`, `di`, `oa`, pre/post runners and runner-out/run fields
- Defensive outcomes: `wp`, `pb`, errors by position, putouts, assists, `fseq`, `firstf`, coarse `loc`, `hittype`, `dpopp` and `pivot`

Presence is not completeness or validated interpretation for every year. Raw substitutions and pitch-sequence markers need correct chronological parsing. `loc` is a batted-ball location category, not a defender's x/y start or a glove coordinate. Counts of outs, errors, assists or advances cannot identify body angles, velocity, lead length, tag timing or paths.

### Documented Statcast Search fields: partial physical/context information

The [current CSV documentation](https://baseballsavant.mlb.com/csv-docs) specifies catcher/fielder IDs (`fielder_2` through `fielder_9`), base occupancy, broad infield/outfield alignment, pitch location/flight and batted-ball fields. `hc_x/hc_y` describe batted-ball hit coordinates; they are not defender trajectories. This pass did not establish these role-specific full traces or all leaderboard quantities as standard CSV columns. No CSV was fetched.

### Public surfaces versus unavailable measurements

- **Verified public L/V surfaces:** the metrics linked in R02–R04 and R06/R08–R12. Some display player/play drilldowns; therefore “only aggregates exist publicly” would be too strong. This review establishes the pages and definitions, not comprehensive machine-readable event coverage, historical snapshots, permitted reuse or calibration metadata.
- **Not present in audited E/S schema:** continuous fielder/runner x/y, complete glove/release-to-tag trajectories, force/EMG, individual hop/contact/footwork annotations and complete joint motion. Some may exist in restricted systems or selected visualizations; that does not make them available to this project.
- **Demonstrably proprietary example:** R13's first-movement lead file. A public article or aggregate lead-distance leaderboard is not a substitute for it.
- **Laboratory/video studies:** journal methods and reported findings do not imply reusable participant-level data. No participant dataset was acquired.

## 6. Consequences for a defensible build

1. An event-only extension can model steal/advance decisions and outcomes, WP/PB, double-play opportunities and team defense context. Name it event-based analysis; do not call it a reconstructed biomechanics model.
2. Use a multi-stage design if later rights-cleared tracking becomes available: opportunity/selection, early movement, acquisition, choice, execution and outcome. Report the forecast clock at each stage and avoid post-outcome labels in predictors.
3. Keep linked interactions explicit: pitcher–catcher–runner on steals; thrower–receiver on throws; multiple defenders on relays and double plays. Player credit depends on the model and cannot be assumed uniquely identifiable.
4. Evaluate temporally, with grouped games/players as appropriate, shrinkage for sparse opportunities, calibration and uncertainty. Separately test attempt selection, success conditional on attempt and denied/unused opportunities.
5. Version rules, instruments and targets, including the 2023 running/positioning regime, catcher-framing model history and 2026 initial-call/ABS distinction. Document units, anchor times, exclusions and source revisions.
6. Require independent, representative validation before using pose/proxy outputs as professional mechanics. This pass found no basis for manufacturing missing joint angles, first steps or route efficiencies from scores, box totals or event counts.

## 7. Search/assessment boundary

Searches covered official Savant role-specific definitions; primary framing models; catcher throw timing and professional comparisons; ground-ball acquisition/cooperative fielding; lead-distance decision models; and turning/arrival experiments. Primary documents were preferred. Publisher abstracts are labeled where full methods were not assessed. The newer version of R13 was checked after finding the earlier preprint; this matters because its validation section changed. Searches for catcher blocking biomechanics did not produce a representative professional causal study suitable for a technique prescription in this bounded pass. This is a documented evidence gap in this review, not a claim that no other study exists.
