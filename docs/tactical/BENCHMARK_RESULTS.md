# Five-sport tactical benchmark results

Status: all seven prespecified final evaluations completed and passed independent numerical verification. The consolidated numerical audit binds every report, selection and source identity. Distribution remains subject to separate source-specific privacy/release review.

## Main findings

The added information helped in some settings, had small or uncertain value in others, and worsened the laboratory baseball estimate. Final results did not change the designated procedures, feature sets or comparison rules. These are measured retrospective associations, not causal coaching effects.

| Study and fixed comparison | Evaluation support | Reference loss | Candidate loss | Difference and uncertainty | Interpretation |
|---|---:|---:|---:|---|---|
| WSL recorded defense + geometry R versus geometry G, calibrated | 1,855 shots / 72 matches | 0.323582 | 0.309887 | -0.013695; 95% match-cluster interval [-0.020777, -0.006477] | Lower loss; fixed descriptive yardstick met |
| ACB nearest-defender D versus geometry/clock C | 708 geometry-supported releases / 5 sequential games | 0.672584 | 0.665462 | -0.007122; no headline interval | Favorable in only 3/5 games; exploratory yardstick not met |
| MLB sequence versus context logistic, calibrated swing target | 705,223 delivered pitches / 2,430 games | 0.658826 | 0.658472 | -0.000354; 95% game-cluster interval [-0.000411, -0.000293] | Small gain, below the fixed 0.001-nat practical threshold |
| NFL full at-snap block C versus game-context A logistic, calibrated | 32,813 plays / 272 games | 0.573844 | 0.522502 | -0.051342; 95% game-cluster interval [-0.057899, -0.044665] | Lower loss; game/week sensitivity and fixed yardstick met |
| Professional tennis serve direction | Four 2025 serve/corpus cells, detailed below | Cell-specific | Cell-specific | Only men’s second serves met the fixed improvement rule | First-serve history references retained; women’s second-serve gain inconclusive |
| Adult baseball lab: body angles + pitch context versus pitch context, equal-athlete MAE | 571 trials / 82 held-out athletes | 5.925761 mph | 6.125848 mph | +0.200087 mph; 95% athlete interval [-0.039580, 0.457915] | Worse point estimate; no demonstrated useful improvement |
| Collegiate tennis execution B1 versus pooled B0, equal-player joint NLL | 548 non-let attempts / 8 held-out players | 2.629705 | 2.445547 | -0.184158; exploratory 95% player interval [-0.243560, -0.113282] | Favorable within this small practice sample; no professional/temporal transfer claim |

All classification losses above are natural-log loss per eligible case, lower is better. Baseball laboratory MAE is mph; the tennis execution loss is an observed-data density score with bounce coordinates in metres. These unlike losses must not be ranked across sports. Bootstrap intervals are conditional on saved predictions and do not include all selection, sensor, source-bias or repeated-team uncertainty.

## What the factors actually added

- Soccer: recorded defense improved the geometry-only model on identical shots. Partial recorded defenders are not full tracking; the result does not establish that moving a particular defender causes the change. The common evaluation cohort happened to contain 1,855 full and matched cases; earlier source coverage differs.
- Basketball: nearest-defender context lowered pooled loss, but its sign was favorable in only three of five games. The predeclared four-of-five consistency requirement failed. The wider all-release population contains 719 releases, including 11 fixed pooled fallbacks for absent geometry. Quality-restricted cohorts remain sensitivity analyses, not replacements for the 708-release primary cohort.
- Baseball events: recent pitch-outcome codes contributed only a small swing-prediction increment. Conditional contact is a secondary target: 336,314 swings, calibrated log loss 0.539116 to 0.538010; difference -0.001106 with interval [-0.001271, -0.000938]. A pitch-outcome sequence does not reveal pitch type, stance or trajectory.
- NFL: much of the logistic gain came from formation/personnel (A 0.573844 → B 0.523804); the motion/box/hash addition produced the smaller B → C change to 0.522502. The full tree comparison also remains reported below; it did not replace the predesignated primary logistic procedure.
- Baseball mechanics: the held-out-athlete mean reference had MAE 5.845214 mph, below both fitted feature models. The four measured foot-plant angles did not demonstrate transferable extra predictive value under this fixed small-cohort design. That is not evidence that biomechanics never matters.
- Tennis execution: B1’s equal-player bounce-location error was 1.060489 m versus 1.159488 m for B0, on the 437 measured bounces. Net-censored attempts remain in the 548-attempt joint score; they receive no invented bounce. The eight-player sample and overlapping training folds make the interval exploratory.

## Professional tennis: retain the development choice

