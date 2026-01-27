import logging
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, TypeAlias

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_VIRTUAL
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EventMetricKey, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_now_in_ms
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

EventTypeSubtypePairs: TypeAlias = set[tuple[HistoryEventType, HistoryEventSubType]]

# Event subtypes that route to a protocol bucket (single bucket).
# These represent positions within a protocol (e.g., receiving aTokens, generating debt).
PROTOCOL_BUCKET_SUBTYPES: Final = {
    HistoryEventSubType.RECEIVE_WRAPPED,
    HistoryEventSubType.GENERATE_DEBT,
    HistoryEventSubType.RETURN_WRAPPED,
    HistoryEventSubType.PAYBACK_DEBT,
}

# Protocol withdrawals that can trigger synthetic interest events when withdrawal exceeds deposit.
PROTOCOL_WITHDRAWAL_EVENTS: Final[EventTypeSubtypePairs] = {
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL),
    (HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET),
}

# Events that affect both wallet and protocol buckets.
# Wallet direction comes from get_event_direction, protocol direction is the opposite.
DUAL_BUCKET_PROTOCOL_EVENTS: Final[EventTypeSubtypePairs] = {
    *PROTOCOL_WITHDRAWAL_EVENTS,
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
    (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
}

# Events that affect both sender and receiver wallet buckets.
# Sender direction is OUT, receiver direction is IN.
DUAL_BUCKET_TRANSFER_EVENTS: Final[EventTypeSubtypePairs] = {
    (HistoryEventType.TRANSFER, HistoryEventSubType.NONE),
    (HistoryEventType.TRANSFER, HistoryEventSubType.DONATE),
}

# Events where wrapped tokens with a protocol attribute move between protocol buckets.
# Example: depositing Balancer LP into Aura gauge moves from balancer bucket to aura bucket.
DUAL_BUCKET_WRAPPED_EVENTS: Final[EventTypeSubtypePairs] = {
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED),
}

METRICS_BATCH_SIZE: Final = 500


def _get_asset_protocol(asset: 'Asset') -> str | None:
    if not asset.is_evm_token():
        return None
    try:
        return asset.resolve_to_evm_token().protocol
    except (UnknownAsset, WrongAssetType):
        return None


class Bucket(NamedTuple):
    """Represents a unique bucket for tracking historical balances.

    A bucket uniquely identifies where an asset balance is held:
    - location: The blockchain/exchange location (e.g., 'ethereum', 'kraken')
    - location_label: The specific address or account label
    - protocol: The DeFi protocol if funds are deposited there (e.g., 'aave'), or None for wallet
    - asset: The asset identifier
    """
    location: str
    location_label: str | None
    protocol: str | None
    asset: str

    @classmethod
    def from_db(cls, row: tuple[str, str | None, str | None, str]) -> 'Bucket':
        return cls(location=row[0], location_label=row[1], protocol=row[2], asset=row[3])

    def serialize(self) -> dict[str, str | None]:
        return {
            'asset': self.asset,
            'protocol': self.protocol,
            'location': Location.deserialize_from_db(self.location).serialize(),
            'location_label': self.location_label,
        }

    @classmethod
    def from_event(
            cls,
            event: 'HistoryBaseEntry',
    ) -> list[tuple['Bucket', Literal[EventDirection.IN, EventDirection.OUT]]]:
        """Returns list of (Bucket, direction) pairs affected by this event.

        Handles the following cases:
        - Protocol deposits/withdrawals: affects both wallet and protocol buckets
        - Transfers: affects sender (OUT) and receiver (IN) buckets. If the transferred
          asset has a protocol attribute (e.g., Curve LP, Balancer LP), both sender and
          receiver use that protocol's bucket; otherwise, wallet buckets are used.
        - Wrapped token deposits/redemptions: updates balances in both source and
          destination protocol buckets (e.g., depositing Balancer LP into Aura updates
          the Balancer bucket with OUT and the Aura bucket with IN)
        - Wrapped tokens and debt positions: tracked in protocol bucket
        - Everything else: tracked in wallet bucket
        """
        location = event.location.serialize_for_db()
        asset = event.asset.resolve_swapped_for().identifier
        event_key = (event.event_type, event.event_subtype)
        counterparty = getattr(event, 'counterparty', None)
        address = getattr(event, 'address', None)
        asset_protocol = _get_asset_protocol(event.asset)

        if (  # Depositing/withdrawing to protocols affects both wallet and protocol buckets
            event_key in DUAL_BUCKET_PROTOCOL_EVENTS and
            counterparty is not None and
            (wallet_direction := event.maybe_get_direction(for_balance_tracking=True)) is not None
        ):
            return [
                (cls(  # type: ignore[list-item]  # wallet_direction will not be neutral for dual bucket protocol events.
                    location=location,
                    location_label=event.location_label,
                    protocol=asset_protocol,
                    asset=asset,
                ), wallet_direction),
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=counterparty,
                    asset=asset,
                ), EventDirection.IN if wallet_direction == EventDirection.OUT else EventDirection.OUT),  # noqa: E501
            ]

        if (  # Transfers affect both sender and receiver. Protocol tokens use protocol buckets.
            event_key in DUAL_BUCKET_TRANSFER_EVENTS and
            address is not None
        ):
            return [
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=asset_protocol,
                    asset=asset,
                ), EventDirection.OUT),
                (cls(
                    location=location,
                    location_label=address,
                    protocol=asset_protocol,
                    asset=asset,
                ), EventDirection.IN),
            ]

        if (  # Wrapping protocol tokens moves between protocol buckets (e.g. Balancer LP to Aura)
            event_key in DUAL_BUCKET_WRAPPED_EVENTS and
            counterparty is not None and
            asset_protocol is not None
        ):
            if event_key == (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED):
                src_protocol, dst_protocol = asset_protocol, counterparty
            elif event_key == (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED):
                src_protocol, dst_protocol = counterparty, asset_protocol
            else:
                log.error(f'Unexpected event_key {event_key} in DUAL_BUCKET_WRAPPED_EVENTS')
                return []
            return [
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=src_protocol,
                    asset=asset,
                ), EventDirection.OUT),
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=dst_protocol,
                    asset=asset,
                ), EventDirection.IN),
            ]

        if (
            (direction := event.maybe_get_direction(for_balance_tracking=True)) is None or
            direction == EventDirection.NEUTRAL
        ):
            return []

        if (  # Wrapped tokens and debt positions are tracked in protocol buckets
            counterparty is not None and
            event.event_subtype in PROTOCOL_BUCKET_SUBTYPES
        ):
            return [(cls(
                location=location,
                location_label=event.location_label,
                protocol=counterparty,
                asset=asset,
            ), direction)]

        # Everything else: wallet bucket, or protocol bucket if asset has protocol
        return [(cls(
            location=location,
            location_label=event.location_label,
            protocol=asset_protocol,
            asset=asset,
        ), direction)]


