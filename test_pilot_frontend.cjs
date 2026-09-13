const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/static/pilot.js','utf8');
function setup(provider){
 const elements=new Map(),store=new Map();
 const get=id=>{if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,textContent:'',addEventListener(n,fn){this[n]=fn;}});return elements.get(id);};
 const ctx=vm.createContext({document:{getElementById:get,querySelectorAll:()=>[...elements.values()]},window:{ethereum:provider},sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},fetch:async()=>({ok:true,json:async()=>({enabled:false,member:null,remaining:null})}),AbortSignal:{timeout:()=>undefined},setTimeout:()=>0,clearTimeout(){},console,crypto:require('crypto').webcrypto});
 vm.runInContext(source,ctx);return {ctx,get,store};
}
(async()=>{
 let t=setup();await new Promise(r=>setImmediate(r));await t.get('connect').onclick();assert.match(t.get('status').textContent,/eklenti/);
 const events={},calls=[];let chain='0x66eee';const account='0x'+'12'.repeat(20);
 const provider={on:(n,f)=>events[n]=f,request:async req=>{calls.push(req.method);if(req.method==='eth_accounts'||req.method==='eth_requestAccounts')return [account];if(req.method==='eth_chainId')return chain;if(req.method==='eth_getBalance')return '0x0';if(req.method==='eth_call')return '0x1312d00';return null;}};
 t=setup(provider);await new Promise(r=>setImmediate(r));await t.get('connect').onclick();assert.match(t.get('balances').textContent,/20.000000/);assert.match(t.get('membership').textContent,/doğrulanamadı/);assert(!calls.includes('eth_sendTransaction'));
 vm.runInContext(`stage({from:'${account}',chainId:'0x66eee',data:'0x'},'test',{});controls();`,t.ctx);
 await t.get('send').onclick();assert.match(t.get('status').textContent,/kutusunu/);assert(!calls.includes('eth_sendTransaction'));
 t.get('consent').checked=true;chain='0x1';await t.get('send').onclick();assert.match(t.get('status').textContent,/Sepolia/);assert(!calls.includes('eth_sendTransaction'));
 chain='0x66eee';events.accountsChanged();assert(t.get('send').disabled);
 vm.runInContext(`unresolved='unknown'; sessionStorage.setItem(STORE,unresolved);`,t.ctx);await t.get('recover').onclick();assert.match(t.get('status').textContent,/belirsiz/);assert(!calls.includes('eth_sendTransaction'));
 console.log('Pilot UI: missing wallet, zero gas, unknown membership, consent, wrong chain, account invalidation and uncertain result guards passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
