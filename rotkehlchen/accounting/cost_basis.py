import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, DefaultDict, NamedTuple, Any, Callable

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Timestamp, Location
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetAcquisitionEvent:
    timestamp: Timestamp
    location: Location
    description: str  # The description of the acquisition. Such as trade, loan etc.
    amount: FVal  # Amount of the asset being bought
    remaining_amount: FVal = field(init=False)  # Same as amount but reduced during processing
    rate: FVal  # Rate in profit currency for which we buy 1 unit of the buying asset
    # Fee rate in profit currency which we paid for each unit of the buying asset
    fee_rate: FVal

    def __post_init__(self) -> None:
        self.remaining_amount = self.amount

    def __str__(self) -> str:
        return (
            f'AssetAcquisitionEvent {self.description} in {str(self.location)} @ {self.timestamp}.'
            f'amount: {self.amount} rate: {self.rate} fee_rate: {self.fee_rate}'
        )

    def serialize(self) -> Dict[str, Any]:
        """Turn to a dict to be returned by the API and shown in the UI"""
        return {
            'time': self.timestamp,
            'description': self.description,
            'location': str(self.location),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee_rate': str(self.fee_rate),
        }

    @property
    def acquisition_cost(self) -> FVal:
        """The acquisition cost of this event is:
        amount * rate + fee_rate * amount
        """
        return self.remaining_amount.fma(self.rate, self.fee_rate * self.remaining_amount)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetSpendEvent:
    timestamp: Timestamp
    location: Location
    amount: FVal  # Amount of the asset we sell
    rate: FVal  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset
    fee_rate: FVal  # Fee rate in 'profit_currency' which we paid for each unit of the sold asset
    gain: FVal  # Gain in profit currency for this trade. Fees are not counted here

    def __str__(self) -> str:
        return (
            f'AssetSpendEvent in {str(self.location)} @ {self.timestamp}.'
            f'amount: {self.amount} rate: {self.rate} fee_rate: {self.fee_rate} '
            f'gain_in_profit_currency: {self.gain} '
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class CostBasisEvents:
    used_acquisitions: List[AssetAcquisitionEvent] = field(init=False)
    acquisitions: List[AssetAcquisitionEvent] = field(init=False)
    spends: List[AssetSpendEvent] = field(init=False)

    def __post_init__(self) -> None:
        """Using this since can't use mutable default arguments"""
        self.used_acquisitions = []
        self.acquisitions = []
        self.spends = []


class MatchedAcquisition(NamedTuple):
    amount: FVal
    event: AssetAcquisitionEvent

    def serialize(self) -> Dict[str, Any]:
        """Turn to a dict to be returned by the API and shown in the UI"""
        serialized_acquisition = self.event.serialize()
        serialized_acquisition['used_amount'] = str(self.amount)
        return serialized_acquisition

    def to_string(self, converter: Callable[[Timestamp], str]) -> str:
        return (
            f'{self.amount} / {self.event.amount} acquired in {str(self.event.location)}'
            f' at {converter(self.event.timestamp)}'
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
        """Turn to a dict to be returned by the API and shown in the UI"""
        return {
            'is_complete': self.is_complete,
            'matched_acquisitions': [x.serialize() for x in self.matched_acquisitions],
        }

    def to_string(self, converter: Callable[[Timestamp], str]) -> str:
        """Turn to a string to be shown in exported files such as CSV"""
        value = ''
        if not self.is_complete:
            value += 'Incomplete cost basis information for spend. '

        if len(self.matched_acquisitions) == 0:
            return value

        value += f'Used: {",".join([x.to_string(converter) for x in self.matched_acquisitions])}'
        return value


class CostBasisCalculator():

    def __init__(self, csv_exporter: CSVExporter, profit_currency: Asset) -> None:
        self._taxfree_after_period: Optional[int] = None
        self.csv_exporter = csv_exporter
        self.reset(profit_currency)

    def reset(self, profit_currency: Asset) -> None:
        self.profit_currency = profit_currency
        self.events: DefaultDict[Asset, CostBasisEvents] = defaultdict(CostBasisEvents)

    @property
    def taxfree_after_period(self) -> Optional[int]:
        return self._taxfree_after_period

    @taxfree_after_period.setter
    def taxfree_after_period(self, value: Optional[int]) -> None:
        is_valid = isinstance(value, int) or value is None
        assert is_valid, 'set taxfree_after_period should only get int or None'
        self._taxfree_after_period = value

    def reduce_asset_amount(self, asset: Asset, amount: FVal) -> bool:
        """Searches all acquisition events for asset and reduces them by amount
        Returns True if enough acquisition events to reduce the asset by amount were
        found and False otherwise.
        """
        # No need to do anything if amount is to be reduced by zero
        if amount == ZERO:
            return True

        if asset not in self.events or len(self.events[asset].acquisitions) == 0:
            return False

        remaining_amount_from_last_buy = FVal('-1')
        remaining_amount = amount
        for idx, acquisition_event in enumerate(self.events[asset].acquisitions):
            if remaining_amount < acquisition_event.remaining_amount:
                stop_index = idx
                remaining_amount_from_last_buy = acquisition_event.remaining_amount - remaining_amount  # noqa: E501
                # stop iterating since we found all acquisitions to satisfy reduction
                break

            # else
            remaining_amount -= acquisition_event.remaining_amount
            if idx == len(self.events[asset].acquisitions) - 1:
                stop_index = idx + 1

        # Otherwise, delete all the used up acquisitions from the list
        del self.events[asset].acquisitions[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            self.events[asset].acquisitions[0].remaining_amount = remaining_amount_from_last_buy
        elif remaining_amount != ZERO:
            return False

        return True

    def obtain_asset(
            self,
            location: Location,
            timestamp: Timestamp,
            description: str,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            fee_in_profit_currency: FVal,
    ) -> None:
        """Adds an acquisition event for an asset

        - rate: The rate in profit currency for which 1 unit of asset is obtained
        - fee_in_profit_currency: The amount of profit currency paid as fee for this acquisition.
            Can be ZERO
        """
        event = AssetAcquisitionEvent(
            location=location,
            timestamp=timestamp,
            description=description,
            amount=amount,
            rate=rate,
            fee_rate=fee_in_profit_currency / amount,
        )
        self.events[asset].acquisitions.append(event)
        logger.debug(event)

    def spend_asset(
            self,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            rate: FVal,
            fee_in_profit_currency: FVal = ZERO,
            gain_in_profit_currency: FVal = ZERO,
    ) -> None:
        event = AssetSpendEvent(
            location=location,
            timestamp=timestamp,
            amount=amount,
            rate=rate,
            fee_rate=fee_in_profit_currency / amount,
            gain=gain_in_profit_currency,
        )
        self.events[asset].spends.append(event)
        logger.debug(event)

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
        stop_index = -1
        taxfree_bought_cost = ZERO
        taxable_bought_cost = ZERO
        taxable_amount = ZERO
        taxfree_amount = ZERO
        remaining_amount_from_last_buy = FVal('-1')
        matched_acquisitions = []
        for idx, acquisition_event in enumerate(self.events[spending_asset].acquisitions):
            if self.taxfree_after_period is None:
                at_taxfree_period = False
            else:
                at_taxfree_period = (
                    acquisition_event.timestamp + self.taxfree_after_period < timestamp
                )

            if remaining_sold_amount < acquisition_event.remaining_amount:
                stop_index = idx
                buying_cost = remaining_sold_amount.fma(
                    acquisition_event.rate,
                    (acquisition_event.fee_rate * remaining_sold_amount),
                )

                if at_taxfree_period:
                    taxfree_amount += remaining_sold_amount
                    taxfree_bought_cost += buying_cost
                else:
                    taxable_amount += remaining_sold_amount
                    taxable_bought_cost += buying_cost

                remaining_amount_from_last_buy = acquisition_event.remaining_amount - remaining_sold_amount  # noqa: E501
                log.debug(
                    'Spend uses up part of historical acquisition',
                    sensitive_log=True,
                    tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                    used_amount=remaining_sold_amount,
                    from_amount=acquisition_event.amount,
                    asset=spending_asset,
                    acquisition_rate=acquisition_event.rate,
                    profit_currency=self.profit_currency,
                    time=self.csv_exporter.timestamp_to_date(acquisition_event.timestamp),
                )
                matched_acquisitions.append(MatchedAcquisition(
                    amount=remaining_sold_amount,
                    event=acquisition_event,
                ))
                # stop iterating since we found all acquisitions to satisfy this spend
                break

            remaining_sold_amount -= acquisition_event.remaining_amount
            if at_taxfree_period:
                taxfree_amount += acquisition_event.remaining_amount
                taxfree_bought_cost += acquisition_event.acquisition_cost
            else:
                taxable_amount += acquisition_event.remaining_amount
                taxable_bought_cost += acquisition_event.acquisition_cost

            log.debug(
                'Spend uses up entire historical acquisition',
                sensitive_log=True,
                tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                bought_amount=acquisition_event.remaining_amount,
                asset=spending_asset,
                acquisition_rate=acquisition_event.rate,
                profit_currency=self.profit_currency,
                time=self.csv_exporter.timestamp_to_date(acquisition_event.timestamp),
            )
            matched_acquisitions.append(MatchedAcquisition(
                amount=acquisition_event.remaining_amount,
                event=acquisition_event,
            ))
            # and since this events is going to be removed, reduce its remaining to zero
            acquisition_event.remaining_amount = ZERO

            # If the sell used up the last historical acquisition
            if idx == len(self.events[spending_asset].acquisitions) - 1:
                stop_index = idx + 1

        if len(self.events[spending_asset].acquisitions) == 0:
            log.critical(
                'No documented acquisition found for "{}" before {}'.format(
                    spending_asset,
                    self.csv_exporter.timestamp_to_date(timestamp),
                ),
            )
            # That means we had no documented acquisition for that asset. This is not good
            # because we can't prove a corresponding acquisition and as such we are burdened
            # calculating the entire spend as profit which needs to be taxed
            return CostBasisInfo(
                taxable_amount=spending_amount,
                taxable_bought_cost=ZERO,
                taxfree_bought_cost=ZERO,
                matched_acquisitions=[],
                is_complete=False,
            )

        is_complete = True
        # Otherwise, delete all the used up acquisitions from the list
        self.events[spending_asset].used_acquisitions.extend(
            self.events[spending_asset].acquisitions[:stop_index],
        )
        del self.events[spending_asset].acquisitions[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            self.events[spending_asset].acquisitions[0].remaining_amount = remaining_amount_from_last_buy  # noqa: E501
        elif remaining_sold_amount != ZERO:
            # if we still have sold amount but no acquisitions to satisfy it then we only
            # found acquisitions to partially satisfy the sell
            adjusted_amount = spending_amount - taxfree_amount
            log.critical(
                f'Not enough documented acquisitions found for "{spending_asset}" before '
                f'{self.csv_exporter.timestamp_to_date(timestamp)}.'
                f'Only found acquisitions for {taxable_amount + taxfree_amount} {spending_asset}',
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

    def calculate_asset_details(
            self,
            taxfree_after_period: Optional[int],
    ) -> Dict[Asset, Tuple[FVal, FVal]]:
        """ Calculates what amount of all assets has been untouched for the tax-free period
        and is hence tax-free and also the average buy price for each asset"""
        self.details: Dict[Asset, Tuple[FVal, FVal]] = {}
        now = ts_now()
        for asset, events in self.events.items():
            tax_free_amount_left = ZERO
            amount_sum = ZERO
            average = ZERO
            for acquisition_event in events.acquisitions:
                if taxfree_after_period is not None:
                    if acquisition_event.timestamp + taxfree_after_period < now:
                        tax_free_amount_left += acquisition_event.remaining_amount
                amount_sum += acquisition_event.remaining_amount
                average += acquisition_event.remaining_amount * acquisition_event.rate

            if amount_sum == ZERO:
                self.details[asset] = (ZERO, ZERO)
            else:
                self.details[asset] = (tax_free_amount_left, average / amount_sum)

        return self.details

    def get_calculated_asset_amount(self, asset: Asset) -> Optional[FVal]:
        """Get the amount of asset accounting has calculated we should have after
        the history has been processed
        """
        if asset not in self.events:
            return None

        amount = FVal(0)
        for acquisition_event in self.events[asset].acquisitions:
            amount += acquisition_event.remaining_amount
        return amount
