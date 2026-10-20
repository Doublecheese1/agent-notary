"use strict";

const $ = id => document.getElementById(id);
const CHAIN = "0xa4b1";
const PENDING_KEY = "agentnotary.deploymentPending";
const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
let account = null, gate = false, expectedDeployer = null, prepared = null, sending = false;
let unresolved = JSON.parse(localStorage.getItem(PENDING_KEY) || "null");

const show = (id, value) => $(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
function saveUnresolved(value) { unresolved = value; if (value) localStorage.setItem(PENDING_KEY, JSON.stringify(value)); else localStorage.removeItem(PENDING_KEY); }
async function api(path, body) {
  const r = await fetch("/mainnet" + path, {method: body ? "POST" : "GET", headers: body ? {"Content-Type": "application/json"} : {}, body: body ? JSON.stringify(body) : undefined, cache: "no-store"});
  const result = await r.json();
  if (!r.ok) throw Error(result.detail || "Request failed");
  return result;
}
function provider() { if (!window.ethereum) throw Error("MetaMask was not found."); return window.ethereum; }
async function wallet() {
  const p = provider(), addresses = await p.request({method: "eth_accounts"});
  if (!addresses[0]) throw Error("Connect the founder wallet first.");
  if (await p.request({method: "eth_chainId"}) !== CHAIN) throw Error("Switch to Arbitrum One.");
  return addresses[0];
}
async function connect() {
  const p = provider();
  await p.request({method: "eth_requestAccounts"});
  await p.request({method: "wallet_switchEthereumChain", params: [{chainId: CHAIN}]});
  account = await wallet();
  if (!expectedDeployer || account.toLowerCase() !== expectedDeployer.toLowerCase()) throw Error("Connect the approved deployer wallet: " + expectedDeployer);
  show("status", "Connected: " + account);
  $("prepareQuorum").disabled = !gate;
  $("prepareResolver").disabled = !gate;
  $("prepareEscrow").disabled = !gate;
}
function requireReady() { if (!gate) throw Error("Founder deployment gate is closed."); if (unresolved) throw Error("Check the saved deployment before preparing another."); }
function stage(data, kind, label) {
  prepared = {transaction: data.transaction, kind};
  show("intent", {action: label, network: "Arbitrum One (42161)", constructor: data.constructor, transaction: data.transaction});
  $("consent").checked = false;
  $("send").disabled = true;
  $("review").classList.remove("hidden");
}
async function verifySafe(raw, label) {
  if (!ADDRESS.test(raw)) throw Error(label + " needs a public wallet address.");
  const p = provider(), code = await p.request({method: "eth_getCode", params: [raw, "latest"]});
  if (!code || code === "0x") throw Error(label + " must already be deployed on Arbitrum One.");
  // Safe's getThreshold() selector. Threshold two or higher is required for this launch.
  let threshold;
  try { threshold = BigInt(await p.request({method: "eth_call", params: [{to: raw, data: "0xe75235b8"}, "latest"]})); }
  catch { throw Error(label + " does not expose Safe getThreshold()."); }
  if (threshold < 2n) throw Error(label + " must require at least two owner signatures.");
  return threshold;
}
async function prepareQuorum() {
  requireReady();
  stage(await api("/prepare-quorum-deployment", {deployer: await wallet(), signer_a: $("signerA").value.trim(), signer_b: $("signerB").value.trim(), signer_c: $("signerC").value.trim()}), "quorum", "Deploy immutable 2-of-3 validator quorum");
}
async function prepareResolver() {
  requireReady();
  const operations = $("operations").value.trim(), human = $("humanReview").value.trim(), recipient = $("feeRecipient").value.trim();
  await Promise.all([verifySafe(operations, "Operations Safe"), verifySafe(human, "Human Review Safe"), verifySafe(recipient, "Treasury Safe")]);
  stage(await api("/prepare-ai-review-resolver-deployment", {deployer: await wallet(), operations_safe: operations, human_review_safe: human, fee_recipient: recipient, signer_a: $("reviewerA").value.trim(), signer_b: $("reviewerB").value.trim(), signer_c: $("reviewerC").value.trim(), automatic_amount_cap_units: 250000000, appeal_window_seconds: 86400, minimum_confidence_bps: 8500}), "resolver", "Deploy appealable 2-of-3 AI review resolver");
}
async function prepareEscrow() {
  requireReady();
  const treasury = $("treasury").value.trim(), operations = $("escrowOperations").value.trim(), arbitrator = $("arbitrator").value.trim(), quorum = $("quorum").value.trim();
  await Promise.all([verifySafe(treasury, "Treasury Safe"), verifySafe(operations, "Operations Safe")]);
  if (!ADDRESS.test(quorum) || await provider().request({method: "eth_getCode", params: [quorum, "latest"]}) === "0x") throw Error("Deploy the validator quorum first.");
  if (!ADDRESS.test(arbitrator) || await provider().request({method: "eth_getCode", params: [arbitrator, "latest"]}) === "0x") throw Error("Deploy the AI review resolver first.");
  stage(await api("/prepare-escrow-deployment", {deployer: await wallet(), treasury_safe: treasury, operations_safe: operations, automatic_validator: quorum, review_arbitrator: arbitrator}), "escrow", "Deploy AgentNotary escrow");
}
async function checkSaved() {
  if (!unresolved) return show("result", "No unresolved deployment.");
  if (await provider().request({method: "eth_chainId"}) !== CHAIN) throw Error("Switch to Arbitrum One before checking the deployment.");
  if (!unresolved.hash) return show("result", "The wallet response was lost before a transaction hash was saved. Inspect MetaMask activity. If a hash exists, paste it below and check it. Do not deploy again based on a NOT_FOUND lookup.");
  const receipt = await provider().request({method: "eth_getTransactionReceipt", params: [unresolved.hash]});
  if (!receipt) return show("result", "Still unresolved: " + unresolved.hash + "\nDo not deploy again.");
  if (BigInt(receipt.status) !== 1n) { show("result", "Confirmed failure: " + unresolved.hash + "\nNo contract was deployed."); saveUnresolved(null); return; }
  if (receipt.from?.toLowerCase() !== unresolved.from.toLowerCase() || receipt.to) return show("result", "Receipt sender or destination does not match the saved contract deployment. Review manually: " + unresolved.hash);
  if (!receipt.contractAddress) return show("result", "Receipt has no contract address. Review this transaction manually: " + unresolved.hash);
  const address = receipt.contractAddress;
  if (unresolved.kind === "quorum") { $("quorum").value = address; localStorage.setItem("agentnotary.quorumAddress", address); }
  if (unresolved.kind === "resolver") { $("arbitrator").value = address; localStorage.setItem("agentnotary.resolverAddress", address); }
  if (unresolved.kind === "escrow") localStorage.setItem("agentnotary.escrowAddress", address);
  show("result", "Confirmed: " + unresolved.hash + "\nContract address: " + address);
  saveUnresolved(null);
  prepared = null;
}
async function send() {
  if (sending) return;
  sending = true; $("send").disabled = true;
  try {
    if (!prepared) throw Error("Prepare the deployment again.");
    if (unresolved) throw Error("Check the saved deployment before sending another.");
    const p = provider(), signer = await wallet();
    if (signer.toLowerCase() !== prepared.transaction.from.toLowerCase()) throw Error("The founder wallet changed. Prepare again.");
    await p.request({method: "eth_estimateGas", params: [prepared.transaction]});
    // Persist an unresolved intent before opening MetaMask. A lost provider response is not proof of failure.
    saveUnresolved({kind: prepared.kind, hash: null, from: signer});
    let hash;
    try { hash = await p.request({method: "eth_sendTransaction", params: [prepared.transaction]}); }
    catch (e) { if (e.code === 4001) saveUnresolved(null); throw e; }
    saveUnresolved({kind: prepared.kind, hash, from: signer});
    show("result", "Submitted: " + hash + "\nWaiting for confirmation. Do not deploy again.");
    for (let i = 0; i < 90; i++) { await checkSaved(); if (!unresolved) return; await new Promise(resolve => setTimeout(resolve, 2000)); }
    show("result", "Still pending: " + hash + "\nCheck the saved transaction later. Do not deploy again.");
  } catch (e) { show("status", e.message || String(e)); }
  finally { sending = false; $("send").disabled = !prepared || !$("consent").checked || !!unresolved; }
}

$("connect").onclick = () => connect().catch(e => show("status", e.message));
$("prepareQuorum").onclick = () => prepareQuorum().catch(e => show("status", e.message));
$("prepareResolver").onclick = () => prepareResolver().catch(e => show("status", e.message));
$("prepareEscrow").onclick = () => prepareEscrow().catch(e => show("status", e.message));
$("consent").onchange = () => $("send").disabled = !$("consent").checked || !!unresolved;
$("send").onclick = send;
$("checkDeployment").onclick = () => checkSaved().catch(e => show("status", e.message));
$("knownTxHash").onchange = () => { const hash = $("knownTxHash").value.trim(); if (unresolved && !unresolved.hash && /^0x[0-9a-fA-F]{64}$/.test(hash)) { saveUnresolved({...unresolved, hash}); checkSaved().catch(e => show("status", e.message)); } };
const savedQuorum = localStorage.getItem("agentnotary.quorumAddress"); if (savedQuorum) $("quorum").value = savedQuorum;
const savedResolver = localStorage.getItem("agentnotary.resolverAddress"); if (savedResolver) $("arbitrator").value = savedResolver;
if (unresolved) show("result", "Unresolved deployment from " + unresolved.from + (unresolved.hash ? "\nTransaction: " + unresolved.hash : "\nNo transaction hash received") + "\nCheck it before continuing.");
api("/setup-status").then(d => { expectedDeployer = d.deployer; gate = d.enabled; show("status", gate ? "Founder deployment gate is open. Approved deployer: " + expectedDeployer : "Founder deployment gate is closed. Configure MAINNET_DEPLOYER_ADDRESS and open MAINNET_DEPLOYMENT_UI only for the deployment session."); }).catch(e => show("status", e.message));
