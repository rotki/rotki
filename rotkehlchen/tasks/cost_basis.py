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

from rotkehlchen.accounting.cost_basis.eth2 import (
    Eth2StakingCostBasis,
    validator_eth2_bucket,
)
from rotkehlchen.accounting.cost_basis.lots import (
    BasisSource,
    BucketLots,
    ConsumedLot,
    CostBasisDirection,
    Lot,
)
from rotkehlchen.accounting.cost_basis.pnl import get_unprocessed_from_ts
from rotkehlchen.accounting.cost_basis.rules import CostBasisRules as _Rules
from rotkehlchen.api.websockets.typedefs import (
    HistoricalBalanceProcessingPhase,
    ProgressUpdateSubType,
    WSMessageType,
)
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.ethereum.modules.eth2.constants import UNKNOWN_VALIDATOR_INDEX
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH2, A_KFEE
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.cause import TRANSIENT_FAILURE_CAUSES
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import (
    IncompleteSwapIssuePayload,
    IncompleteSwapReason,
    MissingCostBasisIssuePayload,
    MissingPriceDirection,
    MissingPriceIssuePayload,
    SwapLegSummary,
    UnmatchedExchangeTransferIssuePayload,
)
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.locations.constants import LOCATION_KRAKEN
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.events import get_unmatched_asset_movements
from rotkehlchen.tasks.historical_balances import (
    MIN_EVENTS_PROCESSED_TO_SLEEP,
    Bucket,
    _get_wallet_protocol,
    process_historical_balances,
)
from rotkehlchen.types import Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.accounting.cost_basis.lots import SpendResult
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
    int,  # is_taxable
    str,  # method
]

COST_BASIS_BATCH_SIZE: Final = 500
# Events walked between two checkpoints of the lots. Each one stores all lots still held, so
# this trades the space they take for how many events a pass replays before what is stale.
COST_BASIS_CHECKPOINT_INTERVAL: Final = 10_000


def _swap_leg_direction(
        event: HistoryBaseEntry,
        bucket_directions: Sequence[tuple[Bucket, EventDirection]],
) -> EventDirection | None:
    if event.asset.is_fiat():
        return event.maybe_get_direction()

    return bucket_directions[0][1] if len(bucket_directions) == 1 else None


