"""Materialization of cost basis on history events, into the event_cost_basis table.

It is a sibling of the historical balance processing rather than a second writer of its walk.
The balance pass can add and rewrite events as it goes (the profit events of protocol
withdrawals), and it has to be able to go stale without the cost basis going stale and the
other way around, e.g. when the cost basis method changes. So the cost basis walks the events
on its own, after the balances, with its own stale markers. `process_balances_and_cost_basis`
is what gets scheduled, so that a single processing pass advances both.

Which buckets an event moves an asset between is decided as for the balances, so that the
lots of a bucket always add up to what it holds. What the accounting rules decide is what a
spend realizes, and which events are the two sides of a swap or of a basis transfer. An event
without a rule still moves lots, but realizes nothing. The per protocol accounting callbacks
of the PnL report are not applied.
"""
import json
import logging
import time
from itertools import starmap
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.cost_basis.lots import (
    BasisSource,
    BucketLots,
    CostBasisDirection,
)
from rotkehlchen.accounting.cost_basis.pnl import get_unprocessed_from_ts
from rotkehlchen.api.websockets.typedefs import (
    HistoricalBalanceProcessingPhase,
    ProgressUpdateSubType,
    WSMessageType,
)
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import AccountingRulesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.locations.constants import LOCATION_KRAKEN
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import (
    MIN_EVENTS_PROCESSED_TO_SLEEP,
    Bucket,
    process_historical_balances,
)
from rotkehlchen.types import Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from collections.abc import Sequence

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
    str | None,  # proceeds
    str | None,  # realized_pnl
    str | None,  # taxfree_pnl
    str | None,  # basis_removed
    str | None,  # post_spend_basis_remaining
    str,  # method
]

COST_BASIS_BATCH_SIZE: Final = 500
# Events walked between two checkpoints of the lots. Each one stores all lots still held, so
# this trades the space they take for how many events a pass replays before what is stale.
COST_BASIS_CHECKPOINT_INTERVAL: Final = 10_000


class _Rules:
    """The accounting rules of the user, as the PnL report resolves them for an event."""

    def __init__(self, database: DBHandler, cursor: DBCursor | None = None) -> None:
        self._by_event: dict[int, BaseEventSettings] = {}
        self._by_type: dict[
            tuple[HistoryEventType, HistoryEventSubType, str | None],
            BaseEventSettings,
        ] = {}
        for rule_info in DBAccountingRules(database).query_rules(
            filter_query=AccountingRulesFilterQuery.make(),
            cursor=cursor,
        )[0]:
            if not rule_info.is_event_specific:
                self._by_type[rule_info.event_key] = rule_info.rule
            elif rule_info.event_ids is not None:
                self._by_event.update(dict.fromkeys(rule_info.event_ids, rule_info.rule))

    def get(self, event: HistoryBaseEntry) -> BaseEventSettings | None:
        """The rule of the event itself, else of its type and counterparty, else of its type."""
        if event.identifier is not None and (rule := self._by_event.get(event.identifier)) is not None:  # noqa: E501
            return rule

        event_key = (event.event_type, event.event_subtype)
        if isinstance(event, OnchainEvent) and (
            rule := self._by_type.get((*event_key, event.counterparty))
        ) is not None:
            return rule

        return self._by_type.get((*event_key, None))


def _swap_leg_direction(
        event: HistoryBaseEntry,
        bucket_directions: Sequence[tuple[Bucket, EventDirection]],
) -> EventDirection | None:
    if event.asset.is_fiat():
        return event.maybe_get_direction()

    return bucket_directions[0][1] if len(bucket_directions) == 1 else None


