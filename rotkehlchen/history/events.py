import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    ETHTransactionsFilterQuery,
    HistoryEventFilterQuery,
    LedgerActionsFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES, ExchangeManager
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EXTERNAL_LOCATION, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.accounting.ledger_actions import LedgerAction
    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of steps excluding the connected exchanges. Current query steps:
# eth transactions
# eth receipts
# eth tx decoding
# ledger actions
# external location trades -> len(EXTERNAL_LOCATION)
# eth2
# base history entries
# Please, update this number each time a history query step is either added or removed
NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES = 6 + len(EXTERNAL_LOCATION)


class EventsHistorian:

    def __init__(
            self,
            user_directory: Path,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            chains_aggregator: 'ChainsAggregator',
            eth_tx_decoder: 'EVMTransactionDecoder',
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.chains_aggregator = chains_aggregator
        self.eth_tx_decoder = eth_tx_decoder
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
        with self.db.conn.read_ctx() as cursor:
            db_settings = self.db.get_settings(cursor)
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
        has_premium = self.chains_aggregator.premium is not None
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
    ) -> Tuple[List[Trade], int]:
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

        has_premium = self.chains_aggregator.premium is not None
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
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> None:
        """Queries the service of a specific location for latest trades and saves them in the DB.
        May raise:

        - RemoteError if there is a problem with reaching the service
        """
        if location in SUPPORTED_EXCHANGES:
            exchanges_list = self.exchange_manager.connected_exchanges.get(location)
            if exchanges_list is None:
                return

            for exchange in exchanges_list:
                exchange.query_trade_history(
                    start_ts=from_ts,
                    end_ts=to_ts,
                    only_cache=False,
                )
        else:
            log.error(f'Requested latest trades for unsupported location {location}')

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
        if only_cache is False:
            self._query_services_for_asset_movements(filter_query=filter_query)

        has_premium = self.chains_aggregator.premium is not None
        asset_movements, filter_total_found = self.db.get_asset_movements_and_limit_info(
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return asset_movements, filter_total_found

    def query_history_events(
        self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            only_cache: bool,
    ) -> Tuple[List[HistoryBaseEntry], int]:
        if only_cache is False:
            exchanges_list = self.exchange_manager.connected_exchanges.get(Location.KRAKEN, [])
            kraken_names = []
            for kraken_instance in exchanges_list:
                with_errors = kraken_instance.query_kraken_ledgers(   # type: ignore
                    cursor=cursor,
                    start_ts=filter_query.from_ts,
                    end_ts=filter_query.to_ts,
                )
                if with_errors:
                    kraken_names.append(kraken_instance.name)
            if len(kraken_names) != 0:
                self.msg_aggregator.add_error(
                    f'Failed to query some events from Kraken exchanges '
                    f'{",".join(kraken_names)}',
                )

        db = DBHistoryEvents(self.db)
        has_premium = self.chains_aggregator.premium is not None
        events, filter_total_found = db.get_history_events_and_limit_info(
            cursor=cursor,
            filter_query=filter_query,
            has_premium=has_premium,
        )
        return events, filter_total_found

    def get_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            has_premium: bool,
    ) -> Tuple[str, List['AccountingEventMixin']]:
        """
        Creates all events history from start_ts to end_ts. Returns it
        sorted by ascending timestamp.
        """
        self._reset_variables()
        step = 0
        total_steps = len(self.exchange_manager.connected_exchanges) + NUM_HISTORY_QUERY_STEPS_EXCL_EXCHANGES  # noqa: E501
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        # start creating the all trades history list
        history: List['AccountingEventMixin'] = []
        empty_or_error = ''

        def populate_history_cb(
                trades_history: List[Trade],
                margin_history: List[MarginPosition],
                result_asset_movements: List[AssetMovement],
                exchange_specific_data: Any,
        ) -> None:
            """This callback will run for succesfull exchange history query

            We don't include ledger actions here since we simply gather all of them at the end
            """
            history.extend(trades_history)
            history.extend(margin_history)
            history.extend(result_asset_movements)

            if exchange_specific_data:
                pass  # this used to be only for polo loans -- removed now. TODO: Think if needed

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

        self.processing_state_name = 'Querying ethereum transactions history'
        tx_filter_query = ETHTransactionsFilterQuery.make(
            limit=None,
            offset=None,
            addresses=None,
            # We need to have history of transactions since before the range
            from_ts=Timestamp(0),
            to_ts=end_ts,
        )
        try:
            _, _ = self.eth_tx_decoder.transactions.query(
                filter_query=tx_filter_query,
                has_premium=True,  # ignore limits here. Limit applied at processing
                only_cache=False,
            )
        except RemoteError as e:
            msg = str(e)
            self.msg_aggregator.add_error(
                f'There was an error when querying etherscan for ethereum transactions: {msg}'
                f'The final history result will not include ethereum transactions',
            )
            empty_or_error += '\n' + msg
        step = self._increase_progress(step, total_steps)

        self.processing_state_name = 'Querying ethereum transaction receipts'
        self.eth_tx_decoder.transactions.get_receipts_for_transactions_missing_them()
        step = self._increase_progress(step, total_steps)

        self.processing_state_name = 'Decoding raw transactions'
        self.eth_tx_decoder.get_and_decode_undecoded_transactions(limit=None)
        step = self._increase_progress(step, total_steps)

        # Include all external trades and trades from external exchanges
        for location in EXTERNAL_LOCATION:
            self.processing_state_name = f'Querying {location} trades history'
            with self.db.conn.read_ctx() as cursor:
                external_trades = self.db.get_trades(
                    cursor,
                    filter_query=TradesFilterQuery.make(location=location),
                    has_premium=True,  # we need all trades for accounting -- limit happens later
                )
            history.extend(external_trades)
            step = self._increase_progress(step, total_steps)

        # include all ledger actions
        self.processing_state_name = 'Querying ledger actions history'
        ledger_actions, _ = self.query_ledger_actions(
            filter_query=LedgerActionsFilterQuery.make(),
            only_cache=True,
        )
        history.extend(ledger_actions)
        step = self._increase_progress(step, total_steps)

        # include eth2 staking events
        eth2 = self.chains_aggregator.get_module('eth2')
        if eth2 is not None and has_premium:
            self.processing_state_name = 'Querying ETH2 staking history'
            try:
                eth2_events = self.chains_aggregator.get_eth2_history_events(
                    from_timestamp=Timestamp(0),
                    to_timestamp=end_ts,
                )
                history.extend(eth2_events)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Eth2 events are not included in the PnL report due to {str(e)}',
                )

        step = self._increase_progress(step, total_steps)

        # Include base history entries
        history_events_db = DBHistoryEvents(self.db)
        with self.db.conn.read_ctx() as cursor:
            base_entries, _ = history_events_db.get_history_events_and_limit_info(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    # We need to have history since before the range
                    from_ts=Timestamp(0),
                    to_ts=end_ts,
                ),
                has_premium=True,  # ignore limits here. Limit applied at processing
            )
        history.extend(base_entries)
        self._increase_progress(step, total_steps)

        history.sort(  # sort events first by timestamp and if history base by sequence index
            key=lambda x: (
                x.get_timestamp(),
                x.sequence_index if isinstance(x, HistoryBaseEntry) else 1,
            ),
        )
        return empty_or_error, history
