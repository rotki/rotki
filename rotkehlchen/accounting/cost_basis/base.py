import heapq
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, Optional, overload

from rotkehlchen.accounting.types import MissingAcquisition, MissingPrice
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.misc import AccountingError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import CostBasisMethod, Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetAcquisitionEvent:
    amount: FVal
    remaining_amount: FVal = field(init=False)  # Same as amount but reduced during processing
    timestamp: Timestamp
    rate: Price
    index: int

    def __post_init__(self) -> None:
        self.remaining_amount = self.amount

    def __str__(self) -> str:
        return (
            f'AssetAcquisitionEvent @{self.timestamp}. amount: {self.amount} rate: {self.rate}'
        )

    @classmethod
    def from_history_event(cls: type['AssetAcquisitionEvent'], event: 'HistoryEvent', price: Price, index: int) -> 'AssetAcquisitionEvent':  # noqa: E501
        return cls(
            amount=event.amount,
            timestamp=Timestamp(event.timestamp // 1000),  # Convert from milliseconds to seconds
            rate=price,
            index=index,
        )

    @classmethod
    def deserialize(cls: type['AssetAcquisitionEvent'], data: dict[str, Any]) -> 'AssetAcquisitionEvent':  # noqa: E501
        """May raise DeserializationError"""
        try:
            return cls(
                amount=data['full_amount'],
                timestamp=data['timestamp'],
                rate=data['rate'],
                index=data['index'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize(self) -> dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'full_amount': str(self.amount),
            'rate': str(self.rate),
            'index': self.index,
        }

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, AssetAcquisitionEvent):
            raise NotImplementedError

        return self.timestamp > other.timestamp

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, AssetAcquisitionEvent):
            raise NotImplementedError

        return self.timestamp < other.timestamp


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetSpendEvent:
    timestamp: Timestamp
    location: Location
    amount: FVal  # Amount of the asset we sell
    rate: FVal  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset

    def __str__(self) -> str:
        return (
            f'AssetSpendEvent in {self.location!s} @ {self.timestamp}.'
            f'amount: {self.amount} rate: {self.rate}'
        )


class AssetAcquisitionHeapElement(NamedTuple):
    """
    https://docs.python.org/3/library/heapq.html#basic-examples

    This represents a heap element for the asset acquisition heap.
    It is a tuple to also carry a priority which is used by the heap algorithm to
    preserve the heap invariant.

    Note:`heapq` uses a min heap implementation i.e. the smallest item comes out first.

    For FIFO, a counter is used as the priority so the first acquisition comes out first.
    For LIFO, a counter is used but negated, so the acquisition added last comes first.
    For HIFO, the amount of the acquisition is used although negated so the
    acquisition with the highest amount comes first.
    """
    priority: FVal  # This is only used by heapq algorithm and not accessed from our code
    acquisition_event: AssetAcquisitionEvent

    def __str__(self) -> str:
        return str(self.acquisition_event)