def _event_issue_bucket(event: HistoryBaseEntry, treat_eth2_as_eth: bool) -> Bucket:
    """Resolve the primary bucket under which a data issue for `event` is filed."""
    if not event.asset.is_fiat():
        buckets = Bucket.from_event(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
        if len(buckets) > 0:
            return buckets[0][0]
    return Bucket(
        location=event.location,
        location_label=event.location_label,
        protocol=_get_wallet_protocol(event),
        asset=event.asset.identifier,
    )


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
            tracked_eth_accounts: set[str] | None = None,
            validator_types: dict[int, ValidatorType] | None = None,
            matched_spend_to_receive: dict[int, int] | None = None,
    ) -> None:
        self.settings = settings
        self.rules = rules
        self.from_ts = from_ts
        self.stored_basis = stored_basis
        self.tracked_eth_accounts = tracked_eth_accounts
        self.matched_spend_to_receive: dict[int, int] = (
            {} if matched_spend_to_receive is None else matched_spend_to_receive
        )
        self.method = settings.cost_basis_method.serialize()
        self.profit_currency = settings.main_currency.resolve_to_asset_with_oracles()
        self.lots = BucketLots[Bucket](settings)
        self.rows: list[CostBasisRow] = []
        self.blocked_buckets: set[Bucket] = set()
        self.invalid_amount_event_ids: set[int] = set()
        self.invalid_amount_issues: list[tuple[Bucket, HistoryBaseEntry]] = []
        self.missing_price_event_ids: set[int] = set()
        self.missing_price_issues: list[tuple[Bucket, HistoryBaseEntry, MissingPriceIssuePayload]] = []  # noqa: E501
        self.missing_cost_basis_event_ids: set[int] = set()
        self.missing_cost_basis_issues: list[tuple[Bucket, HistoryBaseEntry, MissingCostBasisIssuePayload]] = []  # noqa: E501
        self.incomplete_swap_event_ids: set[int] = set()
        self.incomplete_swap_issues: list[tuple[Bucket, TimestampMS, TimestampMS, IncompleteSwapIssuePayload]] = []  # noqa: E501
        self._prices: dict[tuple[str, Timestamp], Price | None] = {}
        # What a swap gives to each of its sides, keyed by the identifier of the side's event.
        self._swap_basis: dict[int, tuple[FVal, BasisSource]] = {}
        self._swap_proceeds: dict[int, tuple[FVal | None, bool, bool]] = {}
        # The receiving side of a basis transfer, which is applied along with its other side.
        self._basis_transfer_receives: set[int] = set()
        # Lots extracted from the spend leg of a matched exchange transfer, keyed by receive id.
        self._pending_matched_transfers: dict[int, tuple[FVal, list[ConsumedLot]]] = {}
        self.eth2 = Eth2StakingCostBasis(host=self, validator_types=validator_types)

    def record_missing_price(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            direction: MissingPriceDirection,
            amount: FVal | None = None,
    ) -> None:
        """Record a `MISSING_PRICE` data issue candidate for an unpriced cost-basis event."""
        assert event.identifier is not None
        self.missing_price_event_ids.add(event.identifier)
        self.missing_price_issues.append((
            bucket,
            event,
            MissingPriceIssuePayload(
                event_identifier=event.identifier,
                group_identifier=event.group_identifier,
                to_asset=self.profit_currency.identifier,
                amount=str(event.amount if amount is None else amount),
                direction=direction,
            ),
        ))

    def record_missing_cost_basis(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            requested_amount: FVal,
            covered_amount: FVal,
    ) -> None:
        """Record a `MISSING_COST_BASIS` issue candidate for uncovered spend/transfer units."""
        uncovered = requested_amount - covered_amount
        if uncovered <= ZERO:
            return
        assert event.identifier is not None
        self.missing_cost_basis_event_ids.add(event.identifier)
        self.missing_cost_basis_issues.append((
            bucket,
            event,
            MissingCostBasisIssuePayload(
                event_identifier=event.identifier,
                group_identifier=event.group_identifier,
                requested_amount=str(requested_amount),
                covered_amount=str(covered_amount),
                uncovered_amount=str(uncovered),
                fallback_basis='0',
            ),
        ))

    def record_incomplete_swap(
            self,
            group_events: Sequence[HistoryBaseEntry],
            present_legs: Sequence[HistoryBaseEntry],
            reason: IncompleteSwapReason,
            excluded_assets: Sequence[str],
            treat_eth2_as_eth: bool,
    ) -> None:
        """Record an `INCOMPLETE_SWAP` issue anchored on the canonical leg of the swap group."""
        candidates = present_legs if len(present_legs) > 0 else group_events
        anchor = min(
            (ev for ev in candidates if ev.identifier is not None),
            key=lambda ev: ev.identifier or 0,
            default=None,
        )
        if anchor is None or anchor.identifier is None:
            return
        anchor_bucket = _event_issue_bucket(anchor, treat_eth2_as_eth=treat_eth2_as_eth)
        sorted_legs = sorted(
            (ev for ev in present_legs if ev.identifier is not None),
            key=lambda ev: (ev.sequence_index, ev.identifier or 0),
        )
        ts_start = TimestampMS(min(ev.timestamp for ev in group_events))
        ts_end = TimestampMS(max(ev.timestamp for ev in group_events))
        payload = IncompleteSwapIssuePayload(
            event_identifier=anchor.identifier,
            group_identifier=anchor.group_identifier,
            event_identifiers=sorted(
                ev.identifier for ev in group_events if ev.identifier is not None
            ),
            present_legs=[
                SwapLegSummary(
                    event_identifier=ev.identifier,
                    subtype=ev.event_subtype.serialize(),
                    asset=ev.asset.identifier,
                    amount=str(ev.amount),
                )
                for ev in sorted_legs
                if ev.identifier is not None
            ],
            missing_or_excluded_reason=reason,
            excluded_assets=sorted(set(excluded_assets)),
        )
        self.incomplete_swap_event_ids.add(anchor.identifier)
        self.incomplete_swap_issues.append((anchor_bucket, ts_start, ts_end, payload))

    def get_price(self, asset: Asset, timestamp: Timestamp) -> Price | None:
        """The price of the asset in the profit currency, or None if no oracle knows it.

        An oracle rejecting the query (e.g. a 401 for history beyond its plan or a 404 for a
        delisted id) also counts as no price, since retrying would get the same answer.

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
        except RemoteError as e:
            if e.cause in TRANSIENT_FAILURE_CAUSES:
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
            treat_eth2_as_eth: bool,
    ) -> None:
        """Value both sides and any fee legs of a swap at what was paid for it.

        A fiat side states that value itself. Otherwise it is the market price of what was
        given, or of what was received if what was given has no price. When
        `include_fees_in_cost_basis` is enabled, priced fee legs are folded into the acquired
        asset's basis (or subtracted from disposal proceeds when selling for fiat) and do not
        realize PnL on their own; otherwise they are treated as taxable fee spends. A swap
        between two crypto assets realizes nothing if the user does not count those as taxable.
        If neither side has a price, the spent side has no proceeds, so its PnL is left unknown
        rather than booking its whole basis as a loss.
        """
        assert out_event.identifier is not None
        assert in_event.identifier is not None
        out_price = self.get_price(asset=out_event.asset, timestamp=timestamp)
        in_price = self.get_price(asset=in_event.asset, timestamp=timestamp)
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
        priced = source != BasisSource.ZERO_COST  # priced fees below may change `source`

        if not priced and (
            self.from_ts is None or
            out_event.timestamp >= self.from_ts or
            in_event.timestamp >= self.from_ts
        ):
            self.record_missing_price(
                event=out_event,
                bucket=_event_issue_bucket(out_event, treat_eth2_as_eth=treat_eth2_as_eth),
                direction='swap',
            )

        total_fees = ZERO
        if self.settings.include_fees_in_cost_basis:
            for fee_event in fee_events:
                if (fee_price := self.get_price(asset=fee_event.asset, timestamp=timestamp)) is not None:  # noqa: E501
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
            if fee_event.asset == A_KFEE:
                fee_proceeds.append((fee_event.identifier, (None, False, False)))
                continue
            if fee_event.asset == self.profit_currency:
                fee_rate: FVal | None = ONE
            elif fee_event.asset == in_event.asset and priced:
                fee_rate = in_rate
            elif fee_event.asset == out_event.asset and priced:
                fee_rate = out_rate
            else:
                fee_rate = self.get_price(asset=fee_event.asset, timestamp=timestamp)
            fee_taxable = not self.settings.include_fees_in_cost_basis
            if (
                fee_taxable and
                fee_rate is None and
                (self.from_ts is None or fee_event.timestamp >= self.from_ts)
            ):
                self.record_missing_price(
                    event=fee_event,
                    bucket=_event_issue_bucket(fee_event, treat_eth2_as_eth=treat_eth2_as_eth),
                    direction='fee',
                )
            fee_proceeds.append((fee_event.identifier, (fee_rate, fee_taxable, fee_taxable)))

        self._swap_basis[in_event.identifier] = (in_rate, source)
        self._swap_proceeds[out_event.identifier] = (
            out_rate if priced else None,
            is_taxable and (in_event.asset.is_fiat() or self.settings.include_crypto2crypto),
            False,
        )
        for fee_id, entry in fee_proceeds:
            self._swap_proceeds[fee_id] = entry

    def add_row(
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
            is_taxable: bool = False,
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
            int(is_taxable),
            self.method,
        ))

    def move_lots(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            destination: Bucket,
            move_amount: FVal,
            dest_amount: FVal,
            received: HistoryBaseEntry,
            is_stale: bool = False,
            issue_bucket: Bucket | None = None,
    ) -> tuple[list[ConsumedLot], list[str], FVal]:
        """Move lots between buckets, creating a zero-basis lot for any uncovered remainder."""
        moved = self.lots.transfer(
            source=source,
            destination=destination,
            asset=event.asset,
            amount=move_amount,
            destination_amount=dest_amount,
            event=event,
        )
        lot_ids = list(dict.fromkeys(entry.lot.lot_id for entry in moved))
        covered = sum((entry.amount for entry in moved), start=ZERO)
        if (unknown_amount := move_amount - covered) > ZERO:
            if is_stale:
                self.record_missing_cost_basis(
                    event=event,
                    bucket=source if issue_bucket is None else issue_bucket,
                    requested_amount=move_amount,
                    covered_amount=covered,
                )
            lot_ids.append(lot_id := str(received.identifier))
            scaled_unknown = (
                unknown_amount if dest_amount == move_amount
                else unknown_amount * dest_amount / move_amount
            )
            self.lots.obtain(
                bucket=destination,
                lot_id=lot_id,
                amount=scaled_unknown,
                basis_per_unit=ZERO,
                timestamp=ts_ms_to_sec(received.timestamp),
            )
        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        return moved, lot_ids, basis

    def transfer(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            destination: Bucket,
            is_stale: bool,
            in_event: HistoryBaseEntry | None = None,
            transfer_amount: FVal | None = None,
            row_source: Bucket | None = None,
            row_destination: Bucket | None = None,
    ) -> None:
        """Move the basis along with an asset that moves between two buckets of the user.

        `in_event` is the receiving side when it is an event of its own, as in a basis transfer
        to another asset. If the source bucket holds less than what moves then the history of
        the rest is not known, and it arrives at the destination as a lot of the receiving
        event with no basis.
        """
        move_amount = event.amount if transfer_amount is None else transfer_amount
        received = event if in_event is None else in_event
        dest_amount = move_amount if in_event is None else in_event.amount
        source_basis_before = (
            self.lots.basis_remaining(source) if is_stale and source == destination else None
        )
        moved, lot_ids, basis = self.move_lots(
            event=event,
            source=source,
            destination=destination,
            move_amount=move_amount,
            dest_amount=dest_amount,
            received=received,
            is_stale=is_stale,
            issue_bucket=row_source,
        )

        if not (in_is_stale := self.from_ts is None or received.timestamp >= self.from_ts):
            return

        if is_stale:
            self.add_row(
                event=event,
                bucket=source if row_source is None else row_source,
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
            self.add_row(
                event=received,
                bucket=destination if row_destination is None else row_destination,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=','.join(lot_ids),
                basis_per_unit=basis / dest_amount,
                basis_source=BasisSource.TRANSFER_IN,
            )

    def _is_taxable_receive(
            self,
            event: HistoryBaseEntry,
            rule: BaseEventSettings | None,
    ) -> bool:
        """Whether an incoming non-swap, non-transfer event realizes taxable income."""
        if isinstance(event, AssetMovement):
            return False

        if (
            event.location == LOCATION_KRAKEN and
            event.event_type == HistoryEventType.STAKING and
            event.event_subtype == HistoryEventSubType.REWARD
        ):
            return True

        if isinstance(event, EthBlockEvent):
            return event.event_type == HistoryEventType.STAKING

        return rule is not None and rule.taxable

    def resolve_receive_basis(
            self,
            event: HistoryBaseEntry,
            timestamp: Timestamp,
            is_stale: bool,
            swap_basis: tuple[FVal, BasisSource] | None = None,
            *,
            use_stored_basis: bool = True,
    ) -> tuple[FVal, BasisSource]:
        """Resolve per-unit basis and source for an incoming lot."""
        assert event.identifier is not None
        if (
            not is_stale and
            use_stored_basis and
            (stored := self.stored_basis.get(event.identifier)) is not None
        ):
            return stored, BasisSource.PRICE_ORACLE
        if swap_basis is not None:
            return swap_basis
        if (price := self.get_price(asset=event.asset, timestamp=timestamp)) is not None:
            return price, BasisSource.PRICE_ORACLE
        return ZERO, BasisSource.ZERO_COST

    @staticmethod
    def compute_receive_pnl(
            amount: FVal,
            basis: FVal,
            basis_source: BasisSource,
            is_taxable: bool,
    ) -> tuple[FVal | None, FVal | None]:
        """Compute `(realized_pnl, taxfree_pnl)` for an incoming event."""
        if is_taxable and basis_source != BasisSource.ZERO_COST:
            return amount * basis, ZERO
        return None, None

    def _resolve_spend_treatment(
            self,
            event: HistoryBaseEntry,
            timestamp: Timestamp,
            rule: BaseEventSettings | None,
            swap_proceeds: tuple[FVal | None, bool, bool] | None,
            *,
            price_non_taxable_rule: bool = True,
    ) -> tuple[FVal | None, bool, bool]:
        """Resolve `(rate, counts_cost_basis, count_entire_amount_spend)` for a spend event."""
        if event.asset == A_KFEE:
            return None, False, False
        if swap_proceeds is not None:
            return swap_proceeds
        if rule is not None:
            counts_cost_basis = rule.taxable and rule.count_cost_basis_pnl
            count_entire_amount_spend = rule.taxable and rule.count_entire_amount_spend
            rate = (
                self.get_price(asset=event.asset, timestamp=timestamp)
                if price_non_taxable_rule or count_entire_amount_spend else None
            )
            return rate, counts_cost_basis, count_entire_amount_spend
        if isinstance(event, AssetMovement) and event.event_subtype == HistoryEventSubType.FEE:
            return self.get_price(asset=event.asset, timestamp=timestamp), True, True
        return None, False, False

    @staticmethod
    def compute_spend_pnl(
            amount: FVal,
            rate: FVal | None,
            counts_cost_basis: bool,
            count_entire_amount_spend: bool,
            result: SpendResult | None = None,
    ) -> tuple[FVal | None, FVal | None, FVal | None]:
        """Compute `(proceeds, realized_pnl, taxfree_pnl)` for a spend event."""
        if rate is not None:
            proceeds = amount * rate
            realized_pnl = -proceeds if count_entire_amount_spend else ZERO
            if counts_cost_basis and result is not None:
                realized_pnl += result.taxable_amount * rate - result.taxable_basis
                taxfree_pnl = (amount - result.taxable_amount) * rate - result.taxfree_basis
            else:
                taxfree_pnl = ZERO
            return proceeds, realized_pnl, taxfree_pnl

        if counts_cost_basis or count_entire_amount_spend:
            return None, None, None

        return None, ZERO, ZERO

    def receive(
            self,
            event: HistoryBaseEntry,
            bucket: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
            *,
            is_taxable: bool | None = None,
    ) -> None:
        assert event.identifier is not None
        swap_basis = self._swap_basis.pop(event.identifier, None)
        basis, basis_source = self.resolve_receive_basis(
            event=event,
            timestamp=timestamp,
            is_stale=is_stale,
            swap_basis=swap_basis,
        )
        self.lots.obtain(
            bucket=bucket,
            lot_id=(lot_id := str(event.identifier)),
            amount=event.amount,
            basis_per_unit=basis,
            timestamp=timestamp,
        )
        if is_stale:
            if swap_basis is None and basis_source == BasisSource.ZERO_COST:
                self.record_missing_price(event=event, bucket=bucket, direction='receive')
            taxable = (
                swap_basis is None and self._is_taxable_receive(event, rule)
                if is_taxable is None else is_taxable
            )
            realized_pnl, taxfree_pnl = self.compute_receive_pnl(
                amount=event.amount,
                basis=basis,
                basis_source=basis_source,
                is_taxable=taxable,
            )
            self.add_row(
                event=event,
                bucket=bucket,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=lot_id,
                basis_per_unit=basis,
                basis_source=basis_source,
                realized_pnl=realized_pnl,
                taxfree_pnl=taxfree_pnl,
                is_taxable=taxable,
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

        if result.uncovered_amount > ZERO:
            self.record_missing_cost_basis(
                event=event,
                bucket=bucket,
                requested_amount=event.amount,
                covered_amount=event.amount - result.uncovered_amount,
            )

        rate, counts_cost_basis, count_entire_amount_spend = self._resolve_spend_treatment(
            event=event,
            timestamp=timestamp,
            rule=rule,
            swap_proceeds=swap_proceeds,
        )
        if (
            swap_proceeds is None and
            rate is None and
            (counts_cost_basis or count_entire_amount_spend)
        ):
            self.record_missing_price(
                event=event,
                bucket=bucket,
                direction='fee' if event.event_subtype == HistoryEventSubType.FEE else 'spend',
            )
        proceeds, realized_pnl, taxfree_pnl = self.compute_spend_pnl(
            amount=event.amount,
            rate=rate,
            counts_cost_basis=counts_cost_basis,
            count_entire_amount_spend=count_entire_amount_spend,
            result=result,
        )
        self.add_row(
            event=event,
            bucket=bucket,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in result.consumed],
            proceeds=proceeds,
            realized_pnl=realized_pnl,
            taxfree_pnl=taxfree_pnl,
            basis_removed=result.basis_removed,
            post_spend_basis_remaining=self.lots.basis_remaining(bucket),
            is_taxable=counts_cost_basis or count_entire_amount_spend,
        )

    def _apply_matched_transfer_spend(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            receive_id: int,
            is_stale: bool,
    ) -> None:
        """Extract lots on the spend leg of a matched exchange transfer into transit storage."""
        moved = self.lots.extract(
            source=source,
            asset=event.asset,
            amount=event.amount,
            event=event,
        )
        covered = sum((entry.amount for entry in moved), start=ZERO)
        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        self._pending_matched_transfers[receive_id] = (event.amount, moved)
        if not is_stale:
            return

        if event.amount - covered > ZERO:
            self.record_missing_cost_basis(
                event=event,
                bucket=source,
                requested_amount=event.amount,
                covered_amount=covered,
            )
        self.add_row(
            event=event,
            bucket=source,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in moved],
            realized_pnl=ZERO,
            basis_removed=basis,
            post_spend_basis_remaining=self.lots.basis_remaining(source),
            is_taxable=False,
        )

    def _apply_matched_transfer_receive(
            self,
            event: HistoryBaseEntry,
            destination: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
    ) -> None:
        """Deposit lots buffered by the matched exchange transfer's spend leg into destination."""
        assert event.identifier is not None
        spend_amount, moved = self._pending_matched_transfers.pop(event.identifier)
        ratio = event.amount / spend_amount if spend_amount > ZERO else ONE
        self.lots.deposit_lots(destination=destination, moved=moved, ratio=ratio)
        lot_ids = list(dict.fromkeys(entry.lot.lot_id for entry in moved))
        covered = sum((entry.amount for entry in moved), start=ZERO)
        if (unknown_amount := spend_amount - covered) > ZERO:
            lot_ids.append(lot_id := str(event.identifier))
            self.lots.obtain(
                bucket=destination,
                lot_id=lot_id,
                amount=unknown_amount * ratio,
                basis_per_unit=ZERO,
                timestamp=timestamp,
            )
        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        if is_stale:
            self.add_row(
                event=event,
                bucket=destination,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=','.join(lot_ids),
                basis_per_unit=basis / event.amount,
                basis_source=BasisSource.TRANSFER_IN,
                is_taxable=False,
            )

    def _apply_fiat_event(
            self,
            event: HistoryBaseEntry,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
    ) -> None:
        """Record PnL for taxable fiat expenses/fees and fiat income without tracking fiat lots."""
        assert event.identifier is not None
        swap_proceeds = self._swap_proceeds.pop(event.identifier, None)
        swap_basis = self._swap_basis.pop(event.identifier, None)
        if not is_stale:
            return

        bucket = Bucket(
            location=event.location,
            location_label=event.location_label,
            protocol=_get_wallet_protocol(event),
            asset=event.asset.identifier,
        )
        direction = event.maybe_get_direction()
        if swap_proceeds is not None or direction == EventDirection.OUT:
            rate, _counts_cost_basis, count_entire_amount_spend = self._resolve_spend_treatment(
                event=event,
                timestamp=timestamp,
                rule=rule,
                swap_proceeds=swap_proceeds,
                price_non_taxable_rule=False,
            )
            if not count_entire_amount_spend:
                return

            if swap_proceeds is None and rate is None:
                self.record_missing_price(
                    event=event,
                    bucket=bucket,
                    direction='fee' if event.event_subtype == HistoryEventSubType.FEE else 'spend',
                )
            proceeds, realized_pnl, taxfree_pnl = self.compute_spend_pnl(
                amount=event.amount,
                rate=rate,
                counts_cost_basis=False,
                count_entire_amount_spend=True,
            )
            self.add_row(
                event=event,
                bucket=bucket,
                direction=CostBasisDirection.SPEND,
                lots_consumed=[],
                proceeds=proceeds,
                realized_pnl=realized_pnl,
                taxfree_pnl=taxfree_pnl,
                basis_removed=ZERO,
                post_spend_basis_remaining=ZERO,
                is_taxable=True,
            )
            return

        if swap_basis is None and direction == EventDirection.IN and self._is_taxable_receive(event, rule):  # noqa: E501
            basis, basis_source = self.resolve_receive_basis(
                event=event,
                timestamp=timestamp,
                is_stale=True,
            )
            if basis_source == BasisSource.ZERO_COST:
                self.record_missing_price(event=event, bucket=bucket, direction='receive')
            realized_pnl, taxfree_pnl = self.compute_receive_pnl(
                amount=event.amount,
                basis=basis,
                basis_source=basis_source,
                is_taxable=True,
            )
            self.add_row(
                event=event,
                bucket=bucket,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=None,
                basis_per_unit=basis,
                basis_source=basis_source,
                realized_pnl=realized_pnl,
                taxfree_pnl=taxfree_pnl,
                is_taxable=True,
            )

    def _maybe_transfer_basis(
            self,
            event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            out_buckets: Sequence[tuple[Bucket, EventDirection]],
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
        self.transfer(
            event=event,
            source=out_buckets[0][0],
            destination=in_buckets[0][0],
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
            'pending_matched_transfers': {
                str(receive_id): [
                    str(spend_amount),
                    [
                        [entry.lot.serialize_state(), str(entry.amount), str(entry.basis_per_unit)]
                        for entry in moved
                    ],
                ]
                for receive_id, (spend_amount, moved) in self._pending_matched_transfers.items()
            },
            'events_since_interval': events_since_interval,
            **self.eth2.serialize_state(),
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
        self._pending_matched_transfers = {
            int(receive_id): (
                FVal(spend_amount),
                [
                    ConsumedLot(
                        lot=Lot.from_state(lot_state),
                        amount=FVal(amount),
                        basis_per_unit=FVal(basis_per_unit),
                        taxable=False,
                    )
                    for lot_state, amount, basis_per_unit in moved_entries
                ],
            )
            for receive_id, (spend_amount, moved_entries) in state.get(
                'pending_matched_transfers', {},
            ).items()
        }
        self.eth2.restore_state(state)
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
        if event.identifier is None:
            return

        if self.eth2.handle_informational_event(event):
            return

        if event.amount == ZERO:
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
            if (
                isinstance(event, EthDepositEvent | EthWithdrawalEvent) and
                event.validator_index != UNKNOWN_VALIDATOR_INDEX
            ):
                self.blocked_buckets.add(validator_eth2_bucket(event.validator_index))
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
                    treat_eth2_as_eth=treat_eth2_as_eth,
                )

        if event.asset.is_fiat():
            self._apply_fiat_event(
                event=event,
                timestamp=timestamp,
                is_stale=is_stale,
                rule=rule,
            )
            return

        if len(bucket_directions) == 0:
            return

        if len(bucket_directions) == 1:
            bucket, direction = bucket_directions[0]
            if bucket in self.blocked_buckets:
                return

            if direction == EventDirection.IN:
                if event.identifier in self._pending_matched_transfers:
                    self._apply_matched_transfer_receive(
                        event=event,
                        destination=bucket,
                        timestamp=timestamp,
                        is_stale=is_stale,
                    )
                    return

                if (
                    isinstance(event, EthBlockEvent | EthWithdrawalEvent) and
                    self.tracked_eth_accounts is not None and
                    event.location_label not in self.tracked_eth_accounts
                ):
                    return

                if (
                    self.settings.eth_staking_taxable_after_withdrawal_enabled and
                    event.location == LOCATION_KRAKEN and
                    event.asset == A_ETH2 and
                    event.event_type == HistoryEventType.STAKING and
                    event.event_subtype == HistoryEventSubType.REWARD and
                    timestamp < SHAPPELA_TIMESTAMP
                ):
                    return

                if isinstance(event, EthWithdrawalEvent):
                    self.eth2.apply_withdrawal(
                        event=event,
                        wallet_bucket=bucket,
                        timestamp=timestamp,
                        is_stale=is_stale,
                        rule=rule,
                    )
                else:
                    self.receive(event, bucket, timestamp, is_stale, rule)
            elif (receive_id := self.matched_spend_to_receive.get(event.identifier)) is not None:
                self._apply_matched_transfer_spend(
                    event=event,
                    source=bucket,
                    receive_id=receive_id,
                    is_stale=is_stale,
                )
            else:
                self._spend(event, bucket, timestamp, is_stale, rule)
            return

        source = next((b for b, d in bucket_directions if d == EventDirection.OUT), None)
        destination = next((b for b, d in bucket_directions if d == EventDirection.IN), None)
        if (
            isinstance(event, EthDepositEvent) and
            event.validator_index != UNKNOWN_VALIDATOR_INDEX and
            source is not None and
            destination is not None
        ):
            self.eth2.apply_deposit(
                event=event,
                source=source,
                destination=destination,
                is_stale=is_stale,
            )
            return

        if (
            source is not None and
            destination is not None and
            source != destination and
            source not in self.blocked_buckets and
            destination not in self.blocked_buckets
        ):
            self.transfer(event, source, destination, is_stale)


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
        'post_spend_basis_remaining, is_taxable, method) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
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
        max_seen_ts: TimestampMS,
        next_min_ts: TimestampMS | None,
        events_since_checkpoint: int,
) -> TimestampMS | None:
    """The timestamp to checkpoint the lots at after the event, or None if not here.

    A checkpoint holds all events strictly before its timestamp, so it can only be taken at a
    strict chronological cut where every remaining event (accounting for clock-skewed matched
    pairs) has timestamp > `max_seen_ts` and no pair of events is halfway applied.
    """
    if (
        events_since_checkpoint < COST_BASIS_CHECKPOINT_INTERVAL or
        next_min_ts is None or
        next_min_ts <= max_seen_ts or
        cost_basis_pass.has_pending_pair
    ):
        return None

    return next_min_ts


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