def _load_bucket_balances_before_ts(
        database: 'DBHandler',
        from_ts: TimestampMS,
) -> dict[Bucket, FVal]:
    """Load the latest balance per bucket before from_ts.

    We use MAX(sort_key) to identify the most recent row per bucket,
    relying on SQLite's bare column behavior to return non-aggregated columns from
    that row. See https://www.sqlite.org/lang_select.html#bareagg
    """
    bucket_balances: dict[Bucket, FVal] = {}
    with database.conn.read_ctx() as cursor:
        cursor.execute(
            """
            SELECT location, location_label, protocol, asset, metric_value, MAX(sort_key)
            FROM event_metrics WHERE metric_key = ? AND timestamp < ?
            GROUP BY location, location_label, protocol, asset
            """,
            (EventMetricKey.BALANCE.serialize(), from_ts),
        )
        for row in cursor:
            bucket_balances[Bucket.from_db(row[:4])] = FVal(row[4])

    log.debug(f'Loaded {len(bucket_balances)} bucket balances before ts={from_ts}')
    return bucket_balances


@skip_if_running
def process_historical_balances(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        from_ts: TimestampMS | None = None,
) -> None:
    """Process events and compute balance metrics."""
    log.debug(f'Starting historical balance processing from_ts={from_ts}')
    processing_started_at, bucket_balances = ts_now_in_ms(), {}
    if from_ts is not None:
        bucket_balances = _load_bucket_balances_before_ts(database, from_ts)

    with database.conn.read_ctx() as cursor:
        last_run_ts = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
        )
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                from_ts=ts_ms_to_sec(from_ts) if from_ts is not None else None,
                order_by_rules=[('timestamp', True), ('sequence_index', True)],
                exclude_ignored_assets=True,
            ),
        )

    if (total_events := len(events)) == 0:
        log.debug('No events to process for historical balances')
        _finalize_processing(database=database, processing_started_at=processing_started_at)
        return

    metrics_batch: list[tuple[int | None, str, str | None, str | None, str, str, str, int, int, int]] = []  # noqa: E501
    first_batch_written, send_ws_every = False, msg_aggregator.how_many_events_per_ws(total_events)
    for idx, event in enumerate(events):
        for event_to_apply in events_to_apply if (events_to_apply := _maybe_add_profit_event(
            database=database,
            event=event,
            bucket_balances=bucket_balances,
        )) is not None else (event,):
            _apply_to_buckets(
                database=database,
                event=event_to_apply,
                bucket_balances=bucket_balances,
                metrics_batch=metrics_batch,
                last_run_ts=last_run_ts,
            )

        if idx % send_ws_every == 0:
            msg_aggregator.add_message(
                message_type=WSMessageType.PROGRESS_UPDATES,
                data={
                    'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
                    'total': total_events,
                    'processed': idx,
                },
            )

        if len(metrics_batch) >= METRICS_BATCH_SIZE:
            with database.user_write() as write_cursor:
                _write_metrics_batch(
                    write_cursor=write_cursor,
                    metrics_batch=metrics_batch,
                    from_ts=from_ts,
                    first_batch_written=first_batch_written,
                )
            first_batch_written, metrics_batch = True, []

    if len(metrics_batch) != 0:
        with database.user_write() as write_cursor:
            _write_metrics_batch(
                write_cursor=write_cursor,
                metrics_batch=metrics_batch,
                from_ts=from_ts,
                first_batch_written=first_batch_written,
            )

    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
            'total': total_events,
            'processed': total_events,
        },
    )
    _finalize_processing(database=database, processing_started_at=processing_started_at)
    log.debug(f'Completed historical balance processing for {total_events} events')


