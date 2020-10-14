#!/usr/bin/env python

import argparse
import logging.config
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, overload

import gevent
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.balances.manual import account_for_manually_tracked_balances
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    EthereumManager,
    NodeName,
)
from rotkehlchen.chain.manager import BlockchainBalancesUpdate, ChainManager
from rotkehlchen.config import default_data_directory
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
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.history import PriceHistorian, TradesHistorian
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import (
    DEFAULT_ANONYMIZED_LOGS,
    LoggingSettings,
    RotkehlchenLogsAdapter,
    configure_logging,
)
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.serialization.deserialize import deserialize_location
from rotkehlchen.typing import (
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
from rotkehlchen.utils.misc import combine_stat_dicts, dict_get_sumof, merge_dicts

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 15
FREE_TRADES_LIMIT = 250
FREE_ASSET_MOVEMENTS_LIMIT = 100
LIMITS_MAPPING = {
    'trade': FREE_TRADES_LIMIT,
    'asset_movement': FREE_ASSET_MOVEMENTS_LIMIT,
}

ICONS_BATCH_SIZE = 5
ICONS_QUERY_SLEEP = 10


class Rotkehlchen():
    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the Rotkehlchen object

        May Raise:
        - SystemPermissionError if the given data directory's permissions
        are not correct.
        """
        self.lock = Semaphore()
        self.lock.acquire()

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

        if not os.access(self.data_dir, os.W_OK | os.R_OK):
            raise SystemPermissionError(
                f'The given data directory {self.data_dir} is not readable or writable',
            )
        self.args = args
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(msg_aggregator=self.msg_aggregator)
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        # Initialize the AssetResolver singleton
        AssetResolver(data_directory=self.data_dir)
        self.data = DataHandler(self.data_dir, self.msg_aggregator)
        self.cryptocompare = Cryptocompare(data_directory=self.data_dir, database=None)
        self.coingecko = Coingecko()
        self.icon_manager = IconManager(data_dir=self.data_dir, coingecko=self.coingecko)
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='periodically_query_icons_until_all_cached',
            method=self.icon_manager.periodically_query_icons_until_all_cached,
            batch_size=ICONS_BATCH_SIZE,
            sleep_time_secs=ICONS_QUERY_SLEEP,
        )
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

        self.lock.release()
        self.shutdown_event = gevent.event.Event()

    def reset_after_failed_account_creation_or_login(self) -> None:
        """If the account creation or login failed make sure that the Rotki instance is clear

        Tricky instances are when after either failed premium credentials or user refusal
        to sync premium databases we relogged in.
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
            self.msg_aggregator.add_error(
                'Tried to synchronize the database from remote but the local password '
                'does not match the one the remote DB has. Please change the password '
                'to be the same as the password of the account you want to sync from ',
            )
            # else let's just continue. User signed in succesfully, but he just
            # has unauthenticable/invalid premium credentials remaining in his DB

        settings = self.get_settings()
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='submit_usage_analytics',
            method=maybe_submit_usage_analytics,
            should_submit=settings.submit_usage_analytics,
        )
        self.etherscan = Etherscan(database=self.data.db, msg_aggregator=self.msg_aggregator)
        historical_data_start = settings.historical_data_start
        eth_rpc_endpoint = settings.eth_rpc_endpoint
        # Initialize the price historian singleton
        PriceHistorian(
            data_directory=self.data_dir,
            history_date_start=historical_data_start,
            cryptocompare=self.cryptocompare,
        )
        self.accountant = Accountant(
            db=self.data.db,
            user_directory=self.user_directory,
            msg_aggregator=self.msg_aggregator,
            create_csv=True,
        )

        # Initialize the rotkehlchen logger
        LoggingSettings(anonymized_logs=settings.anonymized_logs)
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
        Inquirer().inject_ethereum(ethereum_manager)
        self.chain_manager = ChainManager(
            blockchain_accounts=self.data.db.get_blockchain_accounts(),
            ethereum_manager=ethereum_manager,
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            greenlet_manager=self.greenlet_manager,
            premium=self.premium,
            eth_modules=settings.active_modules,
        )
        self.trades_historian = TradesHistorian(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            chain_manager=self.chain_manager,
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
        del self.chain_manager
        self.exchange_manager.delete_all_exchanges()

        # Reset rotkehlchen logger to default
        LoggingSettings(anonymized_logs=DEFAULT_ANONYMIZED_LOGS)

        del self.accountant
        del self.trades_historian
        del self.data_importer

        if self.premium is not None:
            del self.premium
        self.data.logout()
        self.password = ''
        self.cryptocompare.unset_database()

        # Make sure no messages leak to other user sessions
        self.msg_aggregator.consume_errors()
        self.msg_aggregator.consume_warnings()

        self.user_is_logged_in = False
        log.info(
            'User successfully logged out',
            user=user,
        )

    def set_premium_credentials(self, credentials: PremiumCredentials) -> None:
        """
        Sets the premium credentials for Rotki

        Raises PremiumAuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        log.info('Setting new premium credentials')
        if self.premium is not None:
            self.premium.set_credentials(credentials)
        else:
            self.premium = premium_create_and_verify(credentials)

        self.data.db.set_rotkehlchen_premium(credentials)

    def delete_premium_credentials(self, name: str) -> Tuple[bool, str]:
        """Deletes the premium credentials for Rotki"""
        success: bool
        msg = ''

        if name != self.data.username:
            msg = f'Provided user "{name}" is not the logged in user'
            success = False

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

    def premium_sync_data(
            self,
            name: str,
            action: Literal['upload', 'download'],
    ) -> Tuple[bool, str]:
        """Overwrites the remote database with the local one"""
        success: bool
        msg = ''

        if name != self.data.username:
            msg = f'Provided user "{name}" is not the logged in user'
            success = False
        else:
            success, msg = self.premium_sync_manager.sync_data(action)

        return success, msg

    def start(self) -> gevent.Greenlet:
        return gevent.spawn(self.main_loop)

    def main_loop(self) -> None:
        """Rotki main loop that fires often and manages many different tasks

        Each task remembers the last time it run successfully and know how often it
        should run. So each task manages itself.
        """
        # super hacky -- organize better when recurring tasks are implemented
        # https://github.com/rotki/rotki/issues/1106
        xpub_derivation_scheduled = False
        while self.shutdown_event.wait(MAIN_LOOP_SECS_DELAY) is not True:
            if self.user_is_logged_in:
                log.debug('Main loop start')
                self.premium_sync_manager.maybe_upload_data_to_server()
                log.debug('Main loop end')
                if not xpub_derivation_scheduled:
                    # 1 minute in the app's startup try to derive new xpub addresses
                    self.greenlet_manager.spawn_and_track(
                        after_seconds=60.0,
                        task_name='Derive new xpub addresses',
                        method=XpubManager(self.chain_manager).check_for_new_xpub_addresses,
                    )
                    xpub_derivation_scheduled = True

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

        return None

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
        ) = self.trades_historian.get_history(
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
        )
        return result, error_or_empty

    @overload
    def _apply_actions_limit(
            self,
            location: Location,
            action_type: Literal['trade'],
            location_actions: List[Trade],
            all_actions: List[Trade],
    ) -> List[Trade]:
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
            location_actions: Union[List[Trade], List[AssetMovement]],
            all_actions: Union[List[Trade], List[AssetMovement]],
    ) -> Union[List[Trade], List[AssetMovement]]:
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
    ) -> List[Trade]:
        """Queries trades for the given location and time range.
        If no location is given then all external and all exchange trades are queried.

        If the user does not have premium then a trade limit is applied.

        May raise:
        - RemoteError: If there are problems connectingto any of the remote exchanges
        """
        if location is not None:
            trades = self.query_location_trades(from_ts, to_ts, location)
        else:
            trades = self.query_location_trades(from_ts, to_ts, Location.EXTERNAL)
            for name, exchange in self.exchange_manager.connected_exchanges.items():
                exchange_trades = exchange.query_trade_history(start_ts=from_ts, end_ts=to_ts)
                if self.premium is None:
                    trades = self._apply_actions_limit(
                        location=deserialize_location(name),
                        action_type='trade',
                        location_actions=exchange_trades,
                        all_actions=trades,
                    )
                else:
                    trades.extend(exchange_trades)

        # return trades with most recent first
        trades.sort(key=lambda x: x.timestamp, reverse=True)
        return trades

    def query_location_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Location,
    ) -> List[Trade]:
        # clear the trades queried for this location
        self.actions_per_location['trade'][location] = 0

        if location == Location.EXTERNAL:
            location_trades = self.data.db.get_trades(
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )
        else:
            # should only be an exchange
            exchange = self.exchange_manager.get(str(location))
            if not exchange:
                logger.warn(
                    f'Tried to query trades from {location} which is either not an '
                    f'exchange or not an exchange the user has connected to',
                )
                return []

            location_trades = exchange.query_trade_history(start_ts=from_ts, end_ts=to_ts)

        trades: List[Trade] = []
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

        balances = {}
        problem_free = True
        for _, exchange in self.exchange_manager.connected_exchanges.items():
            exchange_balances, _ = exchange.query_balances(ignore_cache=ignore_cache)
            # If we got an error, disregard that exchange but make sure we don't save data
            if not isinstance(exchange_balances, dict):
                problem_free = False
            else:
                balances[exchange.name] = exchange_balances

        try:
            blockchain_result = self.chain_manager.query_balances(
                blockchain=None,
                force_token_detection=ignore_cache,
                ignore_cache=ignore_cache,
            )
            balances['blockchain'] = {
                asset: balance.to_dict() for asset, balance in blockchain_result.totals.items()
            }
        except (RemoteError, EthSyncError) as e:
            problem_free = False
            log.error(f'Querying blockchain balances failed due to: {str(e)}')

        balances = account_for_manually_tracked_balances(db=self.data.db, balances=balances)

        combined = combine_stat_dicts([v for k, v in balances.items()])
        total_usd_per_location = [(k, dict_get_sumof(v, 'usd_value')) for k, v in balances.items()]

        # calculate net usd value
        net_usd = FVal(0)
        for _, v in combined.items():
            net_usd += FVal(v['usd_value'])

        stats: Dict[str, Any] = {
            'location': {
            },
            'net_usd': net_usd,
        }
        for entry in total_usd_per_location:
            name = entry[0]
            total = entry[1]
            if net_usd != FVal(0):
                percentage = (total / net_usd).to_percentage()
            else:
                percentage = '0%'
            stats['location'][name] = {
                'usd_value': total,
                'percentage_of_net_value': percentage,
            }

        for k, v in combined.items():
            if net_usd != FVal(0):
                percentage = (v['usd_value'] / net_usd).to_percentage()
            else:
                percentage = '0%'
            combined[k]['percentage_of_net_value'] = percentage

        result_dict = merge_dicts(combined, stats)

        allowed_to_save = requested_save_data or self.data.should_save_balances()

        if problem_free and allowed_to_save:
            if not timestamp:
                timestamp = Timestamp(int(time.time()))
            self.data.save_balances_data(data=result_dict, timestamp=timestamp)
            log.debug('query_balances data saved')
        else:
            log.debug(
                'query_balances data not saved',
                allowed_to_save=allowed_to_save,
                problem_free=problem_free,
            )

        # After adding it to the saved file we can overlay additional data that
        # is not required to be saved in the history file
        try:
            details = self.accountant.events.details
            for asset, (tax_free_amount, average_buy_value) in details.items():
                if asset not in result_dict:
                    continue

                result_dict[asset]['tax_free_amount'] = tax_free_amount
                result_dict[asset]['average_buy_value'] = average_buy_value

                current_price = result_dict[asset]['usd_value'] / result_dict[asset]['amount']
                if average_buy_value != FVal(0):
                    result_dict[asset]['percent_change'] = (
                        ((current_price - average_buy_value) / average_buy_value) * 100
                    )
                else:
                    result_dict[asset]['percent_change'] = 'INF'

        except AttributeError:
            pass

        return result_dict

    def _query_exchange_asset_movements(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            all_movements: List[AssetMovement],
            exchange: ExchangeInterface,
    ) -> List[AssetMovement]:
        location = deserialize_location(exchange.name)
        # clear the asset movements queried for this exchange
        self.actions_per_location['asset_movement'][location] = 0
        location_movements = exchange.query_deposits_withdrawals(start_ts=from_ts, end_ts=to_ts)

        movements: List[AssetMovement] = []
        if self.premium is None:
            movements = self._apply_actions_limit(
                location=location,
                action_type='asset_movement',
                location_actions=location_movements,
                all_actions=all_movements,
            )
        else:
            movements = location_movements

        return movements

    def query_asset_movements(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
    ) -> List[AssetMovement]:
        """Queries AssetMovements for the given location and time range.

        If no location is given then all exchange asset movements are queried.
        If the user does not have premium then a limit is applied.
        May raise:
        - RemoteError: If there are problems connecting to any of the remote exchanges
        """
        movements: List[AssetMovement] = []
        if location is not None:
            exchange = self.exchange_manager.get(str(location))
            if not exchange:
                logger.warn(
                    f'Tried to query deposits/withdrawals from {location} which is either not an '
                    f'exchange or not an exchange the user has connected to',
                )
                return []
            movements = self._query_exchange_asset_movements(
                from_ts=from_ts,
                to_ts=to_ts,
                all_movements=movements,
                exchange=exchange,
            )
        else:
            for _, exchange in self.exchange_manager.connected_exchanges.items():
                movements = self._query_exchange_asset_movements(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    all_movements=movements,
                    exchange=exchange,
                )

        # return movements with most recent first
        movements.sort(key=lambda x: x.timestamp, reverse=True)
        return movements

    def set_settings(self, settings: ModifiableDBSettings) -> Tuple[bool, str]:
        """Tries to set new settings. Returns True in success or False with message if error"""
        with self.lock:
            if settings.eth_rpc_endpoint is not None:
                result, msg = self.chain_manager.set_eth_rpc_endpoint(settings.eth_rpc_endpoint)
                if not result:
                    return False, msg

            if settings.kraken_account_type is not None:
                kraken = self.exchange_manager.get('kraken')
                if kraken:
                    kraken.set_account_type(settings.kraken_account_type)  # type: ignore

            self.data.db.set_settings(settings)
            return True, ''

    def get_settings(self) -> DBSettings:
        """Returns the db settings with a check whether premium is active or not"""
        db_settings = self.data.db.get_settings(have_premium=self.premium is not None)
        return db_settings

    def setup_exchange(
            self,
            name: str,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Setup a new exchange with an api key and an api secret and optionally a passphrase

        By default the api keys are always validated unless validate is False.
        """
        is_success, msg = self.exchange_manager.setup_exchange(
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            database=self.data.db,
            passphrase=passphrase,
        )

        if is_success:
            # Success, save the result in the DB
            self.data.db.add_exchange(name, api_key, api_secret, passphrase=passphrase)
        return is_success, msg

    def remove_exchange(self, name: str) -> Tuple[bool, str]:
        if not self.exchange_manager.has_exchange(name):
            return False, 'Exchange {} is not registered'.format(name)

        self.exchange_manager.delete_exchange(name)
        # Success, remove it also from the DB
        self.data.db.remove_exchange(name)
        self.data.db.delete_used_query_range_for_exchange(name)
        return True, ''

    def query_periodic_data(self) -> Dict[str, Union[bool, Timestamp]]:
        """Query for frequently changing data"""
        result: Dict[str, Union[bool, Timestamp]] = {}

        if self.user_is_logged_in:
            result['last_balance_save'] = self.data.db.get_last_balance_save_time()
            result['eth_node_connection'] = self.chain_manager.ethereum.web3_mapping.get(NodeName.OWN, None) is not None  # noqa : E501
            result['history_process_start_ts'] = self.accountant.started_processing_timestamp
            result['history_process_current_ts'] = self.accountant.currently_processing_timestamp
            result['last_data_upload_ts'] = Timestamp(self.premium_sync_manager.last_data_upload_ts)  # noqa : E501
        return result

    def shutdown(self) -> None:
        self.logout()
        self.shutdown_event.set()
