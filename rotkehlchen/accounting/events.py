import logging
from typing import Dict, Optional, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import BTC_BCH_FORK_TS, ETH_DAO_FORK_TS, ZERO
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETC, A_ETH
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnknownFromAsset
from rotkehlchen.exchanges.data_structures import BuyEvent, Events, MarginPosition, SellEvent
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Fee, Timestamp
from rotkehlchen.utils.misc import taxable_gain_for_sell, timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TaxableEvents():

    def __init__(self, csv_exporter: CSVExporter, profit_currency: Asset) -> None:
        self.events: Dict[Asset, Events] = dict()
        self.csv_exporter = csv_exporter
        self.profit_currency = profit_currency

        # If this flag is True when your asset is being forcefully sold as a
        # loan/margin settlement then profit/loss is also calculated before the entire
        # amount is taken as a loss
        self.count_profit_for_settlements = False

        self._taxfree_after_period = None
        self._include_crypto2crypto = None

    def reset(self, start_ts: Timestamp, end_ts: Timestamp) -> None:
        self.events = dict()
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.general_trade_profit_loss = FVal(0)
        self.taxable_trade_profit_loss = FVal(0)
        self.loan_profit = FVal(0)
        self.settlement_losses = FVal(0)
        self.margin_positions_profit_loss = FVal(0)

    @property
    def include_crypto2crypto(self) -> bool:
        return self._include_crypto2crypto

    @include_crypto2crypto.setter
    def include_crypto2crypto(self, value: bool) -> None:
        self._include_crypto2crypto = value

    @property
    def taxfree_after_period(self) -> Optional[int]:
        return self._taxfree_after_period

    @taxfree_after_period.setter
    def taxfree_after_period(self, value: Optional[int]) -> None:
        is_valid = isinstance(value, int) or value is None
        assert is_valid, 'set taxfree_after_period should only get int or None'
        self._taxfree_after_period = value

    def calculate_asset_details(self) -> Dict[Asset, Tuple[FVal, FVal]]:
        """ Calculates what amount of all assets has been untouched for a year and
        is hence tax-free and also the average buy price for each asset"""
        self.details: Dict[Asset, Tuple[FVal, FVal]] = dict()
        now = ts_now()
        for asset, events in self.events.items():
            tax_free_amount_left = ZERO
            amount_sum = ZERO
            average = ZERO
            for buy_event in events.buys:
                if self.taxfree_after_period is not None:
                    if buy_event.timestamp + self.taxfree_after_period < now:
                        tax_free_amount_left += buy_event.amount
                amount_sum += buy_event.amount
                average += buy_event.amount * buy_event.rate

            if amount_sum == ZERO:
                self.details[asset] = (ZERO, ZERO)
            else:
                self.details[asset] = (tax_free_amount_left, average / amount_sum)

        return self.details

    def get_rate_in_profit_currency(self, asset: Asset, timestamp: Timestamp) -> FVal:
        if asset == self.profit_currency:
            rate = FVal(1)
        else:
            rate = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=timestamp,
            )
        assert isinstance(rate, (FVal, int))  # TODO Remove. Is temporary assert
        return rate

    def reduce_asset_amount(self, asset: Asset, amount: FVal) -> bool:
        """Searches all buy events for asset and reduces them by amount
        Returns True if enough buy events to reduce the asset by amount were
        found and False otherwise.
        """
        # No need to do anything if amount is to be reduced by zero
        if amount == ZERO:
            return True

        if asset not in self.events or len(self.events[asset].buys) == 0:
            return False

        remaining_amount_from_last_buy = FVal('-1')
        remaining_amount = amount
        for idx, buy_event in enumerate(self.events[asset].buys):
            if remaining_amount < buy_event.amount:
                stop_index = idx
                remaining_amount_from_last_buy = buy_event.amount - remaining_amount
                # stop iterating since we found all buys to satisfy reduction
                break
            else:
                remaining_amount -= buy_event.amount
                if idx == len(self.events[asset].buys) - 1:
                    stop_index = idx + 1

        # Otherwise, delete all the used up buys from the list
        del self.events[asset].buys[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            self.events[asset].buys[0].amount = remaining_amount_from_last_buy
        elif remaining_amount != ZERO:
            return False

        return True

    def handle_prefork_asset_buys(
            self,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            fee_currency: Asset,
            timestamp: Timestamp,
    ) -> None:
        # TODO: Should fee also be taken into account here?
        if bought_asset == 'ETH' and timestamp < ETH_DAO_FORK_TS:
            self.add_buy(
                A_ETC,
                bought_amount,
                paid_with_asset,
                trade_rate,
                fee_in_profit_currency,
                fee_currency,
                timestamp,
                is_virtual=True,
            )

        if bought_asset == 'BTC' and timestamp < BTC_BCH_FORK_TS:
            # Acquiring BTC before the BCH fork provides equal amount of BCH
            self.add_buy(
                A_BCH,
                bought_amount,
                paid_with_asset,
                trade_rate,
                fee_in_profit_currency,
                fee_currency,
                timestamp,
                is_virtual=True,
            )

    def handle_prefork_asset_sells(
            self, sold_asset: Asset,
            sold_amount: FVal,
            timestamp: Timestamp,
    ) -> None:
        if sold_asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
            if not self.reduce_asset_amount(asset=A_ETC, amount=sold_amount):
                log.critical(
                    'No documented buy found for ETC (ETH equivalent) before {}'.format(
                        timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
                    ),
                )

        if sold_asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
            if not self.reduce_asset_amount(asset=A_BCH, amount=sold_amount):
                log.critical(
                    'No documented buy found for BCH (BTC equivalent) before {}'.format(
                        timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
                    ),
                )

    def add_buy_and_corresponding_sell(
            self,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            fee_currency: Asset,
            timestamp: Timestamp,
    ) -> None:
        self.add_buy(
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            fee_in_profit_currency=fee_in_profit_currency,
            fee_currency=fee_currency,
            timestamp=timestamp,
            is_virtual=False,
        )

        if paid_with_asset.is_fiat() or not self.include_crypto2crypto:
            return

        # else you are also selling some other asset to buy the bought asset
        log.debug(
            f'Buying {bought_asset} with {paid_with_asset} also introduces a virtual sell event',
        )
        try:
            bought_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(
                bought_asset,
                timestamp,
            )
        except (NoPriceForGivenTimestamp, PriceQueryUnknownFromAsset):
            bought_asset_rate_in_profit_currency = FVal(-1)

        if bought_asset_rate_in_profit_currency != FVal(-1):
            # The asset bought does not have a price yet
            # Can happen for Token sales, presales e.t.c.
            with_bought_asset_gain = bought_asset_rate_in_profit_currency * bought_amount
            receiving_asset = bought_asset
            receiving_amount = bought_amount
            rate_in_profit_currency = bought_asset_rate_in_profit_currency / trade_rate
            gain_in_profit_currency = with_bought_asset_gain

        sold_amount = trade_rate * bought_amount

        sold_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(
            paid_with_asset,
            timestamp,
        )
        with_sold_asset_gain = sold_asset_rate_in_profit_currency * sold_amount

        # Consider as value of the sell what would give the least profit
        if (bought_asset_rate_in_profit_currency == -1 or
                with_sold_asset_gain < with_bought_asset_gain):
            receiving_asset = self.profit_currency
            receiving_amount = with_sold_asset_gain
            trade_rate = sold_asset_rate_in_profit_currency
            rate_in_profit_currency = sold_asset_rate_in_profit_currency
            gain_in_profit_currency = with_sold_asset_gain

        self.add_sell(
            selling_asset=paid_with_asset,
            selling_amount=sold_amount,
            receiving_asset=receiving_asset,
            receiving_amount=receiving_amount,
            trade_rate=trade_rate,
            rate_in_profit_currency=rate_in_profit_currency,
            gain_in_profit_currency=gain_in_profit_currency,
            total_fee_in_profit_currency=fee_in_profit_currency,
            timestamp=timestamp,
            is_virtual=True,
        )

    def add_buy(
            self,
            bought_asset: Asset,
            bought_amount: FVal,
            paid_with_asset: Asset,
            trade_rate: FVal,
            fee_in_profit_currency: Fee,
            fee_currency: Asset,
            timestamp: Timestamp,
            is_virtual: bool = False,
    ) -> None:
        paid_with_asset_rate = self.get_rate_in_profit_currency(paid_with_asset, timestamp)
        buy_rate = paid_with_asset_rate * trade_rate

        self.handle_prefork_asset_buys(
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            fee_in_profit_currency=fee_in_profit_currency,
            fee_currency=fee_currency,
            timestamp=timestamp,
        )

        if bought_asset not in self.events:
            self.events[bought_asset] = Events(list(), list())

        gross_cost = bought_amount * buy_rate
        cost_in_profit_currency = gross_cost + fee_in_profit_currency

        self.events[bought_asset].buys.append(
            BuyEvent(
                amount=bought_amount,
                timestamp=timestamp,
                rate=buy_rate,
                fee_rate=fee_in_profit_currency / bought_amount,
            ),
        )
        log.debug(
            'Buy Event',
            sensitive_log=True,
            bought_amount=bought_amount,
            bought_asset=bought_asset,
            paid_with_asset=paid_with_asset,
            rate=trade_rate,
            rate_in_profit_currency=buy_rate,
            profit_currency=self.profit_currency,
            timestamp=timestamp,
        )

        if timestamp >= self.query_start_ts:
            self.csv_exporter.add_buy(
                bought_asset=bought_asset,
                rate=buy_rate,
                fee_cost=fee_in_profit_currency,
                amount=bought_amount,
                cost=cost_in_profit_currency,
                paid_with_asset=paid_with_asset,
                paid_with_asset_rate=paid_with_asset_rate,
                timestamp=timestamp,
                is_virtual=is_virtual,
            )

    def add_sell_and_corresponding_buy(
            self,
            selling_asset: Asset,
            selling_amount: FVal,
            receiving_asset: Asset,
            receiving_amount: FVal,
            gain_in_profit_currency: FVal,
            total_fee_in_profit_currency: Fee,
            trade_rate: FVal,
            rate_in_profit_currency: FVal,
            timestamp: Timestamp,
    ) -> None:
        """
        Add and process a selling event to the events list

        Args:
            selling_asset (str): The ticker representation of the asset we sell.
            selling_amount (FVal): The amount of `selling_asset` for sale.
            receiving_asset (str): The ticker representation of the asset we receive
                                   in exchange for `selling_asset`.
            receiving_amount (FVal): The amount of `receiving_asset` we receive.
            gain_in_profit_currency (FVal): This is the amount of `profit_currency` equivalent
                                            we receive after doing this trade. Fees are not counted
                                            in this.
            total_fee_in_profit_currency (FVal): This is the amount of `profit_currency` equivalent
                                                 we pay in fees after doing this trade.
            trade_rate (FVal): How much does 1 unit of `receiving_asset` cost in `selling_asset`
            rate_in_profit_currency (FVal): The equivalent of `trade_rate` in `profit_currency`
            timestamp (int): The timestamp for the trade
        """
        self.add_sell(
            selling_asset,
            selling_amount,
            receiving_asset,
            receiving_amount,
            gain_in_profit_currency,
            total_fee_in_profit_currency,
            trade_rate,
            rate_in_profit_currency,
            timestamp,
            is_virtual=False,
        )

        if receiving_asset.is_fiat() or not self.include_crypto2crypto:
            return

        log.debug(
            f'Selling {selling_asset} for {receiving_asset} also introduces a virtual buy event',
        )
        # else then you are also buying some other asset through your sell
        self.add_buy(
            bought_asset=receiving_asset,
            bought_amount=receiving_amount,
            paid_with_asset=selling_asset,
            trade_rate=1 / trade_rate,
            fee_in_profit_currency=total_fee_in_profit_currency,
            fee_currency=receiving_asset,  # does not matter
            timestamp=timestamp,
            is_virtual=True,
        )

    def add_sell(
            self,
            selling_asset: Asset,
            selling_amount: FVal,
            receiving_asset: Optional[Asset],
            receiving_amount: Optional[FVal],
            gain_in_profit_currency: FVal,
            total_fee_in_profit_currency: Fee,
            trade_rate: FVal,
            rate_in_profit_currency: FVal,
            timestamp: Timestamp,
            loan_settlement: bool = False,
            is_virtual: bool = False,
    ) -> None:

        if selling_asset not in self.events:
            self.events[selling_asset] = Events(list(), list())

        self.events[selling_asset].sells.append(
            SellEvent(
                amount=selling_amount,
                timestamp=timestamp,
                rate=rate_in_profit_currency,
                fee_rate=total_fee_in_profit_currency / selling_amount,
                gain=gain_in_profit_currency,
            ),
        )

        self.handle_prefork_asset_sells(selling_asset, selling_amount, timestamp)

        if loan_settlement:
            log.debug(
                'Loan Settlement Selling Event',
                sensitive_log=True,
                selling_amount=selling_amount,
                selling_asset=selling_asset,
                gain_in_profit_currency=gain_in_profit_currency,
                profit_currency=self.profit_currency,
                timestamp=timestamp,
            )
        else:
            log.debug(
                'Selling Event',
                sensitive_log=True,
                selling_amount=selling_amount,
                selling_asset=selling_asset,
                receiving_amount=receiving_amount,
                receiving_asset=receiving_asset,
                rate=trade_rate,
                rate_in_profit_currency=rate_in_profit_currency,
                profit_currency=self.profit_currency,
                gain_in_profit_currency=gain_in_profit_currency,
                fee_in_profit_currency=total_fee_in_profit_currency,
                timestamp=timestamp,
            )

        # now search the buys for `paid_with_asset` and calculate profit/loss
        (
            taxable_amount,
            taxable_bought_cost,
            taxfree_bought_cost,
        ) = self.search_buys_calculate_profit(
            selling_amount, selling_asset, timestamp,
        )
        general_profit_loss = ZERO
        taxable_profit_loss = ZERO

        # If we don't include crypto2crypto and we sell for crypto, stop here
        if receiving_asset and not receiving_asset.is_fiat() and not self.include_crypto2crypto:
            return

        # calculate profit/loss
        if not loan_settlement or (loan_settlement and self.count_profit_for_settlements):
            taxable_gain = taxable_gain_for_sell(
                taxable_amount=taxable_amount,
                rate_in_profit_currency=rate_in_profit_currency,
                total_fee_in_profit_currency=total_fee_in_profit_currency,
                selling_amount=selling_amount,
            )

            general_profit_loss = gain_in_profit_currency - (
                taxfree_bought_cost +
                taxable_bought_cost +
                total_fee_in_profit_currency
            )
            taxable_profit_loss = taxable_gain - taxable_bought_cost

        # should never happen, should be stopped at the main loop
        assert timestamp <= self.query_end_ts, (
            "Trade time > query_end_ts found in adding to sell event"
        )

        # count profit/losses if we are inside the query period
        if timestamp >= self.query_start_ts:
            if loan_settlement:
                # If it's a loan settlement we are charged both the fee and the gain
                settlement_loss = gain_in_profit_currency + total_fee_in_profit_currency
                expected = rate_in_profit_currency * selling_amount + total_fee_in_profit_currency
                msg = (
                    f'Expected settlement loss mismatch. rate_in_profit_currency'
                    f' ({rate_in_profit_currency}) * selling_amount'
                    f' ({selling_amount}) + total_fee_in_profit_currency'
                    f' ({total_fee_in_profit_currency}) != settlement_loss '
                    f'({settlement_loss})'
                )
                assert expected == settlement_loss, msg
                self.settlement_losses += settlement_loss
                log.debug(
                    'Loan Settlement Loss',
                    sensitive_log=True,
                    settlement_loss=settlement_loss,
                    profit_currency=self.profit_currency,
                )
            else:
                log.debug(
                    "After Sell Profit/Loss",
                    sensitive_log=True,
                    taxable_profit_loss=taxable_profit_loss,
                    general_profit_loss=general_profit_loss,
                    profit_currency=self.profit_currency,
                )

            self.general_trade_profit_loss += general_profit_loss
            self.taxable_trade_profit_loss += taxable_profit_loss

            if loan_settlement:
                self.csv_exporter.add_loan_settlement(
                    asset=selling_asset,
                    amount=selling_amount,
                    rate_in_profit_currency=rate_in_profit_currency,
                    total_fee_in_profit_currency=total_fee_in_profit_currency,
                    timestamp=timestamp,
                )
            else:
                assert receiving_asset, 'Here receiving asset should have a value'
                self.csv_exporter.add_sell(
                    selling_asset=selling_asset,
                    rate_in_profit_currency=rate_in_profit_currency,
                    total_fee_in_profit_currency=total_fee_in_profit_currency,
                    gain_in_profit_currency=gain_in_profit_currency,
                    selling_amount=selling_amount,
                    receiving_asset=receiving_asset,
                    receiving_amount=receiving_amount,
                    receiving_asset_rate_in_profit_currency=self.get_rate_in_profit_currency(
                        receiving_asset,
                        timestamp,
                    ),
                    taxable_amount=taxable_amount,
                    taxable_bought_cost=taxable_bought_cost,
                    timestamp=timestamp,
                    is_virtual=is_virtual,
                )

    def search_buys_calculate_profit(
            self,
            selling_amount: FVal,
            selling_asset: Asset,
            timestamp: Timestamp,
    ) -> Tuple[FVal, FVal, FVal]:
        """
        When selling `selling_amount` of `selling_asset` at `timestamp` this function
        calculates using the first-in-first-out rule the corresponding buy/s from
        which to do profit calculation. Also applies the one year rule after which
        a sell is not taxable in Germany.

        Returns a tuple of 3 values:
            - `taxable_amount`: The amount out of `selling_amount` that is taxable,
                                calculated from the 1 year rule.
            - `taxable_bought_cost`: How much it cost in `profit_currency` to buy
                                     the `taxable_amount`
            - `taxfree_bought_cost`: How much it cost in `profit_currency` to buy
                                     the taxfree_amount (selling_amount - taxable_amount)
        """
        remaining_sold_amount = selling_amount
        stop_index = -1
        taxfree_bought_cost = FVal(0)
        taxable_bought_cost = FVal(0)
        taxable_amount = FVal(0)
        taxfree_amount = FVal(0)
        remaining_amount_from_last_buy = FVal('-1')
        for idx, buy_event in enumerate(self.events[selling_asset].buys):
            if self.taxfree_after_period is None:
                at_taxfree_period = False
            else:
                at_taxfree_period = (
                    buy_event.timestamp + self.taxfree_after_period < timestamp
                )

            if remaining_sold_amount < buy_event.amount:
                stop_index = idx
                buying_cost = remaining_sold_amount.fma(
                    buy_event.rate,
                    (buy_event.fee_rate * remaining_sold_amount),
                )

                if at_taxfree_period:
                    taxfree_amount += remaining_sold_amount
                    taxfree_bought_cost += buying_cost
                else:
                    taxable_amount += remaining_sold_amount
                    taxable_bought_cost += buying_cost

                remaining_amount_from_last_buy = buy_event.amount - remaining_sold_amount
                log.debug(
                    'Sell uses up part of historical buy',
                    sensitive_log=True,
                    tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                    used_amount=remaining_sold_amount,
                    from_amount=buy_event.amount,
                    asset=selling_asset,
                    trade_buy_rate=buy_event.rate,
                    profit_currency=self.profit_currency,
                    trade_timestamp=buy_event.timestamp,
                )
                # stop iterating since we found all buys to satisfy this sell
                break
            else:
                buying_cost = buy_event.amount.fma(
                    buy_event.rate,
                    (buy_event.fee_rate * buy_event.amount),
                )
                remaining_sold_amount -= buy_event.amount
                if at_taxfree_period:
                    taxfree_amount += buy_event.amount
                    taxfree_bought_cost += buying_cost
                else:
                    taxable_amount += buy_event.amount
                    taxable_bought_cost += buying_cost

                log.debug(
                    'Sell uses up entire historical buy',
                    sensitive_log=True,
                    tax_status='TAX-FREE' if at_taxfree_period else 'TAXABLE',
                    bought_amount=buy_event.amount,
                    asset=selling_asset,
                    trade_buy_rate=buy_event.rate,
                    profit_currency=self.profit_currency,
                    trade_timestamp=buy_event.timestamp,
                )

                # If the sell used up the last historical buy
                if idx == len(self.events[selling_asset].buys) - 1:
                    stop_index = idx + 1

        if len(self.events[selling_asset].buys) == 0:
            log.critical(
                'No documented buy found for "{}" before {}'.format(
                    selling_asset,
                    timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
                ),
            )
            # That means we had no documented buy for that asset. This is not good
            # because we can't prove a corresponding buy and as such we are burdened
            # calculating the entire sell as profit which needs to be taxed
            return selling_amount, FVal(0), FVal(0)

        # Otherwise, delete all the used up buys from the list
        del self.events[selling_asset].buys[:stop_index]
        # and modify the amount of the buy where we stopped if there is one
        if remaining_amount_from_last_buy != FVal('-1'):
            self.events[selling_asset].buys[0].amount = remaining_amount_from_last_buy
        elif remaining_sold_amount != ZERO:
            # if we still have sold amount but no buys to satisfy it then we only
            # found buys to partially satisfy the sell
            adjusted_amount = selling_amount - taxfree_amount
            log.critical(
                'Not enough documented buys found for "{}" before {}.'
                'Only found buys for {} {}'.format(
                    selling_asset,
                    timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
                    taxable_amount + taxfree_amount,
                    selling_asset,
                ),
            )
            return adjusted_amount, taxable_bought_cost, taxfree_bought_cost

        return taxable_amount, taxable_bought_cost, taxfree_bought_cost

    def add_loan_gain(
            self,
            gained_asset: Asset,
            gained_amount: FVal,
            fee_in_asset: Fee,
            lent_amount: FVal,
            open_time: Timestamp,
            close_time: Timestamp,
    ) -> None:

        timestamp = close_time
        rate = self.get_rate_in_profit_currency(gained_asset, timestamp)

        if gained_asset not in self.events:
            self.events[gained_asset] = Events(list(), list())

        net_gain_amount = gained_amount - fee_in_asset
        gain_in_profit_currency = net_gain_amount * rate
        assert gain_in_profit_currency > 0, "Loan profit is negative. Should never happen"
        self.events[gained_asset].buys.append(
            BuyEvent(
                amount=net_gain_amount,
                timestamp=timestamp,
                rate=rate,
                fee_rate=ZERO,
            ),
        )
        # count profits if we are inside the query period
        if timestamp >= self.query_start_ts:
            log.debug(
                'Accounting for loan profit',
                sensitive_log=True,
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

            self.loan_profit += gain_in_profit_currency
            self.csv_exporter.add_loan_profit(
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

    def add_margin_position(self, margin: MarginPosition) -> None:
        if margin.pl_currency not in self.events:
            self.events[margin.pl_currency] = Events(list(), list())
        if margin.fee_currency not in self.events:
            self.events[margin.fee_currency] = Events(list(), list())

        pl_currency_rate = self.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)
        fee_currency_rate = self.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)
        net_gain_loss_in_profit_currency = (
            margin.profit_loss * pl_currency_rate - margin.fee * fee_currency_rate
        )

        # Add or remove to the pl_currency asset
        if margin.profit_loss > 0:
            self.events[margin.pl_currency].buys.append(
                BuyEvent(
                    amount=margin.profit_loss,
                    timestamp=margin.close_time,
                    rate=pl_currency_rate,
                    fee_rate=ZERO,
                ),
            )
        elif margin.profit_loss < 0:
            result = self.reduce_asset_amount(
                asset=margin.pl_currency,
                amount=-margin.profit_loss,
            )
            if not result:
                log.critical(
                    f'No documented buy found for {margin.pl_currency} before '
                    f'{timestamp_to_date(margin.close_time, formatstr="%d/%m/%Y %H:%M:%S")}',
                )

        # Reduce the fee_currency asset
        result = self.reduce_asset_amount(asset=margin.fee_currency, amount=margin.fee)
        if not result:
            log.critical(
                f'No documented buy found for {margin.fee_currency} before '
                f'{timestamp_to_date(margin.close_time, formatstr="%d/%m/%Y %H:%M:%S")}',
            )

        # count profit/loss if we are inside the query period
        if margin.close_time >= self.query_start_ts:
            self.margin_positions_profit_loss += net_gain_loss_in_profit_currency

            log.debug(
                'Accounting for margin position',
                sensitive_log=True,
                notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                net_gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
            )

            self.csv_exporter.add_margin_position(
                margin_notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
            )