class BaseCostBasisMethod(ABC):
    """The base class in which every other cost basis method inherits from."""
    def __init__(self) -> None:
        self._acquisitions_heap: list[AssetAcquisitionHeapElement] = []

    @abstractmethod
    def add_in_event(self, acquisition: AssetAcquisitionEvent) -> None:
        """
        The core method. Should be implemented by subclasses.
        This method takes a new acquisition and decides where to insert it
        and thus determines the PnL order.
        """

    def processing_iterator(self) -> Iterator[AssetAcquisitionEvent]:
        """
        Iteration method over acquisition events.
        We can't return here Tuple of AssetAcquisitionEvents as we need to return
        the first event each time but _acquisitions may be not modified between iterations.
        """
        while len(self._acquisitions_heap) > 0:
            yield self._acquisitions_heap[0].acquisition_event

    def get_acquisitions(self) -> tuple[AssetAcquisitionEvent, ...]:
        """Returns read-only _acquisitions"""
        return tuple(entry.acquisition_event for entry in self._acquisitions_heap)

    def consume_result(self, used_amount: FVal, asset: Asset) -> None:
        """
        This function should be used to consume results of the
        currently processed event (received from __next__)
        The current event's remaining_amount will be decreased by used_amount
        If event's remaining_amount will become ZERO, the event will be deleted
        May raise:
        - IndexError if the method was called when acquisitions were empty
        """
        # this is a temporary assertion to test that new accounting tools work properly.
        # Written on 06.06.2022 and can be removed after a couple of months if everything goes well
        assert ZERO <= used_amount <= self._acquisitions_heap[0].acquisition_event.remaining_amount, f'Used amount must be in the interval [0, {self._acquisitions_heap[0].acquisition_event.remaining_amount}] but it was {used_amount} for {asset}'  # noqa: E501

        self._acquisitions_heap[0].acquisition_event.remaining_amount -= used_amount
        if self._acquisitions_heap[0].acquisition_event.remaining_amount == ZERO:
            heapq.heappop(self._acquisitions_heap)

    def calculate_spend_cost_basis(
            self,
            spending_amount: FVal,
            spending_asset: Asset,
            timestamp: Timestamp,
            missing_acquisitions: list[MissingAcquisition],
            used_acquisitions: list[AssetAcquisitionEvent],
            settings: DBSettings,
            timestamp_to_date: Callable[[Timestamp], str],
            average_cost_basis: FVal | None = None,
            originating_event_id: int | None = None,
    ) -> 'CostBasisInfo':
        """
        When spending `spending_amount` of `spending_asset` at `timestamp` this function
        calculates using the method defined by class the corresponding buy(s) from which to do profit calculation.
        It also applies the "free after given time period" rule
        which applies for some jurisdictions such as 1 year for Germany.

        If `average_cost_basis` is provided, it is used as the acquisition cost.

        Returns the information in a CostBasisInfo object if enough acquisitions have
        been found.
        """  # noqa: E501
        remaining_sold_amount = spending_amount
        taxfree_bought_cost = taxable_bought_cost = taxable_amount = taxfree_amount = ZERO
        matched_acquisitions = []

        for acquisition_event in self.processing_iterator():
            if settings.taxfree_after_period is None:
                at_taxfree_period = False
            else:
                at_taxfree_period = acquisition_event.timestamp + settings.taxfree_after_period < timestamp  # noqa: E501

            if remaining_sold_amount < acquisition_event.remaining_amount:
                acquisition_rate = acquisition_event.rate if average_cost_basis is None else average_cost_basis  # noqa: E501
                acquisition_cost = acquisition_rate * remaining_sold_amount

                taxable = True
                if at_taxfree_period:
                    taxfree_amount += remaining_sold_amount
                    taxfree_bought_cost += acquisition_cost
                    taxable = False
                else:
                    taxable_amount += remaining_sold_amount
                    taxable_bought_cost += acquisition_cost

                log.debug(
                    'Spend uses up part of historical acquisition',
                    tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                    used_amount=remaining_sold_amount,
                    from_amount=acquisition_event.amount,
                    asset=spending_asset,
                    acquisition_rate=acquisition_event.rate,
                    profit_currency=settings.main_currency,
                    time=timestamp_to_date(acquisition_event.timestamp),
                )
                matched_acquisitions.append(MatchedAcquisition(
                    amount=remaining_sold_amount,
                    event=acquisition_event,
                    taxable=taxable,
                ))
                self.consume_result(used_amount=remaining_sold_amount, asset=spending_asset)
                remaining_sold_amount = ZERO
                # stop iterating since we found all acquisitions to satisfy this spend
                break

            remaining_sold_amount -= acquisition_event.remaining_amount
            acquisition_rate = acquisition_event.rate if average_cost_basis is None else average_cost_basis  # noqa: E501
            acquisition_cost = acquisition_rate * acquisition_event.remaining_amount
            taxable = True
            if at_taxfree_period:
                taxfree_amount += acquisition_event.remaining_amount
                taxfree_bought_cost += acquisition_cost
                taxable = False
            else:
                taxable_amount += acquisition_event.remaining_amount
                taxable_bought_cost += acquisition_cost

            log.debug(
                'Spend uses up entire historical acquisition',
                tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                bought_amount=acquisition_event.remaining_amount,
                asset=spending_asset,
                acquisition_rate=acquisition_event.rate,
                profit_currency=settings.main_currency,
                time=timestamp_to_date(acquisition_event.timestamp),
            )
            matched_acquisitions.append(MatchedAcquisition(
                amount=acquisition_event.remaining_amount,
                event=acquisition_event,
                taxable=taxable,
            ))
            used_acquisitions.append(acquisition_event)
            self.consume_result(
                used_amount=acquisition_event.remaining_amount,
                asset=spending_asset,
            )
            # and since this event is going to be removed, reduce its remaining to zero
            acquisition_event.remaining_amount = ZERO

        is_complete = True
        if remaining_sold_amount != ZERO:
            # if we still have sold amount but no acquisitions to satisfy it then we only
            # found acquisitions to partially satisfy the sell
            adjusted_amount = spending_amount - taxfree_amount
            missing_acquisitions.append(
                MissingAcquisition(
                    originating_event_id=originating_event_id,
                    asset=spending_asset,
                    time=timestamp,
                    found_amount=taxable_amount + taxfree_amount,
                    missing_amount=remaining_sold_amount,
                ),
            )
            taxable_amount = adjusted_amount
            is_complete = False

        return CostBasisInfo(
            taxable_amount=taxable_amount,
            taxable_bought_cost=taxable_bought_cost,
            taxfree_bought_cost=taxfree_bought_cost,
            matched_acquisitions=matched_acquisitions,
            is_complete=is_complete,
        )

    def __len__(self) -> int:
        return len(self._acquisitions_heap)


