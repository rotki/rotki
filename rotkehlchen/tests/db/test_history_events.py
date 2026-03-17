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
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    TX_DECODED,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.evmtx import DBEvmTx
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
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    EVMTxHash,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)


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
                filtered_ids = [x.tx_ref if isinstance(x, EvmEvent) else x.group_identifier for x in events]  # events are not tuples when aggregate_by_group_ids is False # noqa: E501
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
    assert msg is not None
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
            event_subtype=HistoryEventSubType.RECEIVE,
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


@pytest.mark.skip(reason='Event modification tracking is temporarily removed.')
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
        db.edit_history_event(
            write_cursor=write_cursor,
            event=eth_event,
            mapping_state=HistoryMappingState.CUSTOMIZED,
        )
        mock_mark.assert_not_called()

    # edit asset and should update cache
    with database.user_write() as write_cursor:
        eth_event.asset = A_DAI
        db.edit_history_event(
            write_cursor=write_cursor,
            event=eth_event,
            mapping_state=HistoryMappingState.CUSTOMIZED,
        )

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


@pytest.mark.skip(reason='Event modification tracking is temporarily removed.')
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


def test_get_history_event_group_position(database: 'DBHandler') -> None:
    """Test that get_history_event_group_position returns the correct 0-based position
    of a group in the filtered and sorted (timestamp DESC) list of groups.
    """
    db = DBHistoryEvents(database)

    # Create events with different timestamps and group identifiers.
    # Groups sorted by timestamp DESC: GROUP5 (5000), GROUP4 (4000), GROUP3 (3000),
    # GROUP2 (2000), GROUP1 (1000) at positions 0, 1, 2, 3, 4 respectively.
    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier='GROUP1',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=ONE,
            ), HistoryEvent(
                group_identifier='GROUP2',
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_BTC,
                amount=FVal(2),
            ), HistoryEvent(
                group_identifier='GROUP3',
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal(3),
            ), HistoryEvent(
                group_identifier='GROUP4',
                sequence_index=0,
                timestamp=TimestampMS(4000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=A_USDC,
                amount=FVal(100),
            ), HistoryEvent(
                group_identifier='GROUP5',
                sequence_index=0,
                timestamp=TimestampMS(5000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal(5),
            )],
        )

    # Test positions with no filter (all events)
    filter_query = HistoryEventFilterQuery.make()

    # Most recent group (timestamp 5000) should be at position 0
    assert db.get_history_event_group_position('GROUP5', filter_query) == 0
    # Second most recent (timestamp 4000) should be at position 1
    assert db.get_history_event_group_position('GROUP4', filter_query) == 1
    # Middle group (timestamp 3000) should be at position 2
    assert db.get_history_event_group_position('GROUP3', filter_query) == 2
    # Earlier group (timestamp 2000) should be at position 3
    assert db.get_history_event_group_position('GROUP2', filter_query) == 3
    # Oldest group (timestamp 1000) should be at position 4
    assert db.get_history_event_group_position('GROUP1', filter_query) == 4

    # Test with a non-existent group
    assert db.get_history_event_group_position('NONEXISTENT', filter_query) is None

    # Test with location filter - only Ethereum events
    # Groups: GROUP5, GROUP4, GROUP2, GROUP1 (GROUP3 is on Optimism)
    # Positions: 0, 1, 2, 3
    eth_filter = HistoryEventFilterQuery.make(location=Location.ETHEREUM)
    assert db.get_history_event_group_position('GROUP5', eth_filter) == 0
    assert db.get_history_event_group_position('GROUP4', eth_filter) == 1
    assert db.get_history_event_group_position('GROUP2', eth_filter) == 2
    assert db.get_history_event_group_position('GROUP1', eth_filter) == 3
    # GROUP3 is not in Ethereum, so it should return None
    assert db.get_history_event_group_position('GROUP3', eth_filter) is None

    # Test with asset filter - only ETH events
    # Groups: GROUP5, GROUP3, GROUP1 (only these have ETH)
    # Positions: 0, 1, 2
    eth_asset_filter = HistoryEventFilterQuery.make(assets=(A_ETH,))
    assert db.get_history_event_group_position('GROUP5', eth_asset_filter) == 0
    assert db.get_history_event_group_position('GROUP3', eth_asset_filter) == 1
    assert db.get_history_event_group_position('GROUP1', eth_asset_filter) == 2
    # GROUP2 has BTC, GROUP4 has USDC - should return None
    assert db.get_history_event_group_position('GROUP2', eth_asset_filter) is None
    assert db.get_history_event_group_position('GROUP4', eth_asset_filter) is None


