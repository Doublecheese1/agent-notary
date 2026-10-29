const fs = require("fs");
const assert = require("assert");
const vm = require("vm");

const i18nSource = fs.readFileSync("static/mainnet-i18n.js", "utf8");
const appSource = fs.readFileSync("static/mainnet.js", "utf8");
const html = fs.readFileSync("static/mainnet.html", "utf8");
const server = fs.readFileSync("mainnet.py", "utf8");
const international = fs.readFileSync("international.py", "utf8");
const css = fs.readFileSync("static/brand.css", "utf8");

const sandbox = {
  window: {},
  location: {search: "?lang=tr", href: "https://agentsolis.solists.com.tr/mainnet?lang=tr", pathname: "/mainnet"},
  localStorage: {getItem: () => null, setItem: () => {}},
  document: {readyState: "loading", addEventListener: () => {}},
  URL, URLSearchParams,
};
vm.runInNewContext(i18nSource, sandbox);
const api = sandbox.window.AgentSolisI18n;
const locales = ["en", "tr", "es", "pt-br", "ru", "zh-cn"];
assert.strictEqual(api.lang, "tr", "query string must select the workspace language");
const staleSandbox = {
  window: {},
  location: {search: "", href: "https://agentsolis.solists.com.tr/mainnet?role=buyer#guide", pathname: "/mainnet"},
  localStorage: {getItem: () => "tr", setItem: () => {throw new Error("default language must not be written to browser storage")}},
  document: {readyState: "loading", addEventListener: () => {}},
  URL, URLSearchParams,
};
vm.runInNewContext(i18nSource, staleSandbox);
assert.strictEqual(staleSandbox.window.AgentSolisI18n.lang, "en", "a URL without lang must always open in English even after an earlier Turkish visit");
assert.match(staleSandbox.window.AgentSolisI18n.languageUrl("en"), /[?&]lang=en(?:&|#|$)/, "choosing English must keep an explicit language in the URL");
for (const locale of locales) {
  assert(api.catalog[locale], `missing static catalog: ${locale}`);
  for (const key of Object.keys(api.catalog.en)) {
    assert.strictEqual(typeof api.catalog[locale][key], "string", `missing ${locale} static translation: ${key}`);
    assert(api.catalog[locale][key].trim(), `empty ${locale} static translation: ${key}`);
  }
}
assert(api.catalog.en.previewBody.includes("Public mainnet access is open"), "English workspace must show current public access status");
assert(api.catalog.tr.previewBody.includes("Halka açık mainnet erişimi açıktır"), "Turkish workspace must show current public access status");
assert(!i18nSource.includes("New mainnet deposits stay closed"), "stale English closed-access copy must be removed");

const dynamicStart = appSource.indexOf("const D=") + "const D=".length;
const dynamicEnd = [";\r\nconst REVIEW_COPY=", ";\nconst REVIEW_COPY=", ";\r\nconst T=", ";\nconst T="]
  .map((marker) => appSource.indexOf(marker, dynamicStart))
  .filter((index) => index >= 0)
  .sort((a, b) => a - b)[0];
assert(dynamicStart > "const D=".length && dynamicEnd > dynamicStart, "dynamic translation catalog must be readable");
const dynamic = vm.runInNewContext(`(${appSource.slice(dynamicStart, dynamicEnd)})`);
const fundingGuard = appSource.match(/^function updateFundingButtons\(\)\{.*\}$/m)?.[0];
if (appSource.includes("const REVIEW_COPY=")) {
assert(fundingGuard, "funding preflight guard must exist");
const nodes = { approve: { before(node) { nodes[node.id] = node; } }, propose: {} };
const guardContext = {
  REVIEW_COPY: { en: { closed: "closed", needWallet: "wallet", needEth: "ETH required", ready: "ready" } },
  I18N: { lang: "en" }, account: "0x111", cfg: { accepting_funds: true },
  fundingEthReady: false, pendingHash: "", uncertainIntent: null,
  draft: { approvalConfirmed: false }, $: (id) => nodes[id],
  document: { createElement: () => ({ setAttribute() {} }) },
};
vm.runInNewContext(fundingGuard, guardContext);
guardContext.updateFundingButtons();
assert(nodes.approve.disabled && nodes.propose.disabled, "zero ETH must block approval and funding");
assert.strictEqual(nodes.fundingPreflight.textContent, "ETH required");
guardContext.fundingEthReady = true;
guardContext.updateFundingButtons();
assert(!nodes.approve.disabled && nodes.propose.disabled, "funding needs an approved USDC allowance");
guardContext.draft.approvalConfirmed = true;
guardContext.updateFundingButtons();
assert(nodes.approve.disabled && !nodes.propose.disabled, "confirmed approval enables funding");
guardContext.pendingHash = "0xpending";
guardContext.updateFundingButtons();
assert(nodes.approve.disabled && nodes.propose.disabled, "pending transaction blocks duplicate action");
}
for (const locale of locales) {
  assert(dynamic[locale], `missing dynamic catalog: ${locale}`);
  assert.deepStrictEqual(Object.keys(dynamic[locale]).sort(), Object.keys(dynamic.en).sort(), `dynamic translation keys differ for ${locale}`);
}
assert.strictEqual(dynamic.en.accessActive, "Public mainnet access is open.", "dynamic English access state must be public");
assert.strictEqual(dynamic.tr.accessActive, "Halka açık mainnet erişimi açık.", "dynamic Turkish access state must be public");

assert(html.indexOf('/mainnet/i18n.js') < html.indexOf('/mainnet/app.js'), "translation script must load before transaction logic");
assert(server.includes('@router.get("/i18n.js"'), "server must expose the translation script");
for (const locale of locales.slice(1)) {
  assert(international.includes(`href="/mainnet?lang={locale}#guide"`), "localized landing must preserve its language in the guided transaction link");
}
assert(international.includes('data-event="guide_click"') && international.includes('data["guide"]'), "every localized landing must expose its translated guide link");
assert(international.includes('class="landing-nav-stack"') && international.includes('class="nav-guide"'), "localized guide links must appear as navigation buttons");
assert(!international.includes('class="guided-entry"'), "localized guide links must not remain duplicated inside hero copy");
assert(!international.includes("İngilizce işlem ekranını aç"), "Turkish call to action must not claim that the workspace is English-only");
assert(!international.includes("workspace in English"), "stale English-only workspace wording must be removed");
assert(appSource.includes("localizedDealLink"), "shareable deal links must retain the selected language");
assert(i18nSource.includes("🇹🇷") && i18nSource.includes("🇪🇸") && i18nSource.includes("🇧🇷") && i18nSource.includes("🇷🇺") && i18nSource.includes("🇨🇳"), "language selector must retain country flags");
assert(appSource.includes('CHAIN="0xa4b1"') && appSource.includes('USDC="0xaf88'), "localization must not change chain or token identifiers");
assert(css.includes(".role.selected:hover:not(:disabled)"), "selected role must remain readable after a sticky mobile hover");
console.log("Mainnet localization guards passed for 6 languages, static and dynamic text, links and technical identifiers.");
