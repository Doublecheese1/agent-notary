// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import "@openzeppelin/contracts/interfaces/IERC1271.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @notice Immutable 2-of-3 validation quorum for one validator policy epoch.
/// To rotate a signer, deploy a new quorum and configure it for future deals.
/// Existing deals keep the quorum address stored when they were funded.
contract AgentNotaryValidatorQuorum is IERC1271 {
    bytes4 private constant MAGIC_VALUE = IERC1271.isValidSignature.selector;
    bytes4 private constant INVALID_VALUE = 0xffffffff;

    address[3] public signers;
    mapping(address => bool) public isSigner;

    constructor(address signerA, address signerB, address signerC) {
        require(signerA != address(0) && signerB != address(0) && signerC != address(0), "signer required");
        require(signerA != signerB && signerA != signerC && signerB != signerC, "duplicate signer");
        signers = [signerA, signerB, signerC];
        isSigner[signerA] = true;
        isSigner[signerB] = true;
        isSigner[signerC] = true;
    }

    /// @dev signature is abi.encode(bytes[]), containing signatures from two distinct members.
    function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4) {
        bytes[] memory signatures = abi.decode(signature, (bytes[]));
        if (signatures.length < 2 || signatures.length > 3) return INVALID_VALUE;

        address[] memory seen = new address[](signatures.length);
        uint256 valid;
        for (uint256 i = 0; i < signatures.length; i++) {
            (address recovered, ECDSA.RecoverError error,) = ECDSA.tryRecover(hash, signatures[i]);
            if (error != ECDSA.RecoverError.NoError || !isSigner[recovered]) return INVALID_VALUE;
            for (uint256 j = 0; j < valid; j++) {
                if (seen[j] == recovered) return INVALID_VALUE;
            }
            seen[valid] = recovered;
            valid += 1;
        }
        return valid >= 2 ? MAGIC_VALUE : INVALID_VALUE;
    }
}
