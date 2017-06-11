import json
import time
import urllib2
import os
import glob
import re
from itertools import izip

from exchange import data_up_todate
from kraken import kraken_to_world_pair
from bittrex import trade_from_bittrex
from utils import (
    createTimeStamp,
    tsToDate,
    get_pair_position,
    get_jsonfile_contents_or_empty_list,
    get_jsonfile_contents_or_empty_dict
)
from order_formatting import Trade


DEFAULT_START_DATE = "01/08/2015"
TRADES_HISTORYFILE = 'trades_history.json'
MARGIN_HISTORYFILE = 'margin_trades_history.json'
MANUAL_MARGINS_LOGFILE = 'manual_margin_positions_log.json'
LOANS_HISTORYFILE = 'loans_history.json'
ASSETMOVEMENTS_HISTORYFILE = 'asset_movements_history.json'
FIAT_CURRENCIES = ('EUR', 'USD', 'GBP', 'JPY', 'CNY')


class NoPriceForGivenTimestamp(Exception):
    def __init__(self, from_asset, to_asset, timestamp):
        super(NoPriceForGivenTimestamp, self).__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset, to_asset, timestamp
            )
        )


class PriceQueryUnknownFromAsset(Exception):
    def __init__(self, from_asset):
        super(PriceQueryUnknownFromAsset, self).__init__(
            'Unable to query historical price for Unknown Asset: "{}"'.format(from_asset)
        )


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

    if poloniex_trade['category'] == 'settlement':
        trade_type = "settlement_%s" % trade_type

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


def trades_from_dictlist(given_trades, start_ts, end_ts):
    """ Gets a list of dict trades, most probably read from the json files and
    a time period. Returns it as a list of the Trade tuples that are inside the time period
    """
    returned_trades = list()
    for given_trade in given_trades:
        if given_trade['timestamp'] < start_ts:
            continue
        if given_trade['timestamp'] > end_ts:
            break

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


def write_history_data_in_file(data, filepath, start_ts, end_ts):
    with open(filepath, 'w') as outfile:
        history_dict = dict()
        history_dict['data'] = data
        history_dict['start_time'] = start_ts
        history_dict['end_time'] = end_ts
        json.dump(history_dict, outfile)


def write_trades_history_in_file(history, filepath, start_ts, end_ts):
    out_history = [tr._asdict() for tr in history]
    write_history_data_in_file(out_history, filepath, start_ts, end_ts)


def limit_trade_list_to_period(trades_list, start_ts, end_ts):
    """Accepts a SORTED by timestamp trades_list and returns a shortened version
    of that list limited to a specific time period"""

    start_idx = None
    end_idx = -1
    for idx, trade in enumerate(trades_list):
        if start_idx is None and trade.timestamp >= start_ts:
            start_idx = idx
        elif end_idx == -1 and trade.timestamp > end_ts:
            end_idx = idx - 1 if idx >= 1 else 0
            break

    return trades_list[start_idx:end_idx] if start_idx is not None else list()


def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)


def check_hourly_data_sanity(data, from_asset, to_asset):
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['time'] - n1['time']
        if diff != 3600:
            print(
                "Problem at indices {} and {} of {}_to_{} prices. Time difference is: {}".format(
                    index, index + 1, from_asset, to_asset, diff)
            )
            return False

        index += 2
    return True


def process_polo_loans(data, start_ts, end_ts):
    new_data = list()
    for loan in reversed(data):
        close_time = createTimeStamp(loan['close'], formatstr="%Y-%m-%d %H:%M:%S")
        open_time = createTimeStamp(loan['open'], formatstr="%Y-%m-%d %H:%M:%S")
        if open_time < start_ts:
            continue
        if close_time > end_ts:
            break
        new_data.append({
            'open_time': open_time,
            'close_time': close_time,
            'currency': loan['currency'],
            'fee': float(loan['fee']),
            'earned': float(loan['earned']),
        })

    new_data.sort(key=lambda loan: loan['open_time'])
    return new_data


