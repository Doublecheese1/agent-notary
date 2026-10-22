"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..");
// Release inputs are text files. Hash their canonical LF representation so
// Windows and Linux checkouts produce the same manifest.
const hash = file => {
  const canonical = fs.readFileSync(path.join(root, file), "utf8").replace(/\r\n/g, "\n");
  return crypto.createHash("sha256").update(canonical, "utf8").digest("hex");
};
const automatic = JSON.parse(fs.readFileSync(path.join(root, "policies/automatic-json-evidence-v1.json"), "utf8"));
const review = JSON.parse(fs.readFileSync(path.join(root, "policies/buyer-review-v1.json"), "utf8"));
const releasePath = path.join(root, "release/mainnet-release.json");
const existing = fs.existsSync(releasePath) ? JSON.parse(fs.readFileSync(releasePath, "utf8")) : {};
const recorded = existing.deployment_inputs || {};
const publicAddress = value => /^0x[0-9a-fA-F]{40}$/.test(value || "") ? value : "";
const manifest = {
  product: "AgentSolis",
  release: "mainnet-candidate",
  chain_id: 42161,
  network: "Arbitrum One",
  native_usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  economics: {protocol_fee_bps: 150, protocol_fee_cap_usdc: 50, fixed_fee_usdc: 0},
  limits: {automatic_min_usdc: 10, buyer_review_min_usdc: 100, deal_max_usdc: null, global_escrow_max_usdc: null},
  policies: {
    automatic_id: automatic.id,
    automatic_hash: "0xfc80263827b1f14bff464b89bebc2c5d237a1b355706054f47de87fd1e5bc556",
    review_id: review.id,
    review_hash: "0x3f9234a62a913d1efc1882bc7c2b2bd289cbcb28c8dcf62f5f949c49c99b3014"
  },
  files_sha256: {
    escrow_source: hash("contracts/AgentNotaryMainnetEscrow.sol"),
    quorum_source: hash("contracts/AgentNotaryValidatorQuorum.sol"),
    ai_review_resolver_source: hash("contracts/AgentNotaryAIReviewResolver.sol"),
    escrow_artifact: hash("artifacts/AgentNotaryMainnetEscrow.json"),
    quorum_artifact: hash("artifacts/AgentNotaryValidatorQuorum.json"),
    ai_review_resolver_artifact: hash("artifacts/AgentNotaryAIReviewResolver.json"),
    automatic_policy: hash("policies/automatic-json-evidence-v1.json"),
    review_policy: hash("policies/buyer-review-v1.json")
  },
  deployment_inputs: {
    deployer: "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD",
    treasury_safe: publicAddress(recorded.treasury_safe),
    operations_safe: publicAddress(recorded.operations_safe),
    human_review_safe: publicAddress(recorded.human_review_safe),
    ai_review_resolver: publicAddress(recorded.ai_review_resolver),
    validator_a: "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD",
    validator_b: "0x1Fb26508Ab8467beb0a27714772868d8ea2dDDf2",
    validator_c: "0x2113caE8042E8fCf837498Eb3297D8563D92Dc2A",
    ai_reviewer_a: "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD",
    ai_reviewer_b: "0x1Fb26508Ab8467beb0a27714772868d8ea2dDDf2",
    ai_reviewer_c: "0x2113caE8042E8fCf837498Eb3297D8563D92Dc2A"
  },
  gates: {mainnet_enabled: false, accepting_funds: false, deployment_ui: false, operations_ui: false},
  warning: "Not deployed and not independently audited. Verify every hash and address before funding."
};
fs.mkdirSync(path.join(root, "release"), {recursive: true});
fs.writeFileSync(releasePath, JSON.stringify(manifest, null, 2) + "\n");
console.log("Wrote release/mainnet-release.json");
