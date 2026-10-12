# American football mechanics and tactics: evidence and feasibility review

Research cut-off: 11 October 2026. Scope: professional American football, with lower-level biomechanical studies clearly separated. This is a targeted scoping review, not a registered systematic review or an implemented model. It extends the existing review of STRAIN, Feeling the Pressure, Going Deep, hypothetical completion, snap timing, defensive HMM/attention models, expected points, and nflWAR rather than repeating those papers.

## 1. Main findings

1. **Publicly available play-level data can support meaningful tactical modeling, but cannot measure most physical technique.** Personnel, quarterback alignment, box count, motion occurrence, previous-play history, and context are useful candidates. Hand placement, pad level, hip rotation, route breaks, defensive leverage, and block engagement require substantially richer observations.
2. **The most promising additions are interactions, not more box-score totals:** blocker–rusher matchup and help structure; receiver–defender relative geometry; ball–receiver–defender arrival-time relationships; and offensive motion–defensive response. The evidence is predominantly observational.
3. **Prediction time is part of every feature definition.** A route, pressure, rush count, completion window, or release mechanic measured after the snap is not an admissible same-play pre-snap predictor. Historical estimates of these can be admissible only when lagged and available by the prediction cutoff.
4. **Measurement time and publication time differ.** A formation exists at the snap, but the accessible FTN record is retrospective. FTN charting is published after games; 2023-onward participation is delivered after the postseason. The audited files support a retrospective at-snap experiment, not a demonstrated live data product.
5. **Do not import baseball mechanics directly into quarterbacks.** Football-specific studies measure the kinetic chain, but most accessible experiments are tiny youth/college/club samples under standardized conditions, not NFL throws under pressure.
6. **Rest, snap totals, and time of possession are exposure proxies, not physiological fatigue measurements.** NFL rest evidence is mixed and era-dependent. Wearable workload evidence does not validate a public-data individual injury score.
7. **Open papers and public code do not imply open underlying tracking data.** Several central studies use Kaggle competition data, licensed Hudl inputs, or private NFL tracking. Current project constraints preclude obtaining those through signup, mirrors, or proprietary feeds.

## 2. Targets and timing contract

The current project targets are (a) realized-dropback prediction and (b) pressure probability conditional on realized dropback, using the **final observable physical state at the snap**, represented retrospectively by charted fields. This is a film-review/scouting benchmark. The state is not information available before the offense chose its play, and the published files are not a demonstrated live feed or live play-call recommender. Physical observation, later charting/publication, and the earlier coaching decision are separate clocks. Maintain the following distinctions:

- **Realized dropback is not the coach's intended play call.** Audibles, RPO choices, scrambles, sacks, broken plays, and penalties can separate intent from recorded outcome. Label the model accordingly and document treatment of kneels, spikes, nullified plays, sacks and scrambles.
- **Pressure is not a pure offensive-line or pass-rusher grade.** Protection, coverage, quarterback movement, throw timing, route design, opponent strength and scorer definitions all contribute.
- **Conditional pressure is a conditional forecasting task.** Evaluating only observed dropbacks is reasonable for that estimand. It does not establish the causal effect of choosing pass versus run, and selection into dropback must not be ignored in causal interpretation.
- If an all-play pressure-risk quantity is wanted, use a separately validated two-stage decomposition: dropback probability multiplied by pressure probability conditional on dropback. Report both stages; do not treat non-dropbacks with false pressure flags as equivalent pressure opportunities.
- Freeze an explicit cutoff: pregame; before huddle; final observable pre-snap state; a fixed elapsed post-snap time; release; arrival; or play end. These are different experiments.
- A pre-snap task may use historical post-snap outcomes as lagged summaries. It may not use the current play's outcome, complete-game totals, later games, end-of-season ratings, later roster corrections, or future frames used in smoothing.

### Availability codes used below

- **P:** directly present or derivable in the already audited PBP/FTN/participation files, subject to release latency and field validation
- **J:** potentially obtainable without paid access through a separate official/public source or historical join; coverage, timestamp and rights still need audit
- **T:** requires player/ball tracking not present in the audited files; no approved comprehensive no-signup data route established
- **V:** requires licensed video/manual charting, calibrated pose estimation, IMUs, force plates, or private team measurements
- **H:** candidate hypothesis, not a demonstrated causal or predictive benefit for the current target

The tables are an operational feature-design proposal informed by the evidence capsules below. They are not claims that every listed variable has independently proven NFL predictive value.

## 3. Measurable factor inventory

### A. Blocking, pass rush, orientation, leverage

| Factor | Operational measurement | Earliest observation | Current feasibility and target relevance | Important limitations |
|---|---|---|---|---|
| A1. Trench alignment | Lateral/longitudinal rusher offset from blocker and QB; inside/outside shoulder; width of edge alignment | Final pre-snap frame | T; direct candidate for pressure. Personnel counts are only P proxies | Player position label does not reveal actual alignment or assignment |
| A2. Blocker–rusher assignment | Probability that blocker b is responsible for rusher r at each frame | Pre-snap prior; post-snap posterior | T; central to attribution, historical matchup ratings | Assignment is not proof of physical contact; HMM smoothing can use future frames [L01–L02] |
| A3. Help/protection structure | Overlapping two-blocker engagement, chip duration, slide direction, TE/RB staying in versus releasing | Some intent pre-snap; realized help post-snap | T/V; historical help tendencies may predict pressure | Current-play double team is post-snap; help is assigned preferentially to stronger rushers |
| A4. Horizontal leverage | Blocker position projected onto rusher–QB line; lateral offset from that line; relative orientation encoded by sine/cosine | Pre-snap or within-play snapshot | T; interpretable geometric candidate | Shoulder-pad orientation is not foot, hip, hand or head pose; velocity direction is different from body orientation |
| A5. Stance and pad level | Two-/three-/four-point stance; trunk inclination; knee/hip flexion; helmet and pelvis height | Pre-snap | V; mechanistic hypothesis for get-off and protection | No validated NFL pressure-effect estimate from the small laboratory studies [L03–L04] |
| A6. First-step/get-off | Time from snap to movement onset; first-step displacement and direction; first 0.5-second acceleration | Post-snap | T/V; future within-play pressure task, not current pre-snap predictor | 10 Hz gives coarse timing; filtering must not look ahead; false starts and cadence matter |
| A7. Hand usage/contact technique | Strike onset, hand location, arm extension, independent hand use, grip/hold, rusher move and counter | Post-snap | V; coaching hypothesis | Not recoverable from a single 2D point per player. Blocking drill checklist is not an NFL outcome validation [L05] |
| A8. Sustain/shed time | Engagement duration or time-to-disengagement; define competing pass-release/play-end censoring | Post-snap | T; excellent alternative target if data become lawful/available | Late successful protection has no opportunity to be tested after a quick release; do not treat every censored block as a win |
| A9. Pocket shape/escape lane | QB-centered protected area; nearest-threat distance and closing speed; edge/interior lane occupancy | Post-snap | T; pressure/escape modeling; historically lagged summaries only for current task | QB action jointly changes geometry; more area need not mean safer passing options |
| A10. Opponent-adjusted talent | Shrunk blocker/rusher effects from prior encounters, with role and help terms | Pregame after prior data release | P coarse pressure histories; T for actual head-to-head effects | Teammates, QB, scheme and unequal matchups remain confounded; verify source timing [L01–L02] |

