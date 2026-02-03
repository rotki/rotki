from collections.abc import Mapping
from typing import Any
from unittest.mock import patch

import gevent
import pytest

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH_V6
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_USDC, A_USDT, A_WBTC
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import (
    EthDepositEventFilterQuery,
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.history.events.structures.eth2 import EthDepositEvent, EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import (
    make_ethereum_event,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.types import EVMTxHash, Location, Timestamp, TimestampMS, deserialize_evm_tx_hash


def test_get_event_mapping_states(database):
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier=deserialize_evm_tx_hash('0x75ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=ONE,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                HistoryEvent(
                    group_identifier=deserialize_evm_tx_hash('0x15ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                    sequence_index=1,
                    timestamp=TimestampMS(1),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ), HistoryEvent(
                    group_identifier=deserialize_evm_tx_hash('0x25ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                    sequence_index=1,
                    timestamp=TimestampMS(2),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=FVal(2),
                ),
            ],
        )
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier=deserialize_evm_tx_hash('0x35ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),
                sequence_index=1,
                timestamp=TimestampMS(3),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=ONE,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )

    with db.db.conn.read_ctx() as cursor:
        assert db.get_event_mapping_states(
            cursor=cursor,
            location=None,
        ) == {1: [HistoryMappingState.CUSTOMIZED], 4: [HistoryMappingState.CUSTOMIZED]}
        assert db.get_event_mapping_states(
            cursor=cursor,
            location=Location.ETHEREUM,
        ) == {1: [HistoryMappingState.CUSTOMIZED]}
        assert db.get_event_mapping_states(
            cursor=cursor,
            location=Location.OPTIMISM,
            mapping_state=HistoryMappingState.CUSTOMIZED,
        ) == [4]


def add_history_events_to_db(db: DBHistoryEvents, data: dict[int, tuple[str, TimestampMS, FVal, dict | None]]) -> None:  # noqa: E501
    """Helper function to create HistoryEvent fixtures"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=HistoryEvent(
                    group_identifier=entry[0],
                    sequence_index=1,
                    timestamp=entry[1],
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=entry[2],
                ),
                mapping_values=entry[3],
            )


def add_evm_events_to_db(db: DBHistoryEvents, data: Mapping[int, tuple[EVMTxHash, TimestampMS, FVal, str, str, dict | None]]) -> None:  # noqa: E501
    """Helper function to create EvmEvent fixtures"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=entry[0],
                    sequence_index=1,
                    timestamp=entry[1],
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=entry[2],
                    counterparty=entry[3],
                    address=string_to_evm_address(entry[4]),
                ),
                mapping_values=entry[5],
            )


def add_eth2_events_to_db(db: DBHistoryEvents, data: dict[int, tuple[EVMTxHash, TimestampMS, FVal, str, dict | None]]) -> None:  # noqa: E501
    """Helper function to create fixtures for various Beacon chain staking events"""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EthDepositEvent(
                    identifier=1,
                    tx_ref=entry[0],
                    validator_index=42,
                    sequence_index=1,
                    timestamp=entry[1],
                    amount=entry[2],
                    depositor=string_to_evm_address(entry[3]),
                ),
                mapping_values=entry[4],
            )


def add_eth_deposit_events_to_db(
        db: DBHistoryEvents,
        data: dict[int, tuple[EVMTxHash, TimestampMS, FVal, str, int]],
) -> None:
    """Helper function to create fixtures for eth deposit events with custom validators."""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EthDepositEvent(
                    tx_ref=entry[0],
                    validator_index=entry[4],
                    sequence_index=1,
                    timestamp=entry[1],
                    amount=entry[2],
                    depositor=string_to_evm_address(entry[3]),
                ),
            )


def add_eth_withdrawal_events_to_db(
        db: DBHistoryEvents,
        data: dict[int, tuple[int, TimestampMS, FVal, str, bool]],
) -> None:
    """Helper function to create fixtures for eth withdrawal events with custom validators."""
    with db.db.user_write() as write_cursor:
        for entry in data.values():
            db.add_history_event(
                write_cursor=write_cursor,
                event=EthWithdrawalEvent(
                    validator_index=entry[0],
                    timestamp=entry[1],
                    amount=entry[2],
                    withdrawal_address=string_to_evm_address(entry[3]),
                    is_exit=entry[4],
                ),
            )


