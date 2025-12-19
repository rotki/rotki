import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.constants import CHAIN_EVENT_FIELDS, HISTORY_BASE_ENTRY_FIELDS
from rotkehlchen.db.filtering import HistoryEventWithTxRefFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ASSET_MOVEMENT_MATCH_WINDOW: Final = HOUR_IN_SECONDS


def process_events(
        chains_aggregator: 'ChainsAggregator',
        database: 'DBHandler',
) -> None:
    """Processes all events and modifies/combines them or aggregates processing results

    This is supposed to be a generic processing task that can be requested or run periodically
    """
    if (eth2 := chains_aggregator.get_module('eth2')) is not None:
        eth2.combine_block_with_tx_events()
        eth2.refresh_activated_validators_deposits()

    match_asset_movements(database)

    with database.user_write() as write_cursor:
        database.set_static_cache(  # update last event processing timestamp
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS,
            value=ts_now(),
        )


def match_asset_movements(database: 'DBHandler') -> None:
    """Analyze asset movements and find corresponding onchain events, then update those onchain
    events with proper event_type, counterparty, etc and cache the matched identifiers.
    """
    log.debug('Analyzing asset movements for corresponding onchain events...')
    events_db = DBHistoryEvents(database=database)
    asset_movements, fee_events = get_unmatched_asset_movements(database)
    for asset_movement in asset_movements:
        if (matched_event := _find_asset_movement_match(
            events_db=events_db,
            asset_movement=asset_movement,
            is_deposit=(is_deposit := asset_movement.event_type == HistoryEventType.DEPOSIT),
            fee_event=fee_events.get(asset_movement.group_identifier),
        )) is None:
            continue  # No event found. Skip. Will retry next time this logic runs.

        update_asset_movement_matched_event(
            events_db=events_db,
            asset_movement=asset_movement,
            matched_event=matched_event,
            is_deposit=is_deposit,
        )


def get_unmatched_asset_movements(
        database: 'DBHandler',
) -> tuple[list[AssetMovement], dict[str, AssetMovement]]:
    """Get all asset movements that have not been matched yet. Returns a tuple containing the list
    of asset movements and a dict of the corresponding fee events keyed by their group_identifier.
    """
    asset_movements: list[AssetMovement] = []
    fee_events: dict[str, AssetMovement] = {}
    with database.conn.read_ctx() as cursor:
        for entry in cursor.execute(
                f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {CHAIN_EVENT_FIELDS} FROM history_events '
                'LEFT JOIN chain_events_info ON history_events.identifier=chain_events_info.identifier '  # noqa: E501
                'WHERE history_events.entry_type=? AND history_events.identifier NOT IN '
                '(SELECT value FROM key_value_cache WHERE name LIKE ?) '
                'ORDER BY timestamp, sequence_index',
                (HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.value, 'matched_asset_movement_%'),
        ):
            if (asset_movement := AssetMovement.deserialize_from_db(entry[1:])).asset.is_fiat():
                continue

            if asset_movement.event_subtype == HistoryEventSubType.FEE:
                fee_events[asset_movement.group_identifier] = asset_movement
            else:
                asset_movements.append(asset_movement)

    return asset_movements, fee_events


def update_asset_movement_matched_event(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        matched_event: HistoryBaseEntry,
        is_deposit: bool,
) -> tuple[bool, str]:
    """Update the given matched event with proper event_type, counterparty, etc and cache the
    event identifiers. Returns a tuple containing a boolean indicating success and a string
    containing any error message.
    """
    if isinstance(matched_event, OnchainEvent):
        # This could also be a plain history event (i.e. a btc event, or custom event)
        # so only set counterparty if the event supports it.
        if matched_event.counterparty is not None:
            # This event has been decoded by a protocol decoder and likely isn't the match
            # TODO: Figure out how to handle some cases like swaps and bridging where a
            # protocol event could be the corresponding event for an asset movement.
            return False, 'Event already has a counterparty set'

        matched_event.counterparty = asset_movement.location.name.lower()

    # Modify the matched event
    if is_deposit:
        matched_event.event_type = HistoryEventType.DEPOSIT
        matched_event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
        notes = 'Deposit {amount} {asset} to {exchange}'
    else:
        matched_event.event_type = HistoryEventType.WITHDRAWAL
        matched_event.event_subtype = HistoryEventSubType.REMOVE_ASSET
        notes = 'Withdraw {amount} {asset} from {exchange}'

    matched_event.notes = notes.format(
        amount=matched_event.amount,
        asset=matched_event.asset.resolve_to_asset_with_symbol().symbol,
        exchange=asset_movement.location_label,
    )

    if matched_event.extra_data is None:
        matched_event.extra_data = {}

    matched_event.extra_data['matched_asset_movement'] = {
        'group_identifier': asset_movement.group_identifier,
        'exchange': asset_movement.location.serialize(),
        'exchange_name': asset_movement.location_label,
    }

    # Save the event and cache the matched identifiers
    with events_db.db.conn.write_ctx() as write_cursor:
        events_db.edit_history_event(
            write_cursor=write_cursor,
            event=matched_event,
        )
        events_db.db.set_dynamic_cache(  # type: ignore[call-overload]  # identifiers will not be None here since the events are from the db
            write_cursor=write_cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            value=asset_movement.identifier,
            identifier=matched_event.identifier,
        )

    return True, ''


def _find_asset_movement_match(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        is_deposit: bool,
        fee_event: AssetMovement | None,
) -> HistoryBaseEntry | None:
    """Find an onchain event that matches the given asset movement.
    Returns the matching event or None if no match is found.
    """
    with events_db.db.conn.read_ctx() as cursor:
        asset_movement_timestamp = ts_ms_to_sec(asset_movement.timestamp)
        possible_matches = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventWithTxRefFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.SPEND, HistoryEventSubType.NONE),
                    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET),
                ] if is_deposit else [
                    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
                    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
                ],
                assets=(asset_movement.asset,),
                from_ts=Timestamp(asset_movement_timestamp - ASSET_MOVEMENT_MATCH_WINDOW),
                to_ts=Timestamp(asset_movement_timestamp + ASSET_MOVEMENT_MATCH_WINDOW),
            ),
        )

    close_matches = []
    for event in possible_matches:
        # Check for matching amount, or matching amount + fee for deposits. The fee doesn't need
        # to be included for withdrawals since the onchain event will happen after the fee is
        # already deducted and the amount should always match the main asset movement amount.
        if not (event.amount == asset_movement.amount or (
            is_deposit and
            fee_event is not None and
            fee_event.asset == asset_movement.asset and
            event.amount == (asset_movement.amount + fee_event.amount)
        )):
            log.debug(
                f'Excluding possible match for asset movement {asset_movement.group_identifier} '
                f'due to differing amount. Expected {asset_movement.amount} got {event.amount}',
            )
            continue

        close_matches.append(event)

    if len(close_matches) == 0:
        log.debug(f'No close matches found for asset movement {asset_movement.group_identifier}')
        return None

    if len(close_matches) > 1:  # Multiple close matches
        if (  # Maybe match by tx ref
            asset_movement.extra_data is not None and
            (tx_ref := asset_movement.extra_data.get('transaction_id')) is not None
        ):
            for event in close_matches:
                if isinstance(event, OnchainEvent) and str(event.tx_ref) == tx_ref:
                    return event

        log.debug(
            f'Multiple close matches found for '
            f'asset movement {asset_movement.group_identifier}.',
        )
        # TODO: add to a list of events that need user input and send a WS message to notify user.
        return None

    return close_matches[0]  # Only found one close match.
