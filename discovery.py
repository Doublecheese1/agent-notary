"""Public, read-only discovery surfaces for agents and developer tools."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse


router = APIRouter()
ORIGIN = "https://agentsolis.onrender.com"
PUBLIC_LAUNCH_DATE = "2026-10-23"


def protocol_status() -> dict[str, Any]:
    """Facts safe to publish before external funds are accepted."""
    return {
        "product": "AgentSolis",
        "description": "Deterministic settlement infrastructure for agent-to-agent jobs.",
        "public_launch_date": PUBLIC_LAUNCH_DATE,
        "production": {
            "network": "Arbitrum One",
            "asset": "native USDC",
            "chain_id": 42161,
            "enabled": False,
            "accepting_funds": False,
            "status": "launch_preparation",
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
            "a2a_read_only": True,
        },
        "links": {
            "openapi": f"{ORIGIN}/openapi.json",
            "docs": f"{ORIGIN}/docs",
            "demo": f"{ORIGIN}/play",
            "mainnet_status": f"{ORIGIN}/mainnet",
            "source": "https://github.com/Doublecheese1/agent-notary",
        },
        "warning": "Mainnet deposits are closed. The public A2A interface is read-only and never asks for a wallet key.",
    }


@router.get("/v1/protocol/status", tags=["Discovery"])
def public_protocol_status():
    return protocol_status()


@router.get("/.well-known/agent-card.json", include_in_schema=False)
def agent_card():
    return JSONResponse(
        {
            "name": "AgentSolis",
            "description": "Read-only discovery agent for deterministic agent-to-agent settlement infrastructure.",
            "version": "0.1.0",
            "documentationUrl": f"{ORIGIN}/docs",
            "supportedInterfaces": [
                {"url": f"{ORIGIN}/a2a", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"}
            ],
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
        summary = "AgentSolis public launch is planned for 23 October 2026; mainnet deposits remain closed during preparation."
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
        "> Deterministic settlement infrastructure for agent-to-agent jobs.\n\n"
        "- Public launch: 23 October 2026.\n"
        "- Production network candidate: Arbitrum One with native USDC.\n"
        "- Mainnet deposits: closed during verified deployment preparation.\n"
        "- Wallet-free demo: https://agentsolis.onrender.com/play\n"
        "- Protocol status: https://agentsolis.onrender.com/v1/protocol/status\n"
        "- A2A Agent Card: https://agentsolis.onrender.com/.well-known/agent-card.json\n"
        "- OpenAPI: https://agentsolis.onrender.com/openapi.json\n"
        "- Source: https://github.com/Doublecheese1/agent-notary\n\n"
        "AgentSolis does not request wallet private keys. Public mainnet money movement is not available yet.\n",
        headers={"Cache-Control": "public, max-age=300"},
    )
