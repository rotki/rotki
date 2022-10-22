import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import EXP18, ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x3CAdf2cA458376a6a5feA2EF3612346037D5A787']])  # noqa: E501
def test_uniswap_v2_swap(database, ethereum_manager, eth_transactions):
    """Data for swap
    https://etherscan.io/tx/0x67cf6c4ce5078f9750a14afd2f5070c327caf8c5180bdee2be59644ac59974e1/
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x67cf6c4ce5078f9750a14afd2f5070c327caf8c5180bdee2be59644ac59974e1'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=150000000000000000,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x7ff36ab50000000000000000000000000000000000000000000000165e98da19714be59e00000000000000000000000000000000000000000000000000000000000000800000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787000000000000000000000000000000000000000000000000000000006114d38c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d0000000000000000000000000853d955acef822db058eb8505911ed77f175b99e'),  # noqa: E501
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=508,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000214e8348c4f0000'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=509,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000001be99523'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=511,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000214e8348c4f0000000000000000000000000000000000000000000000000000000000001be995230000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=514,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000007aa72c2d7bbdda13f'),  # noqa: E501
                address=string_to_evm_address('0xf4aD61dB72f114Be877E87d62DC5e7bd52DF4d9B'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009bac32d4f3322bc7588bb119283bad7073145355'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=516,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001be99523000000000000000000000000000000000000000000000007aa72c2d7bbdda13f0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x9BAC32D4f3322bC7588BB119283bAd7073145355'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=517,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001918f7e61d476779dd'),  # noqa: E501
                address=string_to_evm_address('0x853d955aCEf822Db058eb8505911ED77F175b99e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e1573b9d29e2183b1af0e743dc2754979a40d237'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=519,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000007aa72c2d7bbdda13f0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001918f7e61d476779dd'),  # noqa: E501
                address=string_to_evm_address('0xE1573B9D29e2183B1AF0e743Dc2754979A40D237'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
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

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.15'), usd_value=ZERO),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Swap 0.15 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=519,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x853d955aCEf822Db058eb8505911ED77F175b99e'),
            balance=Balance(amount=FVal('462.967761432322996701'), usd_value=ZERO),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Receive 462.967761432322996701 FRAX in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x3CAdf2cA458376a6a5feA2EF3612346037D5A787']])  # noqa: E501
def test_uniswap_v2_swap_eth_returned(database, ethereum_manager, eth_transactions):
    """Test a transaction where eth is swapped and some of it is returned due to change in price"""
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x20ecc226c438a8803a6195d8031ae7dd97a27351e6b7429621b36194121b9b76'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
        to_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        value=FVal('1.59134916748576351') * EXP18,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xfb3bdb410000000000000000000000000000000000000000204fce5e3e2502611000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a78700000000000000000000000000000000000000000000000000000000616ed7a40000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000761d38e5ddf6ccf6cf7c55759d5210750b5d60f3'),  # noqa: E501
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=306,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000015f8d0c01dad329c'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b73644935b8e68019ac6356c40661e1bc315860'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=307,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000204fce5e3e25026110000000'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b73644935b8e68019ac6356c40661e1bc315860'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=309,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000015f8d0c01dad329c0000000000000000000000000000000000000000204fce5e3e250261100000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003cadf2ca458376a6a5fea2ef3612346037d5a787'),  # noqa: E501
                ],
            ),
        ],
    )

    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        trace_id=27,
        timestamp=Timestamp(1646375440),
        block_number=14351442,
        from_address='0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        to_address='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
        value=FVal('0.008104374914845978') * EXP18,
    )

    dbethtx = DBEthTx(database)
    decoder = EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        transactions=eth_transactions,
        msg_aggregator=msg_aggregator,
    )
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx], relevant_address='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787')  # noqa: E501
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.008104374914845978),
                usd_value=ZERO,
            ),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Refund of 0.008104374914845978 ETH in uniswap-v2 due to price change',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=2,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('1.59134916748576351'), usd_value=ZERO),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Swap 1.59134916748576351 ETH in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=310,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            balance=Balance(amount=FVal('10000000000000000000000'), usd_value=ZERO),
            location_label='0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',
            notes='Receive 10000000000000000000000 USDC in uniswap-v2 from 0x3CAdf2cA458376a6a5feA2EF3612346037D5A787',  # noqa: E501
            counterparty=CPT_UNISWAP_V2,
        ),
    ]
    assert events == expected_events
