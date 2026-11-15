"""Materialization of cost basis on history events, into the event_cost_basis table.

It is a sibling of the historical balance processing rather than a second writer of its walk.
The balance pass can add and rewrite events as it goes (the profit events of protocol
withdrawals), and it has to be able to go stale without the cost basis going stale and the
other way around, e.g. when the cost basis method changes. So the cost basis walks the events
on its own, after the balances, with its own stale markers. `process_balances_and_cost_basis`
is what gets scheduled, so that a single processing pass advances both.
"""
import json
import logging
import time
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.cost_basis.lots import (
    BasisSource,
    BucketLots,
    CostBasisDirection,
)
from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.concurrency import checkpoint
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import (
    MIN_EVENTS_PROCESSED_TO_SLEEP,
    Bucket,
    process_historical_balances,
)
from rotkehlchen.types import Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_now_in_ms
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.settings import DBSettings
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

type CostBasisRow = tuple[
    int,  # event_identifier
    str,  # location
    str | None,  # location_label
    str | None,  # protocol
    str,  # asset
    int,  # timestamp
    int,  # sequence_index
    str,  # direction
    str | None,  # lot_created_id
    str | None,  # basis_per_unit
    str | None,  # basis_source
    str | None,  # lots_consumed_json
    str | None,  # realized_pnl
    str | None,  # basis_removed
    str | None,  # post_spend_basis_remaining
    str,  # method
]

COST_BASIS_BATCH_SIZE: Final = 500


