import logging
import time
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.concurrency import checkpoint
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import UnmatchedBridgeIssuePayload
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.bridges import (
    get_bridge_match_window,
    get_event_bridge_data,
    get_unmatched_bridge_events,
)
from rotkehlchen.types import EventMetricKey, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

type EventTypeSubtypePairs = set[tuple[HistoryEventType, HistoryEventSubType]]
type MetricRow = tuple[
    int | None,
    str,
    str | None,
    str | None,
    str,
    str,
    str,
    int,
    int,
    int,
]

# Event subtypes that route to a protocol bucket (single bucket).
# These represent positions within a protocol (e.g., generating debt).
PROTOCOL_BUCKET_SUBTYPES: Final = {
    HistoryEventSubType.GENERATE_DEBT,
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

# Kraken staking/unstaking events are internal spot <-> staking lock state changes.
# They don't move the asset out of the user's Kraken account, so they should not affect balances.
KRAKEN_INTERNAL_STAKING_EVENTS: Final[EventTypeSubtypePairs] = {
    (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
    (HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET),
}

# Events that affect both sender and receiver wallet buckets.
# Sender direction is OUT, receiver direction is IN.
DUAL_BUCKET_TRANSFER_EVENTS: Final[EventTypeSubtypePairs] = {
    (HistoryEventType.TRANSFER, HistoryEventSubType.NONE),
    (HistoryEventType.TRANSFER, HistoryEventSubType.DONATE),
}

METRICS_BATCH_SIZE: Final = 500
# How many events to process before voluntarily releasing the GIL, so concurrent
# DB readers (e.g. the history page) interleave instead of waiting out the switch
# interval per row while this pure-Python loop runs.
MIN_EVENTS_PROCESSED_TO_SLEEP: Final = 25


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
    def from_db(cls, row: tuple[str, str | None, str | None, str]) -> Bucket:
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
            event: HistoryBaseEntry,
            treat_eth2_as_eth: bool = False,
    ) -> list[tuple[Bucket, Literal[EventDirection.IN, EventDirection.OUT]]]:
        """Returns list of (Bucket, direction) pairs affected by this event.

        Handles the following cases:
        - Protocol deposits/withdrawals: affects both wallet and protocol buckets
        - Transfers: affects sender (OUT) and receiver (IN) wallet buckets.
        - Wrapped token deposits/redemptions: tracked as wallet-held asset conversions
        - Debt positions: tracked in protocol bucket
        - Everything else: tracked in wallet bucket
        """
        location = event.location.serialize_for_db()
        asset = (
            A_ETH.identifier if treat_eth2_as_eth is True and event.asset == A_ETH2 else
            event.asset.resolve_swapped_for().identifier
        )
        event_key = (event.event_type, event.event_subtype)
        counterparty = getattr(event, 'counterparty', None)
        address = getattr(event, 'address', None)

        if (
            location == Location.KRAKEN.serialize_for_db() and
            event_key in KRAKEN_INTERNAL_STAKING_EVENTS
        ):
            return []

        if (
            event.event_type == HistoryEventType.TRANSFER and
            event.location in ALL_SUPPORTED_EXCHANGES
        ):
            return []

        if (  # Depositing/withdrawing to protocols affects both wallet and protocol buckets
            event_key in DUAL_BUCKET_PROTOCOL_EVENTS and
            counterparty not in (None, '') and
            (wallet_direction := event.maybe_get_direction(for_balance_tracking=True)) is not None
        ):
            return [
                (cls(  # type: ignore[list-item]  # wallet_direction will not be neutral for dual bucket protocol events.
                    location=location,
                    location_label=event.location_label,
                    protocol=None,
                    asset=asset,
                ), wallet_direction),
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=counterparty,
                    asset=asset,
                ), EventDirection.IN if wallet_direction == EventDirection.OUT else EventDirection.OUT),  # noqa: E501
            ]

        if (  # Transfers affect both sender and receiver wallet buckets.
            event_key in DUAL_BUCKET_TRANSFER_EVENTS and
            address is not None
        ):
            return [
                (cls(
                    location=location,
                    location_label=event.location_label,
                    protocol=None,
                    asset=asset,
                ), EventDirection.OUT),
                (cls(
                    location=location,
                    location_label=address,
                    protocol=None,
                    asset=asset,
                ), EventDirection.IN),
            ]

        if (
            (direction := event.maybe_get_direction(for_balance_tracking=True)) is None or
            direction == EventDirection.NEUTRAL
        ):
            return []

        if event.event_subtype in PROTOCOL_BUCKET_SUBTYPES and counterparty not in (None, ''):
            return [(cls(
                location=location,
                location_label=event.location_label,
                protocol=counterparty,
                asset=asset,
            ), direction)]

        # Everything else: wallet bucket. Token protocol metadata describes asset identity,
        # not custody.
        return [(cls(
            location=location,
            location_label=event.location_label,
            protocol=None,
            asset=asset,
        ), direction)]


