"use strict";

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const addressPattern = /^0x[0-9a-fA-F]{40}$/;
const [treasury, operations, humanReview] = process.argv.slice(2);

if (![treasury, operations, humanReview].every(value => addressPattern.test(value || ""))) {
  console.error("Usage: node scripts/finalize-safe-addresses.cjs <treasury> <operations> <human-review>");
  process.exit(1);
}
if (new Set([treasury, operations, humanReview].map(value => value.toLowerCase())).size !== 3) {
  console.error("Treasury, Operations and Human Review must be three distinct Safe addresses.");
  process.exit(1);
}

const safePath = path.join(root, "release", "safe-setup.json");
const releasePath = path.join(root, "release", "mainnet-release.json");
const safeSetup = JSON.parse(fs.readFileSync(safePath, "utf8"));
const release = JSON.parse(fs.readFileSync(releasePath, "utf8"));
const byName = new Map([
  ["AgentSolis Treasury", treasury],
  ["AgentSolis Operations", operations],
  ["AgentSolis Human Review", humanReview],
]);

for (const safe of safeSetup.safes) safe.address = byName.get(safe.name) || safe.address;
safeSetup.status = "addresses_recorded_pending_onchain_verification";
release.deployment_inputs.treasury_safe = treasury;
release.deployment_inputs.operations_safe = operations;
release.deployment_inputs.human_review_safe = humanReview;

fs.writeFileSync(safePath, JSON.stringify(safeSetup, null, 2) + "\n");
fs.writeFileSync(releasePath, JSON.stringify(release, null, 2) + "\n");
console.log("Recorded three distinct Safe addresses in release files.");
console.log("Next: verify code, owners and getThreshold() = 2 on Arbitrum One before deployment.");
