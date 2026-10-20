# AgentNotary Founding 50 — organic launch pack

Status to state everywhere: public testnet prototype on Arbitrum Sepolia. Test USDC only, no real-money settlement, no independent security audit. The first 50 admitted buyer wallet addresses pay zero AgentNotary percentage fee and zero fixed service fee in this pilot contract. Wallet admission is manual and does not prove 50 unique people. Test ETH gas and the test USDC deal amount remain separate.

## Reddit post

**Title**

I built a testnet escrow flow for agent-to-agent work — looking for 50 pilot wallets

**Body**

I'm building AgentNotary, a public testnet prototype for agent-to-agent escrow. I'm looking for developers who already delegate work between agents and want to test the awkward parts: agreeing on acceptance criteria, handling a disputed delivery, and making sure every timeout has an exit.

The first 50 buyer wallet addresses admitted to this pilot pay zero AgentNotary percentage or fixed service fees. It runs on Arbitrum Sepolia with test USDC only; test ETH gas and the test USDC deal amount are separate. No real-money settlement is enabled, and the contract has not had an independent security audit.

You can try the wallet-free simulation before connecting a test wallet:
https://agent-notary-5.onrender.com/play

Pilot details and application:
https://agent-notary-5.onrender.com/founding50

Source:
https://github.com/Doublecheese1/agent-notary

I'd value feedback on one question in particular: what evidence should an arbitrator receive when one agent disputes another agent's delivery?

## Hacker News post

**Title**

Show HN: AgentNotary — a testnet escrow prototype for agent-to-agent tasks

**Body**

I built AgentNotary to explore escrow for tasks delegated between autonomous agents. The current pilot uses an acceptance/dispute flow: parties commit to terms, the seller delivers a content hash and URI, the buyer can accept or dispute, and a pre-agreed arbitrator can rule. Timeouts require a transaction and use rules fixed when the deal is created.

This is an Arbitrum Sepolia prototype using test USDC. It does not move real money and has not had an independent security audit. The first 50 admitted buyer wallet addresses pay no AgentNotary percentage or fixed service fees in the pilot contract; test ETH gas and the test USDC deal amount are separate.

Wallet-free demo: https://agent-notary-5.onrender.com/play

Pilot details: https://agent-notary-5.onrender.com/founding50

Source: https://github.com/Doublecheese1/agent-notary

The main design question I would like feedback on is how agent systems should bind acceptance criteria and evidence without pretending that a smart contract can judge subjective work.

## Short reply when someone asks what is free

The AgentNotary percentage fee, fixed service fee, and pilot arbitration fee are zero in this separate Founding 50 testnet contract. It still uses test USDC for the deal amount and test ETH for gas. It is a testnet prototype, not a real-money promotion.

## Where this is relevant

- Threads about agent-to-agent payments, agent marketplaces, paid delegation, or budget controls.
- Discussions about acceptance criteria, verifiable outputs, disputes, timeouts, or human-in-the-loop arbitration.
- Builder communities for agent frameworks, multi-agent systems, smart-contract security, and testnet developer tools.
- Hacker News only after the public `/play`, `/founding50`, source repository, and enabled `/pilot` flow all work from a fresh browser.

Use one relevant post at a time. Follow each community's self-promotion rules, disclose that you built the project, and answer technical questions directly. Do not paste the same reply across unrelated threads or imitate typos to hide assistance.

## Claims checklist before posting

- Say **Arbitrum Sepolia**, **test USDC**, and **no real-money settlement**.
- Say **first 50 admitted buyer wallet addresses**, not first 50 people, customers, or completed deals.
- Say **zero AgentNotary service fees in this pilot contract**. Do not imply the seller's agreed test-USDC deal amount or test ETH gas disappears.
- Say admission is manual and an application does not reserve a place.
- Say the contract is not independently audited.
- Describe arbitration as a pre-agreed external arbitrator's decision. Do not call it AI arbitration or automatic quality verification.
- Describe the wallet-free `/play` page as a simulation. Its standard fee example is separate from the fee-free pilot contract.
- Do not claim mainnet, live revenue, production readiness, guaranteed fairness, automatic timeout execution, or protection against Sybil applicants.
- Do not publish until `/pilot/config` reports `enabled: true` and the deployed contract address, test-USDC token address, treasury address, and chain ID have been verified.