def test_read_write_events_from_db(database):
    db = DBHistoryEvents(database)
    history_data = {  # mapping of identifier to unique data
        1: ('TEST1', TimestampMS(1), ONE, None),
        2: ('TEST2', TimestampMS(2), FVal(2), None),
        3: ('TEST3', TimestampMS(3), FVal(3), None),
    }
    evm_data = {  # mapping of identifier to unique data
        4: (make_evm_tx_hash(), TimestampMS(4), FVal(4), 'gas', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        5: (make_evm_tx_hash(), TimestampMS(5), FVal(5), 'liquity', '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        6: (make_evm_tx_hash(), TimestampMS(6), FVal(6), 'aave', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4', None),  # noqa: E501
        7: (make_evm_tx_hash(), TimestampMS(7), FVal(7), 'compound', '0x19222290DD7278Aa3Ddd389Cc1E1d165CC4BAf34', None),  # noqa: E501
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
                        group_identifier=data_entry[0],
                        sequence_index=1,
                        timestamp=data_entry[1],
                        location=Location.ETHEREUM,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_ETH,
                        amount=data_entry[2],
                    )
                else:
                    data_entry = evm_data[event.identifier]
                    expected_event = EvmEvent(
                        identifier=event.identifier,
                        tx_ref=data_entry[0],
                        sequence_index=1,
                        timestamp=data_entry[1],
                        location=Location.ETHEREUM,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_ETH,
                        amount=data_entry[2],
                        counterparty=data_entry[3],
                        address=data_entry[4],
                    )
                    assert event == expected_event


def test_history_events_count_with_chain_filters(database: DBHandler) -> None:
    """Ensure count queries work with chain fields (counterparty/address) filters."""
    db = DBHistoryEvents(database)
    evm_data = {
        1: (make_evm_tx_hash(), TimestampMS(1), ONE, 'aave', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        2: (make_evm_tx_hash(), TimestampMS(2), ONE, 'aave', '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        3: (make_evm_tx_hash(), TimestampMS(3), ONE, 'liquity', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4', None),  # noqa: E501
    }
    add_evm_events_to_db(db, evm_data)
    add_history_events_to_db(db, {4: ('BASE1', TimestampMS(4), ONE, None)})

    query = EvmEventFilterQuery.make(
        counterparties=['aave'],
        addresses=[string_to_evm_address(evm_data[1][4])],
    )
    with db.db.conn.read_ctx() as cursor:
        count_without_limit, count_with_limit = db.get_history_events_count(
            cursor=cursor,
            query_filter=query,
            aggregate_by_group_ids=False,
            entries_limit=None,
        )
        assert count_without_limit == 1
        assert count_with_limit == 1

        events = db.get_history_events(
            cursor=cursor,
            filter_query=query,
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(events) == 1
        assert isinstance(events[0], EvmEvent)
        assert events[0].counterparty == 'aave'
        assert events[0].address == string_to_evm_address(evm_data[1][4])


def test_history_events_count_with_eth_deposit_filters(database: DBHandler) -> None:
    """Ensure count queries work with eth deposit tx_ref filters."""
    db = DBHistoryEvents(database)
    tx_hash_1 = make_evm_tx_hash()
    tx_hash_2 = make_evm_tx_hash()
    deposit_data = {
        1: (tx_hash_1, TimestampMS(10), ONE, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', 42),
        2: (tx_hash_2, TimestampMS(11), ONE, '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', 84),
    }
    add_eth_deposit_events_to_db(db, deposit_data)

    query = EthDepositEventFilterQuery.make(
        tx_hashes=[tx_hash_1],
    )
    with db.db.conn.read_ctx() as cursor:
        count_without_limit, count_with_limit = db.get_history_events_count(
            cursor=cursor,
            query_filter=query,
            aggregate_by_group_ids=False,
            entries_limit=None,
        )
        assert count_without_limit == 1
        assert count_with_limit == 1

        events = db.get_history_events(
            cursor=cursor,
            filter_query=query,
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(events) == 1
        assert isinstance(events[0], EthDepositEvent)
        assert events[0].validator_index == 42
        assert events[0].tx_ref == tx_hash_1


def test_history_events_count_with_eth_withdrawal_filters(database: DBHandler) -> None:
    """Ensure count queries work with eth withdrawal validator filters."""
    db = DBHistoryEvents(database)
    withdrawal_data = {
        1: (7, TimestampMS(20), ONE, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', True),
        2: (9, TimestampMS(21), ONE, '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', False),
    }
    add_eth_withdrawal_events_to_db(db, withdrawal_data)

    query = EthWithdrawalFilterQuery.make(
        validator_indices=[7],
    )
    with db.db.conn.read_ctx() as cursor:
        count_without_limit, count_with_limit = db.get_history_events_count(
            cursor=cursor,
            query_filter=query,
            aggregate_by_group_ids=False,
            entries_limit=None,
        )
        assert count_without_limit == 1
        assert count_with_limit == 1

        events = db.get_history_events(
            cursor=cursor,
            filter_query=query,
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(events) == 1
        assert isinstance(events[0], EthWithdrawalEvent)
        assert events[0].validator_index == 7


@pytest.mark.parametrize(
    ('entries_limit', 'aggregate_by_group_ids'), [(None, False), (None, True), (FREE_HISTORY_EVENTS_LIMIT, False), (FREE_HISTORY_EVENTS_LIMIT, True)],  # noqa: E501
)
def test_read_write_customized_events_from_db(database: DBHandler, entries_limit: int, aggregate_by_group_ids: bool) -> None:  # noqa: E501
    """Tests filtering for fetching only the customized events"""
    db = DBHistoryEvents(database)
    history_data = {
        1: ('TEST1', TimestampMS(1000), ONE, None),
        2: ('TEST2', TimestampMS(2000), FVal(2), {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}),  # noqa: E501
        3: ('TEST3', TimestampMS(3000), FVal(3), {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}),  # noqa: E501
    }

    tx_hashes = [make_evm_tx_hash() for x in range(5)]
    evm_data = {
        4: (tx_hashes[0], TimestampMS(4), FVal(4), 'gas', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        5: (tx_hashes[1], TimestampMS(5), FVal(5), 'liquity', '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        6: (tx_hashes[2], TimestampMS(6), FVal(6), 'aave', '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4', {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}),  # noqa: E501
    }
    eth2_data = {
        7: (tx_hashes[3], TimestampMS(7), FVal(6), '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', None),  # noqa: E501
        8: (tx_hashes[4], TimestampMS(8), FVal(8), '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5', {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}),  # noqa: E501
    }

    add_history_events_to_db(db, history_data)
    add_evm_events_to_db(db, evm_data)
    add_eth2_events_to_db(db, eth2_data)

    filter_query_args: list[
        tuple[
            type[HistoryEventFilterQuery | (EvmEventFilterQuery | EthDepositEventFilterQuery)],
            dict[str, Any],
        ]
    ] = [
        (HistoryEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]), 'state_markers': [HistoryMappingState.CUSTOMIZED]}),  # noqa: E501
        (HistoryEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]), 'state_markers': [HistoryMappingState.CUSTOMIZED], 'from_ts': Timestamp(3)}),  # noqa: E501
        (EvmEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT]), 'state_markers': [HistoryMappingState.CUSTOMIZED]}),  # noqa: E501
        (EthDepositEventFilterQuery, {'entry_types': IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_DEPOSIT_EVENT]), 'state_markers': [HistoryMappingState.CUSTOMIZED]}),  # noqa: E501
    ]
    expected_identifiers = [
        ['TEST2', 'TEST3'],
        ['TEST3'],
        [tx_hashes[2]],
        [tx_hashes[4]],
    ]

    with db.db.conn.read_ctx() as cursor:
        for (filtering_class, filter_args), expected_ids in zip(filter_query_args, expected_identifiers, strict=True):  # noqa: E501
            events = db.get_history_events(
                cursor=cursor,
                filter_query=filtering_class.make(**filter_args),
                entries_limit=entries_limit,
                aggregate_by_group_ids=aggregate_by_group_ids,
            )
            if aggregate_by_group_ids is False:  # don't check the grouping case. Just make sure no exception is raised  # noqa: E501
                filtered_ids = [x.tx_ref if isinstance(x, EvmEvent) else x.group_identifier for x in events]  # type: ignore  # events are not tuples when aggregate_by_group_ids is False  # noqa: E501
                assert filtered_ids == expected_ids

            db.get_history_events_count(  # don't check result, just check for exception
                cursor=cursor,
                query_filter=filtering_class.make(**filter_args),
                aggregate_by_group_ids=aggregate_by_group_ids,
                entries_limit=entries_limit,
            )


