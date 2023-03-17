import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BAL, A_BPT, A_DAI, A_ETH, A_USDC, A_WETH
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1']])  # noqa: E501
def test_balancer_v2_swap(database, ethereum_manager, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x35dd639ba80940cb14d79c965002a11ea2aef17bbf1f1b85cc03c336da1ddebe
    """
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
        chain_id=ChainID.ETHEREUM,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        chain_id=ChainID.ETHEREUM,
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

    dbethtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder = EthereumTransactionDecoder(
            database=database,
            ethereum_inquirer=ethereum_manager.node_inquirer,
            transactions=eth_transactions,
        )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00393701451')),
            location_label='0x20A1CF262Cd3A42a50D226fD728104119e6fD0a1',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.001)),
            location_label=user_address,
            notes='Swap 0.001 ETH in Balancer v2',
            counterparty=CPT_BALANCER_V2,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=100,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(amount=FVal('1.207092929058998715')),
            location_label=user_address,
            notes='Receive 1.207092929058998715 DAI from Balancer v2',
            counterparty=CPT_BALANCER_V2,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])  # noqa: E501
def test_balancer_v1_join(database, ethereum_manager, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xb9dff9df4e3838c75d354d62c4596d94e5eb8904e07cee07a3b7ffa611c05544
    """
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
        chain_id=ChainID.ETHEREUM,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        chain_id=ChainID.ETHEREUM,
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

    dbethtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder = EthereumTransactionDecoder(
            database=database,
            ethereum_inquirer=ethereum_manager.node_inquirer,
            transactions=eth_transactions,
        )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00393701451')),
            location_label='0x7716a99194d758c8537F056825b75Dd0C8FDD89f',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=328,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_BPT,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label='0x7716a99194d758c8537F056825b75Dd0C8FDD89f',
            notes='Receive 0.042569019597126949 BPT from a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data={'deposit_events_num': 1},
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=335,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal(0.05)),
            location_label='0x7716a99194d758c8537F056825b75Dd0C8FDD89f',
            notes='Deposit 0.05 WETH to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x7716a99194d758c8537F056825b75Dd0C8FDD89f']])  # noqa: E501
def test_balancer_v1_exit(database, ethereum_manager, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xfa1dfeb83480e51a15137a93cb0eba9ac92c1b6b0ee0bd8551a422c1ed83695b
    """
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
        chain_id=ChainID.ETHEREUM,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
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

    dbethtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbethtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        decoder = EthereumTransactionDecoder(
            database=database,
            ethereum_inquirer=ethereum_manager.node_inquirer,
            transactions=eth_transactions,
        )
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00393701451')),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=91,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_BPT,
            balance=Balance(amount=FVal('0.042569019597126949')),
            location_label=user_address,
            notes='Return 0.042569019597126949 BPT to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data={'withdrawal_events_num': 2},
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=95,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_BAL,
            balance=Balance(amount=FVal('0.744372160905819159')),
            location_label=user_address,
            notes='Receive 0.744372160905819159 BAL after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=97,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal('0.010687148200906598')),
            location_label=user_address,
            notes='Receive 0.010687148200906598 WETH after removing liquidity from a Balancer v1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x549C0421c69Be943A2A60e76B19b4A801682cBD3']])
def test_deposit_with_excess_tokens(database, ethereum_inquirer, ethereum_accounts):
    """Verify that when a refund is made for a deposit in balancer v1 this is properly decoded"""
    user_address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x22162f5c71261421db82a03ba4ad13725ef4fe9639c62bf6702538f980fbe7ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.01452447')),
            location_label=user_address,
            notes='Burned 0.01452447 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=131,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x72Cd8f4504941Bf8c5a21d1Fd83A96499FD71d2C'),
            balance=Balance(amount=FVal('1675.495956074927519908')),
            location_label=user_address,
            notes='Receive 1675.495956074927519908 BPT from a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data={'deposit_events_num': 4},
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=132,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('131578.947368421052491563')),
            location_label=user_address,
            notes='Deposit 131578.947368421052491563 mUSD to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=134,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('131421.703252')),
            location_label=user_address,
            notes='Deposit 131421.703252 USDC to a Balancer v1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=144,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('6578.947368421052624578')),
            location_label=user_address,
            notes='Refunded 6578.947368421052624578 mUSD after depositing in Balancer V1 pool',  # noqa: E501
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=145,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('6571.085163')),
            location_label=user_address,
            notes='Refunded 6571.085163 USDC after depositing in Balancer V1 pool',
            counterparty=CPT_BALANCER_V1,
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=146,
            timestamp=TimestampMS(1593186380000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xe2f2a5C287993345a840Db3B0845fbC70f5935a5'),
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=user_address,
            notes='Approve 115792089237316195423570985000000000000000000000000000000000 mUSD of 0x549C0421c69Be943A2A60e76B19b4A801682cBD3 for spending by 0x9ED47950144e51925166192Bf0aE95553939030a',  # noqa: E501
            counterparty='0x9ED47950144e51925166192Bf0aE95553939030a',
            identifier=None,
            extra_data=None,
        ),
    ]