def _finalize_processing(database: 'DBHandler', processing_started_at: TimestampMS) -> None:
    """Update cache timestamps. Only clears stale marker if no modifications during processing."""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
            value=ts_now(),
        )

        if (
            (modification_ts := write_cursor.execute(
                'SELECT value FROM key_value_cache WHERE name = ?',
                (DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value,),
            ).fetchone()) is None or
            int(modification_ts[0]) >= processing_started_at
        ):
            if modification_ts is not None:
                log.debug(
                    'Events modified during historical balance processing, '
                    'keeping stale marker for next run',
                )
            return

        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?)',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value,
             DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value),
        )


def _write_metrics_batch(
        write_cursor: 'DBCursor',
        metrics_batch: list[tuple[int | None, str, str | None, str | None, str, str, str, int, int, int]],  # noqa: E501
        from_ts: TimestampMS | None,
        first_batch_written: bool,
) -> None:
    """Write metrics batch to DB, deleting old entries on first write."""
    if not first_batch_written:
        if from_ts is not None:
            write_cursor.execute(
                'DELETE FROM event_metrics WHERE event_identifier IN '
                '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                (from_ts,),
            )
        else:
            write_cursor.execute('DELETE FROM event_metrics')
    write_cursor.executemany(
        'INSERT OR REPLACE INTO event_metrics '
        '(event_identifier, location, location_label, protocol, metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '  # noqa: E501
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        metrics_batch,
    )


def _apply_to_buckets(
        database: 'DBHandler',
        event: 'HistoryBaseEntry',
        bucket_balances: dict[Bucket, FVal],
        metrics_batch: list[tuple[int | None, str, str | None, str | None, str, str, str, int, int, int]],  # noqa: E501
        last_run_ts: Timestamp | None,
) -> None:
    """Apply the given event to the buckets it affects."""
    if len(bucket_directions := Bucket.from_event(event)) == 0:
        return

    for bucket, direction in bucket_directions:
        if (current_balance := bucket_balances.get(bucket, ZERO)) < ZERO:
            continue

        if direction == EventDirection.IN:
            new_balance = current_balance + event.amount
        elif (new_balance := current_balance - event.amount) < ZERO:  # direction == EventDirection.OUT (direction from from_event will not be NEUTRAL) # noqa: E501
            database.msg_aggregator.add_message(
                message_type=WSMessageType.NEGATIVE_BALANCE_DETECTED,
                data={
                    'event_identifier': event.identifier,
                    'group_identifier': event.group_identifier,
                    'asset': event.asset.identifier,
                    'bucket': bucket.serialize(),
                    'balance_before': str(current_balance),
                    'last_run_ts': last_run_ts,
                },
            )
            log.warning(
                f'Negative balance detected for {event.asset.identifier} '
                f'at event {event.identifier}. Skipping {bucket}.',
            )
            bucket_balances[bucket] = new_balance
            continue

        bucket_balances[bucket] = new_balance
        metrics_batch.append((
            event.identifier,
            event.location.serialize_for_db(),
            bucket.location_label,
            bucket.protocol,
            EventMetricKey.BALANCE.serialize(),
            str(new_balance),
            bucket.asset,
            event.timestamp,
            event.sequence_index,
            event.timestamp + event.sequence_index,
        ))


