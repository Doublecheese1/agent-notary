// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
contract TestUSDC is ERC20 {
    constructor() ERC20("Local test token", "TEST") { _mint(msg.sender, 1000000 * 1e6); }
    function decimals() public pure override returns (uint8) { return 6; }
}
