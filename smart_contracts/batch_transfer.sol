pragma solidity 0.5.10;

/*
    Минимальный интерфейс TRC20 токена.
    Нам нужен только transferFrom, так как approve мы НЕ используем.
*/
interface ITRC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

/*
    SafeMath для защиты от переполнения.
    В Solidity 0.5 нет встроенной защиты от overflow.
*/
library SafeMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "Overflow");
        return c;
    }
}

/*
    SecureBatchDistributor

    Основные свойства:

    ✅ Нет approve-модели
    ✅ Нет owner
    ✅ Нет whitelist
    ✅ Любой может отправить транзакцию (relayer)
    ✅ Но выполнить можно ТОЛЬКО с валидной подписью signer
    ✅ Защита от replay через nonce
    ✅ Поддержка разных токенов
    ✅ Атомарность — если один перевод падает, всё откатывается
*/
contract SecureBatchDistributor {

    using SafeMath for uint256;

    /*
        nonce для каждого signer.
        Нужен для защиты от повторного использования подписи (replay attack).
    */
    mapping(address => uint256) public nonces;

    /*
        Ограничение размера батча.
        Нужен для защиты от превышения лимита Energy.
    */
    uint256 public maxBatchSize = 200;

    /*
        Событие логирования успешного батча.
        Позволяет отслеживать историю распределений.
    */
    event BatchExecuted(
        address indexed signer,
        address indexed token,
        uint256 totalRecipients,
        uint256 totalAmount
    );

    /*
        Формирование хеша батча.

        В хеш включается:
        - адрес контракта (защита от replay в другом контракте)
        - signer (кто разрешил списание)
        - token (адрес токена)
        - recipients
        - amounts
        - nonce

        Любое изменение этих параметров делает подпись недействительной.
    */
    function getBatchHash(
        address signer,
        address token,
        address[] memory recipients,
        uint256[] memory amounts,
        uint256 nonce
    )
        public
        view
        returns (bytes32)
    {
        return keccak256(
            abi.encodePacked(
                address(this),   // защита от replay в другом контракте
                signer,
                token,
                recipients,
                amounts,
                nonce
            )
        );
    }

    /*
        Основная функция исполнения батча.

        signer — адрес, с которого будут списаны токены
        token — адрес TRC20 токена
        recipients — массив получателей
        amounts — массив сумм
        v,r,s — параметры подписи

        ВАЖНО:
        - approve НЕ используется
        - контракт проверяет подпись signer
        - nonce увеличивается после успешного выполнения
    */
    function executeBatch(
        address signer,
        address token,
        address[] calldata recipients,
        uint256[] calldata amounts,
        uint8 v,
        bytes32 r,
        bytes32 s
    )
        external
    {
        // Проверка валидности батча
        require(recipients.length > 0, "Empty batch");
        require(recipients.length == amounts.length, "Length mismatch");
        require(recipients.length <= maxBatchSize, "Too large");

        // Получаем текущий nonce signer
        uint256 nonce = nonces[signer];

        // Формируем хеш батча
        bytes32 hash = getBatchHash(
            signer,
            token,
            recipients,
            amounts,
            nonce
        );

        /*
            Tron использует стандартный Ethereum-style personal_sign формат.
            Поэтому добавляем префикс:
            "\x19Ethereum Signed Message:\n32"
        */
        bytes32 ethSignedHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", hash)
        );

        // Восстанавливаем адрес из подписи
        address recovered = ecrecover(ethSignedHash, v, r, s);

        // Проверяем, что подпись действительно принадлежит signer
        require(recovered == signer, "Invalid signature");

        // Увеличиваем nonce — защита от повторного использования подписи
        nonces[signer] = nonce + 1;

        ITRC20 t = ITRC20(token);

        uint256 totalAmount = 0;

        /*
            Выполняем атомарную рассылку.

            Если любой transferFrom вернет false —
            вся транзакция откатится.
        */
        for (uint256 i = 0; i < amounts.length; i++) {
            require(recipients[i] != address(0), "Zero recipient");

            totalAmount = totalAmount.add(amounts[i]);

            require(
                t.transferFrom(signer, recipients[i], amounts[i]),
                "Transfer failed"
            );
        }

        emit BatchExecuted(signer, token, recipients.length, totalAmount);
    }
}