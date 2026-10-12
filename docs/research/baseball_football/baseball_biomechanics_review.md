# Baseball mechanics, fatigue, injury and environment: primary-evidence review

Reviewed: 2026-10-11. Scope: a focused, primary-source scientific inventory to complement the Statcast/Retrosheet tactical review. This is a narrative review, not a systematic review or a clinical guideline. It does not claim that every potentially relevant variable has been studied adequately. No restricted tracking dataset, video collection, or clinical dataset was downloaded, and no predictive model was implemented.

## 1. What the evidence changes

1. **Separate mechanics from their observable consequences.** A professional analysis should distinguish body/segment motion, forces and joint moments, ball release, flight, perception and swing decisions, contact, and the eventual play result. A score or strikeout cannot identify the movement pattern that produced it.
2. **There is meaningful professional pitching evidence.** The strongest additions are prospective UCL-surgery follow-up, large motion-capture cohorts, and professional-versus-amateur comparisons. However, “professional” often pools MLB and MiLB or concerns newly drafted players. It must not silently become “representative MLB.” [B01–B08]
3. **Fatigue is not a single measured quantity.** Workload, perceived exertion, strength loss, neuromuscular coordination, velocity changes, and tissue loading are different variables. They may change differently within the same outing. [B09–B15]
4. **Stable pitch output does not prove stable protective capacity.** An especially useful recent experiment measured reduced medial-elbow muscular restraint while aggregate external loading stayed similar. This is mechanistic support for a load-versus-capacity distinction, not an MLB injury alarm validated for deployment. [B12]
5. **No universal optimal arm slot, separation angle, stance, or pitch-count threshold follows from this literature.** Cross-sectional differences among athletes do not establish the effect of changing one athlete's motion. Differences in measurement convention and competition level are substantial. [B02–B08, B16–B18]
6. **Some real mechanics are publicly visible.** Arm angle, batter positioning, stance and bat-tracking summaries are available through official Savant surfaces. These remain distinct from private full-body trajectories, force plates, joint moments, grip measurements, and medical records. Public visibility does not settle reuse rights or guarantee pitch-level availability. [D01–D05]
7. **Environment belongs in the mechanics chain.** Air conditions affect flight, ball storage affects impact properties, and park geometry maps a flight into an outcome. Travel and recovery are additional context; none should be converted into an invented change in a player's technique. [B22–B25]
8. **Promising proxy models need independent validation.** Recent release-to-torque and broadcast-pose papers expand the scientific inventory, but they do not supply a ready, openly reproducible clinical prediction system. [B26–B28]

## 2. Measurement and inference rules

### Prediction clock

- **G: before the game.** Historical player/arsenal distributions, prior workload, known roster and injury-status reports, park geometry, forecast available at the forecast cutoff, travel/rest history, rule era
- **P: immediately before the pitch.** Count, outs, bases, pitcher/batter matchup, defensive setup, prior pitches, and any genuinely available current stance/pose observation
- **R: release/early flight.** Current release and early-flight measurements, only after their actual acquisition and processing time; a provider field labelled “initial” can still be estimated after the entire flight
- **C: contact or nearest bat–ball approach.** Current bat speed/path/intercept, exit velocity and launch conditions; explanatory for this swing and usable for later predictions, unavailable for an earlier decision
- **H: future-health horizon.** A prespecified endpoint and horizon, with predictors censored at a documented baseline; subsequent surgery, future rest days and retrospective injury labels cannot leak into predictors

Use lagged distributions at G/P for metrics first observed at R/C. A model conditional on the realized pitch or swing answers a different question from a pre-pitch recommendation. Do not mix those tasks in one reported accuracy.

### Evidence labels used below

- **M:** controlled physical/measurement evidence; strong for the tested mechanical relationship, not automatically for game performance or injury prevention
- **P:** prospective observational outcome evidence; better temporal ordering, still susceptible to confounding and selection
- **A:** cross-sectional, retrospective or repeated-measure association
- **E:** exploratory/preprint or insufficiently replicated evidence

These are task-specific labels, not formal GRADE ratings. Measurement validity, transportability, causal effect, predictive value, and access feasibility are separate judgments.

## 3. Factor inventory and proposed measurement specification

The following is an analyst-designed specification informed by the cited studies. “Candidate” means a hypothesis to measure and validate, not a proven useful feature or intervention.

