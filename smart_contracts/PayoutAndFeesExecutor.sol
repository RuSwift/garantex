pragma solidity 0.5.10;

/*
    Минимальный интерфейс TRC20 токена.
*/
interface ITRC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

/*
    SafeMath для защиты от переполнения (Solidity 0.5).
*/
library SafeMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "Overflow");
        return c;
    }
}

/*
    PayoutAndFeesExecutor

    Атомарная выплата: основная сумма + комиссии в одной транзакции.
    Транзакция отправляется от имени эскроу (msg.sender); 2/3 подписей
    собираются offchain (TRON multisig), затем одна подписанная транзакция
    broadcast. Контракт выполняет:
      1) transferFrom(msg.sender, mainRecipient, mainAmount)
      2) цикл transferFrom(msg.sender, feeRecipients[i], feeAmounts[i])

    Свойства:
    - Атомарность: при ошибке любого transferFrom всё откатывается
    - Replay защита через nonce
    - Ограничение размера батча комиссий (maxBatchSize)
    - Эскроу должен заранее approve(this, mainAmount + sum(feeAmounts))
*/
contract PayoutAndFeesExecutor {

    using SafeMath for uint256;

    mapping(address => uint256) public nonces;

    uint256 public maxBatchSize = 10;

    event PayoutAndFeesExecuted(
        address indexed fromAddress,
        address indexed token,
        address indexed mainRecipient,
        uint256 mainAmount,
        uint256 feeRecipientsCount,
        uint256 totalFeesAmount
    );

    /*
        executePayoutAndFees

        Вызывается транзакцией от эскроу (owner_address = escrow).
        msg.sender = эскроу, с него списываются токены.

        token          — адрес TRC20 (например USDT)
        nonce          — текущий nonce эскроу (читается с контракта перед сборкой tx)
        mainRecipient  — получатель основной суммы
        mainAmount     — основная сумма (наименьшие единицы)
        feeRecipients  — массив получателей комиссий
        feeAmounts     — массив сумм комиссий
    */
    function executePayoutAndFees(
        address token,
        uint256 nonce,
        address mainRecipient,
        uint256 mainAmount,
        address[] calldata feeRecipients,
        uint256[] calldata feeAmounts
    ) external {
        require(token != address(0), "Zero token");
        require(mainRecipient != address(0), "Zero main recipient");
        require(mainAmount > 0, "Zero main amount");
        require(nonces[msg.sender] == nonce, "Bad nonce");

        require(
            feeRecipients.length == feeAmounts.length,
            "Fee length mismatch"
        );
        require(
            feeRecipients.length <= maxBatchSize,
            "Too many fees"
        );

        nonces[msg.sender] = nonce + 1;

        ITRC20 t = ITRC20(token);

        require(
            t.transferFrom(msg.sender, mainRecipient, mainAmount),
            "Main transfer failed"
        );

        uint256 totalFees = 0;
        for (uint256 i = 0; i < feeRecipients.length; i++) {
            require(feeRecipients[i] != address(0), "Zero fee recipient");
            totalFees = totalFees.add(feeAmounts[i]);
            require(
                t.transferFrom(msg.sender, feeRecipients[i], feeAmounts[i]),
                "Fee transfer failed"
            );
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
}
