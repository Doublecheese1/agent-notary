"use strict";
const $=id=>document.getElementById(id), CHAIN="0x66eee", STORE="agentnotary-pilot-pending-v2", USDC="0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d";
let account=null,cfg=null,draft=null,pending=null,busy=false,epoch=0,currentDeal=null,approvalConfirmed=false,activeTerms="";
let unresolved=sessionStorage.getItem(STORE);
const show=(id,value)=>{const el=$(id);if(el)el.textContent=typeof value==="string"?value:JSON.stringify(value,null,2);};
const visible=(id,on=true)=>$(id)?.classList.toggle("hidden",!on);
const short=a=>a?a.slice(0,6)+"…"+a.slice(-4):"—";
const units=(n,d=6)=>{n=BigInt(n);const b=10n**BigInt(d);return String(n/b)+"."+String(n%b).padStart(d,"0");};
const same=(a,b)=>!!a&&!!b&&a.toLowerCase()===b.toLowerCase();
const seconds=id=>Number($(id).value)*86400;
function message(e){
 const m=e?.message||String(e);
 if(e?.code===4001)return "You cancelled the request in MetaMask. Nothing was sent.";
 if(/insufficient funds|base fee|gas/i.test(m))return "Not enough test ETH for gas, or the network fee changed. Add test ETH, refresh, then prepare again.";
 if(/allowance|approval/i.test(m))return "USDC approval is missing. Complete step 1, wait for confirmation, then continue to step 2.";
 if(/wrong|caller|role|sender|account/i.test(m))return "The connected account cannot perform this action. Switch to the wallet shown for this role, then reconnect.";
 if(/chain|network/i.test(m))return "Switch MetaMask to Arbitrum Sepolia, then reconnect.";
 if(/deadline|expired|window/i.test(m))return "The time window for this action has ended. Refresh the deal to see the available recovery action.";
 if(/preflight/i.test(m))return "This action is not available now. Refresh the deal and check the connected role, balance and deadline.";
 return m;
}
function controls(){
 document.querySelectorAll("button").forEach(b=>b.disabled=busy);
 if(busy)return;
 $("send").disabled=!pending||!!unresolved||!$("consent").checked;
 $("approval").disabled=!draft||!!unresolved||approvalConfirmed;
 $("proposal").disabled=!draft||!!unresolved||!approvalConfirmed;
}
async function api(path,body){
 const timer=setTimeout(()=>show("status","The service is waking up. This can take about a minute…"),4000);
 try{const r=await fetch("/pilot"+path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000),cache:"no-store"});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==="string"?d.detail:JSON.stringify(d.detail));return d;}finally{clearTimeout(timer);}
}
function provider(){if(!window.ethereum)throw Error("MetaMask was not found. Open this page in Chrome with the MetaMask extension.");return window.ethereum;}
async function wallet(){
 const p=provider(),a=await p.request({method:"eth_accounts"});
 if(!a[0])throw Error("Connect MetaMask first.");
 if(await p.request({method:"eth_chainId"})!==CHAIN)throw Error("Switch to Arbitrum Sepolia.");
 return a[0];
}
async function feeEnvelope(p){
 const [quoted,block]=await Promise.all([p.request({method:"eth_gasPrice"}),p.request({method:"eth_getBlockByNumber",params:["latest",false]})]);
 const floor=BigInt(block?.baseFeePerGas||quoted),suggested=BigInt(quoted),max=(floor>suggested?floor:suggested)*4n;
 return {maxFeePerGas:"0x"+max.toString(16),maxPriorityFeePerGas:"0x0"};
}
function mark(id,text,ok){show(id,text);$(id).className=ok?"ok":"bad";}
async function refresh(){
 const version=epoch,a=account,c=await api("/config"+(a?"?wallet="+encodeURIComponent(a):""));
 if(version!==epoch)return;cfg=c;show("config",c);
 if(!c.enabled)mark("membership","Pilot unavailable",false);
 else if(c.member===null)mark("membership",String(c.remaining)+" places left",true);
 else if(c.member)mark("membership","Admitted · "+c.remaining+" places left",true);
 else mark("membership","This buyer wallet is not admitted",false);
}
async function connect(){
 const p=provider();await p.request({method:"eth_requestAccounts"});
 try{await p.request({method:"wallet_switchEthereumChain",params:[{chainId:CHAIN}]});}
 catch(e){if(e.code!==4902)throw e;await p.request({method:"wallet_addEthereumChain",params:[{chainId:CHAIN,chainName:"Arbitrum Sepolia",nativeCurrency:{name:"Ether",symbol:"ETH",decimals:18},rpcUrls:["https://sepolia-rollup.arbitrum.io/rpc"],blockExplorerUrls:["https://sepolia.arbiscan.io"]}]});await p.request({method:"wallet_switchEthereumChain",params:[{chainId:CHAIN}]});}
 account=await wallet();mark("wallet",short(account),true);mark("network","Arbitrum Sepolia",true);await refresh();
 const [eth,usdc]=await Promise.all([p.request({method:"eth_getBalance",params:[account,"latest"]}),p.request({method:"eth_call",params:[{to:USDC,data:"0x70a08231"+account.slice(2).padStart(64,"0")},"latest"]})]);
 if(!same(await wallet(),account))throw Error("The account changed. Connect again.");
 mark("ethBalance",BigInt(eth)>0n?units(eth,18)+" ETH":"No test ETH",BigInt(eth)>0n);
 mark("usdcBalance",units(usdc)+" test USDC",BigInt(usdc)>0n);
 show("balances",{test_ETH:units(eth,18),test_USDC:units(usdc),next:BigInt(eth)===0n?"Test ETH is required for gas.":"Ready for testnet transactions."});
 if(currentDeal)renderDeal(currentDeal);
}
function bind(id,fn){$(id).onclick=async()=>{if(busy)return;busy=true;controls();show("status","Working…");try{await fn();show("status","Ready.");}catch(e){show("status",message(e));}finally{busy=false;controls();}};}
function encodeTerms(s){const bytes=new TextEncoder().encode(s);let x="";bytes.forEach(b=>x+=String.fromCharCode(b));return btoa(x).replaceAll("+","-").replaceAll("/","_").replaceAll("=","");}
function decodeTerms(s){try{s=s.replaceAll("-","+").replaceAll("_","/");const bin=atob(s),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));return new TextDecoder().decode(bytes);}catch{return "";}}
function shareUrl(id,terms){const origin=window.location?.origin||"";return origin+"/pilot/deal/"+id+"#terms="+encodeTerms(terms);}
function stage(transaction,label,details){
 if(unresolved)throw Error("Check the result of the last transaction first.");
 pending={transaction,label,details};$("consent").checked=false;show("reviewLabel",label);
 show("review",{action:label,from:transaction.from,to:transaction.to||"New test contract",summary:details});
 visible("reviewCard");$("reviewCard").scrollIntoView?.({behavior:"smooth",block:"center"});controls();
}
async function allowance(required){
 if(!account||!cfg?.escrow)return false;
 const data="0xdd62ed3e"+account.slice(2).padStart(64,"0")+cfg.escrow.slice(2).padStart(64,"0");
 const value=await provider().request({method:"eth_call",params:[{to:USDC,data},"latest"]});
 return BigInt(value)>=BigInt(required);
}
async function syncFunding(){
 if(!draft)return;approvalConfirmed=await allowance(draft.locked_units);
 $("approval").textContent=approvalConfirmed?"1/2 Approved ✓":"1/2 Approve test USDC";
 controls();
}
function roleFor(d){if(same(account,d.buyer))return"Buyer";if(same(account,d.seller))return"Seller";if(same(account,d.arbiter))return"Arbitrator";return"Observer";}
function deadline(ts){return ts?new Date(Number(ts)*1000).toLocaleString():"Starts after acceptance";}
function timeline(d){
 const terminal=["ACCEPTED","RESOLVED_SELLER","RESOLVED_BUYER","FINALIZED_SPLIT","PROPOSAL_EXPIRED","UNDELIVERED_EXPIRED"].includes(d.state);
 const names=["Proposed","Funded","Parties accepted","Delivered",d.state==="DISPUTED"?"Disputed":"Closed"];
 let level=d.state==="PROPOSED"?1:d.state==="LOCKED"?2:d.state==="DELIVERED"?3:d.state==="DISPUTED"?4:terminal?4:0;
 $("timeline").replaceChildren(...names.map((n,i)=>{const el=document.createElement("div");el.className="step "+(i<=level?"done":"");el.textContent=n;return el;}));
}
function actionButton(label,action,kind=""){
 const b=document.createElement("button");b.textContent=label;if(kind)b.className=kind;b.onclick=()=>prepareAction(action);$("actionButtons").appendChild(b);
}
function renderDeal(d){
 currentDeal=d;visible("workspace");const role=roleFor(d);show("role","You are: "+role);show("dealTitle","Deal "+short(d.deal_id)+" · "+d.state);show("dealMoney",units(d.amount_units)+" test USDC");
 show("parties","Buyer: "+short(d.buyer)+"\nSeller: "+short(d.seller)+"\nArbitrator: "+short(d.arbiter));
 show("timing","Accept by: "+deadline(d.acceptance_deadline)+"\nDeliver by: "+deadline(d.submit_deadline)+"\nDispute by: "+deadline(d.dispute_deadline)+"\nArbitrate by: "+deadline(d.arbitration_deadline));
 show("termsView",activeTerms||"Terms were not included in this link. Ask the buyer for the complete shared deal link before accepting.");
 $("shareLink").value=shareUrl(d.deal_id,activeTerms);show("state",d);timeline(d);
 ["contentWrap","uriWrap","reasonWrap"].forEach(x=>visible(x,false));$("actionButtons").replaceChildren();let wait="";
 const now=Number(d.chain_time);
 if(d.state==="PROPOSED"){
  if(role==="Seller"&&!d.seller_accepted&&activeTerms)actionButton("Accept deal as Seller","sellerAccept");
  if(role==="Arbitrator"&&!d.arbiter_accepted&&activeTerms)actionButton("Accept unpaid arbitrator role","arbiterAccept");
  if(now>=Number(d.acceptance_deadline))actionButton("Return budget after missed acceptance","expireProposal","secondary");
  wait=d.seller_accepted&&d.arbiter_accepted?"Both parties accepted. Refresh the deal.":"Waiting for seller and arbitrator acceptance.";
 }else if(d.state==="LOCKED"){
  if(role==="Seller"){visible("contentWrap");visible("uriWrap");actionButton("Submit delivery","deliver");}
  if(now>=Number(d.submit_deadline))actionButton("Return budget after missed delivery","expireUndelivered","secondary");
  wait="Waiting for the seller to submit the delivery.";
 }else if(d.state==="DELIVERED"){
  if(role==="Buyer"){actionButton("Accept delivery and pay","acceptDelivery");visible("reasonWrap");actionButton("Dispute delivery","disputeDelivery","danger");}
  if(now>=Number(d.dispute_deadline))actionButton("Finalize seller payment","finalizeIfSilent");
  wait="Waiting for the buyer to accept or dispute the delivery.";
 }else if(d.state==="DISPUTED"){
  if(role==="Arbitrator"){actionButton("Rule for Seller","resolveSeller");actionButton("Rule for Buyer","resolveBuyer","danger");}
  if(now>=Number(d.arbitration_deadline))actionButton("Apply agreed fallback split","finalizeStalemate","secondary");
  wait="Waiting for the arbitrator to rule.";
 }else wait="This deal is closed. No further action is required.";
 show("waiting",wait);show("currentAction",wait+" Connected role: "+role+".");
 visible("open",true);history.replaceState?.({},"","/pilot/deal/"+d.deal_id+(window.location?.hash||""));
}
async function readDeal(){
 const id=$("deal").value.trim();if(!id)throw Error("Paste a Deal ID first.");
 const d=await api("/deals/"+encodeURIComponent(id));renderDeal(d);return d;
}
async function prepareAction(action){
 if(busy)return;busy=true;controls();show("status","Preparing the action…");
 try{const d=currentDeal||await readDeal();const result=await api("/deals/"+encodeURIComponent(d.deal_id)+"/prepare-action",{caller:await wallet(),action,terms:activeTerms,content:$("content").value,uri:$("uri").value.trim(),reason:$("reason").value});stage(result.transaction,action,{deal_id:d.deal_id,state:d.state,role:roleFor(d)});show("status","Review the action below, then confirm in MetaMask.");}catch(e){show("status",message(e));}finally{busy=false;controls();}
}
bind("connect",connect);bind("refresh",async()=>{await refresh();if(currentDeal)await readDeal();});
$("startCreate").onclick=()=>{visible("create");visible("open",false);$("create").scrollIntoView?.({behavior:"smooth"});};
$("startOpen").onclick=()=>{visible("open");visible("create",false);$("open").scrollIntoView?.({behavior:"smooth"});};
bind("read",readDeal);
$("deal").addEventListener("input",()=>{if(currentDeal&&!same($("deal").value.trim(),currentDeal.deal_id)){currentDeal=null;activeTerms="";}});
bind("prepare",async()=>{
 const buyer=await wallet(),version=epoch,salt="0x"+Array.from(crypto.getRandomValues(new Uint8Array(32)),x=>x.toString(16).padStart(2,"0")).join("");
 const split=Number($("split").value);if(!Number.isFinite(split)||split<0||split>100)throw Error("Enter a fallback seller share between 0 and 100 percent.");
 const terms=$("terms").value.trim();if(!terms)throw Error("Describe what must be delivered.");
 const d=await api("/prepare-proposal",{buyer,seller:$("seller").value.trim(),arbiter:$("arbiter").value.trim(),amount:$("amount").value.trim(),salt,terms,split_bps:Math.round(split*100),acceptance_window:seconds("acceptDays"),submit_window:seconds("submitDays"),dispute_window:seconds("disputeDays"),arbitration_window:seconds("arbDays")});
 if(version!==epoch)throw Error("The wallet or form changed. Review the deal again.");
 draft=d;activeTerms=terms;$("deal").value=d.deal_id;$("fundAmount").textContent=units(d.locked_units);show("quote",d);visible("funding");await syncFunding();$("funding").scrollIntoView?.({behavior:"smooth"});
});
bind("approval",async()=>stage(draft.approval,"Approve the exact test USDC amount",{amount:units(draft.locked_units)+" test USDC",moves_funds:false,step:"1 of 2"}));
bind("proposal",async()=>stage(draft.proposal,"Lock the deal budget",{amount:units(draft.locked_units)+" test USDC",deal_id:draft.deal_id,step:"2 of 2",share_link:shareUrl(draft.deal_id,activeTerms)}));
$("copyLink").onclick=async()=>{await navigator.clipboard.writeText($("shareLink").value);show("status","Deal link copied. Send it to the seller and arbitrator.");};
$("consent").onchange=controls;
$("cancelReview").onclick=()=>{pending=null;visible("reviewCard",false);controls();};
async function inspectReceipt(hash,submitted){
 const p=provider();await wallet();const r=await p.request({method:"eth_getTransactionReceipt",params:[hash]});
 if(!r){show("receipt","Submitted: "+hash+"\nWaiting for confirmation. Do not send again.");return false;}
 const head=await p.request({method:"eth_blockNumber"});if(BigInt(head)<BigInt(r.blockNumber)+1n){show("receipt","Submitted: "+hash+"\nWaiting for another observed block.");return false;}
 if(await p.request({method:"eth_chainId"})!==CHAIN)throw Error("The network changed. Check the result on Arbitrum Sepolia.");
 sessionStorage.removeItem(STORE);unresolved=null;pending=null;
 show("receipt",(r.status==="0x1"?"Confirmed ✓":"Transaction failed")+"\nTransaction: "+hash+"\nExplorer: https://sepolia.arbiscan.io/tx/"+hash);
 if(r.status==="0x1"&&submitted?.label?.startsWith("Approve"))await syncFunding();
 if(r.status==="0x1"&&$("deal").value.trim()&&!submitted?.label?.startsWith("Approve")){try{await readDeal();}catch{}}
 return true;
}
bind("send",async()=>{
 if(!pending||unresolved)throw Error("Prepare an action or check the previous transaction first.");
 if(!$("consent").checked)throw Error("Check the review confirmation box.");
 const chosen=pending,p=provider(),a=await wallet();
 if(!same(a,chosen.transaction.from)||chosen.transaction.chainId!==CHAIN)throw Error("The prepared wallet or network does not match MetaMask.");
 await p.request({method:"eth_call",params:[chosen.transaction,"latest"]});
 if(pending!==chosen||!same(await wallet(),a))throw Error("The information changed. Prepare the transaction again.");
 const sendTransaction={...chosen.transaction,...await feeEnvelope(p)};unresolved="unknown";sessionStorage.setItem(STORE,unresolved);
 let hash;try{hash=await p.request({method:"eth_sendTransaction",params:[sendTransaction]});}catch(e){if(e.code===4001){unresolved=null;sessionStorage.removeItem(STORE);}throw e;}
 unresolved=hash;sessionStorage.setItem(STORE,hash);pending=null;show("receipt","Submitted: "+hash+"\nWaiting for confirmation.");
 for(let n=0;n<24;n++){if(await inspectReceipt(hash,chosen))return;await new Promise(r=>setTimeout(r,2500));}
 throw Error("The transaction is still pending. Use Check last transaction before trying anything again.");
});
bind("recover",async()=>{if(!unresolved)throw Error("There is no pending transaction in this browser tab.");if(unresolved==="unknown")throw Error("MetaMask did not return a transaction hash. Check MetaMask Activity before trying again.");await inspectReceipt(unresolved,null);});
function invalidate(){epoch++;draft=null;pending=null;approvalConfirmed=false;$("consent").checked=false;visible("funding",false);visible("reviewCard",false);controls();}
for(const id of ["seller","arbiter","amount","terms","split","acceptDays","submitDays","disputeDays","arbDays"])$(id).addEventListener("input",invalidate);
if(window.ethereum){window.ethereum.on("accountsChanged",()=>{account=null;invalidate();mark("wallet","Account changed — reconnect",false);if(currentDeal)renderDeal(currentDeal);});window.ethereum.on("chainChanged",()=>{account=null;invalidate();mark("network","Network changed — reconnect",false);});}
function loadShared(){
 const path=window.location?.pathname||"",match=path.match(/\/pilot\/deal\/(0x[0-9a-fA-F]{64})/),raw=(window.location?.hash||"").replace(/^#/,"");
 const part=raw.split("&").find(x=>x.startsWith("terms="));activeTerms=decodeTerms(part?part.slice(6):"");if(match){$("deal").value=match[1];visible("open");readDeal().catch(e=>show("status",message(e)));}
}
controls();refresh().then(()=>show("status",unresolved?"Check the previous transaction result first.":"Ready. Connect your wallet to continue.")).catch(e=>show("status",message(e)));loadShared();
