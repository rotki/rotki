import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.transactions import query_ethereum_transactions
from rotkehlchen.typing import EthereumTransaction, FilePath, Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import create_timestamp

if TYPE_CHECKING:
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


HistoryResult = Tuple[
    str,
    List[Union[Trade, MarginPosition]],
    List[Loan],
    List[AssetMovement],
    List[EthereumTransaction],
]


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


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
    _historical_data_start: Timestamp
    _cryptocompare: 'Cryptocompare'

    def __new__(
            cls,
            data_directory: FilePath = None,
            history_date_start: str = None,
            cryptocompare: 'Cryptocompare' = None,
    ) -> 'PriceHistorian':
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
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
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
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            etherscan: Etherscan,
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.etherscan = etherscan

    def create_history(self, start_ts: Timestamp, end_ts: Timestamp) -> HistoryResult:
        """Creates trades and loans history from start_ts to end_ts"""
        log.info(
            'Starting trade history creation',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        # start creating the all trades history list
        history: List[Union[Trade, MarginPosition]] = list()
        asset_movements = list()
        polo_loans = list()
        empty_or_error = ''

        def populate_history_cb(
                trades_history: List[Trade],
                margin_history: List[MarginPosition],
                result_asset_movements: List[AssetMovement],
                exchange_specific_data: Any,
        ) -> None:
            """This callback will run for succesfull exchange history query"""
            history.extend(trades_history)
            history.extend(margin_history)
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

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for _, exchange in self.exchange_manager.connected_exchanges.items():
            exchange.query_history_with_callbacks(
                start_ts=start_ts,
                end_ts=end_ts,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )

        try:
            eth_transactions = query_ethereum_transactions(
                etherscan=self.etherscan,
                from_ts=start_ts,
                to_ts=end_ts,
            )
        except RemoteError as e:
            eth_transactions = []
            msg = str(e)
            self.msg_aggregator.add_error(
                f'There was an error when querying etherscan for ethereum transactions: {msg}'
                f'The final history result will not include ethereum transactions',
            )
            empty_or_error += '\n' + msg

        # We sort it here ... but when accounting runs through the entire actions list,
        # it resorts, so unless the fact that we sort is used somewhere else too, perhaps
        # we can skip it?
        history.sort(key=lambda trade: action_get_timestamp(trade))
        history = limit_trade_list_to_period(history, start_ts, end_ts)

        # Include the external trades in the history
        external_trades = self.db.get_trades(
            from_ts=start_ts,
            to_ts=end_ts,
            location=Location.EXTERNAL,
        )
        history.extend(external_trades)
        history.sort(key=lambda trade: action_get_timestamp(trade))

        return (
            empty_or_error,
            history,
            polo_loans,
            asset_movements,
            eth_transactions,
        )

    def get_history(self, start_ts: Timestamp, end_ts: Timestamp) -> HistoryResult:
        """Gets or creates trades and loans history from start_ts to end_ts or if
        `end_at_least` is given and we have a cache history which satisfies it we
        return the cache
        """
        log.info(
            'Get or create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        # TODO: Perhaps get rid of the extra function call since the caches
        # are no longer used here?
        return self.create_history(start_ts, end_ts)
