const fs = require("fs");
const assert = require("assert");

const html = fs.readFileSync("static/mainnet.html", "utf8");
const js = fs.readFileSync("static/mainnet.js", "utf8");
const landing = fs.readFileSync("static/index.html", "utf8");
const founding = fs.readFileSync("static/founding50-mainnet.html", "utf8");
const foundingJs = fs.readFileSync("static/founding50-mainnet.js", "utf8");
const guideJs = fs.readFileSync("static/mainnet-guide.js", "utf8");
const setup = fs.readFileSync("static/mainnet-setup.js", "utf8");
const operations = fs.readFileSync("static/mainnet-operations.js", "utf8");
const validatorHtml = fs.readFileSync("static/mainnet-validator.html", "utf8");
const validatorJs = fs.readFileSync("static/mainnet-validator.js", "utf8");
const setupHtml = fs.readFileSync("static/mainnet-setup.html", "utf8");
const envExample = fs.readFileSync(".env.example", "utf8");
const analyticsJs = fs.readFileSync("static/launch-analytics.js", "utf8");
const css = fs.readFileSync("static/brand.css", "utf8");
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
assert(setup.includes("DEFAULT_SIGNERS") && setup.includes(APPROVED_DEPLOYER), "deployment must prefill the approved private-canary signers");
assert(setup.includes('$("escrowOperations").value = $("operations").value') && setup.includes('$("treasury").value = $("feeRecipient").value'), "deployment must mirror repeated Safe addresses to reduce entry errors");
assert(operations.includes("prepare-operations-action") && !operations.includes("eth_sendTransaction"), "founder operations must be prepared for Safe execution, not sent from browser");
for (const id of ["arbitrationWindow", "reasonHash", "evidenceUri", "dealLink", "checkTx", "fallbackExample", "costPreview", "hashFile", "hashFileStatus", "approvalStep", "fundingStep", "sellerError"]) {
  assert(html.includes(`id="${id}"`), `missing mainnet UI element: ${id}`);
}
assert(html.includes('id="propose" disabled'), "funding must wait for confirmed approval");
assert(!html.includes("data-live-funding-status"), "workspace must not leave a second stale status indicator");
assert(js.includes('crypto.subtle.digest("SHA-256",bytes)'), "local delivery file helper must calculate a browser-side SHA-256 hash");
assert(!js.includes('FormData') && !js.includes('fetch(file'), "delivery file helper must not upload the selected file");
assert(founding.includes('href="/mainnet#guide"'), "Founding 50 must not assume every applicant is a buyer");
assert(html.includes('<option value="buyer_review" selected>'), "buyer review must be the default settlement mode");
assert(html.includes('id="amount" value="100"'), "buyer review must default to its 100 USDC contract minimum");
assert(html.includes('id="fallback" type="number" min="0" max="100" value="50"'), "buyer review must default to the disclosed 50/50 timeout split");
assert(js.includes('$("fallback").value=review?"50":"0"'), "switching to automatic mode must restore the zero seller-share timeout default");
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
assert(js.includes("validatePreparedTransaction(pending.transaction,a)"), "wallet sends must validate target, selector, chain and value locally");
assert(js.includes("BigInt(expected)") && js.includes("draft?.buyer_total_units") && js.includes("current?.seller_bond_units"), "USDC approval must match the exact buyer total or seller bond");
assert(js.includes("PROPOSE_SELECTOR") && js.includes("draft?._intent") && js.includes("normHash(expected[7])"), "proposal calldata must match the buyer's canonical UI intent and production policy");
assert(js.includes("abiString(tx.data,2)") && js.includes("normHash(current.deal_id)"), "deal actions must match the displayed deal and delivery or dispute evidence");
assert(js.includes('selector!=="0x095ea7b3"') && js.includes("same(spender,cfg.escrow)"), "USDC approvals must be limited to the configured escrow spender");
assert(landing.includes("Illustrative Buyer Review example"), "landing page must label its example as illustrative");
assert(landing.includes("Seller earns 98.50") && landing.includes("their own 5 USDC bond back"), "example must separate seller earnings from bond return");
assert(landing.includes("Buyer gets the 5 USDC reserve back") && landing.includes("AgentSolis receives 1.50 USDC"), "example must account for buyer reserve and protocol fee");
assert(!landing.includes("<strong>103.50 USDC</strong>"), "example must not present gross seller transfer as earnings");
assert(landing.includes("/mainnet?role=buyer#start") && landing.includes("/mainnet?role=seller#start"), "landing role links must open the matching workspace");
assert(!landing.includes("github.com/"), "landing page must keep the repository link hidden from the public navigation");
assert(landing.includes("/assets/agentsolis-social-card.png") && fs.existsSync("static/agentsolis-social-card.png"), "social preview image must exist and be referenced");
assert(founding.includes('id="connectFounding"') && founding.includes('id="applicationForm"'), "Founding 50 must provide a real wallet application path");
assert(founding.includes("Applying does not move money") && founding.includes("Operations Safe"), "Founding 50 must explain signature safety and manual approval");
assert(html.includes('id="guide"') && html.includes('/mainnet/guide.js'), "mainnet workspace must include the beginner guide");
assert(foundingJs.includes('personal_sign') && !foundingJs.includes('eth_sendTransaction'), "Founding application must prove wallet control without sending a transaction");
assert(foundingJs.includes('accepted_terms:true'), "Founding application must record explicit terms acceptance");
const guideStart = guideJs.indexOf("const G=") + "const G=".length;
const guideEnd = guideJs.indexOf(";\n// Use an international", guideStart) > guideStart
  ? guideJs.indexOf(";\n// Use an international", guideStart)
  : guideJs.indexOf(";\nfunction init", guideStart);