class PriceHistorian(object):

    def __init__(self, data_directory, personal_data, logger):
        self.data_directory = data_directory
        self.log = logger
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
                data = json.loads(f.read())
                self.price_history[cache_key] = data

        # Get coin list of crypto compare. TODO: Cache this?
        query_string = 'https://www.cryptocompare.com/api/data/coinlist/'
        resp = urllib2.urlopen(urllib2.Request(query_string))
        resp = json.loads(resp.read())
        if 'Response' not in resp or resp['Response'] != 'Success':
            error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
            if 'Message' in resp:
                error_message += ". Error: {}".format(resp['Message'])
            raise ValueError(error_message)
        self.cryptocompare_coin_list = resp['Data']
        # For some reason even though price for the following assets is returned
        # it's not in the coinlist so let's add them here.
        self.cryptocompare_coin_list['DAO'] = object()
        self.cryptocompare_coin_list['USDT'] = object()

    def get_historical_data(self, from_asset, to_asset, timestamp):
        """Get historical price data from cryptocompare"""
        if from_asset not in self.cryptocompare_coin_list:
            raise ValueError(
                'Attempted to query historical price data for '
                'unknown asset "{}"'.format(from_asset)
            )

        if to_asset not in self.cryptocompare_coin_list and to_asset not in FIAT_CURRENCIES:
            raise ValueError(
                'Attempted to query historical price data for '
                'unknown asset "{}"'.format(to_asset)
            )

        cache_key = from_asset + '_' + to_asset
        if cache_key in self.price_history and self.price_history[cache_key]['end_time'] > timestamp:
            return self.price_history[cache_key]['data']

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
                error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
                if 'Message' in resp:
                    error_message += ". Error: {}".format(resp['Message'])
                raise ValueError(error_message)

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
        assert check_hourly_data_sanity(calculated_history, from_asset, to_asset)
        self.price_history[cache_key] = {
            'data': calculated_history,
            'start_time': self.historical_data_start,
            'end_time': now_ts
        }
        # and now since we actually queried the data let's also save them locally
        write_history_data_in_file(
            calculated_history,
            os.path.join(self.data_directory, 'price_history_' + cache_key + '.json'),
            self.historical_data_start,
            now_ts
        )

        return calculated_history

    def query_historical_price(self, from_asset, to_asset, timestamp):
        if from_asset == to_asset:
            return 1

        if from_asset not in self.cryptocompare_coin_list:
            raise PriceQueryUnknownFromAsset(from_asset)

        data = self.get_historical_data(from_asset, to_asset, timestamp)

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        # print("loaded {}_{}".format(from_asset, to_asset))
        assert timestamp > data[0]['time']
        index = int((timestamp - data[0]['time']) / 3600)
        # print("timestamp: {} index: {} data_length: {}".format(timestamp, index, len(data)))
        diff = abs(data[index]['time'] - timestamp)
        if index + 1 <= len(data) - 1:
            diff_p1 = abs(data[index + 1]['time'] - timestamp)
            if diff_p1 < diff:
                index = index + 1

        if data[index]['high'] is None or data[index]['low'] is None:
            # If we get some None in the hourly set price to 0 so that we check daily price
            price = 0
        else:
            price = (data[index]['high'] + data[index]['low']) / 2

        if price == 0:
            if from_asset != 'BTC' and to_asset != 'BTC':
                # Just get the BTC price
                asset_btc_price = self.query_historical_price(from_asset, 'BTC', timestamp)
                btc_to_asset_price = self.query_historical_price('BTC', to_asset, timestamp)
                price = asset_btc_price * btc_to_asset_price
            else:
                # attempt to get the daily price by timestamp
                query_string = (
                    'https://min-api.cryptocompare.com/data/pricehistorical?'
                    'fsym={}&tsyms={}&ts={}'.format(
                        from_asset, to_asset, timestamp
                    ))
                if to_asset == 'BTC':
                    query_string += '&tryConversion=false'
                resp = urllib2.urlopen(urllib2.Request(query_string))
                resp = json.loads(resp.read())
                print('DAILY PRICE OF ASSET: "{}"'.format(resp))
                if from_asset not in resp:
                    error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
                    raise ValueError(error_message)
                price = resp[from_asset][to_asset]

                if price == 0:
                    raise NoPriceForGivenTimestamp(
                        from_asset,
                        to_asset,
                        tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S')
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
        self.personal_data = personal_data
        # get the start date for historical data
        history_date_start = DEFAULT_START_DATE
        if 'historical_data_start_date' in personal_data:
            history_date_start = personal_data['historical_data_start_date']
        self.historical_data_start = createTimeStamp(history_date_start, formatstr="%d/%m/%Y")
        # If this flag is true we attempt to read from the manually logged margin positions file
        self.read_manual_margin_positions = True

    def create_history(self, start_ts, end_ts, end_at_least_ts):
        """Creates trades and loans history from start_ts to end_ts or if
        `end_at_least` is given and we have a cache history for that particular source
        which satisfies it we return the cache
        """
        # open the external trades file if existing
        external_trades = get_jsonfile_contents_or_empty_list(
            self.personal_data['external_trades_path']
        )
        external_trades = trades_from_dictlist(external_trades, start_ts, end_ts)

        # start creating the all trades history list
        history = list(external_trades)
        asset_movements = list()

        if self.kraken is not None:
            kraken_history = self.kraken.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts
            )
            for trade in kraken_history:
                history.append(trade_from_kraken(trade))
            kraken_asset_movements = self.kraken.query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
            )
            asset_movements.extend(kraken_asset_movements)

        if self.poloniex is not None:
            polo_history = self.poloniex.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts
            )
            poloniex_margin_trades = list()
            for pair, trades in polo_history.iteritems():
                for trade in trades:
                    category = trade['category']

                    if category == 'exchange' or category == 'settlement':
                        history.append(trade_from_poloniex(trade, pair))
                    elif category == 'marginTrade' and not self.read_manual_margin_positions:
                        poloniex_margin_trades.append(trade_from_poloniex(trade, pair))
                    else:
                        raise ValueError("Unexpected poloniex trade category: {}".format(category))

            if self.read_manual_margin_positions:
                # Just read the manual positions log and make virtual trades that
                # correspond to the profits
                assert poloniex_margin_trades == list(), (
                    "poloniex margin trades list should be empty here"
                )
                if os.path.isfile(MANUAL_MARGINS_LOGFILE):
                    with open(MANUAL_MARGINS_LOGFILE, 'r') as f:
                        margin_data = json.load(f)
                        main_currency = self.personal_data.get('main_currency', 'EUR')
                        for trade in margin_data:
                            poloniex_margin_trades.append(Trade(
                                type='margin_position',
                                timestamp=trade['time'],
                                pair='BTC_{}'.format(main_currency),
                                rate=0,
                                cost=0,
                                cost_currency=main_currency,
                                fee=0,
                                fee_currency=0,
                                amount=trade['btc_profit_loss'],
                                location='poloniex'
                            ))

            poloniex_margin_trades.sort(key=lambda trade: trade.timestamp)
            poloniex_margin_trades = limit_trade_list_to_period(
                poloniex_margin_trades,
                start_ts,
                end_ts
            )
            polo_loans = self.poloniex.query_loan_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
                from_csv=True
            )
            polo_loans = process_polo_loans(polo_loans, start_ts, end_ts)
            polo_asset_movements = self.poloniex.query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
            )
            asset_movements.extend(polo_asset_movements)

        if self.bittrex is not None:
            bittrex_history = self.bittrex.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts
            )
            for trade in bittrex_history:
                history.append(trade_from_bittrex(trade))

        # We sort it here ... but when accounting runs through the entire actions list,
        # it resorts, so unless the fact that we sort is used somewhere else too, perhaps
        # we can skip it?
        history.sort(key=lambda trade: trade.timestamp)
        history = limit_trade_list_to_period(history, start_ts, end_ts)

        # Write to files
        historyfile_path = os.path.join(self.data_directory, TRADES_HISTORYFILE)
        write_trades_history_in_file(history, historyfile_path, start_ts, end_ts)
        marginfile_path = os.path.join(self.data_directory, MARGIN_HISTORYFILE)
        write_trades_history_in_file(poloniex_margin_trades, marginfile_path, start_ts, end_ts)
        loansfile_path = os.path.join(self.data_directory, LOANS_HISTORYFILE)
        write_history_data_in_file(polo_loans, loansfile_path, start_ts, end_ts)
        assetmovementsfile_path = os.path.join(self.data_directory, ASSETMOVEMENTS_HISTORYFILE)
        write_history_data_in_file(asset_movements, assetmovementsfile_path, start_ts, end_ts)
        return history, poloniex_margin_trades, polo_loans, asset_movements

    def get_history(self, start_ts, end_ts, end_at_least_ts=None):
        """Gets or creates trades and loans history from start_ts to end_ts or if
        `end_at_least` is given and we have a cache history which satisfies it we
        return the cache
        """
        if end_at_least_ts is None:
            end_at_least_ts = end_ts

        historyfile_path = os.path.join(self.data_directory, TRADES_HISTORYFILE)
        if os.path.isfile(historyfile_path):
            with open(historyfile_path, 'r') as infile:
                try:
                    history_json_data = json.load(infile)
                except:
                    pass

                all_history_okay = data_up_todate(history_json_data, start_ts, end_at_least_ts)
                poloniex_history_okay = True
                if self.poloniex is not None:
                    poloniex_history_okay = self.poloniex.check_trades_cache(
                        start_ts, end_at_least_ts
                    ) is not None
                kraken_history_okay = True
                if self.kraken is not None:
                    kraken_history_okay = self.kraken.check_trades_cache(
                        start_ts, end_at_least_ts
                    ) is not None
                bittrex_history_okay = True
                if self.bittrex is not None:
                    bittrex_history_okay = self.bittrex.check_trades_cache(
                        start_ts, end_at_least_ts
                    ) is not None

                if self.read_manual_margin_positions:
                    pass
                else:
                    margin_file_contents = get_jsonfile_contents_or_empty_dict(MARGIN_HISTORYFILE)
                    margin_history_is_okay = data_up_todate(
                        margin_file_contents,
                        start_ts,
                        end_at_least_ts
                    )

                loan_file_contents = get_jsonfile_contents_or_empty_dict(LOANS_HISTORYFILE)
                loan_history_is_okay = data_up_todate(
                    loan_file_contents,
                    start_ts,
                    end_at_least_ts
                )
                asset_movements_contents = get_jsonfile_contents_or_empty_dict(
                    ASSETMOVEMENTS_HISTORYFILE
                )
                asset_movements_history_is_okay = data_up_todate(
                    asset_movements_contents,
                    start_ts,
                    end_at_least_ts
                )

                if (
                        all_history_okay and
                        poloniex_history_okay and
                        kraken_history_okay and
                        bittrex_history_okay and
                        margin_history_is_okay and
                        loan_history_is_okay and
                        asset_movements_history_is_okay):

                    history_trades = trades_from_dictlist(
                        history_json_data['data'],
                        start_ts,
                        end_ts
                    )
                    margin_trades = trades_from_dictlist(
                        margin_file_contents['data'],
                        start_ts,
                        end_ts
                    )

                    return (
                        history_trades,
                        margin_trades,
                        loan_file_contents['data'],
                        asset_movements_contents['data']
                    )

        return self.create_history(start_ts, end_ts, end_at_least_ts)
