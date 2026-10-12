# Rights, access, provenance and data alternatives

Checked 2026-10-11 UTC. This is an operational source screening, not a legal opinion. Publicly readable papers, open-source software, downloadable sports records and permission to redistribute those records are separate questions. No account, API key, paid service or outreach was used. No denied source was retrieved through a mirror.

## Source decisions

| Source | What is genuinely available | Rights evidence | Decision for this portfolio |
|---|---|---|---|
| Retrosheet official event/parsed-play archives | Real game events, pitch outcome strings, counts, substitutions and game state | [Official notice](https://www.retrosheet.org/notice.txt) permits reuse with attribution, including commercial use | Cleared source for the narrower count/sequence task; preserve notice and changes |
| nflverse PBP | Historical play-by-play, game state, labels and provider-derived metrics | [Publisher repository](https://github.com/nflverse/nflverse-data) identifies CC BY 4.0 for its generally licensed data; confirm each release-specific exception | Use with attribution and pinned files; do not mistake provider metrics for pre-snap observations |
| nflverse participation, NGS era | Participation/personnel/formation and selected charting, 2016–2022 | [Official loader terms](https://nflreadr.nflverse.com/reference/load_participation.html): CC BY-SA 4.0 and source attribution | Permitted with terms; schema/coverage differ materially from FTN era |
| nflverse participation, FTN era | Annual participation, formation/personnel/pressure and coverage fields, 2023 onward | Same official loader specifies CC BY-SA 4.0; credit FTN Data via nflverse | Primary NFL source; annual/postseason release prevents a claim of a live feed |
| FTN charting via nflverse | Per-play motion, box/backfield/hash and other charted annotations, 2022 onward | [Official FTN loader](https://nflreadr.nflverse.com/reference/load_ftn_charting.html): CC BY-SA 4.0 | Primary supplemental source; preserve source-specific license on adapted data |
| Baseball Savant / Statcast | Official CSV export and detailed documented physical measurements; newer bat/stance leaderboards | [CSV documentation](https://baseballsavant.mlb.com/csv-docs) and [MLB terms §1](https://www.mlb.com/official-information/terms-of-use) | Preferred measured-pitch scientific scope, but collection and public-release route not cleared by this review; no bulk retrieval attempted |
| NFL Big Data Bowl official repository | Example game/player/play files, a surviving 2017 tracking game, schema and competition references | [Official repository and FAQ](https://github.com/nfl-football-ops/Big-Data-Bowl) refer to competition rules/research publication; no general-purpose standard data license verified | A research lead, not an unrestricted tracking corpus; cannot turn small example into a league-scale benchmark |
| Kaggle Big Data Bowl releases | Rich selected tracking/labels under year-specific competition rules | Official competitions may require account/terms acceptance | Outside the no-signup constraint; do not use unaffiliated mirrors to evade it |
| Driveline OpenBiomechanics | Real laboratory motion/force/hitting datasets, mostly collegiate athletes | [Data license](https://github.com/drivelineresearch/openbiomechanics/blob/main/LICENSE-DATA.md) and [datasheet](https://github.com/drivelineresearch/openbiomechanics/blob/main/DATASHEET.md) | Bounded local inspection now cleared for the confirmed independent noncommercial scope; retain share-alike/attribution and the additional affiliation restriction. Not an unrestricted MLB fallback |
| Author code accompanying papers | Often reproducible analysis code or methods | Repository-specific license, separate from the paper and source data | Read methodology; do not assume included MLB/NFL rows inherit the code license |
| Private club, PFF, Hudl, NGS tracking/markerless biomechanics | Rich professional mechanics and expert annotations described in papers | No no-signup public license established | Inform scientific design and explicit gaps only; no acquisition or reconstruction from match scores |

### Statcast decision, precisely

MLB terms reserve broader reuse and prohibit automated collection; personal noncommercial copying has a limited exception. Savant-specific export rights remain unresolved.

This is **not** a technical access denial and **not** a claim that every Statcast research use is unlawful. The official export UI matters. A bounded personal export and a publicly distributed portfolio are different proposed uses. No Savant-specific permission resolving this project's automated collection/publication workflow was located in the reviewed official materials. The absence of a Creative Commons label alone is not the blocker.

Operational recommendation: keep a measured-Statcast analysis specification and an optional adapter interface, but do not initiate automated multi-season collection or publish records/models from that source until the intended route and use are reviewed. A user-provided lawfully obtained file can be inspected locally if its permitted use is established. Excluding raw rows is sensible but does not automatically settle rights in all downstream outputs. No external contact is authorized for this task.

## Attribution and packaging

Retrosheet's requested attribution should be carried in the data-source notice:

> The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

For FTN-derived materials, identify **FTN Data via nflverse**, link the source and CC BY-SA 4.0 terms, and state transformations. NGS-era participation should credit the corresponding NGS source via nflverse. PBP should credit nflverse and retain its applicable CC BY notice. Do not apply the repository's code license as if it relicensed these inputs. Keep data-license notices adjacent to any permitted dataset adaptation; whether a particular aggregate or trained artifact is an adaptation should not be resolved by silently applying MIT to it.

A conservative release contains code, source manifests, audit aggregates, methodological documentation and permitted aggregate model evaluation. Raw downloads and local row-level training/prediction artifacts remain excluded from the distributable archive unless separately approved under their source terms. A public URL is not itself redistribution permission.

## Verified download and audit inventory

`data_download_manifest.json` records official source URLs, retrieval UTC, bytes and SHA-256 for the retrieved CSV/ZIP files. Downloads are in the repository's ignored raw-data area. Do not rehost them as part of this brief.

### NFL schemas inspected in actual files

- Participation 2022, 2023, 2024, 2025: IDs, formation, personnel, on-field players, pressure and additional coverage/rush fields
- FTN charting 2022, 2023, 2024, 2025: IDs, QB location, motion, box/backfield, hash, play action/RPO and later-stage charting
- PBP 2025: game/play IDs, chronological/game context, run/pass/dropback/sack/scramble flags and outcomes
- 2025 join/cohort audit: all eligible regular-season plays matched both supplemental sources

Schema and coverage evidence lives in `schema_coverage_audit.json` and `nfl_2025_join_audit.json`, generated by the adjacent research scripts. These scripts are auditing aids, not production ingestion or a finished model.

### Retrosheet schemas inspected in actual files

- Raw EV ZIPs for 2023–2025
- Parsed 2025 plays, with 177 columns and regular/postseason labels
- Raw-to-parsed exact alignment and incremental pitch expansion for all 2025 regular-season games

Keys and useful parsed fields include `gid`, `pn`, `event`, `date`, `gametype`, `inning`, `top_bot`, batter/pitcher, handedness, pre-count, cumulative pitches, pre-outs, runners, scores and team/site. Raw records are still required for correctly timestamped substitutions and cumulative-prefix handling. The source's batted-ball location must not be presented as a pitch coordinate.

## Data alternatives compared on substance

**Retrosheet vs Statcast:** Retrosheet has cleaner reusable rights and robust state/sequence context; Statcast has the requested physical pitch/bat measurements. They solve overlapping but different questions. Choosing Retrosheet is a deliberate scope reduction, not proof that mechanics do not matter.

**nflverse/FTN vs tracking:** charted formation/personnel/motion enables real tactical anticipation with strong temporal evaluation. It lacks x/y/o/dir trajectories, leverage, exact blocking assignments, route geometry and tackle approach speed. Tracking papers establish the relevance of those omitted dimensions, but no engineered feature from final scores can recreate them.

**Open laboratory biomechanics vs professional game tracking:** laboratory markers and force plates can measure true joint/segment mechanics absent from public event data. Laboratory samples, athlete mix, effort conditions and equipment differ from MLB/NFL game deployment. Such data support a separate biomechanics demonstration if rights permit, not a merged pseudo-professional game model.

**Current leaderboards vs historical per-event files:** leaderboards can demonstrate that a measurement exists. They do not automatically supply timestamped rows, selection/quality flags or past versions needed for leakage-safe prospective modeling.

## OpenBiomechanics eligibility and bounded-inspection update

Eligibility was subsequently confirmed for independent noncommercial local research without the excluded affiliations. The exact data/documentation license was re-read and ten small official source files were fetched at a pinned commit; five are summary-data CSVs. No model was fitted and no full-signal/C3D archive was obtained. See [OPENBIOMECHANICS_AUDIT.md](OPENBIOMECHANICS_AUDIT.md) and `openbiomechanics_manifest.json`. This is not permission for commercial reuse, raw-data publication or a paid-license workflow. Keep source-derived documentation/aggregates under the applicable source terms rather than applying the code license to them.
