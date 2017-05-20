import json
import time
import urllib2
import os
import glob
import re
from itertools import izip

from kraken import kraken_to_world_pair
from utils import createTimeStamp, tsToDate, ts_now, get_pair_position
from order_formatting import Trade


DEFAULT_START_DATE = "01/08/2015"
TRADES_HISTORYFILE = 'trades_history.json'


def trade_from_kraken(kraken_trade):
    """Turn a kraken trade returned from kraken trade history to our common trade
    history format"""
    currency_pair = kraken_to_world_pair(kraken_trade['pair'])
    quote_currency = get_pair_position(currency_pair, 'second')
    return Trade(
        timestamp=int(kraken_trade['time']),
        pair=currency_pair,
        type=kraken_trade['type'],
        rate=float(kraken_trade['price']),
        cost=float(kraken_trade['cost']),
        cost_currency=quote_currency,
        fee=float(kraken_trade['fee']),
        fee_currency=quote_currency,
        amount=float(kraken_trade['vol']),
        location='kraken'
    )


def trade_from_poloniex(poloniex_trade, pair):
    """Turn a poloniex trade returned from poloniex trade history to our common trade
    history format"""

    trade_type = poloniex_trade['type']
    amount = float(poloniex_trade['amount'])
    rate = float(poloniex_trade['rate'])
    perc_fee = float(poloniex_trade['fee'])
    base_currency = get_pair_position(pair, 'first')
    quote_currency = get_pair_position(pair, 'second')
    if trade_type == 'buy':
        cost = rate * amount
        cost_currency = base_currency
        fee = amount * perc_fee
        fee_currency = quote_currency
    elif trade_type == 'sell':
        cost = amount * rate
        cost_currency = base_currency
        fee = cost * perc_fee
        fee_currency = base_currency
    else:
        raise ValueError('Got unexpected trade type "{}" for poloniex trade'.format(trade_type))

    return Trade(
        timestamp=createTimeStamp(poloniex_trade['date'], formatstr="%Y-%m-%d %H:%M:%S"),
        pair=pair,
        type=trade_type,
        rate=rate,
        cost=cost,
        cost_currency=cost_currency,
        fee=fee,
        fee_currency=fee_currency,
        amount=amount,
        location='poloniex'
    )


def trades_from_dictlist(given_trades):
    returned_trades = list()
    for given_trade in given_trades:
        returned_trades.append(Trade(
            timestamp=given_trade['timestamp'],
            pair=given_trade['pair'],
            type=given_trade['type'],
            rate=float(given_trade['rate']),
            cost=float(given_trade['cost']),
            cost_currency=given_trade['cost_currency'],
            fee=float(given_trade['fee']),
            fee_currency=given_trade['fee_currency'],
            amount=float(given_trade['amount']),
            location=given_trade['location']
        ))
    return returned_trades


def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)


def check_hourly_data_sanity(data):
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['time'] - n1['time']
        if diff != 3600:
            print(
                "Problem at indices {} and {}. Time difference is: {}".format(
                    index, index + 1, diff)
            )
            return False
        index += 2
    return True


