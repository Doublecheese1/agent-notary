// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @notice Testnet-only prototype. Exact UTF-8 bytes, not semantic/AI arbitration.
contract AgentNotaryEscrow is ReentrancyGuard {
    using SafeERC20 for IERC20;
    uint256 public constant FIXED_FEE = 5000; // USDC has 6 decimals
    uint256 public constant MAX_AMOUNT = 1000 * 1e6;
    IERC20 public immutable token;
    address public immutable treasury;
    enum State { None, Locked, Settled, Rejected, Expired }
    struct Deal {
        address buyer;
        address seller;
        uint256 amount;
        uint256 deadline;
        bytes32 expectedHash;
        bytes32 deliveredHash;
        State state;
    }
    mapping(bytes32 => Deal) public deals;
    event Locked(bytes32 indexed id, address indexed buyer, address indexed seller, uint256 amount, uint256 total, uint256 deadline, bytes32 expectedHash);
    event Finalized(bytes32 indexed id, State state, uint256 sellerPayout, uint256 fee, uint256 refund, bytes32 deliveredHash);

    constructor(address token_, address treasury_) {
        require(block.chainid == 421614 || block.chainid == 31337 || block.chainid == 131277322940537, "testnet only");
        require(token_.code.length > 0 && treasury_ != address(0) && treasury_ != address(this), "bad configuration");
        require(IERC20Metadata(token_).decimals() == 6, "6 decimals required");
        if (block.chainid == 421614) require(token_ == 0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d, "wrong test USDC");
        token = IERC20(token_);
        treasury = treasury_;
    }

    function quote(uint256 amount) public pure returns (uint256 total, uint256 fee, uint256 payout) {
        require(amount > 0 && amount <= MAX_AMOUNT, "bad amount");
        uint256 commission = amount * 150 / 10000; // floor to one micro-USDC
        return (amount + FIXED_FEE, commission + FIXED_FEE, amount - commission);
    }

    function lock(bytes32 salt, address seller, uint256 amount, bytes32 expectedHash, uint256 deadline) external nonReentrant returns (bytes32 id) {
        require(seller != address(0) && seller != msg.sender && seller != address(this), "bad seller");
        require(expectedHash != bytes32(0), "missing hash");
        require(deadline > block.timestamp && deadline <= block.timestamp + 7 days, "bad deadline");
        id = keccak256(abi.encode(msg.sender, salt));
        require(deals[id].state == State.None, "duplicate deal");
        (uint256 total,,) = quote(amount);
        deals[id] = Deal(msg.sender, seller, amount, deadline, expectedHash, bytes32(0), State.Locked);
        uint256 beforeBalance = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), total);
        require(token.balanceOf(address(this)) == beforeBalance + total, "unsupported token transfer");
        emit Locked(id, msg.sender, seller, amount, total, deadline, expectedHash);
    }

    function deliver(bytes32 id, bytes calldata payload) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp < d.deadline, "expired");
        require(payload.length > 0 && payload.length <= 4096, "bad payload length");
        bytes32 digest = keccak256(payload);
        d.deliveredHash = digest;
        uint256 fee;
        uint256 payout;
        uint256 refund;
        if (digest == d.expectedHash) {
            d.state = State.Settled;
            (,fee,payout) = quote(d.amount);
            token.safeTransfer(d.seller, payout);
        } else {
            d.state = State.Rejected;
            fee = FIXED_FEE;
            refund = d.amount;
            token.safeTransfer(d.buyer, refund);
        }
        token.safeTransfer(treasury, fee);
        emit Finalized(id, d.state, payout, fee, refund, digest);
    }

    /// @notice Anyone can trigger expiry; funds always return to the original buyer.
    function refundExpired(bytes32 id) external nonReentrant {
        Deal storage d = deals[id];
        require(d.state == State.Locked, "not locked");
        require(block.timestamp >= d.deadline, "not expired");
        d.state = State.Expired;
        uint256 refund = d.amount + FIXED_FEE; // no arbitration occurred
        token.safeTransfer(d.buyer, refund);
        emit Finalized(id, d.state, 0, 0, refund, bytes32(0));
    }
}
