"""Test for data migration 20 - fixing SwapEvent identifiers"""
from unittest.mock import patch

import pytest

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD
from rotkehlchen.data_migrations.manager import MIGRATION_LIST, DataMigrationManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_event_identifier
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations
from rotkehlchen.types import AssetAmount, Location, TimestampMS


def create_broken_swap_events(
        db: DBHandler,
        timestamp: TimestampMS,
        location: Location,
        location_label: str | None = None,
) -> tuple[str, str, str]:
    """Create SwapEvents with different identifiers like they were created before the fix"""
    # Each event creates its own identifier (the bug)
    spend_event = SwapEvent(
        timestamp=timestamp,
        location=location,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=ONE,
        event_identifier=create_event_identifier(
            location=location,
            timestamp=timestamp,
            asset=A_ETH,
            amount=ONE,
            unique_id='spend',
        ),
        location_label=location_label,
    )

    receive_event = SwapEvent(
        timestamp=timestamp,
        location=location,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=ONE * 2,
        event_identifier=create_event_identifier(
            location=location,
            timestamp=timestamp,
            asset=A_BTC,
            amount=ONE * 2,
            unique_id='receive',
        ),
        location_label=location_label,
    )

    fee_event = SwapEvent(
        timestamp=timestamp,
        location=location,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=ONE / 10,
        event_identifier=create_event_identifier(
            location=location,
            timestamp=timestamp,
            asset=A_USD,
            amount=ONE / 10,
            unique_id='fee',
        ),
        location_label=location_label,
    )

    # Add to database
    db_events = DBHistoryEvents(db)
    with db.user_write() as write_cursor:
        db_events.add_history_events(write_cursor, history=[spend_event, receive_event, fee_event])

    return spend_event.event_identifier, receive_event.event_identifier, fee_event.event_identifier


