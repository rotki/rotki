import glob
import logging
import os
import re
import time
from json.decoder import JSONDecodeError

from rotkehlchen.binance import trade_from_binance  # noqa
from rotkehlchen.bitmex import trade_from_bitmex  # noqa
from rotkehlchen.bittrex import trade_from_bittrex  # noqa
from rotkehlchen.errors import PriceQueryUnknownFromAsset, RemoteError
from rotkehlchen.exchange import data_up_todate
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import FIAT_CURRENCIES, world_to_cryptocompare
from rotkehlchen.kraken import trade_from_kraken  # noqa
from rotkehlchen.logging import RotkehlchenLogsAdapter, make_sensitive
from rotkehlchen.order_formatting import (
    MarginPosition,
    asset_movements_from_dictlist,
    trades_from_dictlist,
)
from rotkehlchen.poloniex import trade_from_poloniex
from rotkehlchen.transactions import query_etherscan_for_transactions, transactions_from_dictlist
from rotkehlchen.typing import Asset, NonEthTokenBlockchainAsset, Timestamp
from rotkehlchen.utils import (
    convert_to_int,
    createTimeStamp,
    get_jsonfile_contents_or_empty_dict,
    request_get,
    rlk_jsondumps,
    rlk_jsonloads,
    ts_now,
    tsToDate,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


TRADES_HISTORYFILE = 'trades_history.json'
MARGIN_HISTORYFILE = 'margin_trades_history.json'
MANUAL_MARGINS_LOGFILE = 'manual_margin_positions_log.json'
LOANS_HISTORYFILE = 'loans_history.json'
ETHEREUM_TX_LOGFILE = 'ethereum_tx_log.json'
ASSETMOVEMENTS_HISTORYFILE = 'asset_movements_history.json'


def trade_from_exchange(exchange, trade):
    name = exchange.name.lower()
    if name == 'bittrex':
        return trade_from_bittrex(trade)
    elif name == 'binance':
        return trade_from_binance(trade, exchange.symbols_to_pair)
    elif name == 'kraken':
        return trade_from_kraken(trade)
    elif name == 'bitmex':
        return trade_from_bitmex(trade)
    elif name == 'poloniex':
        return trade_from_poloniex(trade)


class NoPriceForGivenTimestamp(Exception):
    def __init__(self, from_asset, to_asset, timestamp):
        super(NoPriceForGivenTimestamp, self).__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset, to_asset, timestamp,
            ),
        )


def include_external_trades(db, start_ts, end_ts, history):
    external_trades = db.get_external_trades()
    external_trades = trades_from_dictlist(external_trades, start_ts, end_ts)
    history.extend(external_trades)
    history.sort(key=lambda trade: trade.timestamp)

    return history


def do_read_manual_margin_positions(user_directory):
    manual_margin_path = os.path.join(user_directory, MANUAL_MARGINS_LOGFILE)
    if os.path.isfile(manual_margin_path):
        with open(manual_margin_path, 'r') as f:
            margin_data = rlk_jsonloads(f.read())
    else:
        margin_data = []
        logger.info(
            'Could not find manual margins log file at {}'.format(manual_margin_path),
        )

    # Now turn the manual margin data to our MarginPosition format
    # The poloniex manual data format is:
    # { "open_time": unix_timestamp, "close_time": unix_timestamp,
    #   "btc_profit_loss": floating_point_number for profit or loss,
    #   "notes": "optional string with notes on the margin position"
    # }
    margin_positions = list()
    for position in margin_data:
        margin_positions.append(
            MarginPosition(
                exchange='poloniex',
                open_time=position['open_time'],
                close_time=position['close_time'],
                profit_loss=FVal(position['btc_profit_loss']),
                pl_currency=NonEthTokenBlockchainAsset('BTC'),
                notes=position['notes'],
            ),
        )

    return margin_positions


def write_history_data_in_file(data, filepath, start_ts, end_ts):
    log.info(
        'Writing history file',
        filepath=filepath,
        start_time=start_ts,
        end_time=end_ts,
    )
    with open(filepath, 'w') as outfile:
        history_dict = dict()
        history_dict['data'] = data
        history_dict['start_time'] = start_ts
        history_dict['end_time'] = end_ts
        outfile.write(rlk_jsondumps(history_dict))


