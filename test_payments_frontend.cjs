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
 let network='0x1',added=false;const requests=[];
 const setupProvider={on(){},async request({method,params}){
  requests.push(method);
  if(method==='eth_chainId')return network;
  if(method==='wallet_switchEthereumChain'){if(!added)throw Object.assign(Error('Unknown chain'),{code:4902});network=params[0].chainId;return null;}
  if(method==='wallet_addEthereumChain'){assert.equal(params[0].chainId,'0x66eee');assert.equal(params[0].rpcUrls[0],'https://sepolia-rollup.arbitrum.io/rpc');added=true;return null;}
  if(method==='eth_requestAccounts'||method==='eth_accounts')return ['0x1111111111111111111111111111111111111111'];
  if(method==='eth_getBalance')return '0x0';
  if(method==='eth_call')return '0x1312d00';
  throw Error('Unexpected request '+method);
 }};
 const onboarding=setup(setupProvider);await onboarding.el('connect').onclick();
 assert.match(onboarding.el('readiness').textContent,/No test ETH/);
 assert.match(onboarding.el('readiness').textContent,/20.000000/);
 assert.equal(onboarding.el('treasury').value,'0x1111111111111111111111111111111111111111');
 assert.equal(requests.includes('eth_sendTransaction'),false);
 assert.equal(onboarding.el('prepare').disabled,true);
 const rejectNetwork=setup({on(){},async request({method}){if(method==='eth_chainId')return '0x1';throw Object.assign(Error('User rejected network change'),{code:4001});}});
 await rejectNetwork.el('connect').onclick();assert.match(rejectNetwork.el('status').textContent,/User rejected/);
 console.log('Payment UI guards passed: missing wallet, wrong chain, rejection, uncertain result.');
})().catch(e=>{console.error(e);process.exitCode=1;});
