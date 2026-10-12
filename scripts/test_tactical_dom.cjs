// Optional test dependency: npm install --prefix artifacts/tactical/domqa --ignore-scripts jsdom@26.1.0
// Real local aggregate fixtures are generated separately; this is not browser visual QA.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const {JSDOM}=require(path.join(root,'artifacts/tactical/domqa/node_modules/jsdom'));
const fixtures=JSON.parse(fs.readFileSync(path.join(root,'artifacts/tactical/domqa/fixtures.json'),'utf8'));
const html=fs.readFileSync(path.join(root,'experiments/tactical/web/index.html'),'utf8');
const dom=new JSDOM(html,{url:'http://127.0.0.1:8765',runScripts:'outside-only'});
let requests=[];
dom.window.fetch=async url=>{requests.push(url);return {ok:url in fixtures,json:async()=>fixtures[url]||{error:'not_available'}};};
dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;};
dom.window.eval(fs.readFileSync(path.join(root,'experiments/tactical/web/app.js'),'utf8'));
const flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 await flush(); const doc=dom.window.document;
 assert.equal(doc.querySelectorAll('#sports button').length,5);
 for(const button of doc.querySelectorAll('#sports button')){
  button.click();await flush();assert.equal(doc.querySelector('#sport-name').textContent,button.textContent);
  assert.equal(doc.querySelectorAll('#sports button[aria-pressed="true"]').length,1);
 }
 doc.querySelector('[data-sport="soccer"]').click();await flush();
 assert.equal(doc.querySelectorAll('.geometry-plot circle').length,200);
 assert.equal(doc.querySelector('#provider-attribution').hidden,false);
 assert.equal(doc.querySelector('#provider-logo').getAttribute('src'),'/provider/statsbomb-logo.png');
 const overlay=doc.querySelector('#outcome-overlay');overlay.checked=true;overlay.dispatchEvent(new dom.window.Event('change'));
 assert(doc.querySelector('.geometry-plot svg').getAttribute('aria-label').includes('shown'));
 doc.querySelector('[data-sport="basketball"]').click();await flush();
 assert.equal(doc.querySelectorAll('.geometry-plot circle').length,200);
 assert.equal(doc.querySelector('#provider-attribution').hidden,true);
 doc.querySelector('[data-sport="football"]').click();await flush();
 let select=doc.querySelector('#context-select');assert(select);assert(select.options.length>2);
 select.value='1';select.dispatchEvent(new dom.window.Event('change'));
 assert(doc.querySelector('.bar-row').textContent.includes('PISTOL'));
 const width=doc.querySelector('.bar').style.width;assert(parseFloat(width)>0&&parseFloat(width)<100);
 doc.querySelector('[data-sport="tennis"]').click();await flush();
 select=doc.querySelector('#context-select');assert(select);select.value='1';select.dispatchEvent(new dom.window.Event('change'));
 assert(doc.querySelectorAll('.bar-row').length===3);
 assert.equal(doc.querySelector('#mechanics-panel').hidden,false);
 assert(doc.querySelector('#mechanics-measurement option'));
 doc.querySelector('#mechanics-measurement').value='1';doc.querySelector('#mechanics-measurement').dispatchEvent(new dom.window.Event('change'));
 doc.querySelector('[data-doc="research"]').click();await flush();assert(doc.querySelector('#document').open);
 assert(doc.querySelector('#document-text').textContent.includes('Executive finding'));
 doc.querySelector('#close-document').click();assert(!doc.querySelector('#document').open);
 assert(requests.every(r=>r.startsWith('/api/')));
 assert(!doc.querySelector('script[src^="http"]'));
 console.log('PASS: five sport views, selected states, real shot coordinates/outcome overlays, NFL/tennis conditional charts, aggregate mechanics, source credit, document open/close, only allowlisted local fetch routes');
 dom.window.close();
})().catch(e=>{console.error(e);process.exitCode=1;dom.window.close();});
