import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

from rotkehlchen.chain.ethereum.trades import AMMTRADE_LOCATION_NAMES, AMMTrade, AMMTradeLocations
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EthereumTransaction, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import DefiEvent, LedgerAction
    from rotkehlchen.chain.manager import ChainManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Number of steps excluding the connected exchanges. Current query steps:
# eth transactions
# ledger actions
# external trades: balancer, uniswap
# makerdao dsr
# makerdao vaults
# yearn vaults
# compound
# adex staking
# aave lending
# eth2
# Please, update this number each time a history query step is either added or removed
NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES = 11
FREE_LEDGER_ACTIONS_LIMIT = 50

HistoryResult = Tuple[
    str,
    List[Union[Trade, MarginPosition, AMMTrade]],
    List[Loan],
    List[AssetMovement],
    List[EthereumTransaction],
    List['DefiEvent'],
    List['LedgerAction'],
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


class EventsHistorian():

    def __init__(
            self,
            user_directory: Path,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            chain_manager: 'ChainManager',
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.chain_manager = chain_manager
        db_settings = self.db.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime
        self._reset_variables()

    def timestamp_to_date(self, timestamp: Timestamp) -> str:
        return timestamp_to_date(
            timestamp,
            formatstr=self.dateformat,
            treat_as_local=self.datelocaltime,
        )

    def _reset_variables(self) -> None:
        self.processing_state_name = 'Starting query of historical events'
        self.progress = ZERO
        db_settings = self.db.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime

    def _increase_progress(self, step: int, total_steps: int) -> int:
        step += 1
        self.progress = FVal(step / total_steps) * 100
        return step

    def query_ledger_actions(
            self,
            has_premium: bool,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            location: Optional[Location] = None,
    ) -> Tuple[List['LedgerAction'], int]:
        """Queries the ledger actions from the DB and applies the free version limit

        TODO: Since we always query all in one call, the limiting will work, but if we start
        batch querying by time then we need to amend the logic of limiting here.
        Would need to use the same logic we do with trades. Using db entries count
        and count what all calls return and what is sums up to
        """
        db = DBLedgerActions(self.db, self.msg_aggregator)
        actions = db.get_ledger_actions(from_ts=from_ts, to_ts=to_ts, location=location)
        original_length = len(actions)
        if has_premium is False:
            actions = actions[:FREE_LEDGER_ACTIONS_LIMIT]

        return actions, original_length

    def get_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            has_premium: bool,
    ) -> HistoryResult:
        """Creates trades and loans history from start_ts to end_ts"""
        self._reset_variables()
        step = 0
        total_steps = len(self.exchange_manager.connected_exchanges) + NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES  # noqa: E501
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        # start creating the all trades history list
        history: List[Union[Trade, MarginPosition, AMMTrade]] = []
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
                    # We need to have history of loans since before the range
                    start_ts=Timestamp(0),
                    end_ts=end_ts,
                ))

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for name, exchange in self.exchange_manager.connected_exchanges.items():
            self.processing_state_name = f'Querying {name} exchange history'
            exchange.query_history_with_callbacks(
                # We need to have history of exchanges since before the range
                start_ts=Timestamp(0),
                end_ts=end_ts,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )
            step = self._increase_progress(step, total_steps)

        try:
            self.processing_state_name = 'Querying ethereum transactions history'
            eth_transactions = self.chain_manager.ethereum.transactions.query(
                addresses=None,  # all addresses
                # We need to have history of transactions since before the range
                from_ts=Timestamp(0),
                to_ts=end_ts,
                with_limit=False,  # at the moment ignore the limit for historical processing,
                recent_first=False,  # for history processing we need oldest first
            )
        except RemoteError as e:
            eth_transactions = []
            msg = str(e)
            self.msg_aggregator.add_error(
                f'There was an error when querying etherscan for ethereum transactions: {msg}'
                f'The final history result will not include ethereum transactions',
            )
            empty_or_error += '\n' + msg
        step = self._increase_progress(step, total_steps)

        # Include the external trades in the history
        self.processing_state_name = 'Querying external trades history'
        external_trades = self.db.get_trades(
            # We need to have history of trades since before the range
            from_ts=Timestamp(0),
            to_ts=end_ts,
            location=Location.EXTERNAL,
        )
        history.extend(external_trades)
        step = self._increase_progress(step, total_steps)

        # include the ledger actions
        self.processing_state_name = 'Querying ledger actions history'
        ledger_actions, _ = self.query_ledger_actions(has_premium, from_ts=start_ts, to_ts=end_ts)
        step = self._increase_progress(step, total_steps)

        # include AMM trades: balancer, uniswap
        for amm_location in AMMTradeLocations:
            amm_module_name = cast(AMMTRADE_LOCATION_NAMES, str(amm_location))
            amm_module = self.chain_manager.get_module(amm_module_name)
            if has_premium and amm_module:
                self.processing_state_name = f'Querying {amm_module_name} trade history'
                amm_module_trades = amm_module.get_trades(
                    addresses=self.chain_manager.queried_addresses_for_module(amm_module_name),
                    from_timestamp=Timestamp(0),
                    to_timestamp=end_ts,
                    only_cache=False,
                )
                history.extend(amm_module_trades)
            step = self._increase_progress(step, total_steps)

        # Include makerdao DSR gains
        defi_events = []
        makerdao_dsr = self.chain_manager.get_module('makerdao_dsr')
        if makerdao_dsr and has_premium:
            self.processing_state_name = 'Querying makerDAO DSR history'
            defi_events.extend(makerdao_dsr.get_history_events(
                from_timestamp=Timestamp(0),  # we need to process all events from history start
                to_timestamp=end_ts,
            ))
        step = self._increase_progress(step, total_steps)

        # Include makerdao vault events
        makerdao_vaults = self.chain_manager.get_module('makerdao_vaults')
        if makerdao_vaults and has_premium:
            self.processing_state_name = 'Querying makerDAO vaults history'
            defi_events.extend(makerdao_vaults.get_history_events(
                from_timestamp=Timestamp(0),  # we need to process all events from history start
                to_timestamp=end_ts,
            ))
        step = self._increase_progress(step, total_steps)

        # include yearn vault events
        yearn_vaults = self.chain_manager.get_module('yearn_vaults')
        if yearn_vaults and has_premium:
            self.processing_state_name = 'Querying yearn vaults history'
            defi_events.extend(yearn_vaults.get_history_events(
                from_timestamp=Timestamp(0),  # we need to process all events from history start
                to_timestamp=end_ts,
                addresses=self.chain_manager.queried_addresses_for_module('yearn_vaults'),
            ))
        step = self._increase_progress(step, total_steps)

        # include compound events
        compound = self.chain_manager.get_module('compound')
        if compound and has_premium:
            self.processing_state_name = 'Querying compound history'
            defi_events.extend(compound.get_history_events(
                from_timestamp=Timestamp(0),  # we need to process all events from history start
                to_timestamp=end_ts,
                addresses=self.chain_manager.queried_addresses_for_module('compound'),
            ))
        step = self._increase_progress(step, total_steps)

        # include adex events
        adex = self.chain_manager.get_module('adex')
        if adex is not None and has_premium:
            self.processing_state_name = 'Querying adex staking history'
            defi_events.extend(adex.get_history_events(
                from_timestamp=start_ts,
                to_timestamp=end_ts,
                addresses=self.chain_manager.queried_addresses_for_module('adex'),
            ))
        step = self._increase_progress(step, total_steps)

        # include aave events
        aave = self.chain_manager.get_module('aave')
        if aave is not None and has_premium:
            self.processing_state_name = 'Querying aave history'
            defi_events.extend(aave.get_history_events(
                from_timestamp=start_ts,
                to_timestamp=end_ts,
                addresses=self.chain_manager.queried_addresses_for_module('aave'),
            ))
        self._increase_progress(step, total_steps)

        # include eth2 staking events
        if has_premium:
            self.processing_state_name = 'Querying ETH2 staking history'
            defi_events.extend(self.chain_manager.get_eth2_history_events(
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            ))
        self._increase_progress(step, total_steps)

        history.sort(key=action_get_timestamp)
        return (
            empty_or_error,
            history,
            loans,
            asset_movements,
            eth_transactions,
            defi_events,
            ledger_actions,
        )
