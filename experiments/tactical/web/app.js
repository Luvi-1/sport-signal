"use strict";
const $ = id => document.getElementById(id);
let selected = null;
let generation = 0;
const words = value => String(value).replaceAll("_", " ");
const number = value => typeof value === "number" ? value.toLocaleString(undefined, {maximumFractionDigits: 4}) : String(value);
function node(tag, text, cls) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
async function get(path) { const r=await fetch(path,{cache:"no-store"}); const d=await r.json(); if(!r.ok)throw Error(d.error||d.status||"Local artifact unavailable"); return d; }
function table(rows, parent) {
  if (!rows.length) return;
  const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))].filter(k=>rows.some(r=>r[k]===null||["string","number","boolean"].includes(typeof r[k]))).slice(0,7);
  if (!keys.length) return;
  const wrap=node("div",undefined,"table-wrap"), t=node("table"), head=node("thead"), tr=node("tr");
  keys.forEach(k=>tr.append(node("th",words(k)))); head.append(tr);t.append(head);
  const body=node("tbody");rows.slice(0,30).forEach(row=>{const r=node("tr"); keys.forEach(k=>{const v=row[k];r.append(node("td",v===null?"Missing":v===undefined?"—":typeof v==="object"?"See local report":number(v),typeof v==="number"?"number":undefined));});body.append(r);});t.append(body);wrap.append(t);parent.append(wrap);
  if(rows.length>30)parent.append(node("p",`Showing 30 of ${rows.length.toLocaleString()} aggregate rows. Full results remain in the local summary file.`,"small"));
}
function block(label, value, parent, depth=0) {
  if(value===null||value===undefined||depth>2)return;
  const section=node("section",undefined,"summary-section");section.append(node("h4",words(label)));
  if(Array.isArray(value)) {
    if(value.every(x=>x&&typeof x==="object"&&!Array.isArray(x)))table(value,section);
    else {const list=node("ul");value.slice(0,20).forEach(x=>{if(typeof x!=="object")list.append(node("li",number(x)));});section.append(list);}
  } else if(typeof value==="object") {
    const entries=Object.entries(value), nums=entries.filter(([,v])=>typeof v==="number");
    if(nums.length&&nums.length<=16) {const facts=node("div",undefined,"facts");nums.forEach(([k,v])=>{const f=node("div",undefined,"fact");f.append(node("strong",number(v)),node("span",words(k)));facts.append(f);});section.append(facts);}
    else if(nums.length)table(nums.map(([key,count])=>({category:words(key),count})),section);
    entries.filter(([,v])=>typeof v!=="number").slice(0,20).forEach(([k,v])=>{
      if(v&&typeof v==="object")block(k,v,section,depth+1);
      else if(v!==null)section.append(node("p",`${words(k)}: ${number(v)}`,"small"));
    });
  } else section.append(node("p",number(value)));
  if(section.children.length>1)parent.append(section);
}
function observedBars(rows, parent, rateKey, labelKeys) {
  const plot=node("div");plot.setAttribute("role","img");plot.setAttribute("aria-label","Observed development-sample fractions with case counts");
  rows.slice(0,30).forEach(row=>{
    const rate=row[rateKey]; if(typeof rate!=="number"||!Number.isFinite(rate)||rate<0||rate>1)return;
    const label=labelKeys.map(k=>`${words(k)} ${row[k]}`).join(" · ");
    const r=node("div",undefined,"bar-row"),track=node("div",undefined,"bar-track"),bar=node("div",undefined,"bar");
    bar.style.width=`${rate*100}%`;track.append(bar);r.append(node("span",label),track,node("span",`${(rate*100).toFixed(1)}%`,"bar-number"));plot.append(r);
    plot.append(node("p",`${number(row.n)} recorded cases`,"small"));
  });parent.append(plot);
}
function exploration(summary,parent) {
  const tennis=summary.development_direction_counts;
  const football=summary.development_distributions?.tables;
  if(!tennis&&!football)return;
  const section=node("section",undefined,"summary-section");section.append(node("h4","Explore a development-sample context"));
  const label=node("label","Context "),choose=node("select");choose.id="context-select";label.htmlFor=choose.id;label.append(choose);section.append(label);
  const panel=node("div");section.append(panel);
  section.append(node("p","Empirical fractions describe recorded cases. They are not calibrated predictions or effects of changing a player's technique.","small"));
  if(tennis){
    tennis.forEach((r,i)=>{const option=node("option",`${r.task} · ${r.corpus==='m'?'Men':'Women'} · ${r.surface} · ${r.serve_side}`);option.value=String(i);choose.append(option);});
    const draw=()=>{panel.replaceChildren();const r=tennis[Number(choose.value)];if(!r)return;panel.append(node("p",`2010–2022 · ${number(r.eligible_rows)} eligible serves`));
      const rows=Object.entries(r.counts).map(([direction,count])=>({direction,n:count,share:count/r.eligible_rows}));observedBars(rows,panel,"share",["direction"]);};
    choose.addEventListener("change",draw);draw();
  }else{
    football.forEach((r,i)=>{const option=node("option",r.group_by.map(words).join(" + "));option.value=String(i);choose.append(option);});
    const draw=()=>{panel.replaceChildren();const t=football[Number(choose.value)];if(!t)return;panel.append(node("p",`${summary.development_distributions.season} · observed dropback fraction`));observedBars(t.cells,panel,"observed_dropback_fraction",t.group_by);};
    choose.addEventListener("change",draw);draw();
  }parent.append(section);
}
function geometryPlot(summary,parent) {
  const data=summary.development_plot;
  if(!data||!Array.isArray(data.points)||!data.points.length)return;
  const section=node("section",undefined,"summary-section");section.append(node("h4","Recorded development-shot locations"));
  const toggle=node("input");toggle.type="checkbox";toggle.id="outcome-overlay";
  const label=node("label");label.append(toggle,document.createTextNode(" Show later recorded outcome"));section.append(label);
  const wrapper=node("div",undefined,"geometry-plot");section.append(wrapper);
  section.append(node("p",`${data.points.length} deterministic development observations · ${data.coordinate_units}. ${data.sample_method}.`,"small"));
  section.append(node("p","The rectangle is a coordinate plot, not a reconstructed court boundary. Locations and tracking quality retain their provider definitions; outcome overlays are not earlier inputs.","small"));
  const goal=data.attacking_goal||data.offense_normalized_hoop;
  const draw=()=>{
    const width=Math.max(270,Math.round(wrapper.clientWidth||700)),height=Math.max(280,Math.min(400,width*.57)),pad={l:45,r:22,t:22,b:47};
    const pts=data.points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
    const xs=pts.map(p=>p.x),ys=pts.map(p=>p.y);if(goal){xs.push(goal[0]);ys.push(goal[1]);}
    const extent=a=>{const lo=Math.min(...a),hi=Math.max(...a),d=Math.max(1,(hi-lo)*.08);return[lo-d,hi+d]};
    let [xmin,xmax]=extent(xs),[ymin,ymax]=extent(ys);
    // Equal data-unit scaling preserves visible geometric angles/distances.
    const aw=width-pad.l-pad.r,ah=height-pad.t-pad.b;
    const scale=Math.min(aw/(xmax-xmin),ah/(ymax-ymin)),cx=(xmin+xmax)/2,cy=(ymin+ymax)/2;
    xmin=cx-aw/(2*scale);xmax=cx+aw/(2*scale);ymin=cy-ah/(2*scale);ymax=cy+ah/(2*scale);
    const x=v=>pad.l+(v-xmin)/(xmax-xmin)*(width-pad.l-pad.r),y=v=>pad.t+(ymax-v)/(ymax-ymin)*(height-pad.t-pad.b);
    const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox",`0 0 ${width} ${height}`);svg.setAttribute("role","img");svg.setAttribute("aria-label",`Development locations in ${data.coordinate_units}; outcome overlay ${toggle.checked?'shown':'hidden'}`);
    const add=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));if(text)e.textContent=text;svg.append(e);return e;};
    add("rect",{x:pad.l,y:pad.t,width:width-pad.l-pad.r,height:height-pad.t-pad.b,fill:"none",stroke:"#c5d0c8"});
    for(let i=0;i<4;i++){const xv=xmin+(xmax-xmin)*i/3,yv=ymin+(ymax-ymin)*i/3;add("text",{x:x(xv),y:height-pad.b+20,"text-anchor":"middle"},xv.toFixed(0));add("text",{x:pad.l-8,y:y(yv)+4,"text-anchor":"end"},yv.toFixed(0));}
    pts.forEach(p=>{const make=(p.observed_goal??p.observed_make)===1;const circle=add("circle",{cx:x(p.x),cy:y(p.y),r:toggle.checked&&make?4.2:3,fill:toggle.checked&&!make?"none":"#17694c",stroke:toggle.checked&&!make?"#819087":"#17694c","stroke-width":1,opacity:.75});const title=document.createElementNS(ns,"title");title.textContent=`x=${p.x.toFixed(2)}, y=${p.y.toFixed(2)}${toggle.checked?`; recorded ${make?'score':'no score'}`:''}`;circle.append(title);});
    if(goal){add("path",{d:`M ${x(goal[0])-5} ${y(goal[1])} h 10 M ${x(goal[0])} ${y(goal[1])-5} v 10`,stroke:"#a85c24","stroke-width":2,fill:"none"});add("text",{x:x(goal[0]),y:y(goal[1])-11,"text-anchor":"middle"},data.attacking_goal?"Goal":"Hoop");}
    add("text",{x:(pad.l+width-pad.r)/2,y:height-5,"text-anchor":"middle"},summary.sport==='soccer'?"x · standardized native grid":"x · feet");
    add("text",{x:15,y:(pad.t+height-pad.b)/2,transform:`rotate(-90 15 ${(pad.t+height-pad.b)/2})`,"text-anchor":"middle"},summary.sport==='soccer'?"y · native grid":"y · feet");
    wrapper.replaceChildren(svg);
  };
  toggle.addEventListener("change",draw);parent.append(section);draw();if(typeof ResizeObserver!=="undefined")new ResizeObserver(draw).observe(wrapper);
}
function renderSummary(summary) {
  $("summary").replaceChildren();
  geometryPlot(summary,$("summary"));
  exploration(summary,$("summary"));
  // Display only declared aggregate sections; do not render arbitrary raw records or model objects.
  const allowed=["population","scope","source_counts","match_quality","source_quality_counts","development_scope","cohorts","counts","coverage","source_qa","qa","quality","denominators","cohort_quality","exclusions","development","development_distributions","distributions","measurement_caveats","limitations","clocks","units"];
  for(const key of allowed)if(summary[key]!==undefined && !(key==="development_distributions" && summary[key]?.tables))block(key,summary[key],$("summary"));
  if(!$("summary").children.length)$("summary").append(node("p","The verified summary is available locally. Its display adapter is awaiting schema review; no result has been inferred.","small"));
}
function renderMechanics(data) {
  const parent=$("mechanics-content");parent.replaceChildren();
  block("Study population",data.population,parent);
  const section=node("section",undefined,"summary-section");section.append(node("h4","Measured quantities and units"));
  table(data.measurements.map(r=>({quantity:r.label,unit:r.unit,observed:r.observed,missing:r.missing,median:r.median,q10:r.q10,q90:r.q90})),section);parent.append(section);
  const label=node("label","Measurement distribution "),select=node("select");select.id="mechanics-measurement";label.htmlFor=select.id;label.append(select);parent.append(label);
  data.geometry.forEach((r,i)=>{const option=node("option",`${r.definition} (${r.unit||'source units'})`);option.value=String(i);select.append(option);});
  const panel=node("section",undefined,"summary-section");parent.append(panel);
  const draw=()=>{panel.replaceChildren();const g=data.geometry[Number(select.value)];if(!g)return;panel.append(node("p",`${g.definition} · ${g.observed} observed / ${g.denominator} in the declared cohort. ${g.suppression||''}`,"small"));table(g.bins.map(b=>({interval:`${b.lower??'−∞'} to ${b.upper??'∞'}`,count:b.suppressed?'Suppressed':b.count})),panel);};select.addEventListener("change",draw);draw();
  block("Measurement frame",data.measurement_frame,parent);block("Limitations",data.limitations,parent);
  parent.append(node("p",`${data.source.attribution}. ${data.source.license}. ${data.source.modification||''}`,"small"));
}

