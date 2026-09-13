// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @notice Testnet-only prototype. NOT compiled or tested in this environment.
/// This is a SEPARATE contract from AgentNotaryEscrow.sol and shares no storage
/// or token balance accounting with it beyond both pointing at the same ERC20
/// token and treasury address. A bug here cannot corrupt deals held in the
/// legacy exact-hash-match contract, and vice versa.
///
/// This contract has NO owner, NO pause/kill-switch, and NO admin recovery
/// function of any kind. That is a deliberate design choice, not an omission:
/// every state a deal can be in has exactly one permissionless, time-gated
/// exit path to a terminal state (see each function's NatSpec below).
/// Abandoning this contract does NOT rescue funds that are already locked in
/// it — the only way funds move is through a deal's own permissionless
/// timeout functions or the parties' own actions. There is no
/// "give up and an admin bails you out" path, by design and by absence of code.
///
/// This contract does NOT provide any guarantee that buyer, seller, and
/// arbiter are controlled by independent, non-colluding parties. Distinct
/// addresses are not distinct people. The mandatory splitBps exit rule exists
/// specifically because the contract cannot detect or prevent collusion; it
/// only guarantees that no deal can be created without both parties having
/// explicitly agreed, in advance, to a deterministic fallback outcome.
contract AgentNotaryOpenEscrow is ReentrancyGuard {
    using SafeERC20 for IERC20;

    uint256 public constant FIXED_FEE = 5000; // USDC has 6 decimals, same unit as legacy contract
    uint256 public constant MAX_AMOUNT = 1000 * 1e6;
    uint256 public constant MAX_ARBITER_FEE = 1000 * 1e6;
    uint256 public constant MIN_WINDOW = 10 minutes;
    uint256 public constant MAX_WINDOW = 7 days;
    uint16 public constant BPS_DENOMINATOR = 10000;

    IERC20 public immutable token;
    address public immutable treasury;

    enum State {
        None,               // 0
        Proposed,           // 1 - funds locked, awaiting seller + arbiter acceptance
        Locked,             // 2 - both accepted, delivery window running
        Delivered,          // 3 - seller delivered, dispute window running
        Disputed,           // 4 - buyer disputed, arbitration window running
        Accepted,           // 5 - terminal: explicit or silent acceptance, seller paid
        ResolvedSeller,     // 6 - terminal: arbiter ruled for seller
        ResolvedBuyer,      // 7 - terminal: arbiter ruled for buyer
        FinalizedSplit,     // 8 - terminal: arbiter never ruled, mandatory splitBps applied
        RejectedAtProposal, // 9 - terminal: acceptance window expired, full refund
        ExpiredUndelivered  // 10 - terminal: submit window expired, full refund
    }

    struct OpenDeal {
        address buyer;
        address seller;
        address arbiter;
        uint256 amount;
        uint256 arbiterFee;
        uint16 splitBps;          // seller's share (out of 10000) IF the arbiter never rules.
                                   // Mandatory at creation. This is not a fairness guarantee —
                                   // it is a pre-agreed, deterministic fallback the parties
                                   // accepted before any dispute existed. It can be gamed if
                                   // one party can predict a stalemate is likely; frontends
                                   // integrating this contract MUST surface this risk to both
                                   // parties before they accept a deal, not just show a number.
        bytes32 termsHash;         // binds the job description + acceptance criteria, fixed forever
        uint256 acceptanceDeadline;
        uint256 submitWindow;
        uint256 disputeWindow;
        uint256 arbitrationWindow;
        uint256 submitDeadline;
        uint256 disputeDeadline;
        uint256 arbitrationDeadline;
        bytes32 deliveredContentHash;
        bool sellerAccepted;
        bool arbiterAccepted;
        State state;
    }

    mapping(bytes32 => OpenDeal) public deals;

    event Proposed(
        bytes32 indexed id, address indexed buyer, address indexed seller, address arbiter,
        uint256 amount, uint256 arbiterFee, uint16 splitBps, bytes32 termsHash,
        uint256 acceptanceDeadline
    );
    event PartyAccepted(bytes32 indexed id, address indexed party, bool nowLocked, uint256 submitDeadline);
    event Delivered(bytes32 indexed id, bytes32 contentHash, string uri, uint256 disputeDeadline);
    event Disputed(bytes32 indexed id, bytes32 reasonHash, uint256 arbitrationDeadline);
    event Closed(
        bytes32 indexed id, State state,
        uint256 sellerAmount, uint256 buyerAmount, uint256 treasuryAmount, uint256 arbiterAmount
    );

    constructor(address token_, address treasury_) {
        require(block.chainid == 421614 || block.chainid == 31337 || block.chainid == 131277322940537, "testnet only");
        require(token_.code.length > 0 && treasury_ != address(0) && treasury_ != address(this), "bad configuration");
        require(IERC20Metadata(token_).decimals() == 6, "6 decimals required");
        if (block.chainid == 421614) require(token_ == 0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d, "wrong test USDC");
        token = IERC20(token_);
        treasury = treasury_;
    }

    function _commission(uint256 amount) internal pure returns (uint256) {
        return amount * 150 / BPS_DENOMINATOR; // 1.5%, floored, same formula as legacy contract
    }

    /// @notice Creates a deal. NOTHING about it (terms, amounts, arbiter, windows, splitBps)
    /// can ever be changed after this call succeeds. There is no setter function for any
    /// of these fields anywhere in this contract.
    function proposeDeal(
        bytes32 salt,
        address seller,
        address arbiter,
        uint256 amount,
        uint256 arbiterFee,
        uint16 splitBps,
        bytes32 termsHash,
        uint256 acceptanceWindow,
        uint256 submitWindow,
        uint256 disputeWindow,
        uint256 arbitrationWindow
    ) external nonReentrant returns (bytes32 id) {
        require(seller != address(0) && seller != msg.sender && seller != address(this), "bad seller");
        require(arbiter != address(0) && arbiter != address(this), "bad arbiter");
        require(arbiter != msg.sender && arbiter != seller && arbiter != treasury, "arbiter must be distinct");
        require(amount > 0 && amount <= MAX_AMOUNT, "bad amount");
        require(arbiterFee <= MAX_ARBITER_FEE, "bad arbiter fee");
        require(splitBps <= BPS_DENOMINATOR, "splitBps out of range");
        require(termsHash != bytes32(0), "missing terms hash");
        require(acceptanceWindow >= MIN_WINDOW && acceptanceWindow <= MAX_WINDOW, "bad acceptance window");
        require(submitWindow >= MIN_WINDOW && submitWindow <= MAX_WINDOW, "bad submit window");
        require(disputeWindow >= MIN_WINDOW && disputeWindow <= MAX_WINDOW, "bad dispute window");
        require(arbitrationWindow >= MIN_WINDOW && arbitrationWindow <= MAX_WINDOW, "bad arbitration window");

        id = keccak256(abi.encode(msg.sender, salt, "AGENTNOTARY_OPEN_V1"));
        require(deals[id].state == State.None, "duplicate deal");

        uint256 total = amount + FIXED_FEE + arbiterFee;

        deals[id] = OpenDeal({
            buyer: msg.sender,
            seller: seller,
            arbiter: arbiter,
            amount: amount,
            arbiterFee: arbiterFee,
            splitBps: splitBps,
            termsHash: termsHash,
            acceptanceDeadline: block.timestamp + acceptanceWindow,
            submitWindow: submitWindow,
            disputeWindow: disputeWindow,
            arbitrationWindow: arbitrationWindow,
            submitDeadline: 0,
            disputeDeadline: 0,
            arbitrationDeadline: 0,
            deliveredContentHash: bytes32(0),
            sellerAccepted: false,
            arbiterAccepted: false,
            state: State.Proposed
        });

        uint256 beforeBalance = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), total);
        require(token.balanceOf(address(this)) == beforeBalance + total, "unsupported token transfer");

        emit Proposed(id, msg.sender, seller, arbiter, amount, arbiterFee, splitBps, termsHash, deals[id].acceptanceDeadline);
    }

    function _tryLock(bytes32 id, OpenDeal storage d) internal {
        if (d.sellerAccepted && d.arbiterAccepted) {
            d.state = State.Locked;
            d.submitDeadline = block.timestamp + d.submitWindow;
            emit PartyAccepted(id, address(0), true, d.submitDeadline);
        }
    }

    function sellerAccept(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp < d.acceptanceDeadline, "acceptance window closed");
        require(!d.sellerAccepted, "already accepted");
        d.sellerAccepted = true;
        emit PartyAccepted(id, msg.sender, false, 0);
        _tryLock(id, d);
    }

    function arbiterAccept(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(msg.sender == d.arbiter, "arbiter only");
        require(block.timestamp < d.acceptanceDeadline, "acceptance window closed");
        require(!d.arbiterAccepted, "already accepted");
        d.arbiterAccepted = true;
        emit PartyAccepted(id, msg.sender, false, 0);
        _tryLock(id, d);
    }

    /// @notice Permissionless. If both parties never (or only partially) accepted in time,
    /// anyone can trigger a full, no-deduction refund to the buyer.
    function expireProposal(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Proposed, "not proposed");
        require(block.timestamp >= d.acceptanceDeadline, "not expired");
        d.state = State.RejectedAtProposal; // set before external call
        uint256 refund = d.amount + FIXED_FEE + d.arbiterFee;
        token.safeTransfer(d.buyer, refund);
        emit Closed(id, d.state, 0, refund, 0, 0);
    }

    function deliver(bytes32 id, bytes32 contentHash, string calldata uri) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp < d.submitDeadline, "submit window closed");
        require(contentHash != bytes32(0), "missing content hash");
        require(bytes(uri).length > 0 && bytes(uri).length <= 256, "bad uri length");
        d.deliveredContentHash = contentHash;
        d.state = State.Delivered;
        d.disputeDeadline = block.timestamp + d.disputeWindow;
        emit Delivered(id, contentHash, uri, d.disputeDeadline);
        // Note: uri is not kept in contract storage (gas cost), only emitted via this event;
        // indexers/frontends and the arbiter must read it from the Delivered event log.
    }

    /// @notice Permissionless. If the seller never delivers in time, anyone can trigger a
    /// full, no-deduction refund to the buyer.
    function expireUndelivered(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(block.timestamp >= d.submitDeadline, "not expired");
        d.state = State.ExpiredUndelivered;
        uint256 refund = d.amount + FIXED_FEE + d.arbiterFee;
        token.safeTransfer(d.buyer, refund);
        emit Closed(id, d.state, 0, refund, 0, 0);
    }

    function _settleAccepted(bytes32 id, OpenDeal storage d) internal {
        d.state = State.Accepted; // set before external calls
        uint256 commission = _commission(d.amount);
        uint256 payout = d.amount - commission;
        uint256 treasuryAmount = commission + FIXED_FEE;
        token.safeTransfer(d.seller, payout);
        token.safeTransfer(d.buyer, d.arbiterFee); // arbiter never acted, fee returns to buyer
        token.safeTransfer(treasury, treasuryAmount);
        emit Closed(id, d.state, payout, d.arbiterFee, treasuryAmount, 0);
    }

    function acceptDelivery(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Delivered, "not delivered");
        require(msg.sender == d.buyer, "buyer only");
        _settleAccepted(id, d);
    }

    /// @notice Permissionless. Silence within the dispute window is treated as acceptance.
    function finalizeIfSilent(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Delivered, "not delivered");
        require(block.timestamp >= d.disputeDeadline, "dispute window still open");
        _settleAccepted(id, d);
    }

    function disputeDelivery(bytes32 id, bytes32 reasonHash) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Delivered, "not delivered");
        require(msg.sender == d.buyer, "buyer only");
        require(block.timestamp < d.disputeDeadline, "dispute window closed");
        require(reasonHash != bytes32(0), "missing reason hash");
        d.state = State.Disputed;
        d.arbitrationDeadline = block.timestamp + d.arbitrationWindow;
        emit Disputed(id, reasonHash, d.arbitrationDeadline);
    }

    /// @notice The arbiter's binary ruling. Whether an unreachable delivery URI counts for
    /// or against the seller is NOT decided by this contract — it is a matter the arbiter
    /// must weigh according to the off-chain terms bound by termsHash (e.g. which party
    /// bears responsibility for keeping delivered content accessible). This function only
    /// records the arbiter's ruling and pays out accordingly.
    function arbitrate(bytes32 id, bool sellerWins) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Disputed, "not disputed");
        require(msg.sender == d.arbiter, "arbiter only");
        require(block.timestamp < d.arbitrationDeadline, "arbitration window closed");

        if (sellerWins) {
            d.state = State.ResolvedSeller; // set before external calls
            uint256 commission = _commission(d.amount);
            uint256 payout = d.amount - commission;
            uint256 treasuryAmount = commission + FIXED_FEE;
            token.safeTransfer(d.seller, payout);
            token.safeTransfer(treasury, treasuryAmount);
            token.safeTransfer(d.arbiter, d.arbiterFee);
            emit Closed(id, d.state, payout, 0, treasuryAmount, d.arbiterFee);
        } else {
            d.state = State.ResolvedBuyer; // set before external calls
            token.safeTransfer(d.buyer, d.amount);
            token.safeTransfer(treasury, FIXED_FEE);
            token.safeTransfer(d.arbiter, d.arbiterFee);
            emit Closed(id, d.state, 0, d.amount, FIXED_FEE, d.arbiterFee);
        }
    }

    /// @notice Permissionless. Callable by anyone once the arbitration window has passed
    /// with no ruling. This is the deal's mandatory, pre-agreed exit rule — every deal
    /// created via proposeDeal has a valid splitBps by construction, so this path always
    /// exists and always terminates the deal. It is NOT a fairness mechanism: it pays the
    /// seller floor(amount * splitBps / 10000) exactly as splitBps was fixed at proposal
    /// time, regardless of who was actually in the right. The buyer receives the remainder
    /// of amount plus both arbiterFee (arbiter did not act, this is the buyer's money, not
    /// the arbiter's collateral) and FIXED_FEE (no arbitration service was rendered, so the
    /// protocol keeps nothing). Runs exactly once: state is set to a terminal value before
    /// any transfer, so a second call reverts on the state check below — this IS the single
    /// atomic finalize function, there is no separate "resolve stalemate" step afterward.
    function finalizeStalemate(bytes32 id) external nonReentrant {
        OpenDeal storage d = deals[id];
        require(d.state == State.Disputed, "not disputed");
        require(block.timestamp >= d.arbitrationDeadline, "arbitration window still open");

        d.state = State.FinalizedSplit; // set before external calls; blocks re-entry and re-calls
        uint256 sellerAmount = d.amount * d.splitBps / BPS_DENOMINATOR;
        uint256 buyerAmount = (d.amount - sellerAmount) + d.arbiterFee + FIXED_FEE;

        if (sellerAmount > 0) token.safeTransfer(d.seller, sellerAmount);
        token.safeTransfer(d.buyer, buyerAmount);
        // treasury receives nothing here, by design (see NatSpec above)

        emit Closed(id, d.state, sellerAmount, buyerAmount, 0, 0);
    }
}
