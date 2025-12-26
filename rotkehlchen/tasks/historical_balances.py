import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import EventDirection, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Subtypes where asset enters/leaves PROTOCOL bucket (not wallet)
PROTOCOL_BUCKET_IN_SUBTYPES: Final = (
    HistoryEventSubType.RECEIVE_WRAPPED,
    HistoryEventSubType.GENERATE_DEBT,
)
PROTOCOL_BUCKET_OUT_SUBTYPES: Final = (
    HistoryEventSubType.RETURN_WRAPPED,
    HistoryEventSubType.PAYBACK_DEBT,
)


def get_bucket_for_event(event: 'HistoryBaseEntry') -> tuple[str, str | None, str | None, str]:
    """Returns (location, location_label, bucket_protocol, asset) bucket.

    Most events affect the wallet bucket (protocol=NULL).
    Only wrapped token receipts/returns and debt generation/payback
    affect protocol-specific buckets.
    """
    location = event.location.serialize_for_db()
    asset = event.asset.identifier
    if (
        (
            (counterparty := getattr(event, 'counterparty', None)) is not None and
            (direction := event.maybe_get_direction()) is not None
        ) and
        (
            (event.event_subtype in PROTOCOL_BUCKET_IN_SUBTYPES and direction == EventDirection.IN) or  # noqa: E501
            (event.event_subtype in PROTOCOL_BUCKET_OUT_SUBTYPES and direction == EventDirection.OUT)  # noqa: E501
        )
    ):
        return (location, event.location_label, counterparty, asset)

    return (location, event.location_label, None, asset)


def _load_bucket_balances_before_ts(
        database: 'DBHandler',
        from_ts: Timestamp,
) -> dict[tuple[str, str | None, str | None, str], FVal]:
    """Load the latest balance per bucket from event_metrics for events before from_ts.

    For each bucket (location, location_label, protocol, asset), we need the balance
    from the last event before from_ts. Query is ordered by timestamp DESC so first
    occurrence per bucket is the latest balance.
    """
    bucket_balances: dict[tuple[str, str | None, str | None, str], FVal] = {}
    with database.conn.read_ctx() as cursor:
        cursor.execute(
            """
            SELECT he.location, he.location_label, em.protocol, he.asset, em.metric_value
            FROM event_metrics em
            INNER JOIN history_events he ON em.event_identifier = he.identifier
            WHERE em.metric_key = 'balance' AND he.timestamp < ?
            ORDER BY he.timestamp DESC, he.sequence_index DESC
            """,
            (from_ts,),
        )
        for row in cursor:
            bucket = (row[0], row[1], row[2], row[3])
            if bucket not in bucket_balances:  # first occurrence = latest
                bucket_balances[bucket] = FVal(row[4])

    log.debug(f'Loaded {len(bucket_balances)} bucket balances before ts={from_ts}')
    return bucket_balances


def process_historical_balances(
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        from_ts: Timestamp | None = None,
) -> None:
    """Process events and compute balance metrics. Stops on negative balance."""
    log.debug(f'Starting historical balance processing from_ts={from_ts}')
    if from_ts is not None:  # Clear existing metrics if reprocessing from a timestamp
        with database.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM event_metrics WHERE event_identifier IN '
                '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                (from_ts,),
            )
        bucket_balances = _load_bucket_balances_before_ts(database, from_ts)
    else:
        bucket_balances = {}

    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        filter_query = HistoryEventFilterQuery.make(
            from_ts=from_ts,
            order_by_rules=[('timestamp', True), ('sequence_index', True)],
            exclude_ignored_assets=True,
            exclude_subtypes=[
                HistoryEventSubType.DEPOSIT_ASSET,
                HistoryEventSubType.REMOVE_ASSET,
            ],
        )
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=filter_query,
        )

    if (total_events := len(events)) == 0:
        log.debug('No events to process for historical balances')
        _finalize_processing(database)
        return

    metrics_batch: list[tuple[int | None, str | None, str, str]] = []
    send_ws_every = msg_aggregator.how_many_events_per_ws(total_events)
    for idx, event in enumerate(events):
        bucket = get_bucket_for_event(event)
        current = bucket_balances.get(bucket, ZERO)

        if (direction := event.maybe_get_direction()) == EventDirection.IN:
            new_balance = current + event.amount
        elif direction == EventDirection.OUT:
            if (new_balance := current - event.amount) < ZERO:
                # Negative balance - send notification and stop
                msg_aggregator.add_message(
                    message_type=WSMessageType.HISTORICAL_BALANCE_PROCESSING,
                    data={
                        'status': 'negative_balance',
                        'event_identifier': event.identifier,
                        'group_identifier': event.group_identifier,
                        'asset': event.asset.identifier,
                        'bucket': bucket,
                    },
                )
                log.warning(
                    f'Negative balance detected for {event.asset.identifier} '
                    f'at event {event.identifier}. Stopping processing.',
                )
                # Update timestamp for debounce but don't clear stale marker
                with database.user_write() as write_cursor:
                    database.set_static_cache(
                        write_cursor=write_cursor,
                        name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
                        value=ts_now(),
                    )
                return
        else:  # neutral
            new_balance = current

        bucket_balances[bucket] = new_balance
        metrics_batch.append((
            event.identifier,
            bucket[2],  # protocol
            'balance',
            str(new_balance),
        ))

        if idx % send_ws_every == 0:
            msg_aggregator.add_message(
                message_type=WSMessageType.PROGRESS_UPDATES,
                data={
                    'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
                    'total': total_events,
                    'processed': idx,
                },
            )

        if len(metrics_batch) >= 500:
            with database.user_write() as write_cursor:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO event_metrics '
                    '(event_identifier, protocol, metric_key, metric_value) '
                    'VALUES (?, ?, ?, ?)',
                    metrics_batch,
                )
            metrics_batch = []

    if len(metrics_batch) != 0:
        with database.user_write() as write_cursor:
            write_cursor.executemany(
                'INSERT OR REPLACE INTO event_metrics '
                '(event_identifier, protocol, metric_key, metric_value) '
                'VALUES (?, ?, ?, ?)',
                metrics_batch,
            )

    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
            'total': total_events,
            'processed': total_events,
        },
    )
    _finalize_processing(database)
    log.debug(f'Completed historical balance processing for {total_events} events')


def _finalize_processing(database: 'DBHandler') -> None:
    """Update cache timestamps and clear stale marker."""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
            value=ts_now(),
        )
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value,),
        )