class PriceHistorian(object):

    def __init__(self, data_directory, personal_data):
        self.data_directory = data_directory
        # get the start date for historical data
        history_date_start = DEFAULT_START_DATE
        if 'historical_data_start_date' in personal_data:
            history_date_start = personal_data['historical_data_start_date']
        self.historical_data_start = createTimeStamp(history_date_start, formatstr="%d/%m/%Y")

        self.price_history = dict()
        # TODO: Check if historical data is after the requested start date
        # Check the data folder and load any cached history
        prefix = os.path.join(self.data_directory, 'price_history_')
        regex = re.compile(prefix + '(.*)\.json')
        files_list = glob.glob(prefix + '*.json')
        for file_ in files_list:
            match = regex.match(file_)
            assert match
            cache_key = match.group(1)
            with open(file_, 'r') as f:
                self.price_history[cache_key] = json.loads(f.read())

    def get_historical_data(self, from_asset, to_asset):
        """Get historical price data from cryptocompare"""
        cache_key = from_asset + '_' + to_asset
        if cache_key in self.price_history:
            return self.price_history[cache_key]

        now_ts = int(time.time())
        cryptocompare_hourquerylimit = 2000
        calculated_history = list()

        end_date = self.historical_data_start
        while True:
            pr_end_date = end_date
            end_date = end_date + (cryptocompare_hourquerylimit) * 3600
            query_string = (
                'https://min-api.cryptocompare.com/data/histohour?'
                'fsym={}&tsym={}&limit={}&toTs={}'.format(
                    from_asset, to_asset, cryptocompare_hourquerylimit, end_date
                ))
            resp = urllib2.urlopen(urllib2.Request(query_string))
            resp = json.loads(resp.read())
            if 'Response' not in resp or resp['Response'] != 'Success':
                raise ValueError(
                    'Failed to query cryptocompare for: "{}"'.format(query_string)
                )

            if pr_end_date != resp['TimeFrom']:
                # If we get more than we needed, since we are close to the now_ts
                # then skip all the already included entries
                diff = pr_end_date - resp['TimeFrom']
                if resp['Data'][diff / 3600]['time'] != pr_end_date:
                    raise ValueError(
                        'Expected to find the previous date timestamp during '
                        'historical data fetching'
                    )
                # just add only the part from the previous timestamp and on
                resp['Data'] = resp['Data'][diff / 3600:]

            if end_date < now_ts and resp['TimeTo'] != end_date:
                raise ValueError('End dates no match')

            # If last time slot and first new are the same, skip the first new slot
            last_entry_equal_to_first = (
                len(calculated_history) != 0 and
                calculated_history[-1]['time'] == resp['Data'][0]['time']
            )
            if last_entry_equal_to_first:
                resp['Data'] = resp['Data'][1:]
            calculated_history += resp['Data']
            if end_date >= now_ts:
                break

        # Let's always check for data sanity for the hourly prices.
        assert check_hourly_data_sanity(calculated_history)
        self.price_history[cache_key] = calculated_history
        # and now since we actually queried the data let's also save them locally
        out_filepath = os.path.join(self.data_directory, 'price_history_' + cache_key + '.json')
        with open(out_filepath, 'w') as outfile:
            json.dump(calculated_history, outfile)

        return calculated_history

    def query_historical_price(self, from_asset, to_asset, timestamp):
        if from_asset == to_asset:
            return 1

        data = self.get_historical_data(from_asset, to_asset)

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        assert timestamp > data[0]['time']
        index = int((timestamp - data[0]['time']) / 3600)
        diff = abs(data[index]['time'] - timestamp)
        if index + 1 <= len(data) - 1:
            diff_p1 = abs(data[index + 1]['time'] - timestamp)
            if diff_p1 < diff:
                index = index + 1

        price = (data[index]['high'] + data[index]['low']) / 2

        if price == 0:
            if from_asset != 'BTC':
                # Just get the BTC price
                asset_btc_price = self.query_historical_price(from_asset, 'BTC', timestamp)
                btc_to_asset_price = self.query_historical_price('BTC', to_asset, timestamp)
                price = asset_btc_price * btc_to_asset_price
            else:
                raise ValueError(
                    "Can't query a historical price for '{}' to '{}' at {}".format(
                        from_asset,
                        to_asset,
                        tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S'))
                )
        return price


class TradesHistorian(object):

    def __init__(
            self,
            poloniex,
            kraken,
            bittrex,
            data_directory,
            personal_data,
            start_date='01/11/2015',
    ):

        self.poloniex = poloniex
        self.kraken = kraken
        self.bittrex = bittrex
        self.start_ts = createTimeStamp(start_date, formatstr="%d/%m/%Y")
        self.data_directory = data_directory
        # get the start date for historical data
        history_date_start = DEFAULT_START_DATE
        if 'historical_data_start_date' in personal_data:
            history_date_start = personal_data['historical_data_start_date']
        self.historical_data_start = createTimeStamp(history_date_start, formatstr="%d/%m/%Y")

        # open the external trades file if existing
        if os.path.isfile(personal_data['external_trades_path']):
            with open(personal_data['external_trades_path'], 'r') as f:
                self.external_trades = json.loads(f.read())
            self.external_trades = trades_from_dictlist(self.external_trades)
        else:
            self.external_trade = list()

    def create_history(self):
        kraken_history = self.kraken.query_trade_history(
            start_ts=self.start_ts,
            end_ts=ts_now()
        )
        polo_history = self.poloniex.returnTradeHistory(
            currencyPair='all',
            start=self.start_ts,
            end=ts_now()
        )
        bittrex_history = self.bittrex.query_trade_history(
            start_ts=self.start_ts,
            end_ts=ts_now()
        )
        history = list(self.external_trades)

        for trade in kraken_history:
            history.append(trade_from_kraken(trade))

        for pair, trades in polo_history.iteritems():
            for trade in trades:
                # Do not count margin trading
                if trade['category'] == 'exchange':
                    history.append(trade_from_poloniex(trade, pair))

        history.extend(bittrex_history)
        history.sort(key=lambda trade: trade.timestamp)

        # Write to a file
        out_history = [tr._asdict() for tr in history]
        historyfile_path = os.path.join(self.data_directory, TRADES_HISTORYFILE)
        with open(historyfile_path, 'w') as outfile:
            json.dump(out_history, outfile)

        return history

    def get_history(self, resync):
        historyfile_path = os.path.join(self.data_directory, TRADES_HISTORYFILE)
        have_available_history = os.path.isfile(historyfile_path)

        if have_available_history and not resync:
            with open(historyfile_path, 'r') as infile:
                history_json_data = json.load(infile)
            history = trades_from_dictlist(history_json_data)
        else:
            history = self.create_history()
        return history