class FIFOCostBasisMethod(BaseCostBasisMethod):
    """
    Accounting in FIFO (first-in-first-out) method.
    https://www.investopedia.com/terms/f/fifo.asp
    """
    def __init__(self) -> None:
        super().__init__()
        self._count = ZERO

    def add_in_event(self, acquisition: AssetAcquisitionEvent) -> None:
        """Adds an acquisition to the `_acquisitions_heap` using a counter to achieve the FIFO order."""  # noqa: E501
        heapq.heappush(self._acquisitions_heap, AssetAcquisitionHeapElement(self._count, acquisition))  # noqa: E501
        self._count += 1


class LIFOCostBasisMethod(BaseCostBasisMethod):
    """
    Accounting in LIFO (last-in-first-out) method.
    https://www.investopedia.com/terms/l/lifo.asp
    """
    def __init__(self) -> None:
        super().__init__()
        self._count = ZERO

    def add_in_event(self, acquisition: AssetAcquisitionEvent) -> None:
        """Adds an acquisition to the `_acquisitions_heap` using a negated counter to achieve the LIFO order."""  # noqa: E501
        heapq.heappush(self._acquisitions_heap, AssetAcquisitionHeapElement(-self._count, acquisition))  # noqa: E501
        self._count += 1


class HIFOCostBasisMethod(BaseCostBasisMethod):
    """
    Accounting in HIFO (highest-in-first-out) method.
    https://www.investopedia.com/terms/h/hifo.asp
    """
    def add_in_event(self, acquisition: AssetAcquisitionEvent) -> None:
        """
        Adds an acquisition to the `_acquisitions_heap` using the negated rate
        of the acquisition to achieve the HIFO order.
        """
        heapq.heappush(self._acquisitions_heap, AssetAcquisitionHeapElement(-acquisition.rate, acquisition))  # noqa: E501


