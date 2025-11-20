import contextlib
import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.cost_basis.prefork import (
    handle_prefork_asset_acquisitions,
    handle_prefork_asset_spends,
)
from rotkehlchen.accounting.history_base_entries import EventsAccountant
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_KFEE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
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
            evm_accounting_aggregators: 'EVMAccountingAggregators',
            msg_aggregator: MessagesAggregator,
            is_dummy_pot: bool = False,
    ) -> None:
        """
        If is_dummy_pot is set to True then we won't save any events in the pot nor will we
        load any ignored assets. This option is used when fetching history events and checking
        if they have accounting rules set.
        """
        super().__init__(database=database)

        self.is_dummy_pot = is_dummy_pot
        if is_dummy_pot:
            self.ignored_asset_ids = set()
        else:
            with database.conn.read_ctx() as cursor:
                self.ignored_asset_ids = database.get_ignored_asset_ids(cursor)

        self.profit_currency = self.settings.main_currency.resolve_to_asset_with_oracles()
        self.cost_basis = CostBasisCalculator(
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.pnls = PnlTotals()
        self.processed_events: list[ProcessedAccountingEvent] = []
        self.events_accountant = EventsAccountant(
            evm_accounting_aggregators=evm_accounting_aggregators,
            pot=self,
        )
        # TODO: figure out a better way to resolve the cyclic import
        # when `DBEth2` is imported in `rotkehlchen/history/events/structures/eth2.py`
        self.dbeth2 = DBEth2(database)
        self.query_start_ts = self.query_end_ts = Timestamp(0)
        self.report_id: int | None = None

    def _add_processed_event(self, event: ProcessedAccountingEvent) -> None:
        dbpnl = DBAccountingReports(self.database)
        self.processed_events.append(event)
        try:
            dbpnl.add_report_data(
                report_id=self.report_id,  # type: ignore # report id is initialized by now
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
            rate = Price(ONE)
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
        with self.database.conn.read_ctx() as cursor:
            self.ignored_asset_ids = self.database.get_ignored_asset_ids(cursor)
        self.report_id = report_id
        self.profit_currency = self.settings.main_currency.resolve_to_asset_with_oracles()
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.pnls.reset()
        self.cost_basis.reset(settings)
        self.events_accountant.reset()
        self.processed_events = []

    def add_in_event(
            self,  # pylint: disable=unused-argument
            event_type: AccountingEventType,
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Price | None = None,
            extra_data: dict | None = None,
            **kwargs: Any,  # to be able to consume args given by add_asset_change_event
    ) -> None:
        """Add an asset acquisition event for the pot and count it in PnL if needed.

        If a custom price for the asset should be used it can be passed here via
        given_price. Price is always in profit currency during accounting."""
        if amount == ZERO:  # do nothing for zero acquisitions
            return

        if given_price is not None:
            price = given_price
        else:
            try:
                price = self.get_rate_in_profit_currency(asset=asset, timestamp=timestamp)
            except (PriceQueryUnsupportedAsset, RemoteError):
                price = ZERO_PRICE
            except NoPriceForGivenTimestamp as e:
                # In the case of NoPriceForGivenTimestamp when we got rate limited we let
                # it propagate so the user can take action after the report is made
                if e.rate_limited is True:
                    raise
                price = ZERO_PRICE

        prefork_events = handle_prefork_asset_acquisitions(
            cost_basis=self.cost_basis,
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            price=price,
            ignored_asset_ids=self.ignored_asset_ids,
            starting_index=len(self.processed_events),
        )
        for prefork_event in prefork_events:
            self._add_processed_event(prefork_event)

        if taxable is True:
            taxable_amount = amount
            free_amount = ZERO
        else:
            taxable_amount = ZERO
            free_amount = amount
        event = ProcessedAccountingEvent(
            event_type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            taxable_amount=taxable_amount,
            free_amount=free_amount,
            price=price,
            pnl=PNL(),  # filled out later
            cost_basis=None,
            index=len(self.processed_events),
        )
        if extra_data:
            event.extra_data = extra_data
        self.cost_basis.obtain_asset(event)
        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts and taxable:
            self.pnls[event_type] += event.calculate_pnl(
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
            )

        self._add_processed_event(event)

    def add_out_event(
            self,
            event_type: AccountingEventType,
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Price | None = None,
            taxable_amount_ratio: FVal = ONE,
            count_entire_amount_spend: bool = True,
            count_cost_basis_pnl: bool = True,
            extra_data: dict[str, Any] | None = None,
            originating_event_id: int | None = None,
    ) -> tuple[FVal, FVal]:
        """Add an asset spend event for the pot and count it in PnL if needed

        Since we still have history events mixed with other type of events this can be None.

        If a custom price for the asset should be used it can be passed here via
        given_price. Price is always in profit currency during accounting.

        If taxable_ratio is given then this is how we initialize the taxable and
        free amounts in the case of missing cost basis. By default it's all taxable.

        If count_entire_amount_spend is True then the entire amount is counted as a spend.
        Which means an expense (negative pnl).

        If count_cost_basis_pnl is True then we also count any profit/loss the asset
        may have had compared to when it was acquired.

        originating_event_id is the identifier of the history event that originated it.
        Can be missing since at the moment not all events are history events.

        Returns (free, taxable) amounts.
        """
        if amount == ZERO:  # do nothing for zero spends
            return ZERO, ZERO

        if asset.is_fiat() and event_type == AccountingEventType.TRADE:
            taxable = False  # for buys with fiat do not count it as taxable

        handle_prefork_asset_spends(
            originating_event_id=originating_event_id,
            cost_basis=self.cost_basis,
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

        if asset == A_KFEE:
            count_cost_basis_pnl = False
            taxable = False

        spend_cost = None
        if count_cost_basis_pnl:
            spend_cost = self.cost_basis.spend_asset(
                originating_event_id=originating_event_id,
                location=location,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                rate=price,
                taxable_spend=taxable,
            )

        if spend_cost:
            taxable_amount = spend_cost.taxable_amount
            free_amount = amount - spend_cost.taxable_amount
        elif taxable:
            taxable_amount = taxable_amount_ratio * amount
            free_amount = amount - taxable_amount
        else:
            taxable_amount = ZERO
            free_amount = amount

        spend_event = ProcessedAccountingEvent(
            event_type=event_type,
            notes=notes,
            location=location,
            timestamp=timestamp,
            asset=asset,
            taxable_amount=taxable_amount,
            free_amount=free_amount,
            price=price,
            pnl=PNL(),  # filled out later
            cost_basis=spend_cost,
            index=len(self.processed_events),
        )
        if extra_data:
            spend_event.extra_data = extra_data
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
            direction: EventDirection,
            event_type: AccountingEventType,
            notes: str,
            location: Location,
            timestamp: Timestamp,
            asset: Asset,
            amount: FVal,
            taxable: bool,
            given_price: Price | None = None,
            **kwargs: Any,
    ) -> None:
        if self.is_dummy_pot:
            return None

        fn = getattr(self, f'add_{direction.serialize()}_event')
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
            fees_info: list[tuple[FVal, Asset]],
    ) -> tuple[Price, Price] | None:
        """
        Calculates the prices for assets going in and out of a swap/trade.

        The algorithm is:
        1. Query oracles for prices of asset_out and asset_in.
        2.1 If either of the assets is fiat -- use its amount and price for calculations.
        2.2. If neither of the assets is fiat -- use `out_price` if `out_price` is known,
        otherwise `in_price`.
        3.1 If `fee_info` is provided and it's included in the cost basis,
        fee is included in the price of one of the assets.
        3.2. If `asset_out` is fiat -- fee is added to `calculated_in_price`.
        3.3. If `asset_in` is fiat -- fee is subtracted from `calculated_out_price`.
        3.4. Otherwise fee is added to the price of the asset that was bought.

        Returns (calculated_out_price, calculated_in_price) or None if it can't find proper prices.
        """
        if ZERO in (amount_in, amount_out):
            log.error(
                f'At get_prices_for_swap got a zero amount. {asset_in=} {amount_in=} '
                f'{asset_out=} {amount_out=}. Skipping ...')
            return None

        try:
            out_price = self.get_rate_in_profit_currency(
                asset=asset_out,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
            out_price = None

        try:
            in_price = self.get_rate_in_profit_currency(
                asset=asset_in,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, RemoteError):
            in_price = None
        except NoPriceForGivenTimestamp as e:
            in_price = None
            if e.rate_limited is True and out_price is None:
                raise  # in_price = out_price = None -> notify user

        # when `self.settings.include_fees_in_cost_basis == False` we completely ignore fees in
        # this function since they are not included in the cost basis
        fee_asset_prices = {}
        if self.settings.include_fees_in_cost_basis:
            for fee_info in fees_info:
                with contextlib.suppress(PriceQueryUnsupportedAsset, RemoteError):
                    fee_asset_prices[fee_info[1]] = self.get_rate_in_profit_currency(
                        asset=fee_info[1],
                        timestamp=timestamp,
                    )

        # Determine whether to use `out_price` or `in_price` for calculations
        price_to_use: Literal['in', 'out']
        if asset_out.is_fiat() and asset_out is not None:
            price_to_use = 'out'  # Use `out_price` if `asset_out` is fiat
        elif asset_in.is_fiat() and asset_in is not None:
            price_to_use = 'in'  # Use `in_price` if `asset_in` is fiat
        elif out_price is not None:
            price_to_use = 'out'  # Prefer `out_price` over `in_price`
        elif in_price is not None:
            price_to_use = 'in'
        else:  # Can't proceed if there is no price known
            return None

        if price_to_use == 'in':
            total_paid = amount_in * in_price  # type: ignore[operator]  # in_price is not None
        else:
            total_paid = amount_out * out_price  # type: ignore[operator]  # out_price is not None

        if asset_in.is_fiat():
            for fee_info in fees_info:
                if (fee_price := fee_asset_prices.get(fee_info[1])) is not None:
                    total_paid -= fee_price * fee_info[0]  # Subtract fee from cost basis

            calculated_out_price = Price(total_paid / amount_out)

            if price_to_use == 'in':
                calculated_in_price = in_price
            else:
                calculated_in_price = Price((amount_out * out_price) / amount_in)  # type: ignore[operator]  # out_price is not None

        else:  # if asset_out is fiat or both assets are crypto or both are fiat
            for fee_info in fees_info:
                if (fee_price := fee_asset_prices.get(fee_info[1])) is not None:
                    total_paid += fee_price * fee_info[0]  # Add fee to cost basis

            calculated_in_price = Price(total_paid / amount_in)

            if price_to_use == 'out':
                calculated_out_price = out_price  # type: ignore[assignment]  # out_price is not None
            else:
                calculated_out_price = Price((amount_in * in_price) / amount_out)  # type: ignore[operator]  # in_price is not None

        return (calculated_out_price, calculated_in_price)  # type: ignore[return-value]  # calculated_in_price is not None