### B. Routes, coverage, passing windows

| Factor | Operational measurement | Earliest observation | Current feasibility and relevance | Important limitations |
|---|---|---|---|---|
| B1. Receiver deployment | Eligible-player identity, attached/slot/wide position, split width, bunch/stack spacing, boundary versus field side | Final pre-snap frame | P for identity/personnel; T/V for exact geometry. Relevant to dropback and pressure | Personnel grouping does not identify formation topology |
| B2. Route shape and break | Trajectory curve/cluster; stem depth; break time, curvature, deceleration and exit speed | Post-snap; full route after play | P primary-receiver route label; T all-receiver trajectories | Route family is an outcome/annotation, not the pre-snap playbook call; variable-length and aborted routes [L06] |
| B3. Separation at a specified event | Minimum receiver–defender Euclidean distance at snap, release, or arrival | At named event | T; target/coverage/completion/YAC relevance | Always state event. Nearest defender may not be assigned defender; catch-only/target-only samples are selected |
| B4. Relative leverage and closing | Signed inside/outside and deep/underneath offset, relative velocity, defender facing direction | Pre-snap or within-play | T; better candidate than distance alone | Orientation can be absent even when a paper has x/y tracking; mixed man-match zones resist binary labels [L07] |
| B5. Coverage responsibilities | Probabilities of man/zone/match, safety help, double team and defender–receiver matchup | Prior before snap; revealed after snap | P realized coverage label only; T inferred pre-snap responsibilities | Do not insert realized coverage into a pre-snap model; uncertainty and annotator disagreement are material |
| B6. Defensive reaction/disguise | Change in shell/assignment probability after motion or snap; response delay to offensive movement | Motion interval or post-snap | T; possible pre-snap feature only from frames already seen | Some disguise is only identifiable from later action; mark oracle analyses separately |
| B7. Safe passing window | Receiver arrival-time/reachable-area advantage over all defenders, also constrained by ball travel | Within-play/release | T; QB decision/completion task | Openness does not equal best expected value; simple constant-speed physics omits reaction, jumping and trajectory uncertainty [L08–L10] |
| B8. Spacing and complementary routes | Separation among eligible receivers, overlap of occupied zones, defenders displaced by non-target routes | Post-snap | T/V; untargeted-player contribution | Route combination and defensive policy determine spacing; one primary route label is insufficient |

### C. Running lanes and tackle geometry

| Factor | Operational measurement | Earliest observation | Current feasibility and relevance | Important limitations |
|---|---|---|---|---|
| C1. Front, box and numbers | Box count, defensive personnel, offensive backfield count, defender location by gap | Pre-snap | P counts; T gap alignment. Useful tactical covariates | Box definition/scorer differences; a linebacker can be a rusher or cover player |
| C2. Run concept/point of attack | Inside/outside zone, power/counter, puller and intended gap; distinguish intended from realized direction | Playbook intent before snap; externally charted post-snap | P coarse realized run location; V true concept | Run location is not admissible for same-play pre-snap run/pass prediction |
| C3. Lane width and time-to-close | Width of a connected viable runner corridor; minimum opponent arrival time along candidate paths | Post-snap, often handoff | T; rushing/YAC development target | Pure Voronoi distance ignores speed, turning cost, blocker contact and carrier choice [L13] |
| C4. Carrier decision/cut | Chosen path versus feasible alternatives; heading change, deceleration/reacceleration, decision delay | After handoff | T/V; player evaluation hypothesis | Counterfactual defender/blocker responses are unobserved; maximum simulated yards overstates actionable opportunity |
| C5. Tackle opportunity | Ball-carrier distance, approach angle, relative speed, pursuit interception time, sideline/first-down geometry | Post-possession, before contact | T; tackle probability/YAC task | Opportunity windows must be defined independently of future tackle labels [L11–L12] |
| C6. Shared tackling contribution | Change in forward velocity over contact windows; credit among nearby defenders | Contact through play end | T; retrospective defensive attribution | Nearness is not contact; runner voluntarily slowing or being forced sideways can produce attribution error [L11] |
| C7. Physical tackling technique | Head placement, shoulder contact point, body height, wrap, leg drive, torso rotation | Contact | V; biomechanical/coaching analysis | Cannot infer from 2D center points. NFL case-control injury evidence and NCAA tackle-success evidence are distinct [L26–L27] |
| C8. Momentum/escape support | Mass × velocity, carrier–tackler relative momentum, number/location of helpers and blockers | Within-play | T plus roster mass proxy | Roster mass is approximate; momentum alone is not impact force or injury risk. Closing speed does not remove technique/context confounding [L26] |

### D. Quarterback mechanics and decisions

