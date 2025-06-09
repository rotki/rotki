import logging
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
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
                write_cursor.executemany(
                    'UPDATE history_events SET event_identifier = ? WHERE identifier = ?',
                    updates_to_apply,
                )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