def test_read_write_virtual_events_from_db(database: DBHandler) -> None:
    add_history_events_to_db(DBHistoryEvents(database), {
        1: ('TEST1', TimestampMS(1000), ONE, None),
        2: ('TEST2', TimestampMS(2000), FVal(2), {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.PROFIT_ADJUSTMENT}),  # noqa: E501
        3: ('TEST3', TimestampMS(3000), FVal(3), None),
    })
    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
                state_markers=[HistoryMappingState.PROFIT_ADJUSTMENT],
            ),
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(events) == 1
        assert events[0].group_identifier == 'TEST2'


def test_delete_last_event(database):
    """
    Test that if last event in a group is being deleted and it's not an EVM event,
    then the deletion is allowed.
    """
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        withdrawal_group_identifier = db.add_history_event(
            write_cursor=write_cursor,
            event=EthWithdrawalEvent(
                validator_index=1000,
                timestamp=TimestampMS(1683115229000),
                amount=ONE,
                withdrawal_address=make_evm_address(),
                is_exit=True,
            ),
        )
        evm_group_identifier = db.add_history_event(
            write_cursor=write_cursor,
            event=make_ethereum_event(index=1),
        )
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events_internal(cursor, HistoryEventFilterQuery.make())) == 2

    msg = db.delete_history_events_by_identifier(identifiers=[withdrawal_group_identifier])
    assert msg is None
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events_internal(cursor, HistoryEventFilterQuery.make())) == 1, 'Only the EVM event should be left'  # noqa: E501

    msg = db.delete_history_events_by_identifier(identifiers=[evm_group_identifier])
    assert 'was the last event of a transaction' in msg
    with db.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events_internal(cursor, HistoryEventFilterQuery.make())) == 1, 'EVM event should be left'  # noqa: E501