class _CostBasisPass:
    """The state of one walk over the events.

    Events before `from_ts` are only replayed to rebuild the lots of each bucket. Their rows
    stay as they are, and the basis of what they acquired is taken from those rows, so that the
    lots match what was materialized and no price is queried again.
    """

    def __init__(
            self,
            settings: DBSettings,
            from_ts: TimestampMS | None,
            stored_basis: dict[int, FVal],
    ) -> None:
        self.settings = settings
        self.from_ts = from_ts
        self.stored_basis = stored_basis
        self.method = settings.cost_basis_method.serialize()
        self.profit_currency = settings.main_currency.resolve_to_asset_with_oracles()
        self.lots = BucketLots[Bucket](settings)
        self.rows: list[CostBasisRow] = []
        self._prices: dict[tuple[str, Timestamp], Price | None] = {}
        # What a swap gives to each of its sides, keyed by the identifier of the side's event.
        self._swap_basis: dict[int, tuple[FVal, BasisSource]] = {}
        self._swap_proceeds: dict[int, tuple[FVal, bool]] = {}

    def _price(self, asset: Asset, timestamp: Timestamp) -> Price | None:
        """The price of the asset in the profit currency, or None if no oracle knows it.

        May raise NoPriceForGivenTimestamp if the price oracles are rate limited.
        """
        if asset == self.profit_currency:
            return Price(ONE)

        if (key := (asset.identifier, timestamp)) in self._prices:
            return self._prices[key]

        try:
            price: Price | None = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, RemoteError):
            price = None
        except NoPriceForGivenTimestamp as e:
            if e.rate_limited is True:
                raise
            price = None

        self._prices[key] = price
        return price

    def _price_swap(
            self,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            timestamp: Timestamp,
    ) -> None:
        """Value both sides of a swap at what was paid for it.

        A fiat side states that value itself. Otherwise it is the market price of what was
        given, or of what was received if what was given has no price.
        """
        assert out_event.identifier is not None
        assert in_event.identifier is not None
        out_price = self._price(asset=out_event.asset, timestamp=timestamp)
        in_price = self._price(asset=in_event.asset, timestamp=timestamp)
        source = BasisSource.PRICE_ORACLE
        if out_event.asset.is_fiat() and out_price is not None:
            total_paid, source = out_event.amount * out_price, BasisSource.EVENT_AMOUNT
        elif in_event.asset.is_fiat() and in_price is not None:
            total_paid = in_event.amount * in_price
        elif out_price is not None:
            total_paid = out_event.amount * out_price
        elif in_price is not None:
            total_paid = in_event.amount * in_price
        else:
            total_paid, source = ZERO, BasisSource.ZERO_COST

        self._swap_basis[in_event.identifier] = (total_paid / in_event.amount, source)
        self._swap_proceeds[out_event.identifier] = (
            total_paid / out_event.amount,
            in_event.asset.is_fiat() or self.settings.include_crypto2crypto,
        )

    def _add_row(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            direction: CostBasisDirection,
            lot_created_id: str | None = None,
            basis_per_unit: FVal | None = None,
            basis_source: BasisSource | None = None,
            lots_consumed: list[dict[str, str | bool]] | None = None,
            realized_pnl: FVal | None = None,
            basis_removed: FVal | None = None,
    ) -> None:
        assert event.identifier is not None
        is_spend = direction == CostBasisDirection.SPEND
        self.rows.append((
            event.identifier,
            bucket.location,
            bucket.location_label,
            bucket.protocol,
            bucket.asset,
            event.timestamp,
            event.sequence_index,
            direction.value,
            lot_created_id,
            None if basis_per_unit is None else str(basis_per_unit),
            None if basis_source is None else basis_source.value,
            None if lots_consumed is None else json.dumps(lots_consumed),
            None if realized_pnl is None else str(realized_pnl),
            None if basis_removed is None else str(basis_removed),
            str(self.lots.basis_remaining(bucket)) if is_spend else None,
            self.method,
        ))

    def _transfer(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            destination: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
    ) -> None:
        """Move the basis along with an asset that moves between two buckets of the user.

        If the source bucket holds less than what moves then the history of the rest is not
        known, and it arrives at the destination as a lot of this event with no basis.
        """
        moved = self.lots.transfer(
            source=source,
            destination=destination,
            asset=event.asset,
            amount=event.amount,
        )
        lot_ids = list(dict.fromkeys(entry.lot.lot_id for entry in moved))
        if (unknown_amount := event.amount - sum(entry.amount for entry in moved)) > ZERO:
            lot_ids.append(lot_id := str(event.identifier))
            self.lots.obtain(
                bucket=destination,
                lot_id=lot_id,
                amount=unknown_amount,
                basis_per_unit=ZERO,
                timestamp=timestamp,
            )

        if not is_stale:
            return

        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        self._add_row(
            event=event,
            bucket=source,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in moved],
            realized_pnl=ZERO,
            basis_removed=basis,
        )
        self._add_row(
            event=event,
            bucket=destination,
            direction=CostBasisDirection.RECEIVE,
            lot_created_id=','.join(lot_ids),
            basis_per_unit=basis / event.amount,
            basis_source=BasisSource.TRANSFER_IN,
        )

    def _receive(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
    ) -> None:
        assert event.identifier is not None
        basis_source = BasisSource.PRICE_ORACLE
        if not is_stale and (stored := self.stored_basis.get(event.identifier)) is not None:
            basis: FVal = stored
        elif (swap_basis := self._swap_basis.pop(event.identifier, None)) is not None:
            basis, basis_source = swap_basis
        elif (price := self._price(asset=event.asset, timestamp=timestamp)) is not None:
            basis = price
        else:
            basis, basis_source = ZERO, BasisSource.ZERO_COST

        self.lots.obtain(
            bucket=bucket,
            lot_id=(lot_id := str(event.identifier)),
            amount=event.amount,
            basis_per_unit=basis,
            timestamp=timestamp,
        )
        if is_stale:
            self._add_row(
                event=event,
                bucket=bucket,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=lot_id,
                basis_per_unit=basis,
                basis_source=basis_source,
            )

    def _spend(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
    ) -> None:
        assert event.identifier is not None
        result = self.lots.spend(
            bucket=bucket,
            asset=event.asset,
            amount=event.amount,
            timestamp=timestamp,
        )
        if not is_stale:
            return

        if (proceeds := self._swap_proceeds.pop(event.identifier, None)) is not None:
            rate, taxable = proceeds
        else:
            rate, taxable = self._price(asset=event.asset, timestamp=timestamp) or ZERO, True

        self._add_row(
            event=event,
            bucket=bucket,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in result.consumed],
            realized_pnl=result.taxable_amount * rate - result.taxable_basis if taxable else ZERO,
            basis_removed=result.basis_removed,
        )

    def apply(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
    ) -> None:
        """Apply the event to the lots of the buckets it affects.

        May raise NoPriceForGivenTimestamp if the price oracles are rate limited.
        """
        if event.identifier is None or event.amount == ZERO:
            return

        timestamp = ts_ms_to_sec(event.timestamp)
        if (
            (is_stale := self.from_ts is None or event.timestamp >= self.from_ts) and
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.SPEND and
            next_event is not None and
            next_event.identifier is not None and
            next_event.group_identifier == event.group_identifier and
            next_event.event_type == HistoryEventType.TRADE and
            next_event.event_subtype == HistoryEventSubType.RECEIVE and
            next_event.amount != ZERO
        ):
            self._price_swap(out_event=event, in_event=next_event, timestamp=timestamp)

        if event.asset.is_fiat() or len(bucket_directions := Bucket.from_event(
            event=event,
            treat_eth2_as_eth=treat_eth2_as_eth,
        )) == 0:
            return  # fiat has no cost basis to track

        if len(bucket_directions) == 1:
            if (bucket_direction := bucket_directions[0])[1] == EventDirection.IN:
                self._receive(event, bucket_direction[0], timestamp, is_stale)
            else:
                self._spend(event, bucket_direction[0], timestamp, is_stale)
            return

        source = next((b for b, d in bucket_directions if d == EventDirection.OUT), None)
        destination = next((b for b, d in bucket_directions if d == EventDirection.IN), None)
        if source is not None and destination is not None and source != destination:
            self._transfer(event, source, destination, timestamp, is_stale)


