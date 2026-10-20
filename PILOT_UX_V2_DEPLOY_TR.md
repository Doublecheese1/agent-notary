# Pilot UX V2 deployment

## Changed files

Upload these files to the repository without changing the existing contract or environment variables:

- pilot.py
- static/pilot.html
- static/pilot.js
- static/pilot-admin.html
- static/pilot-admin.js
- test_pilot.py
- test_pilot_frontend.cjs

## Deploy

1. Commit the files to the GitHub repository main branch.
2. Render should start a new deployment automatically.
3. Wait for the deployment status to become Live.
4. Open /pilot in a private tab and confirm the three start choices.
5. Open /pilot/admin directly and confirm founder tools are present only there.
6. Existing Render environment variables and the deployed escrow address remain unchanged.

## Safety retained

- Arbitrum Sepolia network guard
- Exact USDC approval amount
- Preflight simulation before MetaMask
- Account/network change invalidation
- Pending transaction duplicate-send guard
- Four-times gas fee envelope used by the working pilot