def _maybe_add_profit_event(
        database: 'DBHandler',
        event: 'HistoryBaseEntry',
        bucket_balances: dict[Bucket, FVal],
) -> tuple[OnchainEvent, ...] | None:
    """Maybe add a receive/reward event for the profit earned while an asset was in a protocol.
    If the profit event is already present, take no action and return None. Otherwise, update the
    amount of the given withdrawal event, and create the profit event.
    Returns a tuple containing the new profit event and the updated withdrawal event or None
    if there is no profit event needed or if it is already present.
    """
    if CachedSettings().get_entry('auto_create_profit_events') is False:
        return None

    if len(bucket_directions := Bucket.from_event(event)) == 0:
        return None

    for bucket, direction in bucket_directions:
        if (current_balance := bucket_balances.get(bucket, ZERO)) < ZERO:
            continue

        if (
            direction == EventDirection.OUT and
            (new_balance := current_balance - event.amount) < ZERO and
            bucket.protocol is not None and
            (event.event_type, event.event_subtype) in PROTOCOL_WITHDRAWAL_EVENTS and
            isinstance(event, OnchainEvent)
        ):
            # Withdrawal exceeds deposit, meaning yield was earned. Only applies to
            # protocol withdrawals without wrapped tokens (WITHDRAW_FROM_PROTOCOL,
            # REMOVE_ASSET). Create a profit event to account for the earned yield.
            break  # Break loop and create profit event.
    else:
        return None  # no yield earned detected

    with database.conn.read_ctx() as cursor:
        if cursor.execute(
            'SELECT COUNT(*) FROM history_events he '
            'JOIN chain_events_info cei ON he.identifier = cei.identifier '
            'WHERE group_identifier=? AND type=? AND subtype=? '
            'AND location_label=? AND asset=? AND amount=? AND counterparty=?',
            (
                event.group_identifier,
                HistoryEventType.RECEIVE.serialize(),
                HistoryEventSubType.REWARD.serialize(),
                event.location_label,
                event.asset.identifier,
                str(profit_amount := abs(new_balance)),
                bucket.protocol,
            ),
        ).fetchone()[0] != 0:
            return None

    db_events = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        # If the entire amount of the withdrawal is profit, convert the withdrawal itself
        # to an receive/reward event
        if (new_withdraw_amount := event.amount - profit_amount) == ZERO:
            event.event_type = HistoryEventType.RECEIVE
            event.event_subtype = HistoryEventSubType.REWARD
            event.notes = f'Profit earned from {event.asset} in {bucket.protocol}'
            write_cursor.execute(
                'UPDATE history_events SET type=?, subtype=?, notes=? WHERE identifier=?',
                (
                    event.event_type.serialize(),
                    event.event_subtype.serialize(),
                    event.notes,
                    event.identifier,
                ),
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
                'VALUES(?, ?, ?)',
                (event.identifier, HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_VIRTUAL),
            )
            return (event,)

        # First increment the sequence indexes to ensure an unused index for the
        # new event. Can't adjust in a single query or it may try to set an index
        # to an existing index and cause unique constraint errors.
        write_cursor.execute(  # Increment but make negative so it is unique
            'UPDATE history_events SET sequence_index = -(sequence_index + 1) '
            'WHERE group_identifier = ? AND sequence_index >= ?',
            (event.group_identifier, event.sequence_index),
        )
        write_cursor.execute(  # Shift back to positive
            'UPDATE history_events SET sequence_index = -sequence_index '
            'WHERE group_identifier = ? AND sequence_index < 0',
            (event.group_identifier,),
        )
        # Update the amount of the withdrawal event in both the amount and notes columns.
        # Replace the amount in the notes with spaces on each side to prevent matching part of
        # an address or something if the amount is only a single digit.
        if event.notes is not None:
            event.notes = event.notes.replace(f' {event.amount} ', f' {new_withdraw_amount} ')
        event.amount = new_withdraw_amount
        write_cursor.execute(
            'UPDATE history_events SET amount=?, notes=? WHERE identifier=?',
            (str(event.amount), event.notes, event.identifier),
        )
        # Add the profit event
        identifier = db_events.add_history_event(
            write_cursor=write_cursor,
            event=(profit_event := type(event)(
                tx_ref=event.tx_ref,
                sequence_index=event.sequence_index,
                timestamp=event.timestamp,
                location=event.location,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=event.asset,
                amount=profit_amount,
                location_label=event.location_label,
                notes=f'Profit earned from {event.asset} in {bucket.protocol}',
                counterparty=bucket.protocol,
                address=event.address,
            )),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_VIRTUAL},
        )
        profit_event.identifier = identifier
        return profit_event, event
