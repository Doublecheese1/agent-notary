const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(__dirname+'/static/payments.js','utf8');
function setup(provider) {
 const elements = new Map();
 const el = id => {if(!elements.has(id))elements.set(id,{value:'',textContent:'',disabled:false});return elements.get(id);};
 const ctx = vm.createContext({document:{getElementById:el},window:{ethereum:provider},ethereum:provider,AbortSignal,setTimeout,crypto:require('node:crypto').webcrypto,fetch:async()=>({ok:true,json:async()=>({enabled:false})})});
 vm.runInContext(source,ctx);return {el,ctx};
}
(async()=>{
 const noWallet=setup();await noWallet.el('connect').onclick();assert.match(noWallet.el('status').textContent,/No wallet extension/);
 let sends=0;
 const provider={on(){},async request({method}){if(method==='eth_requestAccounts')return ['0x1111111111111111111111111111111111111111'];if(method==='eth_chainId')return '0x1';sends++;throw Error('Unexpected send');}};
 const wrong=setup(provider);await wrong.el('prepare').onclick();assert.match(wrong.el('status').textContent,/Select Arbitrum Sepolia/);assert.equal(sends,0);
 provider.request=async({method})=>{if(method==='eth_requestAccounts')return ['0x1111111111111111111111111111111111111111'];if(method==='eth_chainId')return '0x66eee';if(method==='eth_sendTransaction'){sends++;throw Object.assign(Error('Rejected'),{code:4001});}};
 const rejected=setup(provider);
 await assert.rejects(vm.runInContext("send({from:'0x1111111111111111111111111111111111111111',chainId:'0x66eee'})",rejected.ctx),/Rejected/);
 assert.equal(vm.runInContext('frozen',rejected.ctx),false);
 provider.request=async({method})=>{if(method==='eth_requestAccounts')return ['0x1111111111111111111111111111111111111111'];if(method==='eth_chainId')return '0x66eee';throw Error('Disconnected');};
 await assert.rejects(vm.runInContext("send({from:'0x1111111111111111111111111111111111111111',chainId:'0x66eee'})",rejected.ctx),/uncertain/);
 assert.equal(vm.runInContext('frozen',rejected.ctx),true);
 await rejected.el('deliver').onclick();assert.match(rejected.el('status').textContent,/Resolve the previous/);
 console.log('Payment UI guards passed: missing wallet, wrong chain, rejection, uncertain result.');
})().catch(e=>{console.error(e);process.exitCode=1;});
