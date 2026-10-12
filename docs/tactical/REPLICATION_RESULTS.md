# Source-to-model replication addendum

**Execution and independent AI-assisted final review completed 11 October 2026.**

All seven studies were rebuilt in a separate local workspace from copied,
hash-pinned source inputs. The saved original-versus-refit comparisons show zero
numerical differences in the compared predictions, scores and interval
endpoints. No reported decisions, tied-class sets, reliability-bin assignments
or success criteria changed.

Independent final review verified these comparisons and all 272 successful
operations. This pass independently recalculated ACB, Retrosheet, MCP and
mechanics scores, agreeing within floating-point rounding; soccer and NFL
reports were checked against the earlier independently audited originals.
This does not change the zero observed original-versus-refit differences.
The review is AI-assisted methodological and numerical checking, not human
ground-truth validation or legal certification.

This adds same-environment reproducibility evidence. It does not change the
mixed findings of the studies, create another held-out test, establish causal
effects, or demonstrate performance on a different machine.

## What was repeated

| Study | Counted operations | Attained comparison tier | Largest prediction difference | Largest score/interval difference |
|---|---:|---|---:|---:|
| WSL soccer shot context | 6 | Exact compared values | 0 | 0 |
| ACB basketball shot context | 18 | Exact compared values | 0 | 0 |
| Retrosheet baseball pitch sequences | 20 | Strong same-environment; observed differences zero | 0 | 0 |
| NFL at-snap tendency | 15 | Exact compared values | 0 | 0 |
| MCP tennis serve direction | 22 | Strong same-environment; observed differences zero | 0 | 0 |
| Adult laboratory baseball mechanics | 175 | Exact compared values | 0 | 0 |
| BYU tennis execution | 16 | Exact compared values | 0 | 0 |
| **Total** | **272** | **All saved comparisons passed** | **0** | **0** |

The operations include analytic reference builds and calibrators, so this is
not a count of 272 optimizer fits. The comparison tiers above retain each
frozen checker's terminology. Zero differences mean equality of the compared
numerical values; serialized model files, timestamps and SQLite file bytes need
not be identical.

The source reconstruction used independent file copies, with no original
models, feature caches or history arrays admitted as fitting inputs. Original
artifacts supplied locked configurations and read-only comparison evidence.
Fresh preprocessing and calibration were fitted again in their original roles.

- Soccer, NFL and Retrosheet retained their original refit and calibration
  partitions
- MCP retained its 2010–2022 training-only fits, 2023 selection commitments,
  2024 temperatures and fixed Date+21 availability assumptions
- ACB repeated eight development fits and ten chronological evaluation fits;
  each next-game prediction was saved before that game's labels were admitted
- Adult baseball mechanics repeated the complete 160 inner ridge calculations,
  verified the original choices, then performed ten outer ridge fits and five
  reference builds
- BYU repeated the sixteen fixed leave-one-player-out hurdle procedures on the
  same non-let cohort

All seven development commitments were frozen before final comparison. There
were no retries, additional candidate searches, changes to acceptance
tolerances, or score-based changes to the selected procedures.

## Unavailable procedures stayed unavailable

The original unavailable second-serve men's MCP logistic model was omitted.
Its interrupted candidate was not rerun or assigned an inferred result. The
successful second-serve women's logistic model was fitted directly with its
original terminal 1,000-iteration setting; the discarded 300-iteration warning
attempt was not replayed. Retrosheet's two originally nonconvergent C=3 sequence
candidates were also omitted.

Thus this is a source-to-selected-procedure replication, rather than a replay
of every original search candidate or the interruption/failure trajectory.
The full nested baseball-mechanics calculation and fixed ACB schedule are
explicitly included exceptions to the selected-procedure scope.

## Checks and limits

Pinned sources and development-input identities, roles, exclusions and fixed
configurations were checked before their relevant fits. Final-case identities,
availability masks and original model/schema comparisons were checked at the
sealed comparison stage. Canonical features matched; no approximate-feature
exception was used. Predictions were saved before original comparison
references were opened. Model serialization, preprocessing schema and
discrete-output checks were separate from rounded metric tables.

Target evidence is role-specific. Some roles have directly comparable archived
target digests; others rely on the exact pinned source and unchanged target
extraction code. The mechanics labels were independently reconstructed from
raw columns, not compared with a nonexistent historical label cache.
Retrosheet calibration likewise has pinned source/cohort/code evidence rather
than a separate archived calibration-target-vector digest.

The predefined learned-classifier strong thresholds were 1e-8 for probabilities
and 1e-10 for continuous metrics/intervals; the numerical-consistency ceiling
was 1e-6. Ridge and analytic hurdle ceilings were respectively 1e-8 in output
units and 1e-10. All observed differences were zero. These thresholds were
fixed before comparison and were not relaxed.

The run used the original Python/package versions and task-specific one-, two-
or four-thread limits. Timed adapter-stage work across source rebuilding,
development and evaluation totaled **38.70 minutes**; this excludes review
waits, process import/startup and final receipt hashing. Maximum recorded
process RSS was **2.00 GiB**. Scratch usage before the final summary was
**3.43 GiB**, within the 10 GiB boundary-checked cap. These are measurements of
this run, not performance guarantees.

The implementation suite passed **757 tests** before execution. Browser visual
QA remains unperformed. The already delivered source/aggregate ZIP and original
scientific results have not been replaced by this addendum.

## Interpretation for the project

The rerun supports confidence that the reported findings can be obtained again
from the pinned inputs and selected procedures in this software environment.
The original positive and negative findings remain intact. Reproducibility
does not make a weak model more accurate, remove data-selection limits, turn
an association into a coaching intervention, or justify professional-game
transfer from a small laboratory cohort.

No raw/trial records, individual predictions or fitted athlete-level artifacts
are included in this addendum. Existing source-specific notices and derived
material terms remain applicable. The previously delivered ZIP contains the
full notice at `docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md`; that notice
is not bundled inside this standalone addendum.

## Provenance

- Execution binding: `8786a7b7200750662cf6b77de7fece2f0a90115b24b268a854f04db85f2a6e11`
- Source freeze: `a510df406bcbeca23ada6d64df57eba51b7c9ea0b09517b6df90b3623774fc67`
- Development freeze: `8e26edcd353e3612e3fa1be7a61cb9613d4904447cc7207d010fa3268f7ae4b8`
- Saved aggregate comparison summary: `413226531ed6899108fb7a4d98beff7465d602b477fadf2c27198e0eef793f04`
- Independent final review: `b0995ca1fa4f2a1394ff71c37e0520db6f2632fae206a7e485829887fffe487f`
- Delivered ZIP preserved: `d31da1ebfbceeb80f9f2c0e4a14bbd6e74d10f25a8f19188441b49773ead8917`

This addendum is separate from the previously reviewed release inventory.
It does not itself replace the delivered archive or authorize a publication
amendment.
