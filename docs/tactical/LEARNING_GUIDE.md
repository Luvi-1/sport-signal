# Learning through the five-sport workbench

This extension is AI-assisted research and software development. To describe it
accurately in an application, distinguish work you have personally understood,
reproduced or changed from automated assistance. The exercises below create useful
hands-on experience without implying independent authorship of every component.

## 1. Run the local research workbench

From the repository root:

```sh
python -m experiments.tactical.workbench index
python -m experiments.tactical.workbench serve
```

Open the loopback address printed by the server. It is read-only and does not
fetch sources, train models or expose the service publicly. An absent summary is
reported explicitly; the included reviewed numerical snapshots still work without
raw data or fitted weights. Source/parser commands and permitted acquisition instructions
are in each sport's parser document. Do not assume that a report from a different
installation has the same source bytes.

## 2. Explain one row before explaining a model

For each sport, write down the population, unit, target, observation instant and
important missing quantity. Explain why a charted tennis direction cannot be drawn
as an exact trajectory, why an at-snap NFL annotation is not necessarily a live
pre-play input, and why a contacted laboratory baseball is not an arbitrary MLB
pitch.

## 3. Trace information through a sequence

Inspect a synthetic parser test, then follow its state changes. Alter a future
outcome and verify that the earlier features do not change. For baseball, reconstruct
an interrupted plate appearance without counting old pitch prefixes again. For
tennis, sort points, identify a tie-break from actual state and distinguish its rule
from its current status. Synthetic fixtures demonstrate code behavior; they are
never part of measured dataset results.

## 4. Reconstruct a physical definition

Compute goal angular width from the documented soccer goalposts. Verify basketball
feet and court orientation before calculating distance. For a pose angle, specify
three joints, units, coordinate convention and whether the locations are estimated.
A successful coordinate transform does not validate physical sensor accuracy.

## 5. Read a denominator and an exclusion

Compare all recorded basketball releases with official field-goal attempts. Explain
why excluding lets makes a tennis execution study conditional, and why net-censored
attempts cannot receive invented bounces. Review a real source-quality quarantine
without changing it merely because removing the case improves model results.

## 6. Evaluate only after a protocol exists

Tactical development and final scoring are separate stages. Only open a task's
final results after its exact protocol, fixed selection and evaluation authority
are recorded. Reproduce its simple baseline and saved predictions, then independently
recompute log loss/Brier or unit-aware regression error. Find the calibration
partition and prove the final test was not used to select the model. Compare
identical rows and report both improvements and regressions. The preserved
match-outcome release has its own completed reproduction check; this does not
automatically establish an independent refit reproduction of the tactical extension.

## 7. Make one small, defensible contribution

Examples: add a malformed-state test; improve a missing-value explanation; reproduce
an existing reliability plot; verify a units conversion; or propose a new feature
with a source, availability time and leakage test. A new experiment must get a new
protocol and honest evaluation label, rather than silently replacing the old test.

## Suggested project description, once you have done the exercises

“I’m developing an AI-assisted, five-sport analytics research project. I have
worked through source licensing, event-state reconstruction, chronological and
grouped evaluation, and the distinction between observed context and unavailable
mechanics. The project preserves reproducible match-forecast baselines and is
extending into sport-specific tactical and laboratory analyses. I can explain the
parts I reproduced and the limitations of their evidence.”

Edit this to reflect what you actually did. Do not claim current tactical accuracy,
professional coaching benefit, production deployment, independent data collection
or superiority to commercial systems without measured evidence.
