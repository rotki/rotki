import logging
import os
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, List

from rotkehlchen.assets.asset import Asset
from rotkehlchen.binance import trade_from_binance
from rotkehlchen.bitmex import trade_from_bitmex
from rotkehlchen.bittrex import trade_from_bittrex
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError, UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.exchange import data_up_todate
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.kraken import trade_from_kraken
from rotkehlchen.logging import RotkehlchenLogsAdapter, make_sensitive
from rotkehlchen.order_formatting import (
    MarginPosition,
    Trade,
    asset_movements_from_dictlist,
    trades_from_dictlist,
)
from rotkehlchen.poloniex import trade_from_poloniex
from rotkehlchen.transactions import query_etherscan_for_transactions, transactions_from_dictlist
from rotkehlchen.typing import EthAddress, FiatAsset, FilePath, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    createTimeStamp,
    get_jsonfile_contents_or_empty_dict,
    write_history_data_in_file,
)
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.externalapis import Cryptocompare

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


TRADES_HISTORYFILE = 'trades_history.json'
MARGIN_HISTORYFILE = 'margin_trades_history.json'
MANUAL_MARGINS_LOGFILE = 'manual_margin_positions_log.json'
LOANS_HISTORYFILE = 'loans_history.json'
ETHEREUM_TX_LOGFILE = 'ethereum_tx_log.json'
ASSETMOVEMENTS_HISTORYFILE = 'asset_movements_history.json'


def include_external_trades(db, start_ts, end_ts, history):
    external_trades = db.get_trades()
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
                pl_currency=A_BTC,
                notes=position['notes'],
            ),
        )

    return margin_positions


def write_tupledata_history_in_file(history, filepath, start_ts, end_ts):
    out_history = [tr._asdict() for tr in history]
    write_history_data_in_file(out_history, filepath, start_ts, end_ts)


def limit_trade_list_to_period(
        trades_list: List[Trade],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[Trade]:
    """Accepts a SORTED by timestamp trades_list and returns a shortened version
    of that list limited to a specific time period"""

    start_idx = None
    end_idx = None
    for idx, trade in enumerate(trades_list):
        if start_idx is None and trade.timestamp >= start_ts:
            start_idx = idx

        if end_idx is None and trade.timestamp > end_ts:
            end_idx = idx if idx >= 1 else 0
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


class PriceHistorian():
    __instance = None
    _historical_data_start: Timestamp
    _cryptocompare: 'Cryptocompare'

    def __new__(
            cls,
            data_directory: FilePath = None,
            history_date_start: str = None,
            cryptocompare: 'Cryptocompare' = None,
    ):
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance
        assert data_directory, 'arguments should be given at the first instantiation'
        assert history_date_start, 'arguments should be given at the first instantiation'
        assert cryptocompare, 'arguments should be given at the first instantiation'

        PriceHistorian.__instance = object.__new__(cls)

        # get the start date for historical data
        PriceHistorian._historical_data_start = createTimeStamp(
            datestr=history_date_start,
            formatstr="%d/%m/%Y",
        )
        PriceHistorian._cryptocompare = cryptocompare

        return PriceHistorian.__instance

    @staticmethod
    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
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
            return Price(FVal('1'))

        if from_asset.is_fiat() and to_asset.is_fiat():
            # if we are querying historical forex data then try something other than cryptocompare
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=FiatAsset(from_asset.identifier),
                to_fiat_currency=FiatAsset(to_asset.identifier),
                timestamp=timestamp,
            )
            if price is not None:
                return price
            # else cryptocompare also has historical fiat to fiat data

        instance = PriceHistorian()
        return instance._cryptocompare.query_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            historical_data_start=instance._historical_data_start,
        )


