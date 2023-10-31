from typing import Any, Optional, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.accounting.structures.eth2 import EthDepositEvent, EthWithdrawalEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import (
    EthDepositEventFilterQuery,
    EvmEventFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import (
    make_ethereum_event,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.types import (
    ChainID,
    EVMTxHash,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)


def test_get_customized_event_identifiers(database):
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                event_identifier=deserialize_evm_tx_hash('0x75ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                HistoryEvent(
                    event_identifier=deserialize_evm_tx_hash('0x15ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                    sequence_index=1,
                    timestamp=TimestampMS(1),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(1),
                ), HistoryEvent(
                    event_identifier=deserialize_evm_tx_hash('0x25ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                    sequence_index=1,
                    timestamp=TimestampMS(2),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(2),
                ),
            ],
        )
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                event_identifier=deserialize_evm_tx_hash('0x35ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                sequence_index=1,
                timestamp=TimestampMS(3),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )

    with db.db.conn.read_ctx() as cursor:
        assert db.get_customized_event_identifiers(cursor, chain_id=None) == [1, 4]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.ETHEREUM) == [1]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.OPTIMISM) == [4]


def add_history_events_to_db(db: DBHistoryEvents, data: dict[int, tuple[str, TimestampMS, FVal, Optional[dict]]]) -> None:  # noqa: E501
    """Helper function to create HistoryEvent fixtures"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=HistoryEvent(
                    event_identifier=entry[0],
                    sequence_index=1,
                    timestamp=entry[1],
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(entry[2]),
                ),
                mapping_values=entry[3],
            )


def add_evm_events_to_db(db: DBHistoryEvents, data: dict[int, tuple[EVMTxHash, TimestampMS, FVal, str, EvmProduct, str, Optional[dict]]]) -> None:  # noqa: E501
    """Helper function to create EvmEvent fixtures"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_hash=entry[0],
                    sequence_index=1,
                    timestamp=entry[1],
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(entry[2]),
                    counterparty=entry[3],
                    product=entry[4],
                    address=string_to_evm_address(entry[5]),
                ),
                mapping_values=entry[6],
            )


