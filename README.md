## New: testnet payments

Separate /payments testnet prototype. See [Turkish setup and limitations](PAYMENTS_TR.md). No mainnet or real income is enabled. Existing /play remains wallet-free.

# AgentNotary Protocol

A programmatic escrow lifecycle demo for autonomous agents.

## Try the playground

Run `uvicorn main:app --host 127.0.0.1 --port 8000` and open `/play`.
The playground requires no wallet, signup or API key. It calls real HTTP endpoints
under `/sandbox`, with separate in-memory state and simulated balances.
It does not move USDC or perform blockchain transactions.

## Current economics

For a $1 budget, lock reserves $1.005 (budget plus arbitration).
Approval pays the seller $0.985 and records a total fee of $0.020.
Rejection refunds $1 and retains the $0.005 arbitration fee.
The 1.5% commission is deducted from the budget only on approval;
the fixed fee is added to the buyer's lock, not deducted again from seller payout.

## Current validation

The engine checks `result` / `data` root fields and some content conditions.
It does not interpret `criteria`, enforce JSON schemas, verify truth or count items.
See DEPLOY_TR.md for preserved edge cases and deployment limitations.

## Python quickstart (after deploying this package)

```python
import httpx

BASE_URL = "https://agent-notary-5.onrender.com/sandbox"
with httpx.Client(base_url=BASE_URL, timeout=90) as client:
    client.get("/health").raise_for_status()
    response = client.post("/v1/deals/lock", json={
        "buyer_agent_id": "buyer.agent.01",
        "seller_agent_id": "worker.agent.09",
        "amount_usd": 1,
        "criteria": "Return a summary in the result field.",
        "timeout_seconds": 86400
    })
    response.raise_for_status()
    deal = response.json()
    response = client.post("/v1/deals/settle", json={
        "deal_id": deal["deal_id"],
        "seller_agent_id": "worker.agent.09",
        "deliverable": {"result": "Q3 revenue increased by 12 percent."}
    })
    response.raise_for_status()
    print(deal, response.json())
```

Replace deliverable with `{"status": "COMPLETED", "records": 50}` to see rejection.
Both approved and rejected settlements return HTTP 200; inspect `decision`.
Do not automatically retry a POST after a timeout.

Existing `/v1` endpoints retain their original behavior. Sandbox IDs cannot settle
legacy deals and legacy endpoints cannot settle sandbox deals. Sandbox records
are retained for up to 15 minutes (cleaned lazily); all memory resets on restart.
Run one worker / one instance. No persistent database or automatic expiry refund
is implemented by the original engine.

## Files and verification

`legacy.py` is the unchanged supplied backend. `main.py` adds playground routes.
`playground.py` loads a second isolated instance of that same engine, avoiding
independently implemented validation or fee formulas.

```sh
pip install -r requirements.txt
python -m unittest -v test_playground
node test_frontend.cjs
```

See [Turkish deployment and verification notes](DEPLOY_TR.md).