type ModifiedBucketData = tuple[TimestampMS, int]
type ModifiedBuckets = dict[Bucket, ModifiedBucketData]
type NegativeBalanceResolution = tuple[str, str | None, str | None, str, int]


def _load_bucket_balances_before_ts(
        database: DBHandler,
        from_ts: TimestampMS,
) -> dict[Bucket, FVal]:
    """Load the latest balance per bucket before from_ts.

    We use MAX(sort_key) to identify the most recent row per bucket,
    relying on SQLite's bare column behavior to return non-aggregated columns from
    that row. See https://www.sqlite.org/lang_select.html#bareagg
    """
    bucket_balances: dict[Bucket, FVal] = {}
    with database.conn.read_ctx() as cursor:
        treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
        cursor.execute(
            """
            SELECT location, location_label, protocol, asset, metric_value, MAX(sort_key)
            FROM event_metrics WHERE metric_key = ? AND timestamp < ?
            GROUP BY location, location_label, protocol, asset
            """,
            (EventMetricKey.BALANCE.serialize(), from_ts),
        )
        for row in cursor:
            asset = (
                A_ETH.identifier if treat_eth2_as_eth is True and row[3] == A_ETH2.identifier else
                row[3]
            )
            bucket = Bucket.from_db((row[0], row[1], row[2], asset))
            bucket_balances[bucket] = bucket_balances.get(bucket, ZERO) + FVal(row[4])

    log.debug('Loaded %s bucket balances before ts=%s', len(bucket_balances), from_ts)
    return bucket_balances


@skip_if_running
def process_historical_balances(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        from_ts: TimestampMS | None = None,
) -> None:
    """Process events and compute balance metrics."""
    log.debug(f'Starting historical balance processing from_ts={from_ts}')
    rebasing_token_ids = GlobalDBHandler.get_rebasing_token_ids()
    with database.user_write() as write_cursor:
        registry_from_ts = DBHistoryEvents(database).sync_rebasing_tokens(
            write_cursor=write_cursor,
            identifiers=rebasing_token_ids,
        )
    if registry_from_ts is not None and from_ts is not None:
        from_ts = min(from_ts, registry_from_ts)

    bucket_balances: dict[Bucket, FVal] = {}
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
        # Snapshot the modification timestamp after reading events. This allows us to
        # detect concurrent modifications: if the modification timestamp changed between
        # the read and processing completion, events were modified during processing.
        modification_ts_at_start = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value,),
        ).fetchone()
        modification_ts_at_start = (
            int(modification_ts_at_start[0])
            if modification_ts_at_start else None
        )
        treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
        rebasing_assets = frozenset(
            Asset(identifier).resolve_swapped_for().identifier
            for identifier in rebasing_token_ids
        )

    if (total_events := len(events)) == 0:
        log.debug('No events to process for historical balances')
        _finalize_processing(
            database=database,
            modification_ts_at_start=modification_ts_at_start,
        )
        return

    metrics_batch: list[MetricRow] = []
    modified_buckets: ModifiedBuckets = {}
    negative_balance_resolutions: list[NegativeBalanceResolution] = []
    first_batch_written, send_ws_every = False, msg_aggregator.how_many_events_per_ws(total_events)
    for idx, event in enumerate(events):
        for event_to_apply in events_to_apply if (events_to_apply := _maybe_add_profit_event(
            database=database,
            event=event,
            bucket_balances=bucket_balances,
            rebasing_assets=rebasing_assets,
            treat_eth2_as_eth=treat_eth2_as_eth,
        )) is not None else (event,):
            _apply_to_buckets(
                database=database,
                event=event_to_apply,
                bucket_balances=bucket_balances,
                metrics_batch=metrics_batch,
                modified_buckets=modified_buckets,
                negative_balance_resolutions=negative_balance_resolutions,
                last_run_ts=last_run_ts,
                rebasing_assets=rebasing_assets,
                treat_eth2_as_eth=treat_eth2_as_eth,
            )

        if idx % MIN_EVENTS_PROCESSED_TO_SLEEP == 0:
            time.sleep(0)  # release the GIL so concurrent DB readers interleave

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
            checkpoint()  # cancellation checkpoint of the balance processing loop
            time.sleep(0)

    if len(metrics_batch) != 0:
        with database.user_write() as write_cursor:
            _write_metrics_batch(
                write_cursor=write_cursor,
                metrics_batch=metrics_batch,
                from_ts=from_ts,
                first_batch_written=first_batch_written,
            )

    DataIssuesManager(database).resolve_negative_balance_issues(negative_balance_resolutions)

    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
            'total': total_events,
            'processed': total_events,
        },
    )
    _detect_unmatched_bridge_issues(database=database)
    _finalize_processing(database=database, modification_ts_at_start=modification_ts_at_start)
    log.debug(
        'Completed historical balance processing for %s events with %s modified buckets',
        total_events,
        len(modified_buckets),
    )