def add_eth2_events_to_db(db: DBHistoryEvents, data: dict[int, tuple[EVMTxHash, TimestampMS, FVal, str, Optional[dict]]]) -> None:  # noqa: E501
    """Helper function to create fixtures for various Beacon chain staking events"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EthDepositEvent(
                    identifier=1,
                    tx_hash=entry[0],
                    validator_index=42,
                    sequence_index=1,
                    timestamp=entry[1],
                    balance=Balance(entry[2]),
                    depositor=string_to_evm_address(entry[3]),
                ),
                mapping_values=entry[4],
            )


def test_read_write_events_from_db(database):
    db = DBHistoryEvents(database)
    history_data = {  # mapping of identifier to unique data
        1: ('TEST1', TimestampMS(1), ONE, None),
        2: ('TEST2', TimestampMS(2), FVal(2), None),
        3: ('TEST3', TimestampMS(3), FVal(3), None),
    }
    evm_data = {  # mapping of identifier to unique data
        4: (make_evm_tx_hash(), TimestampMS(4), FVal(4), 'gas', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        5: (make_evm_tx_hash(), TimestampMS(5), FVal(5), 'liquity', EvmProduct.STAKING, '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        6: (make_evm_tx_hash(), TimestampMS(6), FVal(6), 'aave', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4', None),  # noqa: E501
        7: (make_evm_tx_hash(), TimestampMS(7), FVal(7), 'compound', EvmProduct.POOL, '0x19222290DD7278Aa3Ddd389Cc1E1d165CC4BAf34', None),  # noqa: E501
    }

    add_history_events_to_db(db, history_data)
    add_evm_events_to_db(db, evm_data)

    # args for creating filter queries
    filter_query_args = [
        (HistoryEventFilterQuery, None),
        (HistoryEventFilterQuery, IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT])),  # noqa: E501
        (EvmEventFilterQuery, IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT])),
    ]

    with db.db.conn.read_ctx() as cursor:
        for filter_query, entry_types in filter_query_args:
            all_events = db.get_history_events(cursor, filter_query.make(entry_types=entry_types), True, False)  # noqa: E501
            for event in all_events:
                if isinstance(event, HistoryEvent):
                    data_entry = history_data[event.identifier]
                    expected_event = HistoryEvent(
                        identifier=event.identifier,
                        event_identifier=data_entry[0],
                        sequence_index=1,
                        timestamp=data_entry[1],
                        location=Location.ETHEREUM,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_ETH,
                        balance=Balance(data_entry[2]),
                    )
                else:
                    data_entry = evm_data[event.identifier]
                    expected_event = EvmEvent(
                        identifier=event.identifier,
                        tx_hash=data_entry[0],
                        sequence_index=1,
                        timestamp=data_entry[1],
                        location=Location.ETHEREUM,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_ETH,
                        balance=Balance(data_entry[2]),
                        counterparty=data_entry[3],
                        product=data_entry[4],
                        address=data_entry[5],
                    )
                assert event == expected_event


def test_read_write_customized_events_from_db(database: DBHandler) -> None:
    """Tests filtering for fetching only the customized events"""
    db = DBHistoryEvents(database)
    history_data = {
        1: ('TEST1', TimestampMS(1000), ONE, None),
        2: ('TEST2', TimestampMS(2000), FVal(2), {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED}),  # noqa: E501
        3: ('TEST3', TimestampMS(3000), FVal(3), {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED}),  # noqa: E501
    }

    tx_hashes = [make_evm_tx_hash() for x in range(5)]
    evm_data = {
        4: (tx_hashes[0], TimestampMS(4), FVal(4), 'gas', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        5: (tx_hashes[1], TimestampMS(5), FVal(5), 'liquity', EvmProduct.STAKING, '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        6: (tx_hashes[2], TimestampMS(6), FVal(6), 'aave', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4', {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED}),  # noqa: E501
    }
    eth2_data = {
        7: (tx_hashes[3], TimestampMS(7), FVal(6), '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        8: (tx_hashes[4], TimestampMS(8), FVal(8), '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED}),  # noqa: E501
    }

    add_history_events_to_db(db, history_data)
    add_evm_events_to_db(db, evm_data)
    add_eth2_events_to_db(db, eth2_data)

    filter_query_args: list[
        tuple[
            type[Union[HistoryEventFilterQuery, EvmEventFilterQuery, EthDepositEventFilterQuery]],
            dict[str, Any],
        ]
    ] = [
        (HistoryEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]), 'customized_events_only': True}),  # noqa: E501
        (HistoryEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]), 'customized_events_only': True, 'from_ts': Timestamp(3)}),  # noqa: E501
        (EvmEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT]), 'customized_events_only': True}),  # noqa: E501
        (EthDepositEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_DEPOSIT_EVENT]), 'customized_events_only': True}),  # noqa: E501
    ]
    expected_identifiers = [
        ['TEST2', 'TEST3'],
        ['TEST3'],
        [tx_hashes[2]],
        [tx_hashes[4]],
    ]

    with db.db.conn.read_ctx() as cursor:
        for (filtering_class, filter_args), expected_ids in zip(filter_query_args, expected_identifiers):  # noqa: E501
            events = db.get_history_events(
                cursor=cursor,
                filter_query=filtering_class.make(**filter_args),
                has_premium=True,
                group_by_event_ids=False,
            )
            filtered_ids = [x.tx_hash if isinstance(x, EvmEvent) else x.event_identifier for x in events]  # noqa: E501
            assert filtered_ids == expected_ids


def test_delete_last_event(database):
    """
    Test that if last event in a group is being deleted and it's not an EVM event,
    then the deletion is allowed.
    """
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        withdrawal_event_identifier = db.add_history_event(
            write_cursor=write_cursor,
            event=EthWithdrawalEvent(
                validator_index=1000,
                timestamp=TimestampMS(1683115229000),
                balance=Balance(amount=ONE),
                withdrawal_address=make_evm_address(),
                is_exit=True,
            ),
        )
        evm_event_identifier = db.add_history_event(
            write_cursor=write_cursor,
            event=make_ethereum_event(index=1),
        )
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)) == 2

    msg = db.delete_history_events_by_identifier(identifiers=[withdrawal_event_identifier])
    assert msg is None
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)) == 1, 'Only the EVM event should be left'  # noqa: E501

    msg = db.delete_history_events_by_identifier(identifiers=[evm_event_identifier])
    assert 'was the last event of a transaction' in msg
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)) == 1, 'EVM event should be left'  # noqa: E501
