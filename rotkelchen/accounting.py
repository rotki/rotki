from utils import tsToDate, ts_now
from order_formatting import (
    Events,
    BuyEvent,
    SellEvent,
    trade_get_other_pair,
    trade_get_assets
)


FIAT_CURRENCIES = ('EUR', 'USD', 'GBP', 'JPY', 'CNY')
YEAR_IN_SECONDS = 31536000  # 60 * 60 * 24 * 365


class Accountant(object):

    def __init__(
            self,
            logger,
            price_historian,
            profit_currency,
            ignored_assets=['DAO']):

        self.log = logger
        self.price_historian = price_historian
        self.set_profit_currency(profit_currency)
        self.ignored_assets = ignored_assets

        self.general_profit_loss = 0
        self.taxable_profit_loss = 0

    def set_profit_currency(self, currency):
        if currency not in FIAT_CURRENCIES:
            raise ValueError(
                'Attempted to set unsupported "{}" as main currency.'.format(currency)
            )

        self.profit_currency = currency

    def query_historical_price(self, from_asset, to_asset, timestamp):
        return self.price_historian.query_historical_price(from_asset, to_asset, timestamp)

    def get_rate_in_profit_currency(self, asset, timestamp):
        if asset == self.profit_currency:
            rate = 1
        else:
            rate = self.query_historical_price(
                asset,
                self.profit_currency,
                timestamp
            )
        return rate

    def add_buy_to_events(
            self,
            bought_asset,
            bought_amount,
            paid_with_asset,
            trade_rate,
            trade_fee,
            fee_currency,
            timestamp):

        paid_with_asset_rate = self.get_rate_in_profit_currency(paid_with_asset, timestamp)
        buy_rate = paid_with_asset_rate * trade_rate
        fee_price_in_profit_currency = 0
        if trade_fee != 0:
            fee_price_in_profit_currency = self.query_historical_price(
                fee_currency,
                self.profit_currency,
                timestamp
            )

        if bought_asset not in self.events:
            self.events[bought_asset] = Events(list(), list())

        fee_cost = fee_price_in_profit_currency * trade_fee
        cost = bought_amount * buy_rate + fee_cost
        self.events[bought_asset].buys.append(
            BuyEvent(
                amount=bought_amount,
                timestamp=timestamp,
                rate=buy_rate,
                fee_rate=fee_cost / bought_amount,
                cost=cost
            )
        )
        self.log.logdebug('Buying {} "{}" for {} "{}" ({} "{}" per "{}" or {} "{}" per "{}") at {}'.format(            
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
            tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
        ))

    def add_buy_to_events_and_corresponding_sell(
            self,
            bought_asset,
            bought_amount,
            paid_with_asset,
            trade_rate,
            trade_fee,
            fee_currency,
            timestamp):

        self.log.logdebug('\nBUY EVENT:')
        self.add_buy_to_events(
            bought_asset=bought_asset,
            bought_amount=bought_amount,
            paid_with_asset=paid_with_asset,
            trade_rate=trade_rate,
            trade_fee=trade_fee,
            fee_currency=fee_currency,
            timestamp=timestamp
        )

        if paid_with_asset not in FIAT_CURRENCIES:
            # then you are also selling some other asset to buy the bought asset
            bought_asset_rate_in_profit_currency = self.get_rate_in_profit_currency(bought_asset, timestamp)
            sold_amount = trade_rate * bought_amount
            # TODO: Here also check if the fee_currency is same as paid with asset
            #       and then add it to the sold_amount
            self.add_sell_to_events(
                selling_asset=paid_with_asset,
                selling_amount=sold_amount,
                receiving_asset=bought_asset,
                receiving_amount=bought_amount,
                # trade_rate=1 / trade_rate,
                trade_rate=trade_rate,
                rate_in_profit_currency=bought_asset_rate_in_profit_currency / trade_rate,
                # rate_in_profit_currency=bought_asset_rate_in_profit_currency,
                gain_in_profit_currency=bought_asset_rate_in_profit_currency * bought_amount,
                total_fee_in_profit_currency=0,  # fee is done on the buy if at all
                timestamp=timestamp,
            )

    def add_sell_to_events(
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

        self.log.logdebug('Selling {} of "{}" for {} "{}" ({} "{}" per "{}" or {} "{}" per "{}") for total gain of {} "{}" at {}'.format(
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
            tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
        ))

        # now search the buys for `paid_with_asset` and  calculate profit/loss
        remaining_sold_amount = selling_amount
        stop_index = -1
        taxfree_bought_cost = 0
        taxable_bought_cost = 0
        taxable_amount = 0
        taxfree_amount = 0
        for idx, buy_event in enumerate(self.events[selling_asset].buys):
            sell_after_year = buy_event.timestamp + YEAR_IN_SECONDS < timestamp

            if remaining_sold_amount < buy_event.amount:
                stop_index = idx
                buying_cost = (
                    remaining_sold_amount * buy_event.rate +
                    buy_event.fee_rate * remaining_sold_amount
                )
                if sell_after_year:
                    taxfree_amount += remaining_sold_amount
                    taxfree_bought_cost += buying_cost
                else:
                    taxable_amount += remaining_sold_amount
                    taxable_bought_cost += buying_cost

                remaining_amount_from_last_buy = buy_event.amount - remaining_sold_amount
                self.log.logdebug(
                    '[{}] Using up {}/{} "{}" from the buy for {} "{}" per "{}"  at {}'.format(
                        'TAX-FREE' if sell_after_year else 'TAXABLE',
                        remaining_sold_amount,
                        buy_event.amount,
                        selling_asset,
                        buy_event.rate,
                        self.profit_currency,
                        selling_asset,
                        tsToDate(buy_event.timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
                    ))
                # stop iterating since we found all buys to satisfy this sell
                break
            else:
                remaining_sold_amount -= buy_event.amount
                if sell_after_year:
                    taxfree_amount += buy_event.amount
                    taxfree_bought_cost += buy_event.cost
                else:
                    taxable_amount += buy_event.amount
                    taxable_bought_cost += buy_event.cost

                self.log.logdebug(
                    '[{}] Using up the entire buy of {} "{}" for {} "{}" per {} at {}'.format(
                        'TAX-FREE' if sell_after_year else 'TAXABLE',
                        buy_event.amount,
                        selling_asset,
                        buy_event.rate,
                        self.profit_currency,
                        selling_asset,
                        tsToDate(buy_event.timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
                    ))

        if stop_index == -1:
            self.log.logdebug('No documented buy found for "{}" before {}'.format(
                selling_asset, tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
            ))
            # That means we had no documented buy for that asset.
            # It can happen, so for this sell no profit/loss is calculated.
            return

        # Otherwise, delete all the used up buys from the list
        del self.events[selling_asset].buys[:stop_index]
        # and modify the amount of the buy where we stopped
        self.events[selling_asset].buys[0] = self.events[selling_asset].buys[0]._replace(
            amount=remaining_amount_from_last_buy
        )

        # and then calculate profit/loss
        taxable_gain = (
            rate_in_profit_currency * taxable_amount -
            total_fee_in_profit_currency * (taxable_amount / selling_amount)
        )

        general_profit_loss = gain_in_profit_currency - (taxfree_bought_cost + taxable_bought_cost)
        taxable_profit_loss = taxable_gain - taxable_bought_cost
        self.general_profit_loss += general_profit_loss
        self.taxable_profit_loss += taxable_profit_loss
        self.log.logdebug('General Profit/Loss: {}\nTaxable Profit/Loss:{}'.format(
            general_profit_loss,
            taxable_profit_loss
        ))

    def add_sell_to_events_and_corresponding_buy(
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

        self.log.logdebug('\nSELL EVENT:')
        self.add_sell_to_events(
            selling_asset,
            selling_amount,
            receiving_asset,
            receiving_amount,
            gain_in_profit_currency,
            total_fee_in_profit_currency,
            trade_rate,
            rate_in_profit_currency,
            timestamp
        )

        if receiving_asset not in FIAT_CURRENCIES:
            # then you are also buying some other asset through your sell
            self.add_buy_to_events(
                bought_asset=receiving_asset,
                bought_amount=receiving_amount,
                paid_with_asset=selling_asset,
                # For polo corresponding buy to a sell you must not invert this
                trade_rate=1 / trade_rate,
                # trade_rate=trade_rate,
                trade_fee=0,  # fee should have already been acccounted on the sell side
                fee_currency=receiving_amount,  # does not matter
                timestamp=timestamp
            )

    def save_events(self):
        for asset, events in self.events.iteritems():
            pass

    def calculate_asset_details(self):
        """ Calculates what amount of all assets has been untouched for a year and
        is hence tax-free and also the average buy price for each asset"""
        self.details = dict()
        now = ts_now()
        for asset, events in self.events.iteritems():
            tax_free_amount_left = 0
            amount_sum = 0
            average = 0
            for buy_event in events.buys:
                if buy_event.timestamp + YEAR_IN_SECONDS < now:
                    tax_free_amount_left += buy_event.amount
                amount_sum += buy_event.amount
                average += buy_event.amount * buy_event.rate
            self.details[asset] = (tax_free_amount_left, average / amount_sum)
        return self.details

    def process_history(self, history):
        self.events = dict()
        self.general_profit_loss = 0
        self.taxable_profit_loss = 0

        for trade in history:
            asset1, asset2 = trade_get_assets(trade)
            if asset1 in self.ignored_assets or asset2 in self.ignored_assets:
                print("Ignoring trade with {} {}".format(asset1, asset2))
                continue

            # When you buy, you buy with the cost_currency and receive the other one
            # When you sell, you sell the amount in non-cost_currency and receive costs in cost_currency
            if trade.type == 'buy':
                self.add_buy_to_events_and_corresponding_sell(
                    bought_asset=trade_get_other_pair(trade, trade.cost_currency),
                    bought_amount=trade.amount,
                    paid_with_asset=trade.cost_currency,
                    trade_rate=trade.rate,
                    trade_fee=trade.fee,
                    fee_currency=trade.fee_currency,
                    timestamp=trade.timestamp
                )
            elif trade.type == 'sell':
                selling_asset = trade_get_other_pair(trade, trade.cost_currency)
                selling_asset_rate = self.get_rate_in_profit_currency(
                    trade.cost_currency,
                    trade.timestamp
                )
                selling_rate = selling_asset_rate * trade.rate
                fee_rate = self.query_historical_price(
                    trade.fee_currency,
                    self.profit_currency,
                    trade.timestamp
                )
                total_sell_fee_cost = fee_rate * trade.fee
                gain_in_profit_currency = selling_rate * trade.amount - total_sell_fee_cost

                self.add_sell_to_events_and_corresponding_buy(
                    selling_asset=selling_asset,
                    selling_amount=trade.amount,
                    receiving_asset=trade.cost_currency,
                    receiving_amount=trade.cost,
                    gain_in_profit_currency=gain_in_profit_currency,
                    total_fee_in_profit_currency=total_sell_fee_cost,
                    trade_rate=trade.rate,
                    rate_in_profit_currency=selling_rate,
                    timestamp=trade.timestamp
                )
            else:
                raise ValueError('Unknown trade type "{}" encountered'.format(trade.type))

        self.calculate_asset_details()

        return 'Taxable Profit/Loss: {} "{}"\nProfit/Loss: {} "{}"'.format(
            self.taxable_profit_loss,
            self.profit_currency,
            self.general_profit_loss,
            self.profit_currency,
        )
