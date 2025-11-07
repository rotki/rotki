"""Test for data migration 20 - fixing SwapEvent identifiers"""
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD
from rotkehlchen.data_migrations.manager import MIGRATION_LIST, DataMigrationManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.utils import unlock_database
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_group_identifier
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations
from rotkehlchen.types import AssetAmount, Location, TimestampMS
from rotkehlchen.utils.misc import ts_now


def _insert_swap_events(db: DBHandler, events: list[SwapEvent]) -> None:
    """Insert swap events with raw SQL to avoid dependencies on changing DB methods"""
    with db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO history_events(event_identifier, sequence_index, timestamp, location, '
            'location_label, asset, amount, notes, type, subtype, identifier, entry_type, '
            'extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [(
                event.group_identifier,
                event.sequence_index,
                event.timestamp,
                event.location.serialize_for_db(),
                event.location_label,
                event.asset.identifier,
                str(event.amount),
                event.notes,
                event.event_type.serialize(),
                event.event_subtype.serialize(),
                event.identifier,
                event.entry_type.serialize_for_db(),
                event.extra_data,
            ) for event in events],
        )


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
        group_identifier=create_group_identifier(
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
        group_identifier=create_group_identifier(
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
        group_identifier=create_group_identifier(
            location=location,
            timestamp=timestamp,
            asset=A_USD,
            amount=ONE / 10,
            unique_id='fee',
        ),
        location_label=location_label,
    )

    # Add to database
    _insert_swap_events(db=db, events=[spend_event, receive_event, fee_event])

    return spend_event.group_identifier, receive_event.group_identifier, fee_event.group_identifier


def _init_v47_backup_conn(database, password: str | None) -> DBConnection:
    backup_db_path = Path(__file__).resolve().parent.parent / 'data' / 'v47_rotkehlchen.db'
    backup_copy_path = database.user_data_dir / f'{ts_now()}_rotkehlchen_db_v47.backup'
    shutil.copy(src=backup_db_path, dst=backup_copy_path)
    backup_conn = DBConnection(
        path=str(backup_db_path),
        connection_type=DBConnectionType.USER,
        sql_vm_instructions_cb=database.sql_vm_instructions_cb,
    )
    unlock_database(
        db_connection=backup_conn,
        password=password or database.password,
        sqlcipher_version=database.sqlcipher_version,
    )
    return backup_conn


@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_custom_database', ['v48_rotkehlchen.db'])
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
        group_identifier=create_group_identifier(
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
        group_identifier=create_group_identifier(
            location=Location.KRAKEN,
            timestamp=ts2,
            asset=A_BTC,
            amount=ONE * 10,
            unique_id='receive2',
        ),
    )

    _insert_swap_events(db=database, events=[spend_event2, receive_event2])

    spend_id2 = spend_event2.group_identifier
    receive_id2 = receive_event2.group_identifier

    # Also create a correctly linked swap (should not be touched by migration)
    correct_events = create_swap_events(
        timestamp=TimestampMS(3000000),
        location=Location.COINBASE,
        spend=AssetAmount(asset=A_ETH, amount=ONE * 3),
        receive=AssetAmount(asset=A_BTC, amount=ONE * 6),
        group_identifier='correct_swap_id',
    )

    _insert_swap_events(db=database, events=correct_events)

    correct_id = correct_events[0].group_identifier

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
@pytest.mark.parametrize('use_custom_database', ['v48_rotkehlchen.db'])
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
            group_identifier=create_group_identifier(
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
            group_identifier=create_group_identifier(
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
            group_identifier=create_group_identifier(
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
            group_identifier=create_group_identifier(
                location=location,
                timestamp=ts,
                asset=A_ETH,
                amount=ONE * 4,
                unique_id='swap2_receive',
            ),
        ),
    ]

    _insert_swap_events(db=database, events=swap1_events + swap2_events)
    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[10]]):  # Migration 20 is at index 10  # noqa: E501
        DataMigrationManager(rotki).maybe_migrate_data()

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


