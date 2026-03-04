// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
    Minimal TRC20 / ERC20 interface
*/
interface IToken {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

/*
    ReentrancyGuard (lightweight)
*/
abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;

    uint256 private _status = _NOT_ENTERED;

    modifier nonReentrant() {
        require(_status != _ENTERED, "Reentrancy");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

/*
    Production-grade PayoutAndFeesExecutor
*/
contract PayoutAndFeesExecutor is ReentrancyGuard {

    // ================================
    // Storage
    // ================================

    address public owner;
    mapping(address => uint256) public nonces;
    uint256 public maxBatchSize = 10;

    constructor() {
        owner = msg.sender;
    }

    // ================================
    // Events
    // ================================

    event PayoutAndFeesExecuted(
        address indexed fromAddress,
        address indexed token,
        address indexed mainRecipient,
        uint256 mainAmount,
        uint256 feeRecipientsCount,
        uint256 totalFeesAmount
    );

    event MaxBatchSizeUpdated(uint256 newSize);

    // ================================
    // Admin (optional)
    // ================================

    function setMaxBatchSize(uint256 newSize) external {
        require(msg.sender == owner, "OnlyOwner");
        require(newSize > 0 && newSize <= 50, "Invalid size");
        maxBatchSize = newSize;
        emit MaxBatchSizeUpdated(newSize);
    }

    // ================================
    // Main Function
    // ================================

    function executePayoutAndFees(
        address token,
        uint256 nonce,
        address mainRecipient,
        uint256 mainAmount,
        address[] calldata feeRecipients,
        uint256[] calldata feeAmounts
    ) external nonReentrant {

        require(token != address(0) && mainRecipient != address(0), "ZeroAddress");
        require(mainAmount > 0, "ZeroAmount");
        require(nonces[msg.sender] == nonce, "BadNonce");
        require(feeRecipients.length == feeAmounts.length, "FeeLengthMismatch");
        require(feeRecipients.length <= maxBatchSize, "TooManyFees");
        require(_isContract(token), "NotContract");

        nonces[msg.sender]++;

        uint256 totalFees;

        // Main transfer
        _safeTransferFrom(token, msg.sender, mainRecipient, mainAmount);

        // Fee transfers
        for (uint256 i = 0; i < feeRecipients.length; ) {

            address recipient = feeRecipients[i];
            uint256 amount = feeAmounts[i];

            require(recipient != address(0), "ZeroAddress");
            require(amount > 0, "ZeroAmount");

            totalFees += amount;

            _safeTransferFrom(token, msg.sender, recipient, amount);

            unchecked { ++i; }
        }

        emit PayoutAndFeesExecuted(
            msg.sender,
            token,
            mainRecipient,
            mainAmount,
            feeRecipients.length,
            totalFees
        );
    }

    // ================================
    // Internal Safe Transfer
    // ================================

    function _safeTransferFrom(
        address token,
        address from,
        address to,
        uint256 value
    ) internal {

        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(
                IToken.transferFrom.selector,
                from,
                to,
                value
            )
        );

        require(success, "Insufficient balance or allowance");

        if (data.length > 0) {
            require(abi.decode(data, (bool)), "Insufficient balance or allowance");
        }
    }

    function _isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }
}