assert(guideStart > "const G=".length && guideEnd > guideStart, "beginner guide catalog must be readable");
const guideCatalog = require("vm").runInNewContext(`(${guideJs.slice(guideStart, guideEnd)})`);
for (const locale of ['en','tr','es','pt-br','ru','zh-cn']) {
  assert(guideCatalog[locale], `beginner guide must include ${locale}`);
  assert.deepStrictEqual(Object.keys(guideCatalog[locale]).sort(), Object.keys(guideCatalog.en).sort(), `beginner guide keys differ for ${locale}`);
  for (const key of ["checklist","buyerSteps","sellerSteps","disputeSteps"]) assert(guideCatalog[locale][key].length >= 3, `${locale} must provide complete ${key}`);
}
for (const id of ["guideWalletTitle","guideWalletBody","guideChecklist","guideDisputeTitle","guideDisputeSteps","guideReviewNote"]) assert(html.includes(`id="${id}"`), `missing beginner guide section: ${id}`);
assert(html.includes("https://metamask.io/download/") && html.includes('href="/play"'), "guide must link to official MetaMask setup and the wallet-free demo");
assert(landing.includes('/mainnet#guide') && landing.includes("New to crypto wallets?"), "English landing must expose the step-by-step guide");
assert(landing.includes('class="landing-nav-stack"') && landing.includes('class="nav-guide"') && landing.indexOf('class="nav-guide"') < landing.indexOf('class="hero-grid"'), "English guide CTA must be a full-width navigation button above the hero content");
assert(!landing.includes('class="guided-entry"'), "English guide CTA must not remain duplicated inside the hero copy");
assert(css.includes(".landing-nav-stack") && css.includes(".landing-nav-row") && css.includes(".nav-guide"), "guide navigation button must have desktop and mobile layout styles");
assert(landing.includes("Automatic deals start at 10 USDC"), "Landing must show the Automatic deal minimum");
assert(landing.includes("Buyer Review deals start at 100 USDC"), "Landing must show the Buyer Review deal minimum");
for (const event of ["buyer_click", "seller_click", "demo_click", "founding_click", "language_click", "guide_click"]) {
  assert(landing.includes(`data-event="${event}"`), `Landing must mark ${event} for launch measurement`);
}
assert(analyticsJs.includes("sendBeacon") && analyticsJs.includes("utm_campaign"), "Launch measurement must record allow-listed campaign events");
assert(!analyticsJs.includes("localStorage") && !analyticsJs.includes("document.cookie"), "Launch measurement must not add tracking storage");
assert(analyticsJs.includes('replace(/\\/[^/]+$/,"/id")'), "Analytics must remove deal and negotiation identifiers from paths");
assert(js.includes("prepare-review-action") && js.includes("Appeal AI ruling"), "deal UI must expose the AI appeal path");
assert(html.includes('id="reasonHash"') && html.includes("hash created automatically"), "dispute form must accept a plain-language reason and explain automatic hashing");
assert(js.includes('crypto.subtle.digest("SHA-256"') && js.includes('action==="disputeDelivery"?await disputeReasonHash'), "dispute submission must hash the plain-language reason before preparing the on-chain action");
assert(!guideJs.includes("reason fingerprint") && !guideJs.includes("parmak izini") && guideJs.includes("creates the required hash automatically"), "beginner guide must not ask users to manufacture a dispute hash");
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