def _write_rows(
        write_cursor: DBCursor,
        rows: list[CostBasisRow],
        from_ts: TimestampMS | None,
        first_batch_written: bool,
) -> None:
    """Write a batch of rows, dropping the rows that are being replaced on the first write.

    The delete is what keeps a pass idempotent. The unique constraint of the table can not,
    since SQLite treats the NULL location labels and protocols of two rows as distinct.
    """
    if not first_batch_written:
        if from_ts is None:
            write_cursor.execute('DELETE FROM event_cost_basis')
        else:
            write_cursor.execute(
                'DELETE FROM event_cost_basis WHERE timestamp >= ? OR event_identifier IN '
                '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                (from_ts, from_ts),
            )

    write_cursor.executemany(
        'INSERT OR REPLACE INTO event_cost_basis(event_identifier, location, location_label, '
        'protocol, asset, timestamp, sequence_index, direction, lot_created_id, basis_per_unit, '
        'basis_source, lots_consumed_json, realized_pnl, basis_removed, '
        'post_spend_basis_remaining, method) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows,
    )


def _finalize_processing(database: DBHandler, modification_ts_at_start: int | None) -> None:
    """Record the pass, and clear the stale marker unless events changed while it ran."""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            value=ts_now(),
        )
        if (modification_ts := database.get_static_cache(
            cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        )) is None or int(modification_ts) > (modification_ts_at_start or 0):
            return

        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?)',
            (
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
                DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
            ),
        )


def _record_interrupted_pass(database: DBHandler) -> None:
    """Record a pass that stopped early, making sure that it is still seen as stale.

    A first pass has no stale marker to keep, so one that redoes everything is added.
    """
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            value=ts_now(),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES (?, ?), (?, ?)',
            (
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
                '0',
                DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
                str(ts_now_in_ms()),
            ),
        )


