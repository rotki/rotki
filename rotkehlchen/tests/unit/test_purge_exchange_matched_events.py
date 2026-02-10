from typing import TYPE_CHECKING

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.events import match_asset_movements
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_purge_exchange_restores_matched_events(database: 'DBHandler') -> None:
    """Test that purging exchange data restores matched events on the other side of the link.

    Creates a Kraken withdrawal matched with an onchain receive event, then purges Kraken data
    and verifies the onchain event is restored to its original state with no orphaned mappings,
    backups, or links.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1600000000000),
                asset=A_ETH,
                amount=FVal('1.5'),
                unique_id='purge-test-1',
                location_label='Kraken 1',
            ), (onchain_receive := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1600000000001),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1.5'),
                location_label=make_evm_address(),
                notes='Receive 1.5 ETH',
            ))],
        )

    match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        assert len(links := cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type = ?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()) == 1
        matched_event_id = links[0][1]

        assert cursor.execute(
            'SELECT 1 FROM history_events_backup WHERE identifier = ?',
            (matched_event_id,),
        ).fetchone() is not None

        assert cursor.execute(
            'SELECT 1 FROM history_events_mappings '
            'WHERE parent_identifier = ? AND name = ? AND value = ?',
            (matched_event_id, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.AUTO_MATCHED.serialize_for_db()),  # noqa: E501
        ).fetchone() is not None

        # the onchain event should have been modified by matching
        assert events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[matched_event_id]),
        )[0].counterparty == Location.KRAKEN.name.lower()  # type: ignore[attr-defined]

    with database.conn.write_ctx() as write_cursor:
        database.purge_exchange_data(write_cursor=write_cursor, location=Location.KRAKEN)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT 1 FROM history_event_links WHERE link_type = ?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchone() is None
        assert cursor.execute(
            'SELECT 1 FROM history_events_mappings WHERE name = ? AND value = ?',
            (HISTORY_MAPPING_KEY_STATE, HistoryMappingState.AUTO_MATCHED.serialize_for_db()),
        ).fetchone() is None
        assert cursor.execute(
            'SELECT 1 FROM history_events_backup WHERE identifier = ?',
            (matched_event_id,),
        ).fetchone() is None
        assert cursor.execute(
            'SELECT 1 FROM history_events WHERE type = ?',
            (HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),),
        ).fetchone() is None

        # the onchain event should be restored to its original state
        remaining = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[matched_event_id]),
        )
        onchain_receive.identifier = remaining[0].identifier
        assert remaining == [onchain_receive]

        assert events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        ) == []


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_purge_exchange_with_adjustment_event(database: 'DBHandler') -> None:
    """Test that EXCHANGE_ADJUSTMENT events created during matching are cleaned up on purge."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1600000000000),
                asset=A_ETH,
                amount=FVal('2.0'),
                unique_id='purge-adj-1',
                location_label='Kraken 1',
            ), (onchain_receive := EvmEvent(  # slightly different amount triggers an adjustment event  # noqa: E501
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1600000000001),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1.99'),
                location_label=make_evm_address(),
            ))],
        )

    match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE type = ?',
            (HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),),
        ).fetchone()[0] > 0

    with database.conn.write_ctx() as write_cursor:
        database.purge_exchange_data(write_cursor=write_cursor, location=Location.KRAKEN)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT 1 FROM history_events WHERE type = ?',
            (HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),),
        ).fetchone() is None

        remaining = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.ETHEREUM),
        )
        onchain_receive.identifier = remaining[0].identifier
        assert remaining == [onchain_receive]
