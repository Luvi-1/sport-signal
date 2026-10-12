# Local analyst workbench: proposed user experience

Design and staged implementation, 2026-10-11. Source/parser and descriptive
implementation was approved after the independent method review. Predictive fits
remain behind separate exact-protocol review and approval. This is a local research/learning tool; no public deployment,
live data feed, automated coaching intervention or production reliability claim
is part of the current scope.

## Purpose

Help an analyst understand a specific recorded sporting situation, the information
that can be measured, the patterns supported by comparable observations and the
limits of the resulting estimate. A probability without its target, prediction
instant and population is not an adequate answer.

## Proposed flow

### 1. Choose the sport and the actual question

Show separate cards for distinct tasks, rather than one generic sport predictor:

- A match-outcome card can open the preserved four-sport baseline release
- A tactical card states the event, such as a recorded shot or an observed snap
- A mechanics card states the practice/laboratory population and measured quantity

Each card shows implementation status, source period, eligible games/participants,
measurement class, information cutoff and permitted use. A research-only or
blocked card opens the evidence and missing-measurement explanation, not a fake
prediction or a silent fallback to the match-outcome model.

### 2. Inspect measured context

Use a sport-appropriate field/court or sequence view with explicit units, coordinate
orientation and legend. Mark observed, estimated and missing positions differently.
Where uncertainty is known, show it without implying a predicted-error field is a
verified interval. Do not draw unseen players as absent or coarse direction codes
as precise trajectories.

The temporal view separates what was represented at the chosen instant from what
happened afterward. Outcome overlays may be shown during retrospective inspection,
but must be visibly separated from model inputs. Terminal outcome flags cannot
change earlier features when an analyst steps through an event.

### 3. Read the estimate with support

For an implemented and validated task show:

- Exact target and probability or continuous prediction, with class order/units
- Comparable development-sample support and the comparison rule, rather than a
  vague confidence percentage
- Evaluation population, held-out game/participant count and relevant reliability
  evidence, with sparse or unsupported contexts marked clearly
- Comparison against the declared simple baseline on the same evaluation rows
- Inputs used, key missing measurements and applicable source/era warnings
- A link to the frozen protocol, model card, full results and reproduction command

Keep metrics task-specific. Do not display a single blended “five-sport accuracy”
across different targets, prevalences, populations or continuous and categorical
outcomes. Show the baseline and event rate beside a classification score so that
a rare-event classifier is not impressive merely for predicting the common class.

Model disagreement and sampling uncertainty have distinct labels. The workbench
must not convert a low-entropy output, an ensemble agreement score or many repeated
trials from a few people into a claim of high scientific certainty.

### 4. Explore relationships cautiously

Start with count-labelled descriptive plots and prespecified feature-group
comparisons. A permitted scenario view identifies the changed inputs, held-fixed
assumptions and observed support. Unsupported combinations receive an explanation
rather than a precise number. An association is not phrased as an instruction that
an athlete will improve by the displayed amount.

For a physical measurement such as an angle, show its definition and coordinate
convention. A knee angle, trunk orientation, ball launch angle and court bearing
are different variables. Where only a coded category exists, preserve that category.

### 5. Learn what evidence would be needed next

Each task includes a short evidence panel: important mechanisms, primary papers,
their populations and study designs, which factors the current analysis can test,
and which need a different measurement or intervention study. Explain limitations
in ordinary language, with the detailed research map available for deeper reading.

Suggested learning exercises should use verified existing results: reconstruct a
coordinate transform, identify a leaking feature, compare raw and calibrated
probabilities, inspect a failed ablation, or explain why a laboratory result may
not transfer to a professional game. Exercises must not imply that the user
independently collected or authored work they have not done.

## Engineering and release requirements

- Bind any local service to loopback by default; no external hosting or analytics
- Load only verified project-produced artifacts with matching source, code, schema
  and model hashes. Never accept uploaded executable model objects
- Keep raw downloads and restricted row-level views in ignored local storage;
  publish only the material the exact source terms permit
- Show required provider attribution/logo and applicable noncommercial/share-alike
  notices in the relevant view, rather than relying only on a root license file
- No network request or data refresh hidden behind opening an analysis screen;
  use an explicit, versioned fetch/reproduction step
- Fail clearly if data, models or calibration reports are absent; no synthetic
  performance fallback. Clearly labelled geometry examples may illustrate units
  but must not appear in benchmark totals
- Validate inputs, units, population, event-stage fields, finite numbers and class
  mapping before inference; reject rather than silently coerce unsupported values
- Keep test cohorts and original results immutable; an exploratory user filter
  does not retroactively define a new validated model or a new untouched holdout
- Provide a minimal CLI path as well as the workbench so the analysis is inspectable
  and reproducible without a browser

## Planned acceptance checks

The following checks must be implemented and run before the workbench is called
complete; their presence here is not a claim they have already passed:

1. Select every sport and verify the correct target, source and model version
2. Open a task with missing artifacts and verify a useful fail-closed explanation
3. Exercise invalid units, unknown categories, missing values and out-of-support
   combinations without silent normalization or invented measurements
4. Verify a real historical case reproduces the saved model output
5. Reverse supported participant/court orientation and check the mathematical
   transformation, while preserving source-native coordinates for audit
6. Confirm outcome overlays and future frames cannot change pre-event inputs
7. Distinguish practice, professional, small-sample and research-only cards
8. Check labels, keyboard navigation, chart legends, narrow-screen layout and all
   source/report links; screenshots alone are not functional verification
9. Inspect network requests and release contents for raw-data, secret or telemetry
   leakage; confirm the intended loopback-only service configuration
10. Reproduce the documented example from a clean permitted-data installation

