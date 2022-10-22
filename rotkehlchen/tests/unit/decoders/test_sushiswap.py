import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EvmTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])  # noqa: E501
def test_sushiswap_single_swap(database, ethereum_manager, eth_transactions):
    """Data for swap
    https://etherscan.io/tx/0xbfe3c8a13c325a32736beb34ea170053cdbbd1740a9c3ceca52060906b7f87bd
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xbfe3c8a13c325a32736beb34ea170053cdbbd1740a9c3ceca52060906b7f87bd'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',
        to_address='0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x38ed173900000000000000000000000000000000000000000000000109dccca56ed38b8c000000000000000000000000000000000000000000000000ff1886165de79bd900000000000000000000000000000000000000000000000000000000000000a00000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef0000000000000000000000000000000000000000000000000000000060ba9a13000000000000000000000000000000000000000000000000000000000000000200000000000000000000000062b9c7356a2dc64a1969e19c23e4f579f9810aa7000000000000000000000000d533a949740bb3306d119cc777fa900ba034cd52'),  # noqa: E501
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
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000109dccca56ed38b8c'),  # noqa: E501
                address=string_to_evm_address('0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000033f6ddaea2a8a54062e021873bcaee006cdf4007'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=308,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001005f0be0b7f96826'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000033f6ddaea2a8a54062e021873bcaee006cdf4007'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=310,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000109dccca56ed38b8c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001005f0be0b7f96826'),  # noqa: E501
                address=string_to_evm_address('0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000003ba6eb0e4327b96ade6d4f3b578724208a590cef'),  # noqa: E501
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
            location_label='0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=307,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken('eip155:1/erc20:0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7'),
            balance=Balance(amount=FVal('19.157411925828275084'), usd_value=ZERO),
            location_label='0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',
            notes='Swap 19.157411925828275084 cvxCRV in sushiswap-v2 from 0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=309,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52'),
            balance=Balance(amount=FVal('18.47349725628421943'), usd_value=ZERO),
            location_label='0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',
            notes='Receive 18.47349725628421943 CRV in sushiswap-v2 from 0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',  # noqa: E501
            counterparty=CPT_SUSHISWAP_V2,
        ),
    ]
    assert events == expected_events