| Cell | Eligible serves / matches | Designated method | Calibrated B1 loss | Designated loss | Difference; adjusted 98.75% match interval | Fixed improvement rule |
|---|---:|---|---:|---:|---|---|
| A1_m | 91,753 / 575 | B1 | 0.918142 | 0.918142 | 0.000000; [0.000000, 0.000000] | Not met |
| A1_w | 71,404 / 565 | B1 | 1.037946 | 1.037946 | 0.000000; [0.000000, 0.000000] | Not met |
| A2_m | 34,175 / 575 | N | 1.031664 | 1.012053 | -0.019611; [-0.026122, -0.013424] | Met |
| A2_w | 27,163 / 565 | N | 0.998930 | 0.994443 | -0.004486; [-0.009604, 0.000329] | Not met |

A1/A2 mean first/second serve; m/w identify the source corpus. The first-serve B1 reference was selected during development and remained the designated procedure even where another method has a slightly lower final loss. Men’s second-serve N improved on B1 with the prespecified adjusted interval and at least 0.005-nat threshold. Women’s second-serve N did not clear that threshold or uncertainty rule. Tournament/year and four-week sensitivities remain in the saved source report; no narrowest interval was selected.

The men’s second-serve logistic family is unavailable: one C=0.1 fit was interrupted and permanently consumed, and the remaining C=1/10 fits exhausted permitted convergence attempts. It was not replaced. Other failed candidates and the conservative interruption CPU debit are documented in the tennis card and recovery guide.

## Full prespecified procedure summaries

Raw and calibrated streams are both retained. A calibration fit does not guarantee better final loss or establish perfect probability reliability. The local aggregate workbench displays fixed-bin reliability and sparse/empty support; Brier alone is not called a calibration test.

### Soccer

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| full_A_raw | 1,855 | 0.360023 | 0.102932 | 88.36% |
| full_B_raw | 1,855 | 0.330055 | 0.095874 | 88.36% |
| full_G_calibrated | 1,855 | 0.323581 | 0.093850 | 88.68% |
| full_G_raw | 1,855 | 0.323563 | 0.093848 | 88.73% |
| matched_A_raw | 1,855 | 0.360026 | 0.102933 | 88.36% |
| matched_B_raw | 1,855 | 0.330038 | 0.095875 | 88.36% |
| matched_G_calibrated | 1,855 | 0.323582 | 0.093846 | 88.68% |
| matched_G_raw | 1,855 | 0.323562 | 0.093844 | 88.68% |
| matched_R_calibrated | 1,855 | 0.309887 | 0.090047 | 88.68% |
| matched_R_raw | 1,855 | 0.310214 | 0.090123 | 88.84% |

### Basketball: all_releases_with_A_fallback

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| A | 719 | 0.690700 | 0.248722 | 55.63% |
| B | 719 | 0.667596 | 0.237265 | 62.45% |
| C | 719 | 0.672375 | 0.239711 | 58.28% |
| D | 719 | 0.665362 | 0.236263 | 60.36% |

### Basketball: event_geometry

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| A | 708 | 0.691194 | 0.248966 | 55.51% |
| B | 708 | 0.667731 | 0.237330 | 62.43% |
| C | 708 | 0.672584 | 0.239815 | 58.19% |
| D | 708 | 0.665462 | 0.236313 | 60.31% |

### Basketball: raw_consistent_0p1ft

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| A | 658 | 0.695525 | 0.251103 | 54.41% |
| B | 658 | 0.671610 | 0.239209 | 61.85% |
| C | 658 | 0.677396 | 0.242119 | 57.29% |
| D | 658 | 0.669971 | 0.238553 | 59.57% |

### Basketball: raw_consistent_1ft

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| A | 687 | 0.693173 | 0.249942 | 55.02% |
| B | 687 | 0.669756 | 0.238305 | 62.15% |
| C | 687 | 0.675071 | 0.240995 | 57.79% |
| D | 687 | 0.667539 | 0.237406 | 59.97% |

### Basketball: raw_consistent_and_directly_detected_0p1ft

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| A | 587 | 0.694129 | 0.250419 | 54.68% |
| B | 587 | 0.672333 | 0.239536 | 61.67% |
| C | 587 | 0.675270 | 0.241107 | 58.26% |
| D | 587 | 0.663704 | 0.235641 | 60.65% |

### Baseball: contact_given_swing

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| constant_raw | 336,314 | 0.541998 | 0.178315 | 76.78% |
| constant_calibrated | 336,314 | 0.542004 | 0.178317 | 76.78% |
| context_logistic_raw | 336,314 | 0.539110 | 0.177303 | 76.78% |
| context_logistic_calibrated | 336,314 | 0.539116 | 0.177305 | 76.78% |
| context_table_raw | 336,314 | 0.539980 | 0.177619 | 76.78% |
| context_table_calibrated | 336,314 | 0.539986 | 0.177621 | 76.78% |
| history_table_raw | 336,314 | 0.539376 | 0.177393 | 76.78% |
| history_table_calibrated | 336,314 | 0.539381 | 0.177394 | 76.78% |
| sequence_logistic_raw | 336,314 | 0.538002 | 0.176894 | 76.78% |
| sequence_logistic_calibrated | 336,314 | 0.538010 | 0.176897 | 76.78% |

