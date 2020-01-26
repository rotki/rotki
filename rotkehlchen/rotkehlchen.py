#!/usr/bin/env python

import argparse
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import gevent
from gevent.lock import Semaphore

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.blockchain import Blockchain, BlockchainBalancesUpdate
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data.importer import DataImporter
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors import EthSyncError, PremiumAuthenticationError, RemoteError
from rotkehlchen.ethchain import Ethchain
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian, TradesHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import DEFAULT_ANONYMIZED_LOGS, LoggingSettings, RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, PremiumCredentials, premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.typing import ApiKey, ApiSecret, BlockchainAddress, SupportedBlockchain, Timestamp
from rotkehlchen.usage_analytics import maybe_submit_usage_analytics
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import combine_stat_dicts, dict_get_sumof, merge_dicts, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 60


class Rotkehlchen():
    def __init__(self, args: argparse.Namespace) -> None:
        self.lock = Semaphore()
        self.lock.acquire()

        # Can also be None after unlock if premium credentials did not
        # authenticate or premium server temporarily offline
        self.premium: Optional[Premium] = None
        self.user_is_logged_in = False

        logfilename = None
        if args.logtarget == 'file':
            logfilename = args.logfile

        if args.loglevel == 'debug':
            loglevel = logging.DEBUG
        elif args.loglevel == 'info':
            loglevel = logging.INFO
        elif args.loglevel == 'warn':
            loglevel = logging.WARN
        elif args.loglevel == 'error':
            loglevel = logging.ERROR
        elif args.loglevel == 'critical':
            loglevel = logging.CRITICAL
        else:
            raise AssertionError('Should never get here. Illegal log value')

        logging.basicConfig(
            filename=logfilename,
            filemode='w',
            level=loglevel,
            format='%(asctime)s -- %(levelname)s:%(name)s:%(message)s',
            datefmt='%d/%m/%Y %H:%M:%S %Z',
        )

        if not args.logfromothermodules:
            logging.getLogger('zerorpc').setLevel(logging.CRITICAL)
            logging.getLogger('zerorpc.channel').setLevel(logging.CRITICAL)
            logging.getLogger('urllib3').setLevel(logging.CRITICAL)
            logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

        self.sleep_secs = args.sleep_secs
        self.data_dir = args.data_dir
        self.args = args
        self.msg_aggregator = MessagesAggregator()
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        self.data = DataHandler(self.data_dir, self.msg_aggregator)
        # Initialize the Inquirer singleton
        Inquirer(data_dir=self.data_dir)

        self.lock.release()
        self.shutdown_event = gevent.event.Event()

    def unlock_user(
            self,
            user: str,
            password: str,
            create_new: bool,
            sync_approval: str,
            premium_credentials: Optional[PremiumCredentials],
    ) -> None:
        """Unlocks an existing user or creates a new one if `create_new` is True

        Can raise PremiumAuthenticationError if the password can't unlock the database.
        Can raise AuthenticationError if premium_credentials are given and are invalid
        or can't authenticate with the server
        """
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
        )
        # unlock or create the DB
        self.password = password
        self.user_directory = self.data.unlock(user, password, create_new)
        self.data_importer = DataImporter(db=self.data.db)
        self.last_data_upload_ts = self.data.db.get_last_data_upload_ts()
        self.premium_sync_manager = PremiumSyncManager(data=self.data, password=password)

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
            # else let's just continue. User signed in succesfully, but he just
            # has unauthenticable/invalid premium credentials remaining in his DB

        settings = self.data.db.get_settings()
        maybe_submit_usage_analytics(settings.submit_usage_analytics)
        self.etherscan = Etherscan(database=self.data.db, msg_aggregator=self.msg_aggregator)
        historical_data_start = settings.historical_data_start
        eth_rpc_endpoint = settings.eth_rpc_endpoint
        self.trades_historian = TradesHistorian(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            etherscan=self.etherscan,
        )
        # Initialize the price historian singleton
        self.cryptocompare = Cryptocompare(data_directory=self.data_dir, database=self.data.db)
        PriceHistorian(
            data_directory=self.data_dir,
            history_date_start=historical_data_start,
            cryptocompare=self.cryptocompare,
        )
        db_settings = self.data.db.get_settings()
        self.accountant = Accountant(
            db=self.data.db,
            user_directory=self.user_directory,
            msg_aggregator=self.msg_aggregator,
            create_csv=True,
        )

        # Initialize the rotkehlchen logger
        LoggingSettings(anonymized_logs=db_settings.anonymized_logs)
        exchange_credentials = self.data.db.get_exchange_credentials()
        self.exchange_manager.initialize_exchanges(
            exchange_credentials=exchange_credentials,
            database=self.data.db,
        )

        # Initialize blockchain querying modules
        ethchain = Ethchain(
            ethrpc_endpoint=eth_rpc_endpoint,
            etherscan=self.etherscan,
        )
        self.blockchain = Blockchain(
            blockchain_accounts=self.data.db.get_blockchain_accounts(),
            owned_eth_tokens=self.data.db.get_owned_tokens(),
            ethchain=ethchain,
            msg_aggregator=self.msg_aggregator,
        )
        self.user_is_logged_in = True

    def logout(self) -> None:
        if not self.user_is_logged_in:
            return

        user = self.data.username
        log.info(
            'Logging out user',
            user=user,
        )
        del self.blockchain
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

    def start(self) -> gevent.Greenlet:
        return gevent.spawn(self.main_loop)

    def main_loop(self) -> None:
        while self.shutdown_event.wait(MAIN_LOOP_SECS_DELAY) is not True:
            if self.user_is_logged_in:
                log.debug('Main loop start')
                self.premium_sync_manager.maybe_upload_data_to_server()
                log.debug('Main loop end')

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Tuple[Optional[BlockchainBalancesUpdate], str]:
        """Adds new blockchain accounts

        Adds the accounts to the blockchain instance and queries them to get the
        updated balances. Also adds the ones that were valid in the DB

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """

        new_data, added_accounts, msg = self.blockchain.add_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )
        for account in added_accounts:
            self.data.db.add_blockchain_account(blockchain, account)

        return new_data, msg

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Tuple[Optional[BlockchainBalancesUpdate], str]:
        """Removes blockchain accounts

        Removes the accounts from the blockchain instance and queries them to get
        the updated balances. Also removes the ones that were valid from the DB

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        new_data, removed_accounts, msg = self.blockchain.remove_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )
        for account in removed_accounts:
            self.data.db.remove_blockchain_account(blockchain, account)

        return new_data, msg

    def add_owned_eth_tokens(
            self,
            tokens: List[EthereumToken],
    ) -> BlockchainBalancesUpdate:
        """Adds tokens to the blockchain state and updates balance of all accounts

        May raise:
        - InputError if some of the tokens already exist
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
          client and the chain is not synced
        """
        new_data = self.blockchain.track_new_tokens(tokens)
        self.data.write_owned_eth_tokens(self.blockchain.owned_eth_tokens)
        return new_data

    def remove_owned_eth_tokens(
            self,
            tokens: List[EthereumToken],
    ) -> BlockchainBalancesUpdate:
        """
        Removes tokens from the state and stops their balance from being tracked
        for each account

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
          client and the chain is not synced
        """
        new_data = self.blockchain.remove_eth_tokens(tokens)
        self.data.write_owned_eth_tokens(self.blockchain.owned_eth_tokens)
        return new_data

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
        ) = self.trades_historian.get_history(
            # For entire history processing we need to have full history available
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )
        result = self.accountant.process_history(
            start_ts=start_ts,
            end_ts=end_ts,
            trade_history=history,
            loan_history=loan_history,
            asset_movements=asset_movements,
            eth_transactions=eth_transactions,
        )
        return result, error_or_empty

    def query_fiat_balances(self) -> Dict[Asset, Dict[str, FVal]]:
        result = {}
        balances = self.data.get_fiat_balances()
        for currency, str_amount in balances.items():
            amount = FVal(str_amount)
            usd_rate = Inquirer().query_fiat_pair(currency, A_USD)
            result[currency] = {
                'amount': amount,
                'usd_value': amount * usd_rate,
            }

        return result

    def query_balances(
            self,
            requested_save_data: bool = True,
            timestamp: Timestamp = None,
            ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """Query all balances rotkehlchen can see.

        If requested_save_data is True then the data are saved in the DB.
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
            blockchain_result = self.blockchain.query_balances(
                blockchain=None,
                ignore_cache=ignore_cache,
            )
        except (RemoteError, EthSyncError) as e:
            problem_free = False
            log.error(f'Querying blockchain balances failed due to: {str(e)}')

        balances['blockchain'] = blockchain_result['totals']

        result = self.query_fiat_balances()
        if result != {}:
            balances['banks'] = result

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

        allowed_to_save = requested_save_data and self.data.should_save_balances()
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

    def set_settings(self, settings: ModifiableDBSettings) -> Tuple[bool, str]:
        """Tries to set new settings. Returns True in success or False with message if error"""
        with self.lock:
            if settings.eth_rpc_endpoint is not None:
                result, msg = self.blockchain.set_eth_rpc_endpoint(settings.eth_rpc_endpoint)
                if not result:
                    return False, msg

            self.data.db.set_settings(settings)
            return True, ''

    def setup_exchange(
            self,
            name: str,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Setup a new exchange with an api key and an api secret

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
            result['eth_node_connection'] = self.blockchain.ethchain.connected
            result['history_process_start_ts'] = self.accountant.started_processing_timestamp
            result['history_process_current_ts'] = self.accountant.currently_processing_timestamp
        return result

    def shutdown(self) -> None:
        self.logout()
        self.shutdown_event.set()
