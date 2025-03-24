import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from rotkehlchen.constants import ZERO
from rotkehlchen.db.filtering import (
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES, ExchangeManager
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import has_premium_check
from rotkehlchen.tasks.manager import TaskManager
from rotkehlchen.types import EVM_CHAINS_WITH_TRANSACTIONS, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of steps excluding the connected exchanges. Current query steps:
# for chain in EVM_CHAINS_WITH_TRANSACTIONS:
#    chain.transactions
#    chain.receipts
#    chain.tx decoding
#
# reading from the db trades, asset movements, margin positions
# eth2
# base history entries
#
# Please, update this number each time a history query step is either added or removed
NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES = 3 + 3 * len(EVM_CHAINS_WITH_TRANSACTIONS)
STEPS_PER_CEX = 5


class HistoryQueryingManager:

    def __init__(
            self,
            user_directory: Path,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            chains_aggregator: 'ChainsAggregator',
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.chains_aggregator = chains_aggregator
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
        with self.db.conn.read_ctx() as cursor:
            db_settings = self.db.get_settings(cursor)
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime
        # query daily eth2 daily stats for PnL only if they want to count PnL before withdrawals
        self.should_query_eth2_daily_stats = db_settings.eth_staking_taxable_after_withdrawal_enabled is False  # noqa: E501

    def _increase_progress(self, step: int, total_steps: int, step_by: int = 1) -> int:
        """Counts the progress for querying history. When transmitted to the frontend
        this accounts for 50% of the PnL process"""
        step += step_by
        self.progress = FVal(step / total_steps) * 100
        return step

    def _query_services_for_trades(self, filter_query: TradesFilterQuery) -> None:
        """Queries all services requested for trades and writes them to the DB"""
        location = filter_query.location
        from_ts = filter_query.from_ts
        to_ts = filter_query.to_ts
        excluded_instances: dict[Location, set[str]] = defaultdict(set[str])

        with self.db.conn.read_ctx() as cursor:
            for exchange_id in self.db.get_settings(cursor).non_syncing_exchanges:
                excluded_instances[exchange_id.location].add(exchange_id.name)

        if location is not None:
            self.query_location_latest_trades(
                location=location,
                excluded_instances=excluded_instances[location],
                from_ts=from_ts,
                to_ts=to_ts,
            )

            return

        # else query all CEXes
        for exchange in self.exchange_manager.iterate_exchanges():
            exchange.query_trade_history(
                start_ts=from_ts,
                end_ts=to_ts,
                only_cache=False,
            )

    def query_trades(
            self,
            filter_query: TradesFilterQuery,
            only_cache: bool,
    ) -> tuple[list[Trade], int]:
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
        if only_cache is False:
            self._query_services_for_trades(filter_query=filter_query)

        has_premium = has_premium_check(self.chains_aggregator.premium)
        with self.db.conn.read_ctx() as cursor:
            trades, filter_total_found = self.db.get_trades_and_limit_info(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=has_premium,
            )
        return trades, filter_total_found

    def query_location_latest_trades(
            self,
            location: Location,
            excluded_instances: set[str],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> None:
        """Queries the service of a specific location for latest trades and saves them in the DB.
        Services whose names are present in the excluded_instances set are not queried.
        May raise:

        - RemoteError if there is a problem with reaching the service
        """
        if location not in SUPPORTED_EXCHANGES:
            return  # nothing to do

        exchanges_list = self.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return

        for exchange in exchanges_list:
            if exchange.name not in excluded_instances:
                exchange.query_trade_history(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=False,
                )

    def query_history_events(
            self,
            cursor: 'DBCursor',
            location: Literal[Location.KRAKEN, Location.BINANCE, Location.BINANCEUS],
            filter_query: HistoryEventFilterQuery,
            task_manager: TaskManager | None,
            only_cache: bool,
    ) -> tuple[list[HistoryEvent], int]:
        """
        May raise:
        - sqlcipher.OperationalError if a db error occurred while updating missing prices
        """
        if only_cache is False:
            exchanges_list = self.exchange_manager.connected_exchanges.get(location, [])
            exchange_names = []
            for exchange_instance in exchanges_list:
                if location == Location.KRAKEN:
                    exchange_instance.query_history_events()
                elif exchange_instance.query_lending_interests_history(  # type: ignore
                    cursor=cursor,
                    start_ts=filter_query.from_ts,
                    end_ts=filter_query.to_ts,
                ) is True:  # has errors
                    exchange_names.append(exchange_instance.name)

            if len(exchange_names) != 0:
                self.msg_aggregator.add_error(
                    f'Failed to query some events from {location.name} exchanges '
                    f'{",".join(exchange_names)}',
                )

        db = DBHistoryEvents(self.db)
        has_premium = has_premium_check(self.chains_aggregator.premium)
        events, filter_total_found, _ = db.get_history_events_and_limit_info(
            cursor=cursor,
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return events, filter_total_found  # type: ignore  # event is guaranteed HistoryEvent

    def get_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            has_premium: bool,
    ) -> tuple[str, list['AccountingEventMixin']]:
        """
        Creates all events history from start_ts to end_ts. Returns it
        sorted by ascending timestamp.
        """
        self._reset_variables()
        step = 0
        total_steps = (
            self.exchange_manager.connected_and_syncing_exchanges_num() * STEPS_PER_CEX +
            NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES
        )
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        # start creating the all trades history list
        history: list[AccountingEventMixin] = []
        empty_or_error = ''

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        def new_step_cb(state_name: str) -> None:
            """This callback will run for each new step in exchange history query"""
            nonlocal step
            step = self._increase_progress(step, total_steps)
            self.processing_state_name = state_name

        for exchange in self.exchange_manager.iterate_exchanges():
            self.processing_state_name = f'Querying {exchange.name} exchange history'
            exchange.query_history_with_callbacks(
                # We need to have history of exchanges since before the range
                start_ts=Timestamp(0),
                end_ts=end_ts,
                fail_callback=fail_history_cb,
                new_step_data=(new_step_cb, exchange.name),
            )
            # each exchange instance executes STEPS_PER_CEX steps out of the total_steps
            step = self._increase_progress(step, total_steps, step_by=STEPS_PER_CEX)

        # Query all trades, asset movements and margin positions from the DB for all
        # possible locations.
        self.processing_state_name = 'Reading trades, asset movements and margin positions from the DB'  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            # Include all trades
            trades = self.db.get_trades(
                cursor,
                filter_query=TradesFilterQuery.make(to_ts=end_ts),
                has_premium=True,  # we need all trades for accounting -- limit happens later
            )
            history.extend(trades)

            # Include all margin positions
            margin_positions = self.db.get_margin_positions(cursor, to_ts=end_ts)
            history.extend(margin_positions)

        step = self._increase_progress(step, total_steps)

        for blockchain in EVM_CHAINS_WITH_TRANSACTIONS:
            str_blockchain = str(blockchain)
            self.processing_state_name = f'Querying {str_blockchain} transactions history'
            evm_manager = self.chains_aggregator.get_chain_manager(blockchain)
            tx_filter_query = EvmTransactionsFilterQuery.make(
                limit=None,
                offset=None,
                # We need to have history of transactions since before the range
                from_ts=Timestamp(0),
                to_ts=end_ts,
                chain_id=blockchain.to_chain_id(),  # type: ignore[arg-type]
            )
            try:
                evm_manager.transactions.query_chain(filter_query=tx_filter_query)
            except RemoteError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    f'There was an error when querying {str_blockchain} etherscan for transactions: {msg}'  # noqa: E501
                    f'The final history result will not include {str_blockchain} transactions',
                )
                empty_or_error += '\n' + msg

            step = self._increase_progress(step, total_steps)
            self.processing_state_name = f'Querying {str_blockchain} transaction receipts'
            evm_manager.transactions.get_receipts_for_transactions_missing_them()
            step = self._increase_progress(step, total_steps)

            self.processing_state_name = f'Decoding {str_blockchain} raw transactions'
            evm_manager.transactions_decoder.get_and_decode_undecoded_transactions(limit=None)
            step = self._increase_progress(step, total_steps)

        # include eth2 staking events
        eth2 = self.chains_aggregator.get_module('eth2')
        if eth2 is not None and has_premium:
            self.processing_state_name = 'Querying ETH2 staking history'
            if self.should_query_eth2_daily_stats:
                try:
                    eth2_events = self.chains_aggregator.refresh_eth2_get_daily_stats(
                        from_timestamp=Timestamp(0),
                        to_timestamp=end_ts,
                    )
                    history.extend(eth2_events)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Eth2 daily stats are not included in the PnL report due to {e!s}',
                    )
            # make sure that eth2 events and history events are combined
            eth2.combine_block_with_tx_events()

        step = self._increase_progress(step, total_steps)
        self.processing_state_name = 'Querying base history events'
        # Include all base history entries
        history_events_db = DBHistoryEvents(self.db)
        with self.db.conn.read_ctx() as cursor:
            base_entries = history_events_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    # We need to have history since before the range
                    from_ts=Timestamp(0),
                    to_ts=end_ts,
                ),
                has_premium=True,  # ignore limits here. Limit applied at processing
                group_by_event_ids=False,
            )
        history.extend(base_entries)
        self._increase_progress(step, total_steps)

        history.sort(  # sort events first by timestamp (in milliseconds) and by sequence index if HistoryBaseEntry  # noqa: E501
            key=lambda x: (
                (x.timestamp, x.sequence_index) if isinstance(x, HistoryBaseEntry)
                else (ts_sec_to_ms(x.get_timestamp()), 1)
            ),
        )
        return empty_or_error, history
