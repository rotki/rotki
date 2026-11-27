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
from collections import defaultdict, deque
from itertools import chain, starmap
from operator import itemgetter
from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.accounting.cost_basis.eth2 import (
    Eth2StakingCostBasis,
    validator_eth2_bucket,
)
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
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2, UNKNOWN_VALIDATOR_INDEX
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH2, A_KFEE
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.filtering import AccountingRulesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.cause import TRANSIENT_FAILURE_CAUSES
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
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
    _get_wallet_protocol,
    process_historical_balances,
)
from rotkehlchen.types import Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now
from rotkehlchen.utils.mixins.lockable import skip_if_running

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.accounting.cost_basis.lots import ConsumedLot, SpendResult
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
ASSET_MOVEMENT_TRANSIT_LOCATION: Final = 'asset_movement_match'


def _asset_movement_transit_bucket(match_key: str) -> Bucket:
    """Internal in-flight lot bucket for a matched exchange transfer group."""
    return Bucket(
        location=ASSET_MOVEMENT_TRANSIT_LOCATION,
        location_label=f'match:{match_key}',
        protocol=None,
        asset='transit',
    )


class _AssetMovementMatch(NamedTuple):
    """A validated connected component of ASSET_MOVEMENT_MATCH linked events."""
    match_key: str
    out_ids: tuple[int, ...]
    in_ids: tuple[int, ...]
    in_move_amounts: tuple[tuple[int, FVal], ...]
    last_in_id: int
    total_out_amount: FVal
    total_in_amount: FVal
    min_ts: TimestampMS
    max_ts: TimestampMS
    endpoint_buckets: tuple[tuple[int, tuple[Bucket, ...]], ...]

    @property
    def transit_bucket(self) -> Bucket:
        return _asset_movement_transit_bucket(self.match_key)

    def move_amount_for_in(self, in_event_id: int) -> FVal:
        for ev_id, amount in self.in_move_amounts:
            if ev_id == in_event_id:
                return amount
        return self.total_out_amount

    @property
    def signature(self) -> str:
        """Everything the rows of the legs depend on: membership, buckets, split, and time span."""
        in_amounts = ','.join(f'{ev_id}:{amount}' for ev_id, amount in self.in_move_amounts)
        buckets = json.dumps(
            [
                [ev_id, [list(bucket) for bucket in ev_buckets]]
                for ev_id, ev_buckets in self.endpoint_buckets
            ],
            separators=(',', ':'),
        )
        return (
            f'{self.match_key}|{self.total_out_amount}|{self.total_in_amount}|{in_amounts}|'
            f'{self.min_ts}-{self.max_ts}|{buckets}'
        )


class _DeferredMatchIn(NamedTuple):
    """An IN leg of a match recorded before an OUT leg, waiting for that OUT to be applied."""
    event: HistoryBaseEntry
    destination: Bucket
    timestamp: Timestamp
    is_stale: bool
    rule: BaseEventSettings | None


class _DeferredEvent(NamedTuple):
    """An event touching a bucket whose reverse-timestamp matched IN is still waiting."""
    event: HistoryBaseEntry
    next_event: HistoryBaseEntry | None
    swap_fee_events: tuple[HistoryBaseEntry, ...]