| Factor | Operational measurement | Earliest observation | Current feasibility and relevance | Important limitations |
|---|---|---|---|---|
| D1. Starting platform | Under center, shotgun, pistol; depth and handedness | Pre-snap | P categorical alignment; T depth; J handedness. Direct tactical input | Do not equate shotgun with pass or under-center with run |
| D2. Drop and platform stability | Drop depth/steps, hitch count, displacement/speed, base width, plant timing, off-platform throw | Post-snap | T gross movement, V lower-body pose | Current out-of-pocket flag is post-snap; ball release is not foot plant |
| D3. Release sequence | Stride-foot contact → maximum shoulder external rotation → ball release; shoulder/elbow/trunk/pelvis angles and angular velocities | During throw | V; not present in PBP or standard 2D tracking | Distinguish joint angles, timing, ball speed and arm slot; small non-NFL experiments [L14–L15] |
| D4. Release duration versus time-to-throw | Throw initiation-to-release duration versus snap-to-release elapsed time | During/at throw | P snap-to-release only; V true arm-action duration | Calling time-to-throw 'release speed' confounds route development, cognition and mechanics |
| D5. Ball delivery | Release height, speed, launch angle, spin, trajectory, target-relative placement | Release to arrival | V/T with ball tracking; P air yards is only a coarse result | Air yards are not 3D air distance, velocity, launch angle or accuracy |
| D6. Decision alternatives | Option values of each receiver, scramble or throwaway, at each observed decision time | Within-play | T for modeled options; P read_thrown only retrospectively | Target prediction is behavior imitation, not proof of optimality. Full-play best option uses hindsight [L09–L10] |
| D7. Perception/read progression | Gaze dwell, order of reads, coverage recognition accuracy, decision reaction time | Pre-/post-snap dependent | V eye tracking/controlled tests; P categorical read outcome is not gaze | Small youth training effects do not establish NFL decision advantage [L16] |
| D8. QB–protection interaction | Movement toward/away from pressure, escape direction, pocket drift, route availability at release | Post-snap | T; central confounder of pressure grades | Fast release can avoid a recorded pressure; pressure also causes earlier throws |

### E. Personnel, motion, tempo, coach and rules

| Factor | Operational measurement | Earliest observation | Current feasibility and relevance | Important limitations |
|---|---|---|---|---|
| E1. Personnel/continuity | Position counts, actual players, extra OL, prior shared snaps, substitutions since prior play | Pre-snap | P; high-priority hypothesis for both targets | Historical position coding changes; nominal positions do not equal current assignment |
| E2. Motion/shift | Motion occurrence; player identity, path, speed at snap, across/return/orbit-type movement, multiple-player shift | Before/at snap | P occurrence; T/V type/trajectory | FTN is_motion combines before-snap and at-snap motion; cannot recover type or snap synchronization from one Boolean |
| E3. Snap cadence/timing | Motion-onset-to-snap interval; within-QB timing variability; play-clock time at snap | At snap | T/V fine timing; P game-clock/no-huddle proxies | Actual pre-snap duration is not game-clock decrement; the clock stops and broadcast/administrative pauses vary |
| E4. Tempo and prior sequence | No-huddle; previous plays' context/outcomes; trailing pass propensity with shrinkage | Pre-snap | P; high-priority addition beyond static context [L22] | Use only prior plays; sequence persistence may reflect score, clock or personnel rather than hidden psychology |
| E5. Play-action/RPO/screen/deception | Called concept versus executed fake/choice; historical rates by personnel | Intent before snap; observed execution after snap | P historical rates, not current execution flags | A feature can be known to offense but unavailable to external forecaster; RPO realized branch is the target-like variable |
| E6. Coach and system | Head coach/OC/DC identities, tenure, verified play-caller changes, prior situational policy | Pregame | J identities; P team-season proxy and past behavior | Coach, roster and franchise are intertwined. Risk preference is context dependent, not fixed personality [L23] |
| E7. Score/clock/risk policy | Down, distance, field position, score differential, timeouts, clock, era-specific rules | Pre-snap | P; necessary adjustment | WP/EPA model versions can import future training information; betting lines are optional and require their own timestamp |
| E8. Rule/enforcement regime | Season-specific timing, substitution, motion, contact/holding and overtime regime; known officiating context | Pregame | J official rules; P observed past penalties | Same-play penalties are outcomes. Referee association can reflect assigned games and team style; rule text is not measured enforcement [D06] |

### F. Workload, health and environment

| Factor | Operational measurement | Earliest observation | Current feasibility and relevance | Important limitations |
|---|---|---|---|---|
| F1. Recent game exposure | Prior snaps, touches, consecutive on-field plays, drives, previous 7/28-day totals | Pre-snap | P/J depending player participation; plausible controls | Exposure is not workload intensity or fatigue; opportunity/talent and prior injury drive snaps |
| F2. External/internal load | Prior accelerometer PlayerLoad, high-speed distance, collision counts; heart rate/RPE or recovery measures | Prior training/game measurements | V; inaccessible in public panel | Proprietary algorithms, practice omission and device variation; do not recreate a medical ACWR threshold from snap counts [L17] |
| F3. Rest and travel | Days since last game and opponent difference, travel distance/time-zone change, kickoff in home time | Pregame | P/J; feasible low-priority sensitivity block | Team itinerary, adaptation and actual sleep unobserved; bye benefits change by labor regime [L18,L20–L21] |
| F4. Availability and continuity | Public practice/report status, inactives, substitutions and returning player identity as known at cutoff | Pregame/pre-snap | J current coverage/timestamp audit required | Reports are not complete clinical diagnoses; later reports leak. Do not infer injury from motion or create clinical risk claims |
| F5. Wind/weather | Wind speed/direction/gusts, temperature, precipitation, humidity; interaction with roof and passing direction | Forecast before game; observation before prediction | P coarse game weather; J official station series | Stadium bowl wind differs from airport; final observed game weather leaks into pregame forecasts [L24,D05] |
| F6. Surface/traction | Historical surface subtype, wetness, temperature, shoe/stud configuration, field maintenance | Pregame/event-specific | P/J coarse surface; V traction/shoes | Turf effects on injury do not prove effects on pressure/dropback; venue and surface changes confounded [L19] |
| F7. Heat and recovery | Wet-bulb/heat exposure, cumulative exertion, hydration/core temperature | Environment pregame; physiology private | J environmental proxy; V physiology | Injury/medical screening target is outside current scope; ambient temperature alone is not personal heat strain |

