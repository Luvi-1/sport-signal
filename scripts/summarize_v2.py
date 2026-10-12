"""Render the complete prespecified V2 evaluation; never select a new winner."""
from pathlib import Path
import json,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
SPORTS=('soccer','baseball','football','tennis')

def name(key):
    mapping={'ensemble_calibrated':'Prespecified ensemble','v1_recipe_refit_calibrated':'V1 recipe, refitted','elo_calibrated':'Calibrated Elo','training_prior':'Training-frequency prior','rating_logistic_calibrated':'Rating-only logistic','dixon_coles_calibrated':'Dixon–Coles-style Poisson'}
    return mapping.get(key,key.removesuffix('_calibrated').replace('_',' '))

def interval(values):return f'[{values[0]:+.4f}, {values[1]:+.4f}]'

def main():
    reports={};selections={}
    for sport in SPORTS:
        path=ROOT/'reports/v2'/sport/'evaluation.json'
        if not path.exists():raise SystemExit(f'V2 {sport} remains pending; no partial final summary generated')
        reports[sport]=json.loads(path.read_text())
        if reports[sport].get('status')!='completed_single_new_holdout_evaluation':raise SystemExit(f'V2 {sport} is not complete')
        selections[sport]=json.loads((ROOT/'artifacts/v2'/sport/'selection.json').read_text())
    lines=['# V2: stronger models on a newer held-out period','',
      'The V1 holdout had already been inspected. V2 uses it only as disclosed development history and evaluates on new 2025 periods (EPL 2025–26). All four model selections, stacking weights and calibrators were frozen together before any new-period scoring. The main model was specified as the ensemble in advance; it is not replaced because another row later scored better.','',
      '## Same-game comparison against a refitted V1 recipe','',
      '| Sport | New test games | Ensemble accuracy | Ensemble log loss | Refitted V1 log loss | Calibrated Elo log loss | Ensemble minus V1 loss | Approximate 95% difference interval |',
      '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for sport,r in reports.items():
        m=r['metrics'];u=r['uncertainty_vs_v1_recipe_refit'];e=m['ensemble_calibrated'];old=m['v1_recipe_refit_calibrated'];elo=m['elo_calibrated']
        lines.append(f"| {sport.title()} | {r['test']['n']:,} | {e['accuracy']:.2%} | {e['log_loss']:.4f} | {old['log_loss']:.4f} | {elo['log_loss']:.4f} | {u['model_minus_baseline_log_loss']:+.4f} | {interval(u['difference_95pct_interval'])} |")
    lines += ['', 'Negative differences favor V2. These are paired calendar-week bootstrap intervals with 400 replicates. They are unadjusted descriptive intervals, not proof of universal superiority, and do not cover all source, long-range dependence or model-selection uncertainty. Accuracy is secondary to probability log loss.','',
      '## What changed','',
      '- New 2025 data was structurally audited; MLB franchise continuity and a new EPL score schema were resolved without using model performance',
      '- Longer-horizon, availability-aware strength/form and surface features; new ratings use availability-bucket updates that do not invent within-tournament order',
      '- Rating-only and extended logistic models, histogram boosting, random forests, Extra Trees, and a soccer goal-count baseline',
      '- Three chronological development folds; a learned nonnegative ensemble from out-of-fold predictions; separate calibration year',
      '- All candidate development scores, selected configurations, source/code hashes, ensemble weights, temperatures and software versions retained',
      '- Licensed, odds-free frozen NFL input prevents mutable upstream releases from breaking reproduction','',
      '## Interpretation by sport','']
    for sport,r in reports.items():
        u=r['uncertainty_vs_v1_recipe_refit'];lo,hi=u['difference_95pct_interval'];delta=u['model_minus_baseline_log_loss']
        if hi<0:judgment='The ensemble improves probability log loss relative to the refitted V1 recipe, with an approximate interval below zero'
        elif lo>0:judgment='The ensemble is worse than the refitted V1 recipe on probability log loss, with an approximate interval above zero'
        else:judgment='The difference from the refitted V1 recipe remains uncertain under the approximate interval'
        lines += [f"- {sport.title()}: {judgment}. Point difference: {delta:+.4f} nats/event"]
    lines += ['', 'A new year’s accuracy cannot be directly compared with V1’s older-year accuracy to prove improvement. The refitted V1 column uses the same new matches, training/calibration periods and information-availability rules. Its features retain the original simpler recipe. More complex models are not presumed better.','',
      '## All prespecified family comparisons','',
      'Tables below are descriptive rankings of completed test results, not post-test model selection. Raw and calibrated variants remain in the machine-readable reports. Different information structures are explicit: the soccer goal model fits team identities, while generic tabular families use the documented numeric features.','']
    for sport,r in reports.items():
        lines += [f'### {sport.title()}','',f"Test: {r['test']['first_date']} through {r['test']['last_date']} · {r['test']['n']:,} events",'',
          '| Model | Accuracy | Log loss | Brier | Top-label ECE |','| --- | ---: | ---: | ---: | ---: |']
        chosen=[(k,v) for k,v in r['metrics'].items() if k.endswith('_calibrated') or k=='training_prior']
        for key,m in sorted(chosen,key=lambda item:item[1]['log_loss']):
            lines.append(f"| {name(key)} | {m['accuracy']:.2%} | {m['log_loss']:.5f} | {m['brier']:.5f} | {m['top_label_ece_10_bins']:.5f} |")
        write_model_card(sport,r,selections[sport])
        lines += ['',f'![{sport} reliability]({sport}/reliability.svg)','',f'[Full evaluation]({sport}/evaluation.json) · [Development candidates and frozen selection]({sport}/development.json) · [Model card](../../docs/v2/model_cards/{sport}.md)','']
        plot_reliability(r,ROOT/'reports/v2'/sport/'reliability.svg')
    lines += ['## Calibration, uncertainty and exclusions','',
      'Brier is positive-class mean squared error for binary tasks and summed classwise squared error for soccer. ECE depends on ten fixed-width bins; inspect reliability counts in JSON. Calibration can worsen a new period and is not assumed successful. NFL/MLB ties and tennis incomplete/unsupported scores are excluded. Tennis dates remain tournament-start proxies, with 21-day result delays and realized-matchup conditioning. These are corrected historical snapshots, not a validated live feed.','',
      '## Laya and commercial comparisons','',
      'The separately frozen 800-row V1 Laya zero-shot experiment lost to the simpler baselines in all four sports; it was not fine-tuned or used inside V2. [Measured Laya results](../../docs/laya_experiment.md).',
      '', 'A 969-game preserved FiveThirtyEight MLB diagnostic showed a small, uncertain advantage for its pitcher-adjusted forecast over V1, with weaker archival provenance and only 19.94% of the V1 holdout. Verified same-period bulk forecasts were not obtained for the other commercial systems. Missing values are not guessed. [External comparison](../../docs/COMPARATORS.md).','',
      '## Reproduce and inspect','',
      '[Protocol](../../docs/v2/PROTOCOL.md) · [Reproduction instructions](../../docs/v2/REPRODUCE.md) · [Data audit](../../docs/v2_data_audit.md) · [Source manifest](source_manifest.json) · [All-four selection freeze](selection_freeze.json)','',
      'Retrosheet acknowledgment: The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".','',
      'NFL: Lee Sharpe/nflverse, CC BY 4.0. Soccer: OpenFootball, CC0. Tennis: Jeff Sackmann/Tennis Abstract, preserved by Kadantte, CC BY-NC-SA 4.0. Combined tennis-derived reports are conservatively distributed under CC BY-NC-SA 4.0; independent code remains MIT. See ../../DATA_LICENSES.md.']
    (ROOT/'reports/v2/RESULTS.md').write_text('\n'.join(lines)+'\n')
    shutil.copy2(ROOT/'data/v2/manifest.json',ROOT/'reports/v2/source_manifest.json')
    shutil.copy2(ROOT/'artifacts/v2/SELECTION_FREEZE.json',ROOT/'reports/v2/selection_freeze.json')
    plot_differences(reports,ROOT/'reports/v2/improvement_intervals.svg')
    print('V2 comparison, calibration figures, source manifest and selection freeze published locally')

def write_model_card(sport,report,selection):
    m=report['metrics']['ensemble_calibrated'];raw=report['metrics']['ensemble_raw']
    scope={
      'soccer':'English Premier League: designated home win, draw or away win after full time.',
      'baseball':'MLB regular-season winner, conditional on a completed non-tied game.',
      'football':'NFL regular-season winner, conditional on a completed non-tied game.',
      "tennis":"ATP men's singles winner, conditional on a supported completed score; retirements, walkovers, defaults and unsupported scores are excluded."}
    extra={
      'soccer':'Limited to EPL teams and schedules. Promoted teams can have sparse history. Draw probabilities and sparse reliability bins require particular care.',
      'baseball':'No confirmed starting pitchers, batting lineups, injuries, weather or park features. Suspended results are delayed to completion. Oakland/Athletics historical franchise continuity is documented in the source audit.',
      'football':'No quarterback availability, injuries, depth charts, weather or play-by-play strength. Small annual sample and season changes make uncertainty substantial. Ties are outside the modeled target.',
      'tennis':'Dates are tournament-start proxies. Features are frozen from strictly earlier results delayed by 21 days, conditional on realized matchups whose later-round opponents were not known at tournament start. This is not an actual all-fixtures tournament-start forecast. No injury or verified match-time information; historical last-ten features use a documented deterministic ordering approximation.'}
    weights='\n'.join(f'- {key}: {weight:.6f}' for key,weight in zip(selection['ensemble_names'],selection['ensemble_weights']))
    text=f"""# V2 model card: {sport.title()}

## Intended use and target

{scope[sport]}

Historical research and hypothetical matchup comparison. The output is an estimated
outcome distribution, not a guarantee or a deployed live decision service. Side A
is designated home in team sports; tennis sides are canonicalized by stable IDs
independently of outcome. Input factors are descriptive, not causal explanations.

## Frozen architecture

{len(selection['features'])} finite, explicitly whitelisted pre-event features.
Selected base configurations use three earlier chronological folds. Nonnegative
ensemble weights use out-of-fold predictions; separate later-period temperature
calibration uses no new-test outcomes. The ensemble was the main model before
scoring, regardless of which individual row subsequently ranks first.

{weights}

Ensemble calibration temperature: {selection['temperatures']['ensemble']:.6f}.

Training: {selection['training']['first_date']} to {selection['training']['last_date']}
({selection['training']['n']:,} events). Calibration: {selection['calibration']['first_date']}
to {selection['calibration']['last_date']} ({selection['calibration']['n']:,} events).

## Measured new-period results

Test: {report['test']['first_date']} to {report['test']['last_date']}
({report['test']['n']:,} events).

- Accuracy: {m['accuracy']:.2%}
- Calibrated log loss: {m['log_loss']:.6f}; uncalibrated: {raw['log_loss']:.6f}
- Brier: {m['brier']:.6f}
- Ten-bin top-label ECE: {m['top_label_ece_10_bins']:.6f}
- Ensemble minus refitted V1 log loss: {report['uncertainty_vs_v1_recipe_refit']['model_minus_baseline_log_loss']:+.6f}
- Approximate paired weekly-bootstrap 95% interval: {interval(report['uncertainty_vs_v1_recipe_refit']['difference_95pct_interval'])}

Binary Brier uses positive-class squared error; soccer uses summed classwise
squared error. Calibration is assessed with reliability curves and bin counts,
not inferred from Brier alone. Aggregate intervals do not describe one match.
All candidates and negative results remain in the complete comparison.

## Material limitations

{extra[sport]}

Corrected historical snapshots are not guaranteed as-issued live inputs. Earlier
test outcomes update history only after their availability cutoff; classifiers
remain frozen. Performance under unseen future seasons, rule changes, missing
feeds and new participants requires prospective validation. Subgroup stability,
operational monitoring and service-level reliability are not established.

## Provenance and rights

Selection manifest SHA-256: `{report['selection_manifest_sha256']}`.
The public development report records code, source/data, model and runtime hashes.
Only trust locally generated joblib files. Provider rights remain separate from
the original MIT code; tennis-derived artifacts are conservatively CC BY-NC-SA 4.0.

[All comparisons and reliability](../../../reports/v2/RESULTS.md) ·
[Protocol](../PROTOCOL.md) · [Inference and reproduction](../REPRODUCE.md) ·
[Data rights](../../../DATA_LICENSES.md)
"""
    path=ROOT/'docs/v2/model_cards'/f'{sport}.md';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

def plot_reliability(report,path):
    fig,axes=plt.subplots(1,len(report['classes']),figsize=(5*len(report['classes']),4.4),squeeze=False)
    for i,label in enumerate(report['classes']):
        ax=axes[0,i];ax.plot([0,1],[0,1],'--',color='#aaa')
        for key,color in [('ensemble_calibrated','#285cba'),('v1_recipe_refit_calibrated','#dd8833'),('elo_calibrated','#268571')]:
            bins=report['metrics'][key]['reliability'][i]['bins']
            ax.plot([b['mean_probability'] for b in bins],[b['observed_frequency'] for b in bins],'o-',label=name(key),color=color)
        ax.set(xlim=(0,1),ylim=(0,1),title=label.replace('_',' '),xlabel='Mean probability',ylabel='Observed fraction');ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=7);fig.suptitle(f"{report['sport'].title()}: new-period reliability")
    fig.tight_layout();fig.savefig(path,format='svg',metadata={'Date':None});plt.close(fig)

def plot_differences(reports,path):
    fig,ax=plt.subplots(figsize=(9,4.6))
    for i,sport in enumerate(SPORTS):
        u=reports[sport]['uncertainty_vs_v1_recipe_refit'];d=u['model_minus_baseline_log_loss'];lo,hi=u['difference_95pct_interval']
        ax.errorbar(d,i,xerr=[[max(d-lo,0)],[max(hi-d,0)]],fmt='o',color='#285cba',capsize=5)
    ax.axvline(0,color='#777',linestyle='--');ax.set_yticks(range(len(SPORTS)),[s.title() for s in SPORTS]);ax.invert_yaxis()
    ax.set_xlabel('Ensemble minus refitted V1 log loss (negative favors ensemble)')
    ax.set_title('New-period paired differences with approximate 95% weekly-bootstrap intervals')
    ax.grid(axis='x',alpha=.15);fig.tight_layout();fig.savefig(path,format='svg',metadata={'Date':None});plt.close(fig)
if __name__=='__main__':main()