| Factor domain | Measurement definition and relevant clock | Important confounders / interpretation traps | Evidence and availability | Feasible scientific treatment |
|---|---|---|---|---|
| Lower-body force production and braking | Drive/lead-leg ground-reaction force and impulse; stride length normalized to body size; lead-knee flexion/extension velocity at named events; G history or R current delivery | Body size, mound/surface, shoes, effort, pitch type, windup/stretch, foot-contact definition | M/A laboratory studies; professional pelvic/knee associations B02, B03; force plates generally private | Preserve as a true-mechanics domain; do not infer ground forces from release extension or final velocity |
| Pelvis–trunk sequencing | Segment orientations, angular velocities and time between their peaks; hip–shoulder separation at foot contact and its time course, not just one maximum; R | Angle versus timing are different; coordinate systems and cycle normalization differ; anatomy, level, velocity, task constraints | A: professional/mixed cohorts B02–B04; college and HS B07–B08; not standard public ball tracking | Model within-athlete trajectories with validated pose or markers; include interaction terms, not a universal separation target |
| Trunk tilt / shoulder position | Sagittal and lateral trunk angles; shoulder abduction and external rotation at foot contact, maximal external rotation and release; R | Same apparent arm slot can arise from different combinations; movement phase matters; filtering affects derivatives | A: large adult cohort B04 and arm-slot B05; collegiate B06 | Keep joint and trunk variables separate; monitor uncertainty and reject unsupported mechanical diagnoses |
| Arm path, joint loading and tissue load-sharing | Hand trajectory; elbow/shoulder net joint moments via inverse dynamics; distinguish peak moment, loading rate and time integral; R/H | Net joint moment is not isolated UCL force; model inertias, marker placement and filter choices matter; tissue capacity varies | M/A/P: B01, B04, B09, B12, B26; usually private | Do not label an estimated net moment “ligament strain”; do not reuse a model's torque estimate as a measured injury probability |
| Arm angle and release geometry | Measured release position/extension plus shoulder-to-ball angle; R, or lagged G/P summaries | Height, limb length, mound position, trunk lean and elbow posture can produce similar releases; sign/reference conventions | Official arm-angle surface D02; professional comparison B05 | Use separate named observables, stratify pitch type/handedness, and test changes against within-player variability |
| Effort, velocity and pitch type | Measured velocity, prescribed/perceived effort, repertoire; R or historical G/P | Effort is not proportional to velocity or torque; between-pitcher relationships differ from within-pitcher changes | M/A: B09–B10 and B15; velocity/type public, effort private | Estimate player-specific baselines; no “10% less effort means 10% less load” rule |
| Spin, axis, seams and release contact | Spin vector, gyro/transverse components, seam orientation, finger force and release timing; R | Same spin rate can yield different movement; seam-induced force is not fully specified by a 2-D axis; ball construction and air | M physical studies B20–B22; rate/axis summaries public, exact seams/grip usually unavailable | Model ball flight explicitly; treat unexplained movement as residual until an independently measured mechanism is available |
| Approach angles and trajectory shape | Tangent to flight at a specified plate plane; horizontal/vertical components, arrival time and location-normalized residuals; R/C | Location, release height, speed, extension, air and tracking fit; 2026 plate-plane change; selection on swing | Physics supports geometric measurement, not a universal performance effect; D01 plus existing trajectory review | Derive using documented units/plane and verify against known trajectories; use P only through forecasts of the next pitch |
| Tunneling / deception / sequence | Pairwise flight similarity at several time-to-contact points; angular separation from a stated batter viewpoint; velocity/arrival-time differences; P/R | A fixed spatial “decision point” is not every hitter's perceptual deadline; count, intended location, pitch choice and batter adaptation confound | Plausible mechanism; experimental perception B18; no well-isolated MLB causal tunneling effect established in this focused pass | Retain as a candidate domain; evaluate incremental value beyond pitch quality/location and prior-pitch context, not a hand-coded bonus |
| Command / execution | Error relative to intended target, with miss direction and dispersion; R/C | Public plate location is observed execution, not target; strikes are not interchangeable with good command | Intended target usually private; B10 does not validate a command target from ball/strike outcomes | Separate location distribution from command; require catcher target annotation or reliable target data for target error |
| Batter stance and box position | Foot spacing/orientation, hip-midpoint box depth and off-plate position at a declared event; P/R/C | Handedness is not stance; two-strike tactics, pitch location, athlete dimensions and pre/post-stride definitions | Official positioning D03; stride-specific college/KBO studies B16b–B16c; intervention-quality MLB outcome evidence remains limited | Explore within-batter changes with event timestamps; distinguish static stance from dynamic stride and leaderboard averages from individual-pitch measures |
| Swing initiation and lower-body coordination | Stride-foot contact, weight transfer/force impulse, pelvis and trunk rotation, swing-onset latency; P–C | Tee, machine and live pitching elicit different coordination; anticipated pitch speed/type and contact goals | M/A collegiate experiments B16–B17; mixed-level professional comparison B16a; tiny KBO task manipulation B16c; private markers/force plates | Use task-specific models; do not transfer tee norms directly to MLB live hitting |
| Bat path and contact timing | Time-varying sweet-spot trajectory, swing-plane tilt, attack direction/angle and intercept position; C | Timing changes the sampled part of the path; pitch geometry, swing selection, bat length/grip and body dimensions | Public summaries D04; college timing experiment B19; existing swing-tracking papers | Evaluate contact-adjusted and location-adjusted summaries; launch angle cannot stand in for bat attack angle |
| Perception, gaze and anticipation | Gaze/head orientation, predictive saccade timing, occlusion or advance-information conditions; P–C | Eye-tracker calibration, practice versus live game, pitch predictability, very small elite samples | M/A: six NPB top/farm players B18; public MLB eye tracking unavailable | Scientific explanatory domain and targeted future study; no inferred visual-acuity score from strikeouts |
| Bat–ball impact and equipment | Relative velocities, impact offset/orientation, bat inertia and local collision response; C | Wood versus metal/composite, bat properties, collision point and ball compliance; lab versus live task | M: B21–B22; public exit velocity/path partial, equipment properties mostly unobserved | Keep physical impact variables distinct from training strength or decision skill |
| Acute workload, fatigue and recovery | All throws, counts by intensity/type, warm-up/bullpen work, inning duration, rest intervals, RPE, strength/EMG/coordination change; G/P/R/H | Manager removal, opponent order, leverage, role, baseline capacity and warm-ups; fatigue can exist without velocity decline | Mixed M/A results B11–B15; game counts public, complete exposure/physiology private | Workload proxies may support prediction; label physiological state unknown unless measured; model heterogeneous trajectories |
| Chronic exposure and health | Prior exposure windows, role transitions, rehabilitation, prior diagnoses and time-to-event; G/H | Healthy-worker survival, informative dropout, delayed diagnosis, offseason omissions, surgery selection and era | P: early-career pros B01, one-organization MiLB B13; clinical outcomes private | Separate surgery, arm injury and availability endpoints; require prospective validation, calibration, privacy controls and medical oversight |
| Travel, schedule and sleep | Time-zone transitions, rest days, game timing; actual sleep/circadian phase only when measured; G | Scheduled location is not individual itinerary or sleep; team quality, park and calendar; recovery assumptions | A: MLB archival study B25; schedules public, physiology private | Use explicit travel proxies and sensitivity analyses; do not state that an individual is sleep-deprived |
| Weather, roof and air density | Temperature, pressure, humidity, density, wind vector in park coordinates, roof state; G forecast/R contemporaneous | Stadium wind differs from airport wind; precipitation selection; temperature may affect players as well as flight; forecast hindsight | M physics plus A MLB panel B20, B23; weather join feasible after source audit | Keep forecast and observed-weather versions separate; use roof interactions and uncertainty, not universal distance adjustments |
| Park geometry and ball regime | Wall distances/heights, foul territory, surface, altitude, ball-storage/manufacturing era; G/C | Park is correlated with team/player mix; renovations and baseball changes are time-varying | M impact evidence B22; MLB environmental B23; some geometry/era metadata public | Version geometry and park effects by date; never equate aggregate park factor with a pure physical carry coefficient |
| Rules, sensors and officiating | Pitch-clock regime, shift/base rules, ABS/zone definition, ball/grip enforcement, tracking generations and calibrations; G/P | Co-occurring changes and altered sampling/labels; rule effects differ by level and adoption date | Official D01; observational clock evidence B24 | Build an explicit regime registry; treat implementation dates and metric definition breaks as data-model boundaries |

