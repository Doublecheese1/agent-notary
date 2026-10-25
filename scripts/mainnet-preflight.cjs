const fs = require("fs");
const crypto = require("crypto");

const release = JSON.parse(fs.readFileSync("release/mainnet-release.json", "utf8"));
const expectedDeployer = "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD";
const address = /^0x[0-9a-fA-F]{40}$/;
const hash = /^0x[0-9a-fA-F]{64}$/;
const failures = [];
const pending = [];

function requireValue(ok, message) {
  if (!ok) failures.push(message);
}

requireValue(release.chain_id === 42161, "Chain must be Arbitrum One (42161).");
requireValue(release.native_usdc.toLowerCase() === "0xaf88d065e77c8cc2239327c5edb3a432268e5831", "Native Circle USDC address is wrong.");
requireValue(release.deployment_inputs.deployer === expectedDeployer, "Deployer must be the controlled MetaMask Account 1.");
requireValue(hash.test(release.policies.automatic_hash) && hash.test(release.policies.review_hash), "Policy hashes are missing.");
requireValue(typeof release.gates.accepting_funds === "boolean", "Release manifest must declare the current public funding gate.");

const fileMap = {
  escrow_source: "contracts/AgentNotaryMainnetEscrow.sol",
  quorum_source: "contracts/AgentNotaryValidatorQuorum.sol",
  ai_review_resolver_source: "contracts/AgentNotaryAIReviewResolver.sol",
  escrow_artifact: "artifacts/AgentNotaryMainnetEscrow.json",
  quorum_artifact: "artifacts/AgentNotaryValidatorQuorum.json",
  ai_review_resolver_artifact: "artifacts/AgentNotaryAIReviewResolver.json",
  automatic_policy: "policies/automatic-json-evidence-v1.json",
  review_policy: "policies/buyer-review-v1.json",
};

for (const [key, path] of Object.entries(fileMap)) {
  if (!fs.existsSync(path)) {
    failures.push(`Missing release file: ${path}`);
    continue;
  }
  const canonical = fs.readFileSync(path, "utf8").replace(/\r\n/g, "\n");
  const actual = crypto.createHash("sha256").update(canonical, "utf8").digest("hex");
  requireValue(actual === release.files_sha256[key], `SHA-256 mismatch: ${path}`);
}

for (const key of ["treasury_safe", "operations_safe", "human_review_safe", "validator_a", "validator_b", "validator_c", "ai_reviewer_a", "ai_reviewer_b", "ai_reviewer_c"]) {
  if (!address.test(release.deployment_inputs[key] || "")) pending.push(key);
}

console.log("AgentSolis mainnet preflight");
console.log(`- Static release integrity: ${failures.length ? "FAILED" : "PASS"}`);
console.log(`- Controlled deployer: ${release.deployment_inputs.deployer}`);
console.log(`- Public funding gate: ${release.gates.accepting_funds ? "OPEN" : "CLOSED (safe)"}`);
console.log(`- Role addresses still required before deployment: ${pending.length ? pending.join(", ") : "none"}`);
console.log("- ETH balance and on-chain deployment are intentionally the final wallet-signed steps.");

if (failures.length) {
  for (const item of failures) console.error(`ERROR: ${item}`);
  process.exit(1);
}
