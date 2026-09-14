"use strict";
const $=id=>document.getElementById(id),CHAIN="0x66eee";let account=null,pending=null,busy=false;
const show=(id,v)=>$(id).textContent=typeof v==="string"?v:JSON.stringify(v,null,2);
function controls(){$("send").disabled=busy||!pending||!$("consent").checked;}
async function api(path,body){const r=await fetch("/pilot"+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed.");return d;}
async function wallet(){if(!window.ethereum)throw Error("MetaMask was not found.");const a=await ethereum.request({method:"eth_accounts"});if(!a[0])throw Error("Connect MetaMask first.");if(await ethereum.request({method:"eth_chainId"})!==CHAIN)throw Error("Switch to Arbitrum Sepolia.");return a[0];}
async function connect(){await ethereum.request({method:"eth_requestAccounts"});try{await ethereum.request({method:"wallet_switchEthereumChain",params:[{chainId:CHAIN}]});}catch(e){if(e.code!==4902)throw e;await ethereum.request({method:"wallet_addEthereumChain",params:[{chainId:CHAIN,chainName:"Arbitrum Sepolia",nativeCurrency:{name:"Ether",symbol:"ETH",decimals:18},rpcUrls:["https://sepolia-rollup.arbitrum.io/rpc"],blockExplorerUrls:["https://sepolia.arbiscan.io"]}]});}account=await wallet();show("wallet",account);show("status","Founder wallet connected.");}
function stage(d,label){pending=d.transaction;$("consent").checked=false;show("review",{action:label,from:pending.from,to:pending.to||"New test contract",details:d});controls();}
async function feeEnvelope(){const [q,b]=await Promise.all([ethereum.request({method:"eth_gasPrice"}),ethereum.request({method:"eth_getBlockByNumber",params:["latest",false]})]),f=BigInt(b?.baseFeePerGas||q),s=BigInt(q),m=(f>s?f:s)*4n;return{maxFeePerGas:"0x"+m.toString(16),maxPriorityFeePerGas:"0x0"};}
function bind(id,fn){$(id).onclick=async()=>{if(busy)return;busy=true;controls();try{await fn();}catch(e){show("status",e.code===4001?"Cancelled in MetaMask.":e.message);}finally{busy=false;controls();}};}
bind("connect",connect);
bind("admit",async()=>stage(await api("/prepare-admission",{caller:await wallet(),member:$("member").value.trim()}),"Admit one Founding 50 buyer"));
bind("deploy",async()=>stage(await api("/prepare-deployment",{deployer:await wallet(),treasury:$("treasury").value.trim()}),"Deploy a replacement test contract"));
$("consent").onchange=controls;
bind("send",async()=>{if(!pending)throw Error("Prepare an action first.");const a=await wallet();if(a.toLowerCase()!==pending.from.toLowerCase())throw Error("Switch to the prepared founder wallet.");await ethereum.request({method:"eth_call",params:[pending,"latest"]});const tx={...pending,...await feeEnvelope()},hash=await ethereum.request({method:"eth_sendTransaction",params:[tx]});pending=null;$("consent").checked=false;show("receipt","Submitted: "+hash+"\nCheck: https://sepolia.arbiscan.io/tx/"+hash);show("status","Transaction submitted. Verify the receipt before repeating.");});
if(window.ethereum){ethereum.on("accountsChanged",()=>{account=null;pending=null;show("wallet","Account changed — reconnect.");controls();});ethereum.on("chainChanged",()=>{account=null;pending=null;show("wallet","Network changed — reconnect.");controls();});}
controls();
