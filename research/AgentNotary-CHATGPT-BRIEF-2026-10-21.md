# AgentNotary – Launch Readiness Brief (from New Bot, 21 Oct 2026)

Hi ChatGPT. I'm building AgentNotary Protocol: a deterministic escrow / settlement API for autonomous AI agents. After launch, my marketing assistant (another AI bot) will find customers in agent marketplaces and developer communities. It researched where those customers are. Problem: almost all of those places only list products that agents can actually call. Please help me make AgentNotary "listable". Below is what we need, why, and suggestions. Please first ask me what already exists in the codebase, then propose a concrete plan and build it step by step.

## 1. Why this matters (marketplace requirements)

| Place | What it requires to list us |
|---|---|
| Coinbase x402 Bazaar (docs.cdp.coinbase.com/x402/bazaar) | A live HTTP endpoint that returns HTTP 402 with x402 payment requirements, including `bazaar` discovery metadata. Listing happens automatically after the first payment settles through Coinbase's facilitator. No signup form. |
| x402scan (x402scan.com) | "Add your API" – they probe the URL and expect a valid x402 402 response. ~38K sellers / ~36K buyers / ~$1.5M volume in last 30 days. |
| Nevermined catalog (nevermined.app/catalog) | Paid plan + endpoint answering with x402 payment requirements. |
| Skyfire seller directory | Seller application; buyer agents pay with Skyfire tokens and find sellers via Skyfire's MCP server. |
| Official MCP Registry (registry.modelcontextprotocol.io), Smithery, mcp.so, Glama, PulseMCP | A published MCP server (npm/PyPI package or remote HTTP MCP server) with a `server.json`. |
| Virtuals ACP (app.virtuals.io/acp) | Register an agent as provider/evaluator. Has its own escrow (partial competitor) – AgentNotary could act as an evaluator or add settlement attestation. |
| Fetch.ai Agentverse, Olas Mech Marketplace | A running agent endpoint / mech that other agents can hire. |
| ERC-8004 registries (8004scan.io) | On-chain agent identity registration (credibility + reputation). |
| Google A2A / AP2 | Publish an A2A "Agent Card" (`/.well-known/agent-card.json`) describing skills, payment and dispute handling. |
| Agent Payments Stack (agentpaymentsstack.com) | Simple submit form; already lists escrow competitors (Agent Escrow Bond, AgentEscrow, RageQuit Escrow, SpendBound). |

Conclusion: before marketing, AgentNotary needs (a) paid x402 endpoints, (b) an MCP server, (c) a zero-friction demo. Ideally also (d) an A2A agent card and (e) an ERC-8004 registration.

## 2. Must-have deliverables (priority order)

### P0 – x402-paid public API
- At least 2–3 core operations exposed as HTTP endpoints, e.g.:
  - `POST /v1/escrow` – create escrow (buyer agent, seller agent, amount, conditions, deadline, idempotency key)
  - `POST /v1/escrow/{id}/release` and `/refund` / `/dispute`
  - `GET  /v1/escrow/{id}` – state
  - `POST /v1/receipts/verify` – verify a Settlement Attestation Receipt (cheap, great "first paid call")
- Unpaid request → `402 Payment Required` with standard x402 payment requirements (network e.g. Base, asset USDC, price, payTo, resource description, input/output schema). Paid request with `X-PAYMENT` header → verify + settle via a facilitator (Coinbase CDP facilitator so Bazaar indexing works) → return result.
- Include Bazaar discovery metadata (description, input schema, output schema) so we get auto-listed.
- Deterministic behavior: idempotency keys / operation IDs on every mutating call, so retries never double-pay or double-release. This is our core selling point – make it visible in responses (operation_id, state, signed receipt).
- Signed receipts (e.g. Ed25519/EIP-712) for every state transition; publicly verifiable.
- Start on testnet (Base Sepolia) and mainnet with tiny prices (e.g. $0.001–$0.01 per call).

### P0 – MCP server
- Tools: `create_escrow`, `get_escrow`, `release_escrow`, `refund_escrow`, `open_dispute`, `verify_receipt`.
- Two forms: local package (`npx agentnotary-mcp` / `pip install agentnotary-mcp`) and remote Streamable HTTP MCP server.
- `server.json` for the official MCP Registry; README with a 3-line install for Claude Desktop / Cursor.
- Testnet mode by default so devs can try without real money.

### P0 – Zero-friction demo (`/play`)
- Works with no signup and no wallet: server-side sandbox wallets on testnet, shows a full flow (create → deliver → release, plus a failure/retry case proving no double payment).
- Must work in under 2 minutes. This is also the gate for a Show HN post.

### P1
- A2A Agent Card at `/.well-known/agent-card.json` with skills + AP2 payment/dispute info.
- ERC-8004 identity registration for the AgentNotary agent.
- SDKs: TypeScript and Python thin clients; examples for LangChain, CrewAI, OpenAI Agents SDK, Mastra.
- Docs site: quickstart, API reference (OpenAPI spec), pricing page, status page.
- Clear free tier (e.g. first N calls free / testnet always free).

### P2
- Virtuals ACP evaluator/provider integration.
- Fetch.ai Agentverse agent, Olas mech.
- Dashboard with API keys for non-crypto users (card billing), for enterprise later (AWS / Google Cloud Marketplace).

## 3. My (marketing bot's) opinions / suggestions
1. **Differentiation:** The market already has escrow players (Virtuals ACP built-in escrow, Nevermined, Agent Escrow Bond, AgentEscrow, RageQuit, SpendBound). Don't sell "escrow" alone. Sell **deterministic settlement + verifiable receipts + safe retries** ("an agent can retry a timed-out payment 10 times and it settles exactly once, with a signed receipt"). This is exactly the pain I saw in x402 GitHub issues (#2823 payment integrity, #1195 settlement attestation, A2A x402 #60 spend limits / circuit breakers).
2. **Be neutral infrastructure:** work across x402, AP2, ACP rather than competing with them – e.g. "verify_receipt" works for anyone's settlement.
3. **Cheapest first paid call:** `verify_receipt` at ~$0.001 gets us into Bazaar/x402scan fast and gives real transaction stats.
4. **Spend limits & circuit breakers** as a built-in feature (per-agent daily cap, auto-pause on anomalies) – developers are asking for it.
5. **Developer experience beats features:** one-line install, testnet by default, copy-paste examples.
6. **Trust signals:** open-source the MCP server and SDKs, publish the receipt format as a spec, security notes, audit plan if smart contracts are used.
7. **Metrics to expose** (helps marketing): number of escrows, volume, retry-saves (duplicate payments prevented).

## 4. What I need back from you (ChatGPT)
- Current state check: what of the above already exists?
- Concrete architecture + task list for P0, with estimates.
- Then implement P0 step by step with tests.
- At the end, give me a short "launch facts" sheet: public URLs (API, docs, /play, MCP package name, registry links), pricing, supported networks/assets, and 3 one-sentence value propositions – my marketing bot will use it to find customers and write outreach.
