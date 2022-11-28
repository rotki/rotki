import pytest

from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1']])  # noqa: E501
def test_v2_swap(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x35dd639ba80940cb14d79c965002a11ea2aef17bbf1f1b85cc03c336da1ddebe
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x35dd639ba80940cb14d79c965002a11ea2aef17bbf1f1b85cc03c336da1ddebe'
    user_address = string_to_evm_address('0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0xBA12222222228d8Ba445958a75a0704d566BF2C8'),
        value=(FVal('0.001') * EXP18).to_int(exact=True),
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x52bbbe2900000000000000000000000000000000000000000000000000000000000000e000000000000000000000000020a1cf262cd3a42a50d226fd728104119e6fd0a1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020a1cf262cd3a42a50d226fd728104119e6fd0a100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001095fc3cb88f879a0000000000000000000000000000000000000000000000000000000063848296c6a5032dc4bf638e15b4a66bc718ba7ba474ff73000200000000000000000004000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006b175474e89094c44da98b954eedeac495271d0f00000000000000000000000000000000000000000000000000038d7ea4c6800000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=91,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000038d7ea4c6800000000000000000000000000000000000000000000000000010c0749f9f7289bb'),  # noqa: E501
                address=string_to_evm_address('0xBA12222222228d8Ba445958a75a0704d566BF2C8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b'),  # noqa: E501
                    hexstring_to_bytes('0xc6a5032dc4bf638e15b4a66bc718ba7ba474ff73000200000000000000000004'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=95,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000038d7ea4c68000'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ba12222222228d8ba445958a75a0704d566bf2c8'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=98,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000010c0749f9f7289bb'),  # noqa: E501
                address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ba12222222228d8ba445958a75a0704d566bf2c8'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000020a1cf262cd3a42a50d226fd728104119e6fd0a1'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)


@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])  # noqa: E501
def test_v1_join(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xb9dff9df4e3838c75d354d62c4596d94e5eb8904e07cee07a3b7ffa611c05544
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xb9dff9df4e3838c75d354d62c4596d94e5eb8904e07cee07a3b7ffa611c05544'
    user_address = string_to_evm_address('0x7716a99194d758c8537F056825b75Dd0C8FDD89f')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x13830EB6444768cCea2C9d41308195Ceb18eF772'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x1cff79cd000000000000000000000000de4a25a0b9589689945d842c5ba0cf4f0d4eb3ac00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000084c1762b1500000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc200000000000000000000000000000000000000000000000000b1a2bc2ec50000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=327,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000b1a2bc2ec50000'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000013830eb6444768ccea2c9d41308195ceb18ef772'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=330,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000b1a2bc2ec50000'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x63982df10efd8dfaaaa0fcc7f50b2d93b7cba26ccc48adee2873220d485dc39a'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000013830eb6444768ccea2c9d41308195ceb18ef772'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=331,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000973c4c3b85fd25'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=334,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000973c4c3b85fd25'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000013830eb6444768ccea2c9d41308195ceb18ef772'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)



@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])  # noqa: E501
def test_v1_exit(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xfa1dfeb83480e51a15137a93cb0eba9ac92c1b6b0ee0bd8551a422c1ed83695b
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xfa1dfeb83480e51a15137a93cb0eba9ac92c1b6b0ee0bd8551a422c1ed83695b'
    user_address = string_to_evm_address('0x7716a99194d758c8537F056825b75Dd0C8FDD89f')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x13830EB6444768cCea2C9d41308195Ceb18eF772'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x1cff79cd000000000000000000000000de4a25a0b9589689945d842c5ba0cf4f0d4eb3ac00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000084c1762b1500000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc200000000000000000000000000000000000000000000000000b1a2bc2ec50000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=90,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000973c4c3b85fd25'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=93,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000a548a89577b3417'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe74c91552b64c2e2e7bd255639e004e693bd3e1d01cc33e65610b86afcc1ffed'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ba100000625a3754423978a60c9317c58a424e3d'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=94,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000a548a89577b3417'),  # noqa: E501
                address=string_to_evm_address('0xba100000625a3754423978a60c9317c58a424e3D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=95,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000025f7e7982d4f66'),  # noqa: E501
                address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe74c91552b64c2e2e7bd255639e004e693bd3e1d01cc33e65610b86afcc1ffed'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=96,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000025f7e7982d4f66'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000059a19d8c652fa0284f44113d0ff9aba70bd46fb4'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007716a99194d758c8537f056825b75dd0c8fdd89f'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
