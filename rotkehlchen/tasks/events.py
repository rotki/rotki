import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.filtering import (
    HistoryEventFilterQuery,
    HistoryEventWithTxRefFilterQuery,
)
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

    # get all exchange asset movements
    asset_movements: list[AssetMovement]
    with database.conn.read_ctx() as cursor:
        if len(asset_movements := events_db.get_history_events_internal(  # type: ignore  # will be asset movements due to entry type filter.
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(entry_types=IncludeExcludeFilterData(
                values=[HistoryBaseEntryType.ASSET_MOVEMENT_EVENT],
            )),
        )) == 0:
            return

    # get list of asset movements that have already been matched
    with database.conn.read_ctx() as cursor:
        already_matched_list = {int(x[0]) for x in cursor.execute(
            'SELECT value FROM key_value_cache WHERE name LIKE ?',
            ('matched_asset_movement_%',),
        ).fetchall()}

    # for each asset movement, find a matching onchain event and update it.
    for asset_movement in asset_movements:
        if asset_movement.identifier in already_matched_list or asset_movement.asset.is_fiat():
            continue  # Fiat asset movements will not have corresponding onchain events

        if (matched_event := _find_asset_movement_match(
            events_db=events_db,
            asset_movement=asset_movement,
            is_deposit=(is_deposit := asset_movement.event_type == HistoryEventType.DEPOSIT),
        )) is None:
            continue  # No event found. Skip. Will retry next time this logic runs.

        # Modify the matched event
        if is_deposit:
            matched_event.event_type = HistoryEventType.WITHDRAWAL
            matched_event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            notes = 'Withdraw {amount} {asset} to {exchange}'
        else:
            matched_event.event_type = HistoryEventType.DEPOSIT
            matched_event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            notes = 'Deposit {amount} {asset} from {exchange}'

        matched_event.notes = notes.format(
            amount=matched_event.amount,
            asset=matched_event.asset.resolve_to_asset_with_symbol().symbol,
            exchange=asset_movement.location_label,
        )
        # This could also be a plain history event (i.e. a btc event, or custom event)
        # so only set counterparty if the event supports it.
        if isinstance(matched_event, OnchainEvent):
            matched_event.counterparty = asset_movement.location.name.lower()

        # Save the event and cache the matched identifiers
        with database.conn.write_ctx() as write_cursor:
            events_db.edit_history_event(
                write_cursor=write_cursor,
                event=matched_event,
            )
            database.set_dynamic_cache(  # type: ignore[call-overload]  # identifiers will not be None here since the events are from the db
                write_cursor=write_cursor,
                name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
                value=asset_movement.identifier,
                identifier=matched_event.identifier,
            )


def _find_asset_movement_match(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        is_deposit: bool,
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
        if event.amount != asset_movement.amount:
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
