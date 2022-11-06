import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EvmTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f']])  # noqa: E501
def test_pickle_deposit(database, ethereum_manager, eth_transactions):
    """Data for deposit taken from
    https://etherscan.io/tx/0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address='0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f',
        to_address='0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xb6b55f250000000000000000000000000000000000000000000000312ebe013bcd5d6fed'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=259,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000312ebe013bcd5d6fed'),  # noqa: E501
                address=string_to_evm_address('0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000f1a748cdf53bbad378ce2c4429463d01cce0c3f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4ebc2c371182deea04b2264b9ff5ac4f0159c69'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=261,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001e67da0f130b2d9371'),  # noqa: E501
                address=string_to_evm_address('0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000f1a748cdf53bbad378ce2c4429463d01cce0c3f'),  # noqa: E501
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
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd',
            ),
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
            location_label='0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd',
            ),
            sequence_index=260,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken('eip155:1/erc20:0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
            balance=Balance(amount=FVal('907.258590539447889901'), usd_value=ZERO),
            location_label='0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f',
            notes='Deposit 907.258590539447889901 LOOKS in pickle contract',
            counterparty='pickle finance',
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd',
            ),
            sequence_index=262,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
            balance=Balance(amount=FVal('560.885632516582380401'), usd_value=ZERO),
            location_label='0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f',
            notes='Receive 560.885632516582380401 pLOOKS after depositing in pickle contract',
            counterparty='pickle finance',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xC7Dc4Cd171812a441A30472219d390f4F15f6070']])  # noqa: E501
def test_pickle_withdraw(database, ethereum_manager, eth_transactions):
    """Data for withdraw taken from
    https://etherscan.io/tx/0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14355951,
        from_address='0xC7Dc4Cd171812a441A30472219d390f4F15f6070',
        to_address='0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x853828b6'),
        nonce=23,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=105,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000d4f4e1608c485628b'),  # noqa: E501
                address=string_to_evm_address('0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c7dc4cd171812a441a30472219d390f4f15f6070'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=106,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000015da18947013228f17'),  # noqa: E501
                address=string_to_evm_address('0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4ebc2c371182deea04b2264b9ff5ac4f0159c69'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c7dc4cd171812a441a30472219d390f4f15f6070'),  # noqa: E501
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
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab',
            ),
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
            location_label='0xC7Dc4Cd171812a441A30472219d390f4F15f6070',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab',
            ),
            sequence_index=106,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
            balance=Balance(amount=FVal('245.522202162316534411'), usd_value=ZERO),
            location_label='0xC7Dc4Cd171812a441A30472219d390f4F15f6070',
            notes='Return 245.522202162316534411 pLOOKS to the pickle contract',
            counterparty='pickle finance',
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab',
            ),
            sequence_index=107,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken('eip155:1/erc20:0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
            balance=Balance(amount=FVal('403.097099656688209687'), usd_value=ZERO),
            location_label='0xC7Dc4Cd171812a441A30472219d390f4F15f6070',
            notes='Unstake 403.097099656688209687 LOOKS from the pickle contract',
            counterparty='pickle finance',
        )]
    assert events == expected_events
