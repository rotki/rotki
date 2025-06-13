import logging
import random
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CHAIN_ID_TO_BOOSTER_ADDRESSES
from rotkehlchen.chain.evm.decoding.aura_finance.utils import query_aura_pools
from rotkehlchen.chain.evm.decoding.morpho.utils import (
    query_morpho_reward_distributors,
    query_morpho_vaults,
)
from rotkehlchen.chain.evm.decoding.pendle.constants import (
    PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM,
)
from rotkehlchen.chain.evm.decoding.pendle.utils import query_pendle_yield_tokens
from rotkehlchen.constants import WEEK_IN_SECONDS
from rotkehlchen.constants.timing import (
    AAVE_V3_ASSETS_UPDATE,
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
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, has_premium_check, premium_create_and_verify
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.tasks.assets import (
    autodetect_spam_assets_in_db,
    maybe_detect_new_tokens,
    update_aave_v3_underlying_assets,
    update_owned_assets,
    update_spark_underlying_assets,
)
from rotkehlchen.tasks.calendar import (
    CalendarNotification,
    delete_past_calendar_entries,
    maybe_create_calendar_reminders,
    notify_reminders,
)
from rotkehlchen.tasks.utils import should_run_periodic_task
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_BITCOIN_CHAINS,
    CacheType,
    ChainID,
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
        self.prepared_cryptocompare_query = False
        self.running_greenlets: dict[Callable, list[gevent.Greenlet]] = {}
        self.deactivate_premium = deactivate_premium
        self.activate_premium = activate_premium
        self.query_balances = query_balances
        self.last_balance_query_ts = Timestamp(0)
        self.query_yearn_vaults = query_yearn_vaults
        self.query_morpho_vaults = query_morpho_vaults
        self.query_pendle_yield_tokens = query_pendle_yield_tokens
        self.query_morpho_reward_distributors = query_morpho_reward_distributors
        self.query_aura_pools = query_aura_pools
        self.last_premium_status_check = ts_now()
        self.last_calendar_reminder_check = Timestamp(0)
        self.msg_aggregator = msg_aggregator
        self.premium_check_retries = 0
        self.premium_sync_manager: Optional[PremiumSyncManager] = premium_sync_manager
        self.data_updater = data_updater
        self.username = username
        self.base_entries_ignore_set: set[Any] = set()

        self.potential_tasks: list[Callable[[], Optional[list[gevent.Greenlet]]]] = [
            self._maybe_schedule_cryptocompare_query,
            self._maybe_schedule_xpub_derivation,
            self._maybe_query_evm_transactions,
            self._maybe_schedule_exchange_history_query,
            self._maybe_schedule_evm_txreceipts,
            self._maybe_decode_evm_transactions,
            self._maybe_check_premium_status,
            self._maybe_check_data_updates,
            self._maybe_update_snapshot_balances,
            self._maybe_update_yearn_vaults,
            self._maybe_update_morpho_cache,
            self._maybe_update_aura_pools,
            self._maybe_detect_evm_accounts,
            self._maybe_update_ilk_cache,
            self._maybe_query_produced_blocks,
            self._maybe_query_withdrawals,
            self._maybe_run_events_processing,
            self._maybe_detect_withdrawal_exits,
            self._maybe_detect_new_spam_tokens,
            self._maybe_query_monerium,
            self._maybe_update_owned_assets,
            self._maybe_update_aave_v3_underlying_assets,
            self._maybe_update_spark_underlying_assets,
            self._maybe_create_calendar_reminder,
            self._maybe_trigger_calendar_reminder,
            self._maybe_delete_past_calendar_events,
            self._maybe_query_graph_delegated_tokens,
            self._maybe_query_gnosispay,
            self._maybe_update_pendle_cache,
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
                    if now - max(self.last_evm_tx_query_ts[account, blockchain], end_ts) > EVM_TX_QUERY_FREQUENCY:  # noqa: E501
                        queriable_accounts.append(account)

            if len(queriable_accounts) == 0:
                continue

            evm_manager = self.chains_aggregator.get_chain_manager(blockchain)
            address = random.choice(queriable_accounts)
            task_name = f'Query {blockchain!s} transactions for {address}'
            log.debug(f'Scheduling task to {task_name}')
            self.last_evm_tx_query_ts[address, blockchain] = now
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
                tx_filter_query=EvmTransactionsFilterQuery.make(chain_id=blockchain.to_chain_id()),
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
            log.debug('Premium check successful. Sending activate message')
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
        with self.database.conn.read_ctx() as read_cursor:
            if not self.database.should_save_balances(
                cursor=read_cursor,
                last_query_ts=self.last_balance_query_ts,
            ):
                return None

        maybe_detect_new_tokens(self.database)
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

    def _maybe_query_produced_blocks(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the blocks production query if enough time has passed"""
        if (
            self.chains_aggregator.get_module('eth2') is None or
            self.chains_aggregator.beaconchain.is_rate_limited() or
            self.chains_aggregator.beaconchain.produced_blocks_lock.locked() or
            len(indices := self.chains_aggregator.beaconchain.get_outdated_validators_to_query_for_blocks()) == 0  # noqa: E501
        ):
            return None

        task_name = 'Periodically query produced blocks'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.chains_aggregator.beaconchain.get_and_store_produced_blocks,
            indices=indices,
        )]

    def _maybe_query_withdrawals(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the eth withdrawal query if enough time has passed"""
        if (eth2 := self.chains_aggregator.get_module('eth2')) is None:
            return None

        if eth2.withdrawals_query_lock.locked():
            return None  # already running

        now = ts_now()
        with self.database.conn.read_ctx() as cursor:
            # Get user addresses that have validators that may need to be queried
            key_name = DBCacheDynamic.WITHDRAWALS_TS.value[0][:17]
            cursor.execute(
                'SELECT DISTINCT ev.withdrawal_address FROM eth2_validators ev '
                f"LEFT JOIN key_value_cache kv ON kv.name = '{key_name}' || ev.withdrawal_address "
                'WHERE kv.value <= ? OR kv.name IS NULL',
                (ts_now() - HOUR_IN_SECONDS * 3,),
            )
            if len(addresses := [row[0] for row in cursor]) == 0:
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
        if (eth2 := self.chains_aggregator.get_module('eth2')) is None:
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

        if should_update_protocol_cache(self.database, CacheType.YEARN_VAULTS) is True:
            return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update yearn vaults',
                exception_is_error=False,
                method=self.query_yearn_vaults,
                db=self.database,
                ethereum_inquirer=self.chains_aggregator.ethereum.node_inquirer,
            )]

        return None

    def _maybe_update_morpho_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0
            ):
                return None

        greenlets = []
        if should_update_protocol_cache(self.database, CacheType.MORPHO_VAULTS) is True:
            greenlets.append(self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update Morpho vaults',
                exception_is_error=False,
                method=self.query_morpho_vaults,
                database=self.database,
            ))

        if any(
            should_update_protocol_cache(
                userdb=self.database,
                cache_key=CacheType.MORPHO_REWARD_DISTRIBUTORS,
                args=(str(chain_id),),
            )
            for chain_id in {ChainID.ETHEREUM, ChainID.BASE}
        ):
            greenlets.append(self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update Morpho reward distributors',
                exception_is_error=False,
                method=self.query_morpho_reward_distributors,
            ))

        return greenlets if len(greenlets) > 0 else None

    def _maybe_update_pendle_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ARBITRUM_ONE)) == 0 and
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0 and
                len(account_data.get(SupportedBlockchain.BINANCE_SC)) == 0 and
                len(account_data.get(SupportedBlockchain.OPTIMISM)) == 0
            ):
                return None

        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Update Pendle yield tokens for {chain.to_name()}',
                exception_is_error=False,
                method=self.query_pendle_yield_tokens,
                evm_inquirer=self.chains_aggregator.get_evm_manager(chain).node_inquirer,  # type: ignore[arg-type]  # chain is supported
            )
            for chain in PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM | {ChainID.ETHEREUM}
            if should_update_protocol_cache(self.database, CacheType.PENDLE_YIELD_TOKENS, (str(chain.serialize()),)) is True  # noqa: E501
        ]

    def _maybe_update_aura_pools(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0 and
                len(account_data.get(SupportedBlockchain.OPTIMISM)) == 0 and
                len(account_data.get(SupportedBlockchain.POLYGON_POS)) == 0 and
                len(account_data.get(SupportedBlockchain.ARBITRUM_ONE)) == 0 and
                len(account_data.get(SupportedBlockchain.GNOSIS)) == 0
            ):
                return None

        return [self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Update Aura pools for {chain.to_name()}',
                exception_is_error=False,
                method=self.query_aura_pools,
                evm_inquirer=self.chains_aggregator.get_evm_manager(chain).node_inquirer,  # type: ignore[arg-type]  # chain id is valid
            )
            for chain in CHAIN_ID_TO_BOOSTER_ADDRESSES
            if should_update_protocol_cache(self.database, CacheType.AURA_POOLS, (str(chain.value),)) is True  # noqa: E501
        ]

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

        if should_update_protocol_cache(self.database, CacheType.MAKERDAO_VAULT_ILK, 'ETH-A') is True:  # noqa: E501
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

    def _maybe_update_spark_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        """This function runs the logic to query the Spark contracts to get all the
        underlying assets supported by them and save them in the globaldb.
        """
        if should_run_periodic_task(
            database=self.database,
            refresh_period=WEEK_IN_SECONDS,
            key_name=DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
        ) is False:
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Update Spark underlying assets in globaldb',
            exception_is_error=True,
            method=update_spark_underlying_assets,
            chains_aggregator=self.chains_aggregator,
        )]

    def _maybe_query_monerium(self) -> Optional[list[gevent.Greenlet]]:
        if not has_premium_check(self.chains_aggregator.premium):
            return None  # should not run in free mode

        if (monerium := init_monerium(self.database)) is None:
            return None

        if should_run_periodic_task(self.database, DBCacheStatic.LAST_MONERIUM_QUERY_TS, HOUR_IN_SECONDS) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Query monerium',
            exception_is_error=False,  # don't spam user messages if errors happen
            method=monerium.get_and_process_orders,
        )]

    def _maybe_query_gnosispay(self) -> Optional[list[gevent.Greenlet]]:
        if not has_premium_check(self.chains_aggregator.premium):
            return None  # should not run in free mode

        if (gnosispay := init_gnosis_pay(self.database)) is None:
            return None

        if should_run_periodic_task(self.database, DBCacheStatic.LAST_GNOSISPAY_QUERY_TS, HOUR_IN_SECONDS) is False:  # noqa: E501
            return None

        from_ts = Timestamp(0)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('SELECT value FROM key_value_cache WHERE name=?', (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value,))  # noqa: E501
            if (result := cursor.fetchone()) is not None:
                from_ts = deserialize_timestamp(result[0])

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Query Gnosis Pay transaction',
            exception_is_error=False,  # don't spam user messages if errors happen
            method=gnosispay.get_and_process_transactions,
            after_ts=from_ts,
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
            task_name='Maybe create calendar reminders',
            exception_is_error=True,
            method=maybe_create_calendar_reminders,
            database=self.database,
        )]

    def _maybe_trigger_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        """Get upcoming reminders and maybe process them"""
        if (now := ts_now()) - self.last_calendar_reminder_check < 60 * 5:
            return None

        reminders: dict[int, list[CalendarNotification]] = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT event.identifier, event.name, event.description, event.counterparty, '
                'event.timestamp, event.address, event.blockchain, event.color, '
                'event.auto_delete, reminder.identifier, reminder.secs_before FROM '
                'calendar_reminders AS reminder LEFT JOIN calendar AS event '
                'ON reminder.event_id = event.identifier WHERE '
                '? > event.timestamp - reminder.secs_before '
                'ORDER BY event.identifier, reminder.secs_before ASC',
                (now,),
            )
            for row in cursor:
                reminders[row[0]].append(CalendarNotification(
                    event=CalendarEntry.deserialize_from_db(row[:9]),
                    identifier=row[9],
                    secs_before=row[10],
                ))

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

        if len(self.chains_aggregator.accounts.get(SupportedBlockchain.ETHEREUM)) == 0:
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

        Only if should_schedule has been set to True, which happens after the first
        time the user loads up the dashboard. This is to avoid any background tasks running
        during user migrations, db upgrades and asset upgrades.

        Used during logout to make sure no task is being scheduled at the same time
        as logging out
        """
        if self.should_schedule is False:
            return

        with self.schedule_lock:
            if self.should_schedule:  # adding this check here to protect against going to schedule during logout/shutdown once task manager has been cleared and DB has been deleted  # noqa: E501
                self._schedule()

    def clear(self) -> None:
        """Ensure that no task is kept referenced. Used when removing the task manager"""
        for task_list in self.running_greenlets.values():
            gevent.killall(task_list)

        self.running_greenlets.clear()
        self.should_schedule = False