### Baseball: swing

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| constant_raw | 705,223 | 0.692081 | 0.249467 | 52.31% |
| constant_calibrated | 705,223 | 0.692116 | 0.249485 | 52.31% |
| context_logistic_raw | 705,223 | 0.658801 | 0.233460 | 60.41% |
| context_logistic_calibrated | 705,223 | 0.658826 | 0.233468 | 60.36% |
| context_table_raw | 705,223 | 0.659211 | 0.233632 | 60.26% |
| context_table_calibrated | 705,223 | 0.659236 | 0.233641 | 60.28% |
| history_table_raw | 705,223 | 0.659033 | 0.233555 | 60.33% |
| history_table_calibrated | 705,223 | 0.659053 | 0.233563 | 60.30% |
| sequence_logistic_raw | 705,223 | 0.658446 | 0.233292 | 60.48% |
| sequence_logistic_calibrated | 705,223 | 0.658472 | 0.233300 | 60.42% |

### American football

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| constant_raw | 32,813 | 0.672509 | 0.239751 | 60.14% |
| context_raw | 32,813 | 0.597659 | 0.207631 | 63.96% |
| context_calibrated | 32,813 | 0.597577 | 0.207555 | 63.96% |
| logistic_A_raw | 32,813 | 0.573710 | 0.195364 | 69.01% |
| logistic_A_calibrated | 32,813 | 0.573844 | 0.195338 | 69.00% |
| logistic_B_raw | 32,813 | 0.524302 | 0.173893 | 74.94% |
| logistic_B_calibrated | 32,813 | 0.523804 | 0.173937 | 74.82% |
| logistic_C_raw | 32,813 | 0.522672 | 0.173501 | 74.85% |
| logistic_C_calibrated | 32,813 | 0.522502 | 0.173469 | 74.84% |
| tree_A_raw | 32,813 | 0.531713 | 0.180835 | 71.05% |
| tree_A_calibrated | 32,813 | 0.531793 | 0.180890 | 71.01% |
| tree_B_raw | 32,813 | 0.496542 | 0.165194 | 75.77% |
| tree_B_calibrated | 32,813 | 0.496646 | 0.165150 | 75.80% |
| tree_C_raw | 32,813 | 0.486352 | 0.161738 | 75.93% |
| tree_C_calibrated | 32,813 | 0.486625 | 0.161829 | 75.88% |

### Professional tennis: A1_m

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| B0_calibrated | 91,753 | 0.929737 | 0.574951 | 48.01% |
| B0_uncalibrated | 91,753 | 0.929423 | 0.574772 | 48.01% |
| B1_calibrated | 91,753 | 0.918142 | 0.570091 | 49.72% |
| B1_uncalibrated | 91,753 | 0.917765 | 0.569959 | 49.72% |
| L_calibrated | 91,753 | 0.916561 | 0.569045 | 50.06% |
| L_uncalibrated | 91,753 | 0.916219 | 0.568713 | 50.06% |
| N_calibrated | 91,753 | 0.917328 | 0.569043 | 49.94% |
| N_uncalibrated | 91,753 | 0.916586 | 0.568763 | 49.94% |

### Professional tennis: A1_w

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| B0_calibrated | 71,404 | 1.053086 | 0.638571 | 42.53% |
| B0_uncalibrated | 71,404 | 1.052381 | 0.638200 | 42.53% |
| B1_calibrated | 71,404 | 1.037946 | 0.629543 | 44.71% |
| B1_uncalibrated | 71,404 | 1.038004 | 0.629640 | 44.71% |
| L_calibrated | 71,404 | 1.033971 | 0.627243 | 44.83% |
| L_uncalibrated | 71,404 | 1.033890 | 0.627215 | 44.83% |
| N_calibrated | 71,404 | 1.034989 | 0.627757 | 44.84% |
| N_uncalibrated | 71,404 | 1.034960 | 0.627722 | 44.84% |

### Professional tennis: A2_m

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| B0_calibrated | 34,175 | 1.070028 | 0.647606 | 41.29% |
| B0_uncalibrated | 34,175 | 1.070504 | 0.647862 | 41.29% |
| B1_calibrated | 34,175 | 1.031664 | 0.622638 | 46.93% |
| B1_uncalibrated | 34,175 | 1.032208 | 0.622899 | 46.93% |
| N_calibrated | 34,175 | 1.012053 | 0.609760 | 48.82% |
| N_uncalibrated | 34,175 | 1.012431 | 0.609906 | 48.82% |
| L_uncalibrated | — | unavailable | unavailable | unavailable |
| L_calibrated | — | unavailable | unavailable | unavailable |

