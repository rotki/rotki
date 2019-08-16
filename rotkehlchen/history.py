import logging
import os
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, List, Optional, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import DeserializationError, HistoryCacheInvalid, RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    MarginPosition,
    Trade,
    asset_movements_from_dictlist,
    trades_from_dictlist,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface, data_up_todate
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.transactions import query_etherscan_for_transactions, transactions_from_dictlist
from rotkehlchen.typing import EthAddress, FiatAsset, FilePath, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
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
        history: List[Union[Trade, MarginPosition]],
        msg_aggregator: MessagesAggregator,
) -> List[Union[Trade, MarginPosition]]:
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
    # TODO: We also sort in one other place in this file and also in accountant.py
    #       Get rid of the unneeded cases?
    history.sort(key=lambda trade: action_get_timestamp(trade))

    return history


def write_tupledata_history_in_file(history, filepath, start_ts, end_ts):
    out_history = [tr._asdict() for tr in history]
    write_history_data_in_file(out_history, filepath, start_ts, end_ts)


def limit_trade_list_to_period(
        trades_list: List[Union[Trade, MarginPosition]],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[Union[Trade, MarginPosition]]:
    """Accepts a SORTED by timestamp trades_list and returns a shortened version
    of that list limited to a specific time period"""

    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    for idx, trade in enumerate(trades_list):
        timestamp = action_get_timestamp(trade)
        if start_idx is None and timestamp >= start_ts:
            start_idx = idx

        if end_idx is None and timestamp > end_ts:
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

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.eth_accounts = eth_accounts
        self.connected_exchanges: List[ExchangeInterface] = []

    def set_exchange(self, name, exchange_obj):
        if getattr(self, name) is None or exchange_obj is None:
            setattr(self, name, exchange_obj)
        elif exchange_obj:
            raise ValueError(
                'Attempted to set {} exchange in TradesHistorian while it was '
                'already set'.format(name),
            )

    def create_history(self, start_ts: Timestamp, end_ts: Timestamp, end_at_least_ts: Timestamp):
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
        history: List[Union[Trade, MarginPosition]] = list()
        asset_movements = list()
        polo_loans = list()
        empty_or_error = ''

        def populate_history_cb(
                result_history: Union[List[Trade], List[MarginPosition]],
                result_asset_movements: List[AssetMovement],
                exchange_specific_data: Any,
        ) -> None:
            """This callback will run for succesfull exchange history query"""
            history.extend(result_history)
            asset_movements.extend(result_asset_movements)

            if exchange_specific_data:
                # This can only be poloniex at the moment
                polo_loans_data = exchange_specific_data
                polo_loans.extend(process_polo_loans(
                    msg_aggregator=self.msg_aggregator,
                    data=polo_loans_data,
                    start_ts=start_ts,
                    end_ts=end_ts,
                ))
                loansfile_path = os.path.join(self.user_directory, LOANS_HISTORYFILE)
                write_history_data_in_file(polo_loans, loansfile_path, start_ts, end_ts)

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for exchange in self.connected_exchanges:
            exchange.query_history_with_callbacks(
                start_ts=start_ts,
                end_ts=end_ts,
                end_at_least_ts=end_at_least_ts,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )

        try:
            eth_transactions = query_etherscan_for_transactions(self.eth_accounts)
        except RemoteError as e:
            empty_or_error += '\n' + str(e)

        # We sort it here ... but when accounting runs through the entire actions list,
        # it resorts, so unless the fact that we sort is used somewhere else too, perhaps
        # we can skip it?
        history.sort(key=lambda trade: action_get_timestamp(trade))
        history = limit_trade_list_to_period(history, start_ts, end_ts)

        # Write to files
        historyfile_path = os.path.join(self.user_directory, TRADES_HISTORYFILE)
        write_tupledata_history_in_file(history, historyfile_path, start_ts, end_ts)

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
                polo_loans,
                asset_movements,
                eth_transactions,
            ) = self.get_cached_history(start_ts, end_ts, end_at_least_ts)
            return (
                '',
                history_trades,
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

        # Check the cache of each exchange
        poloniex = None
        for exchange in self.connected_exchanges:
            if exchange.name == 'poloniex':
                poloniex = exchange
            if not exchange.check_trades_cache(start_ts, end_at_least_ts):
                raise HistoryCacheInvalid(f'{exchange.name} cache is invalid')

        # Poloniex specific
        loan_data = []
        if poloniex:
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
            loan_data,
            asset_movements,
            eth_transactions,
        )