Other important domains to retain in a complete baseball system include catcher receiving/blocking/throwing, fielder routes and positioning, baserunning acceleration/turns, defensive injury/availability, and umpire decisions. Those are outside this focused pitching/hitting review, not presumed irrelevant or recoverable from scores alone.

## 4. Primary studies: population, result and limitations

### A. Kinetic chain and pitching mechanics

**B01. Fleisig et al. (2025), prospective UCL-surgery study.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12227930/)

- Healthy recent draftees were recruited in 2015–2017 and followed through 2019: 305 professional pitchers; 31 surgery events; 248 valid full-effort biomechanical assessments, including 28 subsequent cases
- Baseline motion capture, examination and MRI were linked to professional-baseball injury surveillance; Cox models associated an additional 10 N·m of elbow varus torque with hazard ratio 1.26, 95% CI 1.01–1.56
- This is newly entering professional baseball, not an MLB-representative sample. Baseline-only testing, missing examinations/MRI, few events, dropout and early termination before pandemic seasons limit interpretation. Normalized torque was not significant. Surgery is a selected endpoint
- **P; meaningful temporal evidence, no demonstrated benefit from a torque-lowering intervention.** Individual data are not public Statcast. Do not translate the hazard ratio into an absolute personal risk or a causal prescription

**B02. Aguinaldo & Escamilla (2019), segmental power.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6390228/)

- Sixteen professional pitchers from MLB/MiLB organizations and 15 high-school pitchers underwent marker-based analysis
- Segment mechanical power, trunk timing, velocity and elbow loading were analyzed. Trunk timing/power were associated with ball speed; the larger model also included upper-arm power for elbow loading
- Absolute torque was greater in professionals; body-size-normalized torque did not significantly differ. This illustrates why population composition and normalization matter
- **A/M; small cross-sectional laboratory sample.** Power transfer is a mechanistic construct, not proof that coaching “more separation” improves performance or health. The clinical training suggestion in the discussion was not tested as an intervention

**B03. Dowling et al. (2022), pelvic rotation in professionals.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9720809/)

- 157 active MLB/MiLB-roster pitchers; fastballs measured at 480 Hz; groups split at the sample median pelvic orientation at foot contact
- The more-open group had longer strides and faster lead-knee extension and ball velocity, without a statistically significant elbow-varus-torque difference
- **A; directly relevant professional measurements, but pooled levels, laboratory context and median-split comparisons.** This conflicts with simplistic claims that an open pelvis must always reduce velocity or increase arm stress. It does not establish an optimal angle or a safe intervention. Anatomy, other mechanics and selection remain explanations

**B04. McCutcheon, Slowik & Fleisig (2025), multiple kinematics and torque.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11789100/)

- 523 healthy adult pitchers: 425 professional, 98 collegiate. Marker-based fastball testing yielded 21 kinematic variables and body-size-normalized torque
- A stepwise model retained 11 parameters and explained 40% of normalized-torque variance; high/low torque groups differed in several early arm, trunk and knee variables
- **A; larger sample, still descriptive.** Correlated features, model selection, pooled competition levels and lack of independent intervention/outcome validation limit causal claims. The unexplained variance is substantial. A ratio of velocity to normalized torque is a defined composite, not a direct measure of biological efficiency or injury safety

**B05. Coladonato et al. (2023), arm-slot comparison.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10601404/)

