"use strict";
(async function () {
  const nodes = document.querySelectorAll("[data-live-funding-status], .launch, .trust-band .notice, .workspace .product-head + .notice, .content-page p");
  const statusNodes = [...nodes].filter(node => node.matches("[data-live-funding-status], .launch, .trust-band .notice, .workspace .product-head + .notice") || /Current status:|Public mainnet funding is open\./i.test(node.textContent || ""));
  if (!statusNodes.length) return;
  const set = (text, open) => statusNodes.forEach(node => {
    node.textContent = text;
    node.classList.toggle("ok", !!open);
    node.classList.toggle("bad", !open);
  });
  try {
    const response = await fetch("/mainnet/config", {cache: "no-store"});
    const config = await response.json();
    if (config.accepting_funds === true) set("Public mainnet funding is open. Connect a wallet to create or track a deal.", true);
    else if (config.public_access === true && config.paused === false) set("Public mainnet access is open, but funding is currently unavailable according to the live status.", false);
    else set("Live mainnet funding is not currently available. Check the live status before signing.", false);
  } catch {
    set("Live mainnet funding status could not be checked. Do not sign until it is confirmed.", false);
  }
})();
