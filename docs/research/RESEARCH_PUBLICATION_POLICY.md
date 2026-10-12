# Publication policy for soccer/basketball research artifacts

Research audit date: 11 October 2026. This is a conservative release classification, not a legal opinion. A general `reports/` allowlist must not override source-specific restrictions. No external publication has been performed by this research task.

## Ready to include with source notices

- `docs/research/SOCCER_BASKETBALL_RESEARCH.md`, `SOCCER_BASKETBALL_FACTOR_INVENTORY.csv`, `SOCCER_BASKETBALL_FACTOR_SOURCES.json`, and `TACTICAL_MEASUREMENT_CONTRACT.json`: original research synthesis/methodology. Keep primary links, attribution and limitations. They contain short source descriptions and independently computed audit counts, not copied papers or raw restricted datasets. The brief's conditional recommendations do not clear a source's commercial rights
- `reports/research_skillcorner_basketball_audit.json`: MIT-origin ACB aggregates, game metadata and acquisition manifest. Include `notices/SKILLCORNER_BASKETBALL_MIT.txt`, source URL/commit and “Data: SkillCorner; audit/derived analysis modified from source”
- `reports/research_skillcorner_all_tracking_audit.json`: MIT-origin counts plus event-level geometry-discrepancy rows. Those rows are derived data, not merely abstract research notes; MIT permits their redistribution subject to the notice. Include the basketball notice and source pin
- `reports/research_skillcorner_soccer_pose_audit.json`: MIT-origin counts plus 30 event/player alignment rows. Include `notices/SKILLCORNER_SOCCER_MIT.txt`, the official Hugging Face MIT declaration, both source pins and modification attribution. State that these are annotation-alignment diagnostics, not confirmed ball-contact labels
- Original audit scripts may be published with provenance and clear instructions, but must not bundle source documents/data or credentials. A published downloader does not itself confer rights to use the downloaded source

The SkillCorner event/player IDs are public professional-sports observations. Do not add inferred health, gaze, injury or other sensitive labels. These permissions do not cover third-party match video or logos not included under the same license.

## Keep local by default; do not add to an automatic release allowlist

- `reports/research_statsbomb_sample_audit.json`: contains per-match counts/metadata derived from the custom-licensed source. Keep local. For a permitted noncommercial research report, publish only a deliberately reduced aggregate coverage/QA summary with required StatsBomb attribution/logo after intended use is confirmed
- `reports/research_statsbomb_coverage.json`: competition-season metadata aggregates are safer than event rows, but still originate from the custom agreement. Keep the machine-readable file local by default; use its summarized counts in the credited research narrative, subject to applicable terms. Do not interpret this as an unrestricted open-data grant
- `reports/research_hoopr_sample_audit.json`: contains aggregate source QA, not event rows, but the selected source has unresolved upstream reuse questions. Keep it local until the source policy is reviewed. The narrative may identify the source and describe the audit/limitations; that is not approval to redistribute its underlying ESPN/NBA-origin records
- Every file under `data/research/` and `data/research_source_docs/`, including downloaded papers, PDFs, license documents, raw JSON/CSV/parquet/ZIP/XML and acquisition manifests, stays excluded from the general release. Even openly licensed raw sources should be redistributed only deliberately with the correct notice, not accidentally through a blanket allowlist
- No StatsBomb-trained model weights or row-level derived tables are automatically cleared for publication
- SPL eligibility has now been clarified for bounded independent noncommercial research. Eighteen raw trial samples were inspected and remain local, along with exact sample manifests. No raw observations, participant/trial identifier values, individual skeletons, body/health assessments, performance rankings or selection recommendations may enter user reports or GitHub. Ages are unverified, so apply these safeguards as potentially involving minors. The source's noncommercial/share-alike and additional affiliation terms still apply; do not relicense derivatives as MIT

## Source-specific fallback options

- Wyscout/Figshare v5 and IDSSE/Figshare v1 have inspected CC BY 4.0 data grants. No derived report from these sources is currently on the release list; a future artifact must include the dataset DOI, creator attribution, license link and a description of modifications
- Metrica, historical NBA/SportVU mirrors, vision clips and third-party source-code repositories were not cleared as universal data licenses in this review

Keep all figures/tables that combine sources labeled with the most restrictive applicable source condition. Separating MIT demonstrations from restricted research outputs is preferable to mixing them in one undifferentiated download.

## Bounded SPL aggregate addendum

`docs/research/SPL_BOUNDED_SCHEMA_ADDENDUM.md` and `reports/research_spl_sample_quality_aggregate.json` contain only deidentified/aggregate schema and measurement-quality findings. They are candidates for the controlled noncommercial research package after review, with MLSE Sport Performance Lab attribution, modification description, a CC BY-NC-SA 4.0 link and the complete `notices/SPL_LICENSE.txt` including its additional restriction. They are not automatically cleared by a general reports allowlist. The report may name schema fields such as `participant_id`, but must not expose actual participant identifier values. Keep the local raw/sample manifest excluded. No numerical model or participant-level visual output is cleared by this audit.
