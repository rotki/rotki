import logging
import random
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.constants.timing import (
    AAVE_V3_ASSETS_UPDATE,
    AUGMENTED_SPAM_ASSETS_DETECTION_REFRESH,
    DATA_UPDATES_REFRESH,
    DAY_IN_SECONDS,
    EVMLIKE_ACCOUNTS_DETECTION_REFRESH,
    HOUR_IN_SECONDS,
    OWNED_ASSETS_UPDATE,
    SPAM_ASSETS_DETECTION_REFRESH,
)
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.calendar import CalendarEntry
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.monerium import Monerium
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, premium_create_and_verify
from rotkehlchen.tasks.assets import (
    augmented_spam_detection,
    autodetect_spam_assets_in_db,
    update_aave_v3_underlying_assets,
    update_owned_assets,
)
from rotkehlchen.tasks.calendar import (
    CalendarNotification,
    delete_past_calendar_entries,
    maybe_create_ens_reminders,
    notify_reminders,
)
from rotkehlchen.tasks.utils import query_missing_prices_of_base_entries, should_run_periodic_task
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_BITCOIN_CHAINS,
    CacheType,
    ChecksumEvmAddress,
    ExchangeLocationID,
    Location,
    Optional,
    SupportedBlockchain,
    Timestamp,
    get_args,
)
from rotkehlchen.utils.misc import ts_now

from .events import process_events

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.greenlets.manager import GreenletManager
    from rotkehlchen.premium.sync import PremiumSyncManager
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
DEFAULT_MAX_TASKS_NUM = 2
CRYPTOCOMPARE_HISTOHOUR_FREQUENCY = 240  # at least 4 mins apart
XPUB_DERIVATION_FREQUENCY = 3600  # every hour
EVM_TX_QUERY_FREQUENCY = 3600  # every hour
EXCHANGE_QUERY_FREQUENCY = 3600  # every hour
PREMIUM_STATUS_CHECK = 3600  # every hour
TX_RECEIPTS_QUERY_LIMIT = 500
TX_DECODING_LIMIT = 500
PREMIUM_CHECK_RETRY_LIMIT = 3


def exchange_fail_cb(error: str) -> None:
    log.error(error)


class CCHistoQuery(NamedTuple):
    from_asset: AssetWithOracles
    to_asset: AssetWithOracles