// Numerical presentation has no inference, model-loading or fitting path. Every
// number below is a strict aggregate from the independently verified local route.
function aggregateTable(headers, rows, caption, parent) {
  const wrap=node("div",undefined,"table-wrap"),t=node("table");
  t.append(node("caption",caption));const head=node("thead"),tr=node("tr");
  headers.forEach(text=>{const th=node("th",text);th.scope="col";tr.append(th);});head.append(tr);t.append(head);
  const body=node("tbody");rows.forEach(row=>{const tr=node("tr");row.forEach((value,index)=>{const cell=node(index===0?"th":"td",value===null?"Unavailable":String(value));if(index===0)cell.scope="row";tr.append(cell);});body.append(tr);});
  t.append(body);wrap.append(t);parent.append(wrap);
}
function choice(id, title, options, parent) {
  const label=node("label",title+" "),select=node("select");select.id=id;label.htmlFor=id;
  options.forEach(([value,text])=>{const option=node("option",text);option.value=value;select.append(option);});
  label.append(select);parent.append(label);return select;
}
function svgPlot(label,width,height) {
  const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");
  svg.setAttribute("viewBox",`0 0 ${width} ${height}`);svg.setAttribute("role","img");svg.setAttribute("aria-label",label);
  const add=(tag,attrs,text)=>{const item=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([key,value])=>item.setAttribute(key,String(value)));if(text!==undefined)item.textContent=text;svg.append(item);return item;};
  add("title",{},label);return {svg,add};
}
const signed=value=>value===null?"Unavailable":`${value>0?"+":""}${number(value)}`;
function gapPlot(rows,unit,parent) {
  const valid=rows.filter(row=>row.delta!==null);if(!valid.length)return;
  const width=820,height=80+valid.length*54,pad=300;
  const {svg,add}=svgPlot(`Same-case model minus reference loss gaps in ${unit}. Negative is favorable; table follows.`,width,height);
  const values=[0,...valid.flatMap(row=>[row.delta,...(row.interval||[]),...(row.sensitivity_range||[])])];
  let lo=Math.min(...values),hi=Math.max(...values);const span=Math.max(hi-lo,.001);lo-=span*.12;hi+=span*.12;
  const x=v=>pad+(v-lo)/(hi-lo)*(width-pad-35);
  add("line",{x1:x(0),x2:x(0),y1:18,y2:height-40,stroke:"#9baaa1","stroke-dasharray":"4 4"});
  valid.forEach((row,index)=>{const y=35+index*54,range=row.interval||row.sensitivity_range;
    add("text",{x:8,y:y-6},`${words(row.model)} − ${words(row.reference)}`);
    add("text",{x:8,y:y+12,"class":"plot-detail"},`${signed(row.delta)} · ${words(row.uncertainty)}`);
    if(range)add("line",{x1:x(range[0]),x2:x(range[1]),y1:y,y2:y,stroke:"#536760","stroke-width":2,"stroke-dasharray":row.sensitivity_range?"4 3":"none"});
    const mark=add("circle",{cx:x(row.delta),cy:y,r:5,fill:row.delta>0?"#a64832":"#17694c"});
    const title=document.createElementNS("http://www.w3.org/2000/svg","title");title.textContent=`${row.model} minus ${row.reference}: ${signed(row.delta)} ${unit}`;mark.append(title);
  });
  for(const tick of [lo,0,hi])add("text",{x:x(tick),y:height-16,"text-anchor":"middle"},signed(tick));
  const wrapper=node("div",undefined,"numerical-plot gap-plot");wrapper.append(svg);parent.append(wrapper);
}
function reliabilityPlot(series,contract,target,parent) {
  const {svg,add}=svgPlot(`Reliability for ${series.model}, class ${series.class}; ${target.cases} cases. Empty bins and support are in the table.`,540,370);
  const x=p=>62+p*430,y=p=>302-p*265;
  add("line",{x1:x(0),x2:x(1),y1:y(0),y2:y(1),stroke:"#9baaa1","stroke-dasharray":"5 4"});
  add("path",{d:`M ${x(0)} ${y(1)} V ${y(0)} H ${x(1)}`,fill:"none",stroke:"#8e9e94"});
  for(const p of [0,.25,.5,.75,1]){add("text",{x:x(p),y:325,"text-anchor":"middle"},number(p));add("text",{x:50,y:y(p)+4,"text-anchor":"end"},number(p));}
  series.bins.forEach((bucket,index)=>{if(!bucket.n)return;const sparse=bucket.n<contract.sparse;
    const marker=add("circle",{cx:x(bucket.mean_probability),cy:y(bucket.observed_fraction),r:Math.min(12,3+Math.sqrt(bucket.n)/8),fill:sparse?"#fff":"#17694c",stroke:sparse?"#aa7227":"#17694c","stroke-width":2});
    const title=document.createElementNS("http://www.w3.org/2000/svg","title");title.textContent=`Bin ${index+1}: n=${bucket.n}; mean p=${number(bucket.mean_probability)}; observed=${number(bucket.observed_fraction)}${sparse?'; low support':''}`;marker.append(title);
  });
  add("text",{x:280,y:355,"text-anchor":"middle"},"Mean saved probability in fixed bin");
  add("text",{x:16,y:170,"text-anchor":"middle",transform:"rotate(-90 16 170)"},"Observed class fraction");
  const wrapper=node("div",undefined,"numerical-plot reliability-plot");wrapper.append(svg);parent.append(wrapper);
  parent.append(node("p",`Hollow amber markers: fewer than ${contract.sparse} cases. Marker size reflects case support, not certainty. The diagonal is a reference, not proof of calibration.`,"small"));
  aggregateTable(["Fixed probability bin","Cases","Clusters","Mean probability","Observed fraction","Support"],series.bins.map((bucket,index)=>[
    `${number(contract.bins[index])} to ${number(contract.bins[index+1])}${index===series.bins.length-1?" (includes 1)":" (upper excluded)"}`,
    number(bucket.n),bucket.clusters===null?"Not reported":number(bucket.clusters),bucket.mean_probability===null?"Empty":number(bucket.mean_probability),
    bucket.observed_fraction===null?"Empty":number(bucket.observed_fraction),!bucket.n?"Empty":bucket.n<contract.sparse?"Low support":"Reported"]),
    `Aggregate reliability bins · ${words(series.model)} · class ${series.class}`,parent);
}
function numericalAttribution(task,parent) {
  // Source-controlled credits, independent of optional descriptive artifacts.
  const sources={
    soccer:{credit:"Data provided by StatsBomb. Noncommercial research under the StatsBomb custom agreement; attribution and logo requirements apply.",url:"https://github.com/statsbomb/open-data",notices:[["statsbomb_notice","StatsBomb agreement and notice"]]},
    basketball:{credit:"SkillCorner basketball open data. Source-derived aggregate material: MIT, with the original SkillCorner notice retained.",url:"https://github.com/SkillCorner/opendata-basketball",notices:[["skillcorner_notice","SkillCorner MIT notice"]]},
    baseball:{credit:'The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org". Original project analysis: MIT; upstream rights are not reassigned.',url:"https://www.retrosheet.org/",notices:[["retrosheet_notice","Retrosheet required attribution"]]},
    football:{credit:"FTN Data via nflverse. Source-derived aggregate material: CC BY-SA 4.0; underlying nflverse play-by-play retains CC BY 4.0 credit.",url:"https://nflverse.nflverse.com/",notices:[["nflverse_ftn_notice","FTN CC BY-SA 4.0 notice"],["nflverse_pbp_notice","Play-by-play CC BY 4.0 notice"]]},
    tennis:{credit:"Jeff Sackmann, Tennis Abstract, the Match Charting Project and its volunteer contributors. Source-derived aggregate material: CC BY-NC-SA 4.0.",url:"https://github.com/JeffSackmann/tennis_MatchChartingProject",notices:[["mcp_notice","MCP CC BY-NC-SA 4.0 notice"]]},
    baseball_mechanics:{credit:"Driveline Baseball OpenBiomechanics Project and contributors. Source-derived aggregate material: CC BY-NC-SA 4.0 with the additional professional-sports-organization / financial-analysis-firm affiliation exclusion. Employees, contractors, associated parties and significant shareholders covered by that condition require a specific written paid license for any use. See the complete source condition.",url:"https://github.com/drivelineresearch/openbiomechanics",notices:[["openbiomechanics_license","Complete OpenBiomechanics license and affiliation exclusion"],["mechanics_attribution","Laboratory source credits and modifications"]]},
    tennis_execution:{credit:"Nate Sandholtz and the authors/contributors of the BYU byu_tennis_serves study. MIT, copyright 2026 Nate Sandholtz. Participant privacy safeguards apply separately; individual records are excluded.",url:"https://github.com/nsandholtz/byu_tennis_serves",notices:[["byu_license","Nate Sandholtz / BYU MIT notice"],["mechanics_attribution","Laboratory source credits and modifications"]]}
  };
  const source=sources[task],section=node("section",undefined,"numerical-attribution");
  section.append(node("h4","Source credit and reuse conditions"),node("p",source.credit));
  const provider=node("a","Provider source");provider.href=source.url;provider.rel="noreferrer";section.append(provider);
  for(const [key,label] of [...source.notices,["license_scope","Exact scope of derived-material licenses"]]){
    section.append(node("span"," · "));const link=node("a",label);link.href=`/api/document/${key}`;
    link.addEventListener("click",event=>{event.preventDefault();documentView(key);});section.append(link);
  }
  section.append(node("p","Project transformations and source-specific conditions are documented in these notices. No provider endorsement is implied; the software license does not replace the source terms.","small"));parent.append(section);
}
function renderNumerical(view,parent) {
  parent.replaceChildren();const c=view.contract;
  // Prespecified display defaults, never JSON insertion order or final-score ranking.
  const primary={soccer:["goal","matched","log_loss"],basketball:["make","event_geometry","log_loss"],
    baseball:["swing","eligible","log_loss"],football:["dropback","eligible","log_loss"],
    tennis:["A1_m","eligible","log_loss"],baseball_mechanics:["exit_velocity","adult_paired","macro_MAE"],
    tennis_execution:["joint_execution","nonlet","joint_NLL_equal_player"]}[view.task];
  const snapshot=view.delivery_mode==="audited_aggregate_snapshot";
  parent.append(node("p",`${snapshot?"Audited aggregate-only snapshot":"Independently verified final aggregate"} · ${c.name}`,"verified-result"));
  numericalAttribution(view.task,parent);
  if(snapshot)parent.append(node("p","This is a hash-verified, independently audited aggregate snapshot. It contains no trained weights or current live model. Source data, private run artifacts and original audit records are not included; their provenance is attested by the distribution review.","small numerical-caveat"));
  const dl=node("dl");[["Population",c.population],["Unit",c.unit],["Evaluation",c.design]].forEach(([label,value])=>dl.append(node("dt",label),node("dd",value)));parent.append(dl);
  view.notices.concat(c.caveats).forEach(text=>parent.append(node("p",text,"small numerical-caveat")));
  const missing=[];for(const id of Object.keys(c.targets))for(const cohort of Object.keys(c.cohorts))if(!view.targets.some(target=>target.id===id&&target.cohort===cohort))missing.push(`${c.targets[id]} · ${c.cohorts[cohort]}`);
  if(missing.length){const details=node("details");details.append(node("summary","Target/cohort results not supplied"));const list=node("ul");missing.forEach(text=>list.append(node("li",`${text}: unavailable`)));details.append(list);parent.append(details);}
  const select=choice(`${view.task}-target`,"Target and denominator",view.targets.map((target,index)=>[String(index),`${c.targets[target.id]} · ${c.cohorts[target.cohort]}`]),parent);
  const primaryIndex=view.targets.findIndex(target=>target.id===primary[0]&&target.cohort===primary[1]);
  if(primaryIndex>=0)select.value=String(primaryIndex);
  else {
    // Missing primary evidence remains explicit. The fallback is label-ordered,
    // independent of serialized array order and every reported outcome.
    const fallback=view.targets.map((target,index)=>({key:`${target.id}/${target.cohort}`,index})).sort((a,b)=>a.key<b.key?-1:a.key>b.key?1:0)[0];
    select.value=String(fallback.index);
    parent.append(node("p",`Prespecified primary target/cohort unavailable: ${c.targets[primary[0]]} · ${c.cohorts[primary[1]]}. Showing another reported cohort; this does not replace the primary result.`,"small numerical-caveat"));
  }
  const panel=node("div",undefined,"target-result");parent.append(panel);
  const draw=()=>{
    panel.replaceChildren();const target=view.targets[Number(select.value)];
    panel.append(node("h4",c.targets[target.id]));panel.append(node("p",`${c.cohorts[target.cohort]} · ${number(target.cases)} cases · ${number(target.clusters)} ${c.cluster_unit}. Every model comparison uses the same frozen case set.`,"denominator"));
    const expected=c.models.filter(name=>view.task!=="soccer"||name.startsWith(target.cohort+"_"));
    const absent=expected.filter(name=>!target.models.some(model=>model.id===name));
    if(absent.length)panel.append(node("p",`No verified procedure results supplied for: ${absent.map(words).join(", ")}.`,"small"));
    const available=[...new Set(target.models.flatMap(model=>Object.keys(model.metrics)))];
    const metricKeys=[primary[2],...available.filter(key=>key!==primary[2])];
    const metricChoice=choice(`${view.task}-metric`,"Metric",metricKeys.map(key=>[key,`${view.metrics[key].label} (${view.metrics[key].unit})`]),panel);
    metricChoice.value=primary[2]; // Absent primary scores render unavailable, not a secondary success.
    const metricPanel=node("div",undefined,"metric-result");panel.append(metricPanel);
    const drawMetric=()=>{
      metricPanel.replaceChildren();const key=metricChoice.value,definition=view.metrics[key];
      metricPanel.append(node("p",`${definition.label} · ${definition.unit} · ${definition.direction==="diagnostic"?"Diagnostic only":`${definition.direction} is better`}. This scale applies only to the selected target.`,"metric-definition"));
      aggregateTable(["Model / feature block","Value","Cases",words(c.cluster_unit),"Availability"],target.models.map(model=>{const score=model.metrics[key];return [words(model.id),score?.value===null||score===undefined?"Unavailable":number(score.value),score?number(score.cases):"—",score?number(score.clusters):"—",score?words(score.status):"Not reported"];}),"Same-case model results; unavailable procedures stay explicit",metricPanel);
      const comparisons=target.comparisons.filter(row=>row.metric===key);
      if(comparisons.length){
        metricPanel.append(node("h4","Paired gaps against fixed references"));gapPlot(comparisons,definition.unit,metricPanel);
        aggregateTable(["Model − reference","Loss gap","Uncertainty","Interpretation"],comparisons.map(row=>{
          const interval=row.interval?`${number(row.confidence*100)}% interval [${signed(row.interval[0])}, ${signed(row.interval[1])}]`:row.sensitivity_range?`Five omission sensitivity range [${signed(row.sensitivity_range[0])}, ${signed(row.sensitivity_range[1])}]; not a confidence interval`:"Interval unavailable";
          const finding=row.delta===null?"Comparison unavailable":row.delta>0?"Worse than reference":row.delta===0?"Tied with reference":row.criterion_met===false?"No demonstrated prespecified improvement":"Favorable estimated gap; criterion conclusion not established by this display";
          return [`${words(row.model)} − ${words(row.reference)}`,signed(row.delta),`${words(row.uncertainty)}; ${interval}`,finding];}),"Negative loss gap is favorable; a negative final result never selects a replacement model",metricPanel);
      }else metricPanel.append(node("p","No independently verified paired contrast is reported for this metric. Separate marginal values do not establish uncertainty for their difference.","small"));
    };
    metricChoice.addEventListener("change",drawMetric);drawMetric();
    panel.append(node("h4","Reliability and support"));
    if(target.reliability.length){
      const choose=choice(`${view.task}-reliability`,"Model and class",target.reliability.map((series,index)=>[String(index),`${words(series.model)} · ${series.class}`]),panel);
      const reliability=node("div",undefined,"reliability-result");panel.append(reliability);
      const drawReliability=()=>{reliability.replaceChildren();reliabilityPlot(target.reliability[Number(choose.value)],c,target,reliability);};
      choose.addEventListener("change",drawReliability);drawReliability();
    }else panel.append(node("p","Reliability bins are not reported for this target. No calibration chart or synthetic probabilities have been substituted.","small"));
  };
  select.addEventListener("change",draw);draw();
  const definitions=node("details");definitions.append(node("summary","Metric definitions and uncertainty limits"));view.definitions.forEach(text=>definitions.append(node("p",text)));definitions.append(node("p","Intervals describe conditional sampling uncertainty only. They do not account for model selection, measurement error or transfer to a different population."));parent.append(definitions);
  const factors=node("div",undefined,"grid numerical-factors");for(const [title,items] of [["Measured feature blocks",c.factors],["Unavailable factors",c.unavailable]]){const section=node("section");section.append(node("h4",title));const ul=node("ul");items.forEach(text=>ul.append(node("li",text)));section.append(ul);factors.append(section);}parent.append(factors);
}
async function loadNumerical(task,parent,current) {
  parent.replaceChildren(node("p","Checking independent final-report verification…","small"));
  try{const data=await get(`/api/model-view/${task}`);if(current!==generation)return;if(data.status!=="verified_final_available"||!data.view)throw Error("invalid_final_artifact");renderNumerical(data.view,parent);}
  catch(error){if(current!==generation)return;const invalid=error.message==="invalid_final_artifact";parent.replaceChildren(node("p",invalid?"Final-report verification failed. Numerical results are withheld; the source/parser views remain available.":"Numerical results are unavailable until a completed final report and its aggregate projection have passed independent, hash-bound verification. No result is inferred from development status.",invalid?"error":"small"));}
}