def _load_asset_movement_matches(
        database: DBHandler,
        cursor: DBCursor,
        ignored_asset_ids: set[str],
        treat_eth2_as_eth: bool,
) -> dict[int, _AssetMovementMatch]:
    """Load validated ASSET_MOVEMENT_MATCH links grouped by connected component.

    Symmetric exchange-to-exchange links collapse into one component, and 1-to-many / many-to-1
    matches share a single transit bucket. Components with ignored assets, ignored actions,
    fiat assets, non-positive amounts, or missing opposite directions are skipped.
    """
    adj: defaultdict[int, set[int]] = defaultdict(set)
    for left_id, right_id in cursor.execute(
        'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type = ?',
        (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
    ):
        l_id, r_id = int(left_id), int(right_id)
        adj[l_id].add(r_id)
        adj[r_id].add(l_id)

    if len(adj) == 0:
        return {}

    dbevents = DBHistoryEvents(database)
    endpoints: dict[int, HistoryBaseEntry] = {}
    for chunk, _ in get_query_chunks(list(adj)):
        for ev in dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                identifiers=list(chunk),
                exclude_ignored_assets=False,
                exclude_ignored_actions=False,
                exclude_untracked_withdrawals=False,
            ),
        ):
            if ev.identifier is not None:
                endpoints[ev.identifier] = ev

    ignored_actions = {
        row[0] for row in cursor.execute('SELECT identifier FROM ignored_actions')
    }
    matches: dict[int, _AssetMovementMatch] = {}
    visited: set[int] = set()
    for start_id in adj:
        if start_id in visited:
            continue
        component: list[int] = []
        queue: deque[int] = deque([start_id])
        visited.add(start_id)
        while len(queue) > 0:
            curr = queue.popleft()
            component.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        out_ids: list[int] = []
        in_entries: list[tuple[tuple[int, str, int, int], int, FVal]] = []
        endpoint_buckets: list[tuple[int, tuple[Bucket, ...]]] = []
        total_out_amount, total_in_amount = ZERO, ZERO
        min_ts: TimestampMS | None = None
        max_ts: TimestampMS | None = None
        valid = True
        for ev_id in sorted(component):
            if (endpoint := endpoints.get(ev_id)) is None:
                valid = False
                break
            if (
                endpoint.asset.identifier in ignored_asset_ids or
                endpoint.group_identifier in ignored_actions
            ):
                valid = False
                break
            if endpoint.amount <= ZERO or endpoint.asset.is_fiat():
                valid = False
                break

            direction = endpoint.maybe_get_direction(for_balance_tracking=True)
            if direction not in (EventDirection.OUT, EventDirection.IN):
                valid = False
                break

            bucket_directions = Bucket.from_event(
                event=endpoint,
                treat_eth2_as_eth=treat_eth2_as_eth,
            )
            if len(bucket_directions) != 1 or bucket_directions[0][1] != direction:
                valid = False
                break

            if direction == EventDirection.OUT:
                out_ids.append(ev_id)
                total_out_amount += endpoint.amount
            else:
                in_entries.append((
                    (
                        int(endpoint.timestamp),
                        endpoint.group_identifier,
                        endpoint.sequence_index,
                        ev_id,
                    ),
                    ev_id,
                    endpoint.amount,
                ))
                total_in_amount += endpoint.amount

            endpoint_buckets.append((ev_id, (bucket_directions[0][0],)))
            min_ts = endpoint.timestamp if min_ts is None or endpoint.timestamp < min_ts else min_ts  # noqa: E501
            max_ts = endpoint.timestamp if max_ts is None or endpoint.timestamp > max_ts else max_ts  # noqa: E501

        if not valid or len(out_ids) == 0 or len(in_entries) == 0 or min_ts is None or max_ts is None:  # noqa: E501
            continue

        # Order IN legs identically to the event query so cumulative telescoping shares sum
        # to `total_out_amount` without rounding dust on 1-to-many unequal-total matches.
        in_entries.sort(key=itemgetter(0))
        in_ids = tuple(ev_id for _key, ev_id, _amt in in_entries)
        in_move_amounts: list[tuple[int, FVal]] = []
        if len(in_entries) == 1:
            in_move_amounts.append((in_entries[0][1], total_out_amount))
        elif total_out_amount == total_in_amount:
            in_move_amounts.extend((ev_id, ev_amount) for _key, ev_id, ev_amount in in_entries)
        else:
            cum_in, prev_cum_out = ZERO, ZERO
            last_idx = len(in_entries) - 1
            for idx, (_key, ev_id, ev_amount) in enumerate(in_entries):
                cum_in += ev_amount
                next_cum_out = (
                    total_out_amount if idx == last_idx
                    else total_out_amount * cum_in / total_in_amount
                )
                in_move_amounts.append((ev_id, next_cum_out - prev_cum_out))
                prev_cum_out = next_cum_out

        # Encode full OUT and IN membership so adding or removing any leg changes the transit
        # bucket key and forces checkpoints spanning the match to step back.
        out_key = ','.join(str(ev_id) for ev_id in out_ids)
        in_key = ','.join(str(ev_id) for ev_id in in_ids)
        match = _AssetMovementMatch(
            match_key=f'{out_key}->{in_key}',
            out_ids=tuple(out_ids),
            in_ids=in_ids,
            in_move_amounts=tuple(in_move_amounts),
            last_in_id=in_ids[-1],
            total_out_amount=total_out_amount,
            total_in_amount=total_in_amount,
            min_ts=min_ts,
            max_ts=max_ts,
            endpoint_buckets=tuple(endpoint_buckets),
        )
        for ev_id in component:
            matches[ev_id] = match

    return matches


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