- 288 professional and 130 high-school pitchers threw 8–12 motion-captured fastballs
- Arm-slot groups differed in shoulder abduction, lateral trunk tilt and other timing/kinetic measures; professional and high-school relationships were not interchangeable
- **A; useful evidence against a universal arm-slot prescription.** Their arm-slot angle is referenced to vertical; public Savant arm angle uses horizontal. A conversion is not justified until the underlying vector, event and coordinate definitions match. Changing an angle in isolation was not tested, nor was subsequent injury measured

**B06. Solomito et al. (2018), sagittal trunk tilt.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6194942/)

- 99 collegiate pitchers; 3-D motion capture and random-intercept models
- Greater forward tilt at release was associated with both elbow varus moment and velocity; the reported increment beyond 28° was 2.9 N·m and 0.7 m/s per 10°
- **A; collegiate rather than professional.** The median-centred slope does not make 28° an optimum, safety limit or treatment target. Repeated pitches and body-position covariation matter. Torque is an intermediate biomechanical outcome, not observed injury prevention

**B07. Wada et al. (2025), pivot leg, pelvis and separation.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11835564/)

- 18 male collegiate pitchers, ten maximal-effort stretch pitches, 250-Hz motion capture; three fastest successful pitches per player analyzed
- Stride-phase pivot-leg/pelvis motion was related to trunk separation. Foot-contact separation correlated with speed (Spearman ρ=0.50), while peak segment rotational velocities did not correlate with speed in this sample
- **A; small and selected trials.** No arm-kinetic outcome was measured. This supports examining coordinated phase-dependent movement, not claiming a larger separation necessarily lowers elbow load. Selection of fastest successful trials narrows generalizability

**B08. Bullock et al. (2020), passive range of motion versus dynamic separation.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7727427/)

- 32 high-school pitchers, four fastballs, motion capture plus clinical hip/trunk range-of-motion measurements
- Separation correlated with peak trunk speed, and trunk speed with ball speed; passive hip/trunk ROM was not significantly related to the measured pitching kinematics
- **A; explicitly not pro evidence.** Dynamic coordination cannot be inferred from a flexibility test, and this design does not prove the entire proposed causal chain. Industry angle thresholds mentioned in the paper should not be promoted to universal professional targets

**B09. Slowik et al. (2019), velocity within versus between pitchers.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6485842/)

- 64 of 452 professional pitchers met pitch-velocity distribution requirements for analysis; 240-Hz markers, radar and inverse dynamics
- Velocity explained little between-player torque variation (reported R²=0.076); a random-intercept analysis reported much stronger within-player association
- **A; important hierarchical-model lesson.** Anthropometrics and individual delivery confound population comparisons. A mixed-model fit statistic is not an externally validated forecast of a new player's torque or injury. The selected subset and laboratory fastballs do not establish a universally transportable velocity-to-load equation

**B10. Escamilla et al. (2017), pitch-type biomechanics.** [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/28968139/)

- 18 professional pitchers, 38 markers, 32–40 maximum-effort fastballs, sliders, curves and changeups; repeated-measures analysis
- Several shoulder/elbow loads differed by pitch type; many differences involved lower changeup loads. Ball versus strike classifications did not yield significant biomechanical differences
- **A/M; small professional laboratory comparison.** The public abstract was available; full methods were not fully audited here. Pitch type and speed are coupled, and no injury follow-up establishes that one repertoire is safer. A ball/strike label does not measure intended-target command

### B. Fatigue, load, capacity and recovery

**B11. Grantham et al. (2014), live-game collegiate mechanics.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4555605/)

- Eleven NCAA Division I starters from three programs, 26 starts, two orthogonal 120-Hz cameras; 26 kinematic measurements across inning/game/season exposure
- Some hip, elbow and shoulder measures changed. Subjective fatigue increased despite no significant beginning-to-end velocity decline; no participant was injured during the observed season
- **A; live-game relevance but small sample, selected fastballs, 2-D measurement and many comparisons.** Pitch count and self-report are imperfect fatigue measures. These data justify investigating multiple state indicators, not an injury classifier or a universal removal threshold

**B12. Yanai & Onuma (2026), active muscular restraint.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13424898/)

- 28 collegiate pitchers completed seven 15-pitch bullpen innings, plus warm-ups. Markerless recordings estimated elbow load; dynamometry with synchronized ultrasound measured maximal voluntary isometric varus capacity before, after four and after seven innings
- Mean/max pitching load did not significantly change, while mean measured muscular capacity fell 8.6% and 10.0%
- **M/A; direct within-session capacity measurements, no prospective injury endpoint.** Isometric laboratory capacity is not the same as muscle force during a pitch; load estimation and intermittent sampling have uncertainty. Planned breaks and freely chosen repertoires further limit game transfer. The inference of greater reliance on passive tissues is plausible, not a directly measured UCL-force series

**B13. Bullock et al. (2022), starting versus relief roles.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8775284/)

- Prospective 2013–2019 cohort: 297 MiLB pitchers in one MLB organization; 85,270 player-days
- Adjusted arm-injury hazard was higher for starters (HR 2.4, 95% CI 1.5–4.0); shoulder estimates were stronger, while the elbow estimate was imprecise and not significant
- **P; MiLB-specific, not evidence that MLB starters universally have this multiplier.** Role assignment, unmeasured velocity, estimated seasonal pitch exposure, pre-contract history and omitted nongame throws leave residual confounding. Fatigue itself was not measured. Exposure accumulated after baseline can complicate causal adjustment

