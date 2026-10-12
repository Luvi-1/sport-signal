# Soccer/basketball source QA

These scripts inspect actual pinned source files; they do not train or evaluate a tactical model. They use Python's standard library and resolve the project root from their own location. No upstream repository code is executed.

Read `docs/research/RESEARCH_PUBLICATION_POLICY.md` before redistributing inputs or generated reports. Read the main research brief for exact source URLs, versions, schemas and download routes. Source files/documents are expected under the local ignored `data/research/` and `data/research_source_docs/` layouts used in this audit.

- `audit_statsbomb_coverage.py`: requires the pinned GitHub tree, official competitions JSON and every match-index JSON. Produces competition-season coverage and a local acquisition manifest
- `audit_statsbomb_samples.py`: requires the nonrandom 42-match sample manifest, corresponding event JSONs and available 360 sample JSONs. Produces per-match source QA, not a prevalence estimate
- `audit_skillcorner_basketball.py`: requires all ten ACB dynamic-event/game-data files plus game 114243 tracking and the optional local acquisition manifest. Produces event field/missingness and source reconciliation diagnostics
- `audit_skillcorner_all_tracking.py`: requires all ten ACB tracking gzip files and event files. Streams all frames, retaining release and release-minus-1/-5/-25 frames only. Produces geometry/detection audits. Four prior samples are not a complete velocity-window validity test
- `audit_soccer_pose.py`: requires the pinned first soccer pose ZIP and the associated SkillCorner dynamic-event CSV. Streams the full ZIP and checks provider-estimated pose coverage at annotated shot-ending possession frames. This does not validate true ball-contact timing

Example from the project root: `python scripts/research/audit_skillcorner_all_tracking.py`.

The published scripts were syntax-checked; the coverage, StatsBomb sample and ACB event scripts were rerun from this location. The full-tracking and pose audit bodies were already run successfully before relocation; their only relocation change is root-path resolution and this documentation. Source QA inspected aggregate outcomes in later-evaluation games; no predictive model was fitted and no held-out model score was examined.

Potential improvements belong in the implementation review: argument-based source roots, explicit schema validation exceptions, tests with tiny legally redistributable fixtures, and cleaner report formatting. These standalone scripts document the research audit, not a production ingestion library.

- `audit_spl_sample_quality.py`: requires the locally retained bounded-sample manifest and 18 SPL trials. Produces only deidentified aggregate schema/missingness/clock quality, including nonstandard JSON tokens. Eligibility was clarified for independent noncommercial research; full source terms remain in force. No participant-level output or model fitting.
