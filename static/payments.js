"use strict";
const el = id => document.getElementById(id);
let account, prepared, config, busy = false, approvalDone = false, frozen = false;
const chain = '0x66eee'; // 421614
const show = (id, value) => el(id).textContent = typeof value === 'string' ? value : JSON.stringify(value,null,2);
async function api(path, body) {
 const r = await fetch('/payments'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000),cache:'no-store'});
 const data = await r.json(); if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
function controls(){for(const id of ['prepare','deliver','refund','deploy','read','connect'])el(id).disabled=busy;
 el('approve').disabled=busy||!prepared||approvalDone||frozen;el('lock').disabled=busy||!prepared||!approvalDone||frozen;}
async function wallet(){
 if(!window.ethereum)throw Error('Open this page in a browser with an EVM test wallet. No wallet extension was detected.');
 const accounts = await ethereum.request({method:'eth_requestAccounts'});account=accounts[0];
 const current=await ethereum.request({method:'eth_chainId'});if(current!==chain)throw Error('Select Arbitrum Sepolia (421614) in your wallet. Mainnet is disabled.');
 show('wallet',account);return account;
}
async function send(transaction){
 const active=await wallet();if(active.toLowerCase()!==transaction.from.toLowerCase())throw Error('Wrong wallet account for this transaction.');
 if(transaction.chainId!==chain)throw Error('Wrong transaction network.');
 show('transaction',{status:'Awaiting wallet approval',transaction});
 let hash;
 try { hash=await ethereum.request({method:'eth_sendTransaction',params:[transaction]}); }
 catch(e){if(e.code!==4001){frozen=true;throw Error('Wallet result uncertain. Check wallet history before preparing another transaction.');}throw e;}
 frozen=true;show('transaction',{hash,status:'Submitted; waiting for two observed blocks'});
 const end=Date.now()+120000;
 while(Date.now()<end){
  if(await ethereum.request({method:'eth_chainId'})!==chain)throw Error('Network changed. Check the submitted hash on Arbitrum Sepolia.');
  const r=await ethereum.request({method:'eth_getTransactionReceipt',params:[hash]});
  if(r){
   if(r.status==='0x0'){frozen=false;throw Error('Transaction reverted: '+hash);}
   const block=await ethereum.request({method:'eth_blockNumber'});
   if(BigInt(block)>=BigInt(r.blockNumber)+1n){show('transaction',{hash,receipt:r,notice:'Observed inclusion, not L1 finality'});frozen=false;return r;}
  }
  await new Promise(resolve=>setTimeout(resolve,2500));
 }
 throw Error('Receipt not confirmed in time. Keep the transaction hash and inspect it in your wallet. Do not blindly resend.');
}
function action(id,fn){el(id).onclick=async()=>{if(busy)return;busy=true;controls();show('status','Working — complete any request in your wallet.');try{await fn();show('status','Done. Review the result below.');}catch(e){show('status',e.message);}finally{busy=false;controls();}};}
action('connect',wallet);
action('prepare',async()=>{if(frozen)throw Error('An earlier transaction has an uncertain result. Resolve it in your wallet first.');
 const buyer=await wallet();const salt='0x'+Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
 prepared=await api('/prepare-lock',{buyer,seller:el('seller').value.trim(),amount:el('amount').value.trim(),salt,expected_text:el('expected').value,duration_seconds:Number(el('duration').value)});
 approvalDone=false;show('quote',prepared);el('deal').value=prepared.deal_id;
});
action('approve',async()=>{if(!prepared||frozen)throw Error('Prepare a deal first.');await send(prepared.approval);approvalDone=true;});
action('lock',async()=>{if(!prepared||!approvalDone||frozen)throw Error('Approve the prepared amount first.');await send(prepared.lock);prepared=null;approvalDone=false;show('state',await api('/deals/'+el('deal').value.trim()));});
action('deliver',async()=>{if(frozen)throw Error('Resolve the previous transaction first.');const seller=await wallet();const p=await api('/deals/'+el('deal').value.trim()+'/prepare-delivery',{seller,text:el('delivery').value});await send(p.transaction);show('state',await api('/deals/'+el('deal').value.trim()));});
action('refund',async()=>{if(frozen)throw Error('Resolve the previous transaction first.');const caller=await wallet();const p=await api('/deals/'+el('deal').value.trim()+'/prepare-refund',{caller});await send(p.transaction);show('state',await api('/deals/'+el('deal').value.trim()));});
action('read',async()=>show('state',await api('/deals/'+el('deal').value.trim())));
action('deploy',async()=>{if(frozen)throw Error('Resolve the previous transaction first.');const deployer=await wallet();const p=await api('/prepare-deployment',{deployer,treasury:el('treasury').value.trim()});const r=await send(p.transaction);show('config',{PAYMENTS_ENABLED:'true',PAYMENTS_ESCROW_ADDRESS:r.contractAddress,PAYMENTS_TREASURY_ADDRESS:p.treasury,note:'Configure these values and an HTTPS Arbitrum Sepolia RPC URL in Render.'});});
if(window.ethereum){ethereum.on('accountsChanged',()=>{account=null;prepared=null;approvalDone=false;show('wallet','Account changed — connect again.');controls();});ethereum.on('chainChanged',()=>{prepared=null;approvalDone=false;show('status','Network changed — only Arbitrum Sepolia is accepted.');controls();});}
api('/config').then(c=>{config=c;show('config',c);show('status',c.enabled?'Testnet configuration verified.':'Payments disabled. Configure a deployed testnet contract first. /play remains available.');}).catch(e=>show('status',e.message));