class AverageCostBasisMethod(BaseCostBasisMethod):
    """
    Accounting in Average Cost Basis(ACB) method.

    This accounting method is used for several jurisdictions. The examples are:
        1. For Canada: https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4037/t4037-22e.pdf, page 23
        2. For UK: https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/877369/HS284_Example_3_2020.pdf

    Also an overall explanation of the method can be found here:
        https://www.investopedia.com/terms/a/averagecostbasismethod.asp

    For more details and explanations go here:
        https://github.com/rotki/rotki/issues/5561#issuecomment-1423338938
    """  # noqa: E501
    def __init__(self) -> None:
        super().__init__()
        self._count = ZERO
        # keeps track of the amount of the asset remaining after every acquisition or spend
        self.current_amount = ZERO
        # the current total cost basis of the asset
        self.current_total_acb = ZERO

    def add_in_event(self, acquisition: AssetAcquisitionEvent) -> None:
        """
        Adds an acquisition to the `_acquisitions_heap` in order of time seen.

        It also calculates the average cost basis of that acquisition with respect to the
        previous average cost basis.

        The formula used to calculate the average cost basis of an acquisition is:
        [Previous Total ACB] + [Cost of New Shares] + [Transaction Costs]
        """
        heapq.heappush(
            self._acquisitions_heap,
            AssetAcquisitionHeapElement(self._count, acquisition),
        )
        self.current_total_acb += acquisition.amount * acquisition.rate
        self.current_amount += acquisition.amount
        self._count += 1

    def consume_result(self, used_amount: FVal, asset: Asset) -> None:
        """
        Same as its parent function but also deducts `used_amount` from `current_amount`.
        `current_amount` is guaranteed to be greater than zero since `consume_result` is
        supposed to be called under `processing_iterator`.
        """
        if self.current_amount == ZERO:
            # this shouldn't happen but a user reported it in
            # https://github.com/rotki/rotki/issues/7273. We couldn't find the reason for it so we
            # decided to protect against it by raising an error shown in the frontend
            log.error(f'Division by zero error when processing report using ACB. {self._acquisitions_heap}')  # noqa: E501
            raise AccountingError(
                f'Remaining amount error during ACB calculation for {asset}. Contact support and '
                'provide the log file for more information',
            )

        self.current_total_acb *= (self.current_amount - used_amount) / self.current_amount
        self.current_amount -= used_amount
        super().consume_result(used_amount=used_amount, asset=asset)

    def calculate_spend_cost_basis(
            self,
            spending_amount: FVal,
            spending_asset: Asset,
            timestamp: Timestamp,
            missing_acquisitions: list[MissingAcquisition],
            used_acquisitions: list[AssetAcquisitionEvent],
            settings: DBSettings,
            timestamp_to_date: Callable[[Timestamp], str],
            average_cost_basis: FVal | None = None,  # pylint: disable=unused-argument
            originating_event_id: int | None = None,
    ) -> 'CostBasisInfo':
        """Calculates the cost basis of the spend using the average cost basis method."""
        if self.current_amount == ZERO:
            missing_acquisitions.append(
                MissingAcquisition(
                    originating_event_id=originating_event_id,
                    asset=spending_asset,
                    time=timestamp,
                    found_amount=self.current_amount,
                    missing_amount=spending_amount,
                ),
            )

            return CostBasisInfo(
                taxable_amount=spending_amount,
                taxable_bought_cost=ZERO,
                taxfree_bought_cost=ZERO,
                matched_acquisitions=[],
                is_complete=False,
            )

        return super().calculate_spend_cost_basis(
            spending_amount=spending_amount,
            spending_asset=spending_asset,
            timestamp=timestamp,
            missing_acquisitions=missing_acquisitions,
            used_acquisitions=used_acquisitions,
            settings=settings,
            timestamp_to_date=timestamp_to_date,
            # Important note: calculation of the average cost basis of the current event has to
            # happen before calling `consume_result`. For correct results `current_total_acb` and
            # `current_amount` have to be used before applying the effect of the event that is
            # being processed.
            average_cost_basis=self.current_total_acb / self.current_amount,
            originating_event_id=originating_event_id,
        )


class CostBasisEvents:
    def __init__(self, cost_basis_method: CostBasisMethod) -> None:
        """This class contains data about acquisitions and spends."""
        if cost_basis_method == CostBasisMethod.FIFO:
            self.acquisitions_manager: BaseCostBasisMethod = FIFOCostBasisMethod()
        elif cost_basis_method == CostBasisMethod.LIFO:
            self.acquisitions_manager = LIFOCostBasisMethod()
        elif cost_basis_method == CostBasisMethod.HIFO:
            self.acquisitions_manager = HIFOCostBasisMethod()
        elif cost_basis_method == CostBasisMethod.ACB:
            self.acquisitions_manager = AverageCostBasisMethod()
        self.spends: list[AssetSpendEvent] = []
        self.used_acquisitions: list[AssetAcquisitionEvent] = []


