# SportsLab: what to inspect first

## The useful question

For a hypothetical pre-event matchup, how strongly do historical results support
each outcome, and how trustworthy have similar probabilities been?

Tennis is a concrete starting point: compare overall and surface strength, recent
form and pre-tournament rankings. Keep the actual feature differences visible,
then inspect held-out reliability. These factors describe model inputs, not causal
proof that a player will win. A model can confidently be wrong.

## Five stops through the repository

1. **Results:** `reports/v2/RESULTS.md` compares every prespecified model family on
   the same newer matches. Read the paired difference interval, not only the best
   looking accuracy. `reports/RESULTS.md` preserves the original experiment.
2. **Protocol:** `docs/v2/PROTOCOL.md` fixes the candidate set, chronology, ensemble
   and evaluation before test scoring. The global freeze binds all four sports.
3. **A match's information boundary:** `sportslab/features.py` and
   `experiments/v2/features.py` allow only earlier available results. Same-day
   games do not update one another. Suspended MLB games wait for completion;
   tennis results wait until 21 days after the tournament-start proxy.
4. **Evidence:** development/evaluation JSON files preserve configurations,
   dates, metrics, reliability-bin counts and hashes. The source manifest ties
   these to documented inputs. Tests deliberately change future outcomes.
5. **Use:** after reproduction, `scripts/analyze_matchup.py` produces a guarded
   hypothetical matchup analysis from the frozen models and verified history.
   It refuses incomplete benchmark releases and incompatible artifacts.

## Read a probability correctly

If a model assigns 70% to side A, that does not mean the prediction is 70% certain
to be accurate in every setting. Calibration asks whether many comparable 70%
forecasts win about 70% of the time. The reliability plots provide a historical,
finite-sample check. Sparse bins can look noisy. A better Brier score alone does
not establish good calibration.

Log loss penalizes probability assigned to the observed outcome; confident wrong
forecasts are costly. Accuracy ignores the difference between 51% and 99% for the
same predicted winner. Soccer has three classes; its losses should not be ranked
against binary tennis losses as if they were the same task.

The scenario's base-model probability range measures disagreement. It is not a
confidence interval. The benchmark's weekly-bootstrap interval describes an
approximate aggregate performance difference, not one match's outcome.

## Understand the comparison record

- V1 established a smaller transparent baseline. Its final holdout was then known
- V2 used a newer period, with its models frozen before scoring it. A refitted V1
  recipe predicts exactly the same V2 matches, making the improvement comparison
  meaningful. Changing years alone does not demonstrate progress
- Laya was tested on a separately frozen 800-row V1 subset. Its fixed-label output
  did not prevent incorrect or poorly calibrated probabilities. The documented
  zero-shot result does not determine what a future sports-fine-tuned model can do
- Commercial comparison is limited by access to archived as-issued forecasts.
  A partial preserved FiveThirtyEight MLB archive is explicitly a diagnostic,
  not a complete market ranking

## What would make this deployment-ready?

A verified live feed and fixture identity contract; reliable timestamps for every
input; secure artifact loading; automated source-change handling; monitored data
quality and drift; rollback/version policies; incident ownership; and prospective
performance evidence. The monitoring design is documented, but those services
are not deployed by this repository.

The frozen historical models omit important information such as confirmed MLB
starters, NFL injuries and tennis injury context. Do not turn that limitation into
an invented explanation or guaranteed recommendation.

## How to present your contribution honestly

This implementation and its initial research were substantially AI-assisted. To
make it your own learning project, reproduce the experiment, trace one row, explain
one leakage test, interpret one negative result, and write one new hypothesis
before testing it. Keep a short dated learning log with commands, observations and
your changes. Only claim skills you can demonstrate.

A sound application description is: “I am developing and studying an AI-assisted
four-sport forecasting project, focusing on reproducible evaluation, information
availability, calibration and baseline comparisons.” Add concrete contributions
as you actually make them.

For exercises and code-reading prompts, see [the walkthrough](walkthrough.md).
