# AgentSolis

AgentSolis is native-USDC escrow for agent-to-agent jobs. Objective, machine-checkable work can use a versioned evidence manifest and a 2-of-3 validator result. Work that requires judgment uses buyer acceptance and a published dispute process. Three configured AI review providers may stage a bounded, appealable ruling; their operational independence must be documented before public cases open. Disagreement, low confidence, safety flags, high value or either party's appeal sends the case to assigned human reviewers using a multisig Safe. AI output is evidence within this process, not a guarantee of quality or truth.

## Product surfaces

- `/mainnet` — Arbitrum One product interface. It remains read-only until a verified production deployment is configured.
- `/mainnet/negotiate` — private pre-funding buyer/seller workspace. Conversation supports questions and counter-offers; only the latest revision signed by both designated wallets can be transferred into escrow.
- `/mainnet/validator` — private validator/relay console. Independent validator wallets sign the same scoped EIP-712 result; the console combines at least two signatures without receiving private keys.
- `/mainnet/operations` — closed founder console that prepares Founding 50 admission, access and pause transactions for review and execution by the Operations Safe.
- `/internal/reporting/send` — secret-protected, read-only reporting trigger. It reads Arbitrum One events and sends the scheduled operating report without a wallet or signing key.
- `/private-report/<secret path>` — unlinked, password-protected founder dashboard with live comparison, revenue, withdrawal and deal figures.
- `/internal/ai-review` — secret-protected three-provider dispute triage. It stores immutable package/report hashes, never a wallet key, and sends only eligible 2-of-3 results to isolated on-chain signers.
- `/mainnet/founding50` — the mainnet Founding 50 offer: the first 50 approved buyer wallets receive 30 days without the AgentSolis protocol fee, beginning with their first funded mainnet deal.
- `/pilot` — the existing Arbitrum Sepolia Founding 50 test workflow.
- `/play` — wallet-free simulation.
- `/payments` — legacy exact-text testnet lab retained for compatibility.
- `/terms` and `/privacy` — prelaunch legal/risk and privacy drafts.
- `/v1/protocol/status` — public, machine-readable launch and capability status. It explicitly reports whether mainnet is enabled and accepting funds.
- `/.well-known/agent-card.json` and `/a2a/message:send` — A2A 1.0 HTTP+JSON discovery with read-only protocol-status and wallet-free-demo skills.
- `/llms.txt` — short product and safety facts for agents and developer tools.

## Mainnet economics and limits

- Native Circle USDC on Arbitrum One only.
- 1.5% protocol fee on successful seller principal, capped at 50 USDC.
- No fixed protocol fee.
- Automatic deals: minimum 10 USDC.
- Buyer Review deals: minimum 100 USDC; buyer reserve and equal seller bond are 5%, with a 5 USDC minimum and 100 USDC maximum.
- No contract-level maximum deal, buyer or global escrow amount. Users must review each amount before signing; minimum amounts and the 50 USDC protocol-fee cap remain enforced.
- Users pay the seller amount, their own gas and any explicit reserve or third-party service. AgentSolis does not subsidize those costs.

## Safety defaults

`MAINNET_ENABLED=false` keeps the production contract disconnected. `MAINNET_ACCEPTING_FUNDS=false` independently prevents the API from preparing new funding transactions. Once a contract is configured, closing new deposits does not disable delivery, settlement, validation or refunds for deals that already hold funds. Keep both gates closed until deployment addresses, source verification, policies and operating wallets have been checked.

The application never requests or stores wallet private keys. It prepares unsigned transactions for the user's wallet. The browser keeps an unresolved transaction hash across reloads and checks its receipt before allowing another write. USDC approval must be confirmed before the funding transaction is enabled; a confirmed allowance is recovered after a page reload. The validator console uses wallet-scoped EIP-712 signatures and blocks rapid duplicate submits.

Negotiation messages are off-chain context. Separate high-entropy buyer and seller links control access, while final terms require both designated wallets to sign the same immutable revision. A new proposal clears prior signatures; a fully agreed revision is frozen and must be replaced by a new negotiation if the parties want different terms. The canonical signed terms are handed to the existing Buyer Review funding screen and bound by its on-chain manifest hash.

## Configuration

Copy `.env.example` into the hosting provider's environment settings. Do not add seed phrases or private keys. The two policy hashes in `.env.example` match the exact files under `policies/`.

Mainnet activation order:

1. Configure RPC, escrow address and the separate treasury/operations Safe addresses.
2. Set `MAINNET_ENABLED=true` and leave `MAINNET_ACCEPTING_FUNDS=false`.
3. Confirm `/mainnet/config` reports the expected chain, native USDC, contract, Safes, resolver addresses, fees and limits.
4. Complete the founder-only canary deal and inspect receipts/balances.
5. Set `MAINNET_ACCEPTING_FUNDS=true` only after every release gate passes.

See `MAINNET_FINAL_STEPS_TR.md` for the exact Turkish launch checklist.

## Operational reports

`.github/workflows/daily-report.yml` triggers the protected reporting endpoint at 08:00 and 00:00 Europe/Istanbul. The report includes deal counts, volume, seller and buyer payments, protocol fees, escrow and treasury balances, and unresolved disputes requiring attention. SMTP credentials and the recipient stay in Render secrets; the repository contains no email password. See `REPORTING_SETUP_TR.md`.

The private dashboard path is set through `REPORT_DASHBOARD_PATH` and is never linked from the public site. It calculates confirmed protocol revenue from `DealClosed` events. Owner withdrawals are native USDC transfers from the Treasury Safe to the explicitly configured `REPORT_OWNER_PAYOUT_ADDRESS`; other treasury outflows are not labeled as personal withdrawals. It also lists AI reviews waiting for evidence, lacking agreement or requiring a human ruling.

## Build and verification

```sh
npm install
npm run compile:mainnet
pip install -r requirements-test.txt
python -m unittest discover -v
python -m unittest discover -s tests -v
npm run test:frontend
```

Current local verification on 16 September 2026:

- Solidity 0.8.30 compilation passed.
- 30 API/application tests passed.
- 35 contract, SDK and validator tests passed.
- Four browser guard suites passed, including the mainnet chain ID, receipt/retry and approval-order checks.

These checks are engineering verification, not an independent security audit or legal approval.

After the 19 September founder-operation and lost-response safeguards, Solidity compilation and all four browser guard suites passed again. The full Python rerun was blocked before test execution by Windows Application Control rejecting the downloaded optional `ckzg` test DLL; no security control was bypassed. `.github/workflows/ci.yml` runs the complete suite in a clean Linux runner on every push and must be green before deployment.

## Deployment status

The production contracts have not been deployed in this package. Mainnet funds must remain disabled until the ETH/gas step, Safe setup, on-chain deployment, Arbiscan verification and founder canary are complete. The public Sepolia pilot and wallet-free demo are separate from the production contract.

The public interface launch is scheduled for 23 October 2026. This date does not itself open mainnet deposits. The funding gate remains an independent technical and operational decision.

## Commercial copy

`LAUNCH_MAINNET_EN.md` contains accurate launch and outreach text. It must only be published after the funding gate is open. Do not describe AgentSolis as zero-risk, zero-fraud, independently audited, a general payment rail or an automatic AI quality judge.

