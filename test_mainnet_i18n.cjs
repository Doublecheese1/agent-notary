const fs = require("fs");
const assert = require("assert");
const vm = require("vm");

const i18nSource = fs.readFileSync("static/mainnet-i18n.js", "utf8");
const appSource = fs.readFileSync("static/mainnet.js", "utf8");
const html = fs.readFileSync("static/mainnet.html", "utf8");
const server = fs.readFileSync("mainnet.py", "utf8");
const international = fs.readFileSync("international.py", "utf8");

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
for (const locale of locales) {
  assert(api.catalog[locale], `missing static catalog: ${locale}`);
  for (const key of Object.keys(api.catalog.en)) {
    assert.strictEqual(typeof api.catalog[locale][key], "string", `missing ${locale} static translation: ${key}`);
    assert(api.catalog[locale][key].trim(), `empty ${locale} static translation: ${key}`);
  }
}

const dynamicStart = appSource.indexOf("const D=") + "const D=".length;
const dynamicEnd = appSource.indexOf(";\r\nconst T=", dynamicStart) >= 0
  ? appSource.indexOf(";\r\nconst T=", dynamicStart)
  : appSource.indexOf(";\nconst T=", dynamicStart);
assert(dynamicStart > "const D=".length && dynamicEnd > dynamicStart, "dynamic translation catalog must be readable");
const dynamic = vm.runInNewContext(`(${appSource.slice(dynamicStart, dynamicEnd)})`);
for (const locale of locales) {
  assert(dynamic[locale], `missing dynamic catalog: ${locale}`);
  assert.deepStrictEqual(Object.keys(dynamic[locale]).sort(), Object.keys(dynamic.en).sort(), `dynamic translation keys differ for ${locale}`);
}

assert(html.indexOf('/mainnet/i18n.js') < html.indexOf('/mainnet/app.js'), "translation script must load before transaction logic");
assert(server.includes('@router.get("/i18n.js"'), "server must expose the translation script");
for (const locale of locales.slice(1)) {
  assert(international.includes(`href="/mainnet?lang={locale}"`), "localized landing must preserve its language in the transaction link");
}
assert(!international.includes("İngilizce işlem ekranını aç"), "Turkish call to action must not claim that the workspace is English-only");
assert(!international.includes("workspace in English"), "stale English-only workspace wording must be removed");
assert(appSource.includes("localizedDealLink"), "shareable deal links must retain the selected language");
assert(i18nSource.includes("🇹🇷") && i18nSource.includes("🇪🇸") && i18nSource.includes("🇧🇷") && i18nSource.includes("🇷🇺") && i18nSource.includes("🇨🇳"), "language selector must retain country flags");
assert(appSource.includes('CHAIN="0xa4b1"') && appSource.includes('USDC="0xaf88'), "localization must not change chain or token identifiers");
console.log("Mainnet localization guards passed for 6 languages, static and dynamic text, links and technical identifiers.");