def test_get_history_event_group_position_with_same_timestamp(database: 'DBHandler') -> None:
    """Test that groups with the same timestamp are ordered by group_identifier as tiebreaker."""
    db = DBHistoryEvents(database)

    # Create events with the same timestamp but different group identifiers.
    # With same timestamp, groups are sorted by group_identifier alphabetically.
    # Alphabetically: GROUP_A, GROUP_B, GROUP_C. Position counts groups before target,
    # so GROUP_A=0, GROUP_B=1, GROUP_C=2.
    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier='GROUP_B',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ), HistoryEvent(
                group_identifier='GROUP_A',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ), HistoryEvent(
                group_identifier='GROUP_C',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            )],
        )

    filter_query = HistoryEventFilterQuery.make()
    assert db.get_history_event_group_position('GROUP_A', filter_query) == 0
    assert db.get_history_event_group_position('GROUP_B', filter_query) == 1
    assert db.get_history_event_group_position('GROUP_C', filter_query) == 2


def test_matched_filter_returns_canonical_entries(database: 'DBHandler') -> None:
    """Test that filtering by MATCHED returns only the canonical (movement) side per group.

    When matching, the MATCHED marker is placed on the matched_event (right_event_id in
    history_event_links). The filter should return only the movement side (left_event_id)
    so that process_matched_asset_movements can fetch the linked events in post-processing.
    This prevents page_size=N from returning fewer than N results.

    Setup:
    - Group A: movement (COINBASE, id=1) -> onchain event (ETHEREUM, id=2), MATCHED on id=2
    - Group B: movement (KRAKEN, id=3) -> onchain event (ETHEREUM, id=4), MATCHED on id=4
    - Group C: adjustment event (id=5) with MATCHED marker, no link (standalone)
    - Group D: unrelated event (COINBASE), no marker, no link

    Expected:
    - markers=[MATCHED]: returns movements (1, 3) + standalone adjustment (5), not onchain (2, 4)
    - markers=[MATCHED] + location=COINBASE: returns only movement 1
    - markers=[MATCHED] + limit=2: returns exactly 2 results (not fewer due to dedup)
    - markers=[CUSTOMIZED]: returns nothing
    """
    db = DBHistoryEvents(database)
    link_type = HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()
    matched = HistoryMappingState.MATCHED.serialize_for_db()

    with database.user_write() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                AssetMovement(  # group A movement (left side of link)
                    identifier=(movement_a_id := 1),
                    group_identifier='GROUP_A',
                    timestamp=TimestampMS(1000),
                    location=Location.COINBASE,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=A_ETH,
                    amount=ONE,
                ), HistoryEvent(  # group A onchain event (right side of link, gets MATCHED)
                    identifier=(onchain_a_id := 2),
                    group_identifier='GROUP_A_ONCHAIN',
                    sequence_index=0,
                    timestamp=TimestampMS(1000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ), AssetMovement(  # group B movement (left side of link)
                    identifier=(movement_b_id := 3),
                    group_identifier='GROUP_B',
                    timestamp=TimestampMS(2000),
                    location=Location.KRAKEN,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_ETH,
                    amount=FVal(2),
                ), HistoryEvent(  # group B onchain event (right side of link, gets MATCHED)
                    identifier=(onchain_b_id := 4),
                    group_identifier='GROUP_B_ONCHAIN',
                    sequence_index=0,
                    timestamp=TimestampMS(2000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=FVal(2),
                ), HistoryEvent(  # group C: standalone adjustment with MATCHED, no link
                    identifier=(adjustment_id := 5),
                    group_identifier='GROUP_C',
                    sequence_index=0,
                    timestamp=TimestampMS(3000),
                    location=Location.COINBASE,
                    event_type=HistoryEventType.EXCHANGE_ADJUSTMENT,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=A_ETH,
                    amount=FVal('0.001'),
                ), HistoryEvent(  # group D: unrelated event, no marker, no link
                    group_identifier='GROUP_D',
                    sequence_index=0,
                    timestamp=TimestampMS(4000),
                    location=Location.COINBASE,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=FVal(3),
                ),
            ],
        )
        # MATCHED markers on the right (matched) side of each link + standalone adjustment
        write_cursor.executemany(
            'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES(?, ?, ?)',
            [
                (onchain_a_id, HISTORY_MAPPING_KEY_STATE, matched),
                (onchain_b_id, HISTORY_MAPPING_KEY_STATE, matched),
                (adjustment_id, HISTORY_MAPPING_KEY_STATE, matched),
            ],
        )
        # links: movement (left) -> onchain (right)
        write_cursor.executemany(
            'INSERT INTO history_event_links(left_event_id, right_event_id, link_type) '
            'VALUES(?, ?, ?)',
            [(movement_a_id, onchain_a_id, link_type), (movement_b_id, onchain_b_id, link_type)],
        )

    with database.conn.read_ctx() as cursor:
        # MATCHED filter returns only movements + standalone adjustment (not onchain events)
        all_matched = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                state_markers=[HistoryMappingState.MATCHED],
            ),
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert {e.identifier for e in all_matched} == {movement_a_id, movement_b_id, adjustment_id}

        # MATCHED + location=COINBASE returns only coinbase movement + coinbase adjustment
        coinbase_matched = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                state_markers=[HistoryMappingState.MATCHED],
                location=Location.COINBASE,
            ),
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert {e.identifier for e in coinbase_matched} == {movement_a_id, adjustment_id}

        # MATCHED + limit=2 returns exactly 2 results (pagination not halved by linked events)
        paginated = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                state_markers=[HistoryMappingState.MATCHED],
                limit=2,
                offset=0,
            ),
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(paginated) == 2

        # CUSTOMIZED returns nothing
        customized = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                state_markers=[HistoryMappingState.CUSTOMIZED],
            ),
            entries_limit=None,
            aggregate_by_group_ids=False,
        )
        assert len(customized) == 0