**B14. Murray et al. (2001) and Escamilla et al. (2007), extended pitching.** [MLB primary abstract](https://pubmed.ncbi.nlm.nih.gov/11292037/); [collegiate primary abstract](https://pubmed.ncbi.nlm.nih.gov/16973902/)

- Murray: seven MLB pitchers; one early and one late fastball per pitcher, high-speed video. Velocity and several forces/torques declined; fatigue versus protective adaptation was unresolved
- Escamilla: ten college pitchers, simulated 105–135-pitch games stopped at perceived fatigue. Velocity and trunk position changed, but no significant increase in shoulder/elbow forces or torques was found
- **A/M; very small samples and limited protocols, abstract-level review here.** These studies do not support a necessary “more pitches → greater net torque” pathway. Conversely, nonsignificant torque changes do not demonstrate absence of fatigue or injury risk

**B15. Hyeamang et al. (2026), prescribed effort.** [Open publisher paper](https://journals.sagepub.com/doi/10.1177/23259671251374296)

- 24 professional pitchers threw at 75% and 100% perceived effort; 38 high-school pitchers also used 50%; 480-Hz motion capture and within-pitcher mixed models
- Reduced prescribed effort lowered measured outputs, but velocity, torque and loading-rate reductions were not proportional to the requested effort percentages
- **M/A; useful short-term manipulation, not a randomized injury-prevention trial.** Subjective effort cannot be used as a calibrated dose. Keep the professional and high-school results separate, and verify the calculation and units of any cumulative-torque quantity before adopting it

**B15a. Mullaney et al. (2025), finger fatigue versus grip.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11952028/)

- 18 high-school/collegiate pitchers completed 64 game-like pitches plus 20 warm-ups; finger-flexion and grip strength were tested between innings
- Middle-finger strength loss after four innings averaged 21%, exceeding ring-finger and grip changes; onset and severity differed across pitchers
- **M/A; small non-MLB sample.** Finger dynamometry is a candidate marker, not a measured ligament load or a validated MLB safety threshold. Strength-training benefits were proposed rather than tested. This adds an otherwise invisible capacity domain to a workload model

**B15b. van Trigt et al. (2023), individual trajectories.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10567693/)

- Fifteen mostly recreational Dutch pitchers, with three from the top two domestic levels; 60–110 fastballs, motion capture and surface EMG
- Group-average torque and muscle-activity trends were not significant, but random slopes differed among pitchers
- **A; valuable repeated-measure design, weak MLB transportability.** The sample's average velocity was approximately 67 mph. Surface EMG is not muscle force, and these trajectories do not establish who will later suffer UCL injury. Pooling pitchers can conceal different individual responses

### C. Batting coordination, perception and contact

**B16. Tee versus pitched-ball batting (2018).** [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/30092394/)

- Ten male collegiate hitters performed tee and pitching-machine batting at about 33.3 m/s; 3-D kinematics, three force platforms and inverse dynamics
- Foot-contact-to-impact timing and lower-limb torque impulses differed between tasks
- **M/A; direct task comparison, small college sample, abstract-level review.** Tee testing does not reproduce the timing constraints of an approaching pitch. An intervention that increases tee exit speed need not improve live-pitch contact, decisions or run value

**B16a. Dowling & Fleisig (2016), tee batting across levels.** [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/27278749/)

- 170 male batters: 33 youth, 69 high school, 22 college and 46 professional; 480-Hz 3-D motion capture
- Professionals differed from youth in rear-arm positioning and extension velocity; higher levels generated faster bat motion
- **A; professional-inclusive, not verified MLB-only; abstract-level review.** Age, body dimensions, strength, selection and training co-vary with level. The paper's suggested rear-arm instruction was not tested. Describing successful athletes does not demonstrate that copying their isolated elbow position improves another hitter

