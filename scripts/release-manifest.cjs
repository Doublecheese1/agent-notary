"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..");
const hash = file => crypto.createHash("sha256").update(fs.readFileSync(path.join(root, file))).digest("hex");
const automatic = JSON.parse(fs.readFileSync(path.join(root, "policies/automatic-json-evidence-v1.json"), "utf8"));
const review = JSON.parse(fs.readFileSync(path.join(root, "policies/buyer-review-v1.json"), "utf8"));
const manifest = {
  product: "AgentNotary",
  release: "mainnet-candidate",
  chain_id: 42161,
  network: "Arbitrum One",
  native_usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  economics: {protocol_fee_bps: 150, protocol_fee_cap_usdc: 50, fixed_fee_usdc: 0},
  limits: {automatic_min_usdc: 10, buyer_review_min_usdc: 100, deal_max_usdc: 1000, global_escrow_max_usdc: 10000},
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
  deployment_inputs: {deployer: "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD", treasury_safe: "", operations_safe: "", human_review_safe: "", ai_review_resolver: "", validator_a: "", validator_b: "", validator_c: "", ai_reviewer_a: "", ai_reviewer_b: "", ai_reviewer_c: ""},
  gates: {mainnet_enabled: false, accepting_funds: false, deployment_ui: false, operations_ui: false},
  warning: "Not deployed and not independently audited. Verify every hash and address before funding."
};
fs.mkdirSync(path.join(root, "release"), {recursive: true});
fs.writeFileSync(path.join(root, "release/mainnet-release.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log("Wrote release/mainnet-release.json");
