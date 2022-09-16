#!/usr/bin/env python

import argparse
import contextlib
import logging.config
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import gevent

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.balances.manual import (
    account_for_manually_tracked_asset_balances,
    get_manually_tracked_balances,
)
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.ethereum.accounting.aggregator import EVMAccountingAggregator
from rotkehlchen.chain.ethereum.decoding import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.modules.curve.pools_cache import (
    clear_curve_pools_cache,
    update_curve_metapools_cache,
    update_curve_registry_pools_cache,
)
from rotkehlchen.chain.ethereum.oracles.saddle import SaddleOracle
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.types import SubstrateChain
from rotkehlchen.chain.substrate.utils import (
    KUSAMA_NODES_TO_CONNECT_AT_START,
    POLKADOT_NODES_TO_CONNECT_AT_START,
)
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.data_import.manager import CSVDataImporter
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.db.settings import DBSettings, ModifiableDBSettings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.misc import EthSyncError, InputError, RemoteError, SystemPermissionError
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.covalent import Covalent, chains_id
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.globaldb.updates import AssetsUpdater
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.history.events import EventsHistorian
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.tasks.manager import DEFAULT_MAX_TASKS_NUM, TaskManager
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    BlockchainAccountData,
    ChecksumEvmAddress,
    ListOfBlockchainAddresses,
    Location,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.usage_analytics import maybe_submit_usage_analytics
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import combine_dicts

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 10


ICONS_BATCH_SIZE = 3
ICONS_QUERY_SLEEP = 60