@pytest.mark.parametrize('use_custom_database', ['botched_v47_rotkehlchen.db'])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [19])
def test_migration_20_recover_lost_trades(database: DBHandler) -> None:
    """Test that migration 20 correctly recovers trades lost during v1.39.0 upgrade.

    The v1.39.0 upgrade had a bug where trades with the same location and empty link field
    would generate identical event identifiers. Since identifiers must be unique, only the
    first trade was kept while subsequent trades were silently dropped from the database.

    This test verifies that the recovery function:
    1. Detects affected databases by looking for events with location hash identifiers
    2. Finds and opens the v47 backup created before the problematic upgrade
    3. Extracts trades with empty link fields from the backup
    4. Converts them to the new SwapEvent format with proper unique event identifiers
    5. Removes the incorrectly imported events and replaces them with recovered ones
    """
    rotki = MockRotkiForMigrations(database)
    shutil.copy(
        src=(backup_db_path := Path(__file__).resolve().parent.parent / 'data' / 'v47_rotkehlchen.db'),  # noqa: E501
        dst=database.user_data_dir / f'{ts_now()}_rotkehlchen_db_v47.backup',
    )
    unlock_database(
        db_connection=(backup_conn := DBConnection(
            path=str(backup_db_path),
            connection_type=DBConnectionType.USER,
            sql_vm_instructions_cb=database.sql_vm_instructions_cb,
        )),
        password=database.password,
        sqlcipher_version=database.sqlcipher_version,
    )
    with backup_conn.read_ctx() as cursor:
        assert cursor.execute("SELECT timestamp, location, base_asset, quote_asset, type, amount, rate, fee, fee_currency, link, notes FROM trades WHERE link=''").fetchall() == [  # noqa: E501
            # Two trades at the same timestamp and same location
            (1749566127, 'A', 'ETH', 'USD', 'A', '10', '2732.36750009618', '12', 'USD', '', None),
            (1749566127, 'A', 'ETH', 'USD', 'A', '5', '2732.36750009618', None, None, '', ''),
            # Same location ('A') but different timestamps
            (1749566154, 'A', 'BTC', 'USD', 'A', '1', '108659.316521703', None, None, '', ''),
            (1749566160, 'A', 'BTC', 'USD', 'A', '2', '108659.316521703', None, None, '', ''),
        ]

    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[10]]):  # Migration 20 is at index 10  # noqa: E501
        DataMigrationManager(rotki).maybe_migrate_data()

    # comprehensive verification of the recovery results
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(  # the trigger events should be removed
            'SELECT COUNT(*) FROM history_events WHERE event_identifier = ?',
            (hash_id(str(Location.KRAKEN)),),
        ).fetchone()[0] == 0

        cursor.execute(  # fetch all recovered swap events
            """SELECT timestamp, location, asset, amount, type, subtype, notes, event_identifier
               FROM history_events
               WHERE entry_type = ?
               GROUP BY event_identifier, sequence_index
            """,
            (HistoryBaseEntryType.SWAP_EVENT.serialize_for_db(),),
        )
        expected_events = [
            # First trade(same timestamp and location)
            (1749566127000, 'A', 'USD', '27323.67500096180', 'trade', 'spend', None, (event_id_1 := '52ffa18967da0d9a29c0cb4c90999f00b578b4f509b674093e881bfd228ae043')),  # noqa: E501
            (1749566127000, 'A', 'ETH', '10', 'trade', 'receive', None, event_id_1),
            (1749566127000, 'A', 'USD', '12', 'trade', 'fee', None, event_id_1),

            # Second trade(same timestamp and location)
            (1749566127000, 'A', 'USD', '13661.83750048090', 'trade', 'spend', '', (event_id_2 := '58848cc2b8c6f3085a228f4f85777826e81879f43c3e8a6838ed67c5b54a5c45')),  # noqa: E501
            (1749566127000, 'A', 'ETH', '5', 'trade', 'receive', None, event_id_2),

            # Third trade(different timestamp but same location)
            (1749566160000, 'A', 'USD', '217318.633043406', 'trade', 'spend', '', (event_id_3 := '858c767c41df3e1a8d4a29bb9e9a8303f0e06efde643bb677f493ea4f1aa4f95')),  # noqa: E501
            (1749566160000, 'A', 'BTC', '2', 'trade', 'receive', None, event_id_3),

            # Fourth trade(different timestamp but same location)
            (1749566154000, 'A', 'USD', '108659.316521703', 'trade', 'spend', '', (event_id_4 := 'effef56a55330e3f4bf893757ea7c71d06078303ae09bcb93950a33a09f4aaac')),  # noqa: E501
            (1749566154000, 'A', 'BTC', '1', 'trade', 'receive', None, event_id_4),
        ]
        assert all(expected_events[i] == row for i, row in enumerate(cursor))

    assert len(list(database.user_data_dir.glob('*_pre_recovery_v48.backup'))) == 1  # verify the safety backup was created  # noqa: E501


@pytest.mark.parametrize('use_custom_database', ['botched_v47_rotkehlchen.db'])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [19])
def test_migration_20_recover_lost_trades_no_backup(database: DBHandler) -> None:
    """Test that recovery handles missing backup gracefully without data loss.

    When events with location hash identifiers are found but no v47 backup exists,
    the recovery should log an error and leave the database unchanged.
    """
    rotki = MockRotkiForMigrations(database)
    for backup in database.user_data_dir.glob('*_rotkehlchen_db_v47.backup'):  # ensure no v47 backups exist  # noqa: E501
        backup.unlink()

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 3
        before_events = cursor.execute('SELECT * FROM history_events').fetchall()

    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[10]]):  # Migration 20 is at index 10  # noqa: E501
        DataMigrationManager(rotki).maybe_migrate_data()

    with database.conn.read_ctx() as cursor:  # database should remain unchanged
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 3
        assert cursor.execute('SELECT * FROM history_events').fetchall() == before_events

    assert len(list(database.user_data_dir.glob('*_pre_recovery_v48.backup'))) == 0  # safety backup is not created  # noqa: E501


@pytest.mark.parametrize('use_custom_database', ['botched_v47_rotkehlchen.db'])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [19])
def test_migration_20_recover_lost_trades_wrong_password(database: DBHandler) -> None:
    """Test that recovery handles encrypted backup with wrong password gracefully.

    The v47 backup is encrypted with sqlcipher. If the password doesn't match,
    the recovery should fail safely without corrupting the current database.
    """
    rotki = MockRotkiForMigrations(database)
    unlock_database(
        db_connection=(backup_conn := DBConnection(
            path=str(database.user_data_dir / f'{ts_now()}_rotkehlchen_db_v47.backup'),
            connection_type=DBConnectionType.USER,
            sql_vm_instructions_cb=database.sql_vm_instructions_cb,
        )),
        password='wrong_password',
        sqlcipher_version=database.sqlcipher_version,
        apply_optimizations=False,
    )
    with backup_conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE trades (id INTEGER PRIMARY KEY)')
    backup_conn.close()

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 3
        before_events = cursor.execute('SELECT * FROM history_events').fetchall()

    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[10]]):  # Migration 20 is at index 10  # noqa: E501
        DataMigrationManager(rotki).maybe_migrate_data()

    with database.conn.read_ctx() as cursor:  # database should remain unchanged
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 3
        assert cursor.execute('SELECT * FROM history_events').fetchall() == before_events

    assert len(list(database.user_data_dir.glob('*_pre_recovery_v48.backup'))) == 0  # safety backup is not created  # noqa: E501
