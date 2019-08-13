import logging
import os
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    DeserializationError,
    HistoryCacheInvalid,
    RemoteError,
    UnknownAsset,
    UnsupportedAsset,
)
from rotkehlchen.exchanges import Binance, Bitmex, Bittrex, Kraken, Poloniex
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    MarginPosition,
    Trade,
    asset_movements_from_dictlist,
    trades_from_dictlist,
)
from rotkehlchen.exchanges.exchange import data_up_todate
from rotkehlchen.exchanges.poloniex import process_polo_loans, trade_from_poloniex
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.transactions import query_etherscan_for_transactions, transactions_from_dictlist
from rotkehlchen.typing import EthAddress, FiatAsset, FilePath, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    create_timestamp,
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


def delete_all_history_cache(directory: FilePath) -> None:
    try:
        os.remove(os.path.join(directory, TRADES_HISTORYFILE))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, 'kraken_trades.json'))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, 'bittrex_trades.json'))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, 'binance_trades.json'))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, 'bitmex_trades.json'))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, 'poloniex_trades.json'))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, LOANS_HISTORYFILE))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, MARGIN_HISTORYFILE))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, MANUAL_MARGINS_LOGFILE))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, ASSETMOVEMENTS_HISTORYFILE))
    except OSError:
        pass
    try:
        os.remove(os.path.join(directory, ETHEREUM_TX_LOGFILE))
    except OSError:
        pass


def maybe_add_external_trades_to_history(
        db: DBHandler,
        start_ts: Timestamp,
        end_ts: Timestamp,
        history: List[Trade],
        msg_aggregator: MessagesAggregator,
) -> List[Trade]:
    """
    Queries the DB to get any external trades, adds them to the provided history and returns it.

    If there is an unexpected error at the external trade deserialization an error is logged.
    """
    serialized_external_trades = db.get_trades()
    try:
        external_trades = trades_from_dictlist(
            given_trades=serialized_external_trades,
            start_ts=start_ts,
            end_ts=end_ts,
            location='external trades',
            msg_aggregator=msg_aggregator,
        )
    except (KeyError, DeserializationError):
        msg_aggregator.add_error('External trades in the DB are in an unrecognized format')
        return history

    history.extend(external_trades)
    history.sort(key=lambda trade: trade.timestamp)

    return history