class Rotkehlchen():
    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the Rotkehlchen object

        This runs during backend initialization so it should be as light as possible.

        May Raise:
        - SystemPermissionError if the given data directory's permissions
        are not correct.
        """
        # Can also be None after unlock if premium credentials did not
        # authenticate or premium server temporarily offline
        self.premium: Optional[Premium] = None
        self.user_is_logged_in: bool = False

        self.args = args
        if self.args.data_dir is None:
            self.data_dir = default_data_directory()
        else:
            self.data_dir = Path(self.args.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        if not os.access(self.data_dir, os.W_OK | os.R_OK):
            raise SystemPermissionError(
                f'The given data directory {self.data_dir} is not readable or writable',
            )
        self.main_loop_spawned = False
        self.api_task_greenlets: List[gevent.Greenlet] = []
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(msg_aggregator=self.msg_aggregator)
        self.rotki_notifier = RotkiNotifier(greenlet_manager=self.greenlet_manager)
        self.msg_aggregator.rotki_notifier = self.rotki_notifier
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        # Initialize the GlobalDBHandler singleton. Has to be initialized BEFORE asset resolver
        GlobalDBHandler(
            data_dir=self.data_dir,
            sql_vm_instructions_cb=self.args.sqlite_instructions,
        )
        self.data = DataHandler(
            self.data_dir,
            self.msg_aggregator,
            sql_vm_instructions_cb=args.sqlite_instructions,
        )
        self.cryptocompare = Cryptocompare(data_directory=self.data_dir, database=None)
        self.coingecko = Coingecko()
        self.icon_manager = IconManager(data_dir=self.data_dir, coingecko=self.coingecko)
        self.assets_updater = AssetsUpdater(self.msg_aggregator)
        # Initialize the Inquirer singleton
        Inquirer(
            data_dir=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            manualcurrent=ManualCurrentOracle(),
            msg_aggregator=self.msg_aggregator,
        )
        self.task_manager: Optional[TaskManager] = None
        self.shutdown_event = gevent.event.Event()

    def reset_after_failed_account_creation_or_login(self) -> None:
        """If the account creation or login failed make sure that the rotki instance is clear

        Tricky instances are when after either failed premium credentials or user refusal
        to sync premium databases we relogged in
        """
        self.cryptocompare.db = None

    def unlock_user(
            self,
            user: str,
            password: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            premium_credentials: Optional[PremiumCredentials],
            initial_settings: Optional[ModifiableDBSettings] = None,
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
        """
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
            sync_database=sync_database,
            initial_settings=initial_settings,
        )

        # unlock or create the DB
        self.password = password
        self.user_directory = self.data.unlock(user, password, create_new, initial_settings)
        # Run the DB integrity check due to https://github.com/rotki/rotki/issues/3010
        # TODO: Hopefully onece 3010 is handled this can go away
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='user DB data integrity check',
            exception_is_error=False,
            method=self.data.db.ensure_data_integrity,
        )
        self.data_importer = CSVDataImporter(db=self.data.db)
        self.premium_sync_manager = PremiumSyncManager(data=self.data, password=password)
        # set the DB in the external services instances that need it
        self.cryptocompare.set_database(self.data.db)

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
        except PremiumAuthenticationError:
            # Reraise it only if this is during the creation of a new account where
            # the premium credentials were given by the user
            if create_new:
                raise
            self.msg_aggregator.add_warning(
                'Could not authenticate the rotki premium API keys found in the DB.'
                ' Has your subscription expired?',
            )
            # else let's just continue. User signed in succesfully, but he just
            # has unauthenticable/invalid premium credentials remaining in his DB

        with self.data.db.conn.read_ctx() as cursor:
            settings = self.get_settings(cursor)
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='submit_usage_analytics',
                exception_is_error=False,
                method=maybe_submit_usage_analytics,
                data_dir=self.data_dir,
                should_submit=settings.submit_usage_analytics,
            )
            self.etherscan = Etherscan(database=self.data.db, msg_aggregator=self.msg_aggregator)  # noqa: E501
            self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)  # noqa: E501
            # Initialize the price historian singleton
            PriceHistorian(
                data_directory=self.data_dir,
                cryptocompare=self.cryptocompare,
                coingecko=self.coingecko,
            )
            PriceHistorian().set_oracles_order(settings.historical_price_oracles)

            exchange_credentials = self.data.db.get_exchange_credentials(cursor)
            self.exchange_manager.initialize_exchanges(
                exchange_credentials=exchange_credentials,
                database=self.data.db,
            )
            blockchain_accounts = self.data.db.get_blockchain_accounts(cursor)

        ethereum_nodes = self.data.db.get_web3_nodes(blockchain=SupportedBlockchain.ETHEREUM, only_active=True)  # noqa: E501
        # Initialize blockchain querying modules
        ethereum_manager = EthereumManager(
            etherscan=self.etherscan,
            msg_aggregator=self.msg_aggregator,
            greenlet_manager=self.greenlet_manager,
            database=self.data.db,
            connect_at_start=ethereum_nodes,
        )
        kusama_manager = SubstrateManager(
            chain=SubstrateChain.KUSAMA,
            msg_aggregator=self.msg_aggregator,
            greenlet_manager=self.greenlet_manager,
            connect_at_start=KUSAMA_NODES_TO_CONNECT_AT_START,
            connect_on_startup=len(blockchain_accounts.ksm) != 0,
            own_rpc_endpoint=settings.ksm_rpc_endpoint,
        )
        polkadot_manager = SubstrateManager(
            chain=SubstrateChain.POLKADOT,
            msg_aggregator=self.msg_aggregator,
            greenlet_manager=self.greenlet_manager,
            connect_at_start=POLKADOT_NODES_TO_CONNECT_AT_START,
            connect_on_startup=len(blockchain_accounts.dot) != 0,
            own_rpc_endpoint=settings.dot_rpc_endpoint,
        )
        self.eth_transactions = EthTransactions(ethereum=ethereum_manager, database=self.data.db)
        self.covalent_avalanche = Covalent(
            database=self.data.db,
            msg_aggregator=self.msg_aggregator,
            chain_id=chains_id['avalanche'],
        )
        avalanche_manager = AvalancheManager(
            avaxrpc_endpoint="https://api.avax.network/ext/bc/C/rpc",
            covalent=self.covalent_avalanche,
            msg_aggregator=self.msg_aggregator,
        )

        Inquirer().inject_ethereum(ethereum_manager)
        uniswap_v2_oracle = UniswapV2Oracle(ethereum_manager)
        uniswap_v3_oracle = UniswapV3Oracle(ethereum_manager)
        saddle_oracle = SaddleOracle(ethereum_manager)
        Inquirer().add_defi_oracles(
            uniswap_v2=uniswap_v2_oracle,
            uniswap_v3=uniswap_v3_oracle,
            saddle=saddle_oracle,
        )
        Inquirer().set_oracles_order(settings.current_price_oracles)

        self.chain_manager = ChainManager(
            blockchain_accounts=blockchain_accounts,
            ethereum_manager=ethereum_manager,
            kusama_manager=kusama_manager,
            polkadot_manager=polkadot_manager,
            avalanche_manager=avalanche_manager,
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            greenlet_manager=self.greenlet_manager,
            premium=self.premium,
            eth_modules=settings.active_modules,
            data_directory=self.data_dir,
            beaconchain=self.beaconchain,
            btc_derivation_gap_limit=settings.btc_derivation_gap_limit,
        )
        self.eth_tx_decoder = EVMTransactionDecoder(
            database=self.data.db,
            ethereum_manager=ethereum_manager,
            transactions=self.eth_transactions,
            msg_aggregator=self.msg_aggregator,
        )
        self.evm_accounting_aggregator = EVMAccountingAggregator(
            ethereum_manager=ethereum_manager,
            msg_aggregator=self.msg_aggregator,
        )
        self.accountant = Accountant(
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            evm_accounting_aggregator=self.evm_accounting_aggregator,
            premium=self.premium,
        )
        self.events_historian = EventsHistorian(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            chain_manager=self.chain_manager,
            eth_tx_decoder=self.eth_tx_decoder,
        )
        self.task_manager = TaskManager(
            max_tasks_num=DEFAULT_MAX_TASKS_NUM,
            greenlet_manager=self.greenlet_manager,
            api_task_greenlets=self.api_task_greenlets,
            database=self.data.db,
            cryptocompare=self.cryptocompare,
            premium_sync_manager=self.premium_sync_manager,
            chain_manager=self.chain_manager,
            exchange_manager=self.exchange_manager,
            eth_tx_decoder=self.eth_tx_decoder,
            deactivate_premium=self.deactivate_premium_status,
            activate_premium=self.activate_premium_status,
            query_balances=self.query_balances,
            update_curve_pools_cache=self.update_curve_pools_cache,
            msg_aggregator=self.msg_aggregator,
        )

        DataMigrationManager(self).maybe_migrate_data()
        self.greenlet_manager.spawn_and_track(
            after_seconds=5,
            task_name='periodically_query_icons_until_all_cached',
            exception_is_error=False,
            method=self.icon_manager.periodically_query_icons_until_all_cached,
            batch_size=ICONS_BATCH_SIZE,
            sleep_time_secs=ICONS_QUERY_SLEEP,
        )
        self.user_is_logged_in = True
        log.debug('User unlocking complete')

    def _logout(self) -> None:
        if not self.user_is_logged_in:
            return
        user = self.data.username
        log.info(
            'Logging out user',
            user=user,
        )

        self.deactivate_premium_status()
        self.greenlet_manager.clear()
        del self.chain_manager
        self.exchange_manager.delete_all_exchanges()

        del self.accountant
        del self.events_historian
        del self.data_importer

        self.data.logout()
        self.password = ''
        self.cryptocompare.unset_database()

        # Make sure no messages leak to other user sessions
        self.msg_aggregator.consume_errors()
        self.msg_aggregator.consume_warnings()
        self.task_manager = None

        self.user_is_logged_in = False
        log.info(
            'User successfully logged out',
            user=user,
        )

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
                self.premium = premium_create_and_verify(credentials)
            except RemoteError as e:
                raise PremiumAuthenticationError(str(e)) from e

        self.premium_sync_manager.premium = self.premium
        self.accountant.activate_premium_status(self.premium)
        self.chain_manager.activate_premium_status(self.premium)

        self.data.db.set_rotkehlchen_premium(credentials)

    def deactivate_premium_status(self) -> None:
        """Deactivate premium in the current session"""
        self.premium = None
        self.premium_sync_manager.premium = None
        self.accountant.deactivate_premium_status()
        self.chain_manager.deactivate_premium_status()

    def activate_premium_status(self, premium: Premium) -> None:
        """Activate premium in the current session if was deactivated"""
        self.premium = premium
        self.premium_sync_manager.premium = self.premium
        self.accountant.activate_premium_status(self.premium)
        self.chain_manager.activate_premium_status(self.premium)

    def delete_premium_credentials(self) -> Tuple[bool, str]:
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
            if self.task_manager is not None:
                self.task_manager.schedule()

    def get_blockchain_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> Union[List[BlockchainAccountData], Dict[str, Any]]:
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
            addresses=list(addresses_to_account_data.keys()),  # type: ignore
        )

        xpub_mappings: Dict['XpubData', List[BlockchainAccountData]] = {}
        for address, xpub_entry in address_to_xpub_mappings.items():
            if xpub_entry not in xpub_mappings:
                xpub_mappings[xpub_entry] = []
            xpub_mappings[xpub_entry].append(addresses_to_account_data[address])

        data: Dict[str, Any] = {'standalone': [], 'xpubs': []}
        # Add xpub data
        for xpub_entry in xpub_data:
            data_entry = xpub_entry.serialize()
            addresses = xpub_mappings.get(xpub_entry, None)
            data_entry['addresses'] = addresses if addresses and len(addresses) != 0 else None
            data['xpubs'].append(data_entry)
        # Add standalone addresses
        for account in account_data:
            if account.address not in address_to_xpub_mappings:
                data['standalone'].append(account)

        return data

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
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
        with self.data.db.user_write() as cursor:
            self.data.db.ensure_tags_exist(
                cursor,
                given_data=account_data,
                action='adding',
                data_type='blockchain accounts',
            )
            address_type = blockchain.get_address_type()
            self.chain_manager.add_blockchain_accounts(
                blockchain=blockchain,
                accounts=[address_type(entry.address) for entry in account_data],
            )
            self.data.db.add_blockchain_accounts(
                cursor,
                blockchain=blockchain,
                account_data=account_data,
            )

    def edit_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> None:
        """Edits blockchain accounts

        Edits blockchain account data for the given accounts

        May raise:
        - InputError if the given accounts list is empty or if
        any of the accounts to edit do not exist.
        - TagConstraintError if any of the given account data contain unknown tags.
        """
        # First check for validity of account data addresses
        if len(account_data) == 0:
            raise InputError('Empty list of blockchain account data to edit was given')
        accounts = [x.address for x in account_data]
        unknown_accounts = set(accounts).difference(self.chain_manager.accounts.get(blockchain))
        if len(unknown_accounts) != 0:
            raise InputError(
                f'Tried to edit unknown {blockchain.value} '
                f'accounts {",".join(unknown_accounts)}',
            )

        self.data.db.ensure_tags_exist(
            write_cursor,
            given_data=account_data,
            action='editing',
            data_type='blockchain accounts',
        )
        # Finally edit the accounts
        self.data.db.edit_blockchain_accounts(
            write_cursor,
            blockchain=blockchain,
            account_data=account_data,
        )

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes blockchain accounts

        Removes the accounts from the blockchain instance. Also removes them from the DB.

        May raise:
        - InputError if a non-existing account was given to remove
        """
        self.chain_manager.remove_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )
        eth_addresses: List[ChecksumEvmAddress] = cast(List[ChecksumEvmAddress], accounts) if blockchain == SupportedBlockchain.ETHEREUM else []  # noqa: E501
        with contextlib.ExitStack() as stack:
            cursor = stack.enter_context(self.data.db.user_write())
            if blockchain == SupportedBlockchain.ETHEREUM:
                stack.enter_context(self.eth_transactions.wait_until_no_query_for(eth_addresses))
                stack.enter_context(self.eth_transactions.missing_receipts_lock)
                stack.enter_context(self.eth_tx_decoder.undecoded_tx_query_lock)
            self.data.db.remove_blockchain_accounts(cursor, blockchain, accounts)

    def get_history_query_status(self) -> Dict[str, str]:
        if self.events_historian.progress < FVal('100'):
            processing_state = self.events_historian.processing_state_name
            progress = self.events_historian.progress / 2
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
    ) -> Tuple[int, str]:
        error_or_empty, events = self.events_historian.get_history(
            start_ts=start_ts,
            end_ts=end_ts,
            has_premium=self.premium is not None,
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
            timestamp: Timestamp = None,
            ignore_cache: bool = False,
    ) -> Dict[str, Any]:
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

        balances: Dict[str, Dict[Asset, Balance]] = {}
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
                if location_str not in balances:
                    # `AssetWithSymbol` is a subclass of `Asset` mypy error is strange
                    balances[location_str] = exchange_balances  # type: ignore
                else:  # multiple exchange of same type. Combine balances
                    balances[location_str] = combine_dicts(
                        balances[location_str],
                        exchange_balances,  # type: ignore
                    )

        liabilities: Dict[Asset, Balance]
        try:
            blockchain_result = self.chain_manager.query_balances(
                blockchain=None,
                beaconchain_fetch_eth1=ignore_cache,
                ignore_cache=ignore_cache,
            )
            if len(blockchain_result.totals.assets) != 0:
                balances[str(Location.BLOCKCHAIN)] = blockchain_result.totals.assets
            liabilities = blockchain_result.totals.liabilities
        except (RemoteError, EthSyncError) as e:
            problem_free = False
            liabilities = {}
            log.error(f'Querying blockchain balances failed due to: {str(e)}')
            self.msg_aggregator.add_message(
                message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
                data={'location': 'blockchain balances query', 'error': str(e)},
            )

        manually_tracked_liabilities = get_manually_tracked_balances(
            db=self.data.db,
            balance_type=BalanceType.LIABILITY,
        )
        manual_liabilities_as_dict: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for manual_liability in manually_tracked_liabilities:
            manual_liabilities_as_dict[manual_liability.asset] += manual_liability.value

        liabilities = combine_dicts(liabilities, manual_liabilities_as_dict)
        # retrieve loopring balances if module is activated
        if self.chain_manager.get_module('loopring'):
            try:
                loopring_balances = self.chain_manager.get_loopring_balances()
            except RemoteError as e:
                problem_free = False
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
                    data={'location': 'loopring', 'error': str(e)},
                )
            else:
                if len(loopring_balances) != 0:
                    balances[str(Location.LOOPRING)] = loopring_balances

        uniswap_v3_balances = None
        try:
            uniswap_v3_balances = self.chain_manager.query_ethereum_lp_balances(balances=balances)
        except RemoteError as e:
            log.error(
                f'At balance snapshot LP balances query failed due to {str(e)}. Error '
                f'is ignored and balance snapshot will still be saved.',
            )

        # retrieve nft balances if module is activated
        nfts = self.chain_manager.get_module('nfts')
        if nfts is not None:
            try:
                nft_mapping = nfts.get_balances(
                    addresses=self.chain_manager.queried_addresses_for_module('nfts'),
                    uniswap_nfts=uniswap_v3_balances,
                    return_zero_values=False,
                    ignore_cache=False,
                )
            except RemoteError as e:
                log.error(
                    f'At balance snapshot NFT balances query failed due to {str(e)}. Error '
                    f'is ignored and balance snapshot will still be saved.',
                )
            else:
                if len(nft_mapping) != 0:
                    if str(Location.BLOCKCHAIN) not in balances:
                        balances[str(Location.BLOCKCHAIN)] = {}

                    for nft_balances in nft_mapping.values():
                        for balance_entry in nft_balances:
                            balances[str(Location.BLOCKCHAIN)][CryptoAsset(
                                balance_entry['id'])] = Balance(
                                amount=ONE,
                                usd_value=balance_entry['usd_price'],
                            )

        balances = account_for_manually_tracked_asset_balances(db=self.data.db, balances=balances)

        # Calculate usd totals
        assets_total_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        total_usd_per_location: Dict[str, FVal] = {}
        for location, asset_balance in balances.items():
            total_usd_per_location[location] = ZERO
            for asset, balance in asset_balance.items():
                assets_total_balance[asset] += balance
                total_usd_per_location[location] += balance.usd_value

        net_usd = sum((balance.usd_value for _, balance in assets_total_balance.items()), ZERO)
        liabilities_total_usd = sum((liability.usd_value for _, liability in liabilities.items()), ZERO)  # noqa: E501
        net_usd -= liabilities_total_usd

        # Calculate location stats
        location_stats: Dict[str, Any] = {}
        for location, total_usd in total_usd_per_location.items():
            if location == str(Location.BLOCKCHAIN):
                total_usd -= liabilities_total_usd

            percentage = (total_usd / net_usd).to_percentage() if net_usd != ZERO else '0%'
            location_stats[location] = {
                'usd_value': total_usd,
                'percentage_of_net_value': percentage,
            }

        # Calculate 'percentage_of_net_value' per asset
        assets_total_balance_as_dict: Dict[Asset, Dict[str, Any]] = {
            asset: balance.to_dict() for asset, balance in assets_total_balance.items()
        }
        liabilities_as_dict: Dict[Asset, Dict[str, Any]] = {
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
        with self.data.db.user_write() as cursor:
            allowed_to_save = requested_save_data or self.data.db.should_save_balances(cursor)
            if (problem_free or save_despite_errors) and allowed_to_save:
                if not timestamp:
                    timestamp = Timestamp(int(time.time()))
                self.data.db.save_balances_data(cursor, data=result_dict, timestamp=timestamp)
                log.debug('query_balances data saved')
            else:
                log.debug(
                    'query_balances data not saved',
                    allowed_to_save=allowed_to_save,
                    problem_free=problem_free,
                    save_despite_errors=save_despite_errors,
                )

        return result_dict

    def set_settings(self, settings: ModifiableDBSettings) -> Tuple[bool, str]:
        """Tries to set new settings. Returns True in success or False with message if error"""
        if settings.ksm_rpc_endpoint is not None:
            result, msg = self.chain_manager.set_ksm_rpc_endpoint(settings.ksm_rpc_endpoint)
            if not result:
                return False, msg

        if settings.dot_rpc_endpoint is not None:
            result, msg = self.chain_manager.set_dot_rpc_endpoint(settings.dot_rpc_endpoint)
            if not result:
                return False, msg

        if settings.btc_derivation_gap_limit is not None:
            self.chain_manager.btc_derivation_gap_limit = settings.btc_derivation_gap_limit

        if settings.current_price_oracles is not None:
            Inquirer().set_oracles_order(settings.current_price_oracles)

        if settings.historical_price_oracles is not None:
            PriceHistorian().set_oracles_order(settings.historical_price_oracles)

        if settings.active_modules is not None:
            self.chain_manager.process_new_modules_list(settings.active_modules)

        with self.data.db.user_write() as cursor:
            self.data.db.set_settings(cursor, settings)
        return True, ''

    def get_settings(self, cursor: 'DBCursor') -> DBSettings:
        """Returns the db settings with a check whether premium is active or not"""
        return self.data.db.get_settings(cursor, have_premium=self.premium is not None)

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
            kraken_account_type: Optional['KrakenAccountType'] = None,
            binance_selected_trade_pairs: Optional[List[str]] = None,
            ftx_subaccount: Optional[str] = None,
    ) -> Tuple[bool, str]:
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
            ftx_subaccount=ftx_subaccount,
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
                ftx_subaccount=ftx_subaccount,
            )
        return is_success, msg

    def remove_exchange(self, name: str, location: Location) -> Tuple[bool, str]:
        if self.exchange_manager.get_exchange(name=name, location=location) is None:
            return False, f'{str(location)} exchange {name} is not registered'

        self.exchange_manager.delete_exchange(name=name, location=location)
        # Success, remove it also from the DB
        with self.data.db.user_write() as cursor:
            self.data.db.remove_exchange(write_cursor=cursor, name=name, location=location)
            if self.exchange_manager.connected_exchanges.get(location) is None:
                # was last exchange of the location type. Delete used query ranges
                self.data.db.delete_used_query_range_for_exchange(write_cursor=cursor, location=location)  # noqa: E501
        return True, ''

    def query_periodic_data(self) -> Dict[str, Union[bool, List[str], Timestamp]]:
        """Query for frequently changing data"""
        result: Dict[str, Union[bool, List[str], Timestamp]] = {}

        if self.user_is_logged_in:
            with self.data.db.conn.read_ctx() as cursor:
                result['last_balance_save'] = self.data.db.get_last_balance_save_time(cursor)
                result['connected_eth_nodes'] = [node.name for node in self.chain_manager.ethereum.get_connected_nodes()]  # noqa: E501
                result['last_data_upload_ts'] = Timestamp(self.premium_sync_manager.last_data_upload_ts)  # noqa : E501
        return result

    def shutdown(self) -> None:
        self.logout()
        self.shutdown_event.set()

    def create_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: Asset,
            to_asset: Asset,
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

        self.cryptocompare.create_cache(from_asset, to_asset, purge_old)

    def update_curve_pools_cache(self) -> None:
        """Updates curve pools cache.
        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb
        """

        # Using shared cursor to not end up having partially populated cache
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # Delete current cache. Need to do this in case curve removes some pools
            clear_curve_pools_cache(write_cursor=write_cursor)
            # write new values to the cache
            update_curve_registry_pools_cache(
                write_cursor=write_cursor,
                ethereum_manager=self.chain_manager.ethereum,
            )
            update_curve_metapools_cache(
                write_cursor=write_cursor,
                ethereum_manager=self.chain_manager.ethereum,
            )
            try:
                curve_decoder = self.eth_tx_decoder.decoders['Curve']
            except KeyError as e:
                raise InputError(
                    'Expected to find Curve decoder but it was not loaded. '
                    'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
                ) from e
            new_mappings = curve_decoder.reload()
            self.eth_tx_decoder.address_mappings.update(new_mappings)