class MatchedAcquisition(NamedTuple):
    amount: FVal  # the amount used from the acquisition event
    event: AssetAcquisitionEvent  # the acquisition event
    taxable: bool  # whether it counts for taxable or non-taxable cost basis

    def serialize(self) -> dict[str, Any]:
        """Turn to a dict to be serialized into the DB"""
        return {
            'amount': str(self.amount),
            'event': self.event.serialize(),
            'taxable': self.taxable,
        }

    @classmethod
    def deserialize(cls: type['MatchedAcquisition'], data: dict[str, Any]) -> 'MatchedAcquisition':
        """May raise DeserializationError"""
        try:
            event = AssetAcquisitionEvent.deserialize(data['event'])
            amount = deserialize_fval(
                value=data['amount'],
                name='amount',
                location='cost_basis',
            )
            taxable = data['taxable']
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

        return MatchedAcquisition(amount=amount, event=event, taxable=taxable)

    def to_string(self, converter: Callable[[Timestamp], str]) -> str:
        """User readable string version of the acquisition"""
        return (
            f'{self.amount} / {self.event.amount}  acquired '
            f'at {converter(self.event.timestamp)} for price: {self.event.rate}'
        )


class CostBasisInfo(NamedTuple):
    """Information on the cost basis of a spend event

        - `taxable_amount`: The amount out of `spending_amount` that is taxable,
                            calculated from the free after given time period rule.
        - `taxable_bought_cost`: How much it cost in `profit_currency` to buy
                                 the `taxable_amount`
        - `taxfree_bought_cost`: How much it cost in `profit_currency` to buy
                                 the taxfree_amount (selling_amount - taxable_amount)
        - `matched_acquisitions`: The list of acquisitions and amount per acquisition
                                   used for this spend
        - `is_complete: Boolean denoting whether enough information was recovered for the spend
    """
    taxable_amount: FVal
    taxable_bought_cost: FVal
    taxfree_bought_cost: FVal
    matched_acquisitions: list[MatchedAcquisition]
    is_complete: bool

    def serialize(self) -> dict[str, Any]:
        """Turn to a dict to be exported into the DB"""
        return {
            'is_complete': self.is_complete,
            'matched_acquisitions': [x.serialize() for x in self.matched_acquisitions],
        }

    @classmethod
    def deserialize(cls: type['CostBasisInfo'], data: dict[str, Any]) -> Optional['CostBasisInfo']:
        """Creates a CostBasisInfo object from a json dict made from serialize()

        May raise:
        - DeserializationError
        """
        try:
            is_complete = data['is_complete']
            matched_acquisitions = [MatchedAcquisition.deserialize(x) for x in data['matched_acquisitions']]  # noqa: E501
        except KeyError as e:
            raise DeserializationError(f'Could not decode CostBasisInfo json from the DB due to missing key {e!s}') from e  # noqa: E501

        return CostBasisInfo(  # the 0 are not serialized and not used at recall so is okay to skip
            taxable_amount=ZERO,
            taxable_bought_cost=ZERO,
            taxfree_bought_cost=ZERO,
            is_complete=is_complete,
            matched_acquisitions=matched_acquisitions,
        )

    def to_string(self, converter: Callable[[Timestamp], str]) -> tuple[str, str]:
        """
        Turn to 2 strings to be shown in exported files such as CSV for taxable and free cost basis
        """
        taxable = ''
        free = ''
        if not self.is_complete:
            taxable += 'Incomplete cost basis information for spend.'
            free += 'Incomplete cost basis information for spend.'

        if len(self.matched_acquisitions) == 0:
            return taxable, free

        for entry in self.matched_acquisitions:
            stringified = entry.to_string(converter)
            if entry.taxable:
                if taxable != '':
                    taxable += ' '
                taxable += stringified
            else:
                if free != '':
                    free += ' '
                free += stringified

        return taxable, free


