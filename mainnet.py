"""Mainnet product routes. Read-only until explicit, verified production configuration."""
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from eth_abi import encode
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from web3 import Web3

from payments import ROOT, address, digest
from ai_review import ready_for_signing, register_manifest, require_trigger as require_ai_trigger

CHAIN = 42161
USDC = Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
ARTIFACT = json.loads((ROOT / "artifacts/AgentNotaryMainnetEscrow.json").read_text())
QUORUM_ARTIFACT = json.loads((ROOT / "artifacts/AgentNotaryValidatorQuorum.json").read_text())
AI_REVIEW_ARTIFACT = json.loads((ROOT / "artifacts/AgentNotaryAIReviewResolver.json").read_text())
router = APIRouter(prefix="/mainnet", tags=["Mainnet candidate"])
STATES = ["NONE", "PROPOSED", "LOCKED", "DELIVERED", "DISPUTED", "PAID", "REFUNDED", "FINALIZED_SPLIT"]


def mainnet_units(value: str) -> int:
    """Convert an uncapped USDC amount while enforcing token precision and uint256 size."""
    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(422, "Enter a valid USDC amount.") from exc
    if not decimal_value.is_finite() or decimal_value <= 0:
        raise HTTPException(422, "Budget must be greater than zero.")
    scaled = decimal_value * 1_000_000
    if scaled != scaled.to_integral_value() or scaled >= 2**256:
        raise HTTPException(422, "Use no more than 6 decimal places and a valid USDC amount.")
    return int(scaled)


def transaction(sender, target, data):
    """Build an unsigned Arbitrum One transaction; never reuse the testnet helper."""
    return {"from": sender, "to": target, "data": data, "value": "0x0", "chainId": hex(CHAIN)}


def enabled() -> bool:
    return os.getenv("MAINNET_ENABLED", "false").lower() == "true"


def accepting() -> bool:
    return os.getenv("MAINNET_ACCEPTING_FUNDS", "false").lower() == "true"


def deployment_ui_enabled() -> bool:
    return os.getenv("MAINNET_DEPLOYMENT_UI", "false").lower() == "true"


def operations_ui_enabled() -> bool:
    return os.getenv("MAINNET_OPERATIONS_UI", "false").lower() == "true"


def expected_deployer() -> str:
    raw = os.getenv("MAINNET_DEPLOYER_ADDRESS", "")
    if not raw:
        raise HTTPException(503, "Configure the approved Arbitrum One deployer address.")
    try:
        return address(raw)
    except Exception as exc:
        raise HTTPException(503, "The configured deployer address is invalid.") from exc


def require_expected_deployer(raw: str) -> str:
    deployer = address(raw)
    if deployer != expected_deployer():
        raise HTTPException(403, "Connect the approved Arbitrum One deployer wallet.")
    return deployer


def connection():
    if not enabled():
        raise HTTPException(503, "Mainnet contract is not configured.")
    rpc = os.getenv("MAINNET_RPC_URL", "")
    if not rpc.startswith("https://"):
        raise HTTPException(503, "Configure an HTTPS Arbitrum One RPC.")
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
        if w3.eth.chain_id != CHAIN:
            raise ValueError("wrong chain")
        contract = w3.eth.contract(address=address(os.getenv("MAINNET_ESCROW_ADDRESS", "")), abi=ARTIFACT["abi"])
        if not w3.eth.get_code(contract.address):
            raise ValueError("missing deployment")
        if Web3.to_checksum_address(contract.functions.token().call()) != USDC:
            raise ValueError("wrong token")
        expected_treasury = address(os.getenv("MAINNET_TREASURY_SAFE", ""))
        expected_operations = address(os.getenv("MAINNET_OPERATIONS_SAFE", ""))
        if contract.functions.treasurySafe().call() != expected_treasury:
            raise ValueError("treasury mismatch")
        if contract.functions.operationsSafe().call() != expected_operations:
            raise ValueError("operations mismatch")
        if contract.functions.PROTOCOL_FEE_BPS().call() != 150:
            raise ValueError("fee mismatch")
        if contract.functions.MAX_PROTOCOL_FEE().call() != 50_000_000:
            raise ValueError("fee cap mismatch")
        if contract.functions.MIN_AUTOMATIC_AMOUNT().call() != 10_000_000:
            raise ValueError("automatic minimum mismatch")
        if contract.functions.MIN_REVIEW_AMOUNT().call() != 100_000_000:
            raise ValueError("review minimum mismatch")
        return w3, contract
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Mainnet RPC or contract configuration could not be verified.") from exc


