import json
import logging
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.migration_utils import (
    create_swap_events_v47_v48,
    get_swap_spend_receive_v47_48,
)
from rotkehlchen.db.utils import unlock_database
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import AssetAmount, FVal, Location, Price
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SwapEventData(NamedTuple):
    """Data structure for a swap event during migration"""
    identifier: int
    event_identifier: str
    subtype: str
    sequence_index: int


@enter_exit_debug_log()
def data_migration_20(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.39.1

    Fix SwapEvent identifiers that were generated differently for spend/receive/fee parts
    before the fix in PR 10103. This migration groups SwapEvents by timestamp, location,
    and location_label, then ensures they all share the same event_identifier.
    """
    @progress_step(description='Fixing SwapEvent identifiers')
    def _fix_swap_event_identifiers(rotki: 'Rotkehlchen') -> None:
        """
        Fix SwapEvent identifiers by grouping related spend/receive/fee events.

        The migration handles these cases:
        1. Simple swaps: spend + receive events that have different identifiers
        2. Swaps with fees: spend + receive + fee events with different identifiers
        3. Multiple swaps at same timestamp/location: Groups them by sequence order
        4. Already correct swaps: Skips swaps that already share the same identifier
        """
        db = rotki.data.db

        # Cache serialized enum values to avoid repeated serialization
        spend_subtype = HistoryEventSubType.SPEND.serialize()
        receive_subtype = HistoryEventSubType.RECEIVE.serialize()
        fee_subtype = HistoryEventSubType.FEE.serialize()
        trade_type = HistoryEventType.TRADE.serialize()

        # Collect all identifier updates that need to be made
        updates_to_apply = []

        with db.conn.read_ctx() as cursor:
            # Get all SwapEvents ordered by timestamp, location, and sequence
            swap_events_cursor = cursor.execute("""
                SELECT
                    identifier,
                    event_identifier,
                    timestamp,
                    location,
                    location_label,
                    subtype,
                    sequence_index
                FROM history_events
                WHERE entry_type = ? AND type = ?
                ORDER BY timestamp, location, location_label, sequence_index
            """, (HistoryBaseEntryType.SWAP_EVENT.serialize_for_db(), trade_type))

            # Group events by (timestamp, location, location_label)
            # This groups all events that could potentially be part of the same swap(s)
            event_groups = defaultdict(list)
            for row in swap_events_cursor:
                (
                    identifier, event_identifier, timestamp, location,
                    location_label, subtype, sequence_index,
                ) = row
                key = (timestamp, location, location_label or '')
                event_groups[key].append(SwapEventData(
                    identifier=identifier,
                    event_identifier=event_identifier,
                    subtype=subtype,
                    sequence_index=sequence_index,
                ))

        # Process each timestamp/location group
        for group_key, events in event_groups.items():
            # Check if all events already share the same identifier
            unique_identifiers = {event.event_identifier for event in events}
            if len(unique_identifiers) == 1:
                continue  # Already fixed, skip this group

            # Separate events by subtype while preserving their order
            spend_events = []
            receive_events = []
            fee_events = []

            for event in events:
                if event.subtype == spend_subtype:
                    spend_events.append(event)
                elif event.subtype == receive_subtype:
                    receive_events.append(event)
                elif event.subtype == fee_subtype:
                    fee_events.append(event)

            # Match spend and receive events based on their order
            # For multiple swaps at the same timestamp/location, we rely on sequence_index
            # to determine which spend goes with which receive
            num_swaps = min(len(spend_events), len(receive_events))

            for i in range(num_swaps):
                spend = spend_events[i]
                receive = receive_events[i]

                # Use the spend event's identifier as the canonical identifier
                canonical_id = spend.event_identifier

                # Update receive event if it has a different identifier
                if receive.event_identifier != canonical_id:
                    updates_to_apply.append((canonical_id, receive.identifier))

                # Match fee events to swaps based on order
                # If there are N swaps and N fees, fee[i] belongs to swap[i]
                if i < len(fee_events):
                    fee = fee_events[i]
                    if fee.event_identifier != canonical_id:
                        updates_to_apply.append((canonical_id, fee.identifier))

            # Log edge cases where we have unmatched events
            if len(spend_events) != len(receive_events):
                log.warning(
                    f'Unmatched swap events at timestamp={group_key[0]}, '
                    f'location={group_key[1]}, location_label={group_key[2]}: '
                    f'{len(spend_events)} spends, {len(receive_events)} receives',
                )

        # Apply all updates in a single transaction
        if updates_to_apply:
            with db.user_write() as write_cursor:
                for update in updates_to_apply:
                    try:
                        write_cursor.execute(
                            'UPDATE history_events SET event_identifier = ? WHERE identifier = ?',
                            update,
                        )
                    except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                        rotki.msg_aggregator.add_error(
                            f'Failed to fix swap with group identifier {update[0]}. '
                            'Skipping it, check logs for more details',
                        )
                        log.error(f'During _fix_swap_event_identifiers found a conflict while applying update {update}. error: {e}. Skipping')  # noqa: E501

    @progress_step(description='Recovering lost trades from v1.39.0 upgrade')
    def _recover_lost_trades_from_v139_upgrade(rotki: 'Rotkehlchen') -> None:
        """Recover trades that were lost during the v1.38.4 to v1.39.0 database upgrade.

        During the upgrade, trades with the same location and empty link field had ID conflicts.
        Only the first trade was kept, while subsequent trades were silently dropped.
        This function attempts to recover those lost trades from a database backup.
        """
        db = rotki.data.db
        log.debug('checking for trades lost during v1.39.0 upgrade')

        # check if any events have location hash as their identifier
        # this indicates the upgrade bug affected this database
        location_hashes = tuple(hash_id(str(loc)) for loc in Location)
        placeholders = ','.join('?' * len(location_hashes))
        with db.conn.read_ctx() as cursor:
            if (affected_events_count := cursor.execute(
                f'SELECT COUNT(*) FROM history_events WHERE event_identifier IN ({placeholders})',
                location_hashes,
            ).fetchone()[0]) == 0:
                log.debug('no trades affected by v1.39.0 upgrade bug')
                return

        log.warning(
            f'found {affected_events_count} events with '
            'location-only identifiers, attempting recovery',
        )
        # look for v47 database backup (created before the problematic upgrade)
        if len(backup_files := sorted([
            p for p in rotki.data.db.user_data_dir.glob('*_rotkehlchen_db_v47.backup')
            if p.is_file()
        ])) == 0:
            log.error('no v47 backup found. cannot recover lost trades. aborting.')
            return

        log.debug(f'found backup at {(backup_path := backup_files[-1])}, proceeding with recovery')
        old_db_conn = DBConnection(
            path=str(backup_path),
            connection_type=DBConnectionType.USER,
            sql_vm_instructions_cb=db.sql_vm_instructions_cb,
        )
        try:
            unlock_database(
                db_connection=old_db_conn,
                password=db.password,
                sqlcipher_version=db.sqlcipher_version,
                apply_optimizations=False,  # we are only making a single read query so it's not needed  # noqa: E501
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            old_db_conn.close()
            log.error(f'failed to decrypt backup database. wrong password or corrupted file due to {e!s}')  # noqa: E501
            return

        try:  # create safety backup of current database before making changes
            current_backup = db.create_db_backup()
            safety_backup_path = db.user_data_dir / f'{ts_now()}_pre_recovery_v48.backup'
            shutil.move(src=current_backup, dst=safety_backup_path)
            log.debug(f'created safety backup at {safety_backup_path}')
        except OSError as e:
            log.error(f'failed to create safety backup: {e}. aborting recovery')
            return

        # recover manual trades (those with a broken link field) from the backup
        recovered_events = []
        with old_db_conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT timestamp, location, base_asset, quote_asset, type, '
                "amount, rate, fee, fee_currency, link, notes FROM trades WHERE link=''",
            )
            for row in cursor:
                spend, receive = get_swap_spend_receive_v47_48(
                    is_buy=row[4] in {'A', 'C'},  # A/C = buy/settlement buy; B,D = sell/settlement sell  # noqa: E501
                    base_asset=Asset(row[2]),
                    quote_asset=Asset(row[3]),
                    amount=FVal(row[5]),
                    rate=Price(FVal(row[6])),
                )
                recovered_events.extend(create_swap_events_v47_v48(
                    timestamp=ts_sec_to_ms(row[0]),
                    location=Location.deserialize_from_db(row[1]),
                    spend=spend,
                    receive=receive,
                    fee=AssetAmount(
                        asset=Asset(row[8]),
                        amount=FVal(row[7]),
                    ) if row[8] is not None and row[7] is not None else None,
                    location_label=None,
                    unique_id=row[9],
                    spend_notes=row[10],
                ))

        old_db_conn.close()
        with db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                f'DELETE FROM history_events WHERE event_identifier IN ({placeholders})',
                location_hashes,
            )
            log.debug(f'removed {affected_events_count} incorrectly imported events')
            for event in recovered_events:
                try:
                    write_cursor.execute(
                        'INSERT INTO history_events(entry_type, event_identifier, '
                        'sequence_index, timestamp, location, location_label, asset, amount, '
                        'notes, type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
                        (
                            event.entry_type.value,
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
                            json.dumps(event.extra_data) if event.extra_data else None,
                        ),
                    )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    log.error(f'failed to add swap event {event.serialize()} due to {e!s}. skipping.')  # noqa: E501

            log.debug(f'successfully recovered {write_cursor.rowcount} lost trade events')

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
