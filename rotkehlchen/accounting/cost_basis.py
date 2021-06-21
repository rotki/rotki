import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, DefaultDict, Dict, List, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

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

        value += f'Used: {"|".join([x.to_string(converter) for x in self.matched_acquisitions])}'
        return value


class CostBasisCalculator():

    def __init__(
            self,
            csv_exporter: CSVExporter,
            profit_currency: Asset,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self._taxfree_after_period: Optional[int] = None
        self.csv_exporter = csv_exporter
        self.msg_aggregator = msg_aggregator
        self.reset(profit_currency)

    def reset(self, profit_currency: Asset) -> None:
        self.profit_currency = profit_currency
        self._events: DefaultDict[Asset, CostBasisEvents] = defaultdict(CostBasisEvents)

    @property
    def taxfree_after_period(self) -> Optional[int]:
        return self._taxfree_after_period

    @taxfree_after_period.setter
    def taxfree_after_period(self, value: Optional[int]) -> None:
        is_valid = isinstance(value, int) or value is None
        assert is_valid, 'set taxfree_after_period should only get int or None'
        self._taxfree_after_period = value

    def get_events(self, asset: Asset) -> CostBasisEvents:
        """Custom getter for events so that we have common cost basis for some assets"""
        if asset == A_WETH:
            asset = A_ETH

        return self._events[asset]

    def inform_user_missing_acquisition(
            self,
            asset: Asset,
            time: Timestamp,
            found_amount: Optional[FVal] = None,
            missing_amount: Optional[FVal] = None,
    ) -> None:
        """Inform the user for missing data for an acquisition via the msg aggregator"""
        if found_amount is None:
            self.msg_aggregator.add_error(
                f'No documented acquisition found for {asset} before '
                f'{self.csv_exporter.timestamp_to_date(time)}. Let rotki '
                f'know how you acquired it via a ledger action',
            )
            return

        self.msg_aggregator.add_error(
            f'Not enough documented acquisitions found for {asset} before '
            f'{self.csv_exporter.timestamp_to_date(time)}. Only found acquisitions '
            f'for {found_amount} {asset} and miss {missing_amount} {asset}.'
            f'Let rotki know how you acquired it via a ledger action',
        )

    def reduce_asset_amount(self, asset: Asset, amount: FVal) -> bool:
        """Searches all acquisition events for asset and reduces them by amount
        Returns True if enough acquisition events to reduce the asset by amount were
        found and False otherwise.
        """
        # No need to do anything if amount is to be reduced by zero
        if amount == ZERO:
            return True

        asset_events = self.get_events(asset)
        if len(asset_events.acquisitions) == 0:
            return False

        remaining_amount_from_last_buy = FVal('-1')
        remaining_amount = amount
        for idx, acquisition_event in enumerate(asset_events.acquisitions):
            if remaining_amount < acquisition_event.remaining_amount:
                stop_index = idx
                remaining_amount_from_last_buy = acquisition_event.remaining_amount - remaining_amount  # noqa: E501
                # stop iterating since we found all acquisitions to satisfy reduction
                break

            # else
            remaining_amount -= acquisition_event.remaining_amount
            if idx == len(asset_events.acquisitions) - 1:
                stop_index = idx + 1

        # Otherwise, delete all the used up acquisitions from the list
        del asset_events.acquisitions[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            asset_events.acquisitions[0].remaining_amount = remaining_amount_from_last_buy
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
        - amount: The amount that gets obtained. Can be zero for some edge cases.
        """
        fee_rate = ZERO if amount == ZERO else fee_in_profit_currency / amount
        event = AssetAcquisitionEvent(
            location=location,
            timestamp=timestamp,
            description=description,
            amount=amount,
            rate=rate,
            fee_rate=fee_rate,
        )
        asset_events = self.get_events(asset)
        asset_events.acquisitions.append(event)
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
        fee_rate = ZERO if amount == ZERO else fee_in_profit_currency / amount
        event = AssetSpendEvent(
            location=location,
            timestamp=timestamp,
            amount=amount,
            rate=rate,
            fee_rate=fee_rate,
            gain=gain_in_profit_currency,
        )
        asset_events = self.get_events(asset)
        asset_events.spends.append(event)
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
        asset_events = self.get_events(spending_asset)
        for idx, acquisition_event in enumerate(asset_events.acquisitions):
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
            if idx == len(asset_events.acquisitions) - 1:
                stop_index = idx + 1

        if len(asset_events.acquisitions) == 0:
            self.inform_user_missing_acquisition(spending_asset, timestamp)
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
        asset_events.used_acquisitions.extend(
            asset_events.acquisitions[:stop_index],
        )
        del asset_events.acquisitions[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            asset_events.acquisitions[0].remaining_amount = remaining_amount_from_last_buy  # noqa: E501
        elif remaining_sold_amount != ZERO:
            # if we still have sold amount but no acquisitions to satisfy it then we only
            # found acquisitions to partially satisfy the sell
            adjusted_amount = spending_amount - taxfree_amount
            self.inform_user_missing_acquisition(
                asset=spending_asset,
                time=timestamp,
                found_amount=taxable_amount + taxfree_amount,
                missing_amount=remaining_sold_amount,
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
        if len(asset_events.acquisitions) == 0:
            return None

        amount = FVal(0)
        for acquisition_event in asset_events.acquisitions:
            amount += acquisition_event.remaining_amount
        return amount