def _write_cost_basis_issues(
        database: DBHandler,
        cost_basis_pass: _CostBasisPass,
) -> None:
    """Flush all pending data issues collected by `cost_basis_pass` and clear its buffers."""
    if (
        len(cost_basis_pass.invalid_amount_issues) == 0 and
        len(cost_basis_pass.missing_price_issues) == 0 and
        len(cost_basis_pass.missing_cost_basis_issues) == 0 and
        len(cost_basis_pass.incomplete_swap_issues) == 0
    ):
        return

    issues_manager = DataIssuesManager(database)
    for bucket, event in cost_basis_pass.invalid_amount_issues:
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
    cost_basis_pass.invalid_amount_issues = []

    for bucket, event, missing_price_payload in cost_basis_pass.missing_price_issues:
        issues_manager.write_issue(
            kind=IssueKind.MISSING_PRICE,
            location=bucket.location,
            location_label=bucket.location_label,
            protocol=bucket.protocol,
            asset=bucket.asset,
            payload=missing_price_payload,
            ts_start=event.timestamp,
            ts_end=event.timestamp,
        )
    cost_basis_pass.missing_price_issues = []

    for bucket, event, missing_basis_payload in cost_basis_pass.missing_cost_basis_issues:
        issues_manager.write_issue(
            kind=IssueKind.MISSING_COST_BASIS,
            location=bucket.location,
            location_label=bucket.location_label,
            protocol=bucket.protocol,
            asset=bucket.asset,
            payload=missing_basis_payload,
            ts_start=event.timestamp,
            ts_end=event.timestamp,
        )
    cost_basis_pass.missing_cost_basis_issues = []

    for bucket, ts_start, ts_end, incomplete_swap_payload in cost_basis_pass.incomplete_swap_issues:  # noqa: E501
        issues_manager.write_issue(
            kind=IssueKind.INCOMPLETE_SWAP,
            location=bucket.location,
            location_label=bucket.location_label,
            protocol=bucket.protocol,
            asset=bucket.asset,
            payload=incomplete_swap_payload,
            ts_start=ts_start,
            ts_end=ts_end,
        )
    cost_basis_pass.incomplete_swap_issues = []


