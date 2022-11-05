import copy
import logging
import random
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, DefaultDict, Dict, List, NamedTuple, Set, Tuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.ethereum.utils import should_update_curve_cache
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import DBEqualsFilter, DBIgnoreValuesFilter, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.types import (
    ChecksumEvmAddress,
    ExchangeLocationID,
    Location,
    Optional,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding import EVMTransactionDecoder

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
DEFAULT_MAX_TASKS_NUM = 2
CRYPTOCOMPARE_HISTOHOUR_FREQUENCY = 240  # at least 4 mins apart
XPUB_DERIVATION_FREQUENCY = 3600  # every hour
ETH_TX_QUERY_FREQUENCY = 3600  # every hour
EXCHANGE_QUERY_FREQUENCY = 3600  # every hour
PREMIUM_STATUS_CHECK = 3600  # every hour
TX_RECEIPTS_QUERY_LIMIT = 500
TX_DECODING_LIMIT = 500
PREMIUM_CHECK_RETRY_LIMIT = 3


def noop_exchange_success_cb(trades, margin, asset_movements, exchange_specific_data) -> None:  # type: ignore # noqa: E501
    pass


def exchange_fail_cb(error: str) -> None:
    log.error(error)


class CCHistoQuery(NamedTuple):
    from_asset: AssetWithOracles
    to_asset: AssetWithOracles


class TaskManager():

    def __init__(
            self,
            max_tasks_num: int,
            greenlet_manager: GreenletManager,
            api_task_greenlets: List[gevent.Greenlet],
            database: DBHandler,
            cryptocompare: Cryptocompare,
            premium_sync_manager: Optional[PremiumSyncManager],
            chains_aggregator: ChainsAggregator,
            exchange_manager: ExchangeManager,
            eth_tx_decoder: 'EVMTransactionDecoder',
            deactivate_premium: Callable[[], None],
            activate_premium: Callable[[Premium], None],
            query_balances: Callable,
            update_curve_pools_cache: Callable,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.max_tasks_num = max_tasks_num
        self.greenlet_manager = greenlet_manager
        self.api_task_greenlets = api_task_greenlets
        self.database = database
        self.cryptocompare = cryptocompare
        self.exchange_manager = exchange_manager
        self.eth_tx_decoder = eth_tx_decoder
        self.cryptocompare_queries: Set[CCHistoQuery] = set()
        self.chains_aggregator = chains_aggregator
        self.last_xpub_derivation_ts = 0
        self.last_eth_tx_query_ts: DefaultDict[ChecksumEvmAddress, int] = defaultdict(int)
        self.last_exchange_query_ts: DefaultDict[ExchangeLocationID, int] = defaultdict(int)
        self.base_entries_ignore_set: Set[str] = set()
        self.prepared_cryptocompare_query = False
        self.running_greenlets: Dict[Callable, gevent.Greenlet] = {}
        self.greenlet_manager.spawn_and_track(  # Needs to run in greenlet, is slow
            after_seconds=None,
            task_name='Prepare cryptocompare queries',
            exception_is_error=True,
            method=self._prepare_cryptocompare_queries,
        )
        self.deactivate_premium = deactivate_premium
        self.activate_premium = activate_premium
        self.query_balances = query_balances
        self.update_curve_pools_cache = update_curve_pools_cache
        self.last_premium_status_check = ts_now()
        self.msg_aggregator = msg_aggregator
        self.premium_check_retries = 0
        self.premium_sync_manager: Optional[PremiumSyncManager] = premium_sync_manager

        self.potential_tasks: List[Callable[[], Optional[gevent.Greenlet]]] = [
            self._maybe_schedule_cryptocompare_query,
            self._maybe_schedule_xpub_derivation,
            self._maybe_query_ethereum_transactions,
            self._maybe_schedule_exchange_history_query,
            self._maybe_schedule_ethereum_txreceipts,
            self._maybe_query_missing_prices,
            self._maybe_decode_evm_transactions,
            self._maybe_check_premium_status,
            self._maybe_update_snapshot_balances,
            self._maybe_update_curve_pools,
        ]
        if self.premium_sync_manager is not None:
            self.potential_tasks.append(self._maybe_schedule_db_upload)
        self.schedule_lock = gevent.lock.Semaphore()

    def _maybe_schedule_db_upload(self) -> Optional[gevent.Greenlet]:
        assert self.premium_sync_manager is not None, 'caller should make sure premium sync manager exists'  # noqa: E501
        if self.premium_sync_manager.check_if_should_sync(force_upload=False) is False:
            return None

        log.debug('Scheduling task for DB upload to server')
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Upload data to server',
            exception_is_error=True,
            method=self.premium_sync_manager.maybe_upload_data_to_server,
        )

    def _prepare_cryptocompare_queries(self) -> None:
        """Prepare the queries to do to cryptocompare

        This would be really slow if the entire json cache files were read but we
        have implemented get_cached_data_metadata to only read the relevant part of the file.
        Before doing that we had to yield with gevent.sleep() at each loop iteration.

        Runs only once in the beginning and then has a number of queries prepared
        for the task manager to schedule
        """
        now_ts = ts_now()
        if self.prepared_cryptocompare_query is True:
            return

        if len(self.cryptocompare_queries) != 0:
            return

        with self.database.conn.read_ctx() as cursor:
            assets = self.database.query_owned_assets(cursor)
            main_currency = self.database.get_setting(cursor=cursor, name='main_currency')
        for asset in assets:
            try:
                asset = asset.resolve_to_asset_with_oracles()
            except (UnknownAsset, WrongAssetType):
                continue  # cryptocompare does not work with non-oracles assets

            if asset.is_fiat() and main_currency.is_fiat():
                continue  # ignore fiat to fiat

            if asset.cryptocompare == '' or main_currency.cryptocompare == '':
                continue  # not supported in cryptocompare

            if asset.cryptocompare is None and asset.symbol is None:
                continue  # type: ignore  # asset.symbol may be None for auto generated underlying tokens # noqa: E501

            data_range = GlobalDBHandler().get_historical_price_range(
                from_asset=asset,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
            )
            if data_range is not None and now_ts - data_range[1] < CRYPTOCOMPARE_QUERY_AFTER_SECS:
                continue

            self.cryptocompare_queries.add(CCHistoQuery(from_asset=asset, to_asset=main_currency))

        self.prepared_cryptocompare_query = True

    def _maybe_schedule_cryptocompare_query(self) -> Optional[gevent.Greenlet]:
        """Schedules a cryptocompare query for a single asset history"""
        if self.prepared_cryptocompare_query is False:
            return None

        if len(self.cryptocompare_queries) == 0:
            return None

        # If there is already a cryptocompary query running don't schedule another
        if any(
                'Cryptocompare historical prices' in x.task_name
                for x in self.greenlet_manager.greenlets
        ):
            return None

        now_ts = ts_now()
        # Make sure there is a long enough period  between an asset's histohour query
        # to avoid getting rate limited by cryptocompare
        if now_ts - self.cryptocompare.last_histohour_query_ts <= CRYPTOCOMPARE_HISTOHOUR_FREQUENCY:  # noqa: E501
            return None

        query = self.cryptocompare_queries.pop()
        task_name = f'Cryptocompare historical prices {query.from_asset} / {query.to_asset} query'
        log.debug(f'Scheduling task for {task_name}')
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=False,
            method=self.cryptocompare.query_and_store_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
        )

    def _maybe_schedule_xpub_derivation(self) -> Optional[gevent.Greenlet]:
        """Schedules the xpub derivation task if enough time has passed and if user has xpubs"""
        now = ts_now()
        if now - self.last_xpub_derivation_ts <= XPUB_DERIVATION_FREQUENCY:
            return None

        with self.database.conn.read_ctx() as cursor:
            btc_xpubs = self.database.get_bitcoin_xpub_data(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN,
            )
            bch_xpubs = self.database.get_bitcoin_xpub_data(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN_CASH,
            )
        should_derive_btc_xpubs = len(btc_xpubs) > 0
        should_derive_bch_xpubs = len(bch_xpubs) > 0
        if should_derive_btc_xpubs is False and should_derive_bch_xpubs is False:
            return None

        log.debug('Scheduling task for Xpub derivation')
        self.last_xpub_derivation_ts = now
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Derive new xpub addresses for BTC & BCH',
            exception_is_error=True,
            method=self.chains_aggregator.derive_new_addresses_from_xpubs,
            should_derive_btc_xpubs=should_derive_btc_xpubs,
            should_derive_bch_xpubs=should_derive_bch_xpubs,
        )

    def _maybe_query_ethereum_transactions(self) -> Optional[gevent.Greenlet]:
        """Schedules the ethereum transaction query task if enough time has passed"""
        with self.database.conn.read_ctx() as cursor:
            accounts = self.database.get_blockchain_accounts(cursor).eth
            if len(accounts) == 0:
                return None

            now = ts_now()
            dbethtx = DBEthTx(self.database)
            queriable_accounts = []
            for account in accounts:
                _, end_ts = dbethtx.get_queried_range(cursor, account)
                if now - max(self.last_eth_tx_query_ts[account], end_ts) > ETH_TX_QUERY_FREQUENCY:
                    queriable_accounts.append(account)

        if len(queriable_accounts) == 0:
            return None

        address = random.choice(queriable_accounts)
        task_name = f'Query ethereum transactions for {address}'
        log.debug(f'Scheduling task to {task_name}')
        self.last_eth_tx_query_ts[address] = now
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.eth_tx_decoder.transactions.single_address_query_transactions,
            address=address,
            start_ts=0,
            end_ts=now,
        )

    def _maybe_schedule_ethereum_txreceipts(self) -> Optional[gevent.Greenlet]:
        """Schedules the ethereum transaction receipts query task

        The DB check happens first here to see if scheduling would even be needed.
        But the DB query will happen again inside the query task while having the
        lock acquired.
        """
        dbethtx = DBEthTx(self.database)
        hash_results = dbethtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=TX_RECEIPTS_QUERY_LIMIT)  # noqa: E501
        if len(hash_results) == 0:
            return None

        task_name = f'Query {len(hash_results)} ethereum transactions receipts'
        log.debug(f'Scheduling task to {task_name}')
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.eth_tx_decoder.transactions.get_receipts_for_transactions_missing_them,
            limit=TX_RECEIPTS_QUERY_LIMIT,
        )

    def _maybe_schedule_exchange_history_query(self) -> Optional[gevent.Greenlet]:
        """Schedules the exchange history query task if enough time has passed"""
        if len(self.exchange_manager.connected_exchanges) == 0:
            return None

        now = ts_now()
        queriable_exchanges = []
        with self.database.conn.read_ctx() as cursor:
            for exchange in self.exchange_manager.iterate_exchanges():
                if exchange.location in (Location.BINANCE, Location.BINANCEUS):
                    continue  # skip binance due to the way their history is queried
                queried_range = self.database.get_used_query_range(cursor, f'{str(exchange.location)}_trades')  # noqa: E501
                end_ts = queried_range[1] if queried_range else 0
                if now - max(self.last_exchange_query_ts[exchange.location_id()], end_ts) > EXCHANGE_QUERY_FREQUENCY:  # noqa: E501
                    queriable_exchanges.append(exchange)

        if len(queriable_exchanges) == 0:
            return None

        exchange = random.choice(queriable_exchanges)
        task_name = f'Query history of {exchange.name} exchange'
        log.debug(f'Scheduling task to {task_name}')
        self.last_exchange_query_ts[exchange.location_id()] = now
        return self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=exchange.query_history_with_callbacks,
            start_ts=0,
            end_ts=now,
            success_callback=noop_exchange_success_cb,
            fail_callback=exchange_fail_cb,
        )

    def _maybe_query_missing_prices(self) -> Optional[gevent.Greenlet]:
        query_filter = HistoryEventFilterQuery.make(limit=100)
        entries = self.get_base_entries_missing_prices(query_filter)
        if len(entries) > 0:
            task_name = 'Periodically query history events prices'
            log.debug(f'Scheduling task to {task_name}')
            return self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.query_missing_prices_of_base_entries,
                entries_missing_prices=entries,
            )
        return None

    def get_base_entries_missing_prices(
        self,
        query_filter: HistoryEventFilterQuery,
    ) -> List[Tuple[str, FVal, Asset, Timestamp]]:
        """
        Searches base entries missing usd prices that have not previously been checked in
        this session.
        """
        # Use a deepcopy to avoid mutations in the filter query if it is used later
        db = DBHistoryEvents(self.database)
        new_query_filter = copy.deepcopy(query_filter)
        new_query_filter.filters.append(
            DBEqualsFilter(and_op=True, column='usd_value', value='0'),
        )
        new_query_filter.filters.append(
            DBIgnoreValuesFilter(
                and_op=True,
                column='identifier',
                values=list(self.base_entries_ignore_set),
            ),
        )
        return db.rows_missing_prices_in_base_entries(filter_query=new_query_filter)

    def query_missing_prices_of_base_entries(
        self,
        entries_missing_prices: List[Tuple[str, FVal, Asset, Timestamp]],
    ) -> None:
        """Queries missing prices for HistoryBaseEntry in database updating
        the price if it is found. Otherwise we add the id to the ignore list
        for this session.
        """
        inquirer = PriceHistorian()
        updates = []
        for identifier, amount, asset, timestamp in entries_missing_prices:
            try:
                price = inquirer.query_historical_price(
                    from_asset=asset,
                    to_asset=A_USD,
                    timestamp=timestamp,
                )
            except (NoPriceForGivenTimestamp, RemoteError) as e:
                log.error(
                    f'Failed to find price for {asset} at {timestamp} in base '
                    f'entry {identifier}. {str(e)}.',
                )
                self.base_entries_ignore_set.add(identifier)
                continue

            usd_value = amount * price
            updates.append((str(usd_value), identifier))

        query = 'UPDATE history_events SET usd_value=? WHERE rowid=?'
        with self.database.user_write() as cursor:
            cursor.executemany(query, updates)

    def _maybe_decode_evm_transactions(self) -> Optional[gevent.Greenlet]:
        """Schedules the evm transaction decoding task

        The DB check happens first here to see if scheduling would even be needed.
        But the DB query will happen again inside the query task while having the
        lock acquired.
        """
        dbethtx = DBEthTx(self.database)
        hashes = dbethtx.get_transaction_hashes_not_decoded(limit=TX_DECODING_LIMIT)
        hashes_length = len(hashes)
        if hashes_length > 0:
            task_name = f'decode {hashes_length} evm trasactions'
            log.debug(f'Scheduling periodic task to {task_name}')
            return self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.eth_tx_decoder.get_and_decode_undecoded_transactions,
                limit=TX_DECODING_LIMIT,
            )
        return None

    def _maybe_check_premium_status(self) -> None:
        """
        Validates the premium status of the account and if the credentials are not valid
        it retries 3 times before deactivating the user's premium status. If the
        credentials are valid and the premium status is not correct it will reactivate
        the user's premium status.
        """
        now = ts_now()
        if now - self.last_premium_status_check < PREMIUM_STATUS_CHECK:
            return

        log.debug('Running the premium status check')
        with self.database.conn.read_ctx() as cursor:
            db_credentials = self.database.get_rotkehlchen_premium(cursor)
        if db_credentials is None:
            self.last_premium_status_check = now
            return

        try:
            premium = premium_create_and_verify(db_credentials)
        except RemoteError:
            if self.premium_check_retries < PREMIUM_CHECK_RETRY_LIMIT:
                self.premium_check_retries += 1
                log.debug(
                    f'Premium check failed {self.premium_check_retries} times. Not '
                    f'sending deactivate message yet',
                )
                self.last_premium_status_check = now
                return
            log.debug('Premium check failed due to remote error. Sending deactivate message')
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': False,
                    'expired': False,
                },
            )
            self.deactivate_premium()
        except PremiumAuthenticationError:
            log.debug('Premium check failed due to authentication error. Sending deactivate message')  # noqa: E501
            self.deactivate_premium()
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': False,
                    'expired': True,
                },
            )
        else:
            log.debug('Premium check succesful. Sending activate message')
            self.activate_premium(premium)
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': True,
                    'expired': False,
                },
            )
            self.premium_check_retries = 0
        finally:
            self.last_premium_status_check = now

    def _maybe_update_snapshot_balances(self) -> Optional[gevent.Greenlet]:
        """
        Update the balances of a user if the difference between last time they were updated
        and the current time exceeds the `balance_save_frequency`.
        """
        with self.database.conn.read_ctx() as cursor:
            if self.database.should_save_balances(cursor):
                task_name = 'Periodically update snapshot balances'
                log.debug(f'Scheduling task to {task_name}')
                return self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=task_name,
                    exception_is_error=True,
                    method=self.query_balances,
                    requested_save_data=True,
                    save_despite_errors=False,
                    timestamp=None,
                    ignore_cache=True,
                )
        return None

    def _maybe_update_curve_pools(self) -> Optional[gevent.Greenlet]:
        """Function that schedules curve pools update task if either there is no curve pools cache
        yet or this cache has expired (i.e. it's been more than a week since last update)."""
        if should_update_curve_cache() is True:
            return self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update curve pools cache',
                exception_is_error=True,
                method=self.update_curve_pools_cache,
                tx_decoder=self.eth_tx_decoder,
            )

        return None

    def _schedule(self) -> None:
        """Schedules background tasks"""
        self.greenlet_manager.clear_finished()
        # Also clear methods mapping in the task manager
        self.running_greenlets = {
            method: greenlet
            for method, greenlet in self.running_greenlets.items()
            if greenlet.dead is False
        }
        current_greenlets = len(self.greenlet_manager.greenlets) + len(self.api_task_greenlets)
        not_proceed = current_greenlets >= self.max_tasks_num
        log.debug(
            f'At task scheduling. Current greenlets: {current_greenlets} '
            f'Max greenlets: {self.max_tasks_num}. '
            f'{"Will not schedule" if not_proceed else "Will schedule"}.',
        )
        if not_proceed:
            return  # too busy

        random.shuffle(self.potential_tasks)
        max_tasks = min(self.max_tasks_num - current_greenlets, len(self.potential_tasks))

        spawned_new = 0
        for scheduling_fn in self.potential_tasks:
            if spawned_new >= max_tasks:
                break  # no more task slots left
            if scheduling_fn in self.running_greenlets:
                continue  # the specified task is already running
            new_greenlet = scheduling_fn()
            if new_greenlet is None:
                continue  # The scheduling function for the specific task decided to not schedule it  # noqa: E501
            self.running_greenlets[scheduling_fn] = new_greenlet
            spawned_new += 1

    def schedule(self) -> None:
        """Schedules background task while holding the scheduling lock

        Used during logout to make sure no task is being scheduled at the same time
        as logging out
        """
        with self.schedule_lock:
            self._schedule()
