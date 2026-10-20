// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

interface ISafeThreshold {
    function getThreshold() external view returns (uint256);
}

interface IAgentNotaryReviewResolver {
    function isAgentNotaryReviewResolver() external pure returns (bool);
}

/// @notice Mainnet candidate. This source is not a live deployment or an audit.
/// It supports deterministic evidence validation and buyer-reviewed work. The
/// operations Safe selects validator quorums/arbitrators for future deals only; every
/// deal permanently stores the resolver that applied when it was funded.
contract AgentNotaryMainnetEscrow is EIP712, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    address public constant ARBITRUM_NATIVE_USDC = 0xaf88d065e77c8cC2239327C5EDb3A432268e5831;
    uint256 public constant MIN_AUTOMATIC_AMOUNT = 10e6;
    uint256 public constant MIN_REVIEW_AMOUNT = 100e6;
    uint256 public constant MAX_AMOUNT = 1_000e6;
    uint256 public constant MAX_TOTAL_ESCROWED = 10_000e6;
    uint256 public constant MIN_ARBITRATION_RESERVE = 5e6;
    uint256 public constant MAX_ARBITRATION_RESERVE = 100e6;
    uint256 public constant MAX_PROTOCOL_FEE = 50e6;
    uint256 public constant MIN_WINDOW = 10 minutes;
    uint256 public constant MAX_WINDOW = 30 days;
    uint16 public constant PROTOCOL_FEE_BPS = 150;
    uint16 public constant BPS_DENOMINATOR = 10_000;
    uint256 public constant FOUNDING_PERIOD = 30 days;
    uint256 public constant FOUNDING_LIMIT = 50;
    uint256 public constant MIN_REVIEW_WINDOW = 24 hours;
    uint256 public constant MAX_INCONCLUSIVE_RESULTS = 3;
    uint256 public constant MAX_ESCROWED_PER_BUYER = 1_100e6;

    bytes32 public constant VALIDATION_TYPEHASH = keccak256(
        "Validation(bytes32 dealId,bytes32 contentHash,bytes32 manifestHash,bytes32 policyHash,uint8 decision,bytes32 evidenceHash,uint256 nonce,uint256 signatureDeadline)"
    );

    IERC20 public immutable token;
    address public immutable treasurySafe;
    address public immutable operationsSafe;

    address public automaticValidator;
    address public reviewArbitrator;
    bool public publicAccess;
    uint256 public totalEscrowed;
    uint256 public foundingSeatCount;

    enum Mode { Automatic, BuyerReview }
    enum State {
        None,
        Proposed,
        Locked,
        Delivered,
        Disputed,
        Paid,
        Refunded,
        FinalizedSplit
    }
    enum ValidationDecision { Pass, Fail, Inconclusive }
    enum ReviewDecision { SellerWins, BuyerWins }
    enum SeatState { None, Approved, Active, Cancelled }

    struct DealRequest {
        bytes32 salt;
        address seller;
        Mode mode;
        uint256 amount;
        uint256 arbitrationReserve;
        uint16 fallbackSellerBps;
        bytes32 manifestHash;
        bytes32 policyHash;
        uint256 acceptanceWindow;
        uint256 deliveryWindow;
        uint256 decisionWindow;
        uint256 arbitrationWindow;
    }

    struct Deal {
        address buyer;
        address seller;
        address resolver;
        Mode mode;
        State state;
        uint256 amount;
        uint256 arbitrationReserve;
        uint256 sellerBond;
        uint256 protocolFee;
        uint16 fallbackSellerBps;
        bytes32 manifestHash;
        bytes32 policyHash;
        bytes32 contentHash;
        uint256 acceptanceDeadline;
        uint256 deliveryWindow;
        uint256 decisionWindow;
        uint256 arbitrationWindow;
        uint256 deliveryDeadline;
        uint256 decisionDeadline;
        uint256 arbitrationDeadline;
        uint256 validationNonce;
    }

    mapping(bytes32 => Deal) public deals;
    mapping(address => bool) public approvedBuyers;
    mapping(address => SeatState) public foundingSeats;
    mapping(address => uint256) public feeWaiverUntil;
    mapping(address => uint256) public escrowedByBuyer;

    event BuyerAccessChanged(address indexed buyer, bool allowed);
    event PublicAccessChanged(bool open);
    event AutomaticValidatorChanged(address indexed validator);
    event ReviewArbitratorChanged(address indexed arbitrator);
    event FoundingSeatChanged(address indexed buyer, SeatState state, uint256 seatCount, uint256 feeWaiverUntil);
    event DealProposed(
        bytes32 indexed id,
        address indexed buyer,
        address indexed seller,
        Mode mode,
        address resolver,
        uint256 amount,
        uint256 arbitrationReserve,
        uint16 fallbackSellerBps,
        bytes32 manifestHash,
        bytes32 policyHash,
        uint256 acceptanceDeadline
    );
    event DealAccepted(bytes32 indexed id, uint256 deliveryDeadline);
    event DealDelivered(bytes32 indexed id, bytes32 contentHash, string uri, uint256 decisionDeadline);
    event ValidationRecorded(bytes32 indexed id, ValidationDecision decision, bytes32 evidenceHash, uint256 nonce);
    event DealDisputed(bytes32 indexed id, bytes32 reasonHash, string evidenceUri, uint256 arbitrationDeadline);
    event DealClosed(
        bytes32 indexed id,
        State state,
        uint256 sellerAmount,
        uint256 buyerAmount,
        uint256 treasuryAmount,
        uint256 resolverAmount
    );

    modifier onlyOperations() {
        require(msg.sender == operationsSafe, "operations only");
        _;
    }

    constructor(
        address token_,
        address treasurySafe_,
        address operationsSafe_,
        address automaticValidator_,
        address reviewArbitrator_
    ) EIP712("AgentNotaryMainnetEscrow", "1") {
        require(
            block.chainid == 42161 || block.chainid == 31337 || block.chainid == 131277322940537,
            "unsupported chain"
        );
        require(token_.code.length > 0, "token required");
        require(IERC20Metadata(token_).decimals() == 6, "USDC must use 6 decimals");
        if (block.chainid == 42161) require(token_ == ARBITRUM_NATIVE_USDC, "native USDC only");
        require(treasurySafe_ != address(0) && operationsSafe_ != address(0), "Safe required");
        require(treasurySafe_ != address(this) && operationsSafe_ != address(this), "bad Safe");
        require(treasurySafe_ != operationsSafe_, "separate Safes required");
        require(automaticValidator_ != address(0) && reviewArbitrator_ != address(0), "resolver required");
        require(automaticValidator_ != reviewArbitrator_, "separate resolvers required");
        require(
            automaticValidator_ != treasurySafe_ && automaticValidator_ != operationsSafe_ &&
            reviewArbitrator_ != treasurySafe_ && reviewArbitrator_ != operationsSafe_,
            "resolver conflicts with Safe"
        );
        if (block.chainid == 42161) {
            require(treasurySafe_.code.length > 0 && operationsSafe_.code.length > 0, "deployed Safes required");
            require(automaticValidator_.code.length > 0, "validator quorum required");
            require(reviewArbitrator_.code.length > 0, "review resolver required");
            require(ISafeThreshold(treasurySafe_).getThreshold() >= 2, "treasury multisig required");
            require(ISafeThreshold(operationsSafe_).getThreshold() >= 2, "operations multisig required");
            require(IAgentNotaryReviewResolver(reviewArbitrator_).isAgentNotaryReviewResolver(), "approved review resolver required");
        }

        token = IERC20(token_);
        treasurySafe = treasurySafe_;
        operationsSafe = operationsSafe_;
        automaticValidator = automaticValidator_;
        reviewArbitrator = reviewArbitrator_;
    }

    function pauseNewDeals() external onlyOperations { _pause(); }
    function resumeNewDeals() external onlyOperations { _unpause(); }

    function setPublicAccess(bool open) external onlyOperations {
        publicAccess = open;
        emit PublicAccessChanged(open);
    }

    function setBuyerAccess(address buyer, bool allowed) external onlyOperations {
        require(buyer != address(0), "buyer required");
        approvedBuyers[buyer] = allowed;
        emit BuyerAccessChanged(buyer, allowed);
    }

    /// @notice Changes affect new deals only. Existing deals retain their resolver.
    function setAutomaticValidator(address validator) external onlyOperations {
        require(validator != address(0), "validator required");
        require(validator != reviewArbitrator && validator != treasurySafe && validator != operationsSafe, "resolver conflict");
        if (block.chainid == 42161) {
            require(validator.code.length > 0, "validator quorum required");
            // Resolver rotation must not replace the reviewed immutable quorum implementation
            // with an arbitrary IERC1271 contract that can approve one operator's signature.
            require(validator.codehash == automaticValidator.codehash, "validator implementation mismatch");
        }
        automaticValidator = validator;
        emit AutomaticValidatorChanged(validator);
    }

    /// @notice Changes affect new deals only. Existing deals retain their resolver.
    function setReviewArbitrator(address arbitrator) external onlyOperations {
        require(arbitrator != address(0), "arbitrator required");
        require(arbitrator != automaticValidator && arbitrator != treasurySafe && arbitrator != operationsSafe, "resolver conflict");
        if (block.chainid == 42161) {
            require(arbitrator.code.length > 0, "review resolver required");
            require(arbitrator.codehash == reviewArbitrator.codehash, "arbitrator implementation mismatch");
            require(IAgentNotaryReviewResolver(arbitrator).isAgentNotaryReviewResolver(), "approved review resolver required");
        }
        reviewArbitrator = arbitrator;
        emit ReviewArbitratorChanged(arbitrator);
    }

    function admitFoundingBuyer(address buyer) external onlyOperations {
        require(buyer != address(0), "buyer required");
        SeatState oldState = foundingSeats[buyer];
        require(oldState == SeatState.None || oldState == SeatState.Cancelled, "seat exists");
        require(foundingSeatCount < FOUNDING_LIMIT, "founding seats full");
        foundingSeats[buyer] = SeatState.Approved;
        approvedBuyers[buyer] = true;
        foundingSeatCount += 1;
        emit FoundingSeatChanged(buyer, SeatState.Approved, foundingSeatCount, 0);
    }

    function cancelUnactivatedFoundingBuyer(address buyer) external onlyOperations {
        require(foundingSeats[buyer] == SeatState.Approved, "not unactivated");
        foundingSeats[buyer] = SeatState.Cancelled;
        approvedBuyers[buyer] = false;
        foundingSeatCount -= 1;
        emit FoundingSeatChanged(buyer, SeatState.Cancelled, foundingSeatCount, 0);
    }

    function protocolFeeFor(address buyer, uint256 amount) public view returns (uint256) {
        if (foundingSeats[buyer] == SeatState.Active && block.timestamp < feeWaiverUntil[buyer]) return 0;
        uint256 fee = amount * PROTOCOL_FEE_BPS / BPS_DENOMINATOR;
        return fee > MAX_PROTOCOL_FEE ? MAX_PROTOCOL_FEE : fee;
    }

    function arbitrationReserveFor(uint256 amount) public pure returns (uint256) {
        uint256 reserve = amount * 500 / BPS_DENOMINATOR; // 5%
        if (reserve < MIN_ARBITRATION_RESERVE) reserve = MIN_ARBITRATION_RESERVE;
        return reserve > MAX_ARBITRATION_RESERVE ? MAX_ARBITRATION_RESERVE : reserve;
    }

    function proposeDeal(DealRequest calldata request) external nonReentrant whenNotPaused returns (bytes32 id) {
        require(publicAccess || approvedBuyers[msg.sender], "buyer not admitted");
        require(request.seller != address(0) && request.seller != msg.sender, "bad seller");
        require(request.amount <= MAX_AMOUNT, "amount too high");
        require(request.fallbackSellerBps <= BPS_DENOMINATOR, "bad fallback");
        require(request.manifestHash != bytes32(0) && request.policyHash != bytes32(0), "terms required");
        _requireWindow(request.acceptanceWindow);
        _requireWindow(request.deliveryWindow);
        _requireWindow(request.decisionWindow);
        _requireWindow(request.arbitrationWindow);

        address resolver;
        if (request.mode == Mode.Automatic) {
            require(request.amount >= MIN_AUTOMATIC_AMOUNT, "automatic minimum 10 USDC");
            require(request.arbitrationReserve == 0, "automatic reserve must be zero");
            resolver = automaticValidator;
        } else {
            require(request.amount >= MIN_REVIEW_AMOUNT, "review minimum 100 USDC");
            require(request.arbitrationReserve == arbitrationReserveFor(request.amount), "wrong arbitration reserve");
            require(request.decisionWindow >= MIN_REVIEW_WINDOW, "review window below 24 hours");
            resolver = reviewArbitrator;
        }

        uint256 total = request.amount + request.arbitrationReserve;
        require(totalEscrowed + total <= MAX_TOTAL_ESCROWED, "global escrow limit");
        require(escrowedByBuyer[msg.sender] + total <= MAX_ESCROWED_PER_BUYER, "buyer escrow limit");

        id = keccak256(abi.encode(address(this), block.chainid, msg.sender, request.seller, request.salt));
        require(deals[id].state == State.None, "duplicate deal");

        if (foundingSeats[msg.sender] == SeatState.Approved) {
            foundingSeats[msg.sender] = SeatState.Active;
            feeWaiverUntil[msg.sender] = block.timestamp + FOUNDING_PERIOD;
            emit FoundingSeatChanged(msg.sender, SeatState.Active, foundingSeatCount, feeWaiverUntil[msg.sender]);
        }

        Deal storage d = deals[id];
        d.buyer = msg.sender;
        d.seller = request.seller;
        d.resolver = resolver;
        d.mode = request.mode;
        d.state = State.Proposed;
        d.amount = request.amount;
        d.arbitrationReserve = request.arbitrationReserve;
        // Price and any Founding waiver are fixed when funds enter escrow.
        d.protocolFee = protocolFeeFor(msg.sender, request.amount);
        d.fallbackSellerBps = request.fallbackSellerBps;
        d.manifestHash = request.manifestHash;
        d.policyHash = request.policyHash;
        d.acceptanceDeadline = block.timestamp + request.acceptanceWindow;
        d.deliveryWindow = request.deliveryWindow;
        d.decisionWindow = request.decisionWindow;
        d.arbitrationWindow = request.arbitrationWindow;

        totalEscrowed += total;
        escrowedByBuyer[msg.sender] += total;
        uint256 beforeBalance = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), total);
        require(token.balanceOf(address(this)) == beforeBalance + total, "unsupported token transfer");

        emit DealProposed(
            id, msg.sender, request.seller, request.mode, resolver, request.amount,
            request.arbitrationReserve, request.fallbackSellerBps, request.manifestHash,
            request.policyHash, d.acceptanceDeadline
        );
    }

    function sellerAccept(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp < d.acceptanceDeadline, "acceptance closed");
        if (d.mode == Mode.BuyerReview) {
            uint256 bond = d.arbitrationReserve;
            require(totalEscrowed + bond <= MAX_TOTAL_ESCROWED, "global escrow limit");
            uint256 beforeBalance = token.balanceOf(address(this));
            token.safeTransferFrom(msg.sender, address(this), bond);
            require(token.balanceOf(address(this)) == beforeBalance + bond, "unsupported token transfer");
            d.sellerBond = bond;
            totalEscrowed += bond;
        }
        d.state = State.Locked;
        d.deliveryDeadline = block.timestamp + d.deliveryWindow;
        emit DealAccepted(id, d.deliveryDeadline);
    }

    function cancelProposal(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(msg.sender == d.buyer, "buyer only");
        _refundAll(id, d);
    }

    function expireProposal(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(block.timestamp >= d.acceptanceDeadline, "not expired");
        _refundAll(id, d);
    }

    function deliver(bytes32 id, bytes32 contentHash, string calldata uri) external {
        Deal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp < d.deliveryDeadline, "delivery closed");
        require(contentHash != bytes32(0), "content hash required");
        require(bytes(uri).length > 0 && bytes(uri).length <= 512, "bad uri");
        d.contentHash = contentHash;
        d.state = State.Delivered;
        d.decisionDeadline = block.timestamp + d.decisionWindow;
        emit DealDelivered(id, contentHash, uri, d.decisionDeadline);
    }

    function expireUndelivered(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(block.timestamp >= d.deliveryDeadline, "not expired");
        _refundAll(id, d);
    }

    /// @notice Anyone can relay a validator's scoped EIP-712 signature and pay its gas.
    function submitValidation(
        bytes32 id,
        ValidationDecision decision,
        bytes32 evidenceHash,
        uint256 signatureDeadline,
        bytes calldata signature
    ) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.Automatic && d.state == State.Delivered, "not automatic delivery");
        require(block.timestamp < d.decisionDeadline, "validation closed");
        require(block.timestamp <= signatureDeadline, "signature expired");
        require(evidenceHash != bytes32(0), "evidence required");

        uint256 nonce = d.validationNonce;
        require(nonce < MAX_INCONCLUSIVE_RESULTS, "validation attempts exhausted");
        bytes32 structHash = keccak256(abi.encode(
            VALIDATION_TYPEHASH,
            id,
            d.contentHash,
            d.manifestHash,
            d.policyHash,
            uint8(decision),
            evidenceHash,
            nonce,
            signatureDeadline
        ));
        bytes32 digest = _hashTypedDataV4(structHash);
        require(SignatureChecker.isValidSignatureNow(d.resolver, digest, signature), "bad validator signature");
        d.validationNonce = nonce + 1;
        emit ValidationRecorded(id, decision, evidenceHash, nonce);

        if (decision == ValidationDecision.Pass) {
            _paySeller(id, d, false);
        } else if (decision == ValidationDecision.Fail) {
            _refundAll(id, d);
        }
    }

    function acceptDelivery(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.BuyerReview && d.state == State.Delivered, "not review delivery");
        require(msg.sender == d.buyer, "buyer only");
        _paySeller(id, d, false);
    }

    function disputeDelivery(bytes32 id, bytes32 reasonHash, string calldata evidenceUri) external {
        Deal storage d = deals[id];
        require(d.mode == Mode.BuyerReview && d.state == State.Delivered, "not review delivery");
        require(msg.sender == d.buyer, "buyer only");
        require(block.timestamp < d.decisionDeadline, "review closed");
        require(reasonHash != bytes32(0), "reason required");
        require(bytes(evidenceUri).length > 0 && bytes(evidenceUri).length <= 512, "bad evidence uri");
        d.state = State.Disputed;
        d.arbitrationDeadline = block.timestamp + d.arbitrationWindow;
        emit DealDisputed(id, reasonHash, evidenceUri, d.arbitrationDeadline);
    }

    function finalizeIfSilent(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.BuyerReview && d.state == State.Delivered, "not review delivery");
        require(block.timestamp >= d.decisionDeadline, "review still open");
        _paySeller(id, d, false);
    }

    function resolveReview(bytes32 id, ReviewDecision decision) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.BuyerReview && d.state == State.Disputed, "not disputed");
        require(msg.sender == d.resolver, "assigned arbitrator only");
        require(block.timestamp < d.arbitrationDeadline, "arbitration closed");
        if (decision == ReviewDecision.SellerWins) _paySeller(id, d, true);
        else _refundBuyerAfterReview(id, d);
    }

    /// @notice Minimal immutable context used by the assigned hybrid review resolver.
    function reviewResolutionContext(bytes32 id) external view returns (
        address buyer,
        address seller,
        address resolver,
        State state,
        uint256 amount,
        uint256 arbitrationDeadline
    ) {
        Deal storage d = deals[id];
        return (d.buyer, d.seller, d.resolver, d.state, d.amount, d.arbitrationDeadline);
    }

    /// @notice Automatic validator outage is not treated as delivery failure.
    function finalizeUnresolvedAutomatic(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.Automatic && d.state == State.Delivered, "not automatic delivery");
        require(block.timestamp >= d.decisionDeadline, "validation still open");
        _applyFallback(id, d);
    }

    function finalizeUnresolvedReview(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.mode == Mode.BuyerReview && d.state == State.Disputed, "not disputed");
        require(block.timestamp >= d.arbitrationDeadline, "arbitration still open");
        _applyFallback(id, d);
    }

    function _paySeller(bytes32 id, Deal storage d, bool payResolver) internal {
        uint256 fee = d.protocolFee;
        uint256 sellerAmount = d.amount - fee;
        uint256 buyerAmount = payResolver ? 0 : d.arbitrationReserve;
        uint256 resolverAmount = payResolver ? d.arbitrationReserve : 0;
        sellerAmount += d.sellerBond;
        d.state = State.Paid;
        _removeEscrow(d);
        token.safeTransfer(d.seller, sellerAmount);
        if (buyerAmount > 0) token.safeTransfer(d.buyer, buyerAmount);
        if (fee > 0) token.safeTransfer(treasurySafe, fee);
        if (resolverAmount > 0) token.safeTransfer(d.resolver, resolverAmount);
        emit DealClosed(id, d.state, sellerAmount, buyerAmount, fee, resolverAmount);
    }

    function _refundAll(bytes32 id, Deal storage d) internal {
        uint256 refund = d.amount + d.arbitrationReserve;
        uint256 sellerAmount = d.sellerBond;
        d.state = State.Refunded;
        _removeEscrow(d);
        token.safeTransfer(d.buyer, refund);
        if (sellerAmount > 0) token.safeTransfer(d.seller, sellerAmount);
        emit DealClosed(id, d.state, sellerAmount, refund, 0, 0);
    }

    function _refundBuyerAfterReview(bytes32 id, Deal storage d) internal {
        uint256 buyerAmount = d.amount + d.arbitrationReserve;
        uint256 resolverAmount = d.sellerBond;
        d.state = State.Refunded;
        _removeEscrow(d);
        token.safeTransfer(d.buyer, buyerAmount);
        if (resolverAmount > 0) token.safeTransfer(d.resolver, resolverAmount);
        emit DealClosed(id, d.state, 0, buyerAmount, 0, resolverAmount);
    }

    function _applyFallback(bytes32 id, Deal storage d) internal {
        uint256 sellerAmount = d.amount * d.fallbackSellerBps / BPS_DENOMINATOR;
        uint256 buyerAmount = d.amount - sellerAmount + d.arbitrationReserve;
        uint256 sellerRefund = d.sellerBond;
        d.state = State.FinalizedSplit;
        _removeEscrow(d);
        if (sellerAmount + sellerRefund > 0) token.safeTransfer(d.seller, sellerAmount + sellerRefund);
        if (buyerAmount > 0) token.safeTransfer(d.buyer, buyerAmount);
        emit DealClosed(id, d.state, sellerAmount + sellerRefund, buyerAmount, 0, 0);
    }

    function _removeEscrow(Deal storage d) internal {
        uint256 buyerDeposit = d.amount + d.arbitrationReserve;
        totalEscrowed -= buyerDeposit + d.sellerBond;
        escrowedByBuyer[d.buyer] -= buyerDeposit;
    }

    function _requireWindow(uint256 window) internal pure {
        require(window >= MIN_WINDOW && window <= MAX_WINDOW, "bad window");
    }
}