@skip_if_running
def process_cost_basis(database: DBHandler, msg_aggregator: MessagesAggregator) -> bool:
    """Materialize the cost basis of the history events that are stale.

    Processes everything on the first pass, and afterwards only from the stale marker forward.
    Rows of another cost basis method mean the method changed, which redoes everything.

    Returns True once the pass ran to completion, and False if it stopped because the price
    oracles are rate limited. In that case the stale marker is kept and the next pass redoes
    the same range, by then with the prices that were found cached. The ``skip_if_running``
    decorator returns None instead when another pass is running.
    """
    with database.conn.read_ctx() as cursor:
        settings = database.get_settings(cursor)
        stale_from_ts, last_processing_ts = database.get_static_caches(
            cursor=cursor,
            names=(
                DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            ),
        )
        if stale_from_ts is None and last_processing_ts is not None:
            return True  # nothing changed since the last pass

        from_ts: TimestampMS | None = None
        stored_basis: dict[int, FVal] = {}
        if (
            stale_from_ts is not None and
            last_processing_ts is not None and  # a first pass has no rows to resume from
            int(stale_from_ts) > 0 and
            cursor.execute(
                'SELECT COUNT(*) FROM event_cost_basis WHERE method != ?',
                (settings.cost_basis_method.serialize(),),
            ).fetchone()[0] == 0
        ):
            from_ts = TimestampMS(int(stale_from_ts))
            stored_basis = {
                event_identifier: FVal(basis_per_unit)
                for event_identifier, basis_per_unit in cursor.execute(
                    'SELECT event_identifier, basis_per_unit FROM event_cost_basis '
                    'WHERE direction = ? AND basis_source != ? AND timestamp < ?',
                    (CostBasisDirection.RECEIVE.value, BasisSource.TRANSFER_IN.value, from_ts),
                )
            }

        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                order_by_rules=[
                    ('timestamp', True),
                    ('sequence_index', True),
                    ('history_events_identifier', True),
                ],
                exclude_ignored_assets=True,
                exclude_untracked_withdrawals=True,
            ),
        )
        # Read after the events, so that an event modified from here on keeps the marker.
        modification_ts_at_start = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        )

    log.debug('Starting cost basis processing of %s events from_ts=%s', len(events), from_ts)
    treat_eth2_as_eth = settings.treat_eth2_as_eth
    cost_basis_pass = _CostBasisPass(settings=settings, from_ts=from_ts, stored_basis=stored_basis)
    first_batch_written, total_events = False, len(events)
    send_ws_every = msg_aggregator.how_many_events_per_ws(total_events)
    is_rate_limited = False
    for idx, event in enumerate(events):
        try:
            cost_basis_pass.apply(
                event=event,
                next_event=events[idx + 1] if idx + 1 < total_events else None,
                treat_eth2_as_eth=treat_eth2_as_eth,
            )
        except NoPriceForGivenTimestamp as e:
            log.warning('Stopping cost basis processing at event %s: %s', event.identifier, e)
            is_rate_limited = True
            break

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

        if len(cost_basis_pass.rows) >= COST_BASIS_BATCH_SIZE:
            with database.user_write() as write_cursor:
                _write_rows(write_cursor, cost_basis_pass.rows, from_ts, first_batch_written)
            first_batch_written, cost_basis_pass.rows = True, []
            checkpoint()  # cancellation checkpoint of the cost basis processing loop
            time.sleep(0)

    with database.user_write() as write_cursor:  # also when empty, to drop the replaced rows
        _write_rows(write_cursor, cost_basis_pass.rows, from_ts, first_batch_written)

    if is_rate_limited:
        _record_interrupted_pass(database)
        return False

    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
            'total': total_events,
            'processed': total_events,
        },
    )
    _finalize_processing(
        database=database,
        modification_ts_at_start=(
            None if modification_ts_at_start is None else int(modification_ts_at_start)
        ),
    )
    log.debug('Completed cost basis processing of %s events', total_events)
    return True


def process_balances_and_cost_basis(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        from_ts: TimestampMS | None = None,
        chains_aggregator: ChainsAggregator | None = None,
        skip_balances: bool = False,
) -> bool | None:
    """Process the historical balances and then the cost basis of the history events.

    The balances go first since their pass can still add events. `from_ts` only scopes the
    balances, the cost basis has its own stale marker. The completion of the balance
    processing is announced once the cost basis is done too, so that the progress that is
    shown covers both. Returns None if a balance pass is already running.
    """
    if skip_balances:
        process_cost_basis(database=database, msg_aggregator=msg_aggregator)
        return True

    if (processed := process_historical_balances(
        database=database,
        msg_aggregator=msg_aggregator,
        from_ts=from_ts,
        chains_aggregator=chains_aggregator,
        notify_completion=False,
    )) is None:
        return None

    try:
        process_cost_basis(database=database, msg_aggregator=msg_aggregator)
    finally:
        msg_aggregator.add_message(
            message_type=WSMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED,
            data={},
        )

    return processed
