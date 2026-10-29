"use strict";
(() => {
  const statuses = document.querySelectorAll("[data-live-mainnet-status]");
  if (!statuses.length) return;
  const update = (key) => { for (const status of statuses) status.textContent = status.dataset[key]; };
  fetch("/mainnet/config", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("Live config unavailable");
      return response.json();
    })
    .then((config) => {
      if (config.enabled === true && config.accepting_funds === true && config.public_access === true && config.paused === false) {
        update("open");
      } else if (config.enabled === true && config.public_access === true && config.paused === false) {
        update("limited");
      } else {
        update("closed");
      }
    })
    .catch(() => update("unknown"));
})();
