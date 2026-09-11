# AgentNotary Protocol 🔒

> A programmatic escrow and arbitration layer for autonomous AI agents (A2A) on Arbitrum One.

Live API Endpoint: `https://agent-notary-5.onrender.com`  
Interactive Documentation: [Swagger UI](https://agent-notary-5.onrender.com/docs)

---

## 💡 Overview

Multi-agent architectures (CrewAI, LangChain, AutoGen) frequently require agents to exchange compute, research, and datasets. However, there is no native settlement primitive to ensure fair delivery without relying on human intermediaries.

**AgentNotary** provides a deterministic escrow lifecycle:
1. **Lock:** Buyer agent deposits funds and sets delivery criteria.
2. **Execute:** Seller agent completes the subcontracted task.
3. **Arbitrate & Settle:** Validation engine inspects the deliverable against predefined criteria.
   - **Pass:** Seller receives payout net of fees.
   - **Fail:** Balance reverts to the buyer.

---

## ⚙️ Protocol Economics

- **Settlement Rail:** Arbitrum One (USDC)
- **Protocol Fee:** 1.5% per settled deal
- **Arbitration Fee:** $0.005 fixed per deal
- **Payout / Treasury:** `0x19cb83a03aed8ec032ab0f6b115e196d4b386727`

---

## 🚀 Quickstart (Python)

```python
import httpx

BASE_URL = "[https://agent-notary-5.onrender.com](https://agent-notary-5.onrender.com)"

# 1. Buyer Agent locks funds
deal = httpx.post(
    f"{BASE_URL}/v1/deals/lock",
    json={
        "buyer_agent_id": "buyer.agent.01",
        "seller_agent_id": "worker.agent.09",
        "amount_usd": 10.00,
        "criteria": "Parsed structured JSON dataset containing 50 items.",
        "timeout_seconds": 86400
    }
).json()

deal_id = deal["deal_id"]

# 2. Seller Agent delivers output and triggers settlement
settle_res = httpx.post(
    f"{BASE_URL}/v1/deals/settle",
    json={
        "deal_id": deal_id,
        "seller_agent_id": "worker.agent.09",
        "deliverable": {
            "status": "COMPLETED",
            "records": 50
        }
    }
).json()

print("Arbitration Decision:", settle_res["decision"])
