// Unit tests for timeouts and error handling, with fake HTTP and a minimal DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/static/app.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup(fetcher) {
  const elements = new Map(), timers = new Map(); let timerId = 0;
  function element() { return {textContent:'', hidden:false, disabled:false, children:[], classList:{toggle(){},add(){},remove(){}}, append(...children){this.children.push(...children)}, replaceChildren(){this.children=[]}, addEventListener(name, fn){this[name]=fn}}; }
  const doc = {getElementById(id){if(!elements.has(id)) elements.set(id,element());return elements.get(id)}, createElement:element, querySelectorAll(){return []}};
  const ctx = vm.createContext({document:doc, location:{origin:'http://localhost:8765'}, navigator:{clipboard:{writeText:async()=>{}}}, fetch:fetcher, AbortController, setTimeout(fn,ms){timers.set(++timerId,{fn,ms});return timerId},clearTimeout(id){timers.delete(id)}});
  vm.runInContext(source,ctx);
  return {elements,timers,ctx,el:id=>doc.getElementById(id)};
}
const response = (body, status=200) => ({ok:status<400,status,text:async()=>JSON.stringify(body)});
(async()=>{
  let calls=[];
  const happy=setup(async(path,opts)=>{calls.push(path);return response(path.endsWith('/lock')?{deal_id:'deal_test',status:'LOCKED',locked_amount_usd:1.005}:path.endsWith('/settle')?{decision:'APPROVED',seller_payout_usd:.985,protocol_fee_usd:.02,refund_to_buyer_usd:0}:{status:'ONLINE'});});
  await tick(); await vm.runInContext('run(true)',happy.ctx);
  assert.equal(happy.el('payout').textContent,'$0.9850');assert.equal(happy.el('fee').textContent,'$0.0200');assert.equal(happy.el('outcome').hidden,false);
  assert.ok(calls.every(p=>p.startsWith('/sandbox/')));assert.equal(happy.timers.size,0);

  const sleeping=setup((_path,opts)=>new Promise((_resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'})))));
  [...sleeping.timers.values()].find(t=>t.ms===3500).fn();assert.match(sleeping.el('connection').textContent,/Waking/);
  [...sleeping.timers.values()].find(t=>t.ms===90000).fn();await tick();assert.equal(sleeping.el('success').disabled,false);assert.match(sleeping.el('connection').textContent,/retry/);

  const broken=setup(async()=>({ok:true,status:200,text:async()=>'<html>proxy error</html>'}));await tick();await vm.runInContext('run(true)',broken.ctx);assert.match(broken.el('connection').textContent,/non-JSON/);assert.equal(broken.el('outcome').hidden,true);

  let count=0;
  const timeout=setup(async(path,opts)=>{count++;if(path.endsWith('/settle')) return new Promise((_resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'}))));return response(path.endsWith('/lock')?{deal_id:'deal_pending',status:'LOCKED',locked_amount_usd:1.005}:{status:'ONLINE'});});
  await tick(); const pending=vm.runInContext('run(true)',timeout.ctx);await tick();await vm.runInContext('run(false)',timeout.ctx);assert.equal(count,4);
  [...timeout.timers.values()].find(t=>t.ms===90000).fn();await pending;assert.match(timeout.el('connection').textContent,/deal_pending.*no automatic retry/);assert.equal(count,4);assert.equal(timeout.el('success').disabled,false);
  console.log('PASS: response totals, sandbox URLs, waking, timeout recovery, non-JSON error, duplicate-click guard and no POST retry');
})().catch(error=>{console.error(error);process.exitCode=1});