def _is_matching_pair_receive_role(
        out_event: HistoryBaseEntry,
        candidate: HistoryBaseEntry,
) -> bool:
    """Whether `candidate` has the event type/subtype of `out_event`'s receiving leg."""
    if (
        out_event.event_type in (
            HistoryEventType.TRADE,
            HistoryEventType.MULTI_TRADE,
            HistoryEventType.MIGRATE,
        ) and
        out_event.event_subtype == HistoryEventSubType.SPEND
    ):
        return (
            candidate.event_type == out_event.event_type and
            candidate.event_subtype == HistoryEventSubType.RECEIVE
        )
    if out_event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED:
        return candidate.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED
    if out_event.event_subtype == HistoryEventSubType.RETURN_WRAPPED:
        return candidate.event_subtype == HistoryEventSubType.REDEEM_WRAPPED
    if out_event.event_subtype == HistoryEventSubType.BRIDGE:
        return candidate.event_subtype == HistoryEventSubType.BRIDGE
    return candidate.event_subtype not in (
        HistoryEventSubType.AIRDROP,
        HistoryEventSubType.APPROVE,
        HistoryEventSubType.FEE,
        HistoryEventSubType.REWARD,
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
            ignored_asset_ids: set[str] | None = None,
            asset_movement_matches: dict[int, _AssetMovementMatch] | None = None,
            match_event_positions: dict[int, int] | None = None,
            match_events: dict[int, HistoryBaseEntry] | None = None,
    ) -> None:
        self.settings = settings
        self.rules = rules
        self.from_ts = from_ts
        self.stored_basis = stored_basis
        self.tracked_eth_accounts = tracked_eth_accounts
        self.ignored_asset_ids: set[str] = set() if ignored_asset_ids is None else ignored_asset_ids  # noqa: E501
        self.asset_movement_matches: dict[int, _AssetMovementMatch] = (
            {} if asset_movement_matches is None else asset_movement_matches
        )
        self.match_event_positions: dict[int, int] = (
            {} if match_event_positions is None else match_event_positions
        )
        self.match_events: dict[int, HistoryBaseEntry] = (
            {} if match_events is None else match_events
        )
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
        # Surviving legs of a swap or basis-transfer group skipped due to an ignored asset.
        self._skipped_event_ids: set[int] = set()
        # OUT legs that an IN leg recorded before them waits for, see `_apply_matched_in`.
        self._pending_match_out_ids: dict[int, _AssetMovementMatch] = {}
        self._deferred_match_ins: dict[str, list[_DeferredMatchIn]] = {}
        # Buckets with a waiting reverse-timestamp IN (or transitively affected by one), and the
        # intervening events deferred behind them so destination-bucket order is preserved too.
        self._deferred_buckets: defaultdict[Bucket, set[str]] = defaultdict(set)
        self._deferred_events: list[_DeferredEvent] = []
        self._deferred_group_ids: dict[int, set[str]] = {}
        self._visited_match_out_ids: set[int] = set()
        self._match_waits_on: defaultdict[str, set[str]] = defaultdict(set)
        self._pending_resumes: deque[_AssetMovementMatch] = deque()
        self._is_replaying_deferred = False
        self._replaying_deferred_min_ts: TimestampMS | None = None
        self.eth2 = Eth2StakingCostBasis(host=self, validator_types=validator_types)

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
        if (unknown_amount := move_amount - sum((entry.amount for entry in moved), start=ZERO)) > ZERO:  # noqa: E501
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
        )

        in_is_stale = self.from_ts is None or received.timestamp >= self.from_ts
        if not is_stale and not in_is_stale:
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

        rate, counts_cost_basis, count_entire_amount_spend = self._resolve_spend_treatment(
            event=event,
            timestamp=timestamp,
            rule=rule,
            swap_proceeds=swap_proceeds,
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
        """Whether the last applied event left state for an event after it.

        That state is what pairs the two sides of a swap, a basis transfer, an ignored
        swap/basis-transfer group, or an IN leg of a match waiting for its OUT leg.
        """
        return (
            len(self._swap_basis) != 0 or
            len(self._swap_proceeds) != 0 or
            len(self._basis_transfer_receives) != 0 or
            len(self._skipped_event_ids) != 0 or
            len(self._pending_match_out_ids) != 0 or
            len(self._deferred_events) != 0
        )

    @property
    def earliest_deferred_ts(self) -> TimestampMS | None:
        """Earliest timestamp of any deferred reverse-timestamp receipt or waiting event."""
        timestamps = [
            deferred.event.timestamp
            for deferred_list in self._deferred_match_ins.values()
            for deferred in deferred_list
        ]
        timestamps.extend(deferred.event.timestamp for deferred in self._deferred_events)
        if self._replaying_deferred_min_ts is not None:
            timestamps.append(self._replaying_deferred_min_ts)
        return min(timestamps) if len(timestamps) != 0 else None

    def _should_skip_ignored_group(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry,
            rule: BaseEventSettings,
            bucket_directions: Sequence[tuple[Bucket, EventDirection]],
            swap_fee_events: Sequence[HistoryBaseEntry],
            treat_eth2_as_eth: bool,
    ) -> bool:
        """Skip the whole swap or basis-transfer group when any leg uses an ignored asset."""
        if len(self.ignored_asset_ids) == 0 or not _is_matching_pair_receive_role(event, next_event):  # noqa: E501
            return False

        assert next_event.identifier is not None
        if rule.accounting_treatment == TxAccountingTreatment.BASIS_TRANSFER:
            if (
                len(bucket_directions) != 1 or
                bucket_directions[0][1] != EventDirection.OUT or
                next_event.asset.is_fiat()
            ):
                return False

            in_buckets = Bucket.from_event(event=next_event, treat_eth2_as_eth=treat_eth2_as_eth)
            if len(in_buckets) != 1 or in_buckets[0][1] != EventDirection.IN:
                return False

            if (
                event.asset.identifier in self.ignored_asset_ids or
                next_event.asset.identifier in self.ignored_asset_ids
            ):
                self._skipped_event_ids.add(next_event.identifier)
                return True
            return False

        if (
            _swap_leg_direction(event, bucket_directions) != EventDirection.OUT or
            _swap_leg_direction(
                next_event,
                [] if next_event.asset.is_fiat() else Bucket.from_event(
                    event=next_event,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                ),
            ) != EventDirection.IN
        ):
            return False

        if (
            event.asset.identifier in self.ignored_asset_ids or
            next_event.asset.identifier in self.ignored_asset_ids or
            any(fee.asset.identifier in self.ignored_asset_ids for fee in swap_fee_events)
        ):
            self._skipped_event_ids.add(next_event.identifier)
            for fee in swap_fee_events:
                assert fee.identifier is not None
                self._skipped_event_ids.add(fee.identifier)
            return True

        return False

    def _has_blocked_match_endpoint(
            self,
            event_ids: Sequence[int],
            expected_direction: EventDirection,
            treat_eth2_as_eth: bool,
    ) -> bool:
        """Whether any matched leg present in this pass targets a blocked bucket."""
        for ev_id in event_ids:
            if (ev := self.match_events.get(ev_id)) is None:
                continue
            ev_buckets = Bucket.from_event(event=ev, treat_eth2_as_eth=treat_eth2_as_eth)
            if (
                len(ev_buckets) == 1 and
                ev_buckets[0][1] == expected_direction and
                ev_buckets[0][0] in self.blocked_buckets
            ):
                return True
        return False

    def _apply_matched_out(
            self,
            event: HistoryBaseEntry,
            source: Bucket,
            match: _AssetMovementMatch,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
            treat_eth2_as_eth: bool,
    ) -> None:
        """Move lots out of `source` into the match's transit bucket without realizing PnL.

        If `source` is blocked, the leg is skipped and transit is marked blocked so healthy IN
        legs fall back to standalone receives. If `source` is healthy but transit, an IN leg's
        bucket, or the bucket of a sibling OUT leg not applied yet is blocked, transit carryover
        is skipped and `source` still spends its lots via `_spend` so withdrawn lots do not
        remain in the healthy bucket. A sibling OUT leg that was already applied has moved its
        lots into transit, so its bucket getting blocked afterwards does not affect this leg.
        """
        assert event.identifier is not None
        self._visited_match_out_ids.add(event.identifier)
        self._pending_match_out_ids.pop(event.identifier, None)
        transit = match.transit_bucket
        if source in self.blocked_buckets:
            self.blocked_buckets.add(transit)
            return

        if (
            transit in self.blocked_buckets or
            self._has_blocked_match_endpoint(
                event_ids=[
                    out_id for out_id in match.out_ids
                    if out_id not in self._visited_match_out_ids
                ],
                expected_direction=EventDirection.OUT,
                treat_eth2_as_eth=treat_eth2_as_eth,
            ) or
            self._has_blocked_match_endpoint(
                event_ids=match.in_ids,
                expected_direction=EventDirection.IN,
                treat_eth2_as_eth=treat_eth2_as_eth,
            )
        ):
            self.blocked_buckets.add(transit)
            self._spend(event, source, timestamp, is_stale, rule)
            return

        moved = self.lots.transfer(
            source=source,
            destination=transit,
            asset=event.asset,
            amount=event.amount,
            event=event,
        )
        if not is_stale:
            return

        basis = sum((entry.amount * entry.basis_per_unit for entry in moved), start=ZERO)
        self.add_row(
            event=event,
            bucket=source,
            direction=CostBasisDirection.SPEND,
            lots_consumed=[entry.serialize() for entry in moved],
            realized_pnl=ZERO,
            basis_removed=basis,
            post_spend_basis_remaining=self.lots.basis_remaining(source),
        )

    def _apply_matched_in(
            self,
            event: HistoryBaseEntry,
            destination: Bucket,
            match: _AssetMovementMatch,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
    ) -> None:
        """Pull lots from the match's transit bucket into `destination`, keeping basis and age.

        A leg recorded before an OUT leg of its match waits until that OUT is applied at its own
        position, so the source bucket gives the lots it holds at the withdrawal and its events in
        between consume theirs in order. Subsequent events touching `destination` are also
        deferred behind this match and replayed once the lots arrive, preserving destination-bucket
        order as well.
        """
        assert event.identifier is not None
        if (in_pos := self.match_event_positions.get(event.identifier)) is not None and len(
            pending_out_ids := [
                out_id for out_id in match.out_ids
                if (
                    out_id not in self._visited_match_out_ids and
                    (out_pos := self.match_event_positions.get(out_id)) is not None and
                    out_pos > in_pos
                )
            ],
        ) != 0:
            self._pending_match_out_ids.update(dict.fromkeys(pending_out_ids, match))
            self._deferred_match_ins.setdefault(match.match_key, []).append(_DeferredMatchIn(
                event=event,
                destination=destination,
                timestamp=timestamp,
                is_stale=is_stale,
                rule=rule,
            ))
            self._deferred_buckets[destination].add(match.match_key)
            return

        self._complete_matched_in(
            event=event,
            destination=destination,
            match=match,
            timestamp=timestamp,
            is_stale=is_stale,
            rule=rule,
        )

    def _match_depends_on(self, start_key: str, target_key: str) -> bool:
        """Whether `start_key` transitively waits on `target_key` in the deferral graph."""
        visited: set[str] = {start_key}
        queue: deque[str] = deque([start_key])
        while len(queue) > 0:
            curr = queue.popleft()
            for nxt in self._match_waits_on.get(curr, ()):
                if nxt == target_key:
                    return True
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return False

    def _maybe_defer_event(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry],
    ) -> bool:
        """Defer an event that depends on a bucket with a waiting reverse-timestamp matched IN."""
        if (
            event.identifier is None or
            (len(self._deferred_buckets) == 0 and len(self._deferred_group_ids) == 0)
        ):
            return False

        if (
            event.identifier in self._skipped_event_ids or
            event.identifier in self._basis_transfer_receives
        ):
            return False

        bucket_directions = (
            [] if event.asset.is_fiat()
            else Bucket.from_event(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
        )
        touched_buckets: set[Bucket] = {bucket for bucket, _dir in bucket_directions}
        if (
            isinstance(event, EthDepositEvent | EthWithdrawalEvent) and
            event.validator_index != UNKNOWN_VALIDATOR_INDEX
        ):
            touched_buckets.add(validator_eth2_bucket(event.validator_index))
        elif (
            isinstance(event, OnchainEvent) and
            event.counterparty == CPT_ETH2 and
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.event_subtype == HistoryEventSubType.CONSOLIDATE and
            event.extra_data is not None and
            isinstance(source_validator := event.extra_data.get('source_validator_index'), int) and
            isinstance(target_validator := event.extra_data.get('target_validator_index'), int) and
            source_validator != target_validator
        ):
            touched_buckets.add(validator_eth2_bucket(source_validator))
            touched_buckets.add(validator_eth2_bucket(target_validator))

        event_match = self.asset_movement_matches.get(event.identifier)
        if (
            event_match is not None and
            len(bucket_directions) == 1 and
            bucket_directions[0][1] == EventDirection.IN
        ):
            touched_buckets.add(event_match.transit_bucket)

        rule = self.rules.get(event)
        next_buckets = (
            [] if next_event is None or next_event.asset.is_fiat()
            else Bucket.from_event(event=next_event, treat_eth2_as_eth=treat_eth2_as_eth)
        )
        is_paired = (
            event.amount > ZERO and
            rule is not None and
            rule.accounting_treatment is not None and
            next_event is not None and
            next_event.identifier is not None and
            next_event.group_identifier == event.group_identifier and
            next_event.amount > ZERO and
            _is_matching_pair_receive_role(event, next_event) and
            _swap_leg_direction(event, bucket_directions) == EventDirection.OUT and
            _swap_leg_direction(next_event, next_buckets) == EventDirection.IN
        )
        if is_paired:
            touched_buckets.update(bucket for bucket, _dir in next_buckets)
            for fee in swap_fee_events:
                if not fee.asset.is_fiat():
                    touched_buckets.update(
                        bucket for bucket, _dir in Bucket.from_event(
                            event=fee,
                            treat_eth2_as_eth=treat_eth2_as_eth,
                        )
                    )

        blocking_keys = set(self._deferred_group_ids.pop(event.identifier, ()))
        for bucket in touched_buckets:
            if (keys := self._deferred_buckets.get(bucket)) is not None:
                blocking_keys.update(keys)
        if len(blocking_keys) == 0:
            return False

        if (out_match := self._pending_match_out_ids.get(event.identifier)) is not None:
            if (
                out_match.match_key in blocking_keys or
                any(self._match_depends_on(key, out_match.match_key) for key in blocking_keys)
            ):
                return False  # break circular timestamp dependency
            self._match_waits_on[out_match.match_key].update(blocking_keys)
            touched_buckets.add(out_match.transit_bucket)
        elif (
            event_match is not None and
            len(bucket_directions) == 1 and
            bucket_directions[0][1] == EventDirection.OUT
        ):
            touched_buckets.add(event_match.transit_bucket)

        for bucket in touched_buckets:
            self._deferred_buckets[bucket].update(blocking_keys)
        if is_paired:
            assert next_event is not None and next_event.identifier is not None
            self._deferred_group_ids.setdefault(next_event.identifier, set()).update(blocking_keys)
            for fee in swap_fee_events:
                assert fee.identifier is not None
                self._deferred_group_ids.setdefault(fee.identifier, set()).update(blocking_keys)

        self._deferred_events.append(_DeferredEvent(
            event=event,
            next_event=next_event,
            swap_fee_events=tuple(swap_fee_events),
        ))
        return True

    def _rebuild_deferred_state(self) -> None:
        """Rebuild deferral tracking from only the still-pending reverse-timestamp matches."""
        self._deferred_buckets.clear()
        self._deferred_group_ids.clear()
        self._match_waits_on.clear()
        for match_key, deferred_ins in self._deferred_match_ins.items():
            for deferred in deferred_ins:
                self._deferred_buckets[deferred.destination].add(match_key)

    def _resume_deferred_match_ins(
            self,
            match: _AssetMovementMatch,
            treat_eth2_as_eth: bool,
    ) -> None:
        """Complete the IN legs of the match that waited, once none of its OUT legs is pending.

        After the IN legs move lots into their destination buckets, deferral tracking is rebuilt
        from only the still-pending matches and all saved deferred events are replayed in their
        original order so earlier events that became unblocked are not re-deferred behind later
        still-blocked ones. Nested resumes triggered during replay are queued and preserve the
        unprocessed tail of the replay list in chronological order. An OUT leg visited without
        reaching `_apply_matched_out` moved nothing into transit, so the caller blocks transit
        and the waiting legs fall back to standalone receives.
        """
        if match.match_key not in self._deferred_match_ins or any(
            out_id in self._pending_match_out_ids for out_id in match.out_ids
        ):
            return

        self._pending_resumes.append(match)
        if self._is_replaying_deferred:
            return

        self._is_replaying_deferred = True
        prev_replaying_min_ts = self._replaying_deferred_min_ts
        try:
            while len(self._pending_resumes) != 0:
                resumed_match = self._pending_resumes.popleft()
                if resumed_match.match_key not in self._deferred_match_ins or any(
                    out_id in self._pending_match_out_ids for out_id in resumed_match.out_ids
                ):
                    continue

                deferred_ins = self._deferred_match_ins.pop(resumed_match.match_key)
                batch_min_ts = min(
                    chain(
                        (deferred.event.timestamp for deferred in deferred_ins),
                        (deferred_ev.event.timestamp for deferred_ev in self._deferred_events),
                    ),
                )
                self._replaying_deferred_min_ts = (
                    batch_min_ts if self._replaying_deferred_min_ts is None
                    else min(self._replaying_deferred_min_ts, batch_min_ts)
                )
                for deferred in deferred_ins:
                    self._complete_matched_in(
                        event=deferred.event,
                        destination=deferred.destination,
                        match=resumed_match,
                        timestamp=deferred.timestamp,
                        is_stale=deferred.is_stale,
                        rule=deferred.rule,
                    )

                self._rebuild_deferred_state()
                pending_events = self._deferred_events
                self._deferred_events = []
                for idx, deferred_ev in enumerate(pending_events):
                    self.apply(
                        event=deferred_ev.event,
                        next_event=deferred_ev.next_event,
                        treat_eth2_as_eth=treat_eth2_as_eth,
                        swap_fee_events=deferred_ev.swap_fee_events,
                    )
                    if len(self._pending_resumes) != 0:
                        self._deferred_events.extend(pending_events[idx + 1:])
                        break
        finally:
            self._pending_resumes.clear()
            self._is_replaying_deferred = False

        # Only restored on clean completion so an interrupting price error keeps `batch_min_ts`
        # visible in `earliest_deferred_ts`.
        self._replaying_deferred_min_ts = prev_replaying_min_ts

    def _complete_matched_in(
            self,
            event: HistoryBaseEntry,
            destination: Bucket,
            match: _AssetMovementMatch,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
    ) -> None:
        """Move the share of the transit lots of the IN leg into `destination`.

        When transit or `destination` is blocked the carryover is skipped: a blocked destination
        stays skipped, while a healthy one falls back to a standalone `receive`.
        """
        assert event.identifier is not None
        transit = match.transit_bucket
        is_last_in = event.identifier == match.last_in_id
        if destination in self.blocked_buckets or transit in self.blocked_buckets:
            if is_last_in:
                self.lots.drop_bucket(transit)
                self.blocked_buckets.discard(transit)
            else:
                self.blocked_buckets.add(transit)
            if destination not in self.blocked_buckets:
                self.receive(event, destination, timestamp, is_stale, rule)
            return

        move_amount = match.move_amount_for_in(event.identifier)
        _moved, lot_ids, basis = self.move_lots(
            event=event,
            source=transit,
            destination=destination,
            move_amount=move_amount,
            dest_amount=event.amount,
            received=event,
        )
        if is_last_in:
            self.lots.drop_bucket(transit)
        else:
            self.lots.drop_empty(transit)
        if is_stale:
            self.add_row(
                event=event,
                bucket=destination,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=','.join(lot_ids),
                basis_per_unit=basis / event.amount,
                basis_source=BasisSource.TRANSFER_IN,
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

        Afterwards only the next event (and swap fee events), or the OUT legs a matched IN leg
        waits for, can have pairing state left, see `has_pending_pair`. May raise
        NoPriceForGivenTimestamp or RemoteError if the price oracles are rate limited or fail
        transiently.
        """
        if self._maybe_defer_event(
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        ):
            return

        self._apply(
            event=event,
            next_event=next_event,
            treat_eth2_as_eth=treat_eth2_as_eth,
            swap_fee_events=swap_fee_events,
        )
        if event.identifier is None:
            return

        self._swap_basis.pop(event.identifier, None)  # left by a side that was not applied
        self._swap_proceeds.pop(event.identifier, None)
        if (
            (match := self.asset_movement_matches.get(event.identifier)) is not None and
            event.identifier in match.out_ids and
            event.identifier not in self._visited_match_out_ids
        ):
            self._visited_match_out_ids.add(event.identifier)
            self._pending_match_out_ids.pop(event.identifier, None)
            self.blocked_buckets.add(match.transit_bucket)  # it moved nothing into transit
            self._resume_deferred_match_ins(match, treat_eth2_as_eth=treat_eth2_as_eth)

    def _apply(
            self,
            event: HistoryBaseEntry,
            next_event: HistoryBaseEntry | None,
            treat_eth2_as_eth: bool,
            swap_fee_events: Sequence[HistoryBaseEntry] = (),
    ) -> None:
        if event.identifier is None:
            return

        if event.identifier in self._skipped_event_ids:
            self._skipped_event_ids.remove(event.identifier)
            return

        if (
            event.asset.identifier not in self.ignored_asset_ids and
            self.eth2.handle_informational_event(event)
        ):
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
        rule = self.rules.get(event)
        if (
            event.amount > ZERO and
            rule is not None and
            rule.accounting_treatment is not None and
            next_event is not None and
            next_event.identifier is not None and
            next_event.group_identifier == event.group_identifier and
            next_event.amount > ZERO and
            self._should_skip_ignored_group(
                event=event,
                next_event=next_event,
                rule=rule,
                bucket_directions=bucket_directions,
                swap_fee_events=swap_fee_events,
                treat_eth2_as_eth=treat_eth2_as_eth,
            )
        ):
            return

        if event.asset.identifier in self.ignored_asset_ids:
            return

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
            if (match := self.asset_movement_matches.get(event.identifier)) is not None:
                if direction == EventDirection.OUT:
                    self._apply_matched_out(
                        event=event,
                        source=bucket,
                        match=match,
                        timestamp=timestamp,
                        is_stale=is_stale,
                        rule=rule,
                        treat_eth2_as_eth=treat_eth2_as_eth,
                    )
                    self._resume_deferred_match_ins(match, treat_eth2_as_eth=treat_eth2_as_eth)
                else:
                    self._apply_matched_in(
                        event=event,
                        destination=bucket,
                        match=match,
                        timestamp=timestamp,
                        is_stale=is_stale,
                        rule=rule,
                    )
                return

            if bucket in self.blocked_buckets:
                return

            if direction == EventDirection.IN:
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
        match_snapshot: str,
) -> None:
    """Write a batch of rows, dropping the rows that are being replaced on the first write.

    The delete is what keeps a pass idempotent. The unique constraint of the table can not,
    since SQLite treats the NULL location labels and protocols of two rows as distinct. The
    checkpoints after `from_ts` hold lots that the stale events may change, and go with them.
    The asset movement matches the rewritten rows are computed with replace the stored ones
    along with them, see `DBCacheStatic.COST_BASIS_MATCH_SNAPSHOT`.
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
        stale_floor = 0 if from_ts is None else from_ts
        write_cursor.execute(
            'UPDATE key_value_cache SET value = ? '
            'WHERE name = ? AND CAST(value AS INTEGER) > ?',
            (str(stale_floor), DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, stale_floor),
        )
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
            (DBCacheStatic.COST_BASIS_MATCH_SNAPSHOT.value, match_snapshot),
        )

    write_cursor.executemany(
        'INSERT OR REPLACE INTO event_cost_basis(event_identifier, location, location_label, '
        'protocol, asset, timestamp, sequence_index, direction, lot_created_id, basis_per_unit, '
        'basis_source, lots_consumed_json, proceeds, realized_pnl, taxfree_pnl, basis_removed, '
        'post_spend_basis_remaining, is_taxable, method) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows,
    )


def _pair_candidate_idx(
        events: Sequence[HistoryBaseEntry],
        idx: int,
        ignored_asset_ids: set[str],
        treat_eth2_as_eth: bool,
) -> int:
    """Index of the event that the event at `idx` may pair with as a swap or basis transfer.

    Unrelated events of ignored assets in the same group (such as an approval or an ignored
    airdrop) are skipped, so they do not split the two sides apart or trigger a false whole-group
    skip. Ignored receiving legs with the matching role are kept, so `_should_skip_ignored_group`
    skips the whole group.
    """
    out_event = events[idx]
    group_identifier = out_event.group_identifier
    pair_idx = idx + 1
    while (
        pair_idx < len(events) and
        (candidate := events[pair_idx]).group_identifier == group_identifier and
        candidate.asset.identifier in ignored_asset_ids
    ):
        if (
            candidate.event_type == out_event.event_type and
            candidate.event_subtype == HistoryEventSubType.SPEND
        ):
            break
        if (
            candidate.amount > ZERO and
            _is_matching_pair_receive_role(out_event, candidate) and
            _swap_leg_direction(
                candidate,
                [] if candidate.asset.is_fiat() else Bucket.from_event(
                    event=candidate,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                ),
            ) == EventDirection.IN
        ):
            break
        pair_idx += 1
    return pair_idx


def _collect_swap_fee_events(
        events: Sequence[HistoryBaseEntry],
        out_idx: int,
        fee_idx: int,
        ignored_asset_ids: set[str],
) -> list[HistoryBaseEntry]:
    """Collect fee events from `fee_idx` on, right after the (out, in) pair of a swap group.

    Unrelated events of ignored assets in the same group (such as an approval before or between
    fee legs) are skipped, while ignored fee legs themselves are kept so
    `_should_skip_ignored_group` can skip the whole swap group.
    """
    out_event = events[out_idx]
    fee_events: list[HistoryBaseEntry] = []
    while fee_idx < len(events):
        candidate = events[fee_idx]
        if candidate.group_identifier != out_event.group_identifier:
            break
        if (
            candidate.event_type == out_event.event_type and
            candidate.event_subtype == HistoryEventSubType.FEE
        ):
            if candidate.identifier is not None and candidate.amount > ZERO:
                fee_events.append(candidate)
            fee_idx += 1
            continue
        if (
            candidate.asset.identifier in ignored_asset_ids and
            not (
                candidate.event_type == out_event.event_type and
                candidate.event_subtype in (HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE)
            )
        ):
            fee_idx += 1
            continue
        break
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
        tracked_eth_accounts: set[str] = set(database.get_blockchain_accounts(cursor).eth)
        ignored_asset_ids = database.get_ignored_asset_ids(cursor=cursor)
        asset_movement_matches = _load_asset_movement_matches(
            database=database,
            cursor=cursor,
            ignored_asset_ids=ignored_asset_ids,
            treat_eth2_as_eth=settings.treat_eth2_as_eth,
        )
        unique_matches = tuple(dict.fromkeys(asset_movement_matches.values()))
        match_snapshot = {match.signature: int(match.min_ts) for match in unique_matches}
        serialized_match_snapshot = json.dumps(match_snapshot, separators=(',', ':'))
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
            stored_snapshot: dict[str, int] = json.loads(raw_snapshot) if (
                raw_snapshot := database.get_static_cache(
                    cursor=cursor,
                    name=DBCacheStatic.COST_BASIS_MATCH_SNAPSHOT,
                )
            ) is not None else {}
            # A match added, removed, or changed since the rows were computed (a link, an
            # ignore, a deleted or edited leg) changes the rows of all its legs, also those
            # before the stale marker that the change set.
            if (changed_min_ts := min(
                (
                    min_ts for signature, min_ts in chain(
                        stored_snapshot.items(),
                        match_snapshot.items(),
                    )
                    if (signature in stored_snapshot) != (signature in match_snapshot)
                ),
                default=None,
            )) is not None and changed_min_ts < from_ts:
                from_ts = TimestampMS(changed_min_ts)

        cost_basis_pass = _CostBasisPass(
            settings=settings,
            rules=rules,
            from_ts=from_ts,
            stored_basis={},
            tracked_eth_accounts=tracked_eth_accounts,
            validator_types=validator_types,
            ignored_asset_ids=ignored_asset_ids,
            asset_movement_matches=asset_movement_matches,
        )
        start_ts = TimestampMS(0)
        restored_terminal_ts: TimestampMS | None = None
        events_since_interval = 0
        if from_ts is not None:
            checkpoint_limit = from_ts
            stepped_back_for_orphan = False
            while (checkpoint_row := cursor.execute(
                'SELECT timestamp, state FROM cost_basis_checkpoints WHERE timestamp <= ? '
                'ORDER BY timestamp DESC LIMIT 1',
                (checkpoint_limit,),
            ).fetchone()) is not None:
                if (restored_events_since_interval := cost_basis_pass.restore_checkpoint(
                    checkpoint_row[1],
                )) is None:
                    break

                candidate_start_ts = TimestampMS(checkpoint_row[0])
                expected_transit_buckets = {
                    match.transit_bucket for match in unique_matches
                    if match.min_ts < candidate_start_ts <= match.max_ts
                }
                has_orphaned_transit = any(
                    bucket.location == ASSET_MOVEMENT_TRANSIT_LOCATION and
                    bucket not in expected_transit_buckets
                    for bucket in (
                        *cost_basis_pass.lots.buckets(),
                        *cost_basis_pass.blocked_buckets,
                    )
                )
                split_min_ts = min(
                    (
                        match.min_ts for match in unique_matches
                        if (
                            match.min_ts < candidate_start_ts <= match.max_ts and
                            not cost_basis_pass.lots.has_bucket(match.transit_bucket) and
                            match.transit_bucket not in cost_basis_pass.blocked_buckets
                        )
                    ),
                    default=None,
                )
                if split_min_ts is not None or has_orphaned_transit:
                    # A match link was created or removed across this checkpoint after it was
                    # taken; step back to an earlier clean checkpoint so both legs replay cleanly.
                    if split_min_ts is not None:
                        from_ts = min(from_ts, split_min_ts)
                    if has_orphaned_transit:
                        stepped_back_for_orphan = True
                    cost_basis_pass = _CostBasisPass(
                        settings=settings,
                        rules=rules,
                        from_ts=from_ts,
                        stored_basis={},
                        tracked_eth_accounts=tracked_eth_accounts,
                        validator_types=validator_types,
                        ignored_asset_ids=ignored_asset_ids,
                        asset_movement_matches=asset_movement_matches,
                    )
                    next_limit = TimestampMS(candidate_start_ts - 1)
                    checkpoint_limit = (
                        min(split_min_ts, next_limit) if split_min_ts is not None else next_limit
                    )
                    continue

                start_ts = candidate_start_ts
                if restored_events_since_interval > 0:
                    restored_terminal_ts = start_ts
                    events_since_interval = restored_events_since_interval
                break

            if stepped_back_for_orphan:
                from_ts = min(from_ts, start_ts)
                cost_basis_pass.from_ts = from_ts

            # Pull `from_ts` back if any match spans `from_ts`, clamping at `start_ts` when an
            # earlier leg was already checkpointed into transit, so every replayed leg and
            # deferred destination event affected by legs at `>= from_ts` is rewritten.
            all_match_spans = [(match.min_ts, match.max_ts) for match in unique_matches]
            while (spanning_min_ts := min(
                (
                    effective_min_ts for span_min_ts, span_max_ts in all_match_spans
                    if (effective_min_ts := max(start_ts, span_min_ts)) < from_ts <= span_max_ts
                ),
                default=None,
            )) is not None:
                from_ts = spanning_min_ts
                cost_basis_pass.from_ts = from_ts

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
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=event_filter,
        )

    if len(asset_movement_matches) != 0:
        for idx, event in enumerate(events):
            if event.identifier is not None and event.identifier in asset_movement_matches:
                cost_basis_pass.match_event_positions[event.identifier] = idx
                cost_basis_pass.match_events[event.identifier] = event

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
            if isinstance(event, EthWithdrawalEvent) and event.is_exit_or_blocknumber == 0:
                lookahead = idx + 1
                while lookahead < total_events and events[lookahead].timestamp == event.timestamp:
                    cost_basis_pass.eth2.buffer_withdrawal_request(
                        events[lookahead],
                        prebuffered=True,
                    )
                    lookahead += 1

            next_event = events[idx + 1] if idx + 1 < total_events else None
            pair_idx = (
                idx + 1 if len(ignored_asset_ids) == 0
                else _pair_candidate_idx(
                    events=events,
                    idx=idx,
                    ignored_asset_ids=ignored_asset_ids,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                )
            )
            pair_event = events[pair_idx] if pair_idx < total_events else None
            swap_fee_events: Sequence[HistoryBaseEntry] = (
                _collect_swap_fee_events(
                    events=events,
                    out_idx=idx,
                    fee_idx=pair_idx + 1,
                    ignored_asset_ids=ignored_asset_ids,
                )
                if (
                    pair_idx + 1 < total_events and
                    events[pair_idx + 1].group_identifier == event.group_identifier and (
                        len(ignored_asset_ids) != 0 or (
                            events[pair_idx + 1].event_type == event.event_type and
                            events[pair_idx + 1].event_subtype == HistoryEventSubType.FEE
                        )
                    )
                )
                else ()
            )
            try:
                cost_basis_pass.apply(
                    event=event,
                    next_event=pair_event,
                    treat_eth2_as_eth=treat_eth2_as_eth,
                    swap_fee_events=swap_fee_events,
                )
            except (NoPriceForGivenTimestamp, RemoteError) as e:
                log.warning('Stopping cost basis processing at event %s: %s', event.identifier, e)
                interrupted_at = event.timestamp
                if (earliest_deferred_ts := cost_basis_pass.earliest_deferred_ts) is not None:
                    interrupted_at = min(interrupted_at, earliest_deferred_ts)
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
                    _write_rows(
                        write_cursor=write_cursor,
                        rows=cost_basis_pass.rows,
                        from_ts=from_ts,
                        first_batch_written=first_batch_written,
                        match_snapshot=serialized_match_snapshot,
                    )
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
                        pair_idx + 1
                        if (
                            pair_event is not None and
                            pair_event.identifier in cost_basis_pass._basis_transfer_receives
                        )
                        else idx + 1
                    )
                    if next_idx < total_events:
                        processed_ts = events[next_idx].timestamp
                        if (earliest_deferred_ts := cost_basis_pass.earliest_deferred_ts) is not None:  # noqa: E501
                            processed_ts = min(processed_ts, earliest_deferred_ts)
                        _record_progress(
                            write_cursor=write_cursor,
                            processed_ts=processed_ts,
                            modification_ts_at_start=modification_ts_at_start,
                        )
                first_batch_written, cost_basis_pass.rows = True, []
                _write_invalid_amount_issues(database, cost_basis_pass.invalid_amount_issues)
                cost_basis_pass.invalid_amount_issues = []
                checkpoint()  # cancellation checkpoint of the cost basis processing loop
                time.sleep(0)

        with database.user_write() as write_cursor:  # also when empty, to drop the replaced rows
            _write_rows(
                write_cursor=write_cursor,
                rows=cost_basis_pass.rows,
                from_ts=from_ts,
                first_batch_written=first_batch_written,
                match_snapshot=serialized_match_snapshot,
            )
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