def write_tupledata_history_in_file(history, filepath, start_ts, end_ts):
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
    return zip(a, a)


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
                    index, index + 1, from_asset, to_asset, diff),
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

        loan_data = {
            'open_time': open_time,
            'close_time': close_time,
            'currency': loan['currency'],
            'fee': FVal(loan['fee']),
            'earned': FVal(loan['earned']),
            'amount_lent': FVal(loan['amount']),
        }
        log.debug('processing poloniex loan', **make_sensitive(loan_data))
        new_data.append(loan_data)

    new_data.sort(key=lambda loan: loan['open_time'])
    return new_data


class PriceHistorian(object):

    def __init__(self, data_directory, history_date_start, inquirer):
        self.data_directory = data_directory
        # get the start date for historical data
        self.historical_data_start = createTimeStamp(history_date_start, formatstr="%d/%m/%Y")
        self.inquirer = inquirer

        self.price_history = dict()
        self.price_history_file = dict()

        # Check the data folder and remember the filenames of any cached history
        prefix = os.path.join(self.data_directory, 'price_history_')
        prefix = prefix.replace('\\', '\\\\')
        regex = re.compile(prefix + '(.*)\\.json')
        files_list = glob.glob(prefix + '*.json')

        for file_ in files_list:
            match = regex.match(file_)
            assert match
            cache_key = match.group(1)
            self.price_history_file[cache_key] = file_

        # Get coin list of crypto compare
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cryptocompare_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'rb') as f:
                try:
                    data = rlk_jsonloads(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery cryptocompare
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            query_string = 'https://www.cryptocompare.com/api/data/coinlist/'
            log.debug('Querying cryptocompare', url=query_string)
            resp = request_get(query_string)
            if 'Response' not in resp or resp['Response'] != 'Success':
                error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
                if 'Message' in resp:
                    error_message += ". Error: {}".format(resp['Message'])

                log.error('Cryptocompare query failure', url=query_string, error=error_message)
                raise ValueError(error_message)

            data = resp['Data']

            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        self.cryptocompare_coin_list = data
        # For some reason even though price for the following assets is returned
        # it's not in the coinlist so let's add them here.
        self.cryptocompare_coin_list['DAO'] = object()
        self.cryptocompare_coin_list['USDT'] = object()

    def got_cached_price(self, cache_key, timestamp):
        """Check if we got a price history for the timestamp cached"""
        if cache_key in self.price_history_file:
            if cache_key not in self.price_history:
                try:
                    with open(self.price_history_file[cache_key], 'rb') as f:
                        data = rlk_jsonloads(f.read())
                        self.price_history[cache_key] = data
                except (OSError, IOError, JSONDecodeError):
                    return False

            in_range = (
                self.price_history[cache_key]['start_time'] <= timestamp and
                self.price_history[cache_key]['end_time'] > timestamp
            )
            if in_range:
                log.debug('Found cached price', cache_key=cache_key, timestamp=timestamp)
                return True

        return False

    def adjust_to_cryptocompare_price_incosistencies(
            self,
            price: FVal,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> FVal:
        """Doublecheck against the USD rate, and if incosistencies are found
        then take the USD adjusted price.

        This is due to incosistencies in the provided historical data from
        cryptocompare. https://github.com/rotkehlchenio/rotkehlchen/issues/221

        Note: Since 12/01/2019 this seems to no longer be happening, but I will
        keep the code around just in case a regression is introduced on the side
        of cryptocompare.
        """
        from_asset_usd = self.query_historical_price(from_asset, 'USD', timestamp)
        to_asset_usd = self.query_historical_price(to_asset, 'USD', timestamp)

        usd_invert_conversion = from_asset_usd / to_asset_usd
        abs_diff = abs(usd_invert_conversion - price)
        relative_difference = abs_diff / max(price, usd_invert_conversion)
        if relative_difference >= FVal('0.1'):
            log.warning(
                'Cryptocompare historical price data are incosistent.'
                'Taking USD adjusted price. Check github issue #221',
                from_asset=from_asset,
                to_asset=to_asset,
                incosistent_price=price,
                usd_price=from_asset_usd,
                adjusted_price=usd_invert_conversion,
            )
            return usd_invert_conversion
        return price

    def get_historical_data(self, from_asset, to_asset, timestamp):
        """Get historical price data from cryptocompare"""
        log.debug(
            'Retrieving historical price data',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        if from_asset not in self.cryptocompare_coin_list and from_asset not in FIAT_CURRENCIES:
            raise ValueError(
                'Attempted to query historical price data for '
                'unknown asset "{}"'.format(from_asset),
            )

        if to_asset not in self.cryptocompare_coin_list and to_asset not in FIAT_CURRENCIES:
            raise ValueError(
                'Attempted to query historical price data for '
                'unknown asset "{}"'.format(to_asset),
            )

        cache_key = from_asset + '_' + to_asset
        got_cached_value = self.got_cached_price(cache_key, timestamp)
        if got_cached_value:
            return self.price_history[cache_key]['data']

        now_ts = int(time.time())
        cryptocompare_hourquerylimit = 2000
        calculated_history = list()

        if self.historical_data_start <= timestamp:
            end_date = self.historical_data_start
        else:
            end_date = timestamp
        while True:
            no_data_for_timestamp = False
            pr_end_date = end_date
            end_date = end_date + (cryptocompare_hourquerylimit) * 3600

            log.debug(
                'Querying cryptocompare for hourly historical price',
                from_asset=from_asset,
                to_asset=to_asset,
                cryptocompare_hourquerylimit=cryptocompare_hourquerylimit,
                end_date=end_date,
            )
            query_string = (
                'https://min-api.cryptocompare.com/data/histohour?'
                'fsym={}&tsym={}&limit={}&toTs={}'.format(
                    world_to_cryptocompare(from_asset, end_date),
                    world_to_cryptocompare(to_asset, end_date),
                    cryptocompare_hourquerylimit,
                    end_date,
                ))

            resp = request_get(query_string)
            if 'Response' not in resp or resp['Response'] != 'Success':
                msg = 'Unable to retrieve requested data at this time, please try again later'
                no_data_for_timestamp = (
                    msg in resp['Message'] and
                    resp['Type'] == 96
                )
                if no_data_for_timestamp:
                    log.debug(
                        'No hourly cryptocompare historical data for pair',
                        from_asset=from_asset,
                        to_asset=to_asset,
                        timestamp=end_date,
                    )
                    continue

                error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
                if 'Message' in resp:
                    error_message += ". Error: {}".format(resp['Message'])

                log.error(
                    'Cryptocompare hourly historical price query failed',
                    error=error_message,
                )
                raise ValueError(error_message)

            if pr_end_date != resp['TimeFrom']:
                # If we get more than we needed, since we are close to the now_ts
                # then skip all the already included entries
                diff = pr_end_date - resp['TimeFrom']
                if resp['Data'][diff // 3600]['time'] != pr_end_date:
                    raise ValueError(
                        'Expected to find the previous date timestamp during '
                        'historical data fetching',
                    )
                # just add only the part from the previous timestamp and on
                resp['Data'] = resp['Data'][diff // 3600:]

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
            'end_time': now_ts,
        }
        # and now since we actually queried the data let's also save them locally
        filename = os.path.join(self.data_directory, 'price_history_' + cache_key + '.json')
        log.info(
            'Updating price history cache',
            filename=filename,
            from_asset=from_asset,
            to_asset=to_asset,
        )
        write_history_data_in_file(
            calculated_history,
            filename,
            self.historical_data_start,
            now_ts,
        )
        self.price_history_file[cache_key] = filename

        return calculated_history

    def query_historical_price(self, from_asset, to_asset, timestamp):
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`.
        So how much `to_asset` does 1 unit of `from_asset` cost.

        Args:
            from_asset (str): The ticker symbol of the asset for which we want to know
                              the price.
            to_asset (str): The ticker symbol of the asset against which we want to
                            know the price.
            timestamp (int): The timestamp at which to query the price
        """
        log.debug(
            'Querying historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        if from_asset == to_asset:
            return 1

        if from_asset in FIAT_CURRENCIES and to_asset in FIAT_CURRENCIES:
            # if we are querying historical forex data then try something other than cryptocompare
            price = self.inquirer.query_historical_fiat_exchange_rates(
                from_asset,
                to_asset,
                timestamp,
            )
            if price is not None:
                return price
            # else cryptocompare also has historical fiat to fiat data

        if from_asset not in self.cryptocompare_coin_list and from_asset not in FIAT_CURRENCIES:
            raise PriceQueryUnknownFromAsset(from_asset)

        data = self.get_historical_data(from_asset, to_asset, timestamp)

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        if timestamp >= data[0]['time']:
            index = convert_to_int((timestamp - data[0]['time']) / 3600, accept_only_exact=False)
            # print("timestamp: {} index: {} data_length: {}".format(timestamp, index, len(data)))
            diff = abs(data[index]['time'] - timestamp)
            if index + 1 <= len(data) - 1:
                diff_p1 = abs(data[index + 1]['time'] - timestamp)
                if diff_p1 < diff:
                    index = index + 1

            if data[index]['high'] is None or data[index]['low'] is None:
                # If we get some None in the hourly set price to 0 so that we check alternatives
                price = FVal(0)
            else:
                price = FVal((data[index]['high'] + data[index]['low'])) / 2
        else:
            # no price found in the historical data from/to asset, try alternatives
            price = FVal(0)

        if price == 0:
            if from_asset != 'BTC' and to_asset != 'BTC':
                log.debug(
                    f"Coudn't find historical price from {from_asset} to "
                    f"{to_asset}. Comparing with BTC...",
                )
                # Just get the BTC price
                asset_btc_price = self.query_historical_price(from_asset, 'BTC', timestamp)
                btc_to_asset_price = self.query_historical_price('BTC', to_asset, timestamp)
                price = asset_btc_price * btc_to_asset_price
            else:
                log.debug(
                    f"Coudn't find historical price from {from_asset} to "
                    f"{to_asset}. Attempting to get daily price...",
                )
                # attempt to get the daily price by timestamp
                cc_from_asset = world_to_cryptocompare(from_asset, timestamp)
                cc_to_asset = world_to_cryptocompare(to_asset, timestamp)
                log.debug(
                    'Querying cryptocompare for daily historical price',
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
                query_string = (
                    'https://min-api.cryptocompare.com/data/pricehistorical?'
                    'fsym={}&tsyms={}&ts={}'.format(
                        cc_from_asset,
                        cc_to_asset,
                        timestamp,
                    ))
                if to_asset == 'BTC':
                    query_string += '&tryConversion=false'
                resp = request_get(query_string)

                if cc_from_asset not in resp:
                    error_message = 'Failed to query cryptocompare for: "{}"'.format(query_string)
                    log.error(
                        'Cryptocompare query for daily historical price failed',
                        from_asset=from_asset,
                        to_asset=to_asset,
                        timestamp=timestamp,
                        error=error_message,
                    )
                    raise ValueError(error_message)

                price = FVal(resp[cc_from_asset][cc_to_asset])

        comparison_to_nonusd_fiat = (
            (to_asset in FIAT_CURRENCIES and to_asset != 'USD') or
            (from_asset in FIAT_CURRENCIES and from_asset != 'USD')
        )
        if comparison_to_nonusd_fiat:
            price = self.adjust_to_cryptocompare_price_incosistencies(
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        if price == 0:
            raise NoPriceForGivenTimestamp(
                from_asset,
                to_asset,
                tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S'),
            )

        log.debug(
            'Got historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            price=price,
        )

        return price


class TradesHistorian(object):

    def __init__(
            self,
            user_directory,
            db,
            eth_accounts,
            historical_data_start,
    ):
        self.exchanges = {}
        self.user_directory = user_directory
        self.db = db
        self.eth_accounts = eth_accounts
        # get the start date for historical data
        self.historical_data_start = createTimeStamp(historical_data_start, formatstr="%d/%m/%Y")
        # If this flag is true we attempt to read from the manually logged margin positions file
        self.read_manual_margin_positions = True

    def set_exchange(self, exchange_id, exchange_obj):
        if self.exchanges.get(exchange_id) is None or exchange_obj is None:
            self.exchanges[exchange_id] = exchange_obj
        elif exchange_obj:
            raise ValueError(
                'Attempted to set {} exchange in TradesHistorian while it was '
                'already set'.format(exchange_id),
            )

    def get_exchange_by_name(self, name):
        for exchange in self.exchanges.values():
            if exchange.name == name:
                return exchange
        return None

    def query_poloniex_history(self, history, asset_movements, start_ts, end_ts, end_at_least_ts):
        log.info(
            'Starting poloniex history query',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )
        poloniex_margin_trades = list()
        polo_loans = list()
        poloniex = self.get_exchange_by_name('Poloniex')
        if poloniex is not None:
            polo_history = poloniex.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
            )

            for pair, trades in polo_history.items():
                for trade in trades:
                    category = trade['category']

                    if category == 'exchange' or category == 'settlement':
                        history.append(trade_from_poloniex(trade, pair))
                    elif category == 'marginTrade':
                        if not self.read_manual_margin_positions:
                            poloniex_margin_trades.append(trade_from_poloniex(trade, pair))
                    else:
                        raise ValueError('Unexpected poloniex trade category: {}'.format(category))

            if self.read_manual_margin_positions:
                # Just read the manual positions log and make virtual trades that
                # correspond to the profits
                assert poloniex_margin_trades == list(), (
                    'poloniex margin trades list should be empty here'
                )
                poloniex_margin_trades = do_read_manual_margin_positions(
                    self.user_directory,
                )
            else:
                poloniex_margin_trades.sort(key=lambda trade: trade.timestamp)
                poloniex_margin_trades = limit_trade_list_to_period(
                    poloniex_margin_trades,
                    start_ts,
                    end_ts,
                )

            polo_loans = poloniex.query_loan_history(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
                from_csv=True,
            )
            polo_loans = process_polo_loans(polo_loans, start_ts, end_ts)
            polo_asset_movements = poloniex.query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
            )
            asset_movements.extend(polo_asset_movements)

        return history, asset_movements, poloniex_margin_trades, polo_loans

    def create_history(self, start_ts, end_ts, end_at_least_ts):
        """Creates trades and loans history from start_ts to end_ts or if
        `end_at_least` is given and we have a cache history for that particular source
        which satisfies it we return the cache
        """
        log.info(
            'Starting trade history creation',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )

        # start creating the all trades history list
        history = list()
        asset_movements = list()
        empty_or_error = ''

        try:
            (
                history,
                asset_movements,
                poloniex_margin_trades,
                polo_loans,
            ) = self.query_poloniex_history(
                history,
                asset_movements,
                start_ts,
                end_ts,
                end_at_least_ts,
            )
        except RemoteError as e:
            empty_or_error += '\n' + str(e)

        for exchange in self.exchanges.values():
            try:
                exchange_history = exchange.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                for trade in exchange_history:
                    history.append(trade_from_exchange(exchange, trade))
            except RemoteError as e:
                empty_or_error += '\n' + str(e)

            if exchange.name == 'Bitmex' or exchange.name == 'Kraken':
                try:
                    asset_movements = exchange.query_deposits_withdrawals(
                        start_ts=start_ts,
                        end_ts=end_ts,
                        end_at_least_ts=end_at_least_ts,
                    )
                    asset_movements.extend(asset_movements)

                except RemoteError as e:
                    empty_or_error += '\n' + str(e)

        try:
            eth_transactions = query_etherscan_for_transactions(self.eth_accounts)
        except RemoteError as e:
            empty_or_error += '\n' + str(e)

        # We sort it here ... but when accounting runs through the entire actions list,
        # it resorts, so unless the fact that we sort is used somewhere else too, perhaps
        # we can skip it?
        history.sort(key=lambda trade: trade.timestamp)
        history = limit_trade_list_to_period(history, start_ts, end_ts)

        poloniex = self.get_exchange_by_name('Poloniex')

        # Write to files
        historyfile_path = os.path.join(self.user_directory, TRADES_HISTORYFILE)
        write_tupledata_history_in_file(history, historyfile_path, start_ts, end_ts)
        if poloniex is not None and not self.read_manual_margin_positions:
            marginfile_path = os.path.join(self.user_directory, MARGIN_HISTORYFILE)
            write_tupledata_history_in_file(
                poloniex_margin_trades,
                marginfile_path,
                start_ts,
                end_ts,
            )

        if poloniex is not None:
            loansfile_path = os.path.join(self.user_directory, LOANS_HISTORYFILE)
            write_history_data_in_file(polo_loans, loansfile_path, start_ts, end_ts)
        assetmovementsfile_path = os.path.join(self.user_directory, ASSETMOVEMENTS_HISTORYFILE)
        write_tupledata_history_in_file(asset_movements, assetmovementsfile_path, start_ts, end_ts)
        eth_tx_log_path = os.path.join(self.user_directory, ETHEREUM_TX_LOGFILE)
        write_tupledata_history_in_file(eth_transactions, eth_tx_log_path, start_ts, end_ts)

        # After writting everything to files include the external trades in the history
        history = include_external_trades(self.db, start_ts, end_ts, history)

        return (
            empty_or_error,
            history,
            poloniex_margin_trades,
            polo_loans,
            asset_movements,
            eth_transactions,
        )

    def get_history(self, start_ts, end_ts, end_at_least_ts=None):
        """Gets or creates trades and loans history from start_ts to end_ts or if
        `end_at_least` is given and we have a cache history which satisfies it we
        return the cache
        """
        if end_at_least_ts is None:
            end_at_least_ts = end_ts

        log.info(
            'Get or create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )

        historyfile_path = os.path.join(self.user_directory, TRADES_HISTORYFILE)
        if os.path.isfile(historyfile_path):
            with open(historyfile_path, 'r') as infile:
                try:
                    history_json_data = rlk_jsonloads(infile.read())
                except JSONDecodeError:
                    pass

                all_history_okay = data_up_todate(history_json_data, start_ts, end_at_least_ts)
                exchange_history_okay = {}
                for exchange in self.exchanges.values():
                    exchange_history_okay[exchange.name] = exchange.check_trades_cache(
                        start_ts, end_at_least_ts,
                    ) is not None

                if not self.read_manual_margin_positions:
                    marginfile_path = os.path.join(self.user_directory, MARGIN_HISTORYFILE)
                    margin_file_contents = get_jsonfile_contents_or_empty_dict(marginfile_path)
                    margin_history_is_okay = data_up_todate(
                        margin_file_contents,
                        start_ts,
                        end_at_least_ts,
                    )
                else:
                    margin_history_is_okay = True
                    margin_file_contents = do_read_manual_margin_positions(
                        self.user_directory,
                    )

                loansfile_path = os.path.join(self.user_directory, LOANS_HISTORYFILE)
                loan_file_contents = get_jsonfile_contents_or_empty_dict(loansfile_path)
                loan_history_is_okay = data_up_todate(
                    loan_file_contents,
                    start_ts,
                    end_at_least_ts,
                )

                assetmovementsfile_path = os.path.join(
                    self.user_directory,
                    ASSETMOVEMENTS_HISTORYFILE,
                )
                asset_movements_contents = get_jsonfile_contents_or_empty_dict(
                    assetmovementsfile_path,
                )
                asset_movements_history_is_okay = data_up_todate(
                    asset_movements_contents,
                    start_ts,
                    end_at_least_ts,
                )

                eth_tx_log_path = os.path.join(self.user_directory, ETHEREUM_TX_LOGFILE)
                eth_tx_log_contents = get_jsonfile_contents_or_empty_dict(eth_tx_log_path)
                eth_tx_log_history_history_is_okay = data_up_todate(
                    eth_tx_log_contents,
                    start_ts,
                    end_at_least_ts,
                )

                if (
                        all_history_okay and
                        all(exchange_history_okay) and
                        margin_history_is_okay and
                        loan_history_is_okay and
                        asset_movements_history_is_okay and
                        eth_tx_log_history_history_is_okay):

                    log.info(
                        'Using cached history',
                        start_ts=start_ts,
                        end_ts=end_ts,
                        end_at_least_ts=end_at_least_ts,
                    )

                    history_trades = trades_from_dictlist(
                        history_json_data['data'],
                        start_ts,
                        end_ts,
                    )
                    if not self.read_manual_margin_positions:
                        margin_trades = trades_from_dictlist(
                            margin_file_contents['data'],
                            start_ts,
                            end_ts,
                        )
                    else:
                        margin_trades = margin_file_contents

                    eth_transactions = transactions_from_dictlist(
                        eth_tx_log_contents['data'],
                        start_ts,
                        end_ts,
                    )
                    asset_movements = asset_movements_from_dictlist(
                        asset_movements_contents['data'],
                        start_ts,
                        end_ts,
                    )

                    history_trades = include_external_trades(
                        self.db,
                        start_ts,
                        end_ts,
                        history_trades,
                    )

                    # make sure that this is the same as what is returned
                    # from create_history
                    return (
                        '',
                        history_trades,
                        margin_trades,
                        loan_file_contents['data'],
                        asset_movements,
                        eth_transactions,
                    )

        return self.create_history(start_ts, end_ts, end_at_least_ts)
