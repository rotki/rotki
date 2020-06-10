import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from rotkehlchen.accounting.structures import DefiEvent, DefiEventType
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.constants.assets import A_DAI, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.transactions import query_ethereum_transactions
from rotkehlchen.typing import EthereumTransaction, FilePath, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


HistoryResult = Tuple[
    str,
    List[Union[Trade, MarginPosition]],
    List[Loan],
    List[AssetMovement],
    List[EthereumTransaction],
    List[DefiEvent],
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

    return trades_list[start_idx:end_idx] if start_idx is not None else []


class TradesHistorian():

    def __init__(
            self,
            user_directory: FilePath,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            chain_manager: ChainManager,
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.chain_manager = chain_manager

    def get_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            has_premium: bool,
    ) -> HistoryResult:
        """Creates trades and loans history from start_ts to end_ts"""
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        now = ts_now()
        # start creating the all trades history list
        history: List[Union[Trade, MarginPosition]] = []
        asset_movements = []
        loans = []
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
                loans.extend(process_polo_loans(
                    msg_aggregator=self.msg_aggregator,
                    data=polo_loans_data,
                    # We need to have full history of loans available
                    start_ts=Timestamp(0),
                    end_ts=now,
                ))

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for _, exchange in self.exchange_manager.connected_exchanges.items():
            exchange.query_history_with_callbacks(
                # We need to have full history of exchanges available
                start_ts=Timestamp(0),
                end_ts=now,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )

        try:
            eth_transactions = query_ethereum_transactions(
                database=self.db,
                etherscan=self.chain_manager.ethereum.etherscan,
                # We need to have full history of transactions available
                from_ts=Timestamp(0),
                to_ts=now,
            )
        except RemoteError as e:
            eth_transactions = []
            msg = str(e)
            self.msg_aggregator.add_error(
                f'There was an error when querying etherscan for ethereum transactions: {msg}'
                f'The final history result will not include ethereum transactions',
            )
            empty_or_error += '\n' + msg

        # Include the external trades in the history
        external_trades = self.db.get_trades(
            # We need to have full history of trades available
            from_ts=Timestamp(0),
            to_ts=now,
            location=Location.EXTERNAL,
        )
        history.extend(external_trades)

        # Include makerdao DSR gains and vault events
        defi_events = []
        if self.chain_manager.makerdao and has_premium:
            dsr_gains = self.chain_manager.makerdao.get_dsr_gains_in_period(
                from_ts=start_ts,
                to_ts=end_ts,
            )
            log.debug('DSR GAINS: {dsr_gains}')
            for gain, timestamp in dsr_gains:
                if gain > ZERO:
                    defi_events.append(DefiEvent(
                        timestamp=timestamp,
                        event_type=DefiEventType.DSR_LOAN_GAIN,
                        asset=A_DAI,
                        amount=gain,
                    ))

            vault_details = self.chain_manager.makerdao.get_vault_details()
            # We count the loss on a vault in the period if the last event is within
            # the given period. It's not a very accurate approach but it's good enough
            # for now. A more detailed approach would need archive node or log querying
            # to find owed debt at any given timestamp
            for detail in vault_details:
                last_event_ts = detail.events[-1].timestamp
                if last_event_ts >= start_ts and last_event_ts <= end_ts:
                    defi_events.append(DefiEvent(
                        timestamp=last_event_ts,
                        event_type=DefiEventType.MAKERDAO_VAULT_LOSS,
                        asset=A_USD,
                        amount=detail.total_liquidated_usd + detail.total_interest_owed,
                    ))

        history.sort(key=lambda trade: action_get_timestamp(trade))
        return (
            empty_or_error,
            history,
            loans,
            asset_movements,
            eth_transactions,
            defi_events,
        )
