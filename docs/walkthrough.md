# Learning walkthrough: be able to explain the project

This project was built with substantial AI assistance. Running and understanding
it is the next step; don't claim independent mastery because code exists.

## 1. State one concrete use case

A tennis matchup comparison: estimate both players' chance of winning from
historical strength, surface history, recent form and tournament-start ranks.
Show the actual input differences, a reliability plot and the limitations. The
system should help ask better questions, not invent a recommendation to bet.

Run `python -m sportslab analyze --sport tennis`. Explain the number of events,
players and dates, and why retirements/walkovers were excluded. That exclusion
makes the target conditional on completed matches.

## 2. Follow one row

Open sportslab/adapters/tennis.py and locate `_completed_score` and `a_is_winner`.
Find how stable IDs define sides before the outcome is mapped. Why would simply
using the CSV's winner as player A make accuracy meaningless?

Then open sportslab/features.py. Find the strict availability comparison. Why
is tournament-start +21 days conservative? Why isn't row order a match timestamp?

## 3. Reproduce before changing

Run the tests, then scripts/reproduce.sh. Open reports/tennis/evaluation.json.
Locate the train, calibration and test date ranges; chosen hyperparameters;
all five backtests; and raw input hashes. Explain why final test data cannot be
used to choose the best C, number of leaves or calibration temperature.

## 4. Compare the right numbers

A constant-prior baseline predicts the same distribution every time. Elo is a
much stronger baseline based on earlier results. Read reports/RESULTS.md and
explain why beating the constant baseline is easier than beating calibrated Elo.
Why does soccer's selected model have lower log loss but lower accuracy than Elo?
Why can temperature calibration improve validation loss and worsen test loss?

## 5. Test the information boundary

Run `python -m unittest discover -s tests -p test_core.py -v`.
Read the test that changes current/future scores. Explain why earlier feature rows
must remain identical. Read the suspended-game test and sketch a timeline with
original date, completion date and the next prediction.

## 6. Make one controlled research extension

Suggested next experiments, each using new future or properly nested evaluation:

- Tennis: compare ranking-only, Elo-only and combined features, surface by surface
- Baseball: add starting-pitcher form with verifiable announcement timestamps
- NFL: model ties explicitly instead of conditioning them away
- Soccer: study draw calibration and promoted teams' cold starts

Write your hypothesis before training. Keep failed experiments. Repeatedly tuning
against either published V1 or V2 holdout turns it into development data; obtain a
fresh prospective holdout before calling an extension an improvement.

## 7. Explain the limits in an application or interview

A truthful summary: “I’m working through an AI-assisted sports analytics project.
It uses real historical data, chronological splits and leakage checks for four
sports. I’m learning to compare predictions with strong baselines and evaluate
probabilities rather than just accuracy.”

Only expand that description with work you have actually done and can explain.
Do not claim an independent production deployment or superiority over other
students' projects without a same-task, same-data benchmark.

## 8. Trace the stronger benchmark

Read `docs/v2/PROTOCOL.md` before `reports/v2/RESULTS.md`. Find the all-four
selection freeze and explain why an ensemble is still reported as the main model
if another family has a better test score. Compare the ensemble with the refitted
V1 recipe on the same matches, not V1's accuracy from different seasons.

For a practical path through the evidence and interface, see
[the project guide](PROJECT_GUIDE.md).