def _setup_two_evm_transactions(database: DBHandler) -> tuple[EVMTxHash, EVMTxHash]:
    """Helper to create two EVM transactions in the database and return their hashes."""
    tx_hash_a, tx_hash_b = make_evm_tx_hash(), make_evm_tx_hash()
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash_a,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(1000),
                block_number=1,
                from_address=make_evm_address(),
                to_address=make_evm_address(),
                value=0,
                gas=21000,
                gas_price=1000000000,
                gas_used=21000,
                input_data=b'',
                nonce=0,
            ), EvmTransaction(
                tx_hash=tx_hash_b,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(2000),
                block_number=2,
                from_address=make_evm_address(),
                to_address=make_evm_address(),
                value=0,
                gas=21000,
                gas_price=1000000000,
                gas_used=21000,
                input_data=b'',
                nonce=1,
            )],
            relevant_address=None,
        )
    return tx_hash_a, tx_hash_b


def test_delete_location_events_customized_handling(database: DBHandler) -> None:
    """Verifies that delete_location_events handles customized events correctly based on
    the customized_handling parameter.

    With 'preserve_transactions': all events in a transaction with a customized event are kept.
    With default 'preserve_events': only the individual customized event is kept.

    1. Create two EVM transactions (tx_a with 3 events, tx_b with 2 events)
    2. Mark one event in tx_a as customized
    3. Call delete_location_events with customized_handling='preserve_transactions'
    4. Assert all 3 events in tx_a are preserved, all events in tx_b are deleted
    5. Re-insert tx_b's events
    6. Call delete_location_events with default customized_handling
    7. Assert only the customized event is preserved, all siblings are deleted
    """
    tx_hash_a, tx_hash_b = _setup_two_evm_transactions(database)
    db = DBHistoryEvents(database)

    with database.user_write() as write_cursor:
        customized_id = None
        for seq_idx in range(3):
            if (identifier := db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_a,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(1000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
                mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if seq_idx == 1 else None,  # noqa: E501
            )) and seq_idx == 1:
                customized_id = identifier
        for seq_idx in range(2):
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_b,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(2000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
            )

        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 5

        # preserve_transactions: all events in tx_a are kept, tx_b's are deleted
        db.delete_location_events(
            write_cursor=write_cursor,
            location=Location.ETHEREUM,
            address=None,
            customized_handling='preserve_transactions',
        )
        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 3
        assert len({row[0] for row in write_cursor.execute(
            'SELECT DISTINCT group_identifier FROM history_events',
        ).fetchall()}) == 1  # only tx_a's group_identifier remains

        # default (preserve_events): only the customized event is kept
        db.delete_location_events(
            write_cursor=write_cursor,
            location=Location.ETHEREUM,
            address=None,
        )
        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 1
        assert write_cursor.execute(
            'SELECT identifier FROM history_events',
        ).fetchone()[0] == customized_id


