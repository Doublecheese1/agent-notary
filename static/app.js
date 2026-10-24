"use strict";
const $ = id => document.getElementById(id);
const lockBody = {buyer_agent_id: "buyer.playground", seller_agent_id: "seller.playground", amount_usd: 1, criteria: "Return a research summary in the result field.", timeout_seconds: 86400};
const valid = {result: "Q3 revenue increased by 12 percent."};
const invalid = {status: "COMPLETED", records: 50};
const pretty = value => JSON.stringify(value, null, 2);
const money = value => typeof value === "number" && Number.isFinite(value) ? "$" + value.toFixed(4) : "Not returned";
let busy = false;
$("buyer-payload").textContent = pretty(lockBody);
$("seller-payload").textContent = pretty(valid);
function status(message, error = false) { $("connection").textContent = message; $("connection").classList.toggle("error", error); }
function trace(method, path, body) {
  const block = document.createElement("div"); block.className = "exchange";
  const title = document.createElement("h3"); title.textContent = method + " " + path;
  const request = document.createElement("pre"); request.textContent = body ? pretty(body) : "No request body";
  const response = document.createElement("pre"); response.textContent = "Waiting for response…";
  block.append(title, request, response); $("trail").append(block); return response;
}
async function request(path, body, record = true) {
  const method = body === undefined ? "GET" : "POST";
  const output = record ? trace(method, path, body) : null;
  const controller = new AbortController();
  const waking = setTimeout(() => status("Waking the server… Render may need a minute. Please keep this page open."), 3500);
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(path, {method, signal: controller.signal, cache: "no-store", headers: body ? {"Content-Type": "application/json"} : {}, body: body ? JSON.stringify(body) : undefined});
    const raw = await response.text();
    if (output) output.textContent = "HTTP " + response.status + "\n" + raw;
    if (!response.ok) throw new Error("HTTP " + response.status + ": " + raw.slice(0, 240));
    try { return JSON.parse(raw); } catch { throw new Error("The server returned a non-JSON response. Please try again when it is awake."); }
  } catch (error) {
    if (output && output.textContent === "Waiting for response…") output.textContent = "No response received: " + error.message;
    throw error;
  } finally { clearTimeout(waking); clearTimeout(timeout); }
}
async function run(success) {
  if (busy) return;
  busy = true; $("success").disabled = $("failure").disabled = true;
  $("outcome").hidden = true; $("trail").replaceChildren();
  document.querySelectorAll(".step").forEach(el => el.classList.remove("active"));
  $("buyer-state").textContent = "Waiting for lock…";
  $("seller-state").textContent = "Waiting for buyer…";
  $("seller-title").textContent = "Ready to deliver";
  $("seller-payload").textContent = pretty(success ? valid : invalid);
  let dealId;
  try {
    status("Connecting to sandbox…");
    await request("/sandbox/health");
    status("The buyer is securing the simulated budget…");
    const locked = await request("/sandbox/v1/deals/lock", lockBody);
    if (typeof locked.deal_id !== "string" || locked.status !== "LOCKED") throw new Error("Unexpected lock response; settlement was not sent.");
    dealId = locked.deal_id;
    $("step-lock").classList.add("active");
    $("buyer-state").textContent = money(locked.locked_amount_usd) + " secured for this demo job.";
    $("step-deliver").classList.add("active");
    $("seller-state").textContent = "Submitting the completed work…";
    status("The seller has delivered the work. AgentSolis is checking the demo rule…");
    const result = await request("/sandbox/v1/deals/settle", {deal_id: dealId, seller_agent_id: lockBody.seller_agent_id, deliverable: success ? valid : invalid});
    if (!["APPROVED", "REJECTED"].includes(result.decision)) throw new Error("Unexpected settlement response; inspect the response trail.");
    $("step-validate").classList.add("active"); $("step-final").classList.add("active");
    const approved = result.decision === "APPROVED";
    $("decision").textContent = approved ? "Job completed · Seller paid" : "Delivery did not pass · Buyer return recorded";
    $("decision").classList.toggle("error", !approved);
    $("deal").textContent = "Demo transaction reference: " + dealId;
    $("locked").textContent = money(locked.locked_amount_usd);
    $("fee").textContent = money(result.protocol_fee_usd);
    $("payout").textContent = money(result.seller_payout_usd);
    $("refund").textContent = money(result.refund_to_buyer_usd);
    $("reason").textContent = approved
      ? "The sample delivery included the result required by this demonstration, so the simulated seller payment was completed."
      : "The sample delivery did not include the result required by this demonstration, so the simulated buyer return was recorded.";
    $("outcome").hidden = false;
    $("seller-title").textContent = approved ? "Delivery approved" : "Delivery rejected";
    $("seller-state").textContent = approved ? "Delivery accepted. Seller receives " + money(result.seller_payout_usd) + "." : "Delivery did not pass the demo rule.";
    $("buyer-state").textContent = approved ? "The transaction is complete." : money(result.refund_to_buyer_usd) + " returned to the simulated buyer balance.";
    status("Demonstration complete. You can now try the other outcome.");
  } catch (error) {
    status((error.name === "AbortError" ? "The server did not respond within 90 seconds." : error.message) + (dealId ? " Deal " + dealId + " may still be pending or finalized; no automatic retry was sent." : "") + " You can start a new sandbox deal.", true);
  } finally { busy = false; $("success").disabled = $("failure").disabled = false; }
}
$("success").addEventListener("click", () => run(true));
$("failure").addEventListener("click", () => run(false));
// Keep startup health checks from racing a user-triggered deal.
busy = true; $("success").disabled = $("failure").disabled = true;
request("/sandbox/health", undefined, false).then(() => status("Demo ready · no wallet or real money is used."))
  .catch(() => status("The demo service is still starting. Choose an example to try again.", true))
  .finally(() => { busy = false; $("success").disabled = $("failure").disabled = false; });