@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [19])
def test_migration_20_fix_swap_identifiers(database: DBHandler) -> None:
    """Test that migration 20 correctly fixes SwapEvent identifiers"""
    rotki = MockRotkiForMigrations(database)

    # Create broken swaps with different identifiers
    ts1 = TimestampMS(1000000)
    ts2 = TimestampMS(2000000)

    # Swap 1: ETH -> BTC with fee
    spend_id1, receive_id1, fee_id1 = create_broken_swap_events(
        db=database,
        timestamp=ts1,
        location=Location.BINANCE,
        location_label='binance1',
    )

    # Swap 2: ETH -> BTC without fee
    spend_event2 = SwapEvent(
        timestamp=ts2,
        location=Location.KRAKEN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=ONE * 5,
        event_identifier=create_event_identifier(
            location=Location.KRAKEN,
            timestamp=ts2,
            asset=A_ETH,
            amount=ONE * 5,
            unique_id='spend2',
        ),
    )

    receive_event2 = SwapEvent(
        timestamp=ts2,
        location=Location.KRAKEN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=ONE * 10,
        event_identifier=create_event_identifier(
            location=Location.KRAKEN,
            timestamp=ts2,
            asset=A_BTC,
            amount=ONE * 10,
            unique_id='receive2',
        ),
    )

    db_events = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        db_events.add_history_events(write_cursor, history=[spend_event2, receive_event2])

    spend_id2 = spend_event2.event_identifier
    receive_id2 = receive_event2.event_identifier

    # Also create a correctly linked swap (should not be touched by migration)
    correct_events = create_swap_events(
        timestamp=TimestampMS(3000000),
        location=Location.COINBASE,
        spend=AssetAmount(asset=A_ETH, amount=ONE * 3),
        receive=AssetAmount(asset=A_BTC, amount=ONE * 6),
        event_identifier='correct_swap_id',
    )

    with database.user_write() as write_cursor:
        db_events.add_history_events(write_cursor, history=correct_events)

    correct_id = correct_events[0].event_identifier

    # Verify the broken state before migration
    with database.conn.read_ctx() as cursor:
        # First swap has 3 different identifiers
        events1 = cursor.execute(
            """SELECT event_identifier, subtype FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?
               ORDER BY sequence_index""",
            (ts1, Location.BINANCE.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert len(events1) == 3
        assert events1[0][0] == spend_id1
        assert events1[1][0] == receive_id1
        assert events1[2][0] == fee_id1
        assert events1[0][0] != events1[1][0] != events1[2][0]  # All different

        # Second swap has 2 different identifiers
        events2 = cursor.execute(
            """SELECT event_identifier, subtype FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?
               ORDER BY sequence_index""",
            (ts2, Location.KRAKEN.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert len(events2) == 2
        assert events2[0][0] == spend_id2
        assert events2[1][0] == receive_id2
        assert events2[0][0] != events2[1][0]  # Different

        # Correct swap already has same identifier
        correct_events_check = cursor.execute(
            """SELECT event_identifier FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?""",
            (3000000, Location.COINBASE.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert all(event[0] == correct_id for event in correct_events_check)

    # Run the migration
    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[10]],  # Migration 20 is at index 10
    ):
        migration_manager = DataMigrationManager(rotki)
        migration_manager.maybe_migrate_data()

    # Verify the fix after migration
    with database.conn.read_ctx() as cursor:
        # First swap should now have same identifier (spend's identifier)
        events1_fixed = cursor.execute(
            """SELECT event_identifier, subtype FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?
               ORDER BY sequence_index""",
            (ts1, Location.BINANCE.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert len(events1_fixed) == 3
        assert events1_fixed[0][0] == spend_id1  # Spend keeps its ID
        assert events1_fixed[1][0] == spend_id1  # Receive now has spend's ID
        assert events1_fixed[2][0] == spend_id1  # Fee now has spend's ID

        # Second swap should now have same identifier
        events2_fixed = cursor.execute(
            """SELECT event_identifier, subtype FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?
               ORDER BY sequence_index""",
            (ts2, Location.KRAKEN.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert len(events2_fixed) == 2
        assert events2_fixed[0][0] == spend_id2  # Spend keeps its ID
        assert events2_fixed[1][0] == spend_id2  # Receive now has spend's ID

        # Correct swap should remain unchanged
        correct_events_check = cursor.execute(
            """SELECT event_identifier FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?""",
            (3000000, Location.COINBASE.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()
        assert all(event[0] == correct_id for event in correct_events_check)


@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [19])
def test_migration_20_edge_case_multiple_swaps(database: DBHandler) -> None:
    """Test the edge case where multiple swaps happen at same timestamp/location"""
    rotki = MockRotkiForMigrations(database)

    ts = TimestampMS(1000000)
    location = Location.BINANCE

    # Create two broken swaps at same timestamp/location
    # Swap 1: ETH -> BTC
    swap1_events = [
        SwapEvent(
            timestamp=ts,
            location=location,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=ONE,
            event_identifier=create_event_identifier(
                location=location,
                timestamp=ts,
                asset=A_ETH,
                amount=ONE,
                unique_id='swap1_spend',
            ),
        ),
        SwapEvent(
            timestamp=ts,
            location=location,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=ONE * 2,
            event_identifier=create_event_identifier(
                location=location,
                timestamp=ts,
                asset=A_BTC,
                amount=ONE * 2,
                unique_id='swap1_receive',
            ),
        ),
    ]

    # Swap 2: BTC -> ETH (reverse)
    swap2_events = [
        SwapEvent(
            timestamp=ts,
            location=location,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_BTC,
            amount=ONE * 3,
            event_identifier=create_event_identifier(
                location=location,
                timestamp=ts,
                asset=A_BTC,
                amount=ONE * 3,
                unique_id='swap2_spend',
            ),
        ),
        SwapEvent(
            timestamp=ts,
            location=location,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=ONE * 4,
            event_identifier=create_event_identifier(
                location=location,
                timestamp=ts,
                asset=A_ETH,
                amount=ONE * 4,
                unique_id='swap2_receive',
            ),
        ),
    ]

    db_events = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        db_events.add_history_events(write_cursor, history=swap1_events + swap2_events)

    # Run the migration
    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[10]],  # Migration 20 is at index 10
    ):
        migration_manager = DataMigrationManager(rotki)
        migration_manager.maybe_migrate_data()

    # Verify the fix - each swap should be grouped correctly
    with database.conn.read_ctx() as cursor:
        all_events = cursor.execute(
            """SELECT event_identifier, subtype, asset, amount FROM history_events
               WHERE timestamp = ? AND location = ? AND entry_type = ?
               ORDER BY identifier""",
            (ts, location.serialize_for_db(),
             HistoryBaseEntryType.SWAP_EVENT.serialize_for_db()),
        ).fetchall()

        # Group by event_identifier to verify correct pairing
        id_groups: dict[str, list[tuple[str, str, str]]] = {}
        for event_id, subtype, asset, amount in all_events:
            if event_id not in id_groups:
                id_groups[event_id] = []
            id_groups[event_id].append((subtype, asset, amount))

        # Should have 2 distinct event identifiers (2 swaps)
        assert len(id_groups) == 2

        # Each group should have a spend and receive
        for events in id_groups.values():
            subtypes = [e[0] for e in events]
            assert HistoryEventSubType.SPEND.serialize() in subtypes
            assert HistoryEventSubType.RECEIVE.serialize() in subtypes
            assert len(events) == 2
