// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

interface IAgentNotaryReviewEscrow {
    function reviewArbitrator() external view returns (address);
    function resolveReview(bytes32 id, uint8 decision) external;
    function reviewResolutionContext(bytes32 id) external view returns (
        address buyer,
        address seller,
        address resolver,
        uint8 state,
        uint256 amount,
        uint256 arbitrationDeadline
    );
}

/// @notice Hybrid review resolver: two independent AI signer services may stage
/// a high-confidence ruling. Either party can appeal before it becomes final;
/// ambiguous, appealed or high-value cases are decided by the human review Safe.
contract AgentNotaryAIReviewResolver is EIP712, ReentrancyGuard {
    using SafeERC20 for IERC20;

    uint8 private constant DISPUTED_STATE = 4;
    uint16 public constant BPS_DENOMINATOR = 10_000;
    uint256 public constant HUMAN_REVIEW_RESERVE = 3 days;
    bytes32 public constant REVIEW_TYPEHASH = keccak256(
        "AIReview(bytes32 dealId,uint8 decision,bytes32 packageHash,bytes32 reportHash,uint16 confidenceBps,uint32 flags,uint256 nonce,uint256 signatureDeadline)"
    );

    struct PendingRuling {
        uint8 decision;
        bytes32 packageHash;
        bytes32 reportHash;
        uint16 confidenceBps;
        uint256 appealDeadline;
        bool appealed;
        bool exists;
    }

    address public immutable operationsSafe;
    address public immutable humanReviewSafe;
    address public immutable feeRecipient;
    uint256 public immutable automaticAmountCap;
    uint256 public immutable appealWindow;
    uint16 public immutable minimumConfidenceBps;
    address[3] public signers;
    mapping(address => bool) public isSigner;
    mapping(bytes32 => uint256) public nonces;
    mapping(bytes32 => PendingRuling) public pendingRulings;
    address public escrow;

    event EscrowBound(address indexed escrow);
    event AIRulingProposed(bytes32 indexed dealId, uint8 decision, bytes32 indexed packageHash, bytes32 reportHash, uint16 confidenceBps, uint256 appealDeadline);
    event AIRulingAppealed(bytes32 indexed dealId, address indexed party);
    event AIRulingFinalized(bytes32 indexed dealId, uint8 decision);
    event HumanRulingFinalized(bytes32 indexed dealId, uint8 decision);
    event ResolverFeesSwept(address indexed token, address indexed recipient, uint256 amount);

    modifier onlyOperations() {
        require(msg.sender == operationsSafe, "operations only");
        _;
    }

    modifier onlyHumanReview() {
        require(msg.sender == humanReviewSafe, "human review Safe only");
        _;
    }

    constructor(
        address operationsSafe_,
        address humanReviewSafe_,
        address feeRecipient_,
        address signerA,
        address signerB,
        address signerC,
        uint256 automaticAmountCap_,
        uint256 appealWindow_,
        uint16 minimumConfidenceBps_
    ) EIP712("AgentNotaryAIReviewResolver", "1") {
        require(operationsSafe_ != address(0) && humanReviewSafe_ != address(0) && feeRecipient_ != address(0), "Safe required");
        require(operationsSafe_ != humanReviewSafe_, "separate operations and review Safes");
        require(signerA != address(0) && signerB != address(0) && signerC != address(0), "signer required");
        require(signerA != signerB && signerA != signerC && signerB != signerC, "duplicate signer");
        require(automaticAmountCap_ > 0, "automatic cap required");
        require(appealWindow_ >= 1 hours && appealWindow_ <= 7 days, "bad appeal window");
        require(minimumConfidenceBps_ >= 5001 && minimumConfidenceBps_ <= BPS_DENOMINATOR, "bad confidence threshold");
        operationsSafe = operationsSafe_;
        humanReviewSafe = humanReviewSafe_;
        feeRecipient = feeRecipient_;
        automaticAmountCap = automaticAmountCap_;
        appealWindow = appealWindow_;
        minimumConfidenceBps = minimumConfidenceBps_;
        signers = [signerA, signerB, signerC];
        isSigner[signerA] = true;
        isSigner[signerB] = true;
        isSigner[signerC] = true;
    }

    function isAgentNotaryReviewResolver() external pure returns (bool) { return true; }

    /// @notice Circular deployment is avoided by binding the escrow exactly once.
    function bindEscrow(address escrow_) external onlyOperations {
        require(escrow == address(0), "escrow already bound");
        require(escrow_.code.length > 0, "escrow contract required");
        require(IAgentNotaryReviewEscrow(escrow_).reviewArbitrator() == address(this), "resolver mismatch");
        escrow = escrow_;
        emit EscrowBound(escrow_);
    }

    function proposeAIResolution(
        bytes32 dealId,
        uint8 decision,
        bytes32 packageHash,
        bytes32 reportHash,
        uint16 confidenceBps,
        uint32 flags,
        uint256 nonce,
        uint256 signatureDeadline,
        bytes[] calldata signatures
    ) external {
        require(escrow != address(0), "escrow not bound");
        require(decision <= 1, "bad decision");
        require(packageHash != bytes32(0) && reportHash != bytes32(0), "review hashes required");
        require(confidenceBps >= minimumConfidenceBps, "low confidence");
        require(flags == 0, "review requires human attention");
        require(block.timestamp <= signatureDeadline, "signatures expired");
        require(nonce == nonces[dealId], "bad nonce");
        require(!pendingRulings[dealId].exists, "ruling already pending");

        (,,, uint8 state, uint256 amount, uint256 arbitrationDeadline) =
            IAgentNotaryReviewEscrow(escrow).reviewResolutionContext(dealId);
        require(state == DISPUTED_STATE, "deal not disputed");
        require(amount <= automaticAmountCap, "amount requires human review");
        require(
            block.timestamp + appealWindow + HUMAN_REVIEW_RESERVE < arbitrationDeadline,
            "insufficient appeal and human review time"
        );

        bytes32 structHash = keccak256(abi.encode(
            REVIEW_TYPEHASH, dealId, decision, packageHash, reportHash,
            confidenceBps, flags, nonce, signatureDeadline
        ));
        _requireQuorum(_hashTypedDataV4(structHash), signatures);
        nonces[dealId] = nonce + 1;
        uint256 deadline = block.timestamp + appealWindow;
        pendingRulings[dealId] = PendingRuling({
            decision: decision,
            packageHash: packageHash,
            reportHash: reportHash,
            confidenceBps: confidenceBps,
            appealDeadline: deadline,
            appealed: false,
            exists: true
        });
        emit AIRulingProposed(dealId, decision, packageHash, reportHash, confidenceBps, deadline);
    }

    function appeal(bytes32 dealId) external {
        PendingRuling storage ruling = pendingRulings[dealId];
        require(ruling.exists && !ruling.appealed, "no appealable ruling");
        require(block.timestamp < ruling.appealDeadline, "appeal closed");
        (address buyer, address seller,,,,) = IAgentNotaryReviewEscrow(escrow).reviewResolutionContext(dealId);
        require(msg.sender == buyer || msg.sender == seller, "deal party only");
        ruling.appealed = true;
        emit AIRulingAppealed(dealId, msg.sender);
    }

    function finalizeAIResolution(bytes32 dealId) external nonReentrant {
        PendingRuling memory ruling = pendingRulings[dealId];
        require(ruling.exists, "no pending ruling");
        require(!ruling.appealed, "human review required");
        require(block.timestamp >= ruling.appealDeadline, "appeal window open");
        (,, address assigned, uint8 state,, uint256 arbitrationDeadline) =
            IAgentNotaryReviewEscrow(escrow).reviewResolutionContext(dealId);
        require(assigned == address(this) && state == DISPUTED_STATE, "deal not resolvable");
        require(block.timestamp < arbitrationDeadline, "arbitration closed");
        delete pendingRulings[dealId];
        IAgentNotaryReviewEscrow(escrow).resolveReview(dealId, ruling.decision);
        emit AIRulingFinalized(dealId, ruling.decision);
    }

    function humanResolve(bytes32 dealId, uint8 decision) external onlyHumanReview nonReentrant {
        require(escrow != address(0), "escrow not bound");
        require(decision <= 1, "bad decision");
        delete pendingRulings[dealId];
        IAgentNotaryReviewEscrow(escrow).resolveReview(dealId, decision);
        emit HumanRulingFinalized(dealId, decision);
    }

    /// @notice Anyone may forward resolver fees to the configured Treasury Safe.
    function sweepFees(address token) external nonReentrant {
        uint256 amount = IERC20(token).balanceOf(address(this));
        require(amount > 0, "no fees");
        IERC20(token).safeTransfer(feeRecipient, amount);
        emit ResolverFeesSwept(token, feeRecipient, amount);
    }

    function _requireQuorum(bytes32 digest, bytes[] calldata signatures) internal view {
        require(signatures.length >= 2 && signatures.length <= 3, "two signatures required");
        address[] memory seen = new address[](signatures.length);
        uint256 valid;
        for (uint256 i = 0; i < signatures.length; i++) {
            address recovered = ECDSA.recover(digest, signatures[i]);
            require(isSigner[recovered], "unknown signer");
            for (uint256 j = 0; j < valid; j++) require(seen[j] != recovered, "duplicate signer");
            seen[valid++] = recovered;
        }
        require(valid >= 2, "quorum not reached");
    }
}