class _CostBasisPass:
    """The state of one walk over the events.

    The walk starts from a checkpoint of the lots when there is one before `from_ts`. Events
    between the two are only replayed to rebuild the lots of each bucket. Their rows stay as
    they are, and the basis of what they acquired is taken from those rows, so that the lots
    match what was materialized and no price is queried again.
    """

    def __init__(
            self,
            settings: DBSettings,
            rules: _Rules,
            from_ts: TimestampMS | None,
            stored_basis: dict[int, FVal],
    ) -> None:
        self.settings = settings
        self.rules = rules
        self.from_ts = from_ts
        self.stored_basis = stored_basis
        self.method = settings.cost_basis_method.serialize()
        self.profit_currency = settings.main_currency.resolve_to_asset_with_oracles()
        self.lots = BucketLots[Bucket](settings)
        self.rows: list[CostBasisRow] = []
        self.blocked_buckets: set[Bucket] = set()
        self.invalid_amount_event_ids: set[int] = set()
        self.invalid_amount_issues: list[tuple[Bucket, HistoryBaseEntry]] = []
        self._prices: dict[tuple[str, Timestamp], Price | None] = {}
        # What a swap gives to each of its sides, keyed by the identifier of the side's event.
        self._swap_basis: dict[int, tuple[FVal, BasisSource]] = {}
        self._swap_proceeds: dict[int, tuple[FVal | None, bool, bool]] = {}
        # The receiving side of a basis transfer, which is applied along with its other side.
        self._basis_transfer_receives: set[int] = set()

    def _price(self, asset: Asset, timestamp: Timestamp) -> Price | None:
        """The price of the asset in the profit currency, or None if no oracle knows it.

        May raise NoPriceForGivenTimestamp or RemoteError if the price oracles are rate limited
        or fail transiently.
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
        except PriceQueryUnsupportedAsset:
            price = None
        except NoPriceForGivenTimestamp as e:
            if e.rate_limited or e.remote_error:
                raise
            price = None

        self._prices[key] = price
        return price

    def _price_swap(
            self,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            fee_events: Sequence[HistoryBaseEntry],
            timestamp: Timestamp,
            is_taxable: bool,
    ) -> None:
        """Value both sides and any fee legs of a swap at what was paid for it.

        A fiat side states that value itself. Otherwise it is the market price of what was
        given, or of what was received if what was given has no price. When
        `include_fees_in_cost_basis` is enabled, priced fee legs are folded into the acquired
        asset's basis (or subtracted from disposal proceeds when selling for fiat) and do not
        realize PnL on their own; otherwise they are treated as taxable fee spends. A swap
        between two crypto assets realizes nothing if the user does not count those as taxable.
        """
        assert out_event.identifier is not None
        assert in_event.identifier is not None
        out_price = self._price(asset=out_event.asset, timestamp=timestamp)
        in_price = self._price(asset=in_event.asset, timestamp=timestamp)
        source = BasisSource.PRICE_ORACLE
        if out_event.asset.is_fiat() and out_price is not None:
            base_total, source = out_event.amount * out_price, BasisSource.EVENT_AMOUNT
        elif in_event.asset.is_fiat() and in_price is not None:
            base_total = in_event.amount * in_price
        elif out_price is not None:
            base_total = out_event.amount * out_price
        elif in_price is not None:
            base_total = in_event.amount * in_price
        else:
            base_total, source = ZERO, BasisSource.ZERO_COST

        total_fees = ZERO
        if self.settings.include_fees_in_cost_basis:
            for fee_event in fee_events:
                if (fee_price := self._price(asset=fee_event.asset, timestamp=timestamp)) is not None:  # noqa: E501
                    total_fees += fee_event.amount * fee_price

        if in_event.asset.is_fiat():
            out_rate = (base_total - total_fees) / out_event.amount
            in_rate = base_total / in_event.amount
        else:
            in_total = base_total + total_fees
            if source == BasisSource.ZERO_COST and total_fees > ZERO:
                source = BasisSource.PRICE_ORACLE
            in_rate = in_total / in_event.amount
            out_rate = base_total / out_event.amount

        fee_proceeds: list[tuple[int, tuple[FVal | None, bool, bool]]] = []
        for fee_event in fee_events:
            assert fee_event.identifier is not None
            if fee_event.asset == self.profit_currency:
                fee_rate: FVal | None = ONE
            elif fee_event.asset == in_event.asset and source != BasisSource.ZERO_COST:
                fee_rate = in_rate
            elif fee_event.asset == out_event.asset and source != BasisSource.ZERO_COST:
                fee_rate = out_rate
            else:
                fee_rate = self._price(asset=fee_event.asset, timestamp=timestamp)
            fee_taxable = not self.settings.include_fees_in_cost_basis
            fee_proceeds.append((fee_event.identifier, (fee_rate, fee_taxable, fee_taxable)))

        self._swap_basis[in_event.identifier] = (in_rate, source)
        self._swap_proceeds[out_event.identifier] = (
            out_rate,
            is_taxable and (in_event.asset.is_fiat() or self.settings.include_crypto2crypto),
            False,
        )
        for fee_id, entry in fee_proceeds:
            self._swap_proceeds[fee_id] = entry

    def _add_row(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            direction: CostBasisDirection,
            lot_created_id: str | None = None,
            basis_per_unit: FVal | None = None,
            basis_source: BasisSource | None = None,
            lots_consumed: list[dict[str, str | int | bool]] | None = None,
            proceeds: FVal | None = None,
            realized_pnl: FVal | None = None,
            taxfree_pnl: FVal | None = None,
            basis_removed: FVal | None = None,
            post_spend_basis_remaining: FVal | None = None,
    ) -> None:
        assert event.identifier is not None
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
            None if proceeds is None else str(proceeds),
            None if realized_pnl is None else str(realized_pnl),
            None if taxfree_pnl is None else str(taxfree_pnl),
            None if basis_removed is None else str(basis_removed),
            str(post_spend_basis_remaining) if post_spend_basis_remaining is not None else None,
            self.method,
        ))

    def _transfer(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            destination: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
            in_event: HistoryBaseEntry | None = None,
    ) -> None:
        """Move the basis along with an asset that moves between two buckets of the user.

        `in_event` is the receiving side when it is an event of its own, as in a basis transfer
        to another asset. If the source bucket holds less than what moves then the history of
        the rest is not known, and it arrives at the destination as a lot of the receiving
        event with no basis.
        """
        received = event if in_event is None else in_event
        source_basis_before = (
            self.lots.basis_remaining(source) if is_stale and source == destination else None
        )
        moved = self.lots.transfer(
            source=source,
            destination=destination,
            asset=event.asset,
            amount=event.amount,
            destination_amount=received.amount,
            event=event,
        )
        lot_ids = list(dict.fromkeys(entry.lot.lot_id for entry in moved))
        if (unknown_amount := event.amount - sum(entry.amount for entry in moved)) > ZERO:
            lot_ids.append(lot_id := str(received.identifier))
            self.lots.obtain(
                bucket=destination,
                lot_id=lot_id,
                amount=unknown_amount * received.amount / event.amount,
                basis_per_unit=ZERO,
                timestamp=ts_ms_to_sec(received.timestamp),
            )

        if not (in_is_stale := self.from_ts is None or received.timestamp >= self.from_ts):
            return

        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        if is_stale:
            self._add_row(
                event=event,
                bucket=source,
                direction=CostBasisDirection.SPEND,
                lots_consumed=[entry.serialize() for entry in moved],
                realized_pnl=ZERO,
                basis_removed=basis,
                post_spend_basis_remaining=(
                    self.lots.basis_remaining(source) if source_basis_before is None
                    else source_basis_before - basis
                ),
            )
        if in_is_stale:
            self._add_row(
                event=received,
                bucket=destination,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=','.join(lot_ids),
                basis_per_unit=basis / received.amount,
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
            rule: BaseEventSettings | None,
    ) -> None:
        """Consume the lots of what is spent, and realize what the rule of the event says.

        A taxable spend realizes the difference between what the asset is worth and its basis
        if the rule counts the cost basis, and on top of that the whole amount as an expense if
        the rule counts the entire amount as spent. The lots are consumed in any case.
        """
        assert event.identifier is not None
        swap_proceeds = self._swap_proceeds.pop(event.identifier, None)
        result = self.lots.spend(
            bucket=bucket,
            asset=event.asset,
            amount=event.amount,
            timestamp=timestamp,
            event=event,
        )
        if not is_stale:
            return

        proceeds: FVal | None = None
        realized_pnl: FVal | None
        taxfree_pnl: FVal | None
        counts_cost_basis = False
        count_entire_amount_spend = False
        if swap_proceeds is not None:
            rate, counts_cost_basis, count_entire_amount_spend = swap_proceeds
        elif rule is not None:
            rate = self._price(asset=event.asset, timestamp=timestamp)
            counts_cost_basis = rule.taxable and rule.count_cost_basis_pnl
            count_entire_amount_spend = rule.taxable and rule.count_entire_amount_spend
        else:
            rate = None  # an event without a rule realizes nothing, so its worth is not needed

        if rate is not None:
            proceeds = event.amount * rate
            pnl = -proceeds if count_entire_amount_spend else ZERO
            if counts_cost_basis:
                pnl += result.taxable_amount * rate - result.taxable_basis
                taxfree_pnl = (
                    (event.amount - result.taxable_amount) * rate - result.taxfree_basis
                )
            else:
                taxfree_pnl = ZERO
            realized_pnl = pnl
        elif counts_cost_basis or count_entire_amount_spend:
            realized_pnl = taxfree_pnl = None
        else:
            realized_pnl = taxfree_pnl = ZERO

        self._add_row(
            event=event,
            bucket=bucket,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in result.consumed],
            proceeds=proceeds,
            realized_pnl=realized_pnl,
            taxfree_pnl=taxfree_pnl,
            basis_removed=result.basis_removed,
            post_spend_basis_remaining=self.lots.basis_remaining(bucket),
        )

    def _maybe_transfer_basis(
            self,
            event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            out_buckets: Sequence[tuple[Bucket, EventDirection]],
            timestamp: Timestamp,
            is_stale: bool,
            treat_eth2_as_eth: bool,
    ) -> bool:
        """Carry the basis from what the event gives to what the next event receives for it.

        Returns False if the events are not a single-bucket spend and receive, in which case
        each is left to be applied on its own. Asset normalization can put both in one bucket.
        """
        assert in_event.identifier is not None
        if len(out_buckets) != 1 or in_event.asset.is_fiat():
            return False

        in_buckets = Bucket.from_event(event=in_event, treat_eth2_as_eth=treat_eth2_as_eth)
        if (
            len(in_buckets) != 1 or
            out_buckets[0][1] != EventDirection.OUT or
            in_buckets[0][1] != EventDirection.IN or
            out_buckets[0][0] in self.blocked_buckets or
            in_buckets[0][0] in self.blocked_buckets
        ):
            return False

        self._basis_transfer_receives.add(in_event.identifier)
        self._transfer(
            event=event,
            source=out_buckets[0][0],
            destination=in_buckets[0][0],
            timestamp=timestamp,
            is_stale=is_stale,
            in_event=in_event,
        )
        return True

    @property
    def has_pending_pair(self) -> bool:
        """Whether the last applied event left state for the event after it.

        That state is what pairs the two sides of a swap or of a basis transfer.
        """
        return (
            len(self._swap_basis) != 0 or
            len(self._swap_proceeds) != 0 or
            len(self._basis_transfer_receives) != 0
        )

    def serialize_checkpoint(self, events_since_interval: int = 0) -> str:
        """The state of the pass that a later pass can resume from, see `restore_checkpoint`.

        Only valid between events with no pending pair, as the pairing state is not included.
        `events_since_interval` is 0 for a permanent interval checkpoint and positive for a
        terminal checkpoint that later incremental passes replace until the interval is reached.
        """
        next_order, buckets = self.lots.serialize_state()
        return json.dumps({
            'method': self.method,
            'next_order': next_order,
            'buckets': [[list(bucket), state] for bucket, state in buckets],
            'blocked_buckets': [list(bucket) for bucket in self.blocked_buckets],
            'invalid_amount_event_ids': list(self.invalid_amount_event_ids),
            'events_since_interval': events_since_interval,
        }, separators=(',', ':'))

    def restore_checkpoint(self, serialized: str) -> int | None:
        """Continue from a state written by `serialize_checkpoint`.

        Returns the checkpoint's `events_since_interval` count, or None leaving the pass as it
        is if the checkpoint is of another method.
        """
        if (state := json.loads(serialized))['method'] != self.method:
            return None

        self.lots.restore_state(
            next_order=state['next_order'],
            buckets=[(Bucket(*bucket), lots) for bucket, lots in state['buckets']],
        )
        self.blocked_buckets = set(starmap(Bucket, state['blocked_buckets']))
        self.invalid_amount_event_ids = set(state['invalid_amount_event_ids'])
        return int(state.get('events_since_interval', 0))

    def apply(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        """Apply the event to the lots of the buckets it affects.

        Afterwards only the next event (and swap fee events) can have pairing state left, see
        `has_pending_pair`. May raise NoPriceForGivenTimestamp or RemoteError if the price oracles
        are rate limited or fail transiently.
        """
        self._apply(
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        )
        if event.identifier is not None:  # a side that is not applied leaves its pairing state
            self._swap_basis.pop(event.identifier, None)
            self._swap_proceeds.pop(event.identifier, None)

    def _apply(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        if event.identifier is None or event.amount == ZERO:
            return

        if event.identifier in self._basis_transfer_receives:
            self._basis_transfer_receives.remove(event.identifier)
            return

        timestamp = ts_ms_to_sec(event.timestamp)
        is_stale = self.from_ts is None or event.timestamp >= self.from_ts
        bucket_directions = (
            [] if event.asset.is_fiat()
            else Bucket.from_event(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
        )
        if event.amount < ZERO:
            for bucket, _direction in bucket_directions:
                if bucket not in self.blocked_buckets:
                    self.blocked_buckets.add(bucket)
                    self.invalid_amount_event_ids.add(event.identifier)
                    if is_stale:
                        self.invalid_amount_issues.append((bucket, event))
            return

        rule = self.rules.get(event)
        if (
            rule is not None and
            rule.accounting_treatment is not None and
            next_event is not None and
            next_event.identifier is not None and
            next_event.group_identifier == event.group_identifier and
            next_event.amount > ZERO
        ):
            if rule.accounting_treatment == TxAccountingTreatment.BASIS_TRANSFER:
                if self._maybe_transfer_basis(
                    event=event,
                    in_event=next_event,
                    out_buckets=bucket_directions,
                    timestamp=timestamp,
                    is_stale=is_stale,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                ):
                    return
            elif (
                (
                    self.from_ts is None or
                    next_event.timestamp >= self.from_ts or
                    any(fee.timestamp >= self.from_ts for fee in swap_fee_events)
                ) and
                _swap_leg_direction(event, bucket_directions) == EventDirection.OUT and
                _swap_leg_direction(
                    next_event,
                    [] if next_event.asset.is_fiat() else Bucket.from_event(
                        event=next_event,
                        treat_eth2_as_eth=treat_eth2_as_eth,
                    ),
                ) == EventDirection.IN
            ):
                self._price_swap(
                    out_event=event,
                    in_event=next_event,
                    fee_events=swap_fee_events,
                    timestamp=timestamp,
                    is_taxable=rule.taxable,
                )

        if len(bucket_directions) == 0:
            return  # fiat has no cost basis to track

        if len(bucket_directions) == 1:
            bucket, direction = bucket_directions[0]
            if bucket in self.blocked_buckets:
                return

            if direction == EventDirection.IN:
                if (
                    self.settings.eth_staking_taxable_after_withdrawal_enabled and
                    event.location == LOCATION_KRAKEN and
                    event.asset == A_ETH2 and
                    event.event_type == HistoryEventType.STAKING and
                    event.event_subtype == HistoryEventSubType.REWARD and
                    timestamp < SHAPPELA_TIMESTAMP
                ):
                    return

                self._receive(event, bucket, timestamp, is_stale)
            else:
                self._spend(event, bucket, timestamp, is_stale, rule)
            return

        source = next((b for b, d in bucket_directions if d == EventDirection.OUT), None)
        destination = next((b for b, d in bucket_directions if d == EventDirection.IN), None)
        if (
            source is not None and
            destination is not None and
            source != destination and
            source not in self.blocked_buckets and
            destination not in self.blocked_buckets
        ):
            self._transfer(event, source, destination, timestamp, is_stale)


def _write_rows(
        write_cursor: DBCursor,
        rows: list[CostBasisRow],
        from_ts: TimestampMS | None,
        first_batch_written: bool,
) -> None:
    """Write a batch of rows, dropping the rows that are being replaced on the first write.

    The delete is what keeps a pass idempotent. The unique constraint of the table can not,
    since SQLite treats the NULL location labels and protocols of two rows as distinct. The
    checkpoints after `from_ts` hold lots that the stale events may change, and go with them.
    """
    if not first_batch_written:
        if from_ts is None:
            write_cursor.execute('DELETE FROM event_cost_basis')
            write_cursor.execute('DELETE FROM cost_basis_checkpoints')
        else:
            write_cursor.execute(
                'DELETE FROM event_cost_basis WHERE timestamp >= ? OR event_identifier IN '
                '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                (from_ts, from_ts),
            )
            write_cursor.execute(
                'DELETE FROM cost_basis_checkpoints WHERE timestamp > ?',
                (from_ts,),
            )

    write_cursor.executemany(
        'INSERT OR REPLACE INTO event_cost_basis(event_identifier, location, location_label, '
        'protocol, asset, timestamp, sequence_index, direction, lot_created_id, basis_per_unit, '
        'basis_source, lots_consumed_json, proceeds, realized_pnl, taxfree_pnl, basis_removed, '
        'post_spend_basis_remaining, method) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows,
    )


def _collect_swap_fee_events(
        events: Sequence[HistoryBaseEntry],
        out_idx: int,
) -> list[HistoryBaseEntry]:
    """Collect fee events immediately following the (out, in) pair of a swap group."""
    out_event = events[out_idx]
    fee_events: list[HistoryBaseEntry] = []
    fee_idx = out_idx + 2
    while fee_idx < len(events):
        candidate = events[fee_idx]
        if (
            candidate.group_identifier != out_event.group_identifier or
            candidate.event_type != out_event.event_type or
            candidate.event_subtype != HistoryEventSubType.FEE
        ):
            break
        if candidate.identifier is not None and candidate.amount > ZERO:
            fee_events.append(candidate)
        fee_idx += 1
    return fee_events


def _write_checkpoint(
        write_cursor: DBCursor,
        cost_basis_pass: _CostBasisPass,
        timestamp: TimestampMS,
        events_since_interval: int = 0,
        replace_timestamp: TimestampMS | None = None,
) -> None:
    """Store the lots of the pass as they are after all events before `timestamp`."""
    if replace_timestamp is not None and replace_timestamp != timestamp:
        write_cursor.execute(
            'DELETE FROM cost_basis_checkpoints WHERE timestamp = ?',
            (replace_timestamp,),
        )
    write_cursor.execute(
        'INSERT OR REPLACE INTO cost_basis_checkpoints(timestamp, state) VALUES (?, ?)',
        (timestamp, cost_basis_pass.serialize_checkpoint(events_since_interval)),
    )


def _checkpoint_ts(
        cost_basis_pass: _CostBasisPass,
        event: HistoryBaseEntry,
        next_event: HistoryBaseEntry | None,
        events_since_checkpoint: int,
) -> TimestampMS | None:
    """The timestamp to checkpoint the lots at after the event, or None if not here.

    A checkpoint holds all events before its timestamp, so it can only be taken where the
    timestamp moves on to the next event and no pair of events is halfway applied.
    """
    if (
        events_since_checkpoint < COST_BASIS_CHECKPOINT_INTERVAL or
        next_event is None or
        next_event.timestamp <= event.timestamp or
        cost_basis_pass.has_pending_pair
    ):
        return None

    return next_event.timestamp


def _record_progress(
        write_cursor: DBCursor,
        processed_ts: TimestampMS,
        modification_ts_at_start: str | None,
) -> None:
    """Record that the pass wrote the rows of all events before `processed_ts`.

    It is written along with those rows, so that they can be read while the pass goes on. The
    modification marker the pass started with is kept with it, since a change to the events or
    the settings after that may make the rows outdated.
    """
    write_cursor.executemany(
        'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
        [
            (DBCacheStatic.COST_BASIS_PASS_PROCESSED_TS.value, str(processed_ts)),
            (DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS.value, modification_ts_at_start or '0'),
        ],
    )


def _write_invalid_amount_issues(
        database: DBHandler,
        issues: list[tuple[Bucket, HistoryBaseEntry]],
) -> None:
    if len(issues) == 0:
        return

    issues_manager = DataIssuesManager(database)
    for bucket, event in issues:
        assert event.identifier is not None
        issues_manager.write_issue(
            kind=IssueKind.INVALID_EVENT_AMOUNT,
            location=bucket.location,
            location_label=bucket.location_label,
            protocol=bucket.protocol,
            asset=bucket.asset,
            payload={
                'event_identifier': event.identifier,
                'amount': str(event.amount),
            },
            ts_start=event.timestamp,
            ts_end=event.timestamp,
        )
        log.warning(
            'Invalid event amount %s for %s at event %s. Skipping %s for cost basis.',
            event.amount,
            event.asset.identifier,
            event.identifier,
            bucket,
        )


def _finalize_processing(
        database: DBHandler,
        modification_ts_at_start: int | None,
        interrupted_at: TimestampMS | None = None,
) -> None:
    """Record the pass, and clear or advance the stale marker if nothing changed while it ran.

    The progress of the pass is dropped, since the stale marker covers what is left to do.

    Events that changed keep the marker they set, and so does a change of the cost basis
    settings, which wipes what the pass wrote. A pass that stopped early advances the marker to
    the event it stopped at, so earlier events are no longer seen as stale.
    """
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            value=ts_now(),
        )
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?, ?)',
            (
                DBCacheStatic.COST_BASIS_PASS_PROCESSED_TS.value,
                DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS.value,
                DBCacheStatic.LAST_COST_BASIS_FAILURE_TS.value,
            ),
        )
        modification_ts = database.get_static_cache(
            cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        )
        if modification_ts is not None and int(modification_ts) > (modification_ts_at_start or 0):
            if interrupted_at is not None and (
                (stale_from_ts := database.get_static_cache(
                    cursor=write_cursor,
                    name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                )) is None or int(stale_from_ts) > interrupted_at
            ):
                database.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                    value=str(interrupted_at),
                )
            return

        if interrupted_at is not None:
            write_cursor.executemany(
                'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
                [
                    (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, str(interrupted_at)),
                    (DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value, '0'),
                ],
            )
            return

        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name IN (?, ?)',
            (
                DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,
                DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
            ),
        )


def _record_failure(
        database: DBHandler,
        cost_basis_pass: _CostBasisPass,
        modification_ts_at_start: str | None,
) -> None:
    """Record that a pass failed, keeping what it committed usable by the next pass.

    If nothing changed the events since the pass started, both modification markers are reset
    together, so that the progress the pass recorded still matches the stale marker.
    """
    _write_invalid_amount_issues(database, cost_basis_pass.invalid_amount_issues)
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_COST_BASIS_FAILURE_TS,
            value=ts_now(),
        )
        if modification_ts_at_start is not None:
            write_cursor.execute(
                'UPDATE key_value_cache SET value = ? WHERE name IN (?, ?) AND value = ?',
                (
                    '0',
                    DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS.value,
                    DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS.value,
                    modification_ts_at_start,
                ),
            )


@skip_if_running
def process_cost_basis(database: DBHandler, msg_aggregator: MessagesAggregator) -> bool:
    """Materialize the cost basis of the history events that are stale.

    Processes everything on the first pass, and afterwards only from the stale marker forward.
    Rows of another cost basis method mean the method changed, which redoes everything. A pass
    that only redoes a part starts from the last checkpoint of the lots before that part, so
    it reads and replays only the events after the checkpoint.

    Returns True once the pass ran to completion, and False if it stopped because the price
    oracles are rate limited or failed transiently. In that case the stale marker is kept and the
    next pass redoes the same range, by then with the prices that were found cached. The
    ``skip_if_running`` decorator returns None instead when another pass is running.
    """
    with database.conn.read_ctx() as cursor:
        # Capture before reading settings, rules, checkpoints, or events so any concurrent change
        # during startup bumps the marker past this value and keeps the stale marker at completion.
        modification_ts_at_start = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
        )
        if (
            unprocessed_from_ts := get_unprocessed_from_ts(cursor=cursor, database=database)
        ) is None:
            return True  # nothing changed since the last pass

        settings = database.get_settings(cursor)
        rules = _Rules(database=database, cursor=cursor)
        from_ts: TimestampMS | None = None
        if (
            unprocessed_from_ts > 0 and
            cursor.execute('SELECT 1 FROM event_cost_basis LIMIT 1').fetchone() is not None and
            cursor.execute(
                'SELECT 1 FROM event_cost_basis WHERE method != ? LIMIT 1',
                (settings.cost_basis_method.serialize(),),
            ).fetchone() is None
        ):
            from_ts = unprocessed_from_ts

        cost_basis_pass = _CostBasisPass(
            settings=settings,
            rules=rules,
            from_ts=from_ts,
            stored_basis={},
        )
        start_ts = TimestampMS(0)
        restored_terminal_ts: TimestampMS | None = None
        events_since_interval = 0
        if from_ts is not None:
            if (checkpoint_row := cursor.execute(
                'SELECT timestamp, state FROM cost_basis_checkpoints WHERE timestamp <= ? '
                'ORDER BY timestamp DESC LIMIT 1',
                (from_ts,),
            ).fetchone()) is not None and (
                restored_events_since_interval := cost_basis_pass.restore_checkpoint(
                    checkpoint_row[1],
                )
            ) is not None:
                start_ts = TimestampMS(checkpoint_row[0])
                if restored_events_since_interval > 0:
                    restored_terminal_ts = start_ts
                    events_since_interval = restored_events_since_interval

            cost_basis_pass.stored_basis = {
                event_identifier: FVal(basis_per_unit)
                for event_identifier, basis_per_unit in cursor.execute(
                    'SELECT event_identifier, basis_per_unit FROM event_cost_basis '
                    'WHERE direction = ? AND basis_source != ? AND timestamp >= ? '
                    'AND timestamp < ?',
                    (
                        CostBasisDirection.RECEIVE.value,
                        BasisSource.TRANSFER_IN.value,
                        start_ts,
                        from_ts,
                    ),
                )
            }

        event_filter = HistoryEventFilterQuery.make(
            order_by_rules=[
                ('timestamp', True),
                ('group_identifier', True),
                ('sequence_index', True),
                ('history_events_identifier', True),
            ],
            exclude_ignored_assets=True,
            exclude_ignored_actions=True,
            exclude_untracked_withdrawals=True,
        )
        if start_ts != 0:
            event_filter.timestamp_filter.from_ts = Timestamp(start_ts)
            event_filter.timestamp_filter.scaling_factor = None
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=event_filter,
        )

    log.debug(
        'Starting cost basis processing of %s events from_ts=%s start_ts=%s',
        len(events),
        from_ts,
        start_ts,
    )
    treat_eth2_as_eth = settings.treat_eth2_as_eth
    first_batch_written, total_events = False, len(events)
    send_ws_every = msg_aggregator.how_many_events_per_ws(total_events)
    interrupted_at: TimestampMS | None = None
    record_failure = True  # unless the pass ends or is cancelled
    try:
        for idx, event in enumerate(events):
            next_event = events[idx + 1] if idx + 1 < total_events else None
            swap_fee_events: Sequence[HistoryBaseEntry] = (
                _collect_swap_fee_events(events, idx)
                if (
                    idx + 2 < total_events and
                    events[idx + 2].group_identifier == event.group_identifier and
                    events[idx + 2].event_type == event.event_type and
                    events[idx + 2].event_subtype == HistoryEventSubType.FEE
                )
                else ()
            )
            try:
                cost_basis_pass.apply(
                    event=event,
                    next_event=next_event,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                    swap_fee_events=swap_fee_events,
                )
            except (NoPriceForGivenTimestamp, RemoteError) as e:
                log.warning('Stopping cost basis processing at event %s: %s', event.identifier, e)
                interrupted_at = event.timestamp
                break

            events_since_interval += 1
            if idx % MIN_EVENTS_PROCESSED_TO_SLEEP == 0:
                time.sleep(0)  # release the GIL so concurrent DB readers interleave

            if idx % send_ws_every == 0:
                msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
                        'phase': str(HistoricalBalanceProcessingPhase.COST_BASIS),
                        'total': total_events,
                        'processed': idx,
                    },
                )

            if (
                (checkpoint_ts := _checkpoint_ts(
                    cost_basis_pass=cost_basis_pass,
                    event=event,
                    next_event=next_event,
                    events_since_checkpoint=events_since_interval,
                )) is not None or
                len(cost_basis_pass.rows) >= COST_BASIS_BATCH_SIZE
            ):
                with database.user_write() as write_cursor:
                    _write_rows(write_cursor, cost_basis_pass.rows, from_ts, first_batch_written)
                    if checkpoint_ts is not None:
                        _write_checkpoint(
                            write_cursor=write_cursor,
                            cost_basis_pass=cost_basis_pass,
                            timestamp=checkpoint_ts,
                            events_since_interval=0,
                            replace_timestamp=restored_terminal_ts,
                        )
                        restored_terminal_ts = None
                        events_since_interval = 0
                    next_idx = (
                        idx + 2
                        if (
                            next_event is not None and
                            next_event.identifier in cost_basis_pass._basis_transfer_receives
                        )
                        else idx + 1
                    )
                    if next_idx < total_events:
                        _record_progress(
                            write_cursor=write_cursor,
                            processed_ts=events[next_idx].timestamp,
                            modification_ts_at_start=modification_ts_at_start,
                        )
                first_batch_written, cost_basis_pass.rows = True, []
                _write_invalid_amount_issues(database, cost_basis_pass.invalid_amount_issues)
                cost_basis_pass.invalid_amount_issues = []
                checkpoint()  # cancellation checkpoint of the cost basis processing loop
                time.sleep(0)

        with database.user_write() as write_cursor:  # also when empty, to drop the replaced rows
            _write_rows(write_cursor, cost_basis_pass.rows, from_ts, first_batch_written)
            if interrupted_at is None and total_events != 0:
                _write_checkpoint(
                    write_cursor=write_cursor,
                    cost_basis_pass=cost_basis_pass,
                    timestamp=TimestampMS(events[-1].timestamp + 1),
                    events_since_interval=(
                        0 if events_since_interval >= COST_BASIS_CHECKPOINT_INTERVAL
                        else events_since_interval
                    ),
                    replace_timestamp=restored_terminal_ts,
                )
        _write_invalid_amount_issues(database, cost_basis_pass.invalid_amount_issues)
        if interrupted_at is None:
            DataIssuesManager(database).resolve_event_issues_except(
                kind=IssueKind.INVALID_EVENT_AMOUNT,
                still_active_ids=cost_basis_pass.invalid_amount_event_ids,
            )

        _finalize_processing(
            database=database,
            modification_ts_at_start=(
                None if modification_ts_at_start is None else int(modification_ts_at_start)
            ),
            interrupted_at=interrupted_at,
        )
        record_failure = False
    except TaskCancelledError:
        record_failure = False  # what the pass committed is resumed as it is
        raise
    finally:
        if record_failure:
            _record_failure(
                database=database,
                cost_basis_pass=cost_basis_pass,
                modification_ts_at_start=modification_ts_at_start,
            )

    if interrupted_at is not None:
        return False

    msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING),
            'phase': str(HistoricalBalanceProcessingPhase.COST_BASIS),
            'total': total_events,
            'processed': total_events,
        },
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
    shown covers both. Returns None if the requested pass is already running.
    """
    ran = True
    try:
        if skip_balances:
            if (processed := process_cost_basis(
                database=database,
                msg_aggregator=msg_aggregator,
            )) is None:
                ran = False
                return None
            return processed

        if (processed := process_historical_balances(
            database=database,
            msg_aggregator=msg_aggregator,
            from_ts=from_ts,
            chains_aggregator=chains_aggregator,
            notify_completion=False,
        )) is None:
            ran = False
            return None

        process_cost_basis(database=database, msg_aggregator=msg_aggregator)
        return processed
    finally:
        if ran:
            msg_aggregator.add_message(
                message_type=WSMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED,
                data={},
            )
