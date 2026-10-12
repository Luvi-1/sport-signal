# Baseball and American-football research package

Research date: 2026-10-11 UTC, before tactical implementation/model scoring. This package documents a broad primary-source search and its limits; it does not claim exhaustive coverage of every paper or factor.

## Start here

1. [Research-to-build recommendation](RESEARCH_BRIEF.md): decision targets, measurement clocks, inspected schemas, cohort audits, baseline ladder, chronological validation and leakage guards
2. [Rights and data alternatives](RIGHTS_AND_DATA.md): exact routes, attribution, publication/access constraints and unresolved gates
3. [Core factor inventory](factor_inventory.csv): 70 operational factor families spanning player skill, mechanics, context, tactics, opponent, health/workload, environment, coaching and rules
4. [Methods literature review](LITERATURE_REVIEW.md): primary tactical/physics papers, professional model descriptions, review depth and implementation implications
5. [Baseball biomechanics review](baseball_biomechanics_review.md): 21 deeper domain specifications plus study-level populations, evidence strength, measurement and transport limitations
6. [Football mechanics review](football_mechanics_review.md): 49 more detailed operational rows and primary studies of blocking, routes, coverage, running/tackling, QB mechanics and contextual gaps
7. [Baseball defense and baserunning](baseball_other_roles_review.md): catcher, fielding, throwing, receiving, runner leads/turns and opportunity definitions
8. [NFL receiving and special teams](football_other_roles_review.md): catching, kicking, punting, snapping/holding, coverage and return decisions
9. [Lab-mechanics candidate](LAB_MECHANICS_CANDIDATE.md) and [verified bounded source audit](OPENBIOMECHANICS_AUDIT.md): actual body-angle/timing schema, target definitions, duplicate/coupling exclusions and athlete-grouped design after eligibility confirmation
10. [Search log](SEARCH_LOG.md): sources/surfaces, query families, inclusion rules, citation follow-up, negative findings and stopping criteria

The inventories overlap by design; their row counts are not a count of independent causal factors or independent studies.

## Scientific and practical recommendation

**NFL:** a retrospective final-at-snap realized-dropback forecast for film review/scouting, with formation/personnel/motion/box information, is supported by inspected licensed data. A separate pressure-susceptibility model on dropbacks is feasible. The observed state is not information available before the offense chose its play. Do not call these live/optimal play-calling or causal blitz/motion models. Richer leverage, engagement, route, tackle and throwing mechanics remain important measured-data gaps.

**Baseball:** measured pitch/bat mechanics remain the preferred scientific scope. Public Statcast/Savant measurements exist, including real stance and bat-path summaries, but the intended acquisition/reuse route and per-event completeness are unresolved. Retrosheet offers a clearly reusable, narrower count/pitch-outcome-sequence task. It cannot substitute for measured pitch type/location/movement or stance. OpenBiomechanics has now passed the bounded local-inspection eligibility check: real body-angle summaries and contact measurements support a separate noncommercial laboratory candidate. It is not an MLB game cohort; model fitting and wider use still require the declared research/build gate.

## Reproducible source audits

- `data_download_manifest.json`: 13 official downloaded source archives/files with URLs, fetch times, byte counts and hashes
- `schema_coverage_audit.json`: actual 2022–2025 NFL supplemental schemas/coverage and 2023–2025 Retrosheet raw coverage
- `nfl_2025_join_audit.json`: 32,813 eligible 2025 regular-season plays from 272 games, complete joins, target/field denominator checks
- `retrosheet_2025_alignment_audit.json`: all 189,939 regular-season parsed records matched to raw EV; prefix/substitution/count checks and one corrupt-sequence example
- Adjacent `inspect_sources.py`, `audit_coverage.py`, `audit_nfl_join.py`, `audit_retrosheet.py`: research audit scripts, **not production-ready parsers or fitted models**
- `openbiomechanics_manifest.json` / `openbiomechanics_schema_audit.json`: pinned official summary files, aggregate quality and sensor/target-coupling checks; no fitted models
- `make_factor_inventory.py`: writes the documentation CSV; it generates no fake player observations

Raw files and downloaded paper PDFs are in an ignored research-data area, not intended for redistribution. These source audits inspected 2025 outcomes/coding for QA; final model evaluation can be performance-blind after QA, but should not be described as perfectly human-blind. Model selection and calibration must use disjoint chronological game partitions.

## Handoff gate

The research recommendation is ready for review. Before implementation, freeze the selected scope, rights route, cohort, prediction moment, exact feature allowlist, split dates and candidate ladder. No tactical model performance or causal improvement has been claimed. Existing match forecasts remain separately identified.
