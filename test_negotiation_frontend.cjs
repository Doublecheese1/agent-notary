const fs = require("fs");
const assert = require("assert");

const html = fs.readFileSync("static/negotiate.html", "utf8");
const js = fs.readFileSync("static/negotiate.js", "utf8");
const mainnet = fs.readFileSync("static/mainnet.js", "utf8");

for (const id of ["buyer", "seller", "description", "deliverables", "limitations", "evidence", "amount", "days", "messages", "accept", "fund", "ownLink", "sellerLink"]) {
  assert(html.includes(`id="${id}"`), `missing negotiation UI element: ${id}`);
}
assert(html.includes("Conversation is context, not the contract"), "chat must not be presented as binding terms");
assert(js.includes("X-Negotiation-Key"), "private role link must authorize negotiation calls");
assert(js.includes("personal_sign"), "final terms must require a wallet signature");
assert(js.includes("agentnotary.agreedTerms"), "agreed terms must transfer to escrow review");
assert(mainnet.includes("agentnotary.agreedTerms") && mainnet.includes('$("mode").value="buyer_review"'), "mainnet must load agreed Buyer Review terms");
assert(!js.includes("privateKey") && !html.includes("privateKey"), "negotiation must never request a private key");
console.log("Negotiation UI guards passed: private links, wallet acceptance and escrow handoff.");