class CostBasisCalculator(CustomizableDateMixin):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(database=database)
        self.msg_aggregator = msg_aggregator
        self.reset(self.settings)

    def reset(self, settings: DBSettings) -> None:
        self.settings = settings
        self.profit_currency = settings.main_currency
        self._events: defaultdict[Asset, CostBasisEvents] = defaultdict(lambda: CostBasisEvents(settings.cost_basis_method))  # noqa: E501
        self.missing_acquisitions: list[MissingAcquisition] = []
        self.missing_prices: set[MissingPrice] = set()

    def get_events(self, asset: Asset) -> CostBasisEvents:
        """Custom getter for events so that we have common cost basis for some assets"""
        if asset == A_WETH:
            asset = A_ETH

        return self._events[asset]

    def reduce_asset_amount(
            self,
            originating_event_id: int | None,
            asset: Asset,
            amount: FVal,
            timestamp: Timestamp,
    ) -> bool:
        """Searches all acquisition events for asset and reduces them by amount.

        Returns True if enough acquisition events to reduce the asset by amount were
        found and False otherwise. Adds missing acquisition only if asset is not fiat.

        This function does the same as calculate_spend_cost_basis as far as consuming
        acquisitions is concerned but does not calculate bought cost.
        """
        asset_events = self.get_events(asset)
        if len(asset_events.acquisitions_manager) == 0:
            return False

        remaining_amount = amount
        for acquisition_event in asset_events.acquisitions_manager.processing_iterator():
            if remaining_amount < acquisition_event.remaining_amount:
                asset_events.acquisitions_manager.consume_result(
                    used_amount=remaining_amount,
                    asset=asset,
                )
                remaining_amount = ZERO
                # stop iterating since we found all acquisitions to satisfy reduction
                break

            remaining_amount -= acquisition_event.remaining_amount
            asset_events.acquisitions_manager.consume_result(
                used_amount=acquisition_event.remaining_amount,
                asset=asset,
            )

        if remaining_amount != ZERO:
            if not asset.is_fiat():
                self.missing_acquisitions.append(
                    MissingAcquisition(
                        originating_event_id=originating_event_id,
                        asset=asset,
                        time=timestamp,
                        found_amount=amount - remaining_amount,
                        missing_amount=remaining_amount,
                    ),
                )
            return False

        return True

    def obtain_asset(
            self,
            event: 'HistoryEvent',
            price: Price,
            index: int,
    ) -> None:
        """Adds an acquisition event for an asset"""
        asset_event = AssetAcquisitionEvent.from_history_event(
            event=event, price=price, index=index,
        )
        asset_events = self.get_events(event.asset)
        asset_events.acquisitions_manager.add_in_event(asset_event)

    @overload
    def spend_asset(
            self,
            originating_event_id: int | None,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: Literal[True],
    ) -> CostBasisInfo:
        ...

    @overload
    def spend_asset(
            self,
            originating_event_id: int | None,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: Literal[False],
    ) -> None:
        ...

    @overload  # not sure why we need this overload too -> https://github.com/python/mypy/issues/6113  # noqa: E501
    def spend_asset(
            self,
            originating_event_id: int | None,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: bool,
    ) -> CostBasisInfo | None:
        ...

    def spend_asset(
            self,
            originating_event_id: int | None,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: bool,
    ) -> CostBasisInfo | None:
        """
        Register an asset spending event. For example from a trade, a fee, a swap.

        The `taxable_spend` argument defines if this spend is to be considered taxable or not.
        This is important for customization of accounting for some events such as swapping
        ETH for aETH, locking GNO for LockedGNO. In many jurisdictions in this case
        it can be considered as locking/depositing instead of swapping.
        """
        event = AssetSpendEvent(
            location=location,
            timestamp=timestamp,
            amount=amount,
            rate=rate,
        )
        asset_events = self.get_events(asset)
        asset_events.spends.append(event)
        if not asset.is_fiat() and taxable_spend:
            return asset_events.acquisitions_manager.calculate_spend_cost_basis(
                spending_amount=amount,
                spending_asset=asset,
                timestamp=timestamp,
                missing_acquisitions=self.missing_acquisitions,
                used_acquisitions=asset_events.used_acquisitions,
                settings=self.settings,
                timestamp_to_date=self.timestamp_to_date,
                originating_event_id=originating_event_id,
            )
        # just reduce the amount's acquisition without counting anything
        self.reduce_asset_amount(
            originating_event_id=originating_event_id,
            asset=asset,
            amount=amount,
            timestamp=timestamp,
        )
        return None