def _load_standalone_swap_groups(cursor: DBCursor) -> set[str]:
    """Return group identifiers whose `INCOMPLETE_SWAP` was manually confirmed as standalone."""
    groups: set[str] = set()
    for (payload_json,) in cursor.execute(
        'SELECT payload_json FROM data_issues '
        'WHERE kind = ? AND state = ? '
        "AND json_extract(payload_json, '$.resolution.manual') = 1 "
        "AND json_extract(payload_json, '$.resolution.disposition') = ?",
        (IssueKind.INCOMPLETE_SWAP.value, IssueState.RESOLVED.value, 'dismiss_as_standalone'),
    ):
        if isinstance(group_id := json.loads(payload_json).get('group_identifier'), str):
            groups.add(group_id)
    return groups


def _group_has_unpaired_swap_leg(
        group_events: Sequence[HistoryBaseEntry],
        rules: _Rules,
        treat_eth2_as_eth: bool,
) -> bool:
    """Whether a swap group without ignored assets has an unpaired swap spend or receive leg."""
    paired_indices: set[int] = set()
    total = len(group_events)
    idx = 0
    while idx < total:
        event = group_events[idx]
        if event.amount <= ZERO:
            idx += 1
            continue
        rule = rules.get(event)
        if (
            rule is not None and
            rule.accounting_treatment == TxAccountingTreatment.SWAP and
            idx + 1 < total and
            group_events[idx + 1].amount > ZERO
        ):
            out_dirs = (
                [] if event.asset.is_fiat()
                else Bucket.from_event(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
            )
            next_ev = group_events[idx + 1]
            in_dirs = (
                [] if next_ev.asset.is_fiat()
                else Bucket.from_event(event=next_ev, treat_eth2_as_eth=treat_eth2_as_eth)
            )
            if (
                _swap_leg_direction(event, out_dirs) == EventDirection.OUT and
                _swap_leg_direction(next_ev, in_dirs) == EventDirection.IN
            ):
                paired_indices.add(idx)
                paired_indices.add(idx + 1)
                fee_idx = idx + 2
                while (
                    fee_idx < total and
                    group_events[fee_idx].event_type == event.event_type and
                    group_events[fee_idx].event_subtype == HistoryEventSubType.FEE
                ):
                    paired_indices.add(fee_idx)
                    fee_idx += 1
                idx = fee_idx
                continue
        idx += 1

    for i, ev in enumerate(group_events):
        if i in paired_indices or ev.amount <= ZERO:
            continue
        if ev.event_subtype == HistoryEventSubType.FEE:
            continue
        rule = rules.get(ev)
        if (
            (rule is not None and rule.accounting_treatment == TxAccountingTreatment.SWAP) or
            ev.event_type in {HistoryEventType.TRADE, HistoryEventType.MULTI_TRADE}
        ):
            return True
    return False


def _prepare_events_and_matches(
        events: list[HistoryBaseEntry],
        rules: _Rules,
        ignored_asset_ids: set[str],
        standalone_swap_groups: set[str],
        asset_movement_links: Sequence[tuple[int, int]],
        treat_eth2_as_eth: bool,
        cost_basis_pass: _CostBasisPass,
) -> tuple[list[HistoryBaseEntry], dict[int, int]]:
    """Apply ignored-asset swap parity, detect incomplete swaps, and resolve matched transfers."""
    groups: dict[str, list[HistoryBaseEntry]] = {}
    for ev in events:
        groups.setdefault(ev.group_identifier, []).append(ev)

    skip_event_ids: set[int] = set()
    for group_id, group_events in groups.items():
        ignored_legs = [ev for ev in group_events if ev.asset.identifier in ignored_asset_ids]
        active_legs = [ev for ev in group_events if ev.asset.identifier not in ignored_asset_ids]
        is_swap_group = any(
            (
                (rule := rules.get(ev)) is not None and
                rule.accounting_treatment == TxAccountingTreatment.SWAP
            ) or (
                ev.event_type in {HistoryEventType.TRADE, HistoryEventType.MULTI_TRADE} and
                (spend_rule := rules.get_for_fields(
                    event_identifier=None,
                    event_type=ev.event_type,
                    event_subtype=HistoryEventSubType.SPEND,
                    counterparty=None,
                )) is not None and
                spend_rule.accounting_treatment == TxAccountingTreatment.SWAP
            )
            for ev in group_events
        )
        is_basis_transfer_group = any(
            (rule := rules.get(ev)) is not None and
            rule.accounting_treatment == TxAccountingTreatment.BASIS_TRANSFER
            for ev in group_events
        )
        group_is_stale = (
            cost_basis_pass.from_ts is None or
            any(ev.timestamp >= cost_basis_pass.from_ts for ev in group_events)
        )

        if is_swap_group and len(ignored_legs) > 0:
            if group_is_stale:
                cost_basis_pass.record_incomplete_swap(
                    group_events=group_events,
                    present_legs=active_legs,
                    reason='ignored_asset',
                    excluded_assets=[ev.asset.identifier for ev in ignored_legs],
                    treat_eth2_as_eth=treat_eth2_as_eth,
                )
            to_skip = group_events if group_id not in standalone_swap_groups else ignored_legs
            skip_event_ids.update(ev.identifier for ev in to_skip if ev.identifier is not None)
            continue

        if is_swap_group and _group_has_unpaired_swap_leg(
            group_events=group_events,
            rules=rules,
            treat_eth2_as_eth=treat_eth2_as_eth,
        ):
            if group_is_stale:
                cost_basis_pass.record_incomplete_swap(
                    group_events=group_events,
                    present_legs=[ev for ev in group_events if ev.amount > ZERO],
                    reason='missing_counterpart_leg',
                    excluded_assets=[],
                    treat_eth2_as_eth=treat_eth2_as_eth,
                )
            continue

        if is_basis_transfer_group and len(ignored_legs) > 0:
            skip_event_ids.update(
                ev.identifier for ev in group_events if ev.identifier is not None
            )
            continue

        if len(ignored_legs) > 0:
            skip_event_ids.update(
                ev.identifier for ev in ignored_legs if ev.identifier is not None
            )

    filtered_events = [
        ev for ev in events
        if ev.identifier is None or ev.identifier not in skip_event_ids
    ]

    # Build 1:1 matched exchange transfer pairs (spend_id -> receive_id) and fix clock skew.
    events_by_id: dict[int, HistoryBaseEntry] = {
        ev.identifier: ev for ev in filtered_events if ev.identifier is not None
    }
    index_by_id: dict[int, int] = {
        ev.identifier: idx for idx, ev in enumerate(filtered_events) if ev.identifier is not None
    }
    adjacency: dict[int, set[int]] = {}
    unique_edges: set[tuple[int, int]] = set()
    for left_id, right_id in asset_movement_links:
        if left_id == right_id:
            continue
        adjacency.setdefault(left_id, set()).add(right_id)
        adjacency.setdefault(right_id, set()).add(left_id)
        unique_edges.add((min(left_id, right_id), max(left_id, right_id)))

    matched_spend_to_receive: dict[int, int] = {}
    skewed_spends_before_receive: dict[int, list[HistoryBaseEntry]] = {}
    moved_spend_ids: set[int] = set()
    for a_id, b_id in sorted(unique_edges):
        if len(adjacency.get(a_id, ())) != 1 or len(adjacency.get(b_id, ())) != 1:
            continue
        if (ev_a := events_by_id.get(a_id)) is None or (ev_b := events_by_id.get(b_id)) is None:
            continue
        if (
            ev_a.asset.is_fiat() or
            ev_b.asset.is_fiat() or
            ev_a.amount <= ZERO or
            ev_b.amount <= ZERO
        ):
            continue
        dirs_a = Bucket.from_event(event=ev_a, treat_eth2_as_eth=treat_eth2_as_eth)
        dirs_b = Bucket.from_event(event=ev_b, treat_eth2_as_eth=treat_eth2_as_eth)
        if len(dirs_a) != 1 or len(dirs_b) != 1:
            continue
        dir_a, dir_b = dirs_a[0][1], dirs_b[0][1]
        if dir_a == EventDirection.OUT and dir_b == EventDirection.IN:
            spend_ev, receive_ev = ev_a, ev_b
        elif dir_b == EventDirection.OUT and dir_a == EventDirection.IN:
            spend_ev, receive_ev = ev_b, ev_a
        else:
            continue
        assert spend_ev.identifier is not None
        assert receive_ev.identifier is not None
        matched_spend_to_receive[spend_ev.identifier] = receive_ev.identifier
        if index_by_id[spend_ev.identifier] > index_by_id[receive_ev.identifier]:
            moved_spend_ids.add(spend_ev.identifier)
            skewed_spends_before_receive.setdefault(receive_ev.identifier, []).append(spend_ev)

    if len(moved_spend_ids) == 0:
        return filtered_events, matched_spend_to_receive

    reordered: list[HistoryBaseEntry] = []
    for ev in filtered_events:
        if ev.identifier is not None and ev.identifier in moved_spend_ids:
            continue
        if ev.identifier is not None and (
            skewed := skewed_spends_before_receive.get(ev.identifier)
        ):
            reordered.extend(skewed)
        reordered.append(ev)
    return reordered, matched_spend_to_receive


def _detect_unmatched_exchange_transfer_issues(
        database: DBHandler,
        ignored_asset_ids: set[str],
        ignored_action_ids: set[str],
        asset_movement_time_range: int,
) -> None:
    """Surface exchange deposit/withdrawal movements lacking an `ASSET_MOVEMENT_MATCH` link."""
    unmatched_movements, _fee_events = get_unmatched_asset_movements(database=database)
    issues_manager = DataIssuesManager(database=database)
    now_ms = ts_sec_to_ms(ts_now())
    grace_window_ms = asset_movement_time_range * 1000
    unmatched_ids: set[int] = set()
    for movement in unmatched_movements:
        if (
            movement.identifier is None or
            movement.amount <= ZERO or
            movement.asset.identifier in ignored_asset_ids or
            movement.group_identifier in ignored_action_ids or
            movement.event_subtype not in {HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE}
        ):
            continue
        if now_ms < movement.timestamp + grace_window_ms:
            continue  # grace window so we don't race the automatic matcher

        unmatched_ids.add(movement.identifier)
        payload = UnmatchedExchangeTransferIssuePayload(
            event_identifier=movement.identifier,
            group_identifier=movement.group_identifier,
            subtype=(
                'spend' if movement.event_subtype == HistoryEventSubType.SPEND else 'receive'
            ),
            amount=str(movement.amount),
        )
        if movement.extra_data is not None:
            tx_ref = (
                movement.extra_data.get('transaction_id') or
                movement.extra_data.get('reference')
            )
            if isinstance(tx_ref, str) and tx_ref != '':
                payload['tx_ref'] = tx_ref
            if isinstance(address := movement.extra_data.get('address'), str) and address != '':
                payload['address'] = address
        issues_manager.write_issue(
            kind=IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
            location=movement.location,
            location_label=movement.location_label,
            protocol=None,
            asset=movement.asset.identifier,
            payload=payload,
            ts_start=movement.timestamp,
            ts_end=movement.timestamp,
        )

    issues_manager.resolve_event_issues_except(
        kind=IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
        still_active_ids=unmatched_ids,
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
    _write_cost_basis_issues(database, cost_basis_pass)
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
        ignored_asset_ids = database.get_ignored_asset_ids(cursor)
        ignored_action_ids = database.get_ignored_action_ids(cursor)
        standalone_swap_groups = _load_standalone_swap_groups(cursor)
        asset_movement_links = cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type = ?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()
        tracked_eth_accounts: set[str] = set(database.get_blockchain_accounts(cursor).eth)
        validator_types: dict[int, ValidatorType] = {
            validator_index: ValidatorType.deserialize_from_db(validator_type)
            for validator_index, validator_type in cursor.execute(
                'SELECT validator_index, validator_type FROM eth2_validators '
                'WHERE validator_index IS NOT NULL',
            )
        }
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
            tracked_eth_accounts=tracked_eth_accounts,
            validator_types=validator_types,
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
            exclude_ignored_assets=False,
            exclude_ignored_actions=True,
            exclude_untracked_withdrawals=True,
        )
        if start_ts != 0:
            event_filter.timestamp_filter.from_ts = Timestamp(start_ts)
            event_filter.timestamp_filter.scaling_factor = None
        raw_events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=event_filter,
        )

    treat_eth2_as_eth = settings.treat_eth2_as_eth
    events, matched_spend_to_receive = _prepare_events_and_matches(
        events=raw_events,
        rules=rules,
        ignored_asset_ids=ignored_asset_ids,
        standalone_swap_groups=standalone_swap_groups,
        asset_movement_links=asset_movement_links,
        treat_eth2_as_eth=treat_eth2_as_eth,
        cost_basis_pass=cost_basis_pass,
    )
    cost_basis_pass.matched_spend_to_receive = matched_spend_to_receive

    log.debug(
        'Starting cost basis processing of %s events from_ts=%s start_ts=%s',
        len(events),
        from_ts,
        start_ts,
    )
    first_batch_written, total_events = False, len(events)
    # Suffix minimum timestamps keep checkpoint/progress timestamps strictly chronological even
    # when clock-skewed matched transfers move a later-timestamp spend before an earlier receive.
    min_future_ts: list[TimestampMS] = [TimestampMS(0)] * total_events
    if total_events != 0:
        running_min = events[-1].timestamp
        for i in range(total_events - 1, -1, -1):
            running_min = min(running_min, events[i].timestamp)
            min_future_ts[i] = running_min
    max_seen_ts = TimestampMS(0)
    send_ws_every = msg_aggregator.how_many_events_per_ws(total_events)
    interrupted_at: TimestampMS | None = None
    record_failure = True  # unless the pass ends or is cancelled
    try:
        for idx, event in enumerate(events):
            max_seen_ts = max(max_seen_ts, event.timestamp)
            if isinstance(event, EthWithdrawalEvent) and event.is_exit_or_blocknumber == 0:
                lookahead = idx + 1
                while lookahead < total_events and events[lookahead].timestamp == event.timestamp:
                    cost_basis_pass.eth2.buffer_withdrawal_request(
                        events[lookahead],
                        prebuffered=True,
                    )
                    lookahead += 1

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
                interrupted_at = min_future_ts[idx]
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

            next_min_ts = min_future_ts[idx + 1] if idx + 1 < total_events else None
            if (
                (checkpoint_ts := _checkpoint_ts(
                    cost_basis_pass=cost_basis_pass,
                    max_seen_ts=max_seen_ts,
                    next_min_ts=next_min_ts,
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
                            processed_ts=min_future_ts[next_idx],
                            modification_ts_at_start=modification_ts_at_start,
                        )
                first_batch_written, cost_basis_pass.rows = True, []
                _write_cost_basis_issues(database, cost_basis_pass)
                checkpoint()  # cancellation checkpoint of the cost basis processing loop
                time.sleep(0)

        with database.user_write() as write_cursor:  # also when empty, to drop the replaced rows
            _write_rows(write_cursor, cost_basis_pass.rows, from_ts, first_batch_written)
            if interrupted_at is None and total_events != 0:
                _write_checkpoint(
                    write_cursor=write_cursor,
                    cost_basis_pass=cost_basis_pass,
                    timestamp=TimestampMS(max_seen_ts + 1),
                    events_since_interval=(
                        0 if events_since_interval >= COST_BASIS_CHECKPOINT_INTERVAL
                        else events_since_interval
                    ),
                    replace_timestamp=restored_terminal_ts,
                )
        _write_cost_basis_issues(database, cost_basis_pass)
        if interrupted_at is None:
            issues_manager = DataIssuesManager(database)
            issues_manager.resolve_event_issues_except(
                kind=IssueKind.INVALID_EVENT_AMOUNT,
                still_active_ids=cost_basis_pass.invalid_amount_event_ids,
            )
            issues_manager.resolve_event_issues_except(
                kind=IssueKind.MISSING_PRICE,
                still_active_ids=cost_basis_pass.missing_price_event_ids,
                from_ts=from_ts,
            )
            issues_manager.resolve_event_issues_except(
                kind=IssueKind.MISSING_COST_BASIS,
                still_active_ids=cost_basis_pass.missing_cost_basis_event_ids,
                from_ts=from_ts,
            )
            issues_manager.resolve_event_issues_except(
                kind=IssueKind.INCOMPLETE_SWAP,
                still_active_ids=cost_basis_pass.incomplete_swap_event_ids,
                from_ts=from_ts,
            )
            _detect_unmatched_exchange_transfer_issues(
                database=database,
                ignored_asset_ids=ignored_asset_ids,
                ignored_action_ids=ignored_action_ids,
                asset_movement_time_range=settings.asset_movement_time_range,
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