def require_accepting():
    if not accepting():
        raise HTTPException(503, "Mainnet deposits are not open yet.")


@router.get("", include_in_schema=False)
def page():
    return FileResponse(ROOT / "static/mainnet.html", headers={"Cache-Control": "no-store"})


@router.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(ROOT / "static/mainnet.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@router.get("/deal/{deal_id}", include_in_schema=False)
def deal_page(deal_id: str):
    digest(deal_id)
    return FileResponse(ROOT / "static/mainnet.html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/setup", include_in_schema=False)
def setup_page():
    if not deployment_ui_enabled():
        raise HTTPException(404, "Not found")
    return FileResponse(ROOT / "static/mainnet-setup.html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/setup.js", include_in_schema=False)
def setup_script():
    if not deployment_ui_enabled():
        raise HTTPException(404, "Not found")
    return FileResponse(ROOT / "static/mainnet-setup.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@router.get("/validator", include_in_schema=False)
def validator_page():
    return FileResponse(ROOT / "static/mainnet-validator.html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/validator.js", include_in_schema=False)
def validator_script():
    return FileResponse(ROOT / "static/mainnet-validator.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@router.get("/operations", include_in_schema=False)
def operations_page():
    return FileResponse(ROOT / "static/mainnet-operations.html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/operations.js", include_in_schema=False)
def operations_script():
    return FileResponse(ROOT / "static/mainnet-operations.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@router.get("/operations-status")
def operations_status():
    return {"enabled": operations_ui_enabled(), "chain_id": CHAIN, "network": "Arbitrum One"}


class OperationsRequest(BaseModel):
    action: str
    buyer: str = ""
    allowed: bool = False


@router.post("/prepare-operations-action")
def prepare_operations_action(req: OperationsRequest):
    if not operations_ui_enabled():
        raise HTTPException(503, "The founder operations screen is closed.")
    _, contract = connection()
    if req.action in {"admitFoundingBuyer", "cancelUnactivatedFoundingBuyer"}:
        fn = getattr(contract.functions, req.action)(address(req.buyer))
    elif req.action == "setBuyerAccess":
        fn = contract.functions.setBuyerAccess(address(req.buyer), req.allowed)
    elif req.action in {"pauseNewDeals", "resumeNewDeals"}:
        fn = getattr(contract.functions, req.action)()
    else:
        raise HTTPException(422, "Unsupported or unsafe operations action.")
    safe = contract.functions.operationsSafe().call()
    return {"transaction": simulated(contract, safe, fn), "safe": safe, "action": req.action}


@router.get("/setup-status")
def setup_status():
    configured = bool(os.getenv("MAINNET_DEPLOYER_ADDRESS", ""))
    deployer = expected_deployer() if configured else None
    return {"enabled": deployment_ui_enabled() and configured, "chain_id": CHAIN,
            "network": "Arbitrum One", "token": USDC, "deployer": deployer}


class QuorumDeployment(BaseModel):
    deployer: str
    signer_a: str
    signer_b: str
    signer_c: str


class EscrowDeployment(BaseModel):
    deployer: str
    treasury_safe: str
    operations_safe: str
    automatic_validator: str
    review_arbitrator: str


class AIReviewResolverDeployment(BaseModel):
    deployer: str
    operations_safe: str
    human_review_safe: str
    fee_recipient: str
    signer_a: str
    signer_b: str
    signer_c: str
    automatic_amount_cap_units: int = Field(default=250_000_000, gt=0)
    appeal_window_seconds: int = Field(default=86400, ge=3600, le=604800)
    minimum_confidence_bps: int = Field(default=8500, ge=5001, le=10000)


def require_deployment_ui():
    if not deployment_ui_enabled():
        raise HTTPException(503, "The founder deployment screen is closed.")


@router.post("/prepare-quorum-deployment")
def prepare_quorum_deployment(req: QuorumDeployment):
    require_deployment_ui()
    deployer = require_expected_deployer(req.deployer)
    signers = [address(req.signer_a), address(req.signer_b), address(req.signer_c)]
    if len({x.lower() for x in signers}) != 3:
        raise HTTPException(422, "Use three distinct validator signer addresses.")
    contract = Web3().eth.contract(abi=QUORUM_ARTIFACT["abi"], bytecode=QUORUM_ARTIFACT["bytecode"])
    return {"transaction": {"from": deployer, "data": contract.constructor(*signers).data_in_transaction,
                            "value": "0x0", "chainId": hex(CHAIN)}, "constructor": {"signers": signers}}


@router.post("/prepare-escrow-deployment")
def prepare_escrow_deployment(req: EscrowDeployment):
    require_deployment_ui()
    deployer = require_expected_deployer(req.deployer)
    treasury, operations = address(req.treasury_safe), address(req.operations_safe)
    validator, arbitrator = address(req.automatic_validator), address(req.review_arbitrator)
    roles = [treasury, operations, validator, arbitrator]
    if len({x.lower() for x in roles}) != 4:
        raise HTTPException(422, "Treasury, operations, validator and arbitrator must use distinct addresses.")
    contract = Web3().eth.contract(abi=ARTIFACT["abi"], bytecode=ARTIFACT["bytecode"])
    data = contract.constructor(USDC, treasury, operations, validator, arbitrator).data_in_transaction
    return {"transaction": {"from": deployer, "data": data, "value": "0x0", "chainId": hex(CHAIN)},
            "constructor": {"token": USDC, "treasury_safe": treasury, "operations_safe": operations,
                            "automatic_validator": validator, "review_arbitrator": arbitrator}}


@router.post("/prepare-ai-review-resolver-deployment")
def prepare_ai_review_resolver_deployment(req: AIReviewResolverDeployment):
    require_deployment_ui()
    deployer = require_expected_deployer(req.deployer)
    operations, human, recipient = address(req.operations_safe), address(req.human_review_safe), address(req.fee_recipient)
    signers = [address(req.signer_a), address(req.signer_b), address(req.signer_c)]
    if operations == human:
        raise HTTPException(422, "Operations and human review must use separate Safes.")
    if len({item.lower() for item in signers}) != 3:
        raise HTTPException(422, "Use three distinct AI review signer addresses.")
    contract = Web3().eth.contract(abi=AI_REVIEW_ARTIFACT["abi"], bytecode=AI_REVIEW_ARTIFACT["bytecode"])
    data = contract.constructor(
        operations, human, recipient, *signers, req.automatic_amount_cap_units,
        req.appeal_window_seconds, req.minimum_confidence_bps,
    ).data_in_transaction
    return {"transaction": {"from": deployer, "data": data, "value": "0x0", "chainId": hex(CHAIN)},
            "constructor": {"operations_safe": operations, "human_review_safe": human,
                            "fee_recipient": recipient, "signers": signers,
                            "automatic_amount_cap_units": req.automatic_amount_cap_units,
                            "appeal_window_seconds": req.appeal_window_seconds,
                            "minimum_confidence_bps": req.minimum_confidence_bps}}


class BindReviewResolver(BaseModel):
    resolver: str
    escrow: str


@router.post("/prepare-bind-review-resolver")
def prepare_bind_review_resolver(req: BindReviewResolver):
    if not operations_ui_enabled():
        raise HTTPException(503, "The founder operations screen is closed.")
    resolver = Web3().eth.contract(address=address(req.resolver), abi=AI_REVIEW_ARTIFACT["abi"])
    operations = resolver.functions.operationsSafe().call()
    fn = resolver.functions.bindEscrow(address(req.escrow))
    return {"transaction": transaction(operations, resolver.address, fn._encode_transaction_data()),
            "safe": operations, "action": "Bind the review resolver exactly once"}


class HumanReviewResolution(BaseModel):
    deal_id: str
    decision: str


@router.post("/prepare-human-review-resolution")
def prepare_human_review_resolution(req: HumanReviewResolution):
    if not operations_ui_enabled():
        raise HTTPException(503, "The founder operations screen is closed.")
    _, escrow_contract = connection()
    resolver_address = escrow_contract.functions.reviewArbitrator().call()
    resolver = Web3().eth.contract(address=resolver_address, abi=AI_REVIEW_ARTIFACT["abi"])
    decisions = {"SELLER_WINS": 0, "BUYER_WINS": 1}
    decision = decisions.get(req.decision.upper())
    if decision is None:
        raise HTTPException(422, "Decision must be SELLER_WINS or BUYER_WINS.")
    safe = resolver.functions.humanReviewSafe().call()
    fn = resolver.functions.humanResolve(digest(req.deal_id), decision)
    return {"transaction": transaction(safe, resolver.address, fn._encode_transaction_data()),
            "safe": safe, "action": req.decision.upper(), "deal_id": req.deal_id}


@router.get("/config")
def config(wallet: str | None = None):
    base = {
        "enabled": False, "accepting_funds": False, "chain_id": CHAIN, "network": "Arbitrum One",
        "token": USDC, "token_symbol": "USDC", "protocol_fee_bps": 150,
        "protocol_fee_cap_units": 50_000_000, "automatic_minimum_units": 10_000_000,
        "review_minimum_units": 100_000_000, "founding_period_days": 30,
        "automatic_policy_hash": os.getenv("MAINNET_AUTOMATIC_POLICY_HASH", ""),
        "review_policy_hash": os.getenv("MAINNET_REVIEW_POLICY_HASH", ""),
    }
    if not enabled():
        return base
    w3, contract = connection()
    block = w3.eth.block_number
    who = address(wallet) if wallet else None
    return {
        **base, "enabled": True, "accepting_funds": accepting(), "escrow": contract.address,
        "treasury_safe": contract.functions.treasurySafe().call(block_identifier=block),
        "operations_safe": contract.functions.operationsSafe().call(block_identifier=block),
        "validator_quorum": contract.functions.automaticValidator().call(block_identifier=block),
        "review_arbitrator": contract.functions.reviewArbitrator().call(block_identifier=block),
        "public_access": contract.functions.publicAccess().call(block_identifier=block),
        "paused": contract.functions.paused().call(block_identifier=block),
        "approved_buyer": contract.functions.approvedBuyers(who).call(block_identifier=block) if who else None,
        "founding_state": contract.functions.foundingSeats(who).call(block_identifier=block) if who else None,
        "fee_waiver_until": contract.functions.feeWaiverUntil(who).call(block_identifier=block) if who else None,
        "observed_block": block,
    }


class Proposal(BaseModel):
    buyer: str
    seller: str
    mode: str = Field(pattern="^(automatic|buyer_review)$")
    amount: str
    salt: str
    manifest: str = Field(min_length=1, max_length=20000)
    policy_hash: str
    fallback_seller_bps: int = Field(ge=0, le=10000)
    acceptance_window: int = Field(ge=600, le=2592000)
    delivery_window: int = Field(ge=600, le=2592000)
    decision_window: int = Field(ge=600, le=2592000)
    arbitration_window: int = Field(ge=600, le=2592000)


def simulated(contract, caller, fn):
    try:
        fn.call({"from": caller})
    except Exception as exc:
        raise HTTPException(409, "The transaction is not currently valid. Check access, balance, allowance, role, state and deadline.") from exc
    return transaction(caller, contract.address, fn._encode_transaction_data())


@router.post("/prepare-proposal")
def prepare_proposal(req: Proposal):
    require_accepting()
    w3, contract = connection()
    buyer, seller = address(req.buyer), address(req.seller)
    if buyer == seller:
        raise HTTPException(422, "Buyer and seller must be different wallets.")
    mode = 0 if req.mode == "automatic" else 1
    amount = mainnet_units(req.amount)
    if req.mode == "buyer_review" and req.decision_window < 2 * 24 * 60 * 60:
        raise HTTPException(422, "Buyer Review requires at least 2 days for the buyer decision window.")
    if req.mode == "buyer_review" and req.arbitration_window < 7 * 24 * 60 * 60:
        raise HTTPException(422, "Buyer Review requires at least 7 days for AI review, appeal and human review.")
    reserve = 0 if mode == 0 else contract.functions.arbitrationReserveFor(amount).call()
    protocol_fee = contract.functions.protocolFeeFor(buyer, amount).call()
    manifest_hash, policy_hash, salt = Web3.keccak(text=req.manifest), digest(req.policy_hash), digest(req.salt)
    register_manifest(Web3.to_hex(manifest_hash), req.manifest)
    request = (
        salt, seller, mode, amount, reserve, req.fallback_seller_bps, manifest_hash, policy_hash,
        req.acceptance_window, req.delivery_window, req.decision_window, req.arbitration_window,
    )
    fn = contract.functions.proposeDeal(request)
    total = amount + reserve
    approval_data = Web3.keccak(text="approve(address,uint256)")[:4] + encode(["address", "uint256"], [contract.address, total])
    deal_id = Web3.keccak(encode(
        ["address", "uint256", "address", "address", "bytes32"],
        [contract.address, CHAIN, buyer, seller, salt],
    ))
    return {
        "deal_id": Web3.to_hex(deal_id), "manifest_hash": Web3.to_hex(manifest_hash),
        "policy_hash": Web3.to_hex(policy_hash), "amount_units": amount,
        "buyer_reserve_units": reserve, "buyer_total_units": total,
        "seller_bond_units": reserve, "protocol_fee_units": protocol_fee,
        "seller_net_units": amount - protocol_fee,
        "approval": transaction(buyer, USDC, Web3.to_hex(approval_data)),
        # The proposal cannot be simulated until the approval transaction is confirmed.
        # The browser performs a fresh eth_call immediately before it asks the wallet to send.
        "proposal": transaction(buyer, contract.address, fn._encode_transaction_data()),
        "notice": "The wallet signs and pays gas. AgentSolis does not hold the wallet key.",
    }


@router.get("/deals/{deal_id}")
def read_deal(deal_id: str):
    w3, contract = connection()
    key = digest(deal_id)
    values = contract.functions.deals(key).call()
    if values[4] == 0:
        raise HTTPException(404, "Deal not found.")
    names = [
        "buyer", "seller", "resolver", "mode_index", "state_index", "amount_units",
        "arbitration_reserve_units", "seller_bond_units", "protocol_fee_units", "fallback_seller_bps",
        "manifest_hash", "policy_hash", "content_hash", "acceptance_deadline", "delivery_window",
        "decision_window", "arbitration_window", "delivery_deadline", "decision_deadline",
        "arbitration_deadline", "validation_nonce",
    ]
    result = dict(zip(names, values))
    for name in ("manifest_hash", "policy_hash", "content_hash"):
        result[name] = Web3.to_hex(result[name])
    block = w3.eth.block_number
    return {**result, "deal_id": deal_id, "mode": ["AUTOMATIC", "BUYER_REVIEW"][values[3]],
            "state": STATES[values[4]], "observed_block": block,
            "chain_time": w3.eth.get_block(block)["timestamp"]}


class Action(BaseModel):
    caller: str
    action: str
    content_hash: str = ""
    uri: str = Field(default="", max_length=512)
    reason_hash: str = ""
    evidence_uri: str = Field(default="", max_length=512)
    decision: int = Field(default=0, ge=0, le=1)
    validation_decision: int = Field(default=0, ge=0, le=2)
    validation_evidence_hash: str = ""
    signature_deadline: int = Field(default=0, ge=0)
    validator_signatures: list[str] = Field(default_factory=list, min_length=0, max_length=3)


@router.post("/deals/{deal_id}/prepare-action")
def prepare_action(deal_id: str, req: Action):
    # Closing new deposits must never disable delivery, settlement or refunds for
    # deals that already hold funds. connection() still requires a verified deployment.
    _, contract = connection()
    key, caller = digest(deal_id), address(req.caller)
    no_args = {
        "sellerAccept", "cancelProposal", "expireProposal", "expireUndelivered", "acceptDelivery",
        "finalizeIfSilent", "finalizeUnresolvedAutomatic", "finalizeUnresolvedReview",
    }
    if req.action in no_args:
        fn = getattr(contract.functions, req.action)(key)
    elif req.action == "deliver":
        if not req.uri.startswith(("ipfs://", "ar://", "https://")):
            raise HTTPException(422, "Use an IPFS, Arweave or HTTPS delivery URI.")
        fn = contract.functions.deliver(key, digest(req.content_hash), req.uri)
    elif req.action == "disputeDelivery":
        if not req.evidence_uri.startswith(("ipfs://", "ar://", "https://")):
            raise HTTPException(422, "Use an IPFS, Arweave or HTTPS evidence URI.")
        fn = contract.functions.disputeDelivery(key, digest(req.reason_hash), req.evidence_uri)
    elif req.action == "submitValidation":
        if len(req.validator_signatures) < 2:
            raise HTTPException(422, "Two validator signatures are required.")
        signatures = []
        for signature in req.validator_signatures:
            if not isinstance(signature, str) or not signature.startswith("0x"):
                raise HTTPException(422, "Each validator signature must be hexadecimal.")
            try:
                raw = bytes.fromhex(signature[2:])
            except ValueError as exc:
                raise HTTPException(422, "Each validator signature must be hexadecimal.") from exc
            if len(raw) != 65:
                raise HTTPException(422, "Each validator signature must contain 65 bytes.")
            signatures.append(raw)
        quorum_signature = encode(["bytes[]"], [signatures])
        fn = contract.functions.submitValidation(
            key, req.validation_decision, digest(req.validation_evidence_hash),
            req.signature_deadline, quorum_signature,
        )
    elif req.action == "approveSellerBond":
        deal = contract.functions.deals(key).call()
        data = Web3.keccak(text="approve(address,uint256)")[:4] + encode(["address", "uint256"], [contract.address, deal[6]])
        return {"transaction": transaction(caller, USDC, Web3.to_hex(data)), "amount_units": deal[6]}
    else:
        raise HTTPException(422, "Unsupported action.")
    return {"transaction": simulated(contract, caller, fn)}


def _review_resolver(contract):
    resolver = Web3().eth.contract(address=contract.functions.reviewArbitrator().call(), abi=AI_REVIEW_ARTIFACT["abi"])
    try:
        if not resolver.functions.isAgentNotaryReviewResolver().call():
            raise ValueError("marker missing")
    except Exception as exc:
        raise HTTPException(503, "The configured review resolver is not supported.") from exc
    return resolver


@router.get("/deals/{deal_id}/review-status")
def review_status(deal_id: str):
    _, contract = connection()
    key = digest(deal_id)
    resolver = _review_resolver(contract)
    ruling = resolver.functions.pendingRulings(key).call()
    return {
        "resolver": resolver.address,
        "human_review_safe": resolver.functions.humanReviewSafe().call(),
        "automatic_amount_cap_units": resolver.functions.automaticAmountCap().call(),
        "minimum_confidence_bps": resolver.functions.minimumConfidenceBps().call(),
        "pending": bool(ruling[6]),
        "decision": ["SELLER_WINS", "BUYER_WINS"][ruling[0]] if ruling[6] else None,
        "package_hash": Web3.to_hex(ruling[1]), "report_hash": Web3.to_hex(ruling[2]),
        "confidence_bps": ruling[3], "appeal_deadline": ruling[4], "appealed": bool(ruling[5]),
    }


class ReviewAction(BaseModel):
    caller: str
    action: str = Field(pattern="^(appeal|finalize)$")


@router.post("/deals/{deal_id}/prepare-review-action")
def prepare_review_action(deal_id: str, req: ReviewAction):
    _, contract = connection()
    key, caller = digest(deal_id), address(req.caller)
    resolver = _review_resolver(contract)
    fn = resolver.functions.appeal(key) if req.action == "appeal" else resolver.functions.finalizeAIResolution(key)
    return {"transaction": simulated(resolver, caller, fn), "action": req.action}


class AIReviewSigningRequest(BaseModel):
    case_id: str
    signature_deadline: int = Field(gt=0)


def _ai_signing_payload(case: dict, resolver, nonce: int, signature_deadline: int):
    decision = {"SELLER_WINS": 0, "BUYER_WINS": 1}[case["decision"]]
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"},
            ],
            "AIReview": [
                {"name": "dealId", "type": "bytes32"}, {"name": "decision", "type": "uint8"},
                {"name": "packageHash", "type": "bytes32"}, {"name": "reportHash", "type": "bytes32"},
                {"name": "confidenceBps", "type": "uint16"}, {"name": "flags", "type": "uint32"},
                {"name": "nonce", "type": "uint256"}, {"name": "signatureDeadline", "type": "uint256"},
            ],
        },
        "primaryType": "AIReview",
        "domain": {"name": "AgentNotaryAIReviewResolver", "version": "1", "chainId": CHAIN,
                   "verifyingContract": resolver.address},
        "message": {"dealId": case["deal_id"], "decision": decision, "packageHash": case["package_hash"],
                    "reportHash": case["report_hash"], "confidenceBps": case["confidence_bps"],
                    "flags": 0, "nonce": nonce, "signatureDeadline": signature_deadline},
    }


@router.post("/ai-review/signing-payload")
def ai_review_signing_payload(req: AIReviewSigningRequest, authorization: str | None = Header(default=None)):
    require_ai_trigger(authorization)
    w3, contract = connection()
    case = ready_for_signing(req.case_id)
    if req.signature_deadline <= w3.eth.get_block("latest")["timestamp"]:
        raise HTTPException(422, "Signature deadline must be in the future.")
    resolver = _review_resolver(contract)
    nonce = resolver.functions.nonces(digest(case["deal_id"])).call()
    return _ai_signing_payload(case, resolver, nonce, req.signature_deadline)


class AIReviewRelayRequest(AIReviewSigningRequest):
    relayer: str
    signatures: list[str] = Field(min_length=2, max_length=3)


@router.post("/ai-review/prepare-relay")
def prepare_ai_review_relay(req: AIReviewRelayRequest, authorization: str | None = Header(default=None)):
    require_ai_trigger(authorization)
    _, contract = connection()
    case = ready_for_signing(req.case_id)
    resolver = _review_resolver(contract)
    key = digest(case["deal_id"])
    nonce = resolver.functions.nonces(key).call()
    decision = {"SELLER_WINS": 0, "BUYER_WINS": 1}[case["decision"]]
    signatures = []
    for value in req.signatures:
        if not isinstance(value, str) or not value.startswith("0x"):
            raise HTTPException(422, "AI review signatures must be hexadecimal.")
        try:
            raw = bytes.fromhex(value[2:])
        except ValueError as exc:
            raise HTTPException(422, "AI review signatures must be hexadecimal.") from exc
        if len(raw) != 65:
            raise HTTPException(422, "Each AI review signature must contain 65 bytes.")
        signatures.append(raw)
    fn = resolver.functions.proposeAIResolution(
        key, decision, digest(case["package_hash"]), digest(case["report_hash"]),
        case["confidence_bps"], 0, nonce, req.signature_deadline, signatures,
    )
    caller = address(req.relayer)
    return {"transaction": simulated(resolver, caller, fn), "case_id": req.case_id,
            "deal_id": case["deal_id"], "decision": case["decision"]}
