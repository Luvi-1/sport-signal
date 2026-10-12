// Synthetic numerical UI tests only. No network, numerical runner, fitting,
// target cache, final report, review file or research artifact is opened/written.
// Optional existing dependency: artifacts/tactical/domqa/node_modules/jsdom.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const {JSDOM}=require(path.join(root,'artifacts/tactical/domqa/node_modules/jsdom'));
const python=process.env.PYTHON||'python';
const data=JSON.parse(execFileSync(python,['-c',`
import sys, json, copy
sys.path.insert(0, 'tests')
from test_tactical_model_views import synthetic_ui_view
from experiments.tactical import model_views as v, workbench as w
views = {task: synthetic_ui_view(task) for task in v.TASKS}
# Reordered fixtures test default selection against canonical/scrambled input.
soccer = copy.deepcopy(views['soccer']['targets'][0]); soccer['cohort'] = 'matched'
for model in soccer['models']: model['id'] = model['id'].replace('full_', 'matched_')
for row in soccer['comparisons']:
    for key in ('model', 'reference'): row[key] = row[key].replace('full_', 'matched_')
for row in soccer['reliability']: row['model'] = row['model'].replace('full_', 'matched_')
views['soccer']['targets'].append(soccer)
fallback = copy.deepcopy(views['basketball']['targets'][0]); fallback['cohort'] = 'all_releases_with_A_fallback'
views['basketball']['targets'].append(fallback)
for task in ('basketball', 'baseball', 'tennis'): views[task]['targets'].reverse()
for task, view in views.items():
    for target in view['targets']:
        metric = 'row_MAE' if task == 'baseball_mechanics' else 'net_Brier_equal_player' if task == 'tennis_execution' else 'brier'
        for model in target['models']:
            model['metrics'][metric] = dict(value=.2, cases=target['cases'], clusters=target['clusters'], status='reported')
        target['comparisons'].append(dict(model=target['models'][1]['id'], reference=target['models'][0]['id'], metric=metric, delta=0, interval=None, confidence=None, uncertainty='not_available', sensitivity_range=None, criterion_met=False))
        if task == 'basketball':
            target['comparisons'][0].update(uncertainty='five_game_leave_one_out', sensitivity_range=[-.02, .2])
        elif task == 'tennis':
            target['comparisons'][0].update(uncertainty='paired_match_bootstrap', interval=[-.02, .2], confidence=.9875)
        if task not in ('baseball_mechanics', 'tennis_execution'):
            target['models'][0]['metrics']['auroc'] = dict(value=None, cases=target['cases'], clusters=target['clusters'], status='undefined_single_class')
            for model in target['models']:
                model['metrics']['accuracy'] = dict(value=.7, cases=target['cases'], clusters=target['clusters'], status='reported')
        for model in target['models']:
            model['metrics'] = dict(sorted(model['metrics'].items(), reverse=task in ('baseball_mechanics', 'tennis_execution')))
    v.validate_view(task, {key: view[key] for key in ('schema_version','task','phase','targets')})
print(json.dumps(dict(views=views,catalog=dict(notice='SYNTHETIC TEST ONLY',sports=[dict(s,status='not_indexed') for s in w.CATALOG]))))
`],{cwd:root,encoding:'utf8'}));
const html=fs.readFileSync(path.join(root,'experiments/tactical/web/index.html'),'utf8');
const dom=new JSDOM(html,{url:'http://127.0.0.1:8765',runScripts:'outside-only'});
const requests=[],overrides=new Map(),deferred=new Map();
const result=(body,ok=true)=>({ok,json:async()=>body});
function ordinary(url){
 if(overrides.has(url))return overrides.get(url);
 if(url==='/api/catalog')return result(data.catalog);
 if(url.startsWith('/api/model-view/'))return result({status:'verified_final_available',view:data.views[url.split('/').pop()]});
 if(url.startsWith('/api/summary/'))return result({status:'not_available'},false);
 if(url.startsWith('/api/document/'))return result({title:url.split('/').pop(),text:'Synthetic document '+url});
 throw Error('Unexpected route '+url);
}
dom.window.fetch=async url=>{requests.push(url);if(deferred.has(url))return new Promise(resolve=>deferred.set(url,resolve));return ordinary(url);};
dom.window.HTMLDialogElement.prototype.showModal=function(){assert(!this.open,'Repeated showModal on an open dialog');this.open=true;};
dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;};
dom.window.eval(fs.readFileSync(path.join(root,'experiments/tactical/web/app.js'),'utf8'));
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const doc=dom.window.document;
const clickSport=async id=>{doc.querySelector(`[data-sport="${id}"]`).click();await flush();};
const change=(id,value)=>{const select=doc.getElementById(id);assert(select,id+' exists');select.value=value;select.dispatchEvent(new dom.window.Event('change'));};
(async()=>{
 await flush();
 assert.equal(doc.querySelectorAll('#sports button').length,5);
 for(const id of ['soccer','basketball','baseball','football','tennis']){
  await clickSport(id);
  const primary={soccer:['goal','matched'],basketball:['make','event_geometry'],baseball:['swing','eligible'],football:['dropback','eligible'],tennis:['A1_m','eligible']}[id];
  const selected=data.views[id].targets[Number(doc.getElementById(id+'-target').value)];
  assert.deepEqual([selected.id,selected.cohort],primary,'Fixed primary target/cohort independent of input ordering');
  assert.equal(doc.getElementById(id+'-metric').value,'log_loss','Accuracy-first JSON must not choose accuracy');
  assert(doc.querySelector('#numerical-content').textContent.includes(data.views[id].contract.population));
  assert(doc.querySelector('#numerical-content').textContent.includes(data.views[id].contract.unit));
  assert(doc.querySelector('#numerical-content').textContent.includes('Worse than reference'));
  assert(doc.querySelector('#summary-state').textContent.includes('No prediction or synthetic result'));
  assert.equal(doc.querySelectorAll('#sports button[aria-pressed=true]').length,1);
  assert(doc.querySelector('#numerical-content').textContent.includes('Performance-blind after source QA'));
  assert(doc.querySelector('#numerical-content').textContent.includes('no causal coaching'));
  assert(doc.querySelector('#numerical-content .reliability-plot svg').getAttribute('aria-label').includes('Reliability'));
  const tableText=doc.querySelector('#numerical-content .reliability-result').textContent;
  assert(tableText.includes('Empty')&&tableText.includes('Low support')&&tableText.includes('Cases'));
  assert(doc.querySelector('#numerical-content .gap-plot svg').getAttribute('aria-label').includes('Negative is favorable'));
  change(id+'-metric','brier');
  assert(doc.querySelector('#numerical-content .metric-result').textContent.includes('Tied with reference'));
  change(id+'-metric','auroc');
  assert(doc.querySelector('#numerical-content .metric-result').textContent.includes('Unavailable'));
  assert(!doc.querySelector('#numerical-content .metric-result .gap-plot'));
  assert(doc.querySelector('#numerical-content').textContent.includes('Unavailable factors'));
  assert(!doc.querySelector('#numerical-content').textContent.includes('SYNTHETIC PRIVATE SENTINEL'));
 }
 await clickSport('basketball');
 assert(doc.querySelector('#numerical-content').textContent.includes('Target/cohort results not supplied'));
 assert(doc.querySelector('#numerical-content').textContent.includes('Five-game prequential'));
 assert(doc.querySelector('#numerical-content .metric-result').textContent.includes('not a confidence interval'));
 await clickSport('football');
 assert(doc.querySelector('#numerical-content').textContent.includes('Retrospective at-snap'));
 await clickSport('tennis');
 assert(doc.querySelector('#numerical-content').textContent.includes('21-day availability is an assumption'));
 assert(doc.querySelector('#numerical-content .metric-result').textContent.includes('98.75% interval'));
 assert.equal(doc.getElementById('tennis-target').options.length,4);
 change('tennis-target',String(data.views.tennis.targets.findIndex(target=>target.id==='A2_w')));assert(doc.querySelector('#numerical-content .target-result h4').textContent.includes("women's corpus"));
 change('tennis-reliability','2');assert(doc.querySelector('#numerical-content .reliability-plot svg').getAttribute('aria-label').includes('class T'));
 assert(!doc.querySelector('#numerical-companion-panel').hidden);
 let companion=doc.querySelector('#numerical-companion-content');
 assert.equal(doc.getElementById('tennis_execution-metric').value,'joint_NLL_equal_player');
 assert(companion.textContent.includes('548 non-lets = 437 observed bounces + 111 net-censored'));
 assert(companion.textContent.includes('All eight individual and pseudonymous player/fold records are suppressed'));
 assert(!companion.querySelector('.reliability-plot'));
 assert.equal(companion.querySelectorAll('tbody tr').length,3); // two model aggregates and one contrast, no player rows
 await clickSport('baseball');companion=doc.querySelector('#numerical-companion-content');
 assert.equal(doc.getElementById('baseball_mechanics-metric').value,'macro_MAE');
 assert(companion.textContent.includes('adult-only paired cohort'));
 assert(companion.textContent.includes('571 cases · 82 athletes'));
 assert(companion.textContent.includes('mph'));
 assert(!companion.querySelector('.reliability-plot'));
 await clickSport('soccer');
 assert(doc.querySelector('#numerical-companion-panel').hidden);
 assert(!doc.querySelector('#provider-attribution').hidden);
 assert.equal(doc.querySelector('#provider-logo').getAttribute('src'),'/provider/statsbomb-logo.png');
 // Missing primary evidence stays visibly unavailable, not replaced by a score.
 const missingPrimary=JSON.parse(JSON.stringify(data.views.soccer));
 missingPrimary.targets=missingPrimary.targets.filter(target=>target.cohort==='full');
 for(const model of missingPrimary.targets[0].models)delete model.metrics.log_loss;
 missingPrimary.targets[0].comparisons=missingPrimary.targets[0].comparisons.filter(row=>row.metric!=='log_loss');
 overrides.set('/api/model-view/soccer',result({status:'verified_final_available',view:missingPrimary}));
 await clickSport('soccer');assert(doc.querySelector('#numerical-content').textContent.includes('Prespecified primary target/cohort unavailable'));
 assert.equal(doc.getElementById('soccer-metric').value,'log_loss');
 assert(doc.querySelector('#numerical-content .metric-result').textContent.includes('Unavailable'));
 overrides.delete('/api/model-view/soccer');
 // Explicit closed/invalid states never replace the descriptive fallback with numbers.
 overrides.set('/api/model-view/soccer',result({status:'invalid_final_artifact',view:null},false));
 await clickSport('soccer');assert(doc.querySelector('#numerical-content').textContent.includes('verification failed'));
 assert.equal(doc.querySelector('#numerical-content').querySelectorAll('table,svg').length,0);
 overrides.set('/api/model-view/soccer',result({status:'awaiting_independent_final_review',view:null},false));
 await clickSport('soccer');assert(doc.querySelector('#numerical-content').textContent.includes('No result is inferred from development status'));
 overrides.delete('/api/model-view/soccer');
 // Clearly distinguish detached audited aggregate snapshots from full-local verified views.
 data.views.soccer.delivery_mode='audited_aggregate_snapshot';await clickSport('soccer');
 assert(doc.querySelector('#numerical-content').textContent.includes('Audited aggregate-only snapshot'));
 assert(doc.querySelector('#numerical-content').textContent.includes('no trained weights or current live model'));
 data.views.soccer.delivery_mode='verified_local_final';
 // All seven numerical panels retain credits/notice links with no summaries.
 const credits={soccer:['StatsBomb','statsbomb_notice'],basketball:['SkillCorner','skillcorner_notice'],baseball:['Retrosheet','retrosheet_notice'],football:['FTN Data via nflverse','nflverse_ftn_notice'],tennis:['Jeff Sackmann','mcp_notice'],baseball_mechanics:['Driveline Baseball OpenBiomechanics','openbiomechanics_license'],tennis_execution:['Nate Sandholtz','byu_license']};
 for(const view of Object.values(data.views))view.delivery_mode='audited_aggregate_snapshot';
 for(const sport of ['soccer','basketball','baseball','football','tennis']){
  await clickSport(sport);
  for(const task of [sport,...({baseball:['baseball_mechanics'],tennis:['tennis_execution']}[sport]||[])]){
   const panel=doc.querySelector(task===sport?'#numerical-content':'#numerical-companion-content'),attribution=panel.querySelector('.numerical-attribution');
   assert(panel.textContent.includes('Audited aggregate-only snapshot'));
   assert(attribution.textContent.includes(credits[task][0]));
   assert(attribution.querySelector('a[href^="https://"]'));
   assert(attribution.querySelector('a[href="/api/document/license_scope"]'));
   const notice=attribution.querySelector(`a[href="/api/document/${credits[task][1]}"]`);assert(notice);notice.click();await flush();
   assert(doc.querySelector('#document-text').textContent.includes('/'+credits[task][1]));doc.querySelector('#close-document').click();
   if(task==='baseball_mechanics'){assert(attribution.textContent.includes('CC BY-NC-SA 4.0'));assert(attribution.textContent.includes('affiliation exclusion'));}
   if(task==='tennis_execution')assert(attribution.textContent.includes('MIT'));
  }
 }
 for(const view of Object.values(data.views))view.delivery_mode='verified_local_final';
 // A slow old view/summary cannot overwrite newer navigation.
 deferred.set('/api/model-view/soccer',null);deferred.set('/api/summary/soccer',null);
 doc.querySelector('[data-sport="soccer"]').click();await flush();
 await clickSport('football');
 deferred.get('/api/model-view/soccer')(ordinary('/api/model-view/soccer'));
 deferred.get('/api/summary/soccer')(result({summary:{counts:{stale_sentinel:999}}}));
 deferred.clear();await flush();
 assert.equal(doc.querySelector('#sport-name').textContent,'American football');
 assert(doc.querySelector('#numerical-content').textContent.includes('Retrospective at-snap'));
 assert(!doc.querySelector('#summary').textContent.includes('stale sentinel'));
 // Repeated/new document requests and close/reopen discard outdated responses.
 deferred.set('/api/document/research',null);
 doc.querySelector('[data-doc="research"]').click();await flush();
 doc.querySelector('[data-doc="method"]').click();await flush();
 assert(doc.querySelector('#document-text').textContent.includes('/method'));
 deferred.get('/api/document/research')(result({title:'old',text:'STALE DOCUMENT'}));deferred.clear();await flush();
 assert(!doc.querySelector('#document-text').textContent.includes('STALE'));
 doc.querySelector('#close-document').click();assert(!doc.querySelector('#document').open);
 deferred.set('/api/document/research',null);doc.querySelector('[data-doc="research"]').click();await flush();
 doc.querySelector('#close-document').click();
 doc.querySelector('[data-doc="model_views"]').click();await flush();
 deferred.get('/api/document/research')(result({title:'closed',text:'STALE CLOSED DOCUMENT'}));deferred.clear();await flush();
 assert(doc.querySelector('#document-text').textContent.includes('/model_views'));
 doc.querySelector('#close-document').click();
 for(const table of doc.querySelectorAll('#numerical-content table')){
  assert(table.querySelector('caption'));assert(table.querySelector('th[scope="col"]'));assert(table.querySelector('th[scope="row"]'));
 }
 assert(!doc.querySelector('script[src^="http"],link[href^="http"]'));
 assert(requests.every(url=>/^\/api\/(catalog$|model-view\/[a-z_]+$|summary\/[a-z_]+$|document\/[a-z_]+$)/.test(url)));
 console.log('PASS: synthetic seven-study numerical DOM; target/metric/class selectors; supported/sparse/empty reliability; same-case gaps, ties and negative findings; scoped units; lab privacy/censoring; closed/invalid and snapshot states; stale navigation and dialog races; captions and local-only requests. Not visual/browser QA.');
 dom.window.close();
})().catch(error=>{console.error(error);process.exitCode=1;dom.window.close();});
