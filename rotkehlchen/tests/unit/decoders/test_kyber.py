import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_CRV, A_ETH, A_USDC
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EthereumInternalTransaction,
    EthereumTransaction,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b']])  # noqa: E501
def test_kyber_legacy_old_contract(database, ethereum_manager, eth_transactions):
    """Data for trade taken from
    https://etherscan.io/tx/0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1591043988,
        block_number=10182160,
        from_address='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',
        to_address='0x818E6FECD516Ecc3849DAf6845e3EC868087B755',
        value=0,
        gas=600000,
        gas_price=22990000000,
        gas_used=527612,
        input_data=hexstring_to_bytes('0xcb3c28c7000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb480000000000000000000000000000000000000000000000000000000002aea540000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee0000000000000000000000006d379cb5ba04c09293b21bf314e7aba3ffeaaf5b8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e5f611df3b9ac000000000000000000000000f1aa99c69715f423086008eb9d06dc1e35cc504d'),  # noqa: E501
        nonce=1,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=87,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000002aea540'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000006d379cb5ba04c09293b21bf314e7aba3ffeaaf5b'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000065bf64ff5f51272f729bdcd7acfb00677ced86cd'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=93,
                data=hexstring_to_bytes('0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee0000000000000000000000000000000000000000000000000000000002aea540000000000000000000000000000000000000000000000000029a80338e28df730000000000000000000000006d379cb5ba04c09293b21bf314e7aba3ffeaaf5b000000000000000000000000000000000000000000000000029a80338e28df730000000000000000000000001670dfb52806de7789d5cf7d5c005cf7083f9a5d000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xd30ca399cb43507ecec6a629a35cf45eb98cda550c27696dcb0d8c4a3873ce6c'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000006d379cb5ba04c09293b21bf314e7aba3ffeaaf5b'),  # noqa: E501
                ],
            ),
        ],
    )
    internal_tx = EthereumInternalTransaction(
        parent_tx_hash=evmhash,
        trace_id=27,
        timestamp=Timestamp(1591043988),
        block_number=10182160,
        from_address='0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd',
        to_address='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',
        value=187603293406027635,
    )
    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx], relevant_address='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b')  # noqa: E501
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87',
            ),
            sequence_index=0,
            timestamp=1591043988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.01212979988),
                usd_value=ZERO,
            ),
            location_label='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',
            notes='Burned 0.01212979988 ETH in gas from 0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87',
            ),
            sequence_index=1,
            timestamp=1591043988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal(45), usd_value=ZERO),
            location_label='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',
            notes='Swap 45 USDC in kyber',
            counterparty='kyber legacy',
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87',
            ),
            sequence_index=89,
            timestamp=1591043988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal('0.187603293406027635'),
                usd_value=ZERO,
            ),
            location_label='0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b',
            notes='Receive 0.187603293406027635 ETH from kyber swap',
            counterparty='kyber legacy',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0']])  # noqa: E501
def test_kyber_legacy_new_contract(database, ethereum_manager, eth_transactions):
    """Data for trade taken from
    https://etherscan.io/tx/0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1644182638,
        block_number=14154915,
        from_address='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
        to_address='0x9AAb3f75489902f3a48495025729a0AF77d4b11e',
        value=0,
        gas=2784000,
        gas_price=71000000000,
        gas_used=938231,
        input_data=hexstring_to_bytes('0xae591d54000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb4800000000000000000000000000000000000000000000000000000001e52b2aa0000000000000000000000000d533a949740bb3306d119cc777fa900ba034cd520000000000000000000000005340f6faff9bf55f66c16db6bf9e020d987f87d0ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000000000000000000000000000000000000000000003ef569a751d10e0000000000000000000000000de63aef60307655405835da74ba02ce4db1a42fb000000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=41,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=349,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000001e52b2aa0'),  # noqa: E501
                address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005340f6faff9bf55f66c16db6bf9e020d987f87d0'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007c66550c9c730b6fdd4c03bc2e73c5462c5f7acc'),  # noqa: E501
                ],
            ),
            EthereumTxReceiptLog(
                log_index=369,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000083a3ee0140f345d2d8'),  # noqa: E501
                address=string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007c66550c9c730b6fdd4c03bc2e73c5462c5f7acc'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005340f6faff9bf55f66c16db6bf9e020d987f87d0'),  # noqa: E501
                ],
            ),
            EthereumTxReceiptLog(
                log_index=372,
                data=hexstring_to_bytes('0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000d533a949740bb3306d119cc777fa900ba034cd520000000000000000000000005340f6faff9bf55f66c16db6bf9e020d987f87d000000000000000000000000000000000000000000000000000000001e52b2aa0000000000000000000000000000000000000000000000083a3ee0140f345d2d8000000000000000000000000de63aef60307655405835da74ba02ce4db1a42fb0000000000000000000000000000000000000000000000000000000000000012'),  # noqa: E501
                address=string_to_evm_address('0x9AAb3f75489902f3a48495025729a0AF77d4b11e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xf724b4df6617473612b53d7f88ecc6ea983074b30960a049fcd0657ffe808083'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000005340f6faff9bf55f66c16db6bf9e020d987f87d0'),  # noqa: E501
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
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22',
            ),
            sequence_index=0,
            timestamp=1644182638000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.066614401),
                usd_value=ZERO,
            ),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Burned 0.066614401 ETH in gas from 0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22',
            ),
            sequence_index=350,
            timestamp=1644182638000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal(8139.77872), usd_value=ZERO),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Swap 8139.77872 USDC in kyber',
            counterparty='kyber legacy',
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22',
            ),
            sequence_index=370, timestamp=1644182638000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_CRV,
            balance=Balance(amount=FVal('2428.33585390706162556'), usd_value=ZERO),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Receive 2428.33585390706162556 CRV from kyber swap',
            counterparty='kyber legacy',
        ),
    ]
    assert events == expected_events