def test_delete_events_by_tx_ref_preserves_customized_transaction(database: DBHandler) -> None:
    """Verifies that delete_events_by_tx_ref with customized_handling='preserve_transactions'
    preserves all events in a transaction when any event is customized.

    1. Create two EVM transactions (tx_a with 2 events, tx_b with 2 events)
    2. Mark one event in tx_a as customized
    3. Call delete_events_by_tx_ref for both tx_refs with 'preserve_transactions'
    4. Assert all events in tx_a are preserved, all events in tx_b are deleted
    """
    tx_hash_a, tx_hash_b = _setup_two_evm_transactions(database)
    db = DBHistoryEvents(database)

    with database.user_write() as write_cursor:
        for seq_idx in range(2):
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_a,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(1000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
                mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if seq_idx == 0 else None,  # noqa: E501
            )
        for seq_idx in range(2):
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_b,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(2000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
            )

        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 4

        db.delete_events_by_tx_ref(
            write_cursor=write_cursor,
            tx_refs=[tx_hash_a, tx_hash_b],
            location=Location.ETHEREUM,
            customized_handling='preserve_transactions',
        )

        # all events in tx_a are preserved, tx_b's events are deleted
        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 2
        group_ids = {row[0] for row in write_cursor.execute(
            'SELECT DISTINCT group_identifier FROM history_events',
        ).fetchall()}
        assert len(group_ids) == 1  # only tx_a's group_identifier remains


def test_reset_events_for_redecode_preserves_customized_transaction(database: DBHandler) -> None:
    """Verifies that reset_events_for_redecode preserves all events in a transaction when
    any event is customized, and keeps the decoded status for that transaction.

    1. Create two EVM transactions (tx_a with 2 events, tx_b with 2 events)
    2. Mark both as decoded in evm_tx_mappings
    3. Mark one event in tx_a as customized
    4. Call reset_events_for_redecode
    5. Assert all events in tx_a are preserved, all events in tx_b are deleted
    6. Assert tx_a's decoded mapping is preserved, tx_b's is deleted
    """
    tx_hash_a, tx_hash_b = _setup_two_evm_transactions(database)
    db = DBHistoryEvents(database)

    with database.user_write() as write_cursor:
        # mark both transactions as decoded
        for tx_hash in (tx_hash_a, tx_hash_b):
            tx_id = write_cursor.execute(
                'SELECT identifier FROM evm_transactions WHERE tx_hash=?',
                (tx_hash,),
            ).fetchone()[0]
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )

        for seq_idx in range(2):
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_a,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(1000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
                mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if seq_idx == 0 else None,  # noqa: E501
            )
        for seq_idx in range(2):
            db.add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=tx_hash_b,
                    sequence_index=seq_idx,
                    timestamp=TimestampMS(2000000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=ONE,
                ),
            )

        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 4
        assert write_cursor.execute('SELECT COUNT(*) FROM evm_tx_mappings').fetchone()[0] == 2

        db.reset_events_for_redecode(write_cursor=write_cursor, location=Location.ETHEREUM)

        # all events in tx_a are preserved, tx_b's events are deleted
        assert write_cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 2
        group_ids = {row[0] for row in write_cursor.execute(
            'SELECT DISTINCT group_identifier FROM history_events',
        ).fetchall()}
        assert len(group_ids) == 1  # only tx_a's group_identifier remains

        # tx_a's decoded mapping is preserved, tx_b's is deleted
        assert write_cursor.execute('SELECT COUNT(*) FROM evm_tx_mappings').fetchone()[0] == 1
        remaining_tx_id = write_cursor.execute(
            'SELECT tx_id FROM evm_tx_mappings',
        ).fetchone()[0]
        remaining_tx_hash = write_cursor.execute(
            'SELECT tx_hash FROM evm_transactions WHERE identifier=?',
            (remaining_tx_id,),
        ).fetchone()[0]
        assert remaining_tx_hash == bytes(tx_hash_a)
