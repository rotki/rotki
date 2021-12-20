import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.chain.ethereum.graph import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.trades import AMMTRADE_LOCATION_NAMES, AMMTrade, AMMTradeLocations
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    ETHTransactionsFilterQuery,
    LedgerActionsFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES, ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EXTERNAL_LOCATION, EthereumTransaction, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import DefiEvent
    from rotkehlchen.chain.manager import ChainManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of steps excluding the connected exchanges. Current query steps:
# eth transactions
# ledger actions
# external location trades -> len(EXTERNAL_LOCATION)
# amm trades len(AMMTradeLocations)
# makerdao dsr
# makerdao vaults
# yearn vaults
# compound
# adex staking
# aave lending
# eth2
# liquity
# Please, update this number each time a history query step is either added or removed
NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES = 10 + len(EXTERNAL_LOCATION) + len(AMMTradeLocations)


HistoryResult = Tuple[
    str,
    List[Union[Trade, MarginPosition, AMMTrade]],
    List[Loan],
    List[AssetMovement],
    List[EthereumTransaction],
    List['DefiEvent'],
    List['LedgerAction'],
]
# TRADES_LIST = List[Union[Trade, AMMTrade]]
TRADES_LIST = List[Trade]


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
        # Keeps how many trades we have found per location. Used for free user limiting
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
            filter_query: LedgerActionsFilterQuery,
            only_cache: bool,
    ) -> Tuple[List['LedgerAction'], int]:
        """Queries the ledger actions with the given filter query

        :param only_cache: Optional. If this is true then the equivalent exchange/location
         is not queried, but only what is already in the DB is returned.
        """
        location = filter_query.location
        from_ts = filter_query.from_ts
        to_ts = filter_query.to_ts
        if only_cache is False:  # query services
            for exchange in self.exchange_manager.iterate_exchanges():
                if location is None or exchange.location == location:
                    exchange.query_income_loss_expense(
                        start_ts=from_ts,
                        end_ts=to_ts,
                        only_cache=False,
                    )

        db = DBLedgerActions(self.db, self.msg_aggregator)
        has_premium = self.chain_manager.premium is not None
        actions, filter_total_found = db.get_ledger_actions_and_limit_info(
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return actions, filter_total_found

    def _query_services_for_trades(self, filter_query: TradesFilterQuery) -> None:
        """Queries all services requested for trades and writes them to the DB"""
        location = filter_query.location
        from_ts = filter_query.from_ts
        to_ts = filter_query.to_ts

        if location is not None:
            self.query_location_latest_trades(location=location, from_ts=from_ts, to_ts=to_ts)
            return

        # else query all CEXes and all AMMs
        for exchange in self.exchange_manager.iterate_exchanges():
            exchange.query_trade_history(
                start_ts=from_ts,
                end_ts=to_ts,
                only_cache=False,
            )

        # for all trades we also need the trades from the amm protocols
        if self.chain_manager.premium is not None:
            for amm_location in AMMTradeLocations:
                self.query_location_latest_trades(
                    location=amm_location,
                    from_ts=from_ts,
                    to_ts=to_ts,
                )

    def query_trades(
            self,
            filter_query: TradesFilterQuery,
            only_cache: bool,
    ) -> Tuple[TRADES_LIST, int]:
        """Queries trades for the given location and time range.
        If no location is given then all external, all exchange and DEX trades are queried.

        If only_cache is given then only trades cached in the DB are returned.
        No service is queried.

        DEX Trades are queried only if the user has premium
        If the user does not have premium then a trade limit is applied.

        Returns all trades and the full amount of trades that got found for the filter.
        May be less than returned trades if user is non premium.

        May raise:
        - RemoteError: If there are problems connecting to any of the remote exchanges
        """
        if only_cache is not True:
            self._query_services_for_trades(filter_query=filter_query)

        has_premium = self.chain_manager.premium is not None
        trades, filter_total_found = self.db.get_trades_and_limit_info(
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return trades, filter_total_found

    def query_location_latest_trades(
            self,
            location: Location,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> None:
        """Queries the service of a specific location for latest trades and saves them in the DB.
        May raise:

        - RemoteError if there is a problem with reaching the service
        """
        if location in AMMTradeLocations:
            if self.chain_manager.premium is not None:
                amm_module_name = cast(AMMTRADE_LOCATION_NAMES, str(location))
                amm_module = self.chain_manager.get_module(amm_module_name)
                if amm_module is not None:
                    amm_module.get_trades(
                        addresses=self.chain_manager.queried_addresses_for_module(amm_module_name),
                        from_timestamp=from_ts,
                        to_timestamp=to_ts,
                        only_cache=False,
                    )
        elif location in SUPPORTED_EXCHANGES:
            exchanges_list = self.exchange_manager.connected_exchanges.get(location)
            if exchanges_list is None:
                return

            for exchange in exchanges_list:
                exchange.query_trade_history(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=False,
                )

    def _query_services_for_asset_movements(self, filter_query: AssetMovementsFilterQuery) -> None:
        """Queries all services requested for asset movements and writes them to the DB"""
        location = filter_query.location
        from_ts = filter_query.from_ts
        to_ts = filter_query.to_ts

        if location is None:
            # query all CEXes
            for exchange in self.exchange_manager.iterate_exchanges():
                exchange.query_deposits_withdrawals(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=False,
                )
            return

        if location not in SUPPORTED_EXCHANGES:
            return  # nothing to do

        # otherwise it's a single connected exchange and we need to query it
        exchanges_list = self.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return

        for exchange in exchanges_list:
            exchange.query_deposits_withdrawals(
                start_ts=from_ts,
                end_ts=to_ts,
                only_cache=False,
            )

    def query_asset_movements(
            self,
            filter_query: AssetMovementsFilterQuery,
            only_cache: bool,
    ) -> Tuple[List[AssetMovement], int]:
        """Queries AssetMovements for the given filter

        If only_cache is True then only what is already in the DB is returned.
        Otherwise we query all services requested by the filter, populate the DB
        and then return.

        May raise:
        - RemoteError: If there are problems connecting to any of the remote exchanges
        """
        if only_cache is not True:
            self._query_services_for_asset_movements(filter_query=filter_query)

        has_premium = self.chain_manager.premium is not None
        asset_movements, filter_total_found = self.db.get_asset_movements_and_limit_info(
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return asset_movements, filter_total_found

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
        ledger_actions = []
        loans = []
        empty_or_error = ''

        def populate_history_cb(
                trades_history: List[Trade],
                margin_history: List[MarginPosition],
                result_asset_movements: List[AssetMovement],
                result_ledger_actions: List[LedgerAction],
                exchange_specific_data: Any,
        ) -> None:
            """This callback will run for succesfull exchange history query"""
            history.extend(trades_history)
            history.extend(margin_history)
            asset_movements.extend(result_asset_movements)
            ledger_actions.extend(result_ledger_actions)

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

        for exchange in self.exchange_manager.iterate_exchanges():
            self.processing_state_name = f'Querying {exchange.name} exchange history'
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
            filter_query = ETHTransactionsFilterQuery.make(
                order_ascending=True,  # for history processing we need oldest first
                limit=None,
                offset=None,
                addresses=None,
                # We need to have history of transactions since before the range
                from_ts=Timestamp(0),
                to_ts=end_ts,
            )
            ethtx_module = EthTransactions(ethereum=self.chain_manager.ethereum, database=self.db)
            eth_transactions, _ = ethtx_module.query(
                filter_query=filter_query,
                with_limit=False,  # at the moment ignore the limit for historical processing
                only_cache=False,
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

        # Include all external trades and trades from external exchanges
        for location in EXTERNAL_LOCATION:
            self.processing_state_name = f'Querying {location} trades history'
            external_trades = self.db.get_trades(
                filter_query=TradesFilterQuery.make(location=location),
                has_premium=True,  # we need all trades for accounting -- limit happens later
            )
            history.extend(external_trades)
            step = self._increase_progress(step, total_steps)

        # include the ledger actions from offline sources
        self.processing_state_name = 'Querying ledger actions history'
        offline_ledger_actions, _ = self.query_ledger_actions(
            filter_query=LedgerActionsFilterQuery.make(),
            only_cache=True,
        )
        unique_ledger_actions = list(set(offline_ledger_actions) - set(ledger_actions))
        ledger_actions.extend(unique_ledger_actions)
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
            try:
                # we need to process all events from history start
                defi_events.extend(compound.get_history_events(
                    from_timestamp=Timestamp(0),
                    to_timestamp=end_ts,
                    addresses=self.chain_manager.queried_addresses_for_module('compound'),
                ))
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(protocol="Compound", error_msg=str(e)),
                )

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
        step = self._increase_progress(step, total_steps)

        # include eth2 staking events
        eth2 = self.chain_manager.get_module('eth2')
        if eth2 is not None and has_premium:
            self.processing_state_name = 'Querying ETH2 staking history'
            try:
                eth2_events = self.chain_manager.get_eth2_history_events(
                    from_timestamp=start_ts,
                    to_timestamp=end_ts,
                )
                defi_events.extend(eth2_events)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Eth2 events are not included in the PnL report due to {str(e)}',
                )

        step = self._increase_progress(step, total_steps)

        # include liquity events
        liquity = self.chain_manager.get_module('liquity')
        if liquity is not None and has_premium:
            self.processing_state_name = 'Querying Liquity staking history'
            defi_events.extend(liquity.get_history_events(
                from_timestamp=start_ts,
                to_timestamp=end_ts,
                addresses=self.chain_manager.queried_addresses_for_module('liquity'),
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