def test_get_history_events_free_filter(database: 'DBHandler'):
    """Test that the history events filter works consistently with has_premium=True/False"""
    history_events = DBHistoryEvents(database=database)
    group_identifiers = [str(make_evm_tx_hash()) for _ in range(6)]
    dummy_events = (
        AssetMovement(
            group_identifier=group_identifiers[5],
            timestamp=TimestampMS(1000),
            location=Location.KRAKEN,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_BTC,
            amount=ONE,
        ), HistoryEvent(
            group_identifier=group_identifiers[0],
            sequence_index=0,
            timestamp=TimestampMS(1000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ONE,
        ), HistoryEvent(
            group_identifier=group_identifiers[1],
            sequence_index=0,
            timestamp=TimestampMS(2000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ), HistoryEvent(
            group_identifier=group_identifiers[1],
            sequence_index=1,
            timestamp=TimestampMS(2000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            amount=FVal(1000),
        ), HistoryEvent(
            group_identifier=group_identifiers[2],
            sequence_index=0,
            timestamp=TimestampMS(3000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=FVal(5),
        ), HistoryEvent(
            group_identifier=group_identifiers[2],
            sequence_index=1,
            timestamp=TimestampMS(3000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=FVal('1.5'),
        ), HistoryEvent(
            group_identifier=group_identifiers[2],
            sequence_index=2,
            timestamp=TimestampMS(3000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=FVal('0.02762431'),
        ), HistoryEvent(
            group_identifier=group_identifiers[3],
            sequence_index=0,
            timestamp=TimestampMS(4000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=FVal('0.000076'),
        ), HistoryEvent(
            group_identifier=group_identifiers[3],
            sequence_index=1,
            timestamp=TimestampMS(4000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ONE,
        ), HistoryEvent(
            group_identifier=group_identifiers[3],
            sequence_index=2,
            timestamp=TimestampMS(4000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(1000),
        ), HistoryEvent(
            group_identifier=group_identifiers[4],
            sequence_index=0,
            timestamp=TimestampMS(5000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=ONE,
        ),
    )
    with database.conn.write_ctx() as write_cursor:
        history_events.add_history_events(  # add dummy history events
            write_cursor=write_cursor,
            history=dummy_events,
        )
        database.add_to_ignored_assets(
            write_cursor=write_cursor,
            asset=A_USDC,
        )

    with database.conn.read_ctx() as cursor:
        # free and premium results should be same with len(events) < FREE_LIMIT
        for filters in (  # trying different filters with some combinations
            HistoryEventFilterQuery.make(location=Location.OPTIMISM),
            HistoryEventFilterQuery.make(assets=(A_ETH,)),
            HistoryEventFilterQuery.make(assets=(A_ETH,), location=Location.COINBASE),
            HistoryEventFilterQuery.make(from_ts=Timestamp(2)),
            HistoryEventFilterQuery.make(assets=(A_USDT,), to_ts=Timestamp(3)),
            HistoryEventFilterQuery.make(location=Location.KRAKEN),
            HistoryEventFilterQuery.make(exclude_ignored_assets=True),
        ):
            assert history_events.get_history_events(  # when grouping
                cursor=cursor,
                filter_query=filters,
                entries_limit=None,
                aggregate_by_group_ids=True,
            ) == history_events.get_history_events(
                cursor=cursor,
                filter_query=filters,
                entries_limit=None,
                aggregate_by_group_ids=True,
            ) != []
            assert history_events.get_history_events(  # when not grouping
                cursor=cursor,
                filter_query=filters,
                entries_limit=None,
                aggregate_by_group_ids=False,
            ) == history_events.get_history_events(
                cursor=cursor,
                filter_query=filters,
                entries_limit=None,
                aggregate_by_group_ids=False,
            ) != []

        with patch(target='rotkehlchen.tests.db.test_history_events.FREE_HISTORY_EVENTS_LIMIT', new=3):  # noqa: E501
            for filters in (  # trying different filters with some combinations
                HistoryEventFilterQuery.make(event_subtypes=[HistoryEventSubType.NONE]),
                HistoryEventFilterQuery.make(assets=(A_ETH, A_USDT)),
                HistoryEventFilterQuery.make(from_ts=Timestamp(2)),
                HistoryEventFilterQuery.make(assets=(A_ETH, A_USDC, A_USDT)),
                HistoryEventFilterQuery.make(exclude_ignored_assets=True),
            ):
                premium_grouped_result = history_events.get_history_events_internal(  # when grouping  # noqa: E501
                    cursor=cursor,
                    filter_query=filters,
                    aggregate_by_group_ids=True,
                )
                assert len(premium_grouped_result) > 3
                free_grouped_result = history_events.get_history_events(
                    cursor=cursor,
                    filter_query=filters,
                    entries_limit=FREE_HISTORY_EVENTS_LIMIT,
                    aggregate_by_group_ids=True,
                )
                assert len(free_grouped_result) == min(3, len(premium_grouped_result))
                assert free_grouped_result == premium_grouped_result[-3:]
                premium_result = history_events.get_history_events_internal(  # when not grouping
                    cursor=cursor,
                    filter_query=filters,
                    aggregate_by_group_ids=False,
                )
                assert len(premium_result) > 3
                free_result = history_events.get_history_events(
                    cursor=cursor,
                    filter_query=filters,
                    entries_limit=FREE_HISTORY_EVENTS_LIMIT,
                    aggregate_by_group_ids=False,
                )
                for free_event in free_result:
                    assert free_event.identifier is not None
                    assert free_event.identifier > 3, 'Free sub-events should be from the latest 3 event groups'  # noqa: E501


def test_history_events_with_ignored_groups_excluding_assets(database: 'DBHandler') -> None:
    db = DBHistoryEvents(database)
    group_identifier = 'group_with_ignored_asset'
    timestamp = TimestampMS(1)
    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                HistoryEvent(
                    group_identifier=group_identifier,
                    sequence_index=1,
                    timestamp=timestamp,
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=A_ETH,
                    amount=ONE,
                ),
                HistoryEvent(
                    group_identifier=group_identifier,
                    sequence_index=2,
                    timestamp=timestamp,
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_WBTC,
                    amount=ONE,
                ),
            ],
        )
        database.add_to_ignored_assets(write_cursor, A_WBTC)

    with database.conn.read_ctx() as cursor:
        events_result_excluding = db.get_history_events_and_limit_info(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(exclude_ignored_assets=True),
            entries_limit=None,
            match_exact_events=True,
            aggregate_by_group_ids=False,
        )
        events_result_including = db.get_history_events_and_limit_info(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(exclude_ignored_assets=False),
            entries_limit=None,
            match_exact_events=True,
            aggregate_by_group_ids=False,
        )

    events_excluding: list[HistoryBaseEntry] = events_result_excluding.events  # type: ignore[assignment]  # filter uses aggregate_by_group_ids=False.
    assert len(events_excluding) == 1
    assert events_excluding[0].asset == A_ETH
    # With the window function fix, ignored_group_identifiers is detected even when excluding
    assert events_result_excluding.ignored_group_identifiers == {group_identifier}
    assert events_result_including.ignored_group_identifiers == {group_identifier}


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_match_exact_events(database: 'DBHandler', start_with_valid_premium: bool) -> None:
    """Test that when toggling the match with exact events options
    we receive the expected number of events in both free and premium tiers
    """
    db = DBHistoryEvents(database)
    timestamp, account = TimestampMS(0), make_evm_address()
    entries_limit = None if start_with_valid_premium else FREE_HISTORY_EVENTS_LIMIT
    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                EvmEvent(
                    tx_ref=(tx_hash := make_evm_tx_hash()),
                    sequence_index=0,
                    timestamp=timestamp,
                    location=Location.BASE,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(gas := '1.6'),
                    location_label=account,
                    notes=f'Burn {gas} ETH for gas',
                    counterparty=CPT_GAS,
                ), EvmEvent(
                    tx_ref=tx_hash,
                    sequence_index=2,
                    timestamp=timestamp,
                    location=Location.BASE,
                    event_type=HistoryEventType.INFORMATIONAL,
                    event_subtype=HistoryEventSubType.APPROVE,
                    asset=A_DAI,
                    amount=ZERO,
                    location_label=account,
                    notes=f'Revoke DAI spending approval of {account} by {CPT_ONEINCH_V6}',
                ), EvmSwapEvent(
                    tx_ref=tx_hash,
                    sequence_index=3,
                    timestamp=timestamp,
                    location=Location.BASE,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=A_DAI,
                    amount=FVal(swap_amount := FVal(3)),
                    location_label=account,
                    notes=f'Swap {swap_amount} DAI in 1inch-v6',
                    counterparty=CPT_ONEINCH_V6,
                ), EvmSwapEvent(
                    tx_ref=tx_hash,
                    sequence_index=4,
                    timestamp=timestamp,
                    location=Location.BASE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_ETH,
                    amount=FVal(receive_amount := 5),
                    location_label=account,
                    notes=f'Receive {receive_amount} ETH as a result of a 1inch-v6 swap',
                    counterparty=CPT_ONEINCH_V6,
                ),
            ],
        )

    with database.conn.read_ctx() as cursor:
        result_match = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(assets=(A_DAI,)),
            entries_limit=entries_limit,
            aggregate_by_group_ids=False,
            match_exact_events=True,
        )
        result_no_match = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(assets=(A_DAI,)),
            entries_limit=entries_limit,
            aggregate_by_group_ids=False,
            match_exact_events=False,
        )

    assert len(result_match) == 2 and len(result_no_match) == 4
    assert all(entry.asset == A_DAI for entry in result_match)

    # also check the case of grouping by id
    with database.conn.read_ctx() as cursor:
        result_match_grouped = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(assets=(A_DAI,)),
            entries_limit=entries_limit,
            aggregate_by_group_ids=True,
            match_exact_events=True,
        )
        result_no_match_grouped = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(assets=(A_DAI,)),
            entries_limit=entries_limit,
            aggregate_by_group_ids=True,
            match_exact_events=False,
        )
        assert result_match_grouped[0][0] == 2 and result_no_match_grouped[0][0] == 4
        assert result_match_grouped[0][1].asset == A_DAI
        assert result_match_grouped[0][1].asset == A_DAI


def test_event_modification_tracks_earliest_timestamp(database: 'DBHandler') -> None:
    db = DBHistoryEvents(database)
    event_ts_key = DBCacheStatic.STALE_BALANCES_FROM_TS.value
    modification_ts_key = DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone() is None

    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[(eth_event := HistoryEvent(
                group_identifier='TEST1',
                sequence_index=1,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            )), HistoryEvent(
                group_identifier='TEST2',
                sequence_index=1,
                timestamp=(ts_2000 := TimestampMS(2000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_BTC,
                amount=ONE,
            )],
        )

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == ts_2000  # global minimum across all assets
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (modification_ts_key,),
        ).fetchone()[0]) > 0

    with database.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier='TEST3',
                sequence_index=1,
                timestamp=(ts_1000 := TimestampMS(1000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
        )

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == ts_1000  # updated to earlier timestamp

    # add event at later timestamp 5000 and cache should remain at 1000
    with database.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier='TEST4',
                sequence_index=1,
                timestamp=TimestampMS(5000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
        )

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == ts_1000  # remains at minimum

    # edit notes only and _mark_events_modified should NOT be called
    with (
        patch.object(db, '_mark_events_modified') as mock_mark,
        database.user_write() as write_cursor,
    ):
        eth_event.identifier = 1
        eth_event.notes = 'Updated notes'
        db.edit_history_event(write_cursor=write_cursor, event=eth_event)
        mock_mark.assert_not_called()

    # edit asset and should update cache
    with database.user_write() as write_cursor:
        eth_event.asset = A_DAI
        db.edit_history_event(write_cursor=write_cursor, event=eth_event)

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == ts_1000  # still the global minimum

    # test purge_exchange_data updates cache via delete_events_and_track
    with database.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier='KRAKEN1',
                sequence_index=1,
                timestamp=(ts_500 := TimestampMS(500)),
                location=Location.KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=ONE,
            ),
        )
        database.purge_exchange_data(write_cursor=write_cursor, location=Location.KRAKEN)

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == ts_500  # updated to deleted event's timestamp


def test_modification_ts_updated_on_each_modification(database: 'DBHandler') -> None:
    db = DBHistoryEvents(database)
    event_ts_key = DBCacheStatic.STALE_BALANCES_FROM_TS.value
    modification_ts_key = DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value

    with database.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier='TEST1',
                sequence_index=1,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
        )

    with database.conn.read_ctx() as cursor:
        modification_ts1 = int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (modification_ts_key,),
        ).fetchone()[0])

    gevent.sleep(0.01)  # ensure different modification_ts between events

    with database.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier='TEST2',
                sequence_index=1,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
        )

    with database.conn.read_ctx() as cursor:
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (event_ts_key,),
        ).fetchone()[0]) == 1000
        assert int(cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?', (modification_ts_key,),
        ).fetchone()[0]) >= modification_ts1
