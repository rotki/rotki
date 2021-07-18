#!/usr/bin/env python

import argparse
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
    Optional,
    Tuple,
    Union,
    cast,
    overload,
)

import gevent
from typing_extensions import Literal

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.structures import Balance
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import account_for_manually_tracked_balances
from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    EthereumManager,
    NodeName,
)
from rotkehlchen.chain.ethereum.trades import AMMTRADE_LOCATION_NAMES, AMMTrade, AMMTradeLocations
from rotkehlchen.chain.manager import BlockchainBalancesUpdate, ChainManager
from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.typing import SubstrateChain
from rotkehlchen.chain.substrate.utils import KUSAMA_NODES_TO_CONNECT_AT_START
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data.importer import DataImporter
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.settings import DBSettings, ModifiableDBSettings
from rotkehlchen.errors import (
    EthSyncError,
    InputError,
    PremiumAuthenticationError,
    RemoteError,
    SystemPermissionError,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.manager import ALL_SUPPORTED_EXCHANGES, ExchangeManager
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.globaldb.updates import AssetsUpdater
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.history.events import FREE_LEDGER_ACTIONS_LIMIT, EventsHistorian
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter, configure_logging
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.tasks.manager import DEFAULT_MAX_TASKS_NUM, TaskManager
from rotkehlchen.typing import (
    EXTERNAL_EXCHANGES,
    EXTERNAL_LOCATION,
    ApiKey,
    ApiSecret,
    BlockchainAccountData,
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
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 10
FREE_TRADES_LIMIT = 250
FREE_ASSET_MOVEMENTS_LIMIT = 100

LIMITS_MAPPING = {
    'trade': FREE_TRADES_LIMIT,
    'asset_movement': FREE_ASSET_MOVEMENTS_LIMIT,
    'ledger_action': FREE_LEDGER_ACTIONS_LIMIT,
}

ICONS_BATCH_SIZE = 3
ICONS_QUERY_SLEEP = 60


TRADES_LIST = List[Union[Trade, AMMTrade]]


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
        configure_logging(args)

        self.sleep_secs = args.sleep_secs
        if args.data_dir is None:
            self.data_dir = default_data_directory()
        else:
            self.data_dir = Path(args.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        if not os.access(self.data_dir, os.W_OK | os.R_OK):
            raise SystemPermissionError(
                f'The given data directory {self.data_dir} is not readable or writable',
            )
        self.main_loop_spawned = False
        self.args = args
        self.api_task_greenlets: List[gevent.Greenlet] = []
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(msg_aggregator=self.msg_aggregator)
        self.rotki_notifier = RotkiNotifier(greenlet_manager=self.greenlet_manager)
        self.msg_aggregator.rotki_notifier = self.rotki_notifier
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        # Initialize the GlobalDBHandler singleton. Has to be initialized BEFORE asset resolver
        GlobalDBHandler(data_dir=self.data_dir)
        self.data = DataHandler(self.data_dir, self.msg_aggregator)
        self.cryptocompare = Cryptocompare(data_directory=self.data_dir, database=None)
        self.coingecko = Coingecko()
        self.icon_manager = IconManager(data_dir=self.data_dir, coingecko=self.coingecko)
        self.assets_updater = AssetsUpdater(self.msg_aggregator)
        # Initialize the Inquirer singleton
        Inquirer(
            data_dir=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
        )
        # Keeps how many trades we have found per location. Used for free user limiting
        self.actions_per_location: Dict[str, Dict[Location, int]] = {
            'trade': defaultdict(int),
            'asset_movement': defaultdict(int),
        }
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
    ) -> None:
        """Unlocks an existing user or creates a new one if `create_new` is True

        May raise:
        - PremiumAuthenticationError if the password can't unlock the database.
        - AuthenticationError if premium_credentials are given and are invalid
        or can't authenticate with the server
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error.
        - SystemPermissionError if the directory or DB file can not be accessed
        """
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
            initial_settings=initial_settings,
        )

        # unlock or create the DB
        self.password = password
        self.user_directory = self.data.unlock(user, password, create_new, initial_settings)
        self.data_importer = DataImporter(db=self.data.db)
        self.last_data_upload_ts = self.data.db.get_last_data_upload_ts()
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

        settings = self.get_settings()
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='submit_usage_analytics',
            exception_is_error=False,
            method=maybe_submit_usage_analytics,
            should_submit=settings.submit_usage_analytics,
        )
        self.etherscan = Etherscan(database=self.data.db, msg_aggregator=self.msg_aggregator)
        self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)
        eth_rpc_endpoint = settings.eth_rpc_endpoint
        # Initialize the price historian singleton
        PriceHistorian(
            data_directory=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
        )
        PriceHistorian().set_oracles_order(settings.historical_price_oracles)

        self.accountant = Accountant(
            db=self.data.db,
            user_directory=self.user_directory,
            msg_aggregator=self.msg_aggregator,
            create_csv=True,
            premium=self.premium,
        )

        exchange_credentials = self.data.db.get_exchange_credentials()
        self.exchange_manager.initialize_exchanges(
            exchange_credentials=exchange_credentials,
            database=self.data.db,
        )

        # Initialize blockchain querying modules
        ethereum_manager = EthereumManager(
            ethrpc_endpoint=eth_rpc_endpoint,
            etherscan=self.etherscan,
            database=self.data.db,
            msg_aggregator=self.msg_aggregator,
            greenlet_manager=self.greenlet_manager,
            connect_at_start=ETHEREUM_NODES_TO_CONNECT_AT_START,
        )
        kusama_manager = SubstrateManager(
            chain=SubstrateChain.KUSAMA,
            msg_aggregator=self.msg_aggregator,
            greenlet_manager=self.greenlet_manager,
            connect_at_start=KUSAMA_NODES_TO_CONNECT_AT_START,
            connect_on_startup=self._connect_ksm_manager_on_startup(),
            own_rpc_endpoint=settings.ksm_rpc_endpoint,
        )

        Inquirer().inject_ethereum(ethereum_manager)
        Inquirer().set_oracles_order(settings.current_price_oracles)

        self.chain_manager = ChainManager(
            blockchain_accounts=self.data.db.get_blockchain_accounts(),
            ethereum_manager=ethereum_manager,
            kusama_manager=kusama_manager,
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            greenlet_manager=self.greenlet_manager,
            premium=self.premium,
            eth_modules=settings.active_modules,
            data_directory=self.data_dir,
            beaconchain=self.beaconchain,
            btc_derivation_gap_limit=settings.btc_derivation_gap_limit,
        )
        self.events_historian = EventsHistorian(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            chain_manager=self.chain_manager,
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
        )
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

    def logout(self) -> None:
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

    def set_premium_credentials(self, credentials: PremiumCredentials) -> None:
        """
        Sets the premium credentials for rotki

        Raises PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        log.info('Setting new premium credentials')
        if self.premium is not None:
            self.premium.set_credentials(credentials)
        else:
            self.premium = premium_create_and_verify(credentials)
            self.premium_sync_manager.premium = self.premium
            self.accountant.premium = self.premium

        self.data.db.set_rotkehlchen_premium(credentials)

    def delete_premium_credentials(self) -> Tuple[bool, str]:
        """Deletes the premium credentials for rotki"""
        msg = ''

        success = self.data.db.del_rotkehlchen_premium()
        if success is False:
            msg = 'The database was unable to delete the Premium keys for the logged-in user'
        self.deactivate_premium_status()
        return success, msg

    def deactivate_premium_status(self) -> None:
        """Deactivate premium in the current session"""
        self.premium = None
        self.premium_sync_manager.premium = None
        self.chain_manager.deactivate_premium_status()
        self.accountant.deactivate_premium_status()

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
            blockchain: SupportedBlockchain,
    ) -> Union[List[BlockchainAccountData], Dict[str, Any]]:
        account_data = self.data.db.get_blockchain_account_data(blockchain)
        if blockchain != SupportedBlockchain.BITCOIN:
            return account_data

        xpub_data = self.data.db.get_bitcoin_xpub_data()
        addresses_to_account_data = {x.address: x for x in account_data}
        address_to_xpub_mappings = self.data.db.get_addresses_to_xpub_mapping(
            list(addresses_to_account_data.keys()),  # type: ignore
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
    ) -> BlockchainBalancesUpdate:
        """Adds new blockchain accounts

        Adds the accounts to the blockchain instance and queries them to get the
        updated balances. Also adds them in the DB

        May raise:
        - EthSyncError from modify_blockchain_account
        - InputError if the given accounts list is empty.
        - TagConstraintError if any of the given account data contain unknown tags.
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        self.data.db.ensure_tags_exist(
            given_data=account_data,
            action='adding',
            data_type='blockchain accounts',
        )
        address_type = blockchain.get_address_type()
        updated_balances = self.chain_manager.add_blockchain_accounts(
            blockchain=blockchain,
            accounts=[address_type(entry.address) for entry in account_data],
        )
        self.data.db.add_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
        )

        return updated_balances

    def edit_blockchain_accounts(
            self,
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
            given_data=account_data,
            action='editing',
            data_type='blockchain accounts',
        )

        # Finally edit the accounts
        self.data.db.edit_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
        )

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> BlockchainBalancesUpdate:
        """Removes blockchain accounts

        Removes the accounts from the blockchain instance and queries them to get
        the updated balances. Also removes them from the DB

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - InputError if a non-existing account was given to remove
        """
        balances_update = self.chain_manager.remove_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )
        self.data.db.remove_blockchain_accounts(blockchain, accounts)
        return balances_update

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
                self.accountant.events.query_start_ts,
                self.accountant.first_processed_timestamp,
            )
            diff = self.accountant.events.query_end_ts - start_ts
            progress = 50 + 100 * (
                FVal(self.accountant.currently_processing_timestamp - start_ts) /
                FVal(diff) / 2)

        return {'processing_state': str(processing_state), 'total_progress': str(progress)}

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[Dict[str, Any], str]:
        (
            error_or_empty,
            history,
            loan_history,
            asset_movements,
            eth_transactions,
            defi_events,
            ledger_actions,
        ) = self.events_historian.get_history(
            start_ts=start_ts,
            end_ts=end_ts,
            has_premium=self.premium is not None,
        )
        result = self.accountant.process_history(
            start_ts=start_ts,
            end_ts=end_ts,
            trade_history=history,
            loan_history=loan_history,
            asset_movements=asset_movements,
            eth_transactions=eth_transactions,
            defi_events=defi_events,
            ledger_actions=ledger_actions,
        )
        return result, error_or_empty

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
                if self.premium is None:
                    trades = self._apply_actions_limit(
                        location=exchange.location,
                        action_type='trade',
                        location_actions=exchange_trades,
                        all_actions=trades,
                    )
                else:
                    trades.extend(exchange_trades)

            # for all trades we also need the trades from the amm protocols
            if self.premium is not None:
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
            location_trades = self.data.db.get_trades(  # type: ignore  # list invariance
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )
        elif location in AMMTradeLocations:
            if self.premium is not None:
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
                logger.warning(
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
        if self.premium is None:
            trades = self._apply_actions_limit(
                location=location,
                action_type='trade',
                location_actions=location_trades,
                all_actions=trades,
            )
        else:
            trades = location_trades

        return trades

    def query_balances(
            self,
            requested_save_data: bool = False,
            timestamp: Timestamp = None,
            ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """Query all balances rotkehlchen can see.

        If requested_save_data is True then the data are always saved in the DB,
        if it is False then data are saved if self.data.should_save_balances()
        is True.
        If timestamp is None then the current timestamp is used.
        If a timestamp is given then that is the time that the balances are going
        to be saved in the DB
        If ignore_cache is True then all underlying calls that have a cache ignore it

        Returns a dictionary with the queried balances.
        """
        log.info('query_balances called', requested_save_data=requested_save_data)

        balances: Dict[str, Dict[Asset, Balance]] = {}
        problem_free = True
        for exchange in self.exchange_manager.iterate_exchanges():
            exchange_balances, _ = exchange.query_balances(ignore_cache=ignore_cache)
            # If we got an error, disregard that exchange but make sure we don't save data
            if not isinstance(exchange_balances, dict):
                problem_free = False
            else:
                location_str = str(exchange.location)
                if location_str not in balances:
                    balances[location_str] = exchange_balances
                else:  # multiple exchange of same type. Combine balances
                    balances[location_str] = combine_dicts(
                        balances[location_str],
                        exchange_balances,
                    )

        liabilities: Dict[Asset, Balance]
        try:
            blockchain_result = self.chain_manager.query_balances(
                blockchain=None,
                force_token_detection=ignore_cache,
                ignore_cache=ignore_cache,
            )
            if len(blockchain_result.totals.assets) != 0:
                balances[str(Location.BLOCKCHAIN)] = blockchain_result.totals.assets
            liabilities = blockchain_result.totals.liabilities
        except (RemoteError, EthSyncError) as e:
            problem_free = False
            liabilities = {}
            log.error(f'Querying blockchain balances failed due to: {str(e)}')

        # retrieve loopring balances if module is activated
        if self.chain_manager.get_module('loopring'):
            loopring_balances = self.chain_manager.get_loopring_balances()
            if len(loopring_balances) != 0:
                balances[str(Location.LOOPRING)] = loopring_balances

        balances = account_for_manually_tracked_balances(db=self.data.db, balances=balances)

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
        allowed_to_save = requested_save_data or self.data.should_save_balances()

        if problem_free and allowed_to_save:
            if not timestamp:
                timestamp = Timestamp(int(time.time()))
            self.data.db.save_balances_data(data=result_dict, timestamp=timestamp)
            log.debug('query_balances data saved')
        else:
            log.debug(
                'query_balances data not saved',
                allowed_to_save=allowed_to_save,
                problem_free=problem_free,
            )

        return result_dict

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
            location_movements = self.data.db.get_asset_movements(
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )

        movements: List[AssetMovement] = []
        if self.premium is None:
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
                    logger.warning(
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

    def set_settings(self, settings: ModifiableDBSettings) -> Tuple[bool, str]:
        """Tries to set new settings. Returns True in success or False with message if error"""
        if settings.eth_rpc_endpoint is not None:
            result, msg = self.chain_manager.set_eth_rpc_endpoint(settings.eth_rpc_endpoint)
            if not result:
                return False, msg

        if settings.ksm_rpc_endpoint is not None:
            result, msg = self.chain_manager.set_ksm_rpc_endpoint(settings.ksm_rpc_endpoint)
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

        self.data.db.set_settings(settings)
        return True, ''

    def get_settings(self) -> DBSettings:
        """Returns the db settings with a check whether premium is active or not"""
        db_settings = self.data.db.get_settings(have_premium=self.premium is not None)
        return db_settings

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
            kraken_account_type: Optional['KrakenAccountType'] = None,
            binance_markets: Optional[List[str]] = None,
            ftx_subaccount_name: Optional[str] = None,
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
            ftx_subaccount_name=ftx_subaccount_name,
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
                binance_markets=binance_markets,
                ftx_subaccount_name=ftx_subaccount_name,
            )
        return is_success, msg

    def remove_exchange(self, name: str, location: Location) -> Tuple[bool, str]:
        if self.exchange_manager.get_exchange(name=name, location=location) is None:
            return False, f'{str(location)} exchange {name} is not registered'

        self.exchange_manager.delete_exchange(name=name, location=location)
        # Success, remove it also from the DB
        self.data.db.remove_exchange(name=name, location=location)
        if self.exchange_manager.connected_exchanges.get(location) is None:
            # was last exchange of the location type. Delete used query ranges
            self.data.db.delete_used_query_range_for_exchange(location)
        return True, ''

    def query_periodic_data(self) -> Dict[str, Union[bool, Timestamp]]:
        """Query for frequently changing data"""
        result: Dict[str, Union[bool, Timestamp]] = {}

        if self.user_is_logged_in:
            result['last_balance_save'] = self.data.db.get_last_balance_save_time()
            result['eth_node_connection'] = self.chain_manager.ethereum.web3_mapping.get(NodeName.OWN, None) is not None  # noqa : E501
            result['last_data_upload_ts'] = Timestamp(self.premium_sync_manager.last_data_upload_ts)  # noqa : E501
        return result

    def shutdown(self) -> None:
        self.logout()
        self.shutdown_event.set()

    def _connect_ksm_manager_on_startup(self) -> bool:
        return bool(self.data.db.get_blockchain_accounts().ksm)

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