async function select(sport) {
  selected=sport;const current=++generation;
  $("mechanics-panel").hidden=true;$("mechanics-content").replaceChildren();
  $("numerical-companion-panel").hidden=true;$("numerical-companion-content").replaceChildren();
  loadNumerical(sport.id,$("numerical-content"),current);
  const numericalCompanion={baseball:"baseball_mechanics",tennis:"tennis_execution"}[sport.id];
  if(numericalCompanion){$("numerical-companion-panel").hidden=false;loadNumerical(numericalCompanion,$("numerical-companion-content"),current);}
  document.querySelectorAll("#sports button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.sport===sport.id)));
  $("content").hidden=false;$("sport-name").textContent=sport.name;$("question").textContent=sport.question;
  $("status").textContent=sport.status==="descriptive_available"?"Source/parser results ready":"Source/parser stage";
  const contract=$("contract");contract.replaceChildren();
  for(const [label,value] of [["Population",sport.population],["Unit",sport.unit],["Observation",sport.cutoff],["Measurement",sport.measurement]])contract.append(node("dt",label),node("dd",value));
  $("mechanism").textContent=sport.mechanism;$("companion").textContent=sport.companion;$("missing").replaceChildren(...sport.unavailable.map(v=>node("li",v)));
  $("provider-attribution").hidden=sport.id!=="soccer";if(sport.id==="soccer")$("provider-logo").src="/provider/statsbomb-logo.png";else $("provider-logo").removeAttribute("src");
  $("source").href=sport.source;$("credit").textContent=sport.credit;$("summary").replaceChildren();$("summary-state").className="";
  $("summary-state").textContent="Reading verified local aggregate summary…";
  try {const d=await get(`/api/summary/${sport.id}`);if(current!==generation)return;$("summary-state").textContent="Verified local summary. Target/context descriptions are restricted to the declared development period; later cohorts contribute source-quality checks only.";renderSummary(d.summary);}
  catch(e){if(current!==generation)return;const invalid=["integrity_mismatch","invalid_artifact"].includes(e.message);$("summary-state").className=invalid?"error":"";$("summary-state").textContent=invalid?"Artifact verification failed. Regenerate and review the summary before indexing it again.":"This parser's reviewed summary has not been indexed in this installation. No prediction or synthetic result is substituted.";}
  const companion={baseball:"baseball_mechanics",tennis:"tennis_execution"}[sport.id];
  if(companion){
    try{const d=await get(`/api/summary/${companion}`);if(current!==generation)return;$("mechanics-panel").hidden=false;$("mechanics-state").textContent="Aggregate physical-measurement descriptions from a separate practice/laboratory population. Independently verified numerical evidence, if available, is shown separately below.";renderMechanics(d.summary);}
    catch(e){if(current!==generation)return;$("mechanics-panel").hidden=false;$("mechanics-state").textContent="The separate mechanics summary is not available or its integrity check needs renewal. No measurements are inferred from match records.";}
  }
}
let documentGeneration=0;
async function documentView(key) {
  const current=++documentGeneration;
  $("document-title").textContent="Research document";$("document-text").textContent="Loading…";if(!$("document").open)$("document").showModal();
  try{const d=await get(`/api/document/${key}`);if(current!==documentGeneration||!$("document").open)return;$("document-title").textContent=words(d.title);$("document-text").textContent=d.text;}catch(e){if(current===documentGeneration&&$("document").open)$("document-text").textContent=e.message;}
}
$("close-document").addEventListener("click",()=>{documentGeneration++;$("document").close();});
$("document").addEventListener("cancel",()=>{documentGeneration++;});
$("sport-doc").addEventListener("click",()=>selected&&documentView(selected.id));
document.querySelectorAll("[data-doc]").forEach(b=>b.addEventListener("click",()=>documentView(b.dataset.doc)));
get("/api/catalog").then(data=>{$("notice").textContent=data.notice;data.sports.forEach(sport=>{const b=node("button",sport.name);b.type="button";b.dataset.sport=sport.id;b.setAttribute("aria-pressed","false");b.addEventListener("click",()=>select(sport));$("sports").append(b);});select(data.sports[0]);}).catch(e=>{$("notice").textContent=e.message;$("notice").classList.add("error");});
