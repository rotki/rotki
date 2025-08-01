#!/usr/bin/env python

import argparse
import contextlib
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from types import FunctionType
from typing import TYPE_CHECKING, Any, Literal, Optional, cast, overload

import gevent

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, Nft
from rotkehlchen.balances.manual import (
    account_for_manually_tracked_asset_balances,
    get_manually_tracked_balances,
)
from rotkehlchen.chain.accounts import OptionalBlockchainAccount, SingleBlockchainAccountData
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.base.manager import BaseManager
from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.binance_sc.manager import BinanceSCManager
from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
from rotkehlchen.chain.bitcoin.bch.manager import BitcoinCashManager
from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.names import NamePrioritizer
from rotkehlchen.chain.evm.nodes import populate_rpc_nodes_in_database
from rotkehlchen.chain.gnosis.manager import GnosisManager
from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
from rotkehlchen.chain.optimism.manager import OptimismManager
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
from rotkehlchen.chain.scroll.manager import ScrollManager
from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.utils import (
    KUSAMA_NODES_TO_CONNECT_AT_START,
    POLKADOT_NODES_TO_CONNECT_AT_START,
)
from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.data_import.manager import CSVDataImporter
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.db.settings import CachedSettings, DBSettings, ModifiableDBSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.db.utils import replace_tag_mappings, table_exists
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    EthSyncError,
    GreenletKilledError,
    InputError,
    RemoteError,
    SystemPermissionError,
)
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.manager import HistoryQueryingManager
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.premium.premium import (
    Premium,
    PremiumCredentials,
    has_premium_check,
    premium_create_and_verify,
)
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.tasks.manager import DEFAULT_MAX_TASKS_NUM, TaskManager
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    EVM_CHAINS_WITH_TRANSACTIONS_TYPE,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    BTCAddress,
    ChainType,
    ChecksumEvmAddress,
    ExternalService,
    ListOfBlockchainAddresses,
    Location,
    SubstrateAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.usage_analytics import maybe_submit_usage_analytics
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.datadir import maybe_restructure_rotki_data_directory
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 10