def do_read_manual_margin_positions(user_directory: FilePath) -> List[MarginPosition]:
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

    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
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


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
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
        PriceHistorian._historical_data_start = create_timestamp(
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
            from_asset: The ticker symbol of the asset for which we want to know
                        the price.
            to_asset: The ticker symbol of the asset against which we want to
                      know the price.
            timestamp: The timestamp at which to query the price
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
            msg_aggregator: MessagesAggregator,
    ):

        self.poloniex: Optional[Poloniex] = None
        self.kraken: Optional[Kraken] = None
        self.bittrex: Optional[Bittrex] = None
        self.bitmex: Optional[Bitmex] = None
        self.binance: Optional[Binance] = None
        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.eth_accounts = eth_accounts
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

    def query_poloniex_history(
            self,
            history: List[Trade],
            asset_movements: List[AssetMovement],
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> Tuple[
        List[Trade],
        List[AssetMovement],
        Union[List[MarginPosition], List[Trade]],
        List[Loan],
    ]:
        # The poloniex margin trades list can either be normal trades list or
        # if we read manual margin positions a List or MarginPosition
        # TODO: This is pretty ugly. Simply remove the manual MarginPosition trades
        # possibility from poloniex. Will make it easier to maintain
        poloniex_margin_trades: List[Trade] = []
        poloniex_manual_margin_positions: List[MarginPosition] = []
        polo_loans: List[Loan] = list()
        if not self.poloniex:
            return history, asset_movements, poloniex_margin_trades, polo_loans

        log.info(
            'Starting poloniex history query',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )

        polo_trades = self.poloniex.query_trade_history(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )
        history.extend(polo_trades)

        margin_return_list: Union[List[MarginPosition], List[Trade]]
        if self.read_manual_margin_positions:
            # Just read the manual positions log and make virtual trades that
            # correspond to the profits
            poloniex_manual_margin_positions = do_read_manual_margin_positions(
                self.user_directory,
            )
            margin_return_list = poloniex_manual_margin_positions
        else:
            poloniex_margin_trades.sort(key=lambda trade: trade.timestamp)
            poloniex_margin_trades = limit_trade_list_to_period(
                poloniex_margin_trades,
                start_ts,
                end_ts,
            )
            margin_return_list = poloniex_margin_trades

        polo_loans_data = self.poloniex.query_loan_history(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
            from_csv=True,
        )
        polo_loans = process_polo_loans(self.msg_aggregator, polo_loans_data, start_ts, end_ts)
        polo_asset_movements = self.poloniex.query_deposits_withdrawals(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )
        asset_movements.extend(polo_asset_movements)

        return history, asset_movements, margin_return_list, polo_loans

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
                history.extend(kraken_history)

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
                history.extend(bittrex_history)

                bittrex_asset_movements = self.bittrex.query_deposits_withdrawals(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                asset_movements.extend(bittrex_asset_movements)

            except RemoteError as e:
                empty_or_error += '\n' + str(e)

        if self.bitmex is not None:
            try:
                bitmex_history = self.bitmex.query_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                history.extend(bitmex_history)
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
                history.extend(binance_history)

                binance_asset_movements = self.binance.query_deposits_withdrawals(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_at_least_ts=end_at_least_ts,
                )
                asset_movements.extend(binance_asset_movements)

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
        history = maybe_add_external_trades_to_history(
            db=self.db,
            start_ts=start_ts,
            end_ts=end_ts,
            history=history,
            msg_aggregator=self.msg_aggregator,
        )

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
        log.info(
            'Get or create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )
        try:
            (
                history_trades,
                poloniex_margin_trades,
                polo_loans,
                asset_movements,
                eth_transactions,
            ) = self.get_cached_history(start_ts, end_ts, end_at_least_ts)
            return (
                '',
                history_trades,
                poloniex_margin_trades,
                polo_loans,
                asset_movements,
                eth_transactions,
            )
        except HistoryCacheInvalid:
            # If for some reason cache history is invalidated then we should
            # delete all history related cache files
            delete_all_history_cache(self.user_directory)
            return self.create_history(start_ts, end_ts, end_at_least_ts)

    def _get_cached_asset_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> List[AssetMovement]:
        """
        Attetmps to read the cache of asset movements and returns a list of them.

        If there is a problem can raise HistoryCacheInvalid
        """
        assetmovementsfile_path = os.path.join(
            self.user_directory,
            ASSETMOVEMENTS_HISTORYFILE,
        )
        asset_movements_contents = get_jsonfile_contents_or_empty_dict(
            FilePath(assetmovementsfile_path),
        )
        asset_movements_history_is_okay = data_up_todate(
            asset_movements_contents,
            start_ts,
            end_at_least_ts,
        )
        if not asset_movements_history_is_okay:
            raise HistoryCacheInvalid('Asset Movements cache is invalid')

        try:
            asset_movements = asset_movements_from_dictlist(
                asset_movements_contents['data'],
                start_ts,
                end_ts,
            )
        except (KeyError, DeserializationError, UnknownAsset) as e:
            raise HistoryCacheInvalid(f'Asset Movements cache is invalid because of {str(e)}')

        return asset_movements

    def get_cached_history(self, start_ts, end_ts, end_at_least_ts=None):
        """Gets all the cached history data instead of querying all external sources
        to create the history through create_history()

        Can raise:
            - HistoryCacheInvalid:
                If any of the cache files are corrupt in any way, missing or
                do not cover the given time range
        """
        if end_at_least_ts is None:
            end_at_least_ts = end_ts

        historyfile_path = os.path.join(self.user_directory, TRADES_HISTORYFILE)
        if not os.path.isfile(historyfile_path):
            raise HistoryCacheInvalid()

        with open(historyfile_path, 'r') as infile:
            try:
                history_json_data = rlk_jsonloads(infile.read())
            except JSONDecodeError:
                pass

        if not data_up_todate(history_json_data, start_ts, end_at_least_ts):
            raise HistoryCacheInvalid('Historical trades cache invalid')
        try:
            history_trades = trades_from_dictlist(
                given_trades=history_json_data['data'],
                start_ts=start_ts,
                end_ts=end_ts,
                location='historical trades',
                msg_aggregator=self.msg_aggregator,
            )
        except (KeyError, DeserializationError):
            raise HistoryCacheInvalid('Historical trades cache invalid')

        history_trades = maybe_add_external_trades_to_history(
            db=self.db,
            start_ts=start_ts,
            end_ts=end_ts,
            history=history_trades,
            msg_aggregator=self.msg_aggregator,
        )

        kraken_okay = (
            self.kraken is None or
            self.kraken.check_trades_cache(
                start_ts, end_at_least_ts,
            ) is not None
        )
        if not kraken_okay:
            raise HistoryCacheInvalid('Kraken cache is invalid')

        bittrex_okay = (
            self.bittrex is None or
            self.bittrex.check_trades_cache(
                start_ts, end_at_least_ts,
            ) is not None
        )
        if not bittrex_okay:
            raise HistoryCacheInvalid('Bittrex cache is invalid')

        binance_okay = (
            self.binance is None or
            self.binance.check_trades_cache(
                start_ts, end_at_least_ts,
            ) is not None
        )
        if not binance_okay:
            raise HistoryCacheInvalid('Binance cache is invalid')

        bitmex_okay = (
            self.bitmex is None or
            self.bitmex.check_trades_cache(
                start_ts, end_at_least_ts,
            ) is not None
        )
        if not bitmex_okay:
            raise HistoryCacheInvalid('Bitmex cache is invalid')

        # Poloniex specific
        loan_data = []
        if self.poloniex:
            if not self.poloniex.check_trades_cache(start_ts, end_at_least_ts):
                raise HistoryCacheInvalid('Poloniex cache is invalid')

            loansfile_path = os.path.join(self.user_directory, LOANS_HISTORYFILE)
            loan_file_contents = get_jsonfile_contents_or_empty_dict(loansfile_path)
            loan_history_is_okay = data_up_todate(
                loan_file_contents,
                start_ts,
                end_at_least_ts,
            )
            if not loan_history_is_okay:
                raise HistoryCacheInvalid('Poloniex loan cache is invalid')
            loan_data = loan_file_contents['data']

        # margin positions that have been manually input
        if not self.read_manual_margin_positions:
            marginfile_path = os.path.join(self.user_directory, MARGIN_HISTORYFILE)
            margin_file_contents = get_jsonfile_contents_or_empty_dict(marginfile_path)
            margin_history_is_okay = data_up_todate(
                margin_file_contents,
                start_ts,
                end_at_least_ts,
            )
            if not margin_history_is_okay:
                raise HistoryCacheInvalid('Margin Positions cache is invalid')

            try:
                margin_trades = trades_from_dictlist(
                    given_trades=margin_file_contents['data'],
                    start_ts=start_ts,
                    end_ts=end_ts,
                    location='Margin position trades',
                    msg_aggregator=self.msg_aggregator,
                )
            except (KeyError, DeserializationError):
                raise HistoryCacheInvalid('Margin Positions cache is invalid')

        else:
            margin_trades = do_read_manual_margin_positions(
                self.user_directory,
            )

        asset_movements = self._get_cached_asset_movements(
            start_ts=start_ts,
            end_ts=end_ts,
            end_at_least_ts=end_at_least_ts,
        )

        eth_tx_log_path = os.path.join(self.user_directory, ETHEREUM_TX_LOGFILE)
        eth_tx_log_contents = get_jsonfile_contents_or_empty_dict(eth_tx_log_path)
        eth_tx_log_history_is_okay = data_up_todate(
            eth_tx_log_contents,
            start_ts,
            end_at_least_ts,
        )
        if not eth_tx_log_history_is_okay:
            raise HistoryCacheInvalid('Ethereum transactions cache is invalid')

        try:
            eth_transactions = transactions_from_dictlist(
                eth_tx_log_contents['data'],
                start_ts,
                end_ts,
            )
        except KeyError:
            raise HistoryCacheInvalid('Ethereum transactions cache is invalid')

        # make sure that this is the same as what is returned
        # from create_history, except for the first argument
        return (
            history_trades,
            margin_trades,
            loan_data,
            asset_movements,
            eth_transactions,
        )
