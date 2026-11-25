"""Cost basis lots tracked per bucket, on top of the existing cost basis method heaps.

The `CostBasisCalculator` of base.py keeps one pool of acquisitions per asset, which is what
the PnL report needs. The materialization of cost basis on history events keeps one pool per
bucket instead, so that the basis follows the asset as it moves between the user's accounts.
The order in which lots are consumed is still decided by the same FIFO/LIFO/HIFO/ACB heaps.
"""
from collections.abc import Hashable
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.accounting.cost_basis.base import (
    AssetAcquisitionEvent,
    AverageCostBasisMethod,
    BaseCostBasisMethod,
    CostBasisEvents,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.settings import DBSettings
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


class BasisSource(StrEnum):
    """Where the basis of a lot created by a receive comes from."""
    # The amount paid is carried by the events themselves, e.g. an acquisition paid in fiat.
    EVENT_AMOUNT = auto()
    # The basis is the market price of the asset, queried from the historical price oracles.
    PRICE_ORACLE = auto()
    # The lots were carried over from another bucket of the user, keeping their basis.
    TRANSFER_IN = auto()
    # The asset was acquired at no cost. It is also what is used when no price can be found.
    ZERO_COST = auto()
    # The user marked the event as not counting as an acquisition. Nothing sets this yet.
    FREE_ACQUISITION = auto()


class CostBasisDirection(StrEnum):
    RECEIVE = auto()
    SPEND = auto()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Lot(AssetAcquisitionEvent):
    """An acquisition with an identity that survives a move to another bucket.

    `index` is the position of the acquisition among all lots of the user. A lot moved to
    another bucket keeps it, so that FIFO and LIFO consume it by when it was acquired and not
    by when it arrived.
    """
    lot_id: str

    def serialize_state(self) -> list[str | int]:
        return [
            self.lot_id,
            self.timestamp,
            self.index,
            str(self.amount),
            str(self.remaining_amount),
            str(self.rate),
        ]

    @classmethod
    def from_state(cls, state: list[str | int]) -> Lot:
        lot_id, timestamp, index, amount, remaining_amount, rate = state
        lot = cls(
            amount=FVal(amount),
            timestamp=Timestamp(int(timestamp)),
            rate=Price(FVal(rate)),
            index=int(index),
            lot_id=str(lot_id),
        )
        lot.remaining_amount = FVal(remaining_amount)
        return lot


class ConsumedLot(NamedTuple):
    lot: Lot
    amount: FVal  # amount taken out of the lot
    basis_per_unit: FVal  # the average basis of the bucket for ACB, otherwise the rate of the lot
    taxable: bool  # False if the lot was held for longer than the tax free period

    def serialize(self) -> dict[str, str | int | bool]:
        return {
            'lot_id': self.lot.lot_id,
            'acquired_at': self.lot.timestamp,
            'amount_consumed': str(self.amount),
            'basis_per_unit': str(self.basis_per_unit),
            'taxable': self.taxable,
        }


class SpendResult(NamedTuple):
    consumed: list[ConsumedLot]
    taxable_amount: FVal  # includes any amount for which no lot was found
    taxable_basis: FVal
    taxfree_basis: FVal

    @property
    def basis_removed(self) -> FVal:
        return self.taxable_basis + self.taxfree_basis


class BucketLots[K: Hashable]:
    """The lots of each bucket, consumed in the order of the given cost basis method."""

    def __init__(self, settings: DBSettings) -> None:
        self.settings = settings
        self._buckets: dict[K, BaseCostBasisMethod] = {}
        self._next_order = 0

    def _get(self, bucket: K) -> BaseCostBasisMethod:
        if (manager := self._buckets.get(bucket)) is None:
            manager = CostBasisEvents(self.settings.cost_basis_method).acquisitions_manager
            self._buckets[bucket] = manager

        return manager

    def serialize_state(self) -> tuple[int, list[tuple[K, dict[str, Any]]]]:
        """The lots of every bucket, to be restored by `restore_state`.

        The lots of a bucket are listed in the order of its heap, which pushing them back in
        reproduces exactly, including the order between lots that the method ranks the same.
        """
        return self._next_order, [(bucket, {
            'lots': [
                lot.serialize_state()  # type: ignore[attr-defined]  # only lots are added to the buckets
                for lot in manager.get_acquisitions()
            ],
            'acb': (
                [str(manager.current_amount), str(manager.current_total_acb)]
                if isinstance(manager, AverageCostBasisMethod) else None
            ),
        }) for bucket, manager in self._buckets.items()]

    def restore_state(self, next_order: int, buckets: list[tuple[K, dict[str, Any]]]) -> None:
        """Replace the lots with ones serialized by `serialize_state`."""
        self._buckets, self._next_order = {}, next_order
        for bucket, state in buckets:
            manager = self._get(bucket)
            for lot_state in state['lots']:
                lot = Lot.from_state(lot_state)
                manager.add_in_event(lot, order=lot.index)
            if isinstance(manager, AverageCostBasisMethod):
                manager.current_amount = FVal(state['acb'][0])
                manager.current_total_acb = FVal(state['acb'][1])

    @staticmethod
    def _average_basis(manager: BaseCostBasisMethod) -> FVal | None:
        """The basis of each unit in an ACB bucket. None for the other methods."""
        if not isinstance(manager, AverageCostBasisMethod) or manager.current_amount == ZERO:
            return None

        return manager.current_total_acb / manager.current_amount

    def obtain(
            self,
            bucket: K,
            lot_id: str,
            amount: FVal,
            basis_per_unit: FVal,
            timestamp: Timestamp,
    ) -> None:
        """Add a new lot to the bucket, acquired after every lot added before it."""
        lot = Lot(
            amount=amount,
            timestamp=timestamp,
            rate=Price(basis_per_unit),
            index=self._next_order,
            lot_id=lot_id,
        )
        self._next_order += 1
        self._get(bucket).add_in_event(lot, order=lot.index)

    def spend(
            self,
            bucket: K,
            asset: Asset,
            amount: FVal,
            timestamp: Timestamp,
            event: HistoryBaseEntry | None = None,
    ) -> SpendResult:
        """Consume lots of the bucket for the given amount.

        Any part of the amount that no lot covers has no basis and counts as taxable.
        """
        average_basis = self._average_basis(manager := self._get(bucket))
        info = manager.calculate_spend_cost_basis(
            spending_amount=amount,
            spending_asset=asset,
            timestamp=timestamp,
            missing_acquisitions=[],
            used_acquisitions=[],
            settings=self.settings,
            timestamp_to_date=str,
            event=event,
        )
        return SpendResult(
            consumed=[ConsumedLot(
                lot=matched.event,  # type: ignore[arg-type]  # only lots are added to the buckets
                amount=matched.amount,
                basis_per_unit=matched.event.rate if average_basis is None else average_basis,
                taxable=matched.taxable,
            ) for matched in info.matched_acquisitions if matched.amount > ZERO],
            taxable_amount=info.taxable_amount,
            taxable_basis=info.taxable_bought_cost,
            taxfree_basis=info.taxfree_bought_cost,
        )

    def transfer(
            self,
            source: K,
            destination: K,
            asset: Asset,
            amount: FVal,
            destination_amount: FVal | None = None,
            event: HistoryBaseEntry | None = None,
    ) -> list[ConsumedLot]:
        """Move lots for the given amount from one bucket to another.

        The moved lots keep their identity, acquisition time and basis, so nothing is realized.
        A lot that is only partly moved exists in both buckets afterwards. For ACB what moves
        is the average basis of the source bucket. Returns what was moved, in units of the
        source, which is less than the amount if the source bucket does not hold enough.

        `destination_amount` is what the amount turns into when the two buckets hold different
        assets, e.g. a token and its wrapped version. The lots are scaled to it, so that their
        total basis stays the same.
        """
        ratio = ONE if destination_amount is None else destination_amount / amount
        average_basis = self._average_basis(manager := self._get(source))
        remaining, moved = amount, []
        for lot in manager.processing_iterator():
            if remaining <= ZERO:
                break

            moved.append(ConsumedLot(
                lot=lot,  # type: ignore[arg-type]  # only lots are added to the buckets
                amount=(used := min(remaining, lot.remaining_amount)),
                basis_per_unit=lot.rate if average_basis is None else average_basis,
                taxable=False,
            ))
            remaining -= used
            manager.consume_result(used_amount=used, asset=asset, event=event)

        destination_manager = self._get(destination)
        for entry in moved:
            destination_manager.add_in_event(Lot(
                amount=entry.amount * ratio,
                timestamp=entry.lot.timestamp,
                rate=Price(entry.basis_per_unit / ratio),
                index=entry.lot.index,
                lot_id=entry.lot.lot_id,
            ), order=entry.lot.index)

        return moved

    def basis_remaining(self, bucket: K) -> FVal:
        """The total basis of what the bucket still holds."""
        if isinstance(manager := self._get(bucket), AverageCostBasisMethod):
            return manager.current_total_acb

        return sum(
            (lot.remaining_amount * lot.rate for lot in manager.get_acquisitions()),
            start=ZERO,
        )

    def amount_remaining(self, bucket: K) -> FVal:
        """The total amount of what the bucket still holds."""
        if isinstance(manager := self._get(bucket), AverageCostBasisMethod):
            return manager.current_amount

        return sum(
            (lot.remaining_amount for lot in manager.get_acquisitions()),
            start=ZERO,
        )
