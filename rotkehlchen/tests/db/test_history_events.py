from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.accounting.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.filtering import EvmEventFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.tests.utils.factories import (
    make_ethereum_event,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash


def test_get_customized_event_identifiers(database):
    db = DBHistoryEvents(database)
    with db.db.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                event_identifier=deserialize_evm_tx_hash('0x75ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
        db.add_history_events(
            write_cursor=write_cursor,
            history=[
                HistoryEvent(
                    event_identifier=deserialize_evm_tx_hash('0x15ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                    sequence_index=1,
                    timestamp=TimestampMS(1),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    balance=Balance(1),
                ), HistoryEvent(
                    event_identifier=deserialize_evm_tx_hash('0x25ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
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
                event_identifier=deserialize_evm_tx_hash('0x35ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791'),  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(3),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(1),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )

    with db.db.conn.read_ctx() as cursor:
        assert db.get_customized_event_identifiers(cursor, chain_id=None) == [1, 4]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.ETHEREUM) == [1]
        assert db.get_customized_event_identifiers(cursor, chain_id=ChainID.OPTIMISM) == [4]


def add_history_events_to_db(db: DBHistoryEvents, history_data: dict) -> None:
    with db.db.user_write() as write_cursor:
        for _, entry in history_data.items():
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
            )


def add_evm_events_to_db(db: DBHistoryEvents, evm_data: dict) -> None:
    with db.db.user_write() as write_cursor:
        for _, entry in evm_data.items():
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
                    address=entry[5],
                ),
            )


def test_read_write_events_from_db(database):
    db = DBHistoryEvents(database)
    history_data = {  # mapping of identifier to unique data
        1: ('TEST1', TimestampMS(1), 1),
        2: ('TEST2', TimestampMS(2), 2),
        3: ('TEST3', TimestampMS(3), 3),
    }

    evm_data = {  # mapping of identifier to unique data
        4: (make_evm_tx_hash(), TimestampMS(4), 4, 'gas', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5'),  # noqa: E501
        5: (make_evm_tx_hash(), TimestampMS(5), 5, 'liquity', EvmProduct.STAKING, '0x85222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5'),  # noqa: E501
        6: (make_evm_tx_hash(), TimestampMS(6), 6, 'aave', EvmProduct.POOL, '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe4'),  # noqa: E501
        7: (make_evm_tx_hash(), TimestampMS(7), 7, 'compound', EvmProduct.POOL, '0x19222290DD7278Aa3Ddd389Cc1E1d165CC4BAf34'),  # noqa: E501
    }

    add_history_events_to_db(db, history_data)
    add_evm_events_to_db(db, evm_data)

    # args for creating filter queries
    filter_query_args = [
        (HistoryEventFilterQuery, None),
        (HistoryEventFilterQuery, IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT], behaviour='IN')),  # noqa: E501
        (EvmEventFilterQuery, IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT], behaviour='IN')),  # noqa: E501
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