**B16b. Kuwabara et al. (2026), stride diversity.** [Primary journal abstract](https://sjsp.aearedo.es/index.php/sjsp/article/view/stride-strategies-collegiate-baseball-batters?articlesBySimilarityPage=14)

- 95 collegiate batters performed maximal tee swings with 3-D motion capture and force plates; stride width, direction and peak foot height were analyzed separately
- Width correlated weakly with bat-head speed (r = .328); height and direction did not significantly correlate with speed, although they related to other movement/force measures
- **A; a recent descriptive study, abstract-level review.** Dynamic stride is different from initial stance. Nonsignificant pairwise correlations do not prove statistical independence or irrelevance, and a cross-sectional correlation does not show the benefit of changing stride width. No MLB/live-pitch transfer or training effect was established

**B16c. Kim et al. (2026), leg kick versus toe tap.** [Open primary paper](https://e-kjab.org/archive/detail/338)

- Five active KBO players performed five tee swings per condition; 200-Hz marker capture and 1,000-Hz force plates, with each player's trials averaged before paired testing
- Some foot-contact angular velocities and lead-leg vertical force differed; bat speed did not significantly differ
- **M/E; actual task manipulation in professionals, but very small and not MLB.** Sequential conditions, multiple comparisons, familiar-technique differences and absence of incoming pitches limit inference; a null bat-speed result is not equivalence. Peak-force units/normalization need clarification before numeric reuse. This establishes neither an optimal strategy nor a long-term training benefit

**B17. Kinetic characteristics against different pitch speeds (2010).** [Open journal record](https://www.jstage.jst.go.jp/article/sobim/34/3/34_216/_article/-char/en)

- 29 university players hit three speed bands (75–80, 100–105 and 125–130 km/h); Vicon and force plates quantified body motion and ground forces
- Faster pitches changed available movement time, impulse and lower-body contributions to trunk rotation
- **M/A; pitch-speed manipulation below typical MLB fastball speed.** It motivates speed-conditioned coordination rather than a single ideal stride. Predictability, machine delivery and level restrict transport; no long-term training or MLB outcome was established

**B18. Kishita et al. (2020), elite live-batting gaze.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7739578/)

- Six NPB batters, three top-team and three farm-team players, faced former professionals; wearable eye tracking and optical head/bat motion capture
- Predictive saccades and head–bat relationships differed among players and with advance pitch-type information; saccade initiation varied approximately 80–220 ms before impact
- **M/A; elite Japanese professional evidence, not MLB.** Tiny groups, offseason setting and individual variability prohibit a universal perceptual deadline. Gaze direction is not a complete measure of attention or usable information, and advance-information conditions are not a coaching-effect trial

**B19. Nakashima et al. (2025), timing-error tolerance.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11985794/)

- 29 collegiate batters supplied laboratory dry-swing trajectories, combined with pitch-flight data in a geometric contact/timing analysis
- The study connects bat-path shape and pitch approach to a modeled window of permissible timing error
- **M/model; a useful mechanism, already in the main review.** Dry swings plus trajectory recombination do not establish how MLB hitters adapt in live at-bats or whether teaching a different path improves run value. Preserve the difference between modeled collision tolerance and observed perceptual/swing decision timing

### D. Ball physics, equipment and environment

**B20. Nathan et al. (2006), spin and flight.** [Author preprint](https://arxiv.org/abs/physics/0605041)

- Pitching-machine experiment covering 50–110 mph and 1,500–4,500 rpm, with high-speed tracking over about five metres plus total travel distance
- Fitted trajectories estimated lift and drag over the tested speed/spin range
- **M; direct ball physics, no athlete population.** Useful for physically defensible flight variables; not a universal mapping from rpm to “pitch quality.” Grip/seam effects, atmospheric conditions and differing balls require separate treatment. The cited version is a conference-submission preprint

**B21. Kensrud, Nathan & Smith (2017), oblique impact.** [Author manuscript](https://arxiv.org/abs/1610.03464)

- Apparatus collided a swinging bat with stationary baseballs/softballs; 63–88 mph bat speeds, high-speed video, ball speed/launch angle/spin and collision modelling
- Findings support tangential deformation and grip during impact rather than a purely rigid rolling model
- **M; strong for tested impacts, not a live batting intervention.** Baseball and softball results must remain separate; no MLB hitter sample. Impact geometry and equipment matter, and launch conditions cannot uniquely reconstruct the preceding full-body swing. Exact collision count was not verified in this focused abstract-level read

**B22. Nathan et al. (2011), ball storage and restitution.** [Author manuscript](https://arxiv.org/pdf/1009.2549)

- The humidity experiment conditioned 48 official MLB balls in eight groups across humidity conditions, then measured mass and cylindrical-impact restitution; additional temperature testing was performed
- Storage conditions altered collision properties. The paper's carry/home-run calculations involve assumptions translating laboratory impacts to game-speed contact and flight
- **M; a real physical mechanism, not a contemporary league-wide causal estimate.** Ambient humidity during flight and long-term humidity of stored balls are different exposures. Do not use old ball tests to assert a fixed modern park effect or a permanent baseball-manufacturing explanation

**B23. Callahan et al. (2023), temperature and home runs.** [Paper](https://journals.ametsoc.org/view/journals/bams/104/5/BAMS-D-22-0235.1.xml); [authors' replication repository](https://github.com/ccallahan45/Callahan-et-al_ClimateBaseball_2023)

- MLB panel of 114,417 games, 1962–2019, with a roughly 220,000-batted-ball analysis; weather regressions, launch-condition controls and climate-model attribution
- Warmer conditions were associated with more home runs, with weaker effects in closed-roof games, consistent with air-density physics
- **A supported by M; more persuasive than raw seasonal correlations, still not a randomized experiment.** Weather-station exposure, roster/era changes and environmental co-variation matter. Climate attribution is a distinct task from forecasting tomorrow's game. The repository is a reproducibility lead; its included Statcast records do not bypass original data rights

**B24. Card et al. (2025), pitch clock and UCL injury.** [Open publisher paper](https://journals.sagepub.com/doi/10.1177/23259671251366422)

- Retrospective public-record MLB comparison of 2021–2022 and 2023–2024; Table 2 accounts for 54 pre-clock and 58 clock-era cases. Inclusion required surgery, excluding diagnosed nonoperative tears
- Reported incidence per 1,000 innings was 0.63 versus 0.67, without a significant difference; clock-era cases accumulated more preinjury workload
- **A; hypothesis-generating, no proof of a protective or harmful clock effect.** Era comparisons co-vary with age, starter/reliever mix, velocity, other rules and reporting. Restricting secondary analyses to injured pitchers induces selection; time before injury is not itself a measure of tolerance. A null result is not equivalence

**B25. Song, Severini & Allada (2017), travel/circadian context.** [Open paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC5307448/)

- 46,535 MLB games, 1992–2011; schedules generated directional jet-lag proxies, with regression adjustment for team effects
- Travel-related performance associations were reported, especially after eastward travel
- **A; broad actual-game sample, coarse physiological measurement.** Actual flight times, individual sleep and adaptation were not measured; the one-hour-per-day adaptation rule is an assumption. This warrants schedule/rest features and sensitivity analysis, not diagnosing fatigue or attributing a specific mechanical change to jet lag

### E. Emerging measurement and proxy models

**B26. Moore et al. (2026), release metrics to elbow torque.** [Open paper](https://www.nature.com/articles/s44387-026-00112-3)

- 143 professional MLB/MiLB-roster pitchers, 2,984 pitches from bullpen testing; motion-capture torque targets with TrackMan/Rapsodo release inputs
- Leave-one-pitcher-out random forests reported RMSE 3.41 N·m and R² 0.94; load-dependent error remained. Conversion from normalized torque still needs body size
- **A/model; promising held-out-player validation.** It predicts a biomechanical surrogate, not future injury. Private confidential data and request-only code prevent reproduction here. Verify all preprocessing within folds, device harmonization, in-game external validity and high-load calibration before reuse. “Release” inputs arrive after the pitch; no pre-pitch claim is supported

**B27. Aguinaldo et al. (2025), markerless-system validation.** [Authors' institutional record](https://scholars.uky.edu/en/publications/assessing-the-accuracy-of-in-stadium-and-portable-multi-camera-ma/); [DOI](https://doi.org/10.1080/02640414.2025.2595411)

- Eighteen collegiate pitchers were captured simultaneously with Hawk-Eye, Theia3D and a marker-based reference
- Joint-position and metric agreement were evaluated with waveform, error, concordance and Bland–Altman methods; disagreement varied by variable/system
- **M; validation rather than performance/intervention evidence.** The public institutional abstract was inspected. Results from one camera configuration and college sample do not validate every stadium, speed, body angle or commercial output. Marker-based motion is itself a model-based reference, not direct tissue loading

**B28. Bright and colleagues (2026), broadcast-pose preprints.** [Pitch-type anticipation](https://arxiv.org/html/2603.04874v1); [injury screening](https://arxiv.org/html/2603.04864v1)

- Pitch-type paper: 119,561 professional pitch sequences, 229 pose-derived features, reported 80.4% accuracy; an 80/20 stratified random pitch split, not demonstrated held-out-pitcher/time testing
- Injury paper: paired validation on 13 pitchers/156 pitches; claimed AUC 0.811 in 7,348 pitchers. The recent Tommy John case count differs between the table (209) and narrative (167). Retrieved methods do not clearly specify a leakage-safe temporal injury split
- **E; research leads only.** Require independent, blinded pose validation, error by joint/event, stable case definitions, explicit prediction horizons, held-out organizations/seasons, calibration and licensed footage. A biologically plausible skeleton is not measured ground truth. Neither paper establishes preventive benefit from changing mechanics

## 5. Official measurements and research access

**D01. [Savant CSV documentation](https://baseballsavant.mlb.com/csv-docs).** `stand` records batting side, not stance. Release/flight, arm-angle and bat-path fields have different time meanings. In 2026, `plate_x`/`plate_z` move from front-of-plate to middle-of-plate and `sz_top`/`sz_bot` become ABS-defined. The “days until next game” fields are future information. Freeze a versioned dictionary, actual export headers and per-season completeness before analysis; the page alone does not establish a field's first available season, latency or reliable coverage.

**D02. [Official arm-angle surface](https://baseballsavant.mlb.com/leaderboard/pitcher-arm-angles).** Shoulder-to-ball orientation at release uses a horizontal reference, with data stated as available from 2020. It is not shoulder abduction, trunk tilt or a complete arm path.

**D03. [Official stance/intercept visualization](https://baseballsavant.mlb.com/visuals/batting-stance).** Displays hip-midpoint box depth/off-plate distance, foot spacing/orientation and nearest bat–ball intercept, including misses. These are genuine positioning observations, not values extracted from the handedness code. Preserve each measurement event and aggregation level.

**D04. [Official swing-path surface](https://baseballsavant.mlb.com/leaderboard/bat-tracking/swing-path-attack-angle).** Attack angle/direction describe sweet-spot travel at impact, while tilt summarizes the preceding 40-ms path plane. The site states bat tracking begins in the second half of 2023. Its “ideal” label is an operational category, not an individualized causal optimum.

**D05. [Official active-spin](https://baseballsavant.mlb.com/leaderboard/active-spin) and [spin-direction](https://baseballsavant.mlb.com/leaderboard/spin-direction-pitches) surfaces.** Candidate sources for separating movement-related spin from total rpm and comparing observed versus movement-inferred direction. Keep optical measurements, aerodynamic inference and residuals explicitly distinct. Use the already identified Smith/Smith seam-shifted-wake and Kagan/Nathan trajectory papers alongside these definitions; they answer physical questions, not the whole pitch-selection problem.

**D06. [Driveline OpenBiomechanics datasheet](https://github.com/drivelineresearch/openbiomechanics/blob/main/DATASHEET.md) and [project repository](https://github.com/drivelineresearch/openbiomechanics).** Current documentation reports 411 fastball trials/100 athletes and 677 swings/98 athletes, predominantly college with small MiLB/independent/high-school subsets. It contains laboratory marker/force data, not linked MLB games. Data/documentation use noncommercial share-alike terms plus an additional exclusion covering specified professional-sports/financial-analysis affiliations without separate licensing. Treat it as a measurement/reproduction candidate behind an explicit license/use-case gate. Reading the science remains useful regardless of current ingestion status.

## 6. Specific research-design requirements before implementation

### A. Do not infer an intervention from a prediction model

A statement such as “larger trunk tilt predicts higher velocity” does not identify the effect of instructing this pitcher to tilt farther. A player may change several linked segments, intended effort, grip or location. Required intervention evidence should specify the manipulation, compliance, within-athlete response, performance trade-offs and follow-up duration. Randomized/crossover training studies with sufficient washout and repeated baseline trials are preferable where feasible. Immediate laboratory changes cannot demonstrate long-term health benefit.

For a future observational analysis, draw the assumed causal graph first. For example, conditioning on velocity may estimate a mechanics association at fixed speed, whereas omitting velocity may include the pathway through speed. Those are different estimands. Do not automatically “control for everything,” especially variables measured after an intervention, after fatigue, or after injury onset.

### B. Fatigue needs a multidimensional state model

The useful conceptual decomposition is external exposure, internal response, output adaptation and remaining capacity. This is a research framework, not a fitted score:

- External exposure: number, intensity, type and spacing of all throws, including training and warm-ups
- Internal response: reported exertion, strength loss, EMG or physiological measurements when actually available
- Output adaptation: shifts in velocity, release, movement, location variability and coordination
- Capacity and prior state: anatomy, training history, previous injury and current recovery

Game-only public data observe only part of this system. A high-performing pitcher who remains in the game is a selected survivor; a fatigued pitcher removed early disappears from later-inning samples. Manager decisions and times-through-the-order effects must be treated explicitly. Use player-specific baselines and random slopes, predefine comparison pitch types, and retain both mean and variability changes. Report “workload-associated change” unless fatigue was directly measured.

### C. Injury modelling requires a different validation protocol

Prespecify whether the target is first UCL surgery, any arm injury, a particular diagnosis, days lost or roster availability. Use an at-risk cohort with valid exposure time, not only surgery cases. Time-varying predictors must precede the earliest plausible onset; public report dates can lag onset. Account for competing retirement/release, role changes and prior procedures. Freeze training before validation seasons, keep each pitcher out of leakage-prone folds, and report calibration, precision-recall, base rates and decision consequences as well as ROC AUC. Sensitivity to unmeasured training load and label incompleteness is mandatory.

Do not create a medical risk flag from public anomalies until the endpoint, population, measurement validity and clinical use have been independently assessed. The scientific inventory can still include those factors as unavailable or investigational.

### D. Mechanics datasets need stronger quality assurance than box scores

Record coordinate axes, handedness reflection, anatomical versus global angles, event detectors, units, frame rate, smoothing/filter cutoff, derivatives, joint-center model, inertial assumptions, normalization and uncertainty. Record whether values are directly tracked, algorithmically estimated, imputed, reconstructed or forecast. Validate within-session repeatability and between-system agreement. A repeatable bias is not accuracy, and tiny angle differences should not be declared real without a measurement-error analysis.

Do not count multiple papers using the same ASMI/Motus cohort as independent replications without checking participant overlap. Do not treat thousands of pitches from a small number of people as thousands of independent subjects. Broadcast camera, uniform, pitcher identity and pitch repertoire can leak into pose classifiers.

### E. Environment and regime validation

Use park-date geometry, roof state and a documented weather observation/forecast source. Resolve wind into the park coordinate system but recognize that local flow can differ from station measurements. Keep storage humidity, ambient humidity and ball-generation effects separate. Test whether environmental adjustments improve held-out calibration within parks and across parks, and whether the ball-flight model transfers across tracking eras. An all-season park coefficient fitted with future games cannot enter a true pregame forecast.

Maintain separate rule adoption calendars for MLB, MiLB, NPB and college. Test plate-plane/zone transformations using the 2026 definition boundary rather than mixing coordinates blindly. Catcher, umpire, defensive rules and bases can change the mapping from the same physical event to its scored outcome.

## 7. Recommended staged scientific scope

1. **Ready to specify, subject to source-use approval:** historical ball release/flight, arm-angle, stance, bat-path, environment and workload-proxy hypotheses with strict prediction-time boundaries
2. **Needs appropriate ground truth:** kinetic-chain/force/load models, grip/seam orientation, target-based command, gaze/vision, all-throw workload and physiological fatigue; identify licensed or newly collected measurements rather than fabricate them
3. **Needs stronger outcome/intervention evidence:** individualized injury-risk decisions, technique prescriptions, “optimal” separation/stance rules and fatigue-removal thresholds
4. **Experimental research only:** broadcast-derived clinical screening and release-to-torque transfer to in-game public data until externally reproduced

Deliverable stopping condition: a defensible scientific inventory and measurement/evaluation plan. This review intentionally makes no claim of a completed data pipeline, validated mechanics predictor, causal coaching engine or clinical injury model.

## Subsequent permitted source-inspection note

After this literature pass, the bounded noncommercial eligibility gate was cleared. [OPENBIOMECHANICS_AUDIT.md](OPENBIOMECHANICS_AUDIT.md) now verifies the actual small summary files, one session per athlete, outcome missingness, duplicated definitions, sensor differences and filename/target coupling. No model was fitted. This update does not change the scientific population/intervention limits or authorize unrestricted/commercial reuse.
