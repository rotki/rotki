import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    overload,
)

from rotkehlchen.accounting.types import MissingAcquisition, MissingPrice
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CostBasisMethod, Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
    from rotkehlchen.db.dbhandler import DBHandler

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
    def from_processed_event(cls: Type['AssetAcquisitionEvent'], event: 'ProcessedAccountingEvent') -> 'AssetAcquisitionEvent':  # noqa: E501
        return cls(
            amount=event.taxable_amount,
            timestamp=event.timestamp,
            rate=event.price,
            index=event.index,
        )

    @classmethod
    def deserialize(cls: Type['AssetAcquisitionEvent'], data: Dict[str, Any]) -> 'AssetAcquisitionEvent':  # noqa: E501
        """May raise DeserializationError"""
        try:
            return cls(
                amount=data['full_amount'],
                timestamp=data['timestamp'],
                rate=data['rate'],
                index=data['index'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {str(e)}') from e

    def serialize(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'full_amount': str(self.amount),
            'rate': str(self.rate),
            'index': self.index,
        }


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetSpendEvent:
    timestamp: Timestamp
    location: Location
    amount: FVal  # Amount of the asset we sell
    rate: FVal  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset

    def __str__(self) -> str:
        return (
            f'AssetSpendEvent in {str(self.location)} @ {self.timestamp}.'
            f'amount: {self.amount} rate: {self.rate}'
        )


class BaseAcquisitionsOrder(metaclass=ABCMeta):
    _acquisitions: deque[AssetAcquisitionEvent]

    def __init__(self) -> None:
        self._acquisitions = deque()

    @abstractmethod
    def add_acquisition(self, acquisition: AssetAcquisitionEvent) -> None:
        """The core method. Should be implemented by subclasses.
        This method takes a new acquisition and decides where to insert it
        and thus determines the PnL order.
        """
        ...

    def processing_iterator(self) -> Iterator[AssetAcquisitionEvent]:
        """Iteration method over acquisition events.
        We can't return here Tuple of AssetAcquisitionEvents as we need to return
        the first event each time but _acquisitions may be not modified between iterations.
        """
        while len(self._acquisitions) > 0:
            yield self._acquisitions[0]

    def get_acquisitions(self) -> Tuple[AssetAcquisitionEvent, ...]:
        """Returns read-only _acquisitions"""
        return tuple(self._acquisitions)

    def consume_result(self, used_amount: FVal) -> None:
        """This function should be used to consume results of the
        currently processed event (received from __next__)
        The current event's remaining_amount will be decreased by used_amount
        If event's remaining_amount will become ZERO, the event will be deleted
        May raise:
        - IndexError if the method was called when acquisitions were empty
        """
        # this is a temporary assertion to test that new accounting tools work properly.
        # Written on 06.06.2022 and can be removed after a couple of months if everything goes well
        assert ZERO <= used_amount <= self._acquisitions[0].remaining_amount, \
            f'Used amount must be in the interval [0, {self._acquisitions[0].remaining_amount}] but it was {used_amount}'  # noqa: E501

        self._acquisitions[0].remaining_amount -= used_amount
        if self._acquisitions[0].remaining_amount == ZERO:
            self._acquisitions.popleft()

    def __len__(self) -> int:
        return len(self._acquisitions)


class FIFOAcquisitionsOrder(BaseAcquisitionsOrder):
    """Accounting in FIFO (first-in-first-out) order"""
    def add_acquisition(self, acquisition: AssetAcquisitionEvent) -> None:
        self._acquisitions.append(acquisition)


class LIFOAcquisitionsOrder(BaseAcquisitionsOrder):
    """Accounting in LIFO (last-in-first-out) order"""
    def add_acquisition(self, acquisition: AssetAcquisitionEvent) -> None:
        self._acquisitions.appendleft(acquisition)


class CostBasisEvents:
    used_acquisitions: List[AssetAcquisitionEvent]
    acquisitions_manager: BaseAcquisitionsOrder
    spends: List[AssetSpendEvent]

    def __init__(self, cost_basis_method: CostBasisMethod) -> None:
        """This class contains data about acquisitions and spends. `acquisitions` field contains
        custom Iterable that provides acquisitions in the order defined by `cost_basis_method`
        """
        if cost_basis_method == CostBasisMethod.FIFO:
            self.acquisitions_manager = FIFOAcquisitionsOrder()
        elif cost_basis_method == CostBasisMethod.LIFO:
            self.acquisitions_manager = LIFOAcquisitionsOrder()
        self.spends = []
        self.used_acquisitions = []


class MatchedAcquisition(NamedTuple):
    amount: FVal  # the amount used from the acquisition event
    event: AssetAcquisitionEvent  # the acquisition event
    taxable: bool  # whether it counts for taxable or non-taxable cost basis

    def serialize(self) -> Dict[str, Any]:
        """Turn to a dict to be serialized into the DB"""
        return {
            'amount': str(self.amount),
            'event': self.event.serialize(),
            'taxable': self.taxable,
        }

    @classmethod
    def deserialize(cls: Type['MatchedAcquisition'], data: Dict[str, Any]) -> 'MatchedAcquisition':
        """May raise DeserializationError"""
        try:
            event = AssetAcquisitionEvent.deserialize(data['event'])
            amount = FVal(data['amount'])  # TODO: deserialize_fval
            taxable = data['taxable']
        except KeyError as e:
            raise DeserializationError(f'Missing key {str(e)}') from e

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
    matched_acquisitions: List[MatchedAcquisition]
    is_complete: bool

    def serialize(self) -> Dict[str, Any]:
        """Turn to a dict to be exported into the DB"""
        return {
            'is_complete': self.is_complete,
            'matched_acquisitions': [x.serialize() for x in self.matched_acquisitions],
        }

    @classmethod
    def deserialize(cls: Type['CostBasisInfo'], data: Dict[str, Any]) -> Optional['CostBasisInfo']:
        """Creates a CostBasisInfo object from a json dict made from serialize()

        May raise:
        - DeserializationError
        """
        try:
            is_complete = data['is_complete']
            matched_acquisitions = []
            for entry in data['matched_acquisitions']:
                matched_acquisitions.append(MatchedAcquisition.deserialize(entry))
        except KeyError as e:
            raise DeserializationError(f'Could not decode CostBasisInfo json from the DB due to missing key {str(e)}') from e  # noqa: E501

        return CostBasisInfo(  # the 0 are not serialized and not used at recall so is okay to skip
            taxable_amount=ZERO,
            taxable_bought_cost=ZERO,
            taxfree_bought_cost=ZERO,
            is_complete=is_complete,
            matched_acquisitions=matched_acquisitions,
        )

    def to_string(self, converter: Callable[[Timestamp], str]) -> Tuple[str, str]:
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
        self._events: DefaultDict[Asset, CostBasisEvents] = defaultdict(lambda: CostBasisEvents(settings.cost_basis_method))  # noqa: E501
        self.missing_acquisitions: List[MissingAcquisition] = []
        self.missing_prices: Set[MissingPrice] = set()

    def get_events(self, asset: Asset) -> CostBasisEvents:
        """Custom getter for events so that we have common cost basis for some assets"""
        if asset == A_WETH:
            asset = A_ETH

        return self._events[asset]

    def reduce_asset_amount(self, asset: Asset, amount: FVal, timestamp: Timestamp) -> bool:
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
                asset_events.acquisitions_manager.consume_result(remaining_amount)
                remaining_amount = ZERO
                # stop iterating since we found all acquisitions to satisfy reduction
                break

            remaining_amount -= acquisition_event.remaining_amount
            asset_events.acquisitions_manager.consume_result(acquisition_event.remaining_amount)

        if remaining_amount != ZERO:
            if not asset.is_fiat():
                self.missing_acquisitions.append(
                    MissingAcquisition(
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
            event: 'ProcessedAccountingEvent',
    ) -> None:
        """Adds an acquisition event for an asset"""
        asset_event = AssetAcquisitionEvent.from_processed_event(event=event)
        asset_events = self.get_events(event.asset)
        asset_events.acquisitions_manager.add_acquisition(asset_event)

    @overload
    def spend_asset(
            self,
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
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: bool,
    ) -> Optional[CostBasisInfo]:
        ...

    def spend_asset(
            self,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            taxable_spend: bool,
    ) -> Optional[CostBasisInfo]:
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
            return self.calculate_spend_cost_basis(
                spending_amount=amount,
                spending_asset=asset,
                timestamp=timestamp,
            )
        # just reduce the amount's acquisition without counting anything
        self.reduce_asset_amount(asset=asset, amount=amount, timestamp=timestamp)
        return None

    def calculate_spend_cost_basis(
            self,
            spending_amount: FVal,
            spending_asset: Asset,
            timestamp: Timestamp,
    ) -> CostBasisInfo:
        """
        When spending `spending_amount` of `spending_asset` at `timestamp` this function
        calculates using the first-in-first-out rule the corresponding buy/s from
        which to do profit calculation. Also applies the "free after given time period"
        rule which applies for some jurisdictions such as 1 year for Germany.

        Returns the information in a CostBasisInfo object if enough acquisitions have
        been found.
        """
        remaining_sold_amount = spending_amount
        taxfree_bought_cost = taxable_bought_cost = taxable_amount = taxfree_amount = ZERO  # noqa: E501
        matched_acquisitions = []
        asset_events = self.get_events(spending_asset)

        for acquisition_event in asset_events.acquisitions_manager.processing_iterator():
            if self.settings.taxfree_after_period is None:
                at_taxfree_period = False
            else:
                at_taxfree_period = (
                    acquisition_event.timestamp + self.settings.taxfree_after_period < timestamp
                )

            if remaining_sold_amount < acquisition_event.remaining_amount:
                acquisition_cost = acquisition_event.rate * remaining_sold_amount

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
                    profit_currency=self.profit_currency,
                    time=self.timestamp_to_date(acquisition_event.timestamp),
                )
                matched_acquisitions.append(MatchedAcquisition(
                    amount=remaining_sold_amount,
                    event=acquisition_event,
                    taxable=taxable,
                ))
                asset_events.acquisitions_manager.consume_result(remaining_sold_amount)
                remaining_sold_amount = ZERO
                # stop iterating since we found all acquisitions to satisfy this spend
                break

            remaining_sold_amount -= acquisition_event.remaining_amount
            acquisition_cost = acquisition_event.rate * acquisition_event.remaining_amount
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
                profit_currency=self.profit_currency,
                time=self.timestamp_to_date(acquisition_event.timestamp),
            )
            matched_acquisitions.append(MatchedAcquisition(
                amount=acquisition_event.remaining_amount,
                event=acquisition_event,
                taxable=taxable,
            ))
            asset_events.used_acquisitions.append(acquisition_event)
            asset_events.acquisitions_manager.consume_result(acquisition_event.remaining_amount)
            # and since this event is going to be removed, reduce its remaining to zero
            acquisition_event.remaining_amount = ZERO

        is_complete = True
        if remaining_sold_amount != ZERO:
            # if we still have sold amount but no acquisitions to satisfy it then we only
            # found acquisitions to partially satisfy the sell
            adjusted_amount = spending_amount - taxfree_amount
            self.missing_acquisitions.append(
                MissingAcquisition(
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

    def get_calculated_asset_amount(self, asset: Asset) -> Optional[FVal]:
        """Get the amount of asset accounting has calculated we should have after
        the history has been processed
        """
        asset_events = self.get_events(asset)

        amount = ZERO
        for acquisition_event in asset_events.acquisitions_manager.get_acquisitions():
            amount += acquisition_event.remaining_amount
        return amount if amount != ZERO else None
