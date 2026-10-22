const fs = require("fs");
const assert = require("assert");

const html = fs.readFileSync("static/mainnet.html", "utf8");
const js = fs.readFileSync("static/mainnet.js", "utf8");
const landing = fs.readFileSync("static/index.html", "utf8");
const founding = fs.readFileSync("static/founding50-mainnet.html", "utf8");
const setup = fs.readFileSync("static/mainnet-setup.js", "utf8");
const operations = fs.readFileSync("static/mainnet-operations.js", "utf8");
const validatorHtml = fs.readFileSync("static/mainnet-validator.html", "utf8");
const validatorJs = fs.readFileSync("static/mainnet-validator.js", "utf8");
const setupHtml = fs.readFileSync("static/mainnet-setup.html", "utf8");
const envExample = fs.readFileSync(".env.example", "utf8");
const release = JSON.parse(fs.readFileSync("release/mainnet-release.json", "utf8"));
const APPROVED_DEPLOYER = "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD";
const EXCHANGE_DEPOSIT = "0x21a7b51ffF1963C3EE530097B6A71a294a09c26D";

assert(js.includes('CHAIN="0xa4b1"'), "mainnet UI must use Arbitrum One chain ID");
assert(!js.includes('CHAIN="0x66eee"'), "mainnet UI must never use Arbitrum Sepolia chain ID");
assert(js.includes("agentnotary.pendingTx"), "pending transaction hash must survive reloads");
assert(js.includes("agentnotary.uncertainIntent") && js.includes("saveUncertain"), "lost wallet responses must preserve unresolved intent");
assert(js.includes("eth_getTransactionReceipt"), "wallet flow must check the receipt");
assert(js.includes("Do not send it again"), "uncertain writes must block blind retries");
assert(!js.includes("privateKey"), "browser must not contain a private-key field");
assert(/CHAIN\s*=\s*"0xa4b1"/.test(setup), "deployment UI must use Arbitrum One");
assert(!setup.includes("privateKey"), "deployment UI must not contain a private-key field");
assert(setup.includes("getThreshold()") && setup.includes("0xe75235b8"), "deployment must check Safe multisig thresholds");
assert(setup.includes("agentnotary.deploymentPending") && setup.includes("Check the saved deployment"), "deployment must retain uncertain writes across reloads");
assert(operations.includes("prepare-operations-action") && !operations.includes("eth_sendTransaction"), "founder operations must be prepared for Safe execution, not sent from browser");
for (const id of ["arbitrationWindow", "reasonHash", "evidenceUri", "dealLink", "checkTx", "fallbackExample", "approvalStep", "fundingStep", "sellerError"]) {
  assert(html.includes(`id="${id}"`), `missing mainnet UI element: ${id}`);
}
assert(html.includes('id="propose" disabled'), "funding must wait for confirmed approval");
assert(html.includes('id="fallback" type="number" min="0" max="100" value="0"'), "automatic mode must not default to seller payout on validator silence");
assert(!html.includes('id="resolverRole"'), "review must not appear as a public starting role");
assert(html.includes('value="604800" selected'), "buyer review arbitration must default to seven days");
assert(!html.includes("in two days"), "launch copy must not use a stale relative date");
assert(!html.includes("three independent AI reviewers"), "unconfigured reviewer independence must not be claimed");
assert(js.includes("Protocol fee deducted from seller payout"), "funding summary must disclose the seller-side protocol deduction");
assert(js.includes("reconcileApproval"), "confirmed allowance must survive a page reload");
assert(js.includes("Buyer and seller must use different wallet addresses"), "browser must warn before a buyer uses the same seller wallet");
assert(js.includes("new URLSearchParams(location.search)"), "role-specific landing links must select buyer or seller");
assert(js.includes("No protocol fee is charged on this fallback"), "fallback must show a concrete payout example");
assert(js.includes("fundingProgress"), "approval and funding must have a visible progress state");
assert(landing.includes("Illustrative Buyer Review example"), "landing page must label its example as illustrative");
assert(landing.includes("Seller earns 98.50") && landing.includes("their own 5 USDC bond back"), "example must separate seller earnings from bond return");
assert(landing.includes("Buyer gets the 5 USDC reserve back") && landing.includes("AgentSolis receives 1.50 USDC"), "example must account for buyer reserve and protocol fee");
assert(!landing.includes("<strong>103.50 USDC</strong>"), "example must not present gross seller transfer as earnings");
assert(landing.includes("/mainnet?role=buyer#start") && landing.includes("/mainnet?role=seller#start"), "landing role links must open the matching workspace");
assert(landing.includes("https://github.com/Doublecheese1/agent-notary"), "landing page must expose the verified public repository");
assert(landing.includes("/assets/agentsolis-social-card.png") && fs.existsSync("static/agentsolis-social-card.png"), "social preview image must exist and be referenced");
assert(founding.includes("Applications are not open yet"), "Founding 50 must not imply that a missing application path is open");
assert(landing.includes("Automatic deals start at 10 USDC"), "Landing must show the Automatic deal minimum");
assert(landing.includes("Buyer Review deals start at 100 USDC"), "Landing must show the Buyer Review deal minimum");
assert(js.includes("prepare-review-action") && js.includes("Appeal AI ruling"), "deal UI must expose the AI appeal path");
assert(!js.includes("Prepare seller-wins ruling") && !js.includes("Prepare buyer-wins ruling"), "ordinary users must not impersonate the resolver");
assert(js.includes("if(sending)return"), "wallet send must block rapid duplicate clicks");
assert(validatorJs.includes("eth_signTypedData_v4"), "validator console must use scoped wallet signatures");
assert(validatorJs.includes('action:"submitValidation"'), "validator console must prepare quorum relay");
assert(!validatorJs.includes("privateKey"), "validator console must never request a private key");
assert(setupHtml.includes(APPROVED_DEPLOYER), "deployment page must show the controlled MetaMask deployer");
assert(envExample.includes(`MAINNET_DEPLOYER_ADDRESS=${APPROVED_DEPLOYER}`), "environment example must use the controlled MetaMask deployer");
assert.strictEqual(release.deployment_inputs.deployer, APPROVED_DEPLOYER, "release manifest deployer must match the controlled MetaMask wallet");
for (const [name, content] of Object.entries({setupHtml, envExample, release: JSON.stringify(release)})) {
  assert(!content.includes(EXCHANGE_DEPOSIT), `${name} must never use the exchange deposit address as deployer`);
}
for (const id of ["evidenceHash", "signature1", "signature2", "deadline"]) {
  assert(validatorHtml.includes(`id="${id}"`), `missing validator console field: ${id}`);
}
console.log("Mainnet UI guards passed: chain, receipt, retry, approval recovery, duplicate-click lock and validator relay.");
