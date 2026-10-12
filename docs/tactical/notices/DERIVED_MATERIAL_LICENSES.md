# License scope for the released tactical material

The root MIT software license does **not** relicense third-party data or the
source-derived materials listed here. This notice applies to this SportsLab
release, rather than referring only to an upstream repository. Preserve the
source credits, modification descriptions, license links and additional source
conditions when redistributing the corresponding material. No provider endorses
the project. This package is intended for independent noncommercial research.

## Exact aggregate and model-card paths

| Released project paths | License or applicable source conditions |
|---|---|
| `reports/tactical/model_views/football.json`; `docs/tactical/model_cards/football.md` | The project's source-derived aggregate material is released under **CC BY-SA 4.0**, crediting FTN Data via nflverse. The underlying play-by-play contribution retains its CC BY 4.0 credit. See `NFLVERSE_FTN_NOTICE.md` and `NFLVERSE_PBP_NOTICE.md` |
| `reports/tactical/model_views/tennis.json`; `docs/tactical/model_cards/tennis.md` | The project's source-derived aggregate material is released under **CC BY-NC-SA 4.0**, crediting Jeff Sackmann/Tennis Abstract, the Match Charting Project and its contributors. See `MCP_NOTICE.md` |
| `reports/tactical/model_views/baseball_mechanics.json`; `docs/tactical/model_cards/baseball_mechanics.md` | The project's source-derived aggregate material is released under **CC BY-NC-SA 4.0 with the upstream additional professional-organization/financial-analysis affiliation exclusion**. Credit the Driveline OpenBiomechanics Project. The complete additional condition is retained in `OPENBIOMECHANICS_DATA_LICENSE.md`; this is not an unrestricted standard-CC grant |
| `reports/tactical/model_views/basketball.json`; `docs/tactical/model_cards/basketball.md` | MIT, with SkillCorner attribution and the complete `docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt` notice retained |
| `reports/tactical/model_views/baseball.json`; `docs/tactical/model_cards/baseball.md` | Original project analysis under MIT, with the mandatory Retrosheet attribution in `RETROSHEET_NOTICE.txt`; upstream Retrosheet rights are not reassigned |
| `reports/tactical/model_views/tennis_execution.json`; `docs/tactical/model_cards/tennis_execution.md` | MIT, with the original Nate Sandholtz notice in `BYU_MIT.txt`. Participant privacy safeguards apply separately; no individual records are licensed for distribution by this aggregate release |
| `reports/tactical/model_views/soccer.json`; `docs/tactical/model_cards/soccer.md` | Noncommercial research analysis subject to the **StatsBomb custom agreement**, attribution and logo requirements in `STATSBOMB_NOTICE.md`. These paths are not offered under root MIT or a Creative Commons data license |

License texts: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The source notices identify the exact upstream repositories, relevant pins and
the project's transformations.

## Mixed-source benchmark and research documents

`docs/tactical/BENCHMARK_RESULTS.md` contains separately attributed study tables
and interpretations. Its NFL-derived tables/analysis are released under CC BY-SA
4.0; its MCP-derived tables/analysis under CC BY-NC-SA 4.0; and its OpenBiomechanics-
derived tables/analysis under CC BY-NC-SA 4.0 with the complete upstream affiliation
exclusion. Its soccer-derived tables/analysis remain subject to StatsBomb's custom
noncommercial conditions. SkillCorner, Retrosheet and BYU sections retain the
corresponding terms and credits above. No single MIT header overrides these
section-level grants and restrictions.

The same affirmative source-specific licenses and conditions apply to data-derived
counts, tables, figures and analysis in the following released methodological/
research documents, according to the source attribution of each passage:

- `docs/tactical/SOCCER_PROTOCOL_DRAFT.md`, `soccer_parser.md`, `soccer_model.md`
- `docs/tactical/BASKETBALL_PROTOCOL_DRAFT.md`, `basketball_parser.md`, `basketball_model.md`
- `docs/tactical/BASEBALL_PROTOCOL_DRAFT.md`, `baseball_parser.md`, `baseball_model.md`
- `docs/tactical/FOOTBALL_PROTOCOL_DRAFT.md`, `football_parser.md`, `football_model.md`
- `docs/tactical/TENNIS_PROTOCOL_DRAFT.md`, `tennis_parser.md`, `tennis_model.md`
- `docs/tactical/BASEBALL_MECHANICS_PROTOCOL_DRAFT.md`, `TENNIS_EXECUTION_PROTOCOL_PUBLIC.md`, `mechanics_measurements.md`, `mechanics_models.md`
- `START_HERE_FIVE_SPORTS.md` and `docs/tactical/TENNIS_RECOVERY.md`: source-derived portions retain their corresponding terms; original workflow/resource-accounting descriptions remain original writing
- `docs/research/SOCCER_BASKETBALL_RESEARCH.md`, `SOCCER_BASKETBALL_FACTOR_INVENTORY.csv`, `SOCCER_BASKETBALL_FACTOR_SOURCES.json`, `TACTICAL_MEASUREMENT_CONTRACT.json`
- The explicitly listed research synthesis documents under `docs/research/baseball_football/` and `docs/research/tennis/` in `TACTICAL_PUBLISH_MANIFEST.json`

Original software, synthetic code fixtures and source-independent methodological
writing remain under the project's MIT license unless a file says otherwise.
Source-independent code does not acquire access to restricted data through that
license. Citation of a paper also does not grant rights in its underlying data.

The release manifest binds exact selected paths and bytes. Raw observations,
individual predictions, participant memberships and tactical trained weights are
excluded; nothing in this notice authorizes obtaining or redistributing them.
The aggregate-only privacy review is separate from copyright permission and
does not confer medical, selection or commercial-use authority.

For every included file, `TACTICAL_PUBLISH_MANIFEST.json` records its exact path,
byte hash and `sources` list. This is the complete applicability index, including
mixed-source synthesis and factor inventories not individually expanded above.
For each listed source, its attributed data-derived portion is affirmatively
licensed on the terms stated here and in that source's required notice. A file
with multiple sources is a collection of separately licensed passages/tables:
FTN-derived BY-SA portions are not relabeled BY-NC-SA, and StatsBomb-derived
portions are not relabeled Creative Commons. The index is not permission to omit
attribution or to assume licenses are interchangeable. Source-independent code
and writing remain distinguishable from those portions.
