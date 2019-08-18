#!/usr/bin/env python

import logging
import time
from typing import Any, Dict, List, Tuple, Union

import gevent
from gevent.lock import Semaphore

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.blockchain import Blockchain
from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.constants.assets import A_USD, S_USD
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.errors import (
    AuthenticationError,
    DeserializationError,
    EthSyncError,
    InputError,
    UnknownAsset,
)
from rotkehlchen.ethchain import Ethchain
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian, TradesHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import DEFAULT_ANONYMIZED_LOGS, LoggingSettings, RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import premium_create_and_verify
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.serializer import process_result
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    BlockchainAddress,
    ResultCache,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    combine_stat_dicts,
    dict_get_sumof,
    merge_dicts,
    simple_result,
    ts_now,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 60


def accounts_result(per_account, totals) -> Dict:
    result = {
        'result': True,
        'message': '',
        'per_account': per_account,
        'totals': totals,
    }
    return process_result(result)


class Rotkehlchen():
    def __init__(self, args):
        # --cache related variable start
        self.lock = Semaphore()
        self.lock.acquire()
        self.results_cache: ResultCache = dict()
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS
        # --cache related variable end

        self.premium = None
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
            raise ValueError('Should never get here. Illegal log value')

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
            sync_approval: bool,
            api_key: ApiKey,
            api_secret: ApiSecret,
    ) -> None:
        """Unlocks an existing user or creates a new one if `create_new` is True"""
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
        )
        # unlock or create the DB
        self.password = password
        self.user_directory = self.data.unlock(user, password, create_new)
        self.last_data_upload_ts = self.data.db.get_last_data_upload_ts()
        self.premium_sync_manager = PremiumSyncManager(data=self.data, password=password)
        try:
            self.premium = self.premium_sync_manager.try_premium_at_start(
                api_key=api_key,
                api_secret=api_secret,
                username=user,
                create_new=create_new,
                sync_approval=sync_approval,
            )
        except AuthenticationError:
            # It means that our credentials were not accepted by the server
            # or some other error happened
            pass

        settings = self.data.db.get_settings()
        historical_data_start = settings['historical_data_start']
        eth_rpc_endpoint = settings['eth_rpc_endpoint']
        self.trades_historian = TradesHistorian(
            user_directory=self.user_directory,
            db=self.data.db,
            eth_accounts=self.data.get_eth_accounts(),
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
        )
        # Initialize the price historian singleton
        PriceHistorian(
            data_directory=self.data_dir,
            history_date_start=historical_data_start,
            cryptocompare=Cryptocompare(data_directory=self.data_dir),
        )
        db_settings = self.data.db.get_settings()
        self.accountant = Accountant(
            profit_currency=self.data.main_currency(),
            user_directory=self.user_directory,
            msg_aggregator=self.msg_aggregator,
            create_csv=True,
            ignored_assets=self.data.db.get_ignored_assets(),
            include_crypto2crypto=db_settings['include_crypto2crypto'],
            taxfree_after_period=db_settings['taxfree_after_period'],
            include_gas_costs=db_settings['include_gas_costs'],
        )

        # Initialize the rotkehlchen logger
        LoggingSettings(anonymized_logs=db_settings['anonymized_logs'])
        exchange_credentials = self.data.db.get_exchange_credentials()
        self.exchange_manager.initialize_exchanges(
            exchange_credentials=exchange_credentials,
            user_directory=self.user_directory,
        )

        ethchain = Ethchain(eth_rpc_endpoint)
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

        if self.premium is not None:
            del self.premium
        self.data.logout()
        self.password = ''

        self.user_is_logged_in = False
        log.info(
            'User successfully logged out',
            user=user,
        )

    def set_premium_credentials(self, api_key: ApiKey, api_secret: ApiSecret) -> None:
        """
        Raises IncorrectApiKeyFormat if the given key is not in a proper format
        Raises AuthenticationError if the given key is rejected by the Rotkehlchen server
        """
        log.info('Setting new premium credentials')

        if self.premium is not None:
            self.premium.set_credentials(api_key, api_secret)
        else:
            self.premium = premium_create_and_verify(api_key, api_secret)

        self.data.set_premium_credentials(api_key, api_secret)

    def start(self):
        return gevent.spawn(self.main_loop)

    def main_loop(self):
        while self.shutdown_event.wait(MAIN_LOOP_SECS_DELAY) is not True:
            log.debug('Main loop start')
            poloniex = self.exchange_manager.connected_exchanges.get('poloniex', None)
            if poloniex:
                poloniex.main_logic()

            self.premium_sync_manager.maybe_upload_data_to_server()

            log.debug('Main loop end')

    def add_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> Dict:
        try:
            new_data = self.blockchain.add_blockchain_account(blockchain, account)
        except (InputError, EthSyncError) as e:
            return simple_result(False, str(e))
        self.data.add_blockchain_account(blockchain, account)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def remove_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ):
        try:
            new_data = self.blockchain.remove_blockchain_account(blockchain, account)
        except (InputError, EthSyncError) as e:
            return simple_result(False, str(e))
        self.data.remove_blockchain_account(blockchain, account)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def add_owned_eth_tokens(self, tokens: List[str]):
        ethereum_tokens = [
            EthereumToken(identifier=identifier) for identifier in tokens
        ]
        try:
            new_data = self.blockchain.track_new_tokens(ethereum_tokens)
        except (InputError, EthSyncError) as e:
            return simple_result(False, str(e))

        self.data.write_owned_eth_tokens(self.blockchain.owned_eth_tokens)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def remove_owned_eth_tokens(self, tokens: List[str]):
        ethereum_tokens = [
            EthereumToken(identifier=identifier) for identifier in tokens
        ]
        try:
            new_data = self.blockchain.remove_eth_tokens(ethereum_tokens)
        except InputError as e:
            return simple_result(False, str(e))
        self.data.write_owned_eth_tokens(self.blockchain.owned_eth_tokens)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def process_history(self, start_ts, end_ts):
        (
            error_or_empty,
            history,
            loan_history,
            asset_movements,
            eth_transactions,
        ) = self.trades_historian.get_history(
            start_ts=0,  # For entire history processing we need to have full history available
            end_ts=ts_now(),
            end_at_least_ts=end_ts,
        )
        result = self.accountant.process_history(
            start_ts,
            end_ts,
            history,
            loan_history,
            asset_movements,
            eth_transactions,
        )
        return result, error_or_empty

    def query_fiat_balances(self) -> Dict[Asset, Dict[str, FVal]]:
        result = {}
        balances = self.data.get_fiat_balances()
        for currency, amount in balances.items():
            amount = FVal(amount)
            usd_rate = Inquirer().query_fiat_pair(currency, A_USD)
            result[currency] = {
                'amount': amount,
                'usd_value': amount * usd_rate,
            }

        return result

    def query_balances(
            self,
            requested_save_data: bool = False,
            timestamp: Timestamp = None,
    ) -> Dict[str, Any]:
        """Query all balances rotkehlchen can see.

        If requested_save_data is True then the data are saved in the DB.
        If timestamp is None then the current timestamp is used.
        If a timestamp is given then that is the time that the balances are going
        to be saved in the DB

        Returns a dictionary with the queried balances.
        """
        log.info('query_balances called', requested_save_data=requested_save_data)

        balances = {}
        problem_free = True
        for _, exchange in self.exchange_manager.connected_exchanges.items():
            exchange_balances, _ = exchange.query_balances()
            # If we got an error, disregard that exchange but make sure we don't save data
            if not isinstance(exchange_balances, dict):
                problem_free = False
            else:
                balances[exchange.name] = exchange_balances

        result, error_or_empty = self.blockchain.query_balances()
        if error_or_empty == '':
            balances['blockchain'] = result['totals']
        else:
            problem_free = False

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
            details = self.data.accountant.details
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

    def set_main_currency(self, currency: str):
        with self.lock:
            self.data.set_main_currency(currency, self.accountant)
            if currency != S_USD:
                self.usd_to_main_currency_rate = Inquirer().query_fiat_pair(A_USD, Asset(currency))

    def set_settings(self, settings):
        log.info('Add new settings')

        message = ''
        with self.lock:
            if 'eth_rpc_endpoint' in settings:
                result, msg = self.blockchain.set_eth_rpc_endpoint(settings['eth_rpc_endpoint'])
                if not result:
                    # Don't save it in the DB
                    del settings['eth_rpc_endpoint']
                    message += "\nEthereum RPC endpoint not set: " + msg

            if 'main_currency' in settings:
                given_symbol = settings['main_currency']
                try:
                    main_currency = Asset(given_symbol)
                except UnknownAsset:
                    return False, f'Unknown fiat currency {given_symbol} provided'
                except DeserializationError:
                    return False, 'Non string type given for fiat currency'

                if not main_currency.is_fiat():
                    msg = (
                        f'Provided symbol for main currency {given_symbol} is '
                        f'not a fiat currency'
                    )
                    return False, msg

                if main_currency != A_USD:
                    self.usd_to_main_currency_rate = Inquirer().query_fiat_pair(
                        A_USD,
                        main_currency,
                    )

            res, msg = self.accountant.customize(settings)
            if not res:
                message += '\n' + msg
                return False, message

            _, msg, = self.data.set_settings(settings, self.accountant)
            if msg != '':
                message += '\n' + msg

            # Always return success here but with a message
            return True, message

    def setup_exchange(
            self,
            name: str,
            api_key: str,
            api_secret: str,
    ) -> Tuple[bool, str]:
        """
        Setup a new exchange with an api key and an api secret

        By default the api keys are always validated unless validate is False.
        """
        is_success, msg = self.exchange_manager.setup_exchange(
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            user_directory=self.user_directory,
        )

        if is_success:
            # Success, save the result in the DB
            self.data.db.add_exchange(name, api_key, api_secret)
        return is_success, msg

    def remove_exchange(self, name: str) -> Tuple[bool, str]:
        if not self.exchange_manager.has_exchange(name):
            return False, 'Exchange {} is not registered'.format(name)

        self.exchange_manager.delete_exchange(name)
        # Success, remove it also from the DB
        self.data.db.remove_exchange(name)
        return True, ''

    def query_periodic_data(self) -> Dict[str, Union[bool, Timestamp]]:
        """Query for frequently changing data"""
        result = {}

        if self.user_is_logged_in:
            result['last_balance_save'] = self.data.db.get_last_balance_save_time()
            result['eth_node_connection'] = self.blockchain.ethchain.connected
            result['history_process_start_ts'] = self.accountant.started_processing_timestamp
            result['history_process_current_ts'] = self.accountant.currently_processing_timestamp
        return result

    def shutdown(self):
        self.logout()
        self.shutdown_event.set()