## 4. Evidence capsules and primary-source register

Evidence ratings refer to relevance to the current model, not merely publication venue: **B** = useful NFL observational/methodological evidence; **C** = small or limited-population mechanistic/descriptive evidence; **D** = early proposal/abstract or indirect target evidence. None establishes a universal causal coefficient transferable into the project.

### L01. Opponent-adjusted blocking/rushing ratings (2026, preprint) — B

[Pipping-Gamón et al., full paper](https://arxiv.org/html/2604.01491). Authors report 153,138 interactions, 33,283 pass plays and 266 games from 2021 Hudl tracking. Ridge Bradley–Terry models jointly estimate blocker/rusher effects, with a double-team term. The win label uses relative distance to QB within 2.5 seconds. Reported log-loss gains over strong matchup baselines are small; the severity comparison's interval reaches zero. Relevant for opponent adjustment and hierarchical shrinkage, not for treating sack totals as ability. Help, QB timing and teammate effects remain limitations. All-Pro alignment is face validation. **Data private/licensed; at-snap adoption requires lagged ratings, not realized engagement.**

### L02. Probabilistic pass-blocking assignments (September 2026, preprint) — B, early

[Brahme et al., v2](https://arxiv.org/html/2609.33664v2). Uses 2021 weeks 1–8 tracking to infer frame-level assignments from position and orientation. Outputs include attention, switching, disengagement/survival and pocket-space contribution. The paper reports 87.5% agreement with PFF's main rusher assignment across 44,037 matched blocker-plays; this is not contact detection or causal skill validation. Standard forward–backward assignment probabilities are retrospective: a forecasting adaptation would require causal filtering. The paper itself notes assignment versus actual impediment ambiguity. **Competition tracking plus external charting; no approved full data route.**

### L03. Knee loading in lineman movements (2015) — C

[Lambach et al., primary abstract](https://pubmed.ncbi.nlm.nih.gov/25536366/). Fifteen NCAA linemen performed three unloaded blocking movements, walking and jogging. Motion analysis and inverse dynamics estimated knee moments/forces. Jogging had larger peaks, while blocking peaks occurred at greater knee flexion. This supports measuring stance and load separately. It does not estimate the effect of pad level on NFL block success, nor represent collisions against an opponent. **Laboratory measurements, unavailable in PBP.**

### L04. Starting stance (2014) — C

[Bonnechere et al., primary abstract](https://pubmed.ncbi.nlm.nih.gov/24790500/) and [publisher paper](https://www.jssm.org/volume13/iss2/cap/jssm-13-423.pdf). Twenty-five men, including twelve football players, performed different sprint starts. Vicon measured head/trunk orientation, head rise timing and speed. The study offers a biomechanical rationale for stance/vision trade-offs. It did not prospectively observe NFL concussion or blocking outcomes, so its injury interpretation is not a validated prediction rule. **Use to define measurements, not to prescribe an optimal NFL stance.**

### L05. Pass-blocking behavioral coaching (2010) — C

[Stokes et al., original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2938948/). Five relatively inexperienced high-school linemen were evaluated with a ten-step checklist and a multiple-baseline coaching intervention. Video feedback and acoustical guidance improved measured execution, with some game assessment. Mean observer agreement was 90% in practice and 88% in games. The useful contribution is operational coding and reliability assessment. Selection of the least-skilled players, tiny sample and developmental population rule out inference about NFL technique effects. **Video/manual measurement; no public NFL equivalent.**

### L06. Route identification (2019 preprint / 2020 JQAS) — B

[Chu et al.](https://arxiv.org/abs/1908.02423). Model-based curve clustering represents variable-length receiver trajectories with Bernstein/Bézier curves. The reported sample contains 34,698 routes on 6,963 pass plays. It supports route-conditioned comparison and all-receiver deployment analysis. Learned clusters are not necessarily the coach's playbook labels; complete observed route shape is post-snap. **Tracking required; public FTN primary-receiver route fields cannot reproduce all-player geometry.**

### L07. Unsupervised pass coverage (2019 preprint / 2020 JQAS) — B

[Dutta, Yurko and Ventura](https://arxiv.org/html/1906.11373). Movement/distance features over event-defined intervals generate soft man/zone assignments. The analyzed set has 6,712 passes and 16,316 feature vectors. Orientation is explicitly unavailable in their sample, an important caution against assuming every tracking release has it. Interpretation is based on qualitative examination rather than comprehensive expert ground truth. Some informative variables occur after the pass. **Useful for measurement design and uncertain labels; not validation of pre-snap coverage prediction.**

### L08. Safe passing regions (2026, Journal of Big Data) — B

[Schilling et al.](https://link.springer.com/article/10.1186/s40537-026-01416-6). Combines receiver, defender and ball reachable regions in 17,643 passes from 2018. One configuration reports 89% completion for classified-safe throws versus 59% otherwise, but safe throws are a small, selected subset and usually shorter. This is not a randomized decision-policy gain. The physics baseline simplifies initial velocity and shared athletic parameters; the data-driven version uses direction/speed-conditioned observed reach. **Needs competition tracking and a new time-causal evaluation; safe is not synonymous with best situational choice.**

### L09. DeepQB (2019 Sloan paper) — B

[Burke, official conference page](https://www.sloansportsconference.com/research-papers/deepqb-deep-learning-with-player-tracking-to-quantify-quarterback-decision-making-performance) and [paper](https://assets-global.website-files.com/5f1af76ed86d6771ad48324b/5f6d394ebce99d0d6cdb767c_DeepQB.pdf). Uses more than two NFL seasons and a passing-state snapshot to predict target choice. Reports 60% cross-validated target identification. Matching the predicted receiver is associated with higher completion, but this is behavior prediction, not identification of an optimal policy. Design intent, coverage and difficulty confound that comparison. **Private tracking/charting, within-play task; not replicable with FTN read_thrown.**

### L10. QB options and execution (2021 online / 2023 issue) — B

[Reyers and Swartz, author paper](https://www.sfu.ca/~tswartz/papers/nfl.pdf). Considers pass and non-designed running options, using field ownership, sideline distance, rush distance, QB speed and expected points. The cleaned 2017 sample has 6,727 plays; competitive-state filtering reduces pass/run cases further. Hypothetical arrival uses modeling assumptions, including fixed ball speed. The evaluation also considers options up to 0.5 seconds after the actual decision, making that version retrospective. **Strong factor inventory, but counterfactual action response and temporal validation remain open.**

### L11. Fractional tackles (2024) — B

[Nguyen et al.](https://arxiv.org/html/2403.14769). Analyzes 5,539 run plays in 2022 weeks 1–9. Contact windows use a 1.5-yard proximity threshold; contribution measures unrecovered loss of carrier forward velocity, shared across involved defenders. This captures assistance omitted by discrete tackle credits. It does not establish actual body contact or remove selection into tackle opportunities. Forward motion can change for reasons other than a defender's physical action. **Post-contact retrospective metric; cannot be a pre-snap feature.**

### L12. NFLNet tackle prediction (2025) — B/D

[Original journal paper](https://openjournals.uwaterloo.ca/index.php/vsl/article/download/6370/6238/27500). Compares neural architectures using 2022 tracking and short-horizon tackle/contact examples. Graph connectivity and relative positions improve reported classification; the graph model uses a state 0.5 seconds before the event. The paper balances tackle and first-contact examples and reports a 70/20/10 split, without establishing game-/season-held-out deployment calibration. First contact is not universally an unsuccessful tackle. Thus reported accuracy is not an unconditional in-game tackle probability guarantee. **Competition tracking required; validation design needs strengthening before adoption.**

### L13. Space ownership via trajectory planning (2019 Big Data Bowl proposal) — D

[Burris, official NFL-hosted paper](https://operations.nfl.com/media/3665/big-data-bowl-burris.pdf). Proposes reachability using current direction/speed plus acceleration, deceleration, turning ability and maximum speed. It improves the conceptual basis over nearest-player ownership. The official indexed abstract was accessible, but the complete PDF fetch failed during this pass; no quantitative validation claim is made here. **A useful lane-modeling hypothesis, not an independently validated professional run-block metric.**

### L14. IMU quarterback sequencing (2025) — C

[Labbe et al., original article](https://ijspt.scholasticahq.com/article/142488-kinematic-sequencing-of-the-football-pass-using-inertial-motion-analysis). Eight healthy right-handed quarterbacks, four high-school and four collegiate, made nine throws each at 10/20/30 yards. Sensors estimated knee, trunk, pelvis, shoulder and elbow angles at defined throwing events. This is descriptive sequencing, not a demonstrated accuracy, velocity, injury or NFL performance model. Small developmental sample, no game pressure, sensor drift and movement artifacts limit translation. **Supports a pose/IMU feature ontology only.**

### L15. Trunk–pelvis/shoulder relationships in QBs (Aso et al., January 2026) — C

[Original PMC article](https://pmc.ncbi.nlm.nih.gov/articles/PMC12966902/) and [PubMed record](https://pubmed.ncbi.nlm.nih.gov/41799375/), DOI 10.1016/j.jseint.2026.101630. Eleven Japanese university/club quarterbacks made five maximal 30-yard throws each; 240 Hz side-view video supplied PitchAI kinematics. Trunk/pelvis angles at stride-foot contact correlated with shoulder angles at maximum external rotation. The planned sample was 29; only eleven were recruited. The authors explicitly state that PitchAI joint-angle validity has not been established for QB throws; baseball validation does not establish football validity, especially for shoulder angles. Nongame correlations without kinetic measurements cannot establish injury causality or NFL performance benefit. The ordinary PMC fetch encountered a challenge, but the indexed original article exposed methods, results and limitations, which were reviewed. **Measurement ontology and an important validation warning, not a validated mechanics score.**

### L16. QB video decision training (2020) — C

[Original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7077253/). A small high-school quarterback intervention uses temporal occlusion and feedback to assess decision reaction time and accuracy. Benefits vary by task; modification of decisions did not show improvement. Familiarity with team film and expert-answer ambiguity matter. This supports measuring perceptual skill separately from throw mechanics. **It does not validate NFL gaze inference from helmet orientation or public read labels.**

### L17. Wearable workload and soft-tissue injury (2019/2020) — B for association, D for present target

[Li et al., original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6931176/). A single NFL team over two seasons contributed 101 injuries with complete wearable/clinical data. Practice accelerometry-derived workload changes were associated with injury; game-day GPS load was not measured. The often-cited acute/chronic threshold is observational and does not justify replacing sensor load with snap counts. Practice exposure, contact mechanism, prior fitness, missing observations and injury-related load changes complicate interpretation. **Private clinical/wearable data; neither an individual injury predictor nor direct pressure evidence.**

### L18. Short rest and observed injury (2020 full study) — B, indirect

[Perez et al., primary abstract](https://journals.sagepub.com/doi/abs/10.1177/0363546520919989). Uses 2013–2016 official gamebooks, all teams and 2,846 recorded injuries. Short-rest games did not show higher recorded injury rates than normal rest. This is a useful counterexample to automatically converting a short week into a large fatigue penalty. Gamebook ascertainment, player selection and exposure differ from total soreness, recovery or all clinical injury. **Schedule-derived rest is feasible; the physiologic effect is not directly observed.**

### L19. Surface and lower-extremity injury (2018 online / 2019 issue) — B, indirect

[Mack et al., primary abstract](https://journals.sagepub.com/doi/abs/10.1177/0363546518808499). All 32 NFL teams' 2012–2016 surveillance data associate synthetic turf with higher lower-extremity injury per play (adjusted framework; reported overall IRR 1.16). Full article is restricted, so the assessment is abstract-level. Surface generation, cleat–surface interaction and venue context matter. **Supports recording historical surface accurately; not a quantified direct effect on dropback choice or pressure.**

### L20. Rest differential and era (2024 preprint) — B, indirect

[Lopez and Bliss](https://arxiv.org/abs/2408.10867). Bayesian state-space analysis finds no significant contemporary bye/mini-bye competitive advantage and traces an earlier bye benefit to the pre-2011 labor-agreement era. Abstract and official source were reviewed; the HTML endpoint yielded supplementary material rather than a complete main-paper review. **Use rest as a hypothesis with era interactions and shrinkage, not a fixed bonus or proof that fatigue is absent.**

### L21. Circadian alignment (2013) — B, indirect/older era

[Smith et al., original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3825451/). Reviews 106 East–West evening NFL games and 293 daytime comparison games over 1970–2011, with point-spread comparison. Finds an evening advantage consistent with a circadian hypothesis. Actual sleep, body-clock phase and travel itinerary are unmeasured. Prime-time selection, older eras and team composition limit current per-play transfer. **Kickoff relative to home timezone is measurable; physiological misalignment is inferred.**

### L22. Sequential play-call prediction (2020 preprint / 2021 journal) — B, direct

[Ötting, full preprint](https://arxiv.org/html/2003.10791). Team-specific HMMs fit 2009–2017 PBP and evaluate 2018, reporting 71.5% accuracy. The model accounts for latent passing propensity and observed game context; personnel was a stated missing covariate. Its chronological season test is a useful design precedent, although its run/pass label and sample exclusions must be reconciled with the project's realized-dropback target. **Public PBP permits a clean sequential baseline without reproducing the paper's Kaggle download.**

### L23. Context-dependent coach risk preferences (2023 preprint; later journal publication) — B, indirect

[Sandholtz et al.](https://arxiv.org/abs/2309.00756). Uses 2014–2022 PBP and inverse MDP optimization to estimate fourth-down risk preferences. Preferences vary with field region and era. The model assumes observed choices are near-optimal for an unknown risk measure; it does not reveal a coach's psychology or independently isolate coaching skill. **Motivates situational policy and coach/era interactions rather than a universal coach coefficient.**

### L24. Weather and offensive performance (2014 senior thesis) — D

[Zipperman, university repository](https://scholarship.claremont.edu/cmc_theses/830/). Examines 2002–2013 NFL game data for wind, temperature, home/away conditions and visiting-team adaptation. This is open undergraduate research, not a peer-reviewed causal result. The original repository abstract was accessible; full-PDF fetch failed. **Weather is a plausible measured covariate, but this review does not endorse a universal wind threshold or transport an aggregate yardage effect into per-play pressure.**

### L25. Exposure-normalized load (2026) — C, supplementary

[Lever et al., primary publisher record](https://www.tandfonline.com/doi/full/10.1080/02640414.2026.2705698). Indexed publisher methods report 232 athletes at one NCAA FBS program across ten seasons. The design examines total and per-snap external load with positional groups and athlete/game effects. The full-page fetch failed, so no effect-size claim is adopted. **Useful reinforcement that exposure should be normalized and role-specific; not NFL physiological validation.**

### L26. Physical tackle technique and NFL concussion (Sherwood et al., 2025) — B, health outcome

[Primary abstract](https://pubmed.ncbi.nlm.nih.gov/40037391/) and [author manuscript, Ulster University](https://pure.ulster.ac.uk/ws/portalfiles/portal/218512307/Tackle_Techniques_and_Characteristics_Associated_With_a_Concussion_in_Tackling_Players_in_the_National_Football_League.pdf), DOI 10.1177/03635465251321005. Multi-view video coded 20 characteristics for 51 tackler concussions in 2015–2019 and 96 controls matched using tracking trajectories/closing speed. Helmet-led contact was associated with higher concussion odds (OR 5.18, 95% CI 1.87–14.33); primary helmet versus shoulder loading had OR 4.61 (1.41–15.05). Closing speed remained associated despite matching. Measurements include head placement, wrap, foot separation, support feet, torso inclination and primary contact region. Cases were restricted to one-on-one tackles, excluding boundary/goal-line proximity, special teams, post-turnover plays and ground-caused concussions. Correlated features, rare categories and imperfect matching limit causal interpretation; NFL funding/affiliations are disclosed. **Direct professional physical-technique evidence, but selected case-control injury evidence is not a prospective individual risk model, tackle-success model or pre-snap pressure feature. Raw video/tracking are private.**

### L27. Physical tackle technique and NCAA success (Hirase et al., 2023) — C, performance outcome

[Original open publisher paper](https://journals.sagepub.com/doi/pdf/10.1177/23259671231182968), DOI 10.1177/23259671231182968. Three reviewers examined 1,000 consecutive solo defensive tackle attempts from eight SEC universities in October–December 2021. They coded head angle, contact above/below waist, method and success; mean interrater kappa was 0.718. Head-up attempts succeeded in 76.2% versus 55.1% for head-down; inside-shoulder attempts succeeded in 93.2% versus 41.6% for arm attempts. No tackler injuries were recorded. Video exclusions, unadjusted comparisons and situational selection are crucial: an out-of-position defender may attempt an arm tackle precisely because a shoulder tackle is unavailable. **Defines reproducible physical technique and tackle-success labels, but observational college associations do not establish an NFL causal technique effect or injury prevention benefit. Article license is CC BY-NC-ND; video access/reuse is a separate question.**

### Backward-citation leads kept separate from reviewed evidence

- [Fleisig et al., 1996, DOI 10.1123/jab.12.2.207](https://doi.org/10.1123/jab.12.2.207): original comparison of baseball pitching and football passing. Publisher fetch returned 403; indexed abstract describes high-school/college samples. Retain for later full primary review, not as an NFL coefficient source.
- [Bohnert, 2016 university thesis](https://uknowledge.uky.edu/khp_etds/32/): kinematic, kinetic and EMG analysis of collegiate quarterback throwing. Repository abstract reviewed, full thesis not reviewed here.
- [2023 physiological/biomechanical scoping review](https://pmc.ncbi.nlm.nih.gov/articles/PMC10098592/) was used only to locate original stance, lineman and throwing studies. Its broad conclusions are not substituted for primary evidence.

## 5. Data access, license and reproducibility register

| Source | What is actually available | Rights/access conclusion | Decision |
|---|---|---|---|
| D01. [FTN charting loader](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) | Play-level subset from 2022 onward; loader describes charting within 48 hours after games | CC BY-SA 4.0; attribute FTN Data via nflverse | Eligible historical source; not a live pre-snap feed |
| D02. [Participation loader](https://nflreadr.nflverse.com/reference/load_participation.html) and [schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) | 2023-onward FTN participation arrives after postseason; older source differs | Loader states CC BY-SA 4.0 and source-specific attribution | Eligible retrospective source; retain season/source indicators and publication cutoff |
| D03. [FTN dictionary](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html), [participation dictionary](https://nflreadr.nflverse.com/articles/dictionary_participation.html) | Exact schema, definitions and source transitions | Official documentation, no signup | Pin retrieved version; do not infer raw tracking from aggregate fields |
| D04. [nfl-elo code](https://github.com/WhartonSABI/nfl-elo) | MIT source; README requires six licensed inputs | Code license does not license Hudl data. README warns Git history contains older derived data | Methods reference only; do not mine history for inputs or clone restricted data |
| D04b. [Matchup_Identifier](https://github.com/IshTheCoder/Matchup_Identifier), [tackle](https://github.com/qntkhvn/tackle) | Public author code pages | No standard license verified on inspected root pages; underlying competition data separate | Link/reference only; copying/reuse needs explicit rights verification |
| D05. [NOAA GHCN hourly](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly) | Official station observations, documentation and bulk PSV/parquet access | Public no-signup page and bulk route; per-product metadata/conditions still must be retained | Candidate weather join, not downloaded/audited in this task |
| D06. [2025 official NFL rulebook](https://operations.nfl.com/media/ntif5hxb/2025-nfl-rulebook-final.pdf) | Season-specific primary rules | Read/reference; no blanket redistribution right assumed | Use correct historical season; do not replace 2023 rules with 2026 rules |
| Kaggle Big Data Bowl datasets | Study-specific tracking subsets and rules | Sign-in/competition terms fall outside current constraint; a paper calling data 'public' does not remove these | No download, account creation, API token or mirror |
| NFL's small official 2017 sample | Previously located project sample | Prior audit did not verify standard repository license or comprehensive coverage | Do not generalize a demonstration sample into season-scale mechanics data |
| Biomechanics/medical datasets | Study aggregates, methods; raw subject data generally not found in verified no-signup licensed feeds | Article access does not authorize raw data access or clinical inference | Literature-only evidence at present |

**Reproducibility warning:** the current nfl-elo README describes training weeks 1–15, testing weeks 16–18 and updated outcome masks/weights, whereas L01's paper describes ordered 80/20 splitting and different outcome construction. A later reproduction must pin manuscript version, code commit and input schema together. No code in these external repositories was run in this review.

**Weather source update:** NOAA identifies GHCNh as the replacement for ISD. Legacy ISD remains useful for historical reproduction, but do not promise an unchanged active ISD pipeline. Verify GHCNh station identity, historical coverage, flags, timestamp, roof status and stadium distance before use.

## 6. Field-level safeguards from the audited data

The existing audit files in this directory establish joined coverage; this review does not replace them or rerun the source downloads. The project reports 32,813 valid 2025 plays in its selected joined population.

- Do not silently merge pre-2023 NGS participation with 2023-onward FTN labels: formation, personnel granularity, pressure and route definitions/source coverage change.
- `offense_personnel`/`defense_personnel` are position counts, not a geometric formation map, player task or protection call.
- `is_motion` indicates motion before **or** at the snap. Motion speed/type, mover identity and synchronized snap timing are missing.
- `read_thrown` is a charted progression category. The official dictionary states `0` means primary read from 2023 onward; 2022 primary reads appear as NA. Thus a blanket `0 = missing` rule is wrong. Conversely, valid coding on eligible passes does not make non-pass rows meaningful read observations.
- `qb_location=0` and `starting_hash=0` are missing/sentinel values in the project's audited 2025 cohort. This is a **column- and cohort-specific** finding; it does not override the valid primary-read meaning of `read_thrown=0` or authorize blanket zero recoding. Retain raw values and explicit per-column cleaning rules.
- `route` names the primary receiver's realized route, not every route or intended play call.
- `time_to_throw` is snap-to-pass-release duration; it is not arm-action release duration.
- `number_of_pass_rushers`, `n_pass_rushers`, `n_blitzers`, `was_pressure`, realized coverage, route, play-action, screen, RPO, out-of-pocket, read, drop and catchability annotations all require timing/definition review. They cannot be admitted merely because they are present in the joined table.
- `ngs_air_yards` is a legacy field absent for 2024 onward according to current documentation. PBP `air_yards` is a different measurement route and remains post-snap.
- Separate true absence, structural non-applicability, source-uncovered play and bad/sentinel code. In particular, a pressure Boolean populated on all play types does not define pressure opportunities.
- No raw x/y trajectories, player orientation time series, joint angles, hand placement, force, gaze or ball spin are present in the audited feature source.

## 7. Research-to-experiment priorities, with stopping gates

### Tier 1: immediately testable retrospective tactical hypotheses

1. Establish a time-valid context baseline and honest target label, then add QB alignment, offensive/defensive personnel, backfield/box count, motion occurrence and no-huddle.
2. Test interactions with football meaning: personnel × down/distance; QB alignment × backfield count; motion × personnel; offense/defense personnel mismatch; box count × yardline/distance. Use shrinkage and ablations rather than an exhaustive unregularized interaction expansion.
3. Add prior-only team/QB/opponent rates and sequential context. Compare a simple exponentially weighted/trailing rate with a sequential model before adopting HMM complexity.
4. Evaluate known-player/lineup continuity only after ID/position/availability checks. An observed player on the current snap is a valid physical state for an at-snap experiment, but the public historical file's delayed publication still prevents claiming live readiness.

**Development-selection gate:** decide whether to retain a feature block using only the prespecified chronological development/selection folds, their log loss/Brier score, calibration, subgroup behavior and uncertainty. The final test set must never determine feature retention, tuning, model choice or calibration. Freeze the selected block/model before final scoring, and retain/report failed final-test ablations rather than redesigning against that test. Accuracy alone and in-sample feature importance are insufficient. Cluster resampling by game and, where feasible, evaluate unseen teams/coaches/players or new-season transfer as prespecified diagnostics.

### Tier 2: feasible after an additional source audit

- Historical rest, timezone/travel and stadium/weather/surface blocks
- Public injury/inactive status and verified coach/play-caller identities
- Lagged public weekly tracking aggregates, if rights, minimum-attempt censoring and release date are verified

**Gate:** no source is assumed complete merely because a loader exists. Audit 2023–2025 coverage and archive/version timestamps. For current injury coverage, inspect actual files; the documentation alone is not proof that every year is populated. Keep these as modest controls/hypotheses, not a causal 'fatigue' or health score.

### Tier 3: richer mechanics only after data rights and sensor validity gates

- Blocker–rusher assignment and engagement survival
- Pre-snap alignment/leverage and motion-response geometry
- All-receiver route/coverage probabilities
- Within-play lane, passing-window and tackle models
- QB pose/throw sequencing and tackle/blocking contact technique

**Gate:** obtain a clearly permitted dataset with sufficient games, outcomes and aligned tracking. Verify sample frequency, coordinate orientation, left/right normalization, measurement error and synchrony. Pose work additionally needs calibrated views, occlusion/error assessment and joint-specific validation. Broadcast extraction is not a rights workaround.

### Claims that should remain out of the initial model

- 'Lower pad level causes fewer pressures' from unloaded NCAA drills
- 'Motion causes passing success' from unadjusted motion/no-motion outcome comparison
- 'A 2.5-second block win is ground-truth player skill'
- 'A nearest defender is the responsible coverage player'
- 'Snap count equals fatigue' or 'short week necessarily causes more injury'
- 'Large separation at catch was known before the snap'
- 'Quick time-to-throw proves fast arm mechanics or superior processing'
- 'A model's most likely target is the optimal choice'
- 'A generic turf label establishes an individual injury probability'

## 8. Search method, backward chaining and omissions

Searched on 11 October 2026 through web-indexed arXiv, original journal/publisher pages, PubMed/PMC, official NFL-hosted research, university author repositories, author GitHub repositories and official nflverse/NOAA documentation. Queries combined professional/American-football terms with mechanics and tactics; soccer and Australian-rules results were screened out. Search snippets were used for discovery, with original sources opened where available. Review depth is explicitly marked when restricted to an original abstract/indexed extract.

Representative exact query strings used:

- `American football offensive line blocking biomechanics study stance technique force`
- `NFL player tracking tackling geometry tackle probability research paper`
- `American football quarterback throwing biomechanics kinematics college professional study open access`
- `NFL player tracking running lanes pitch control run blocking research paper`
- `site.arxiv.org NFL running lanes space control rushing tracking orientation`
- `site.arxiv.org NFL route separation receiver leverage motion coverage tracking`
- `NFL player workload fatigue short rest injury study open access NFL`
- `NFL weather wind precipitation passing performance study paper`
- `site.arxiv.org "NFL" "motion" pre-snap`
- `site.pmc.ncbi.nlm.nih.gov National Football League circadian travel performance short rest`
- `"DeepQB" "Burke" 2019 pdf`
- `"What is the Safest Sprint Starting Position" Bonnechere DOI`
- `"Knee joint loading during lineman" DOI`
- `"quarterback" "visual search" "decision" study`
- `"American football" "run" "Voronoi" paper`
- `NFL coaching play calling run pass causal inference paper arxiv`
- `NFL play calling predictability personnel formation shotgun study paper`
- `site.operations.nfl.com 2025 rulebook offensive shift motion one player`
- `"NFL" "fatigue" "performance" "plays" research`
- `"Kinematic Sequencing of the Football Pass" site.ijspt.scholasticahq.com`
- `site.nflreadr.nflverse.com dictionary ftn charting CC BY SA`
- `site.ncei.noaa.gov integrated surface database global hourly access noaa`
- `NFL tackling technique concussion head placement study`
- `"At-Risk Tackling Techniques" "NCAA"`
- `"PMC12966902" "limitations"`

Backward/forward citation paths actually followed:

1. Physiological/biomechanical scoping review → Lambach lineman loading, Bonnechere stance, historical Fleisig throwing comparison, quarterback thesis/IMU studies
2. Fractional Tackles → DeepQB, route clustering, coverage clustering and original tackle code
3. Safe Passing Regions → Reyers–Swartz quarterback options → hypothetical completion / field ownership distinctions
4. New blocking-assignment paper → STRAIN, assignment geometry, PFF validation and author repository
5. Opponent-adjusted blocking paper → author code → licensed-input requirement and manuscript/code mismatch
6. Play-call HMM → earlier play prediction and personnel limitations; coach risk-preference paper used for contextual policy rather than physical mechanics
7. Older weather/ISD references → current official NOAA GHCNh replacement documentation
8. NFL tackle-technique study → author-deposited manuscript and matched-control definitions; NCAA technique study → original slow-motion coding, reliability and situational limitations
9. Aso QB paper → original indexed methods/limitations and PitchAI validation citation; baseball validation was not treated as QB validation

Exclusions and limits:

- No paid products, new accounts, Kaggle acceptance, tokens, outreach, unlicensed dataset mirrors, or restricted-data extraction
- No reliance on SEO content, betting advice or coaching anecdotes as validation
- No claim that this pass exhausts NFL special-teams mechanics, receiver catching biomechanics, footwear engineering, injury epidemiology or sport psychology
- Small college/youth studies retained only where they define a needed measurement or expose an NFL evidence gap
- Publication year and studied season are kept separate; an October 2026-accessible paper can study 2017–2022 data
- Football-rule primary text is contextual documentation, not experimental evidence
- This review made no core code changes and did not run or claim to reproduce any literature model

## 9. Bottom line

Proceed, after research review, with a narrowly named **retrospective pre-snap tactical prediction experiment** using the verified public panel. Preserve a separate, explicit mechanics roadmap. The literature supports richer interactions and better measurement, but the current files do not justify representing footwork, leverage, hand technique, gaze or throwing kinematics as observed professional data. A sophisticated model cannot repair an unobserved or mistimed variable.