def _detect_unmatched_bridge_issues(database: DBHandler) -> None:
    """Surface bridge legs whose counterpart is unknown as data issues.

    A linked bridge pair is an internal transfer the scanner can follow across
    chains. An unlinked deposit past its bridge's settlement window means money
    left a tracked bucket for an unknown destination; an unlinked withdrawal is
    an inflow from an unknown source. Both are reported in the issues inbox and
    auto-resolved once the leg gets matched, ignored, or resolved as external.
    """
    deposits, withdrawals = get_unmatched_bridge_events(database=database)
    issues_manager = DataIssuesManager(database=database)
    now_ms = ts_sec_to_ms(ts_now())
    default_window = CachedSettings().get_settings().bridge_match_time_range
    unmatched_ids: set[int] = set()
    for direction, events in (('deposit', deposits), ('withdrawal', withdrawals)):
        for event in events:
            if event.identifier is None:
                continue

            counterparty = getattr(event, 'counterparty', None)
            window = get_bridge_match_window(
                counterparty=counterparty,
                default_window=default_window,
            ) if direction == 'deposit' else default_window  # grace so we don't race the matcher
            if now_ms < event.timestamp + window * 1000:
                continue  # the counterpart leg may still legitimately appear

            unmatched_ids.add(event.identifier)
            payload = UnmatchedBridgeIssuePayload(
                event_identifier=event.identifier,
                group_identifier=event.group_identifier,
                direction=direction,
            )
            if counterparty is not None:
                payload['counterparty'] = counterparty
            if len(bridge_data := get_event_bridge_data(event)) > 0:
                payload['bridge'] = bridge_data
            issues_manager.write_issue(
                kind=IssueKind.UNMATCHED_BRIDGE,
                location=event.location.serialize(),
                location_label=event.location_label,
                protocol=counterparty,
                asset=event.asset.identifier,
                payload=payload,
                ts_start=event.timestamp,
                ts_end=event.timestamp,
            )

    # System-resolve issues whose leg is no longer unmatched (got matched, ignored
    # or resolved as external). This is an observed fact, not a user/remediation
    # state transition, so it bypasses the state machine on purpose.
    with database.user_write() as write_cursor:
        query = (
            'UPDATE data_issues SET state = ?, resolved_at = ? WHERE kind = ? '
            'AND state != ? AND resolved_at IS NULL'
        )
        bindings: tuple = (
            IssueState.RESOLVED,
            ts_now(),
            IssueKind.UNMATCHED_BRIDGE,
            IssueState.DISMISSED,
        )
        if len(unmatched_ids) > 0:
            placeholders = ','.join(['?'] * len(unmatched_ids))
            query += f' AND event_identifier NOT IN ({placeholders})'
            bindings += tuple(unmatched_ids)
        write_cursor.execute(query, bindings)


