import logging
from typing import TYPE_CHECKING, Any, List, Literal, Optional, Tuple

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.transactions import TransactionsAccountant
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors import (
    DeserializationError,
    InputError,
    NoPriceForGivenTimestamp,
    PriceQueryUnsupportedAsset,
    RemoteError,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AccountingPot(CustomizableDateMixin):
    """
    Represents a single accounting depot for which events are processed
    under a specific set of rules
    """

    def __init__(
            self,
            database: 'DBHandler',
            evm_tx_decoder: 'EVMTransactionDecoder',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(database=database)
        self.profit_currency = self.settings.main_currency
        self.cost_basis = CostBasisCalculator(
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.pnls = PnlTotals()
        self.processed_events: List[ProcessedAccountingEvent] = []
        self.transactions = TransactionsAccountant(
            evm_tx_decoder=evm_tx_decoder,
            pot=self,
        )
        self.query_start_ts = self.query_end_ts = Timestamp(0)
        # If this flag is True when your asset is being forcefully sold as a
        # loan/margin settlement then profit/loss is also calculated before the entire
        # amount is taken as a loss
        self.count_profit_for_settlements = False

    def _add_processed_event(self, event: ProcessedAccountingEvent) -> None:
        dbpnl = DBAccountingReports(self.database)
        self.processed_events.append(event)
        try:
            dbpnl.add_report_data(
                report_id=self.report_id,
                time=event.timestamp,
                ts_converter=self.timestamp_to_date,
                event=event,
            )
        except (DeserializationError, InputError) as e:
            log.error(str(e))
            return

        log.debug(event.to_string(self.timestamp_to_date))

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
            report_id: int,
    ) -> None:
        self.settings = settings
        self.report_id = report_id
        self.profit_currency = self.settings.main_currency
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.pnls.reset()
        self.cost_basis.reset(settings)
        self.transactions.reset()

    def add_acquisition(
            self,
            event_type: AccountingEventType,
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
        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts and taxable:
            self.pnls[event_type] += event.calculate_pnl(
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
            )

        self._add_processed_event(event)

    def add_spend(
            self,
            event_type: AccountingEventType,
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Optional[Price] = None,
            taxable_amount_ratio: FVal = ONE,
            count_entire_amount_spend: bool = True,
            count_cost_basis_pnl: bool = True,
    ) -> Tuple[FVal, FVal]:
        """Add an asset spend event for the pot and count it in PnL if needed

        If a custom price for the asset should be used it can be passed here via
        given_price. Price is always in profit currency during accounting.

        If taxable_ratio is given then this is how we initialize the taxable and
        free amounts in the case of missing cost basis. By default it's all taxable.

        If count_entire_amount_spend is True then the entire amount is counted as a spend.
        Which means an expense (negative pnl).

        If count_cost_basis_pnl is True then we also count any profit/loss the asset
        may have had compared to when it was acquired.

        Returns (free, taxable) amounts.
        """
        if asset.is_fiat() and event_type != AccountingEventType.FEE:
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

        spend_cost = None
        if count_cost_basis_pnl:
            spend_cost = self.cost_basis.spend_asset(
                location=location,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                rate=price,
                taxable_spend=taxable,
            )
        taxable_amount = taxable_amount_ratio * amount
        free_amount = amount - taxable_amount
        if spend_cost:
            taxable_amount = spend_cost.taxable_amount
            free_amount = amount - spend_cost.taxable_amount

        spend_event = ProcessedAccountingEvent(
            type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            taxable_amount=taxable_amount,
            free_amount=free_amount,
            price=price,
            pnl=PNL(),  # filled out later
            cost_basis=spend_cost,
        )
        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts and taxable:
            self.pnls[event_type] += spend_event.calculate_pnl(
                count_entire_amount_spend=count_entire_amount_spend,
                count_cost_basis_pnl=count_cost_basis_pnl,
            )

        self._add_processed_event(spend_event)
        return free_amount, taxable_amount

    def add_asset_change_event(
            self,
            method: Literal['acquisition', 'spend'],
            event_type: AccountingEventType,
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Optional[Price] = None,
            **kwargs: Any,
    ) -> None:
        fn = getattr(self, f'add_{method}')
        return fn(
            event_type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            taxable=taxable,
            given_price=given_price,
            **kwargs,
        )

    def get_prices_for_swap(
            self,
            timestamp: Timestamp,
            amount_in: FVal,
            asset_in: Asset,
            amount_out: FVal,
            asset_out: Asset,
            fee: Optional[FVal],
            fee_asset: Optional[Asset],
    ) -> Optional[Tuple[Price, Price]]:
        """Calculates the prices for assets going in and out of a swap/trade.

        The rules are:
        - For the asset_in we get the equivalent rate from asset_out + fee if any.
        If there is no price found for fee_currency we ignore it.
        If there is no price for asset_out then we switch to using the asset_in price itself.
        If neither of the 2 assets can have their price known, we bail.

        - For the asset_out we get the equivalent rate from asset_in.
        if there is no price found for asset_in then we switch to using the asset_out price.
        If neither of the 2 assets can have their price known we bail.

        Returns (out_price, in_price) or None if it can't find proper prices
        """
        try:
            out_price = self.get_rate_in_profit_currency(
                asset=asset_out,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
            out_price = None

        fee_price = None
        if fee is not None and fee != ZERO:
            try:
                fee_price = self.get_rate_in_profit_currency(
                    asset=fee_asset,  # type: ignore # fee_asset should exist here
                    timestamp=timestamp,
                )
            except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
                fee_price = None
        try:
            in_price = self.get_rate_in_profit_currency(
                asset=asset_in,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
            in_price = None

        if out_price is None and in_price is None:
            return None

        if out_price is not None:
            paid = amount_out * out_price
            if fee_price is not None:
                paid += fee_price * fee  # type: ignore # fee should exist here
            calculated_in = Price(paid / amount_in)
        else:
            calculated_in = in_price  # type: ignore # in_price should exist here

        if in_price is not None:
            calculated_out = Price((amount_in * in_price) / amount_out)
        else:
            calculated_out = out_price  # type: ignore # out_price should exist here

        return (calculated_out, calculated_in)