class TradesHistorian():

    def __init__(
            self,
            user_directory: FilePath,
            db: DBHandler,
            eth_accounts: List[EthAddress],
            historical_data_start: str,
            msg_aggregator: MessagesAggregator,
    ):

        self.poloniex = None
        self.kraken = None
        self.bittrex = None
        self.bitmex = None
        self.binance = None
        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.eth_accounts = eth_accounts
        # get the start date for historical data
        self.historical_data_start = createTimeStamp(historical_data_start, formatstr="%d/%m/%Y")
        # If this flag is true we attempt to read from the manually logged margin positions file
        self.read_manual_margin_positions = True

    def set_exchange(self, name, exchange_obj):
        if getattr(self, name) is None or exchange_obj is None:
            setattr(self, name, exchange_obj)
        elif exchange_obj:
            raise ValueError(
                'Attempted to set {} exchange in TradesHistorian while it was '
                'already set'.format(name),
            )

    def query_poloniex_history(self, history, asset_movements, start_ts, end_ts, end_at_least_ts):
        if not self.poloniex:
            return history, asset_movements, [], []

        log.info(
            'Starting poloniex history query',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )
        poloniex_margin_trades = list()
        polo_loans = list()
        polo_history = self.poloniex.query_trade_history(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )

        for pair, trades in polo_history.items():
            for trade in trades:
                category = trade['category']

                try:
                    if category == 'exchange' or category == 'settlement':
                        history.append(trade_from_poloniex(trade, pair))
                    elif category == 'marginTrade':
                        if not self.read_manual_margin_positions:
                            poloniex_margin_trades.append(trade_from_poloniex(trade, pair))
                    else:
                        raise ValueError(
                            f'Unexpected poloniex trade category: {category}',
                        )
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found poloniex trade with unsupported asset'
                        f' {e.asset_name}. Ignoring it.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found poloniex trade with unknown asset'
                        f' {e.asset_name}. Ignoring it.',
                    )
                    continue
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

        polo_loans = self.poloniex.query_loan_history(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
            from_csv=True,
        )
        polo_loans = process_polo_loans(polo_loans, start_ts, end_ts)
        polo_asset_movements = self.poloniex.query_deposits_withdrawals(
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

        if self.kraken is not None:
            try:
                kraken_history = self.kraken.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                for trade in kraken_history:
                    try:
                        history.append(trade_from_kraken(trade))
                    except UnknownAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found kraken trade with unknown asset '
                            f'{e.asset_name}. Ignoring it.',
                        )
                        continue
                    except UnprocessableTradePair as e:
                        self.msg_aggregator.add_warning(
                            f'Found kraken trade with unprocessable pair '
                            f'{e.pair}. Ignoring it.',
                        )

                kraken_asset_movements = self.kraken.query_deposits_withdrawals(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                asset_movements.extend(kraken_asset_movements)

            except RemoteError as e:
                empty_or_error += '\n' + str(e)

        poloniex_query_error = False
        poloniex_margin_trades = []
        polo_loans = []
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
            poloniex_query_error = True

        if self.bittrex is not None:
            try:
                bittrex_history = self.bittrex.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                for trade in bittrex_history:
                    try:
                        history.append(
                            trade_from_bittrex(trade),
                        )
                    except UnknownAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found bittrex trade with unknown asset '
                            f'{e.asset_name}. Ignoring it.',
                        )
                        continue
                    except UnsupportedAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found bittrex trade with unsupported asset '
                            f'{e.asset_name}. Ignoring it.',
                        )
                        continue
                    except UnprocessableTradePair as e:
                        self.msg_aggregator.add_warning(
                            f'Found bittrex trade with unprocessable pair '
                            f'{e.pair}. Ignoring it.',
                        )

            except RemoteError as e:
                empty_or_error += '\n' + str(e)

        if self.bitmex is not None:
            try:
                bitmex_history = self.bitmex.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                for trade in bitmex_history:
                    history.append(trade_from_bitmex(trade))

                bitmex_asset_movements = self.bitmex.query_deposits_withdrawals(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                asset_movements.extend(bitmex_asset_movements)

            except RemoteError as e:
                empty_or_error += '\n' + str(e)

        if self.binance is not None:
            try:
                binance_history = self.binance.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                for trade in binance_history:
                    try:
                        history.append(
                            trade_from_binance(trade, self.binance.symbols_to_pair),
                        )
                    except UnsupportedAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found binance trade with unsupported asset '
                            f'{e.asset_name}. Ignoring it.',
                        )
                        continue
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

        # Write to files
        historyfile_path = os.path.join(self.user_directory, TRADES_HISTORYFILE)
        write_tupledata_history_in_file(history, historyfile_path, start_ts, end_ts)
        if self.poloniex is not None:
            if not self.read_manual_margin_positions and not poloniex_query_error:
                marginfile_path = os.path.join(self.user_directory, MARGIN_HISTORYFILE)
                write_tupledata_history_in_file(
                    poloniex_margin_trades,
                    marginfile_path,
                    start_ts,
                    end_ts,
                )

        if not poloniex_query_error:
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
                poloniex_history_okay = True
                if self.poloniex is not None:
                    poloniex_history_okay = self.poloniex.check_trades_cache(
                        start_ts, end_at_least_ts,
                    ) is not None
                kraken_history_okay = True
                if self.kraken is not None:
                    kraken_history_okay = self.kraken.check_trades_cache(
                        start_ts, end_at_least_ts,
                    ) is not None
                bittrex_history_okay = True
                if self.bittrex is not None:
                    bittrex_history_okay = self.bittrex.check_trades_cache(
                        start_ts, end_at_least_ts,
                    ) is not None
                bitmex_history_okay = True
                if self.bitmex is not None:
                    bitmex_history_okay = self.bitmex.check_trades_cache(
                        start_ts, end_at_least_ts,
                    ) is not None
                binance_history_okay = True
                if self.binance is not None:
                    binance_history_okay = self.binance.check_trades_cache(
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
                        poloniex_history_okay and
                        kraken_history_okay and
                        bittrex_history_okay and
                        bitmex_history_okay and
                        binance_history_okay and
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
