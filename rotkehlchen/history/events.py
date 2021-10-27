import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast, overload

from typing_extensions import Literal

from rotkehlchen.chain.ethereum.graph import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.trades import AMMTRADE_LOCATION_NAMES, AMMTrade, AMMTradeLocations
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.manager import ALL_SUPPORTED_EXCHANGES, ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    EXTERNAL_EXCHANGES,
    EXTERNAL_LOCATION,
    EthereumTransaction,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.accounting.ledger_actions import LedgerAction
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
TRADES_LIST = List[Union[Trade, AMMTrade]]

FREE_TRADES_LIMIT = 250
FREE_ASSET_MOVEMENTS_LIMIT = 100

LIMITS_MAPPING = {
    'trade': FREE_TRADES_LIMIT,
    'asset_movement': FREE_ASSET_MOVEMENTS_LIMIT,
    'ledger_action': FREE_LEDGER_ACTIONS_LIMIT,
}


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
        self.actions_per_location: Dict[str, Dict[Location, int]] = {
            'trade': defaultdict(int),
            'asset_movement': defaultdict(int),
        }
        self.processing_state_name = 'Starting query of historical events'
        self.progress = ZERO
        db_settings = self.db.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime

    def _increase_progress(self, step: int, total_steps: int) -> int:
        step += 1
        self.progress = FVal(step / total_steps) * 100
        return step

    @overload
    def _apply_actions_limit(
            self,
            location: Location,
            action_type: Literal['trade'],
            location_actions: TRADES_LIST,
            all_actions: TRADES_LIST,
    ) -> TRADES_LIST:
        ...

    @overload
    def _apply_actions_limit(
            self,
            location: Location,
            action_type: Literal['asset_movement'],
            location_actions: List[AssetMovement],
            all_actions: List[AssetMovement],
    ) -> List[AssetMovement]:
        ...

    def _apply_actions_limit(
            self,
            location: Location,
            action_type: Literal['trade', 'asset_movement'],
            location_actions: Union[TRADES_LIST, List[AssetMovement]],
            all_actions: Union[TRADES_LIST, List[AssetMovement]],
    ) -> Union[TRADES_LIST, List[AssetMovement]]:
        """Take as many actions from location actions and add them to all actions as the limit permits

        Returns the modified (or not) all_actions
        """
        # If we are already at or above the limit return current actions disregarding this location
        actions_mapping = self.actions_per_location[action_type]
        current_num_actions = sum(x for _, x in actions_mapping.items())
        limit = LIMITS_MAPPING[action_type]
        if current_num_actions >= limit:
            return all_actions

        # Find out how many more actions can we return, and depending on that get
        # the number of actions from the location actions and add them to the total
        remaining_num_actions = limit - current_num_actions
        if remaining_num_actions < 0:
            remaining_num_actions = 0

        num_actions_to_take = min(len(location_actions), remaining_num_actions)

        actions_mapping[location] = num_actions_to_take
        all_actions.extend(location_actions[0:num_actions_to_take])  # type: ignore
        return all_actions

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

    def query_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
            only_cache: bool,
    ) -> TRADES_LIST:
        """Queries trades for the given location and time range.
        If no location is given then all external, all exchange and DEX trades are queried.

        If only_cache is given then only trades cached in the DB are returned.
        No service is queried.

        DEX Trades are queried only if the user has premium
        If the user does not have premium then a trade limit is applied.

        May raise:
        - RemoteError: If there are problems connecting to any of the remote exchanges
        """
        trades: TRADES_LIST
        if location is not None:
            # clear the trades queried for this location
            self.actions_per_location['trade'][location] = 0
            trades = self.query_location_trades(from_ts, to_ts, location, only_cache)
        else:
            for given_location in ALL_SUPPORTED_EXCHANGES + [Location.EXTERNAL]:
                # clear the trades queried for this location
                self.actions_per_location['trade'][given_location] = 0
            trades = self.query_location_trades(from_ts, to_ts, Location.EXTERNAL, only_cache)
            # Look for trades that might be imported from CSV files
            for csv_location in EXTERNAL_EXCHANGES:
                trades.extend(self.query_location_trades(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    location=csv_location,
                    only_cache=only_cache,
                ))

            for exchange in self.exchange_manager.iterate_exchanges():
                all_set = {x.identifier for x in trades}
                exchange_trades = exchange.query_trade_history(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=only_cache,
                )
                # TODO: Really dirty. Figure out a better way.
                # Since some of the trades may already be in the DB if multiple
                # keys are used for a single exchange.
                exchange_trades = [x for x in exchange_trades if x.identifier not in all_set]
                if self.chain_manager.premium is None:
                    trades = self._apply_actions_limit(
                        location=exchange.location,
                        action_type='trade',
                        location_actions=exchange_trades,
                        all_actions=trades,
                    )
                else:
                    trades.extend(exchange_trades)

            # for all trades we also need the trades from the amm protocols
            if self.chain_manager.premium is not None:
                for amm_location in AMMTradeLocations:
                    amm_module_name = cast(AMMTRADE_LOCATION_NAMES, str(amm_location))
                    amm_module = self.chain_manager.get_module(amm_module_name)
                    if amm_module is not None:
                        trades.extend(
                            amm_module.get_trades(
                                addresses=self.chain_manager.queried_addresses_for_module(amm_module_name),  # noqa: E501
                                from_timestamp=from_ts,
                                to_timestamp=to_ts,
                                only_cache=only_cache,
                            ),
                        )
        # return trades with most recent first
        trades.sort(key=lambda x: x.timestamp, reverse=True)
        return trades

    def query_location_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Location,
            only_cache: bool,
    ) -> TRADES_LIST:
        location_trades: TRADES_LIST
        if location in EXTERNAL_LOCATION:
            location_trades = self.db.get_trades(  # type: ignore  # list invariance
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )
        elif location in AMMTradeLocations:
            if self.chain_manager.premium is not None:
                amm_module_name = cast(AMMTRADE_LOCATION_NAMES, str(location))
                amm_module = self.chain_manager.get_module(amm_module_name)
                if amm_module is not None:
                    location_trades = amm_module.get_trades(  # type: ignore  # list invariance
                        addresses=self.chain_manager.queried_addresses_for_module(amm_module_name),
                        from_timestamp=from_ts,
                        to_timestamp=to_ts,
                        only_cache=only_cache,
                    )
        else:
            # should only be an exchange
            exchanges_list = self.exchange_manager.connected_exchanges.get(location)
            if exchanges_list is None:
                log.warning(
                    f'Tried to query trades from {str(location)} which is either not an '
                    f'exchange or not an exchange the user has connected to',
                )
                return []

            location_trades = []
            for exchange in exchanges_list:
                all_set = {x.identifier for x in location_trades}
                new_trades = exchange.query_trade_history(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=only_cache,
                )
                # TODO: Really dirty. Figure out a better way.
                # Since some of the trades may already be in the DB if multiple
                # keys are used for a single exchange.
                new_trades = [x for x in new_trades if x.identifier not in all_set]
                location_trades.extend(new_trades)

        trades: TRADES_LIST = []
        if self.chain_manager.premium is None:
            trades = self._apply_actions_limit(
                location=location,
                action_type='trade',
                location_actions=location_trades,
                all_actions=trades,
            )
        else:
            trades = location_trades

        return trades

    def _query_and_populate_exchange_asset_movements(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            all_movements: List[AssetMovement],
            exchange: Union[ExchangeInterface, Location],
            only_cache: bool,
    ) -> List[AssetMovement]:
        """Queries exchange for asset movements and adds it to all_movements"""
        all_set = {x.identifier for x in all_movements}
        if isinstance(exchange, ExchangeInterface):
            location = exchange.location
            location_movements = exchange.query_deposits_withdrawals(
                start_ts=from_ts,
                end_ts=to_ts,
                only_cache=only_cache,
            )
            # TODO: Really dirty. Figure out a better way.
            # Since some of the asset movements may already be in the DB if multiple
            # keys are used for a single exchange.
            location_movements = [x for x in location_movements if x.identifier not in all_set]
        else:
            assert isinstance(exchange, Location), 'only a location should make it here'
            assert exchange in EXTERNAL_EXCHANGES, 'only csv supported exchanges should get here'  # noqa : E501
            location = exchange
            # We might have no exchange information but CSV imported information
            self.actions_per_location['asset_movement'][location] = 0
            location_movements = self.db.get_asset_movements(
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )

        movements: List[AssetMovement] = []
        if self.chain_manager.premium is None:
            movements = self._apply_actions_limit(
                location=location,
                action_type='asset_movement',
                location_actions=location_movements,
                all_actions=all_movements,
            )
        else:
            all_movements.extend(location_movements)
            movements = all_movements

        return movements

    def query_asset_movements(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
            only_cache: bool,
    ) -> List[AssetMovement]:
        """Queries AssetMovements for the given location and time range.

        If no location is given then all exchange asset movements are queried.
        If only_cache is True then only what is already in the DB is returned.
        If the user does not have premium then a limit is applied.
        May raise:
        - RemoteError: If there are problems connecting to any of the remote exchanges
        """
        movements: List[AssetMovement] = []
        if location is not None:
            # clear the asset movements queried for this exchange
            self.actions_per_location['asset_movement'][location] = 0
            if location in EXTERNAL_EXCHANGES:
                movements = self._query_and_populate_exchange_asset_movements(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    all_movements=movements,
                    exchange=location,
                    only_cache=only_cache,
                )
            else:
                exchanges_list = self.exchange_manager.connected_exchanges.get(location)
                if exchanges_list is None:
                    log.warning(
                        f'Tried to query deposits/withdrawals from {str(location)} which is '
                        f'either not an exchange or not an exchange the user has connected to',
                    )
                    return []

                # clear the asset movements queried for this exchange
                self.actions_per_location['asset_movement'][location] = 0
                for exchange in exchanges_list:
                    self._query_and_populate_exchange_asset_movements(
                        from_ts=from_ts,
                        to_ts=to_ts,
                        all_movements=movements,
                        exchange=exchange,
                        only_cache=only_cache,
                    )
        else:
            for exchange_location in ALL_SUPPORTED_EXCHANGES:
                # clear the asset movements queried for this exchange
                self.actions_per_location['asset_movement'][exchange_location] = 0
            # we may have DB entries due to csv import from supported locations
            for external_location in EXTERNAL_EXCHANGES:

                movements = self._query_and_populate_exchange_asset_movements(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    all_movements=movements,
                    exchange=external_location,
                    only_cache=only_cache,
                )
            for exchange in self.exchange_manager.iterate_exchanges():
                self._query_and_populate_exchange_asset_movements(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    all_movements=movements,
                    exchange=exchange,
                    only_cache=only_cache,
                )

        # return movements with most recent first
        movements.sort(key=lambda x: x.timestamp, reverse=True)
        return movements

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
            eth_transactions = ethtx_module.query(
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
            external_trades = self.query_location_trades(
                # We need to have history of trades since before the range
                from_ts=Timestamp(0),
                to_ts=end_ts,
                location=location,
                only_cache=True,
            )
            history.extend(external_trades)
            step = self._increase_progress(step, total_steps)

        # include the ledger actions
        self.processing_state_name = 'Querying ledger actions history'
        ledger_actions, _ = self.query_ledger_actions(has_premium, from_ts=None, to_ts=end_ts)
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
