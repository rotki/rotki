"""ETH2 staking state and cost-basis mechanics for deposits, consolidations, and exits."""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.cost_basis.lots import BasisSource, CostBasisDirection
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    CPT_ETH2,
    MAX_EFFECTIVE_BALANCE,
    MIN_EFFECTIVE_BALANCE,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorType
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tasks.historical_balances import Bucket
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from typing import Protocol

    from rotkehlchen.accounting.cost_basis.lots import BucketLots, ConsumedLot, SpendResult
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.db.settings import DBSettings
    from rotkehlchen.history.data_issues.types import MissingPriceDirection
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.history.events.structures.eth2 import EthDepositEvent, EthWithdrawalEvent
    from rotkehlchen.types import Price, Timestamp

    class Eth2CostBasisHost(Protocol):
        """Cost-basis pass primitives used by `Eth2StakingCostBasis`."""

        settings: DBSettings
        lots: BucketLots[Bucket]
        blocked_buckets: set[Bucket]

        def get_price(self, asset: Asset, timestamp: Timestamp) -> Price | None: ...

        def record_missing_price(
                self,
                event: HistoryBaseEntry,
                bucket: Bucket,
                direction: MissingPriceDirection,
                amount: FVal | None = None,
        ) -> None: ...

        def record_missing_cost_basis(
                self,
                event: HistoryBaseEntry,
                bucket: Bucket,
                requested_amount: FVal,
                covered_amount: FVal,
        ) -> None: ...

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
        ) -> None: ...

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
        ) -> tuple[list[ConsumedLot], list[str], FVal]: ...

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
        ) -> None: ...

        def receive(
                self,
                event: HistoryBaseEntry,
                bucket: Bucket,
                timestamp: Timestamp,
                is_stale: bool,
                rule: BaseEventSettings | None,
                *,
                is_taxable: bool | None = None,
        ) -> None: ...

        def resolve_receive_basis(
                self,
                event: HistoryBaseEntry,
                timestamp: Timestamp,
                is_stale: bool,
                swap_basis: tuple[FVal, BasisSource] | None = None,
                *,
                use_stored_basis: bool = True,
        ) -> tuple[FVal, BasisSource]: ...

        @staticmethod
        def compute_receive_pnl(
                amount: FVal,
                basis: FVal,
                basis_source: BasisSource,
                is_taxable: bool,
        ) -> tuple[FVal | None, FVal | None]: ...

        @staticmethod
        def compute_spend_pnl(
                amount: FVal,
                rate: FVal | None,
                counts_cost_basis: bool,
                count_entire_amount_spend: bool,
                result: SpendResult | None = None,
        ) -> tuple[FVal | None, FVal | None, FVal | None]: ...


def validator_eth2_bucket(validator_index: int) -> Bucket:
    """Internal lot bucket holding staked ETH principal for a specific validator."""
    return Bucket(
        location=LOCATION_ETHEREUM,
        location_label=f'validator:{validator_index}',
        protocol=CPT_ETH2,
        asset=A_ETH.identifier,
    )