### Professional tennis: A2_w

| Procedure | Cases | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| B0_calibrated | 27,163 | 1.047241 | 0.632500 | 46.73% |
| B0_uncalibrated | 27,163 | 1.047131 | 0.632449 | 46.73% |
| B1_calibrated | 27,163 | 0.998930 | 0.603244 | 49.69% |
| B1_uncalibrated | 27,163 | 0.998832 | 0.603217 | 49.69% |
| L_calibrated | 27,163 | 0.994220 | 0.601519 | 49.85% |
| L_uncalibrated | 27,163 | 0.994005 | 0.601342 | 49.85% |
| N_calibrated | 27,163 | 0.994443 | 0.602741 | 49.11% |
| N_uncalibrated | 27,163 | 0.994678 | 0.602890 | 49.11% |

### Adult baseball mechanics

| Procedure | Equal-athlete MAE (mph) | Mean athlete RMSE (mph) | Trial MAE (mph) | Trial RMSE (mph) |
|---|---:|---:|---:|---:|
| augmented | 6.125848 | 6.809169 | 6.100403 | 8.033531 |
| context | 5.925761 | 6.639354 | 5.899852 | 7.872903 |
| mean | 5.845214 | 6.526891 | 5.803572 | 7.801103 |

Macro RMSE here means the mean of each athlete’s RMSE, not the square root of a pooled athlete-mean MSE. All procedures use the same 571 trials and 82 athletes.

### Collegiate tennis execution

| Procedure | Joint NLL, equal player | Joint NLL, attempt weighted | Net Brier, equal player | Bounce error, equal player (m) | Observed 90% ellipse coverage, equal player |
|---|---:|---:|---:|---:|---:|
| B0 | 2.629705 | 2.638956 | 0.159494 | 1.159488 | 89.77% |
| B1 | 2.445547 | 2.468955 | 0.157854 | 1.060489 | 90.55% |

Joint/net metrics use 548 non-let attempts; bounce/ellipse metrics use 437 measured bounces, each across eight players. Nominal-versus-observed ellipse coverage is a diagnostic, not established calibration or a promise for a new athlete. No per-player, per-fold or pseudonymous performance records are published.

## Engineering, failures and limits

- Fixed global selection commitment: `31f0720d46d6029d0a2c8635a09e60495746e2a53f5b5a7a1f6e6df8db60881d`. The final batch was separately approved against this commitment and its independent pre-evaluation review.
- ACB used exactly ten prespecified past-only evaluation refits. Other tasks used frozen procedures. No score-based replacement, new feature grid, recalibration or additional evaluation fit was introduced.
- Two baseball C=3 sequence selection candidates failed the 1,000-iteration limit; the remaining selected refits/calibrations completed under the 38-operation budget. Tennis’s 41 reserved slots include nine convergence warnings and the consumed interrupted attempt. Failures were not hidden by larger retries.
- Before final execution, 598 repository tests passed and 68 lead-recorded protected original forecast files remained byte-identical. Independent review separately checked a broader 416-file protection inventory.
- This tactical extension has source/cache, gate, serialization and saved-prediction checks. It has not yet had a clean independent source-to-model refit replication. The original four-sport package’s earlier reproduction is separate evidence.
- All final periods are performance-blind after source QA, not fully human-blind or prospective. Retrospective charting, missing factors, sensor coupling, small cohorts and selection bias remain.
- Browser-rendered visual QA was blocked by the environment. Functional/DOM tests passed; rendered layout, accessibility and browser compatibility still require local visual inspection.
- Source notices, noncommercial/share-alike restrictions and participant privacy apply. Raw rows, tactical weights and individual lab predictions are excluded from the controlled distribution.

## Comparison with other systems

These studies include matched-case count, rating/history, logistic, boosted-tree and regularized regression references where their reviewed protocols permit them. Those comparisons answer the specific targets above. The preserved original package includes its separate Laya experiment (worse probabilistic loss in all four match-outcome samples) and a limited historical FiveThirtyEight MLB diagnostic with uncertain provenance/timing. Neither is an equivalent tactical benchmark. No verified same-case, as-issued commercial archive covers these seven new targets; no closed-source or enterprise-superiority claim is made.

## What a next study would need

Use a newly registered period or new population before testing additional changes. Useful measurement gaps include professional pitch trajectories and stance, verified completion/publication timing, independently validated tracking/contact alignment, broader ACB games, and larger multi-session biomechanics cohorts. A new study may test a stronger method, but this already-inspected final set cannot become its untouched proof. See the factor inventories for the evidence behind those priorities.
