import logging
from typing import TYPE_CHECKING, List, Literal, Optional

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures import ProcessedAccountingEvent
from rotkehlchen.accounting.transactions import TransactionsAccountant
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventType
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AccountingPot():
    """
    Represents a single accounting depot for which events are processed
    under a specific set of rules
    """

    def __init__(
            self,
            profit_currency: Asset,
            evm_tx_decoder: 'EVMTransactionDecoder',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.profit_currency = profit_currency
        self.cost_basis = CostBasisCalculator(
            profit_currency=profit_currency,
            msg_aggregator=msg_aggregator,
        )
        self.pnls = PnlTotals()
        self.processed_events: List[ProcessedAccountingEvent] = []
        self.transactions = TransactionsAccountant(
            evm_tx_decoder=evm_tx_decoder,
            pot=self,
        )
        self.settings = DBSettings()
        self.query_start_ts = self.query_end_ts = 0
        # If this flag is True when your asset is being forcefully sold as a
        # loan/margin settlement then profit/loss is also calculated before the entire
        # amount is taken as a loss
        self.count_profit_for_settlements = False

    def get_rate_in_profit_currency(self, asset: Asset, timestamp: Timestamp) -> Price:
        """Get the profit_currency price of asset in the given timestamp

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        if asset == self.profit_currency:
            rate = Price(FVal(1))
        else:
            rate = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=timestamp,
            )
        return rate

    def reset(
            self,
            settings: DBSettings,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        self.profit_currency = settings.main_currency
        self.settings = settings
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.pnls.reset()
        self.cost_basis.reset(self.profit_currency)

    def add_acquisition(
            self,
            event_type: 'AccountingEventType',
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Optional[Price] = None,
    ) -> None:
        """Add an asset acquisition event for the pot and count it in PnL if needed.

        If a custom price for the asset should be used it can be passed here via
        given_price. Price is always in profit currency during accounting."""
        if given_price is not None:
            price = given_price
        else:
            price = self.get_rate_in_profit_currency(asset=asset, timestamp=timestamp)

        prefork_events = self.cost_basis.handle_prefork_asset_acquisitions(
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            price=price,
        )
        self.processed_events.extend(prefork_events)

        event = ProcessedAccountingEvent(
            type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            taxable_amount=amount,
            free_amount=ZERO,
            price=price,
            pnl=PNL(),  # filled out later
            cost_basis=None,
        )
        self.cost_basis.obtain_asset(event)
        self.processed_events.append(event)
        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts and taxable:
            self.pnls[event_type.to_pnl_overview_str()] += event.calculate_pnl()

    def add_spend(
            self,
            event_type: 'AccountingEventType',
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Optional[FVal] = None,
    ) -> None:
        """Add an asset spend event for the pot and count it in PnL if needed

        If a custom price for the asset should be used it can be passed here via
        given_price. Price is always in profit currency during accounting.
        """
        if asset.is_fiat():
            taxable = False

        self.cost_basis.handle_prefork_asset_spends(
            asset=asset,
            amount=amount,
            timestamp=timestamp,
        )
        if given_price is not None:
            price = given_price
        else:
            price = self.get_rate_in_profit_currency(
                asset=asset,
                timestamp=timestamp,
            )
        spend_cost = self.cost_basis.spend_asset(
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            rate=price,
            taxable_spend=taxable,
        )
        spend_event = ProcessedAccountingEvent(
            type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            taxable_amount=spend_cost.taxable_amount,
            free_amount=amount - spend_cost.taxable_amount,
            price=price,
            pnl=PNL(),  # filled out later
            cost_basis=spend_cost,
        )
        self.processed_events.append(spend_event)
        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts and taxable:
            self.pnls[event_type.to_pnl_overview_str()] += spend_event.calculate_pnl()

    def add_asset_change_event(
            self,
            method: Literal['acquisition', 'spend'],
            event_type: 'AccountingEventType',
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Optional[FVal] = None,
    ) -> None:
        fn = getattr(self, method)
        return fn(
            event_type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            taxable=taxable,
            given_price=given_price,
        )