class Eth2StakingCostBasis:
    """Tracks per-validator ETH2 principal, consolidations, and EIP-7002 withdrawal requests.

    Separates staked principal (whose basis carries across validator deposits, consolidations,
    requested partial withdrawals, and exits) from consensus rewards and slashing losses.
    """

    def __init__(
            self,
            host: Eth2CostBasisHost,
            validator_types: dict[int, ValidatorType] | None = None,
    ) -> None:
        self._host = host
        self.validator_types = validator_types
        self._validator_principal: dict[int, FVal] = {}
        self._consolidated_sources: set[int] = set()
        self._withdrawal_requests: dict[int, list[tuple[TimestampMS, FVal]]] = {}
        self._prebuffered_request_ids: set[int] = set()

    def serialize_state(self) -> dict[str, Any]:
        """Serialize ETH2 validator tracking state into top-level checkpoint JSON fields."""
        return {
            'validator_principal': {str(k): str(v) for k, v in self._validator_principal.items()},
            'consolidated_sources': sorted(self._consolidated_sources),
            'validator_withdrawal_requests': {
                str(k): [[ts, str(amount)] for ts, amount in requests]
                for k, requests in self._withdrawal_requests.items()
                if requests
            },
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore ETH2 validator tracking state from checkpoint JSON fields."""
        self._validator_principal = {
            int(k): FVal(v) for k, v in state.get('validator_principal', {}).items()
        }
        self._consolidated_sources = set(state.get('consolidated_sources', ()))
        self._withdrawal_requests = {
            int(k): [(TimestampMS(int(ts)), FVal(amount)) for ts, amount in requests]
            for k, requests in state.get('validator_withdrawal_requests', {}).items()
            if requests
        }
        self._prebuffered_request_ids.clear()

    def buffer_withdrawal_request(
            self,
            event: HistoryBaseEntry,
            *,
            prebuffered: bool = False,
    ) -> bool:
        """Buffer an EIP-7002 partial withdrawal request for inline matching against 0x02 exits.

        `prebuffered=True` is used for same-timestamp lookahead when a partial withdrawal sorts
        before its request event at the exact same timestamp; the event's later normal visit
        consumes the prebuffered marker instead of buffering a duplicate.
        """
        if not (
            isinstance(event, OnchainEvent) and
            event.counterparty == CPT_ETH2 and
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.event_subtype == HistoryEventSubType.REMOVE_ASSET and
            event.extra_data is not None and
            isinstance(v_index := event.extra_data.get('validator_index'), int)
        ):
            return False

        if event.identifier is not None and event.identifier in self._prebuffered_request_ids:
            if not prebuffered:
                self._prebuffered_request_ids.remove(event.identifier)
            return True

        if event.amount > ZERO:
            self._withdrawal_requests.setdefault(v_index, []).append(
                (event.timestamp, event.amount),
            )
            if prebuffered and event.identifier is not None:
                self._prebuffered_request_ids.add(event.identifier)
        return True

    def handle_informational_event(self, event: HistoryBaseEntry) -> bool:
        """Handle ETH2 informational events (consolidations and EIP-7002 withdrawal requests)."""
        if not (
            isinstance(event, OnchainEvent) and
            event.counterparty == CPT_ETH2 and
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.extra_data is not None
        ):
            return False

        if (
            event.event_subtype == HistoryEventSubType.CONSOLIDATE and
            isinstance(source_validator := event.extra_data.get('source_validator_index'), int) and
            isinstance(target_validator := event.extra_data.get('target_validator_index'), int) and
            source_validator != target_validator
        ):
            self._consolidate_validator(
                event=event,
                source_validator=source_validator,
                target_validator=target_validator,
            )
            return True

        if event.event_subtype == HistoryEventSubType.REMOVE_ASSET:
            return self.buffer_withdrawal_request(event)

        return False

    def _consume_withdrawal_request(
            self,
            validator_index: int,
            timestamp: TimestampMS,
            amount: FVal,
    ) -> bool:
        """Pop the latest buffered EIP-7002 request matching `(req_ts <= timestamp, amount)`."""
        requests = self._withdrawal_requests.get(validator_index)
        if not requests:
            return False

        for idx in range(len(requests) - 1, -1, -1):
            req_ts, req_amount = requests[idx]
            if req_ts <= timestamp and req_amount == amount:
                requests.pop(idx)
                if not requests:
                    self._withdrawal_requests.pop(validator_index, None)
                return True

        return False

    def _consolidate_validator(
            self,
            event: HistoryBaseEntry,
            source_validator: int,
            target_validator: int,
    ) -> None:
        """Transfer staked principal and lots from a consolidated source validator to target."""
        self._consolidated_sources.add(source_validator)
        if source_validator in self._validator_principal:
            source_principal = self._validator_principal.pop(source_validator)
            has_source_principal = True
        elif (
            self.validator_types is not None and
            (source_type := self.validator_types.get(source_validator)) is not None and
            source_type != ValidatorType.ACCUMULATING
        ):
            source_principal = MIN_EFFECTIVE_BALANCE
            has_source_principal = True
        else:
            source_principal = ZERO
            has_source_principal = False

        if has_source_principal:
            self._validator_principal[target_validator] = (
                self._validator_principal.get(target_validator, ZERO) + source_principal
            )

        source_bucket = validator_eth2_bucket(source_validator)
        target_bucket = validator_eth2_bucket(target_validator)
        if (
            source_bucket not in self._host.blocked_buckets and
            target_bucket not in self._host.blocked_buckets and
            (lot_amount := self._host.lots.amount_remaining(source_bucket)) > ZERO
        ):
            self._host.lots.transfer(
                source=source_bucket,
                destination=target_bucket,
                asset=A_ETH,
                amount=lot_amount,
                event=event,
            )

    def apply_deposit(
            self,
            event: EthDepositEvent,
            source: Bucket,
            destination: Bucket,
            is_stale: bool,
    ) -> None:
        """Move deposited ETH lots into the validator bucket and record staked principal."""
        validator_bucket = validator_eth2_bucket(event.validator_index)
        if (
            source in self._host.blocked_buckets or
            validator_bucket in self._host.blocked_buckets
        ):
            return

        self._validator_principal[event.validator_index] = (
            self._validator_principal.get(event.validator_index, ZERO) + event.amount
        )
        self._host.transfer(
            event=event,
            source=source,
            destination=validator_bucket,
            is_stale=is_stale,
            row_destination=destination,
        )

    def _apply_principal_withdrawal(
            self,
            event: EthWithdrawalEvent,
            validator_bucket: Bucket,
            wallet_bucket: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
            principal_eth: FVal,
            loss_eth: FVal,
            excess_eth: FVal,
            drain_validator: bool,
    ) -> None:
        """Transfer validator principal lots to the wallet and realize any exit loss or reward."""
        assert event.identifier is not None
        eth2_row_bucket = Bucket(
            location=LOCATION_ETHEREUM,
            location_label=event.location_label,
            protocol=CPT_ETH2,
            asset=A_ETH.identifier,
        )
        loss_result = (
            self._host.lots.spend(
                bucket=validator_bucket,
                asset=event.asset,
                amount=loss_eth,
                timestamp=timestamp,
                event=event,
            )
            if loss_eth > ZERO else None
        )
        move_amount = event.amount if loss_eth > ZERO else principal_eth
        if move_amount > ZERO:
            moved, lot_ids, transferred_basis = self._host.move_lots(
                event=event,
                source=validator_bucket,
                destination=wallet_bucket,
                move_amount=move_amount,
                dest_amount=move_amount,
                received=event,
                is_stale=is_stale,
                issue_bucket=eth2_row_bucket,
            )
        else:
            moved, lot_ids, transferred_basis = [], [], ZERO

        drained = (
            self._host.lots.spend(
                bucket=validator_bucket,
                asset=event.asset,
                amount=leftover,
                timestamp=timestamp,
                event=event,
            )
            if (
                drain_validator and
                (leftover := self._host.lots.amount_remaining(validator_bucket)) > ZERO
            )
            else None
        )

        excess_basis = ZERO
        excess_basis_source = BasisSource.TRANSFER_IN
        if excess_eth > ZERO:
            # A mixed principal+excess exit writes a blended basis_per_unit on its single RECEIVE
            # row, so incremental replay must not feed that blended value back as the excess lot's
            # basis; only pure-excess exits store an unblended basis_per_unit.
            excess_basis, excess_basis_source = self._host.resolve_receive_basis(
                event=event,
                timestamp=timestamp,
                is_stale=is_stale,
                use_stored_basis=move_amount == ZERO,
            )
            lot_id = str(event.identifier)
            self._host.lots.obtain(
                bucket=wallet_bucket,
                lot_id=lot_id,
                amount=excess_eth,
                basis_per_unit=excess_basis,
                timestamp=timestamp,
            )
            if lot_id not in lot_ids:
                lot_ids.append(lot_id)

        if not is_stale:
            return

        if loss_result is not None or move_amount > ZERO or drained is not None:
            all_consumed = [
                *(loss_result.consumed if loss_result is not None else ()),
                *moved,
                *(drained.consumed if drained is not None else ()),
            ]
            basis_removed = (
                (loss_result.basis_removed if loss_result is not None else ZERO) +
                transferred_basis +
                (drained.basis_removed if drained is not None else ZERO)
            )
            if loss_result is not None:
                if loss_result.uncovered_amount > ZERO:
                    self._host.record_missing_cost_basis(
                        event=event,
                        bucket=eth2_row_bucket,
                        requested_amount=loss_eth,
                        covered_amount=loss_eth - loss_result.uncovered_amount,
                    )
                taxable_loss = self._host.settings.eth_staking_taxable_after_withdrawal_enabled
                rate = (
                    self._host.get_price(asset=event.asset, timestamp=timestamp)
                    if taxable_loss else None
                )
                if taxable_loss and rate is None:
                    self._host.record_missing_price(
                        event=event,
                        bucket=eth2_row_bucket,
                        direction='spend',
                        amount=loss_eth,
                    )
                proceeds, spend_realized_pnl, spend_taxfree_pnl = self._host.compute_spend_pnl(
                    amount=loss_eth,
                    rate=rate,
                    counts_cost_basis=taxable_loss,
                    count_entire_amount_spend=taxable_loss,
                    result=loss_result,
                )
            else:
                taxable_loss = False
                proceeds, spend_realized_pnl, spend_taxfree_pnl = None, ZERO, None

            self._host.add_row(
                event=event,
                bucket=eth2_row_bucket,
                direction=CostBasisDirection.SPEND,
                lots_consumed=[entry.serialize() for entry in all_consumed],
                proceeds=proceeds,
                realized_pnl=spend_realized_pnl,
                taxfree_pnl=spend_taxfree_pnl,
                basis_removed=basis_removed,
                post_spend_basis_remaining=self._host.lots.basis_remaining(validator_bucket),
                is_taxable=taxable_loss,
            )

        if event.amount > ZERO:
            if excess_eth > ZERO:
                is_taxable = self._host.settings.eth_staking_taxable_after_withdrawal_enabled
                if excess_basis_source == BasisSource.ZERO_COST:
                    self._host.record_missing_price(
                        event=event,
                        bucket=wallet_bucket,
                        direction='receive',
                        amount=excess_eth,
                    )
                recv_realized_pnl, recv_taxfree_pnl = self._host.compute_receive_pnl(
                    amount=excess_eth,
                    basis=excess_basis,
                    basis_source=excess_basis_source,
                    is_taxable=is_taxable,
                )
                recv_basis_per_unit = (
                    excess_basis if move_amount == ZERO
                    else (transferred_basis + excess_eth * excess_basis) / event.amount
                )
                recv_basis_source = excess_basis_source
            else:
                is_taxable = False
                recv_realized_pnl = recv_taxfree_pnl = None
                recv_basis_per_unit = transferred_basis / event.amount
                recv_basis_source = BasisSource.TRANSFER_IN

            self._host.add_row(
                event=event,
                bucket=wallet_bucket,
                direction=CostBasisDirection.RECEIVE,
                lot_created_id=','.join(lot_ids),
                basis_per_unit=recv_basis_per_unit,
                basis_source=recv_basis_source,
                realized_pnl=recv_realized_pnl,
                taxfree_pnl=recv_taxfree_pnl,
                is_taxable=is_taxable,
            )

    def apply_withdrawal(
            self,
            event: EthWithdrawalEvent,
            wallet_bucket: Bucket,
            timestamp: Timestamp,
            is_stale: bool,
            rule: BaseEventSettings | None,
    ) -> None:
        """Apply an ETH2 withdrawal or exit according to validator type and principal history."""
        validator_type: ValidatorType | None = (
            ValidatorType.DISTRIBUTING if self.validator_types is None
            else self.validator_types.get(event.validator_index)
        )
        if validator_type is None:
            self._host.receive(event, wallet_bucket, timestamp, is_stale, rule, is_taxable=False)
            return

        is_exit = event.is_exit_or_blocknumber != 0
        v_index = event.validator_index
        validator_bucket = validator_eth2_bucket(v_index)
        if validator_bucket in self._host.blocked_buckets:
            return

        taxable_after_withdrawal = self._host.settings.eth_staking_taxable_after_withdrawal_enabled
        if validator_type != ValidatorType.ACCUMULATING:
            is_consolidated_source = v_index in self._consolidated_sources
            if is_exit:
                self._validator_principal.pop(v_index, None)
                self._consolidated_sources.discard(v_index)
                self._withdrawal_requests.pop(v_index, None)
            if (
                (not is_exit and event.amount < MIN_EFFECTIVE_BALANCE) or
                (is_exit and is_consolidated_source)
            ):
                self._host.receive(
                    event,
                    wallet_bucket,
                    timestamp,
                    is_stale,
                    rule,
                    is_taxable=taxable_after_withdrawal,
                )
                return

            effective_principal = MIN_EFFECTIVE_BALANCE
            drain_validator = is_exit
        elif not is_exit:
            if not self._consume_withdrawal_request(v_index, event.timestamp, event.amount):
                self._host.receive(
                    event,
                    wallet_bucket,
                    timestamp,
                    is_stale,
                    rule,
                    is_taxable=taxable_after_withdrawal,
                )
                return

            if v_index in self._validator_principal:
                self._validator_principal[v_index] = max(
                    ZERO,
                    self._validator_principal[v_index] - event.amount,
                )
            effective_principal = event.amount
            drain_validator = False
        else:
            has_principal_history = v_index in self._validator_principal
            principal_eth = self._validator_principal.pop(v_index, ZERO)
            self._consolidated_sources.discard(v_index)
            self._withdrawal_requests.pop(v_index, None)
            effective_principal = (
                principal_eth if has_principal_history
                else min(event.amount, MAX_EFFECTIVE_BALANCE)
            )
            drain_validator = True

        net_pnl_eth = event.amount - effective_principal
        self._apply_principal_withdrawal(
            event=event,
            validator_bucket=validator_bucket,
            wallet_bucket=wallet_bucket,
            timestamp=timestamp,
            is_stale=is_stale,
            principal_eth=effective_principal,
            loss_eth=max(ZERO, -net_pnl_eth),
            excess_eth=max(ZERO, net_pnl_eth),
            drain_validator=drain_validator,
        )