class TaskManager:

    def __init__(
            self,
            max_tasks_num: int,
            greenlet_manager: 'GreenletManager',
            api_task_greenlets: list[gevent.Greenlet],
            database: 'DBHandler',
            cryptocompare: 'Cryptocompare',
            premium_sync_manager: Optional['PremiumSyncManager'],
            chains_aggregator: 'ChainsAggregator',
            exchange_manager: 'ExchangeManager',
            deactivate_premium: Callable[[], None],
            activate_premium: Callable[[Premium], None],
            query_balances: Callable,
            msg_aggregator: 'MessagesAggregator',
            data_updater: 'RotkiDataUpdater',
            username: str,
    ) -> None:
        self.should_schedule = False
        self.max_tasks_num = max_tasks_num
        self.greenlet_manager = greenlet_manager
        self.api_task_greenlets = api_task_greenlets
        self.database = database
        self.cryptocompare = cryptocompare
        self.exchange_manager = exchange_manager
        self.cryptocompare_queries: set[CCHistoQuery] = set()
        self.chains_aggregator = chains_aggregator
        self.last_xpub_derivation_ts = 0
        self.last_evm_tx_query_ts: defaultdict[tuple[ChecksumEvmAddress, SupportedBlockchain], int] = defaultdict(int)  # noqa: E501
        self.last_exchange_query_ts: defaultdict[ExchangeLocationID, int] = defaultdict(int)
        self.base_entries_ignore_set: set[str] = set()
        self.prepared_cryptocompare_query = False
        self.running_greenlets: dict[Callable, list[gevent.Greenlet]] = {}
        self.deactivate_premium = deactivate_premium
        self.activate_premium = activate_premium
        self.query_balances = query_balances
        self.query_yearn_vaults = query_yearn_vaults
        self.last_premium_status_check = ts_now()
        self.last_calendar_reminder_check = Timestamp(0)
        self.msg_aggregator = msg_aggregator
        self.premium_check_retries = 0
        self.premium_sync_manager: Optional[PremiumSyncManager] = premium_sync_manager
        self.data_updater = data_updater
        self.username = username

        self.potential_tasks: list[Callable[[], Optional[list[gevent.Greenlet]]]] = [
            self._maybe_schedule_cryptocompare_query,
            self._maybe_schedule_xpub_derivation,
            self._maybe_query_evm_transactions,
            self._maybe_schedule_exchange_history_query,
            self._maybe_schedule_evm_txreceipts,
            self._maybe_query_missing_prices,
            self._maybe_decode_evm_transactions,
            self._maybe_check_premium_status,
            self._maybe_check_data_updates,
            self._maybe_update_snapshot_balances,
            self._maybe_update_yearn_vaults,
            self._maybe_detect_evm_accounts,
            self._maybe_update_ilk_cache,
            self._maybe_query_produced_blocks,
            self._maybe_query_withdrawals,
            self._maybe_run_events_processing,
            self._maybe_detect_withdrawal_exits,
            self._maybe_detect_new_spam_tokens,
            self._maybe_augmented_detect_new_spam_tokens,
            self._maybe_query_monerium,
            self._maybe_update_owned_assets,
            self._maybe_update_aave_v3_underlying_assets,
            self._maybe_create_calendar_reminder,
            self._maybe_trigger_calendar_reminder,
            self._maybe_delete_past_calendar_events,
            self._maybe_query_graph_delegated_tokens,
        ]
        if self.premium_sync_manager is not None:
            self.potential_tasks.append(self._maybe_schedule_db_upload)
        self.schedule_lock = gevent.lock.Semaphore()

    def _maybe_schedule_db_upload(self) -> Optional[list[gevent.Greenlet]]:
        assert self.premium_sync_manager is not None, 'caller should make sure premium sync manager exists'  # noqa: E501
        if self.premium_sync_manager.check_if_should_sync(force_upload=False) is False:
            return None

        log.debug('Scheduling task for DB upload to server')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Upload data to server',
            exception_is_error=True,
            method=self.premium_sync_manager.maybe_upload_data_to_server,
        )]

    def _prepare_cryptocompare_queries(self) -> None:
        """
        Prepare the queries to do to cryptocompare
        Runs only once and then has a number of queries prepared for the task manager to schedule
        """
        log.debug('Preparing cryptocompare historical price queries')
        if len(self.cryptocompare_queries) != 0:
            return

        with self.database.conn.read_ctx() as cursor:
            assets = self.database.query_owned_assets(cursor)
            main_currency = self.database.get_setting(cursor=cursor, name='main_currency')

        if main_currency.cryptocompare == '':  # main currency not supported
            self.prepared_cryptocompare_query = True
            return

        now_ts = ts_now()
        for raw_asset in assets:
            try:
                asset = raw_asset.resolve_to_asset_with_oracles()
            except (UnknownAsset, WrongAssetType):
                continue  # cryptocompare does not work with non-oracles assets

            if asset.is_fiat() and main_currency.is_fiat():
                continue  # ignore fiat to fiat

            if asset.cryptocompare == '':
                continue  # not supported in cryptocompare

            if asset.cryptocompare is None and asset.symbol is None:
                continue  # type: ignore  # asset.symbol may be None for auto generated underlying tokens

            data_range = GlobalDBHandler.get_historical_price_range(
                from_asset=asset,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
            )
            if data_range is not None and now_ts - data_range[1] < CRYPTOCOMPARE_QUERY_AFTER_SECS:
                continue

            self.cryptocompare_queries.add(CCHistoQuery(from_asset=asset, to_asset=main_currency))

        self.prepared_cryptocompare_query = True

    def _maybe_schedule_cryptocompare_query(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules a cryptocompare query for a single asset history"""
        if self.prepared_cryptocompare_query is False:
            self._prepare_cryptocompare_queries()

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
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=False,
            method=self.cryptocompare.query_and_store_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
        )]

    def _maybe_schedule_xpub_derivation(self) -> Optional[list[gevent.Greenlet]]:
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
        should_derive_xpubs = {
            SupportedBlockchain.BITCOIN: len(btc_xpubs) > 0,
            SupportedBlockchain.BITCOIN_CASH: len(bch_xpubs) > 0,
        }
        if not any(should_derive_xpubs.values()):
            return None

        greenlets = []
        self.last_xpub_derivation_ts = now
        xpub_manager = XpubManager(chains_aggregator=self.chains_aggregator)
        for chain in get_args(SUPPORTED_BITCOIN_CHAINS):
            if should_derive_xpubs[chain] is False:
                continue

            log.debug(f'Scheduling task for {chain} Xpub derivation')
            greenlets.append(self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Derive new xpub addresses for {chain}',
                exception_is_error=True,
                method=xpub_manager.check_for_new_xpub_addresses,
                blockchain=chain,
            ))
        return greenlets

    def _maybe_query_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction query task if enough time has passed"""
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            with self.database.conn.read_ctx() as cursor:
                accounts = self.database.get_blockchain_accounts(cursor).get(blockchain)
                if len(accounts) == 0:
                    continue

                now = ts_now()
                dbevmtx = DBEvmTx(self.database)
                queriable_accounts: list[ChecksumEvmAddress] = []
                for account in accounts:
                    _, end_ts = dbevmtx.get_queried_range(cursor, account, blockchain)
                    if now - max(self.last_evm_tx_query_ts[(account, blockchain)], end_ts) > EVM_TX_QUERY_FREQUENCY:  # noqa: E501
                        queriable_accounts.append(account)

            if len(queriable_accounts) == 0:
                continue

            evm_manager = self.chains_aggregator.get_chain_manager(blockchain)
            address = random.choice(queriable_accounts)
            task_name = f'Query {blockchain!s} transactions for {address}'
            log.debug(f'Scheduling task to {task_name}')
            self.last_evm_tx_query_ts[(address, blockchain)] = now
            # Since this task is heavy we spawn it only for one chain at a time.
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=evm_manager.transactions.single_address_query_transactions,
                address=address,
                start_ts=0,
                end_ts=now,
            )]
        return None

    def _maybe_schedule_evm_txreceipts(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction receipts query task

        The DB check happens first here to see if scheduling would even be needed.
        But the DB query will happen again inside the query task while having the
        lock acquired.
        """
        dbevmtx = DBEvmTx(self.database)
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            hash_results = dbevmtx.get_transaction_hashes_no_receipt(
                tx_filter_query=EvmTransactionsFilterQuery.make(chain_id=blockchain.to_chain_id()),  # type: ignore[arg-type]
                limit=TX_RECEIPTS_QUERY_LIMIT,
            )
            if len(hash_results) == 0:
                return None

            evm_inquirer = self.chains_aggregator.get_chain_manager(blockchain)
            task_name = f'Query {len(hash_results)} {blockchain!s} transactions receipts'
            log.debug(f'Scheduling task to {task_name}')
            # Since this task is heavy we spawn it only for one chain at a time.
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=evm_inquirer.transactions.get_receipts_for_transactions_missing_them,
                limit=TX_RECEIPTS_QUERY_LIMIT,
            )]
        return None

    def _maybe_schedule_exchange_history_query(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the exchange history query task if enough time has passed"""
        if len(self.exchange_manager.connected_exchanges) == 0:
            return None

        now = ts_now()
        queriable_exchanges = []
        with self.database.conn.read_ctx() as cursor:
            for exchange in self.exchange_manager.iterate_exchanges():
                if exchange.location in (Location.BINANCE, Location.BINANCEUS):
                    continue  # skip binance due to the way their history is queried
                queried_range = self.database.get_used_query_range(cursor, f'{exchange.location!s}_trades')  # noqa: E501
                end_ts = queried_range[1] if queried_range else 0
                if now - max(self.last_exchange_query_ts[exchange.location_id()], end_ts) > EXCHANGE_QUERY_FREQUENCY:  # noqa: E501
                    queriable_exchanges.append(exchange)

        if len(queriable_exchanges) == 0:
            return None

        exchange = random.choice(queriable_exchanges)
        task_name = f'Query history of {exchange.name} exchange'
        log.debug(f'Scheduling task to {task_name}')
        self.last_exchange_query_ts[exchange.location_id()] = now
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=exchange.query_history_with_callbacks,
            start_ts=0,
            end_ts=now,
            fail_callback=exchange_fail_cb,
        )]

    def _maybe_query_missing_prices(self) -> Optional[list[gevent.Greenlet]]:
        query_filter = HistoryEventFilterQuery.make(limit=100)
        db = DBHistoryEvents(self.database)
        entries = db.get_base_entries_missing_prices(
            query_filter=query_filter,
            ignored_assets=list(self.base_entries_ignore_set),
        )
        if len(entries) == 0:
            return None

        task_name = 'Periodically query history events prices'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=query_missing_prices_of_base_entries,
            database=self.database,
            entries_missing_prices=entries,
            base_entries_ignore_set=self.base_entries_ignore_set,
        )]

    def _maybe_decode_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction decoding task

        The DB check happens first here to see if scheduling would even be needed.
        But the DB query will happen again inside the query task while having the
        lock acquired.
        """
        dbevmtx = DBEvmTx(self.database)
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            number_of_tx_to_decode = dbevmtx.count_hashes_not_decoded(
                chain_id=blockchain.to_chain_id(),
            )
            if number_of_tx_to_decode == 0:
                return None

            evm_inquirer = self.chains_aggregator.get_chain_manager(blockchain)
            task_name = f'decode {min(number_of_tx_to_decode, TX_DECODING_LIMIT)} {blockchain!s} transactions'  # noqa: E501
            log.debug(f'Scheduling periodic task to {task_name}')
            # Since this task is heavy we spawn it only for one chain at a time.
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=evm_inquirer.transactions_decoder.get_and_decode_undecoded_transactions,
                limit=TX_DECODING_LIMIT,
            )]
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
            premium = premium_create_and_verify(
                credentials=db_credentials,
                username=self.username,
            )
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

    def _maybe_update_snapshot_balances(self) -> Optional[list[gevent.Greenlet]]:
        """
        Update the balances of a user if the difference between last time they were updated
        and the current time exceeds the `balance_save_frequency`.
        """
        with self.database.conn.read_ctx() as cursor:
            if self.database.should_save_balances(cursor):
                task_name = 'Periodically update snapshot balances'
                log.debug(f'Scheduling task to {task_name}')
                return [self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=task_name,
                    exception_is_error=True,
                    method=self.query_balances,
                    requested_save_data=True,
                    save_despite_errors=False,
                    timestamp=None,
                    ignore_cache=True,
                )]
        return None

    def _maybe_query_produced_blocks(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the blocks production query if enough time has passed"""
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(
                cursor=cursor, name=DBCacheStatic.LAST_PRODUCED_BLOCKS_QUERY_TS,
            )
            if result is not None and ts_now() - result <= DAY_IN_SECONDS:
                return None

            cursor.execute('SELECT validator_index FROM eth2_validators')
            indices = [row[0] for row in cursor]

        if len(indices) == 0:
            return None

        if self.chains_aggregator.beaconchain.produced_blocks_lock.locked():
            return None  # task is already running, either api or periodic

        task_name = 'Periodically query produced blocks'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.chains_aggregator.beaconchain.get_and_store_produced_blocks,
            indices_or_pubkeys=indices,
        )]

    def _maybe_query_withdrawals(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the eth withdrawal query if enough time has passed"""
        eth2 = self.chains_aggregator.get_module('eth2')
        if eth2 is None:
            return None

        if eth2.withdrawals_query_lock.locked():
            return None  # already running

        now = ts_now()
        addresses = self.chains_aggregator.accounts.eth
        with self.database.conn.read_ctx() as cursor:
            end_timestamps = cursor.execute(
                'SELECT value FROM key_value_cache WHERE name LIKE ?',
                (DBCacheDynamic.WITHDRAWALS_TS.value[0].replace('{address}', '%'),),
            ).fetchall()

        should_query = False
        if len(end_timestamps) != len(addresses):
            should_query = True
        else:
            for entry in end_timestamps:
                if now - int(entry[0]) >= HOUR_IN_SECONDS * 3:
                    should_query = True
                    break

        if not should_query:
            return None

        task_name = 'Periodically query ethereum withdrawals'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=eth2.query_services_for_validator_withdrawals,
            addresses=addresses,
            to_ts=now,
        )]

    def _maybe_detect_withdrawal_exits(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the task that detects if any of the withdrawals should be exits

        Not putting a lock as it should probably not be a too heavy task?
        """
        eth2 = self.chains_aggregator.get_module('eth2')
        if eth2 is None:
            return None

        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(
                cursor=cursor, name=DBCacheStatic.LAST_WITHDRAWALS_EXIT_QUERY_TS,
            )
            if result is not None and ts_now() - result <= HOUR_IN_SECONDS * 2:
                return None

        task_name = 'Periodically detect withdrawal exits'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=eth2.detect_exited_validators,
        )]

    def _maybe_run_events_processing(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the events processing task which may combine/edit events"""
        now = ts_now()
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(
                cursor=cursor, name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS,
            )
            if result is not None and now - result <= HOUR_IN_SECONDS:
                return None

        task_name = 'Periodically process events'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=process_events,
            chains_aggregator=self.chains_aggregator,
            database=self.database,
        )]

    def _maybe_update_yearn_vaults(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            if len(self.database.get_single_blockchain_addresses(cursor, SupportedBlockchain.ETHEREUM)) == 0:  # noqa: E501
                return None

        if should_update_protocol_cache(CacheType.YEARN_VAULTS) is True:
            ethereum_manager: EthereumManager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)  # noqa: E501
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update yearn vaults',
                exception_is_error=True,
                method=self.query_yearn_vaults,
                db=self.database,
                ethereum_inquirer=ethereum_manager.node_inquirer,
            )]

        return None

    def _maybe_check_data_updates(self) -> Optional[list[gevent.Greenlet]]:
        """
        Function that schedules the data update task if either there is no data update
        cache yet or this cache is older than `DATA_UPDATES_REFRESH`
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_DATA_UPDATES_TS, DATA_UPDATES_REFRESH) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Data update task',
            exception_is_error=True,
            method=self.data_updater.check_for_updates,
        )]

    def _maybe_detect_evm_accounts(self) -> Optional[list[gevent.Greenlet]]:
        """
        Function that schedules the EVM accounts detection task if there has been more than
        EVM_ACCOUNTS_DETECTION_REFRESH seconds since the last time it ran.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS, EVMLIKE_ACCOUNTS_DETECTION_REFRESH) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Detect EVM accounts',
            exception_is_error=True,
            method=self.chains_aggregator.detect_evm_accounts,
            progress_handler=None,
            chains=self.database.get_chains_to_detect_evm_accounts(),
        )]

    def _maybe_update_ilk_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            if len(self.database.get_single_blockchain_addresses(cursor, SupportedBlockchain.ETHEREUM)) == 0:  # noqa: E501
                return None

        if should_update_protocol_cache(CacheType.MAKERDAO_VAULT_ILK, 'ETH-A') is True:
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update ilk cache',
                exception_is_error=True,
                method=query_ilk_registry_and_maybe_update_cache,
                ethereum=self.chains_aggregator.ethereum.node_inquirer,
            )]

        return None

    def _maybe_detect_new_spam_tokens(self) -> Optional[list[gevent.Greenlet]]:
        """
        This function queries the globaldb looking for assets that look like spam tokens
        and ignores them in addition to marking them as spam tokens
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY, SPAM_ASSETS_DETECTION_REFRESH) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Detect spam assets in globaldb',
            exception_is_error=True,
            method=autodetect_spam_assets_in_db,
            user_db=self.database,
        )]

    def _maybe_augmented_detect_new_spam_tokens(self) -> Optional[list[gevent.Greenlet]]:
        """
        This function runs the augmented token detection algorithm which is a heavier and more
        time consuming analysis on user's asset that involves external calls in order to find and
        detect potential spam tokens.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY, AUGMENTED_SPAM_ASSETS_DETECTION_REFRESH) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Augmented detection of spam assets',
            exception_is_error=True,
            method=augmented_spam_detection,
            user_db=self.database,
        )]

    def _maybe_update_owned_assets(self) -> Optional[list[gevent.Greenlet]]:
        """
        This function runs the logic to copy the owned assets from the user db to the globaldb.
        This task is required to have a fresh status on the assets searches when the filter for
        owned assets is used.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_OWNED_ASSETS_UPDATE, OWNED_ASSETS_UPDATE) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Update owned assets in globaldb',
            exception_is_error=True,
            method=update_owned_assets,
            user_db=self.database,
        )]

    def _maybe_update_aave_v3_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        """
        This function runs the logic to query the aave v3 contracts to get all the
        underlying assets supported by them and save them in the globaldb.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE, AAVE_V3_ASSETS_UPDATE) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Update aave v3 underlying assets in globaldb',
            exception_is_error=True,
            method=update_aave_v3_underlying_assets,
            chains_aggregator=self.chains_aggregator,
        )]

    def _maybe_query_monerium(self) -> Optional[list[gevent.Greenlet]]:
        if self.chains_aggregator.premium is None:
            return None  # should not run in free mode

        if should_run_periodic_task(self.database, DBCacheStatic.LAST_MONERIUM_QUERY_TS, HOUR_IN_SECONDS) is False:  # noqa: E501
            return None

        with self.database.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT api_key, api_secret FROM external_service_credentials WHERE name=?',
                ('monerium',),
            ).fetchone()
            if result is None:
                return None

        monerium = Monerium(database=self.database, user=result[0], password=result[1])
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Query monerium',
            exception_is_error=False,  # don't spam user messages if errors happen
            method=monerium.get_and_process_orders,
        )]

    def _maybe_create_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        """Create upcoming reminders for specific history events, if not already created."""
        if (
            CachedSettings().get_entry('auto_create_calendar_reminders') is False or
            should_run_periodic_task(
                database=self.database,
                key_name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
                refresh_period=DAY_IN_SECONDS,
            ) is False
        ):
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Maybe create ENS reminders',
            exception_is_error=True,
            method=maybe_create_ens_reminders,
            database=self.database,
        )]

    def _maybe_trigger_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        """Get upcoming reminders and maybe process them"""
        if (now := ts_now()) - self.last_calendar_reminder_check < 60 * 5:
            return None

        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT event.identifier, event.name, event.description, event.counterparty, '
                'event.timestamp, event.address, event.blockchain, event.color, '
                'event.auto_delete, reminder.identifier, reminder.secs_before FROM '
                'calendar_reminders AS reminder LEFT JOIN calendar AS event '
                'ON reminder.event_id = event.identifier WHERE '
                '? > event.timestamp - reminder.secs_before',
                (now,),
            )
            reminders = [CalendarNotification(
                event=CalendarEntry.deserialize_from_db(row[:9]),
                identifier=row[9],
                secs_before=row[10],
            ) for row in cursor]

        if len(reminders) == 0:
            return None

        self.last_calendar_reminder_check = now
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Notify calendar reminders',
            exception_is_error=True,
            method=notify_reminders,
            reminders=reminders,
            database=self.database,
            msg_aggregator=self.msg_aggregator,
        )]

    def _maybe_delete_past_calendar_events(self) -> Optional[list[gevent.Greenlet]]:
        """
        Delete old calendar events if the setting for deleting them allows it and if they haven't
        been marked to not be deleted.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS, DAY_IN_SECONDS) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Delete old calendar entries',
            exception_is_error=True,
            method=delete_past_calendar_entries,
            database=self.database,
        )]

    def _maybe_query_graph_delegated_tokens(self) -> Optional[list[gevent.Greenlet]]:
        """
        Periodically query Ethereum transaction logs for Graph staking-related transactions,
        particularly, search for DelegationTransferredToL2 event. If not found, it decodes
        and adds them.
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS, DAY_IN_SECONDS) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name="Search for Graph's GRT DelegationTransferredToL2 events",
            exception_is_error=True,
            method=self.chains_aggregator.ethereum.transactions.query_for_graph_delegation_txns,  # type: ignore[attr-defined]
            addresses=self.chains_aggregator.accounts.eth,
        )]

    def _schedule(self) -> None:
        """Schedules background tasks"""
        self.greenlet_manager.clear_finished()
        # Also clear methods mapping in the task manager
        self.running_greenlets = {
            method: greenlets
            for method, greenlets in self.running_greenlets.items()
            if not all(greenlet.dead for greenlet in greenlets)
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
            new_greenlets = scheduling_fn()
            if new_greenlets is None:
                continue  # The scheduling function for the specific task decided to not schedule it  # noqa: E501
            self.running_greenlets[scheduling_fn] = new_greenlets
            spawned_new += 1

    def schedule(self) -> None:
        """Schedules background task while holding the scheduling lock

        Only if should_schedule has been set to True, which happpens after the first
        time the user loads up the dashboard. This is to avoid any background tasks running
        during user migrations, db upgrades and asset upgrades.

        Used during logout to make sure no task is being scheduled at the same time
        as logging out
        """
        if self.should_schedule is False:
            return

        with self.schedule_lock:
            self._schedule()
