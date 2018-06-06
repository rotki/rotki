from rotkehlchen.utils import tsToDate, ts_now, taxable_gain_for_sell
from rotkehlchen.order_formatting import (
    Events,
    BuyEvent,
    SellEvent,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history import (
    NoPriceForGivenTimestamp,
    PriceQueryUnknownFromAsset,
    FIAT_CURRENCIES
)
from rotkehlchen.constants import ETH_DAO_FORK_TS, BTC_BCH_FORK_TS

import logging
logger = logging.getLogger(__name__)


class TaxableEvents(object):

    def __init__(self, price_historian, csv_exporter, profit_currency):
        self.events = dict()
        self.price_historian = price_historian
        self.csv_exporter = csv_exporter
        self.profit_currency = profit_currency

        # If this flag is True when your asset is being forcefully sold as a
        # loan/margin settlement then profit/loss is also calculated before the entire
        # amount is taken as a loss
        self.count_profit_for_settlements = False

    def reset(self, start_ts, end_ts):
        self.events = dict()
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts
        self.general_trade_profit_loss = FVal(0)
        self.taxable_trade_profit_loss = FVal(0)
        self.loan_profit = FVal(0)
        self.settlement_losses = FVal(0)
        self.margin_positions_profit = FVal(0)

    @property
    def include_crypto2crypto(self):
        return self._include_crypto2crypto

    @include_crypto2crypto.setter
    def include_crypto2crypto(self, value):
        self._include_crypto2crypto = value

    @property
    def taxfree_after_period(self):
        return self._taxfree_after_period

    @taxfree_after_period.setter
    def taxfree_after_period(self, value):
        assert isinstance(value, int), 'set taxfree_after_period should only get int'
        self._taxfree_after_period = value

    def calculate_asset_details(self):
        """ Calculates what amount of all assets has been untouched for a year and
        is hence tax-free and also the average buy price for each asset"""
        self.details = dict()
        now = ts_now()
        for asset, events in self.events.items():
            tax_free_amount_left = 0
            amount_sum = 0
            average = 0
            for buy_event in events.buys:
                if self.taxfree_after_period is not None:
                    if buy_event.timestamp + self.taxfree_after_period < now:
                        tax_free_amount_left += buy_event.amount
                amount_sum += buy_event.amount
                average += buy_event.amount * buy_event.rate

            if amount_sum == 0:
                self.details[asset] = (0, 0)
            else:
                self.details[asset] = (tax_free_amount_left, average / amount_sum)

        return self.details

    def get_rate_in_profit_currency(self, asset, timestamp):
        if asset == self.profit_currency:
            rate = 1
        else:
            rate = self.price_historian.query_historical_price(
                asset,
                self.profit_currency,
                timestamp
            )
        assert isinstance(rate, (FVal, int))  # TODO Remove. Is temporary assert
        return rate

    def handle_prefork_acquisitions(
            self,
            bought_asset,
            bought_amount,
            paid_with_asset,
            trade_rate,
            trade_fee,
            fee_currency,
            timestamp
    ):
        # TODO: Should fee also be taken into account here?
        if bought_asset == 'ETH' and timestamp < ETH_DAO_FORK_TS:
            # Acquiring ETH before the DAO fork provides equal amount of ETC
            self.add_buy(
                'ETC',
                bought_amount,
                paid_with_asset,
                trade_rate,
                0,
                fee_currency,
                timestamp,
                is_virtual=True
            )

        if bought_asset == 'BTC' and timestamp < BTC_BCH_FORK_TS:
            # Acquiring BTC before the BCH fork provides equal amount of BCH
            self.add_buy(
                'BCH',
                bought_amount,
                paid_with_asset,
                trade_rate,
                0,
                fee_currency,
                timestamp,
                is_virtual=True
            )

    def add_buy_and_corresponding_sell(
            self,
            bought_asset,
            bought_amount,
            paid_with_asset,
            trade_rate,
            trade_fee,
            fee_currency,
            timestamp
    ):

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('\nBUY EVENT:')

        self.add_buy(
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            trade_fee=trade_fee,
            fee_currency=fee_currency,
            timestamp=timestamp,
            is_virtual=False,
        )

        if paid_with_asset in FIAT_CURRENCIES or not self.include_crypto2crypto:
            return

        # else you are also selling some other asset to buy the bought asset
        try:
            bought_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(
                bought_asset,
                timestamp
            )
        except (NoPriceForGivenTimestamp, PriceQueryUnknownFromAsset):
            bought_asset_rate_in_profit_currency = -1

        if bought_asset_rate_in_profit_currency != -1:
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
            timestamp
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

        # add the fee
        fee_rate = self.get_rate_in_profit_currency(fee_currency, timestamp)
        fee_in_profit_currency = fee_rate * trade_fee

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
            bought_asset,
            bought_amount,
            paid_with_asset,
            trade_rate,
            trade_fee,
            fee_currency,
            timestamp,
            is_virtual=False
    ):

        paid_with_asset_rate = self.get_rate_in_profit_currency(paid_with_asset, timestamp)
        buy_rate = paid_with_asset_rate * trade_rate
        fee_price_in_profit_currency = 0
        if trade_fee != 0:
            fee_price_in_profit_currency = self.price_historian.query_historical_price(
                fee_currency,
                self.profit_currency,
                timestamp
            )

        self.handle_prefork_acquisitions(
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            trade_fee=trade_fee,
            fee_currency=fee_currency,
            timestamp=timestamp
        )

        if bought_asset not in self.events:
            self.events[bought_asset] = Events(list(), list())

        fee_cost = fee_price_in_profit_currency * trade_fee
        gross_cost = bought_amount * buy_rate
        cost = gross_cost + fee_cost

        self.events[bought_asset].buys.append(
            BuyEvent(
                amount=bought_amount,
                timestamp=timestamp,
                rate=buy_rate,
                fee_rate=fee_cost / bought_amount,
                cost=cost
            )
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                'Buying {} "{}" for {} "{}" ({} "{}" per "{}" or {} "{}" per '
                '"{}") at {}'.format(
                    bought_amount,
                    bought_asset,
                    bought_amount * trade_rate,
                    paid_with_asset,
                    trade_rate,
                    paid_with_asset,
                    bought_asset,
                    buy_rate,
                    self.profit_currency,
                    bought_asset,
                    tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S')
                )
            )

        self.csv_exporter.add_buy(
            bought_asset=bought_asset,
            rate=buy_rate,
            fee_cost=fee_cost,
            amount=bought_amount,
            gross_cost=gross_cost,
            cost=cost,
            paid_with_asset=paid_with_asset,
            paid_with_asset_rate=paid_with_asset_rate,
            timestamp=timestamp,
            is_virtual=is_virtual,
        )

    def add_sell_and_corresponding_buy(
            self,
            selling_asset,
            selling_amount,
            receiving_asset,
            receiving_amount,
            gain_in_profit_currency,
            total_fee_in_profit_currency,
            trade_rate,
            rate_in_profit_currency,
            timestamp):
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

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('\nSELL EVENT:')

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

        if receiving_asset in FIAT_CURRENCIES or not self.include_crypto2crypto:
            return

        # else then you are also buying some other asset through your sell
        # TODO: Account for trade fees in the virtual buy too
        self.add_buy(
            bought_asset=receiving_asset,
            bought_amount=receiving_amount,
            paid_with_asset=selling_asset,
            trade_rate=1 / trade_rate,
            trade_fee=0,
            fee_currency=receiving_amount,  # does not matter
            timestamp=timestamp,
            is_virtual=True,
        )

    def add_sell(
            self,
            selling_asset,
            selling_amount,
            receiving_asset,
            receiving_amount,
            gain_in_profit_currency,
            total_fee_in_profit_currency,
            trade_rate,
            rate_in_profit_currency,
            timestamp,
            loan_settlement=False,
            is_virtual=False):

        if selling_asset not in self.events:
            self.events[selling_asset] = Events(list(), list())

        self.events[selling_asset].sells.append(
            SellEvent(
                amount=selling_amount,
                timestamp=timestamp,
                rate=rate_in_profit_currency,
                fee_rate=total_fee_in_profit_currency / selling_amount,
                gain=gain_in_profit_currency,
            )
        )

        debug_enabled = logger.isEnabledFor(logging.DEBUG)
        if debug_enabled:
            if loan_settlement:
                logger.debug('Loan Settlement Selling {} of "{}" for {} "{}" at {}'.format(
                    selling_amount,
                    selling_asset,
                    gain_in_profit_currency,
                    self.profit_currency,
                    tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S')
                ))
            else:
                logger.debug(
                    'Selling {} of "{}" for {} "{}" ({} "{}" per "{}" or {} "{}" '
                    'per "{}") for a gain of {} "{}" and a fee of {} "{} at {}'.format(
                        selling_amount,
                        selling_asset,
                        receiving_amount,
                        receiving_asset,
                        trade_rate,
                        receiving_asset,
                        selling_asset,
                        rate_in_profit_currency,
                        self.profit_currency,
                        selling_asset,
                        gain_in_profit_currency,
                        self.profit_currency,
                        total_fee_in_profit_currency,
                        self.profit_currency,
                        tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S')
                    ))

        # now search the buys for `paid_with_asset` and  calculate profit/loss
        (
            taxable_amount,
            taxable_bought_cost,
            taxfree_bought_cost
        ) = self.search_buys_calculate_profit(
            selling_amount, selling_asset, timestamp
        )
        general_profit_loss = 0
        taxable_profit_loss = 0

        # If we don't include crypto2crypto and we sell for crypto, stop here
        if receiving_asset not in FIAT_CURRENCIES and not self.include_crypto2crypto:
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
                self.settlement_losses += settlement_loss
                if debug_enabled:
                    logger.debug("Loan Settlement Loss: {} {}".format(
                        settlement_loss, self.profit_currency
                    ))
            elif debug_enabled:
                logger.debug("Taxable P/L: {} {} General P/L: {} {}".format(
                    taxable_profit_loss,
                    self.profit_currency,
                    general_profit_loss,
                    self.profit_currency,
                ))

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

    def search_buys_calculate_profit(self, selling_amount, selling_asset, timestamp):
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
        taxfree_bought_cost = 0
        taxable_bought_cost = 0
        taxable_amount = 0
        taxfree_amount = 0
        debug_enabled = logger.isEnabledFor(logging.DEBUG)
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
                    - (buy_event.fee_rate * remaining_sold_amount)
                )

                if at_taxfree_period:
                    taxfree_amount += remaining_sold_amount
                    taxfree_bought_cost += buying_cost
                else:
                    taxable_amount += remaining_sold_amount
                    taxable_bought_cost += buying_cost

                remaining_amount_from_last_buy = buy_event.amount - remaining_sold_amount
                if debug_enabled:
                    logger.debug(
                        '[{}] Using up {}/{} "{}" from the buy for {} "{}" per "{}"  at {}'.format(
                            'TAX-FREE' if at_taxfree_period else 'TAXABLE',
                            remaining_sold_amount,
                            buy_event.amount,
                            selling_asset,
                            buy_event.rate,
                            self.profit_currency,
                            selling_asset,
                            tsToDate(buy_event.timestamp, formatstr='%d/%m/%Y %H:%M:%S')
                        ))
                # stop iterating since we found all buys to satisfy this sell
                break
            else:
                remaining_sold_amount -= buy_event.amount
                if at_taxfree_period:
                    taxfree_amount += buy_event.amount
                    taxfree_bought_cost += buy_event.cost
                else:
                    taxable_amount += buy_event.amount
                    taxable_bought_cost += buy_event.cost

                if debug_enabled:
                    logger.debug(
                        '[{}] Using up the entire buy of {} "{}" for {} "{}" per {} at {}'.format(
                            'TAX-FREE' if at_taxfree_period else 'TAXABLE',
                            buy_event.amount,
                            selling_asset,
                            buy_event.rate,
                            self.profit_currency,
                            selling_asset,
                            tsToDate(buy_event.timestamp, formatstr='%d/%m/%Y %H:%M:%S')
                        ))

        if stop_index == -1:
            logger.critical('No documented buy found for "{}" before {}'.format(
                selling_asset, tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S')
            ))
            # That means we had no documented buy for that asset. This is not good
            # because we can't prove a corresponding buy and as such we are burdened
            # calculating the entire sell as profit which needs to be taxed
            return selling_amount, 0, 0

        # Otherwise, delete all the used up buys from the list
        del self.events[selling_asset].buys[:stop_index]
        # and modify the amount of the buy where we stopped
        self.events[selling_asset].buys[0] = self.events[selling_asset].buys[0]._replace(
            amount=remaining_amount_from_last_buy
        )

        return taxable_amount, taxable_bought_cost, taxfree_bought_cost

    def add_loan_gain(
            self,
            gained_asset,
            gained_amount,
            fee_in_asset,
            lent_amount,
            open_time,
            close_time
    ):

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
                fee_rate=0,
                cost=0
            )
        )
        # count profits if we are inside the query period
        if timestamp >= self.query_start_ts:
            self.loan_profit += gain_in_profit_currency

            self.csv_exporter.add_loan_profit(
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

    def add_margin_position(
            self,
            gained_asset,
            gained_amount,
            fee_in_asset,
            margin_notes,
            timestamp):

        rate = self.get_rate_in_profit_currency(gained_asset, timestamp)

        if gained_asset not in self.events:
            self.events[gained_asset] = Events(list(), list())

        net_gain_amount = gained_amount - fee_in_asset
        gain_in_profit_currency = net_gain_amount * rate
        assert gain_in_profit_currency > 0, (
            'Margin profit is negative. Should never happen for the hacky way I use em now'
        )
        self.events[gained_asset].buys.append(
            BuyEvent(
                amount=net_gain_amount,
                timestamp=timestamp,
                rate=rate,
                fee_rate=0,
                cost=0
            )
        )
        # count profits if we are inside the query period
        if timestamp >= self.query_start_ts:
            self.margin_positions_profit += gain_in_profit_currency

        self.csv_exporter.add_margin_position(
            margin_notes=margin_notes,
            gained_asset=gained_asset,
            net_gain_amount=net_gain_amount,
            gain_in_profit_currency=gain_in_profit_currency,
            timestamp=timestamp,
        )