class Rotkehlchen:
    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the Rotkehlchen object

        This runs during backend initialization so it should be as light as possible.

        May Raise:
        - SystemPermissionError if the given data directory's permissions
        are not correct.
        - DBSchemaError if GlobalDB's schema is malformed
        """
        # Can also be None after unlock if premium credentials did not
        # authenticate or premium server temporarily offline
        self.premium: Premium | None = None
        self.user_is_logged_in: bool = False

        self.args = args
        if self.args.data_dir is None:
            self.data_dir = default_data_directory()
        else:
            self.data_dir = Path(self.args.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        maybe_restructure_rotki_data_directory(self.data_dir)

        if not os.access(self.data_dir, os.W_OK | os.R_OK):
            raise SystemPermissionError(
                f'The given data directory {self.data_dir} is not readable or writable',
            )
        self.main_loop_spawned = False
        self.api_task_greenlets: list[gevent.Greenlet] = []
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(msg_aggregator=self.msg_aggregator)
        self.rotki_notifier = RotkiNotifier()
        self.msg_aggregator.rotki_notifier = self.rotki_notifier
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        # Initialize the GlobalDBHandler singleton. Has to be initialized BEFORE asset resolver
        globaldb = GlobalDBHandler(
            data_dir=self.data_dir,
            perform_assets_updates=True,
            sql_vm_instructions_cb=self.args.sqlite_instructions,
            msg_aggregator=self.msg_aggregator,
        )
        if globaldb.used_backup is True:
            self.msg_aggregator.add_warning(
                'Your global database was left in an half-upgraded state. '
                'Restored from the latest backup we could find',
            )
        self.data = DataHandler(
            self.data_dir,
            self.msg_aggregator,
            sql_vm_instructions_cb=args.sqlite_instructions,
        )
        self.cryptocompare = Cryptocompare(database=None)
        self.coingecko = Coingecko(database=None)
        self.defillama = Defillama(database=None)
        self.alchemy = Alchemy(database=None)
        self.icon_manager = IconManager(
            data_dir=self.data_dir,
            coingecko=self.coingecko,
            greenlet_manager=self.greenlet_manager,
        )

        # Initialize the Inquirer singleton
        Inquirer(
            data_dir=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            manualcurrent=ManualCurrentOracle(),
            msg_aggregator=self.msg_aggregator,
        )
        # Initialize EVM Contracts common abis
        EvmContracts.initialize_common_abis()
        self.task_manager: TaskManager | None = None
        self.shutdown_event = gevent.event.Event()
        self.migration_manager = DataMigrationManager(self)

    def maybe_kill_running_tx_query_tasks(
            self,
            blockchain: SupportedBlockchain,
            addresses: list[ChecksumEvmAddress],
    ) -> None:
        """Checks for running greenlets related to transactions query for the given
        addresses and kills them if they exist"""
        assert self.task_manager is not None, 'task manager should have been initialized at this point'  # noqa: E501

        for address in addresses:
            account_data = OptionalBlockchainAccount(address=address, chain=blockchain)
            for greenlet in self.api_task_greenlets:
                is_evm_tx_greenlet = (
                    greenlet.dead is False and
                    len(greenlet.args) >= 1 and
                    isinstance(greenlet.args[0], FunctionType) and
                    greenlet.args[0].__qualname__ == 'RestAPI.refresh_transactions'
                )
                if (
                        is_evm_tx_greenlet and
                        greenlet.kwargs.get('only_cache', False) is False and
                        account_data in greenlet.kwargs['accounts']
                ):
                    greenlet.kill(exception=GreenletKilledError('Killed due to request for evm address removal'))  # noqa: E501

            tx_query_task_greenlets = self.task_manager.running_greenlets.get(self.task_manager._maybe_query_evm_transactions, [])  # noqa: E501
            for greenlet in tx_query_task_greenlets:
                if greenlet.dead is False and greenlet.kwargs['address'] in addresses:
                    greenlet.kill(exception=GreenletKilledError('Killed due to request for evm address removal'))  # noqa: E501

    def reset_after_failed_account_creation_or_login(self) -> None:
        """If the account creation or login failed make sure that the rotki instance is clear

        Tricky instances are when after either failed premium credentials or user refusal
        to sync premium databases we relogged in
        """
        self.cryptocompare.db = None
        self.exchange_manager.delete_all_exchanges()
        self.data.logout()
        for instance in (self.cryptocompare, self.defillama, self.coingecko, self.alchemy, Inquirer()._manualcurrent):  # noqa: E501
            if instance.db is not None:  # unset DB if needed
                instance.unset_database()
        CachedSettings().reset()

    def _perform_new_db_actions(self) -> None:
        """Actions to perform at creation of a new DB"""
        with (
            self.data.db.user_write() as write_cursor,
            GlobalDBHandler().conn.read_ctx() as cursor,
        ):
            populate_rpc_nodes_in_database(
                db_write_cursor=write_cursor,
                globaldb_cursor=cursor,
            )

    def unlock_user(
            self,
            user: str,
            password: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            premium_credentials: PremiumCredentials | None,
            resume_from_backup: bool,
            initial_settings: ModifiableDBSettings | None = None,
            sync_database: bool = True,
    ) -> None:
        """Unlocks an existing user or creates a new one if `create_new` is True

        May raise:
        - PremiumAuthenticationError if the password can't unlock the database.
        - AuthenticationError if premium_credentials are given and are invalid
        or can't authenticate with the server
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - SystemPermissionError if the directory or DB file can not be accessed
        - sqlcipher.OperationalError: If some very weird error happens with the DB.
        For example unexpected schema.
        - DBSchemaError if database schema is malformed.
        """
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
            sync_database=sync_database,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )

        # unlock or create the DB
        self.user_directory = self.data.unlock(
            username=user,
            password=password,
            create_new=create_new,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )
        if create_new:
            self._perform_new_db_actions()

        self.data_importer = CSVDataImporter(db=self.data.db)
        self.premium_sync_manager = PremiumSyncManager(
            migration_manager=self.migration_manager,
            data=self.data,
        )
        # set the DB in the instances that need it
        self.cryptocompare.set_database(self.data.db)
        self.defillama.set_database(self.data.db)
        self.coingecko.set_database(self.data.db)
        self.alchemy.set_database(self.data.db)
        Inquirer()._manualcurrent.set_database(database=self.data.db)

        # Anything that was set above here has to be cleaned in case of failure in the next step
        # by reset_after_failed_account_creation_or_login()
        try:
            self.premium = self.premium_sync_manager.try_premium_at_start(
                given_premium_credentials=premium_credentials,
                username=user,
                create_new=create_new,
                sync_approval=sync_approval,
                sync_database=sync_database,
            )
        except PremiumAuthenticationError as e:
            # Reraise it only if this is during the creation of a new account where
            # the premium credentials were given by the user
            if create_new:
                raise
            self.msg_aggregator.add_warning(
                'Could not authenticate the rotki premium API keys found in the DB. '
                f'Error: {e}. Check logs for more details',
            )
            # else let's just continue. User signed in successfully, but he just
            # has unauthenticable/invalid premium credentials remaining in his DB

        with self.data.db.conn.read_ctx() as cursor:
            settings = self.get_settings(cursor)
            CachedSettings().initialize(settings)  # initialize with saved DB settings
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='submit_usage_analytics',
                exception_is_error=False,
                method=maybe_submit_usage_analytics,
                data_dir=self.data_dir,
                should_submit=settings.submit_usage_analytics,
            )
            self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)  # noqa: E501

            exchange_credentials = self.data.db.get_exchange_credentials(cursor)
            self.exchange_manager.initialize_exchanges(
                exchange_credentials=exchange_credentials,
                database=self.data.db,
            )
            blockchain_accounts = self.data.db.get_blockchain_accounts(cursor)

        etherscan = Etherscan(
            database=self.data.db,
            msg_aggregator=self.data.db.msg_aggregator,
        )

        # Initialize blockchain querying modules
        self.chains_aggregator = ChainsAggregator(
            blockchain_accounts=blockchain_accounts,
            ethereum_manager=EthereumManager(
                node_inquirer=(ethereum_inquirer := EthereumInquirer(
                    greenlet_manager=self.greenlet_manager,
                    database=self.data.db,
                    etherscan=etherscan,
                )),
                beacon_chain=self.beaconchain,
            ),
            optimism_manager=OptimismManager(OptimismInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            polygon_pos_manager=PolygonPOSManager(PolygonPOSInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            arbitrum_one_manager=ArbitrumOneManager(ArbitrumOneInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            base_manager=BaseManager(BaseInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            gnosis_manager=GnosisManager(GnosisInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            scroll_manager=ScrollManager(ScrollInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            binance_sc_manager=BinanceSCManager(BinanceSCInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            kusama_manager=SubstrateManager(
                chain=SupportedBlockchain.KUSAMA,
                msg_aggregator=self.msg_aggregator,
                greenlet_manager=self.greenlet_manager,
                connect_at_start=KUSAMA_NODES_TO_CONNECT_AT_START,
                connect_on_startup=len(blockchain_accounts.ksm) != 0,
                own_rpc_endpoint=settings.ksm_rpc_endpoint,
            ),
            polkadot_manager=SubstrateManager(
                chain=SupportedBlockchain.POLKADOT,
                msg_aggregator=self.msg_aggregator,
                greenlet_manager=self.greenlet_manager,
                connect_at_start=POLKADOT_NODES_TO_CONNECT_AT_START,
                connect_on_startup=len(blockchain_accounts.dot) != 0,
                own_rpc_endpoint=settings.dot_rpc_endpoint,
            ),
            avalanche_manager=AvalancheManager(
                avaxrpc_endpoint='https://api.avax.network/ext/bc/C/rpc',
                msg_aggregator=self.msg_aggregator,
            ),
            zksync_lite_manager=ZksyncLiteManager(
                ethereum_inquirer=ethereum_inquirer,
                database=self.data.db,
            ),
            bitcoin_manager=BitcoinManager(database=self.data.db),
            bitcoin_cash_manager=BitcoinCashManager(database=self.data.db),
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            greenlet_manager=self.greenlet_manager,
            premium=self.premium,
            eth_modules=settings.active_modules,
            data_directory=self.data_dir,
            beaconchain=self.beaconchain,
            btc_derivation_gap_limit=settings.btc_derivation_gap_limit,
        )
        Inquirer().inject_evm_managers([
            (chain.to_chain_id(), self.chains_aggregator.get_chain_manager(chain))
            for chain in EVM_CHAINS_WITH_TRANSACTIONS
        ])

        price_historian = PriceHistorian(  # Initialize the price historian singleton
            data_directory=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            uniswapv2=(uniswap_v2_oracle := UniswapV2Oracle()),
            uniswapv3=(uniswap_v3_oracle := UniswapV3Oracle()),
        )
        price_historian.set_oracles_order(settings.historical_price_oracles)

        Inquirer().add_defi_oracles(
            uniswap_v2=uniswap_v2_oracle,
            uniswap_v3=uniswap_v3_oracle,
        )
        Inquirer().set_oracles_order(settings.current_price_oracles)

        self.accountant = Accountant(
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            chains_aggregator=self.chains_aggregator,
            premium=self.premium,
        )
        self.history_querying_manager = HistoryQueryingManager(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            chains_aggregator=self.chains_aggregator,
        )
        self.data_updater = RotkiDataUpdater(
            msg_aggregator=self.msg_aggregator,
            user_db=self.data.db,
        )
        self.task_manager = TaskManager(
            max_tasks_num=DEFAULT_MAX_TASKS_NUM,
            greenlet_manager=self.greenlet_manager,
            api_task_greenlets=self.api_task_greenlets,
            database=self.data.db,
            cryptocompare=self.cryptocompare,
            premium_sync_manager=self.premium_sync_manager,
            chains_aggregator=self.chains_aggregator,
            exchange_manager=self.exchange_manager,
            deactivate_premium=self.deactivate_premium_status,
            activate_premium=self.activate_premium_status,
            query_balances=self.query_balances,
            msg_aggregator=self.msg_aggregator,
            data_updater=self.data_updater,
            username=user,
        )

        self.migration_manager.maybe_migrate_data()
        self.assets_updater = AssetsUpdater(
            msg_aggregator=self.msg_aggregator,
            globaldb=GlobalDBHandler(),
        )
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Check data updates',
            exception_is_error=False,
            method=self.data_updater.check_for_updates,
        )

        self.addressbook_prioritizer = NamePrioritizer(self.data.db)  # Initialize here since it's reused by the api for addressbook endpoints.  # noqa: E501
        self.user_is_logged_in = True
        log.debug('User unlocking complete')

        # Send a notification to the user if data associated with
        # old erc721 tokens has been saved during the db upgrade.
        # TODO: Remove this after a couple versions (added in version 1.38).
        self._check_migration_table_and_notify(
            conn=self.data.db.conn._get_connection(),
            table_name='temp_erc721_data',
            notification_callback=lambda: self.msg_aggregator.add_warning(
                'Data associated with invalid ERC721 assets is present in your database. '
                'Please contact rotki support via our discord to resolve this issue.',
            ),
        )

        # Send a notification to the user if custom Solana tokens were previously
        # added and need to be migrated manually in the app.
        # TODO: Remove this after a couple versions (added in version 1.40).
        global_conn = GlobalDBHandler().conn
        with global_conn.read_ctx() as cursor:
            self._check_migration_table_and_notify(
                conn=global_conn,
                table_name='user_added_solana_tokens',
                notification_callback=lambda: self.msg_aggregator.add_message(
                    message_type=WSMessageType.SOLANA_TOKENS_MIGRATION,
                    data={'identifiers': [i[0] for i in cursor.execute('SELECT identifier FROM user_added_solana_tokens')]},  # noqa: E501
                ),
                extra_check_callback=lambda: cursor.execute('SELECT COUNT(*) FROM user_added_solana_tokens').fetchone()[0] > 0,  # noqa: E501
            )

    def _logout(self) -> None:
        if not self.user_is_logged_in:
            return
        user = self.data.username
        log.info('Logging out user', user=user)

        self.deactivate_premium_status()
        del self.chains_aggregator
        self.exchange_manager.delete_all_exchanges()

        del self.accountant
        del self.history_querying_manager
        del self.data_importer

        self.task_manager.clear()  # type: ignore  # task_manager is not None here
        self.task_manager = None
        self.greenlet_manager.clear()

        self.data.logout()
        # unset the DB in the instances that need unsetting
        self.cryptocompare.unset_database()
        self.defillama.unset_database()
        self.coingecko.unset_database()
        self.alchemy.unset_database()
        Inquirer()._manualcurrent.unset_database()
        CachedSettings().reset()

        # Make sure no messages leak to other user sessions
        self.msg_aggregator.consume_errors()
        self.msg_aggregator.consume_warnings()
        PriceHistorian._PriceHistorian__instance = None  # type: ignore  #  has no attribute "_PriceHistorian__instance" but is the name used by python
        Inquirer.clear()

        # We have locks in the chain aggregator that gets removed in this
        # function and in the db connections. The user db gets replaced but the globaldb
        # needs to be released.
        GlobalDBHandler().clear_locks()
        self.user_is_logged_in = False
        log.info('User successfully logged out', user=user)

    def logout(self) -> None:
        if self.task_manager is None:  # no user logged in?
            return

        with self.task_manager.schedule_lock:
            self._logout()

    def set_premium_credentials(self, credentials: PremiumCredentials) -> None:
        """
        Sets the premium credentials for rotki

        Raises PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        log.info('Setting new premium credentials')
        if self.premium is not None:
            self.premium.set_credentials(credentials)
        else:
            try:
                self.premium = premium_create_and_verify(
                    credentials=credentials,
                    username=self.data.username,
                    msg_aggregator=self.msg_aggregator,
                )
            except RemoteError as e:
                raise PremiumAuthenticationError(str(e)) from e

        self.premium_sync_manager.premium = self.premium
        self.accountant.activate_premium_status(self.premium)
        self.chains_aggregator.activate_premium_status(self.premium)

        self.data.db.set_rotkehlchen_premium(credentials)

    def deactivate_premium_status(self) -> None:
        """Deactivate premium in the current session"""
        self.premium = None
        self.premium_sync_manager.premium = None
        self.accountant.deactivate_premium_status()
        self.chains_aggregator.deactivate_premium_status()

    def activate_premium_status(self, premium: Premium) -> None:
        """Activate premium in the current session if was deactivated"""
        self.premium = premium
        self.premium_sync_manager.premium = self.premium
        self.accountant.activate_premium_status(self.premium)
        self.chains_aggregator.activate_premium_status(self.premium)

    def delete_premium_credentials(self) -> tuple[bool, str]:
        """Deletes the premium credentials for rotki"""
        msg = ''

        success = self.data.db.delete_premium_credentials()
        if success is False:
            msg = 'The database was unable to delete the Premium keys for the logged-in user'
        self.deactivate_premium_status()
        return success, msg

    def start(self) -> gevent.Greenlet:
        assert not self.main_loop_spawned, 'Tried to spawn the main loop twice'
        greenlet = gevent.spawn(self.main_loop)
        self.main_loop_spawned = True
        return greenlet

    def main_loop(self) -> None:
        """rotki main loop that fires often and runs the task manager's scheduler"""
        while self.shutdown_event.wait(timeout=MAIN_LOOP_SECS_DELAY) is not True:
            if self.task_manager is not None and self.args.disable_task_manager is False:
                self.task_manager.schedule()

    def get_blockchain_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> list[SingleBlockchainAccountData] | dict[str, Any]:
        account_data = self.data.db.get_blockchain_account_data(cursor, blockchain)
        if blockchain not in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            return account_data

        xpub_data = self.data.db.get_bitcoin_xpub_data(
            cursor=cursor,
            blockchain=blockchain,  # type: ignore
        )
        addresses_to_account_data = {x.address: x for x in account_data}
        address_to_xpub_mappings = self.data.db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=blockchain,  # type: ignore
            addresses=list(addresses_to_account_data.keys()),
        )

        xpub_mappings: dict[XpubData, list[SingleBlockchainAccountData]] = {}
        for address, xpub_entry in address_to_xpub_mappings.items():
            if xpub_entry not in xpub_mappings:
                xpub_mappings[xpub_entry] = []
            xpub_mappings[xpub_entry].append(addresses_to_account_data[address])

        data: dict[str, Any] = {'standalone': [], 'xpubs': []}
        # Add xpub data
        for xpub_entry in xpub_data:
            data_entry = xpub_entry.serialize()
            addresses = xpub_mappings.get(xpub_entry)
            data_entry['addresses'] = addresses if addresses and len(addresses) != 0 else None
            data['xpubs'].append(data_entry)
        # Add standalone addresses
        data['standalone'] = [x for x in account_data if x.address not in address_to_xpub_mappings]
        return data

    def add_evm_accounts(
            self,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> tuple[
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
    ]:
        """Adds each account for all evm addresses

        Counting ethereum mainnet as the main chain we check if the account is a contract
        in mainnet. If not we check if there is any transactions/activity in that chain for
        the address and if yes we add it too.
        If it's already added in a chain we just ignore that chain.

        Returns four lists:
        - list address, chain tuples for all newly added addresses.
        - list address, chain tuples for all addresses already tracked.
        - list address, chain tuples for all addresses that failed to be added.
        - list address, chain tuples for all addresses that have no activity in their chain.
        - list address, chain tuples for all addresses that are contracts except those
        identified as SAFE contracts.

        May raise:
        - TagConstraintError if any of the given account data contain unknown tags.
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        account_data_map: dict[ChecksumEvmAddress, SingleBlockchainAccountData[ChecksumEvmAddress]] = {x.address: x for x in account_data}  # noqa: E501
        with self.data.db.conn.read_ctx() as cursor:
            self.data.db.ensure_tags_exist(
                cursor=cursor,
                given_data=account_data,
                action='adding',
                data_type='blockchain accounts',
            )

        (
            added_accounts,
            existed_accounts,
            failed_accounts,
            no_activity_accounts,
            evm_contract_addresses,
        ) = self.chains_aggregator.add_accounts_to_all_evm(accounts=[entry.address for entry in account_data])  # noqa: E501
        with self.data.db.user_write() as write_cursor:
            for chain, address in added_accounts:
                account_data_entry = account_data_map[address]
                self.data.db.add_blockchain_accounts(
                    write_cursor=write_cursor,
                    account_data=[account_data_entry.to_blockchain_account_data(chain)],
                )

        return (
            added_accounts,
            existed_accounts,
            failed_accounts,
            no_activity_accounts,
            evm_contract_addresses,
        )

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> None:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
    ) -> None:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS,
            account_data: list[SingleBlockchainAccountData[BTCAddress]],
    ) -> None:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> None:
        ...

    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> None:
        """Adds new blockchain accounts

        Adds the accounts to the blockchain instance and queries them to get the
        updated balances. Also adds them in the DB

        May raise:
        - InputError if the given accounts list is empty.
        - TagConstraintError if any of the given account data contain unknown tags.
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        if len(account_data) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        with self.data.db.conn.read_ctx() as cursor:
            self.data.db.ensure_tags_exist(
                cursor=cursor,
                given_data=account_data,
                action='adding',
                data_type='blockchain accounts',
            )
        self.chains_aggregator.modify_blockchain_accounts(
            blockchain=chain,
            accounts=[entry.address for entry in account_data],
            append_or_remove='append',
        )
        with self.data.db.user_write() as write_cursor:
            self.data.db.add_blockchain_accounts(
                write_cursor=write_cursor,
                account_data=[x.to_blockchain_account_data(chain) for x in account_data],
            )

    def edit_single_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> None:
        """Edits blockchain accounts data for a single chain

        May raise:
        - InputError if the given accounts list is empty or if
        any of the accounts to edit do not exist.
        - TagConstraintError if any of the given account data contain unknown tags.
        """
        # First check for validity of account data addresses
        if len(account_data) == 0:
            raise InputError('Empty list of blockchain account data to edit was given')
        accounts = [x.address for x in account_data]
        unknown_accounts = set(accounts).difference(self.chains_aggregator.accounts.get(blockchain))  # noqa: E501
        if len(unknown_accounts) != 0:
            raise InputError(
                f'Tried to edit unknown {blockchain!s} accounts {",".join(unknown_accounts)}',
            )

        self.data.db.ensure_tags_exist(
            cursor=write_cursor,
            given_data=account_data,
            action='editing',
            data_type='blockchain accounts',
        )
        # Finally edit the accounts
        self.data.db.edit_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[x.to_blockchain_account_data(blockchain) for x in account_data],
        )

    def edit_chain_type_accounts_labels(
            self,
            cursor: 'DBCursor',
            account_data: list[SingleBlockchainAccountData],
    ) -> None:
        """Edit the tags and labels for the accounts in all the chains
        where they are tracked.
        May raise:
        - TagConstraintError: if the new tags don't exist
        - InputError: If not all the selected addresses get updated
        """
        self.data.db.ensure_tags_exist(
            cursor=cursor,
            given_data=account_data,
            action='editing',
            data_type='blockchain accounts',
        )

        address_book_db = DBAddressbook(db_handler=self.data.db)
        for account in account_data:
            if account.label is None:
                continue

            address_book_db.update_addressbook_entries(
                book_type=AddressbookType.PRIVATE,
                entries=[AddressbookEntry(
                    address=account.address,
                    name=account.label,
                    blockchain=None,
                )],
            )

        with self.data.db.user_write() as write_cursor:
            replace_tag_mappings(
                write_cursor=write_cursor,
                data=account_data,
                object_reference_keys=['address'],
            )

    def remove_chain_type_accounts(
            self,
            chain_type: ChainType,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Remove the provided accounts from the specified chains
        May raise:
        - InputError: If we are trying to remove a non tracked account, the
        removal fails or an invalid chain_type is provided.
        """
        blockchain_to_addresses, blockchains, accounts_seen = defaultdict(list), chain_type.type_to_blockchains(), set()  # noqa: E501
        for blockchain in blockchains:
            blockchain_accounts = self.chains_aggregator.accounts.get(blockchain)
            for account in accounts:
                if account in blockchain_accounts:
                    accounts_seen.add(account)
                    blockchain_to_addresses[blockchain].append(account)

        if len(missing_accounts := set(accounts).difference(accounts_seen)) != 0:
            raise InputError(f'Tried to delete non tracked addresses {missing_accounts}')

        for blockchain, tracked_accounts in blockchain_to_addresses.items():
            self.remove_single_blockchain_accounts(
                blockchain=blockchain,
                accounts=tracked_accounts,  # type: ignore  # mypy doesn't detect this as a list of blockchain addresses
            )

    def remove_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes blockchain accounts

        Removes the accounts from the blockchain instance. Also removes them from the DB.

        May raise:
        - InputError if a non-existing account was given to remove
        """
        self.chains_aggregator.remove_single_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )
        with contextlib.ExitStack() as stack:
            if blockchain in EVM_CHAINS_WITH_TRANSACTIONS:
                blockchain = cast('EVM_CHAINS_WITH_TRANSACTIONS_TYPE', blockchain)  # by default mypy doesn't narrow the type  # noqa: E501
                evm_manager = self.chains_aggregator.get_chain_manager(blockchain)
                evm_addresses: list[ChecksumEvmAddress] = cast('list[ChecksumEvmAddress]', accounts)  # noqa: E501
                self.maybe_kill_running_tx_query_tasks(blockchain, evm_addresses)
                stack.enter_context(evm_manager.transactions.wait_until_no_query_for(evm_addresses))
                stack.enter_context(evm_manager.transactions.missing_receipts_lock)
                stack.enter_context(evm_manager.transactions_decoder.undecoded_tx_query_lock)
            write_cursor = stack.enter_context(self.data.db.user_write())
            self.data.db.remove_single_blockchain_accounts(write_cursor, blockchain, accounts)

    def get_history_query_status(self) -> dict[str, str]:
        if self.history_querying_manager.progress < FVal('100'):
            processing_state = self.history_querying_manager.processing_state_name
            progress = self.history_querying_manager.progress / 2
        elif self.accountant.first_processed_timestamp == -1:
            processing_state = 'Processing all retrieved historical events'
            progress = FVal(50)
        else:
            processing_state = 'Processing all retrieved historical events'
            # start_ts is min of the query start or the first action timestamp since action
            # processing can start well before query start to calculate cost basis
            start_ts = min(
                self.accountant.query_start_ts,
                self.accountant.first_processed_timestamp,
            )
            diff = self.accountant.query_end_ts - start_ts
            progress = 50 + 100 * (
                FVal(self.accountant.currently_processing_timestamp - start_ts) /
                FVal(diff) / 2)

        return {'processing_state': str(processing_state), 'total_progress': str(progress)}

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[int, str]:
        error_or_empty, events = self.history_querying_manager.get_history(
            start_ts=start_ts,
            end_ts=end_ts,
            has_premium=has_premium_check(self.premium),
        )
        report_id = self.accountant.process_history(
            start_ts=start_ts,
            end_ts=end_ts,
            events=events,
        )
        return report_id, error_or_empty

    def query_balances(
            self,
            requested_save_data: bool = False,
            save_despite_errors: bool = False,
            timestamp: Timestamp | None = None,
            ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Query all balances rotkehlchen can see.

        If requested_save_data is True then the data are always saved in the DB,
        if it is False then data are saved if self.data.should_save_balances()
        is True.
        If save_despite_errors is True then even if there is any error the snapshot
        will be saved.
        If timestamp is None then the current timestamp is used.
        If a timestamp is given then that is the time that the balances are going
        to be saved in the DB
        If ignore_cache is True then all underlying calls that have a cache ignore it

        Returns a dictionary with the queried balances.
        """
        log.info(
            'query_balances called',
            requested_save_data=requested_save_data,
            save_despite_errors=save_despite_errors,
        )

        if self.task_manager is not None:
            self.task_manager.last_balance_query_ts = ts_now()

        balances: dict[str, dict[Asset, Balance]] = {}
        problem_free = True
        for exchange in self.exchange_manager.iterate_exchanges():
            exchange_balances, error_msg = exchange.query_balances(ignore_cache=ignore_cache)
            # If we got an error, disregard that exchange but make sure we don't save data
            if not isinstance(exchange_balances, dict):
                problem_free = False
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
                    data={'location': exchange.name, 'error': error_msg},
                )
            else:
                location_str = str(exchange.location)
                if location_str not in balances:  # need to widen type at assignment here
                    balances[location_str] = cast('dict[Asset, Balance]', exchange_balances)
                else:  # multiple exchange of same type. Combine balances
                    balances[location_str] = combine_dicts(
                        balances[location_str],
                        exchange_balances,  # type: ignore
                    )

        liabilities: dict[Asset, Balance]
        try:
            blockchain_result = self.chains_aggregator.query_balances(
                blockchain=None,
                ignore_cache=ignore_cache,
            )  # copies below since if cache is used we end up modifying the balance sheet object

            blockchain_assets: dict[Asset, Balance] = {}
            for asset, asset_balances in blockchain_result.totals.assets.items():
                total_balance = Balance()
                for balance in asset_balances.values():
                    total_balance += balance
                if total_balance.amount != ZERO:
                    blockchain_assets[asset] = total_balance

            if len(blockchain_assets) != 0:
                balances[str(Location.BLOCKCHAIN)] = blockchain_assets

            liabilities = {}
            for asset, asset_balances in blockchain_result.totals.liabilities.items():
                total_balance = Balance()
                for balance in asset_balances.values():
                    total_balance += balance
                if total_balance.amount != ZERO:
                    liabilities[asset] = total_balance

        except (RemoteError, EthSyncError) as e:
            problem_free = False
            liabilities = {}
            log.error(f'Querying blockchain balances failed due to: {e!s}')
            self.msg_aggregator.add_message(
                message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
                data={'location': 'blockchain balances query', 'error': str(e)},
            )

        manually_tracked_liabilities = get_manually_tracked_balances(
            db=self.data.db,
            balance_type=BalanceType.LIABILITY,
        )
        manual_liabilities_as_dict: defaultdict[Asset, Balance] = defaultdict(Balance)
        for manual_liability in manually_tracked_liabilities:
            manual_liabilities_as_dict[manual_liability.asset] += manual_liability.value

        liabilities = combine_dicts(liabilities, manual_liabilities_as_dict)
        # retrieve loopring balances if module is activated
        if self.chains_aggregator.get_module('loopring'):
            try:
                loopring_balances = self.chains_aggregator.get_loopring_balances()
            except RemoteError as e:
                problem_free = False
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
                    data={'location': 'loopring', 'error': str(e)},
                )
            else:
                if len(loopring_balances) != 0:
                    balances[str(Location.LOOPRING)] = loopring_balances

        # retrieve nft balances if module is activated
        nfts = self.chains_aggregator.get_module('nfts')
        if nfts is not None:
            try:
                nft_balances = nfts.get_db_nft_balances(filter_query=NFTFilterQuery.make())['entries']  # noqa: E501
            except RemoteError as e:
                log.error(
                    f'At balance snapshot NFT balances query failed due to {e!s}. Error '
                    f'is ignored and balance snapshot will still be saved.',
                )
            else:
                if len(nft_balances) != 0:
                    if (blockchain_location := str(Location.BLOCKCHAIN)) not in balances:
                        balances[str(Location.BLOCKCHAIN)] = {}

                    for balance_entry in nft_balances:
                        if balance_entry['usd_price'] == ZERO:
                            continue

                        # It can happen that the asset was manually added
                        # as a token and we don't want to ignore NFTs from the token query since
                        # they might not be tracked by Opensea. In case of them being already
                        # in the chain balances we update the price and continue
                        blockchain_balances = balances[blockchain_location]
                        nft = Nft(balance_entry['id'])
                        nft_as_token = GlobalDBHandler.get_evm_token(
                            address=nft.evm_address,
                            chain_id=nft.chain_id,
                        )  # we need the eip155 identifier instead of the _nft_ one.

                        if nft_as_token in blockchain_balances:
                            blockchain_balances[nft_as_token].usd_value = balance_entry['usd_price']  # noqa: E501
                        else:
                            blockchain_balances[nft] = Balance(
                                amount=ONE,
                                usd_value=balance_entry['usd_price'],
                            )

        balances = account_for_manually_tracked_asset_balances(db=self.data.db, balances=balances)

        # Calculate usd totals
        assets_total_balance: defaultdict[Asset, Balance] = defaultdict(Balance)
        total_usd_per_location: dict[str, FVal] = {}
        for location, asset_balance in balances.items():
            total_usd_per_location[location] = ZERO
            for asset, balance in asset_balance.items():
                assets_total_balance[asset] += balance
                total_usd_per_location[location] += balance.usd_value

        net_usd = sum((balance.usd_value for _, balance in assets_total_balance.items()), ZERO)
        liabilities_total_usd = sum((liability.usd_value for _, liability in liabilities.items()), ZERO)  # noqa: E501
        net_usd -= liabilities_total_usd

        # Calculate location stats
        location_stats: dict[str, Any] = {}
        for location, total_usd in total_usd_per_location.items():
            if location == str(Location.BLOCKCHAIN):
                total_usd -= liabilities_total_usd  # noqa: PLW2901

            percentage = (total_usd / net_usd).to_percentage() if net_usd != ZERO else '0%'
            location_stats[location] = {
                'usd_value': total_usd,
                'percentage_of_net_value': percentage,
            }

        # Calculate 'percentage_of_net_value' per asset
        assets_total_balance_as_dict: dict[Asset, dict[str, Any]] = {
            asset: balance.to_dict() for asset, balance in assets_total_balance.items()
        }
        liabilities_as_dict: dict[Asset, dict[str, Any]] = {
            asset: balance.to_dict() for asset, balance in liabilities.items()
        }
        for asset, balance_dict in assets_total_balance_as_dict.items():
            percentage = (balance_dict['usd_value'] / net_usd).to_percentage() if net_usd != ZERO else '0%'  # noqa: E501
            assets_total_balance_as_dict[asset]['percentage_of_net_value'] = percentage

        for asset, balance_dict in liabilities_as_dict.items():
            percentage = (balance_dict['usd_value'] / net_usd).to_percentage() if net_usd != ZERO else '0%'  # noqa: E501
            liabilities_as_dict[asset]['percentage_of_net_value'] = percentage

        # Compose balances response
        result_dict = {
            'assets': assets_total_balance_as_dict,
            'liabilities': liabilities_as_dict,
            'location': location_stats,
            'net_usd': net_usd,
        }
        with self.data.db.conn.read_ctx() as cursor:
            allowed_to_save = requested_save_data or self.data.db.should_save_balances(cursor)
            if (problem_free or save_despite_errors) and allowed_to_save:
                if not timestamp:
                    timestamp = Timestamp(int(time.time()))
                with self.data.db.user_write() as write_cursor:
                    self.data.db.save_balances_data(
                        write_cursor=write_cursor,
                        data=result_dict,
                        timestamp=timestamp,
                    )
                log.debug('query_balances data saved')
            else:
                log.debug(
                    'query_balances data not saved',
                    allowed_to_save=allowed_to_save,
                    problem_free=problem_free,
                    save_despite_errors=save_despite_errors,
                )

        # Once the first snapshot is taken the task manager should now be able to
        # start scheduling tasks. This means that the user has logged in and seen
        # the dashboard. This is to avoid scheduling tasks during DB upgrade,
        # migrations and asset updates.
        self.task_manager.should_schedule = True  # type: ignore[union-attr]  # should exist here
        return result_dict

    def set_settings(self, settings: ModifiableDBSettings) -> tuple[bool, str]:
        """Tries to set new settings. Returns True in success or False with message if error"""
        # TODO: https://github.com/orgs/rotki/projects/11?pane=issue&itemId=52425560
        # For those rpc endpoints improve the logic and make it similar to EVM rpc endpoints
        if settings.ksm_rpc_endpoint is not None:
            result, msg = self.chains_aggregator.set_ksm_rpc_endpoint(settings.ksm_rpc_endpoint)
            if not result:
                return False, msg

        if settings.dot_rpc_endpoint is not None:
            result, msg = self.chains_aggregator.set_dot_rpc_endpoint(settings.dot_rpc_endpoint)
            if not result:
                return False, msg

        if settings.beacon_rpc_endpoint is not None and (eth2 := self.chains_aggregator.get_module('eth2')) is not None:  # noqa: E501
            try:
                eth2.beacon_inquirer.set_rpc_endpoint(settings.beacon_rpc_endpoint)
            except RemoteError as e:
                msg = str(e)
                log.error(f'Failed to connect to given beacon node {settings.beacon_rpc_endpoint} due to {msg}')  # noqa: E501
                return False, msg

        if settings.btc_derivation_gap_limit is not None:
            self.chains_aggregator.btc_derivation_gap_limit = settings.btc_derivation_gap_limit

        success, msg = self._validate_and_set_oracles(
            oracle_type=CurrentPriceOracle,
            oracles=settings.current_price_oracles,
            set_oracles_order_method=Inquirer().set_oracles_order,
        )
        if not success:
            return False, msg

        success, msg = self._validate_and_set_oracles(
            oracle_type=HistoricalPriceOracle,
            oracles=settings.historical_price_oracles,
            set_oracles_order_method=PriceHistorian().set_oracles_order,
        )
        if not success:
            return False, msg

        if settings.active_modules is not None:
            self.chains_aggregator.process_new_modules_list(settings.active_modules)

        with self.data.db.user_write() as cursor:
            self.data.db.set_settings(cursor, settings)

        return True, ''

    def _validate_and_set_oracles(
            self,
            oracle_type: type[CurrentPriceOracle | HistoricalPriceOracle],
            oracles: Sequence[CurrentPriceOracle] | Sequence[HistoricalPriceOracle] | None,
            set_oracles_order_method: Callable,
    ) -> tuple[bool, str]:
        if oracles is None:
            return True, ''

        if (
            oracle_type.ALCHEMY in oracles and
            self.data.db.get_external_service_credentials(ExternalService.ALCHEMY) is None
        ):
            return False, (
                'You have enabled the Alchemy price oracle but you do not have an API key '
                'set. Please go to API Keys -> External Services and add one.'
            )

        set_oracles_order_method(oracles)
        return True, ''

    def get_settings(self, cursor: 'DBCursor') -> DBSettings:
        """Returns the db settings with a check whether premium is active or not"""
        return self.data.db.get_settings(cursor, have_premium=self.premium is not None)

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            passphrase: str | None = None,
            kraken_account_type: Optional['KrakenAccountType'] = None,
            binance_selected_trade_pairs: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Setup a new exchange with an api key and an api secret and optionally a passphrase
        """
        is_success, msg = self.exchange_manager.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            database=self.data.db,
            passphrase=passphrase,
            binance_selected_trade_pairs=binance_selected_trade_pairs,
        )
        if is_success:
            # Success, save the result in the DB
            self.data.db.add_exchange(
                name=name,
                location=location,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type,
                binance_selected_trade_pairs=binance_selected_trade_pairs,
            )
        return is_success, msg

    def query_periodic_data(self) -> dict[str, bool | (dict[str, list[str]] | Timestamp)]:
        """Query for frequently changing data"""
        result: dict[str, bool | (dict[str, list[str]] | Timestamp)] = {}

        if self.user_is_logged_in:
            with self.data.db.conn.read_ctx() as cursor:
                result[DBCacheStatic.LAST_BALANCE_SAVE.value] = self.data.db.get_last_balance_save_time(cursor)  # noqa: E501
                connected_nodes, failed_to_connect = {}, {}
                for evm_manager in self.chains_aggregator.iterate_evm_chain_managers():
                    connected_nodes[evm_manager.node_inquirer.chain_name] = [node.name for node in evm_manager.node_inquirer.get_connected_nodes()]  # noqa: E501
                    if len(evm_manager.node_inquirer.failed_to_connect_nodes) != 0:
                        failed_to_connect[evm_manager.node_inquirer.chain_name] = list(evm_manager.node_inquirer.failed_to_connect_nodes)  # noqa: E501

                result['connected_nodes'] = connected_nodes
                if len(failed_to_connect) != 0:
                    result['failed_to_connect'] = failed_to_connect

                result[DBCacheStatic.LAST_DATA_UPLOAD_TS.value] = Timestamp(self.premium_sync_manager.last_remote_data_upload_ts)  # noqa: E501
        return result

    def shutdown(self) -> None:
        self.logout()
        self.shutdown_event.set()

    def create_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            purge_old: bool,
    ) -> None:
        """Creates the cache of the given asset pair from the start of time
        until now for the given oracle.

        if purge_old is true then any old cache in memory and in a file is purged

        May raise:
            - RemoteError if there is a problem reaching the oracle
            - UnsupportedAsset if any of the two assets is not supported by the oracle
        """
        if oracle != HistoricalPriceOracle.CRYPTOCOMPARE:
            return  # only for cryptocompare for now

        with contextlib.suppress(UnknownAsset):  # if suppress -> assets are not crypto or fiat, so we can't query cryptocompare  # noqa: E501
            self.cryptocompare.create_cache(
                from_asset=from_asset,
                to_asset=to_asset,
                purge_old=purge_old,
            )

    @staticmethod
    def _check_migration_table_and_notify(
            conn: 'DBConnection',
            table_name: str,
            notification_callback: Callable,
            extra_check_callback: Callable | None = None,
    ) -> None:
        """Helper function to check if a migration table
        exists and send notification if it does.
        """
        with conn.read_ctx() as cursor:
            if table_exists(cursor, table_name) and (extra_check_callback is None or extra_check_callback()):  # noqa: E501
                notification_callback()