def _finalize_processing(
        database: DBHandler,
        modification_ts_at_start: int | None,
) -> None:
    """Update cache timestamps. Only clears stale marker if no modifications during processing.

    Uses a snapshot of the modification timestamp taken after reading events. If the current
    modification timestamp is strictly greater than the snapshot, events were modified during
    processing and the stale marker is kept for the next run.
    """
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
            int(modification_ts[0]) > (modification_ts_at_start or 0)
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
        write_cursor: DBCursor,
        metrics_batch: list[MetricRow],
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
        database: DBHandler,
        event: HistoryBaseEntry,
        bucket_balances: dict[Bucket, FVal],
        metrics_batch: list[MetricRow],
        modified_buckets: ModifiedBuckets,
        negative_balance_resolutions: list[NegativeBalanceResolution],
        last_run_ts: Timestamp | None,
        rebasing_assets: frozenset[str],
        treat_eth2_as_eth: bool,
) -> None:
    """Apply the given event to the buckets it affects."""
    if len(bucket_directions := Bucket.from_event(
        event=event,
        treat_eth2_as_eth=treat_eth2_as_eth,
    )) == 0:
        return

    for bucket, direction in bucket_directions:
        if (current_balance := bucket_balances.get(bucket, ZERO)) < ZERO:
            continue

        if direction == EventDirection.IN:
            new_balance = current_balance + event.amount
        elif (new_balance := current_balance - event.amount) < ZERO:  # direction == EventDirection.OUT (direction from from_event will not be NEUTRAL) # noqa: E501
            assert event.identifier is not None, 'Processed history events should have identifiers'
            if bucket.asset in rebasing_assets:
                metrics_batch.append(_make_metric_row(
                    event=event,
                    bucket=bucket,
                    metric_key=EventMetricKey.REBASE_YIELD,
                    value=(rebase_yield := abs(new_balance)),
                ))
                negative_balance_resolutions.append((
                    bucket.location,
                    bucket.location_label,
                    bucket.protocol,
                    bucket.asset,
                    event.identifier,
                ))
                new_balance = current_balance + rebase_yield - event.amount
            else:
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
                DataIssuesManager(database).write_issue(
                    IssueKind.NEGATIVE_BALANCE,
                    location=bucket.location,
                    location_label=bucket.location_label,
                    protocol=bucket.protocol,
                    asset=bucket.asset,
                    payload={
                        'event_identifier': event.identifier,
                        'in_memory_negative_amount': str(new_balance),
                        'derived_balance_before_event': str(current_balance),
                    },
                    ts_start=event.timestamp,
                    ts_end=event.timestamp,
                )
                log.warning(
                    'Negative balance detected for %s at event %s. Skipping %s.',
                    event.asset.identifier,
                    event.identifier,
                    bucket,
                )
                bucket_balances[bucket] = new_balance
                continue

        bucket_balances[bucket] = new_balance
        metrics_batch.append(_make_metric_row(
            event=event,
            bucket=bucket,
            metric_key=EventMetricKey.BALANCE,
            value=new_balance,
        ))
        if event.identifier is not None:
            modified_buckets[bucket] = (event.timestamp, event.identifier)


def _make_metric_row(
        event: HistoryBaseEntry,
        bucket: Bucket,
        metric_key: EventMetricKey,
        value: FVal,
) -> MetricRow:
    metric_order = 0 if metric_key == EventMetricKey.REBASE_YIELD else 1
    return (
        event.identifier,
        bucket.location,
        bucket.location_label,
        bucket.protocol,
        metric_key.serialize(),
        str(value),
        bucket.asset,
        event.timestamp,
        event.sequence_index,
        (event.timestamp + event.sequence_index) * 2 + metric_order,
    )


def _maybe_add_profit_event(
        database: DBHandler,
        event: HistoryBaseEntry,
        bucket_balances: dict[Bucket, FVal],
        rebasing_assets: frozenset[str],
        treat_eth2_as_eth: bool,
) -> tuple[OnchainEvent, ...] | None:
    """Maybe add a receive/reward event for the profit earned while an asset was in a protocol.
    If the profit event is already present, take no action and return None. Otherwise, update the
    amount of the given withdrawal event, and create the profit event.
    Returns a tuple containing the new profit event and the updated withdrawal event or None
    if there is no profit event needed or if it is already present.
    """
    if CachedSettings().get_entry('auto_create_profit_events') is False:
        return None

    if len(bucket_directions := Bucket.from_event(
        event=event,
        treat_eth2_as_eth=treat_eth2_as_eth,
    )) == 0:
        return None

    for bucket, direction in bucket_directions:
        if (current_balance := bucket_balances.get(bucket, ZERO)) < ZERO:
            continue

        if (
            direction == EventDirection.OUT and
            (new_balance := current_balance - event.amount) < ZERO and
            bucket.asset not in rebasing_assets and
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
                (event.identifier, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.PROFIT_ADJUSTMENT.serialize_for_db()),  # noqa: E501
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
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.PROFIT_ADJUSTMENT},
        )
        profit_event.identifier = identifier
        return profit_event, event
