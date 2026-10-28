"""Public, read-only discovery surfaces for agents and developer tools."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse


router = APIRouter()
ORIGIN = "https://agentsolis.solists.com.tr"
PUBLIC_LAUNCH_DATE = "2026-10-23"


def protocol_status() -> dict[str, Any]:
    """Publish the same live mainnet gate used by the transaction workspace."""
    try:
        # Keep discovery, A2A and llms.txt aligned with the transaction UI.
        from mainnet import config as mainnet_config

        live = mainnet_config()
    except Exception:
        live = {}
    enabled = bool(live.get("enabled"))
    accepting_funds = bool(live.get("accepting_funds"))
    public_access = bool(live.get("public_access"))
    paused = bool(live.get("paused"))
    if accepting_funds:
        status = "public_mainnet_funding_open"
        warning = "Public mainnet funding is open. Verify the live network, token, amount, parties and contract address before signing."
    elif public_access and not paused:
        status = "public_access_open_funding_closed"
        warning = "Public mainnet access is open, but the live funding gate is currently closed. Do not sign a funding transaction until accepting_funds is true."
    else:
        status = "status_unavailable_or_closed"
        warning = "The live mainnet funding status is unavailable or closed. Do not fund until the workspace reports accepting_funds=true."
    return {
        "product": "AgentSolis",
        "description": "Evidence-based escrow and settlement infrastructure for online work involving people and AI agents.",
        "public_launch_date": PUBLIC_LAUNCH_DATE,
        "production": {
            "network": "Arbitrum One",
            "asset": "native USDC",
            "chain_id": 42161,
            "enabled": enabled,
            "accepting_funds": accepting_funds,
            "public_access": public_access,
            "paused": paused,
            "status": status,
        },
        "sandbox": {
            "enabled": True,
            "real_money": False,
            "retention_seconds": 900,
            "url": f"{ORIGIN}/play",
            "api": f"{ORIGIN}/sandbox",
        },
        "capabilities": {
            "safe_retry_guards": True,
            "operation_id_guard": True,
            "policy_bound_eip712_decisions": True,
            "public_money_movement_tools": False,
            "x402_payments": False,
            "mcp_server": False,
        },
        "links": {
            "demo": f"{ORIGIN}/play",
            "mainnet_status": f"{ORIGIN}/mainnet",
        },
        "warning": warning,
    }


@router.get("/v1/protocol/status", tags=["Discovery"])
def public_protocol_status():
    return protocol_status()


@router.get("/.well-known/agent-card.json", include_in_schema=False)
def agent_card():
    return JSONResponse(
        {
            "name": "AgentSolis",
            "description": "Read-only discovery surface for evidence-based escrow and settlement involving people and AI agents.",
            "version": "0.1.0",
            "documentationUrl": f"{ORIGIN}/v1/protocol/status",
            "supportedInterfaces": [],
            "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
            "defaultInputModes": ["text/plain", "application/json"],
            "defaultOutputModes": ["text/plain", "application/json"],
            "skills": [
                {
                    "id": "protocol_status",
                    "name": "AgentSolis protocol status",
                    "description": "Returns supported networks, assets, safety gates and public integration URLs.",
                    "tags": ["escrow", "settlement", "status", "a2a"],
                    "examples": ["Show AgentSolis protocol status", "Is AgentSolis accepting mainnet funds?"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["application/json"],
                },
                {
                    "id": "sandbox_demo",
                    "name": "Wallet-free sandbox information",
                    "description": "Returns the no-wallet, no-real-money demo URL and its safety limits.",
                    "tags": ["sandbox", "demo", "safe-retry"],
                    "examples": ["How can an agent try AgentSolis without a wallet?"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["application/json"],
                },
            ],
        },
        headers={"Cache-Control": "public, max-age=300"},
    )


def _message_text(body: dict[str, Any]) -> str:
    message = body.get("message")
    if not isinstance(message, dict):
        raise HTTPException(422, "message is required")
    parts = message.get("parts")
    if not isinstance(parts, list) or not parts:
        raise HTTPException(422, "message.parts must contain text")
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    text = " ".join(value for value in texts if isinstance(value, str)).strip()
    if not text:
        raise HTTPException(422, "a text part is required")
    if len(text) > 4000:
        raise HTTPException(422, "message text is too long")
    return text


@router.post("/a2a/message:send", tags=["Discovery"])
def a2a_send_message(body: dict[str, Any], a2a_version: str = Header(default="1.0", alias="A2A-Version")):
    if a2a_version != "1.0":
        return JSONResponse(
            {
                "type": "https://a2a-protocol.org/errors/version-not-supported",
                "title": "Protocol Version Not Supported",
                "status": 400,
                "detail": "AgentSolis currently supports A2A protocol version 1.0.",
                "supportedVersions": ["1.0"],
            },
            status_code=400,
            media_type="application/problem+json",
        )
    text = _message_text(body)
    lowered = text.casefold()
    status = protocol_status()
    if any(word in lowered for word in ("demo", "sandbox", "wallet")):
        payload = {"skill": "sandbox_demo", **status["sandbox"], "warning": status["warning"]}
        summary = "The wallet-free sandbox is available and never moves real money."
    else:
        payload = {"skill": "protocol_status", **status}
        summary = ("AgentSolis public mainnet funding is open according to the live status."
                   if status["production"]["accepting_funds"]
                   else "AgentSolis public access is available, but live funding is not currently enabled.")
    task_id = str(uuid.uuid4())
    context_id = body.get("message", {}).get("contextId") or str(uuid.uuid4())
    return JSONResponse(
        {
            "task": {
                "id": task_id,
                "contextId": context_id,
                "status": {"state": "TASK_STATE_COMPLETED"},
                "artifacts": [
                    {
                        "artifactId": str(uuid.uuid4()),
                        "name": payload["skill"],
                        "parts": [{"text": summary}, {"data": payload}],
                    }
                ],
            }
        },
        media_type="application/a2a+json",
        headers={"A2A-Version": "1.0", "Cache-Control": "no-store"},
    )


@router.get("/llms.txt", include_in_schema=False)
def llms_txt():
    return PlainTextResponse(
        "# AgentSolis\n\n"
        "> Evidence-based escrow and settlement for online work involving people and AI agents.\n\n"
        "- Public launch: 23 October 2026.\n"
        "- Production network candidate: Arbitrum One with native USDC.\n"
        f"- Public mainnet funding: {'open' if protocol_status()['production']['accepting_funds'] else 'not currently enabled according to the live gate'}.\n"
        "- Wallet-free demo: https://agentsolis.solists.com.tr/play\n"
        "- Protocol status: https://agentsolis.solists.com.tr/v1/protocol/status\n"
        "- Discovery card: https://agentsolis.solists.com.tr/.well-known/agent-card.json\n"
        "- OpenAPI, full docs, MCP and a callable A2A integration are not published yet.\n"
        "\n"
        "AgentSolis does not request wallet private keys. Always verify the live status before signing.\n",
        headers={"Cache-Control": "public, max-age=300"},
    )
