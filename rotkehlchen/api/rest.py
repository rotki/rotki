import datetime
import hashlib
import json
import logging
import os
import sys
import tempfile
import traceback
from collections import defaultdict
from http import HTTPStatus
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Literal,
    Optional,
    Union,
    get_args,
    overload,
)
from uuid import uuid4
from zipfile import ZipFile

import gevent
from flask import Response, make_response, send_file
from gevent.event import Event
from gevent.lock import Semaphore
from marshmallow.exceptions import ValidationError
from pysqlcipher3 import dbapi2 as sqlcipher
from web3.exceptions import BadFunctionCallOutput
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry, StakingEvent
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.api.v1.schemas import TradeSchema
from rotkehlchen.api.v1.types import (
    EvmPendingTransactionDecodingApiData,
    EvmTransactionDecodingApiData,
)
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
    FiatAsset,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
    get_manually_tracked_balances,
    remove_manually_tracked_balances,
)
from rotkehlchen.chain.accounts import SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.airdrops import check_airdrops
from rotkehlchen.chain.ethereum.modules.eth2.constants import FREE_VALIDATORS_LIMIT
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.chain.evm.names import find_ens_mappings, search_for_addresses_names
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.limits import (
    FREE_ASSET_MOVEMENTS_LIMIT,
    FREE_ETH_TX_LIMIT,
    FREE_HISTORY_EVENTS_LIMIT,
    FREE_LEDGER_ACTIONS_LIMIT,
    FREE_TRADES_LIMIT,
    FREE_USER_NOTES_LIMIT,
)
from rotkehlchen.constants.misc import (
    ASSET_TYPES_EXCLUDED_FOR_USERS,
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    HTTP_STATUS_INTERNAL_DB_ERROR,
    ONE,
    ZERO,
)
from rotkehlchen.constants.resolver import ChainID, evm_address_to_identifier
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_CHAINID,
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    Eth2DailyStatsFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
    LedgerActionsFilterQuery,
    LevenshteinFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.snapshots import DBSnapshot
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.api import (
    AuthenticationError,
    IncorrectApiKeyFormat,
    PremiumApiError,
    PremiumAuthenticationError,
    PremiumPermissionError,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import (
    DBSchemaError,
    DBUpgradeError,
    EthSyncError,
    InputError,
    ModuleInactive,
    RemoteError,
    SystemPermissionError,
    TagConstraintError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.utils import query_binance_exchange_pairs
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.assets_management import export_assets_from_file, import_assets_from_file
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.updates import ASSETS_VERSION_KEY
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import NOT_EXPOSED_SOURCES, HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle, Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS,
    SUPPORTED_SUBSTRATE_CHAINS,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    AssetAmount,
    BTCAddress,
    ChecksumEvmAddress,
    Eth2PubKey,
    EvmTokenKind,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    ModuleName,
    OptionalChainAddress,
    Price,
    SubstrateAddress,
    SupportedBlockchain,
    Timestamp,
    TradeType,
    UserNote,
)
from rotkehlchen.utils.misc import combine_dicts
from rotkehlchen.utils.snapshots import parse_import_snapshot_data
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.exchanges.kraken import KrakenAccountType


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

OK_RESULT = {'result': True, 'message': ''}


def _wrap_in_ok_result(result: Any) -> dict[str, Any]:
    return {'result': result, 'message': ''}


def _wrap_in_result(result: Any, message: str) -> dict[str, Any]:
    return {'result': result, 'message': message}


def _get_status_code_from_async_response(response: dict[str, Any], default: HTTPStatus = HTTPStatus.OK) -> HTTPStatus:  # noqa: E501
    return response.get('status_code', default)


def wrap_in_fail_result(message: str, status_code: Optional[HTTPStatus] = None) -> dict[str, Any]:
    result: dict[str, Any] = {'result': None, 'message': message}
    if status_code:
        result['status_code'] = status_code

    return result


def api_response(
        result: dict[str, Any],
        status_code: HTTPStatus = HTTPStatus.OK,
        log_result: bool = True,
) -> Response:
    if status_code == HTTPStatus.NO_CONTENT:
        assert not result, 'Provided 204 response with non-zero length response'
        data = ''
    else:
        data = json.dumps(result)

    response = make_response(
        (
            data,
            status_code,
            {
                'mimetype': 'application/json',
                'Content-Type': 'application/json',
                'rotki-log-result': log_result,  # popped by after request callback
            }),
    )
    return response


class RestAPI():
    """ The Object holding the logic that runs inside all the API calls"""
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self._handle_killed_greenlets)
        # Greenlets that will be waited for when we shutdown (just main loop)
        self.waited_greenlets = [mainloop_greenlet]
        self.task_lock = Semaphore()
        self.task_id = 0
        self.task_results: dict[int, Any] = {}
        self.trade_schema = TradeSchema()
        self.import_tmp_files: DefaultDict[FileStorage, Path] = defaultdict()

    # - Private functions not exposed to the API
    def _new_task_id(self) -> int:
        with self.task_lock:
            task_id = self.task_id
            self.task_id += 1
        return task_id

    def _write_task_result(self, task_id: int, result: Any) -> None:
        with self.task_lock:
            self.task_results[task_id] = result

    def _handle_killed_greenlets(self, greenlet: gevent.Greenlet) -> None:
        if not greenlet.exception:
            log.warning('handle_killed_greenlets without an exception')
            return

        try:
            task_id = greenlet.task_id
            task_str = f'Greenlet for task {task_id}'
        except AttributeError:
            task_id = None
            task_str = 'Main greenlet'

        log.error(
            '{} dies with exception: {}.\n'
            'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
            .format(
                task_str,
                greenlet.exception,
                greenlet.exc_info[0],
                greenlet.exc_info[1],
                ''.join(traceback.format_tb(greenlet.exc_info[2])),
            ))
        # also write an error for the task result if it's not the main greenlet
        if task_id is not None:
            result = {
                'result': None,
                'message': f'The backend query task died unexpectedly: {str(greenlet.exception)}',
            }
            self._write_task_result(task_id, result)

    def _do_query_async(self, command: Callable, task_id: int, **kwargs: Any) -> None:
        log.debug(f'Async task with task id {task_id} started')
        result = command(**kwargs)
        self._write_task_result(task_id, result)

    def _query_async(self, command: Callable, **kwargs: Any) -> Response:
        task_id = self._new_task_id()
        greenlet = gevent.spawn(
            self._do_query_async,
            command,
            task_id,
            **kwargs,
        )
        greenlet.task_id = task_id
        greenlet.link_exception(self._handle_killed_greenlets)
        self.rotkehlchen.api_task_greenlets.append(greenlet)
        return api_response(_wrap_in_ok_result({'task_id': task_id}), status_code=HTTPStatus.OK)

    # - Public functions not exposed via the rest api
    def stop(self) -> None:
        self.rotkehlchen.shutdown()
        log.debug('Waiting for greenlets')
        gevent.wait(self.waited_greenlets)
        log.debug('Waited for greenlets. Killing all other greenlets')
        gevent.killall(self.rotkehlchen.api_task_greenlets)
        log.debug('Shutdown completed')
        logging.shutdown()
        self.stop_event.set()

    # - Public functions exposed via the rest api
    def set_settings(self, settings: ModifiableDBSettings) -> Response:
        success, message = self.rotkehlchen.set_settings(settings)
        if not success:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            new_settings = process_result(self.rotkehlchen.get_settings(cursor))
        result_dict = {'result': new_settings, 'message': ''}
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    def get_settings(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result_dict = _wrap_in_ok_result(process_result(self.rotkehlchen.get_settings(cursor)))
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    def query_tasks_outcome(self, task_id: Optional[int]) -> Response:
        if task_id is None:
            # If no task id is given return list of all pending and completed tasks
            completed = []
            pending = []
            for greenlet in self.rotkehlchen.api_task_greenlets:
                task_id = greenlet.task_id
                if task_id in self.task_results:
                    completed.append(task_id)
                else:
                    pending.append(task_id)

            result = _wrap_in_ok_result({'pending': pending, 'completed': completed})
            return api_response(result=result, status_code=HTTPStatus.OK)

        with self.task_lock:
            for idx, greenlet in enumerate(self.rotkehlchen.api_task_greenlets):
                if greenlet.task_id == task_id:
                    if task_id in self.task_results:
                        # Task has completed and we just got the outcome
                        function_response = self.task_results.pop(int(task_id), None)
                        # The result of the original request
                        result = function_response['result']
                        # The message of the original request
                        message = function_response['message']
                        status_code = function_response.get('status_code')
                        ret = {'result': result, 'message': message}
                        returned_task_result = {
                            'status': 'completed',
                            'outcome': process_result(ret),
                        }
                        if status_code:
                            returned_task_result['status_code'] = status_code
                        result_dict = {
                            'result': returned_task_result,
                            'message': '',
                        }
                        # Also remove the greenlet from the api tasks
                        self.rotkehlchen.api_task_greenlets.pop(idx)
                        return api_response(result=result_dict, status_code=HTTPStatus.OK)
                    # else task is still pending and the greenlet is running
                    result_dict = {
                        'result': {'status': 'pending', 'outcome': None},
                        'message': f'The task with id {task_id} is still pending',
                    }
                    return api_response(result=result_dict, status_code=HTTPStatus.OK)

        # The task has not been found
        result_dict = {
            'result': {'status': 'not-found', 'outcome': None},
            'message': f'No task with id {task_id} found',
        }
        return api_response(result=result_dict, status_code=HTTPStatus.NOT_FOUND)

    def _get_exchange_rates(self, given_currencies: list[AssetWithOracles]) -> dict[str, Any]:
        currencies = given_currencies
        fiat_currencies: list[FiatAsset] = []
        asset_rates = {}
        for asset in currencies:
            if asset.is_fiat():
                fiat_currencies.append(asset.resolve_to_fiat_asset())
                continue

            usd_price = Inquirer().find_usd_price(asset)
            if usd_price == Price(ZERO):
                asset_rates[asset] = Price(ZERO)
            else:
                asset_rates[asset] = Price(ONE / usd_price)

        fiat_rates = Inquirer().get_fiat_usd_exchange_rates(fiat_currencies)
        for fiat, rate in fiat_rates.items():
            asset_rates[fiat] = rate

        return _wrap_in_ok_result(process_result(asset_rates))

    def get_exchange_rates(
            self,
            given_currencies: list[AssetWithOracles],
            async_query: bool,
    ) -> Response:
        if len(given_currencies) == 0:
            return api_response(
                wrap_in_fail_result('Empty list of currencies provided'),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        if async_query is True:
            return self._query_async(
                command=self._get_exchange_rates,
                given_currencies=given_currencies,
            )

        response_result = self._get_exchange_rates(given_currencies)
        return api_response(result=response_result, status_code=HTTPStatus.OK)

    def _query_all_balances(
            self,
            save_data: bool,
            ignore_errors: bool,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        result = self.rotkehlchen.query_balances(
            requested_save_data=save_data,
            save_despite_errors=ignore_errors,
            ignore_cache=ignore_cache,
        )
        return {'result': result, 'message': ''}

    def query_all_balances(
            self,
            save_data: bool,
            ignore_errors: bool,
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._query_all_balances,
                save_data=save_data,
                ignore_errors=ignore_errors,
                ignore_cache=ignore_cache,
            )

        response = self._query_all_balances(
            save_data=save_data,
            ignore_errors=ignore_errors,
            ignore_cache=ignore_cache,
        )
        return api_response(
            _wrap_in_result(process_result(response['result']), response['message']),
            HTTPStatus.OK,
        )

    def _return_external_services_response(self) -> Response:
        credentials_list = self.rotkehlchen.data.db.get_all_external_service_credentials()
        response_dict = {}
        for credential in credentials_list:
            name = credential.service.name.lower()
            response_dict[name] = {'api_key': credential.api_key}

        return api_response(_wrap_in_ok_result(response_dict), status_code=HTTPStatus.OK)

    def get_external_services(self) -> Response:
        return self._return_external_services_response()

    def add_external_services(self, services: list[ExternalServiceApiCredentials]) -> Response:
        self.rotkehlchen.data.db.add_external_service_credentials(services)
        return self._return_external_services_response()

    def delete_external_services(self, services: list[ExternalService]) -> Response:
        self.rotkehlchen.data.db.delete_external_service_credentials(services)
        return self._return_external_services_response()

    def get_exchanges(self) -> Response:
        return api_response(
            _wrap_in_ok_result(self.rotkehlchen.exchange_manager.get_connected_exchanges_info()),
            status_code=HTTPStatus.OK,
        )

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: Optional[list[str]],
            ftx_subaccount: Optional[str],
    ) -> Response:
        result = None
        status_code = HTTPStatus.OK
        msg = ''
        result, msg = self.rotkehlchen.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            binance_selected_trade_pairs=binance_markets,
            ftx_subaccount=ftx_subaccount,
        )
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT

        return api_response(_wrap_in_result(result, msg), status_code=status_code)

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: Optional[list[str]],
            ftx_subaccount: Optional[str],
    ) -> Response:
        result: Optional[bool] = True
        status_code = HTTPStatus.OK
        msg = ''
        try:
            edited, msg = self.rotkehlchen.exchange_manager.edit_exchange(
                name=name,
                location=location,
                new_name=new_name,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type,
                binance_selected_trade_pairs=binance_markets,
                ftx_subaccount=ftx_subaccount,
            )
        except InputError as e:
            edited = False
            msg = str(e)

        if not edited:
            result = None
            status_code = HTTPStatus.CONFLICT

        return api_response(_wrap_in_result(result, msg), status_code=status_code)

    def remove_exchange(self, name: str, location: Location) -> Response:
        result: Optional[bool]
        result, message = self.rotkehlchen.remove_exchange(name=name, location=location)
        status_code = HTTPStatus.OK
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    def _query_all_exchange_balances(self, ignore_cache: bool) -> dict[str, Any]:
        final_balances = {}
        error_msg = ''
        for exchange_obj in self.rotkehlchen.exchange_manager.iterate_exchanges():
            balances, msg = exchange_obj.query_balances(ignore_cache=ignore_cache)
            if balances is None:
                error_msg += msg
            else:
                location_str = str(exchange_obj.location)
                if location_str not in final_balances:
                    final_balances[location_str] = balances
                else:  # multiple exchange of same type. Combine balances
                    final_balances[location_str] = combine_dicts(
                        final_balances[location_str],
                        balances,
                    )

        if final_balances == {}:
            result = None
            status_code = HTTPStatus.CONFLICT
        else:
            result = final_balances
            status_code = HTTPStatus.OK

        return {'result': result, 'message': error_msg, 'status_code': status_code}

    def _query_exchange_balances(self, location: Optional[Location], ignore_cache: bool) -> dict[str, Any]:  # noqa: E501
        if location is None:
            # Query all exchanges
            return self._query_all_exchange_balances(ignore_cache=ignore_cache)

        # else query only the specific exchange
        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return {
                'result': None,
                'message': f'Could not query balances for {str(location)} since it is not registered',  # noqa: E501
                'status_code': HTTPStatus.CONFLICT,
            }

        balances: dict[AssetWithOracles, Balance] = {}
        for exchange in exchanges_list:
            result, msg = exchange.query_balances(ignore_cache=ignore_cache)
            if result is None:
                return {
                    'result': result,
                    'message': msg,
                    'status_code': HTTPStatus.CONFLICT,
                }
            balances = combine_dicts(balances, result)

        return {
            'result': balances,
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def query_exchange_balances(
            self,
            location: Optional[Location],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._query_exchange_balances,
                location=location,
                ignore_cache=ignore_cache,
            )

        response = self._query_exchange_balances(location=location, ignore_cache=ignore_cache)
        balances = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if balances is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        return api_response(_wrap_in_ok_result(process_result(balances)), HTTPStatus.OK)

    def get_supported_chains(self) -> Response:
        result = []
        for blockchain in SupportedBlockchain:
            data = {
                'id': blockchain.value,
                'name': str(blockchain),
                'type': blockchain.get_chain_type(),
            }
            if blockchain == SupportedBlockchain.OPTIMISM:
                data['native_asset'] = A_ETH.serialize()
            if blockchain.is_evm() is True:
                data['evm_chain_name'] = blockchain.to_chain_id().to_name()
            result.append(data)

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def _query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
            ignore_cache: bool,
    ) -> dict[str, Any]:
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            balances = self.rotkehlchen.chains_aggregator.query_balances(
                blockchain=blockchain,
                ignore_cache=ignore_cache,
            )
        except EthSyncError as e:
            msg = str(e)
            status_code = HTTPStatus.CONFLICT
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY
        else:
            result = balances.serialize()

        return {'result': result, 'message': msg, 'status_code': status_code}

    def query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._query_blockchain_balances,
                blockchain=blockchain,
                ignore_cache=ignore_cache,
            )

        response = self._query_blockchain_balances(
            blockchain=blockchain,
            ignore_cache=ignore_cache,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def _get_trades(
            self,
            only_cache: bool,
            filter_query: TradesFilterQuery,
    ) -> dict[str, Any]:
        try:
            trades, filter_total_found = self.rotkehlchen.events_historian.query_trades(
                filter_query=filter_query,
                only_cache=only_cache,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        trades_result = []
        for trade in trades:
            serialized_trade = self.trade_schema.dump(trade)
            serialized_trade['trade_id'] = trade.identifier
            trades_result.append(serialized_trade)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            mapping = self.rotkehlchen.data.db.get_ignored_action_ids(cursor, ActionType.TRADE)
            ignored_ids = mapping.get(ActionType.TRADE, [])
            entries_result = []
            for entry in trades_result:
                entries_result.append(
                    {'entry': entry, 'ignored_in_accounting': entry['trade_id'] in ignored_ids},
                )

            result = {
                'entries': entries_result,
                'entries_found': filter_total_found,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(
                    cursor=cursor,
                    entries_table='trades',
                ),
                'entries_limit': FREE_TRADES_LIMIT if self.rotkehlchen.premium is None else -1,
            }

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_trades(
            self,
            async_query: bool,
            only_cache: bool,
            filter_query: TradesFilterQuery,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_trades,
                only_cache=only_cache,
                filter_query=filter_query,
            )

        response = self._get_trades(
            only_cache=only_cache,
            filter_query=filter_query,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def add_trade(
            self,
            timestamp: Timestamp,
            location: Location,
            base_asset: Asset,
            quote_asset: Asset,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Optional[Fee],
            fee_currency: Optional[Asset],
            link: Optional[str],
            notes: Optional[str],
    ) -> Response:
        trade = Trade(
            timestamp=timestamp,
            location=location,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )
        with self.rotkehlchen.data.db.user_write() as cursor:
            self.rotkehlchen.data.db.add_trades(cursor, [trade])
        # For the outside world we should also add the trade identifier
        result_dict = self.trade_schema.dump(trade)
        result_dict['trade_id'] = trade.identifier
        result_dict = _wrap_in_ok_result(result_dict)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_trade(
            self,
            trade_id: str,
            timestamp: Timestamp,
            location: Location,
            base_asset: Asset,
            quote_asset: Asset,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Optional[Fee],
            fee_currency: Optional[Asset],
            link: Optional[str],
            notes: Optional[str],
    ) -> Response:
        trade = Trade(
            timestamp=timestamp,
            location=location,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )
        with self.rotkehlchen.data.db.user_write() as cursor:
            result, msg = self.rotkehlchen.data.db.edit_trade(cursor, old_trade_id=trade_id, trade=trade)  # noqa: E501

        if not result:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        # For the outside world we should also add the trade identifier
        result_dict = self.trade_schema.dump(trade)
        result_dict['trade_id'] = trade.identifier
        result_dict = _wrap_in_ok_result(result_dict)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def delete_trades(self, trades_ids: list[str]) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.delete_trades(cursor, trades_ids)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def _get_asset_movements(
            self,
            filter_query: AssetMovementsFilterQuery,
            only_cache: bool,
    ) -> dict[str, Any]:
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            movements, filter_total_found = self.rotkehlchen.events_historian.query_asset_movements(  # noqa: E501
                filter_query=filter_query,
                only_cache=only_cache,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        serialized_movements = process_result_list([x.serialize() for x in movements])
        limit = FREE_ASSET_MOVEMENTS_LIMIT if self.rotkehlchen.premium is None else -1

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            mapping = self.rotkehlchen.data.db.get_ignored_action_ids(cursor, ActionType.ASSET_MOVEMENT)  # noqa: E501
            ignored_ids = mapping.get(ActionType.ASSET_MOVEMENT, [])
            entries_result = []
            for entry in serialized_movements:
                entries_result.append({
                    'entry': entry,
                    'ignored_in_accounting': entry['identifier'] in ignored_ids,
                })

            result = {
                'entries': entries_result,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor, 'asset_movements'),  # noqa: E501
                'entries_found': filter_total_found,
                'entries_limit': limit,
            }

        return {'result': result, 'message': msg, 'status_code': status_code}

    def get_asset_movements(
            self,
            filter_query: AssetMovementsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_asset_movements,
                filter_query=filter_query,
                only_cache=only_cache,
            )

        response = self._get_asset_movements(
            filter_query=filter_query,
            only_cache=only_cache,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        status_code = _get_status_code_from_async_response(response)
        return api_response(process_result(result_dict), status_code=status_code)

    def _get_ledger_actions(
            self,
            filter_query: LedgerActionsFilterQuery,
            only_cache: bool,
    ) -> dict[str, Any]:
        actions, filter_total_found = self.rotkehlchen.events_historian.query_ledger_actions(
            filter_query=filter_query,
            only_cache=only_cache,
        )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            mapping = self.rotkehlchen.data.db.get_ignored_action_ids(cursor, ActionType.LEDGER_ACTION)  # noqa: E501
            ignored_ids = mapping.get(ActionType.LEDGER_ACTION, [])
            entries_result = []
            for action in actions:
                entries_result.append({
                    'entry': action.serialize(),
                    'ignored_in_accounting': str(action.identifier) in ignored_ids,
                })

            result = {
                'entries': entries_result,
                'entries_found': filter_total_found,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor, 'ledger_actions'),  # noqa: E501
                'entries_limit': FREE_LEDGER_ACTIONS_LIMIT if self.rotkehlchen.premium is None else -1,  # noqa: E501
            }

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_ledger_actions(
            self,
            filter_query: LedgerActionsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_ledger_actions,
                filter_query=filter_query,
                only_cache=only_cache,
            )

        response = self._get_ledger_actions(
            filter_query=filter_query,
            only_cache=only_cache,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def add_ledger_action(self, action: LedgerAction) -> Response:
        db = DBLedgerActions(self.rotkehlchen.data.db, self.rotkehlchen.msg_aggregator)
        with self.rotkehlchen.data.db.user_write() as cursor:
            try:
                identifier = db.add_ledger_action(cursor, action)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                error_msg = 'Failed to add Ledger action due to entry already existing in the DB'
                return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)  # noqa: E501

        result_dict = _wrap_in_ok_result({'identifier': identifier})
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_ledger_action(self, action: LedgerAction) -> Response:
        db = DBLedgerActions(self.rotkehlchen.data.db, self.rotkehlchen.msg_aggregator)
        error_msg = db.edit_ledger_action(action)
        if error_msg is not None:
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        # Success - return all ledger actions after the edit
        response = self._get_ledger_actions(
            filter_query=LedgerActionsFilterQuery.make(),
            only_cache=True,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def delete_ledger_actions(self, identifiers: list[int]) -> Response:
        db = DBLedgerActions(self.rotkehlchen.data.db, self.rotkehlchen.msg_aggregator)
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                db.remove_ledger_actions(cursor, identifiers=identifiers)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def add_history_event(self, event: HistoryBaseEntry, chain_id: ChainID) -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.user_write() as cursor:
            try:
                identifier = db.add_history_event(
                    write_cursor=cursor,
                    event=event,
                    mapping_values={
                        HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED,
                        HISTORY_MAPPING_KEY_CHAINID: chain_id.serialize_for_db(),
                    },
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                error_msg = f'Failed to add event to the DB due to a DB error: {str(e)}'
                return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)  # noqa: E501

        if identifier is None:
            error_msg = 'Failed to add event to the DB. It already exists'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        # success
        result_dict = _wrap_in_ok_result({'identifier': identifier})
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_history_event(self, event: HistoryBaseEntry) -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        result, msg = db.edit_history_event(event)
        if result is False:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_history_events(self, identifiers: list[int]) -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        error_msg = db.delete_history_events_by_identifier(identifiers=identifiers)
        if error_msg is not None:
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        # Success
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_tags(self, cursor: 'DBCursor') -> Response:
        result = self.rotkehlchen.data.db.get_tags(cursor)
        response = {name: data.serialize() for name, data in result.items()}
        return api_response(_wrap_in_ok_result(response), status_code=HTTPStatus.OK)

    def get_tags(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            return self._get_tags(cursor)

    def add_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> Response:

        with self.rotkehlchen.data.db.user_write() as cursor:
            try:
                self.rotkehlchen.data.db.add_tag(
                    write_cursor=cursor,
                    name=name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
            except TagConstraintError as e:
                return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

            return self._get_tags(cursor)

    def edit_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: Optional[HexColorCode],
            foreground_color: Optional[HexColorCode],
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.edit_tag(
                    write_cursor=cursor,
                    name=name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)  # noqa: E501
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            return self._get_tags(cursor)

    def delete_tag(self, name: str) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.delete_tag(cursor, name=name)
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            return self._get_tags(cursor)

    def get_users(self) -> Response:
        result = self.rotkehlchen.data.get_users()
        result_dict = _wrap_in_ok_result(result)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def create_new_user(
            self,
            name: str,
            password: str,
            premium_api_key: str,
            premium_api_secret: str,
            sync_database: bool,
            initial_settings: Optional[ModifiableDBSettings],
    ) -> Response:
        result_dict: dict[str, Any] = {'result': None, 'message': ''}

        if self.rotkehlchen.user_is_logged_in:
            result_dict['message'] = (
                f'Can not create a new user because user '
                f'{self.rotkehlchen.data.username} is already logged in. '
                f'Log out of that user first',
            )
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        if (
                premium_api_key != '' and premium_api_secret == '' or
                premium_api_secret != '' and premium_api_key == ''
        ):
            result_dict['message'] = 'Must provide both or neither of api key/secret'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        premium_credentials = None
        if premium_api_key != '' and premium_api_secret != '':
            try:
                premium_credentials = PremiumCredentials(
                    given_api_key=premium_api_key,
                    given_api_secret=premium_api_secret,
                )
            except IncorrectApiKeyFormat:
                result_dict['message'] = 'Provided API/Key secret format is invalid'
                return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        try:
            self.rotkehlchen.unlock_user(
                user=name,
                password=password,
                create_new=True,
                # For new accounts the value of sync approval does not matter.
                # Will always get the latest data from the server since locally we got nothing
                sync_approval='yes',
                premium_credentials=premium_credentials,
                initial_settings=initial_settings,
                sync_database=sync_database,
            )
        # not catching RotkehlchenPermissionError here as for new account with premium
        # syncing there is no way that permission needs to be asked by the user
        except (
            AuthenticationError,
            PremiumAuthenticationError,
            SystemPermissionError,
            DBSchemaError,
        ) as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        # Success!
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result_dict['result'] = {
                'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchanges_info(),
                'settings': process_result(self.rotkehlchen.get_settings(cursor)),
            }
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def _user_login(
            self,
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
    ) -> dict[str, Any]:
        if self.rotkehlchen.user_is_logged_in:
            return wrap_in_fail_result(
                message=(
                    f'Can not login to user {name} because user '
                    f'{self.rotkehlchen.data.username} is already logged in. '
                    f'Log out of that user first'
                ),
                status_code=HTTPStatus.CONFLICT,
            )

        try:
            self.rotkehlchen.unlock_user(
                user=name,
                password=password,
                create_new=False,
                sync_approval=sync_approval,
                premium_credentials=None,
            )
        # We are not catching PremiumAuthenticationError here since it should not bubble
        # up until here. Even with non valid keys in the DB login should work fine
        except AuthenticationError as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.UNAUTHORIZED,
            )
        except RotkehlchenPermissionError as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            return {
                'result': e.message_payload,
                'message': e.error_message,
                'status_code': HTTPStatus.MULTIPLE_CHOICES,
            }
        except (DBUpgradeError, SystemPermissionError, DBSchemaError) as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.CONFLICT,
            )
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            return wrap_in_fail_result(
                message=f'Unexpected database error: {str(e)}',
                status_code=HTTP_STATUS_INTERNAL_DB_ERROR,  # type: ignore  # Is a custom status code, not a member of HTTPStatus  # noqa: E501
            )

        # Success!
        exchanges = self.rotkehlchen.exchange_manager.get_connected_exchanges_info()
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = process_result(self.rotkehlchen.get_settings(cursor))

        return _wrap_in_ok_result({
            'exchanges': exchanges,
            'settings': settings,
        })

    def user_login(
            self,
            async_query: bool,
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._user_login,
                name=name,
                password=password,
                sync_approval=sync_approval,
            )

        response = self._user_login(
            name=name,
            password=password,
            sync_approval=sync_approval,
        )
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        result_dict = _wrap_in_result(result=result, message=msg)
        return api_response(result_dict, status_code=status_code)

    def user_logout(self, name: str) -> Response:
        result_dict: dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user {name} is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        # Kill all queries apart from the main loop -- perhaps a bit heavy handed
        # but the other options would be:
        # 1. to wait for all of them. That could take a lot of time, for no reason.
        #    All results would be discarded anyway since we are logging out.
        # 2. Have an intricate stop() notification system for each greenlet, but
        #   that is going to get complicated fast.
        gevent.killall(self.rotkehlchen.api_task_greenlets)
        with self.task_lock:
            self.task_results = {}
        self.rotkehlchen.logout()
        result_dict['result'] = True
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def user_set_premium_credentials(
            self,
            name: str,
            api_key: str,
            api_secret: str,
    ) -> Response:
        result_dict: dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user {name} is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        try:
            credentials = PremiumCredentials(
                given_api_key=api_key,
                given_api_secret=api_secret,
            )
        except IncorrectApiKeyFormat:
            result_dict['message'] = 'Given API Key/Secret pair format is invalid'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        try:
            self.rotkehlchen.set_premium_credentials(credentials)
        except PremiumAuthenticationError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        result_dict['result'] = True
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def user_change_password(
            self,
            name: str,
            current_password: str,
            new_password: str,
    ) -> Response:
        result_dict: dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user "{name}" is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        if current_password != self.rotkehlchen.data.password:
            result_dict['message'] = 'Provided current password is not correct'
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        success: bool
        try:
            success = self.rotkehlchen.data.change_password(new_password=new_password)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        if success is False:
            msg = 'The database rejected the password change for unknown reasons'
            result_dict['message'] = msg
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        # else
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def user_premium_key_remove(self) -> Response:
        """Returns successful result if API keys are successfully removed"""
        result_dict: dict[str, Any] = {'result': None, 'message': ''}
        success: bool

        success, msg = self.rotkehlchen.delete_premium_credentials()

        if success is False:
            result_dict['message'] = msg
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        # else
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def query_list_of_all_assets(
            self,
            filter_query: AssetsFilterQuery,
            identifiers: Optional[list[str]],
    ) -> Response:
        """
        If a set of identifiers is provided returns the information for those identifiers otherwise
        returns all supported assets with pagination.
        """
        assets, assets_found = GlobalDBHandler().retrieve_assets(filter_query=filter_query)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            assets_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='assets',
            )

        if identifiers is not None and len(identifiers) != assets_found:
            not_found = []
            found_assets = {asset['identifier'] for asset in assets}
            for asset in identifiers:
                if asset not in found_assets:
                    not_found.append(asset)
            msg = f"Queried identifiers {','.join(not_found)} are not present in the database"
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        result = {
            'entries': assets,
            'entries_found': assets_found,
            'entries_total': assets_total,
            'entries_limit': -1,
        }
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def get_assets_mappings(self, identifiers: list[str]) -> Response:
        try:
            asset_mappings, asset_collections = GlobalDBHandler().get_assets_mappings(identifiers)
            nft_mappings = self.rotkehlchen.data.db.get_nft_mappings(identifiers)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
        data_dict = {
            'assets': asset_mappings | nft_mappings,
            'asset_collections': asset_collections,
        }
        return api_response(
            # Using | is safe since keys in asset_mappings and nft_mappings don't intersect
            _wrap_in_ok_result(data_dict),
            status_code=HTTPStatus.OK,
        )

    def search_assets(self, filter_query: AssetsFilterQuery) -> Response:
        result = GlobalDBHandler().search_assets(
            db=self.rotkehlchen.data.db,
            filter_query=filter_query,
        )
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def search_assets_levenshtein(
            self,
            filter_query: LevenshteinFilterQuery,
            limit: Optional[int],
            search_nfts: bool,
    ) -> Response:
        result = search_assets_levenshtein(
            db=self.rotkehlchen.data.db,
            filter_query=filter_query,
            limit=limit,
            search_nfts=search_nfts,
        )
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @staticmethod
    def supported_modules() -> Response:
        """Returns all supported modules"""
        data = [{'id': x, 'name': y} for x, y in AVAILABLE_MODULES_MAP.items()]
        return api_response(
            _wrap_in_ok_result(data),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def query_owned_assets(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = process_result_list(self.rotkehlchen.data.db.query_owned_assets(cursor))
        return api_response(
            _wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
        )

    @staticmethod
    def get_asset_types() -> Response:
        types = [str(x) for x in AssetType if x not in ASSET_TYPES_EXCLUDED_FOR_USERS]
        return api_response(_wrap_in_ok_result(types), status_code=HTTPStatus.OK)

    def add_user_asset(self, asset_type: AssetType, **kwargs: Any) -> Response:
        globaldb = GlobalDBHandler()
        # There is no good way to figure out if an asset already exists in the DB
        # Best approximation we can do is this.
        identifiers = globaldb.check_asset_exists(
            asset_type=asset_type,
            name=kwargs['name'],  # no key error possible. Checked by marshmallow
            symbol=kwargs['symbol'],  # no key error possible. Checked by marshmallow
        )
        if identifiers is not None:
            return api_response(
                result=wrap_in_fail_result(
                    f'Failed to add {str(asset_type)} {kwargs["name"]} '
                    f'since it already exists. Existing ids: {",".join(identifiers)}'),
                status_code=HTTPStatus.CONFLICT,
            )

        # asset id needs to be unique but no combination of asset data is guaranteed to be unique.
        # And especially with the ability to edit assets we need an external uuid
        asset_id = str(uuid4())
        try:
            GlobalDBHandler().add_asset(
                asset_id=asset_id,
                asset_type=asset_type,
                data=kwargs,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.user_write() as cursor:
            self.rotkehlchen.data.db.add_asset_identifiers(cursor, [asset_id])
        return api_response(
            _wrap_in_ok_result({'identifier': asset_id}),
            status_code=HTTPStatus.OK,
        )

    @staticmethod
    def edit_user_asset(data: dict[str, Any]) -> Response:
        try:
            GlobalDBHandler().edit_user_asset(data)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver to requery DB
        AssetResolver().assets_cache.remove(data['identifier'])
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_asset(self, identifier: str) -> Response:
        try:

            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                # Before deleting, also make sure we have up to date global DB owned data
                self.rotkehlchen.data.db.update_owned_assets_in_globaldb(cursor)
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.rotkehlchen.data.db.delete_asset_identifier(write_cursor, identifier)

            GlobalDBHandler().delete_asset_by_identifier(identifier)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver
        AssetResolver().assets_cache.remove(identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def replace_asset(self, source_identifier: str, target_asset: Asset) -> Response:
        try:
            self.rotkehlchen.data.db.replace_asset_identifier(source_identifier, target_asset)
        except (UnknownAsset, InputError) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver
        AssetResolver().assets_cache.remove(source_identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @staticmethod
    def get_custom_evm_tokens(
            address: Optional[ChecksumEvmAddress],
            chain_id: ChainID,
    ) -> Response:
        if address is not None:
            token = GlobalDBHandler().get_evm_token(
                address=address,
                chain_id=chain_id,
            )
            if token is None:
                result = wrap_in_fail_result(f'Custom token with address {address} and chain {chain_id.to_name()} not found')  # noqa: E501
                status_code = HTTPStatus.NOT_FOUND
            else:
                result = _wrap_in_ok_result(token.to_dict())
                status_code = HTTPStatus.OK

            return api_response(result, status_code)

        # else return all custom tokens
        tokens = GlobalDBHandler().get_evm_tokens(chain_id=chain_id)
        return api_response(
            _wrap_in_ok_result([x.to_dict() for x in tokens]),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def add_custom_ethereum_token(self, token: EvmToken) -> Response:
        try:
            GlobalDBHandler().add_asset(
                asset_id=token.identifier,
                asset_type=AssetType.EVM_TOKEN,
                data=token,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.user_write() as cursor:
            # clean token detection cache.
            cursor.execute('DELETE from evm_accounts_details;')
            self.rotkehlchen.data.db.add_asset_identifiers(cursor, [token.identifier])

        return api_response(
            _wrap_in_ok_result({'identifier': token.identifier}),
            status_code=HTTPStatus.OK,
        )

    @staticmethod
    def edit_custom_ethereum_token(token: EvmToken) -> Response:
        try:
            identifier = GlobalDBHandler().edit_evm_token(token)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver to requery DB
        AssetResolver().assets_cache.remove(identifier)

        return api_response(
            result=_wrap_in_ok_result({'identifier': identifier}),
            status_code=HTTPStatus.OK,
        )

    def delete_custom_ethereum_token(
            self,
            address: ChecksumEvmAddress,
            chain_id: ChainID,
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                # Before deleting, also make sure we have up to date global DB owned data
                self.rotkehlchen.data.db.update_owned_assets_in_globaldb(cursor)
                identifier = evm_address_to_identifier(
                    address=address,
                    chain_id=chain_id,
                    token_type=EvmTokenKind.ERC20,
                )

            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.rotkehlchen.data.db.delete_asset_identifier(write_cursor, identifier)
                identifier = GlobalDBHandler().delete_evm_token(address=address, chain_id=chain_id)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver
        AssetResolver().assets_cache.remove(identifier)

        return api_response(
            result=_wrap_in_ok_result({'identifier': identifier}),
            status_code=HTTPStatus.OK,
        )

    def rebuild_assets_information(
            self,
            reset: Literal['soft', 'hard'],
            ignore_warnings: bool,
    ) -> Response:
        msg = 'Invalid value for reset'
        if reset == 'soft':
            success, msg = GlobalDBHandler().soft_reset_assets_list()
        elif reset == 'hard':
            success, msg = GlobalDBHandler().hard_reset_assets_list(
                user_db=self.rotkehlchen.data.db,
                force=ignore_warnings,
            )

        if success:
            return api_response(_wrap_in_ok_result(OK_RESULT), status_code=HTTPStatus.OK)
        return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

    def query_netvalue_data(self, include_nfts: bool) -> Response:
        from_ts = Timestamp(0)
        premium = self.rotkehlchen.premium

        if premium is None or not premium.is_active():
            today = datetime.datetime.now(tz=datetime.timezone.utc)
            start_of_day_today = datetime.datetime(today.year, today.month, today.day, tzinfo=datetime.timezone.utc)  # noqa: E501
            from_ts = Timestamp(int((start_of_day_today - datetime.timedelta(days=14)).timestamp()))  # noqa: E501

        data = self.rotkehlchen.data.db.get_netvalue_data(from_ts, include_nfts)
        result = process_result({'times': data[0], 'data': data[1]})
        return api_response(
            result=_wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def query_timed_balances_data(
            self,
            asset: Asset,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        # TODO: Think about this, but for now this is only balances, not liabilities
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            data = self.rotkehlchen.data.db.query_timed_balances(
                cursor=cursor,
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                asset=asset,
                balance_type=BalanceType.ASSET,
            )

        result = process_result_list(data)
        return api_response(
            result=_wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def query_value_distribution_data(self, distribution_by: str) -> Response:
        data: Union[list[DBAssetBalance], list[LocationData]]
        if distribution_by == 'location':
            data = self.rotkehlchen.data.db.get_latest_location_value_distribution()
        else:
            # Can only be 'asset'. Checked by the marshmallow encoding
            data = self.rotkehlchen.data.db.get_latest_asset_value_distribution()

        result = process_result_list(data)
        return api_response(
            result=_wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def query_premium_components(self) -> Response:
        result_dict = {'result': None, 'message': ''}
        try:
            # Here we ignore mypy error since we use @require_premium_user() decorator
            result = self.rotkehlchen.premium.query_premium_components()  # type: ignore
            result_dict['result'] = result
            status_code = HTTPStatus.OK
        except (RemoteError, PremiumAuthenticationError) as e:
            result_dict['message'] = str(e)
            status_code = HTTPStatus.CONFLICT

        return api_response(
            result=process_result(result_dict),
            status_code=status_code,
            log_result=False,
        )

    def get_messages(self) -> Response:
        warnings = self.rotkehlchen.msg_aggregator.consume_warnings()
        errors = self.rotkehlchen.msg_aggregator.consume_errors()
        result = {'warnings': warnings, 'errors': errors}
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def _process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        report_id, error_or_empty = self.rotkehlchen.process_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        return {'result': report_id, 'message': error_or_empty}

    def process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._process_history,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        response = self._process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        result_dict = _wrap_in_result(result=result, message=msg)
        return api_response(result_dict, status_code=status_code)

    def _get_history_debug(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Optional[Path],
    ) -> dict[str, Any]:
        """This method exports all history events for a timestamp range.
        It also exports the user settings & ignored action identifiers for PnL debugging.
        """
        error_or_empty, events = self.rotkehlchen.events_historian.get_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            has_premium=self.rotkehlchen.premium is not None,
        )
        if error_or_empty != '':
            return wrap_in_fail_result(error_or_empty, status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rotkehlchen.get_settings(cursor)
            ignored_ids = self.rotkehlchen.data.db.get_ignored_action_ids(cursor, None)
        debug_info = {
            'events': [entry.serialize_for_debug_import() for entry in events],
            'settings': settings.serialize(),
            'ignored_events_ids': {k.serialize(): v for k, v in ignored_ids.items()},
            'pnl_setting': {
                'from_timestamp': int(from_timestamp),
                'to_timestamp': int(to_timestamp),
            },
        }
        if directory_path is not None:
            with open(f'{directory_path}/pnl_debug.json', mode='w') as f:
                json.dump(debug_info, f, indent=2)
            return OK_RESULT
        return _wrap_in_ok_result(debug_info)

    def get_history_debug(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Optional[Path],
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_history_debug,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                directory_path=directory_path,
            )

        response = self._get_history_debug(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            directory_path=directory_path,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = _wrap_in_result(result=response['result'], message=response['message'])
        return api_response(result_dict, status_code=status_code)

    if getattr(sys, 'frozen', False) is False:
        def _import_history_debug(self, filepath: Union[FileStorage, Path]) -> dict[str, Any]:
            """Imports the PnL debug data for processing and report generation"""
            json_importer = DebugHistoryImporter(self.rotkehlchen.data.db)
            if isinstance(filepath, Path):
                success, msg, data = json_importer.import_history_debug(filepath=filepath)
            else:
                tmpfilepath = self.import_tmp_files[filepath]
                success, msg, data = json_importer.import_history_debug(filepath=tmpfilepath)
                tmpfilepath.unlink(missing_ok=True)
                del self.import_tmp_files[filepath]

            if success is False:
                return wrap_in_fail_result(
                    message=msg,
                    status_code=HTTPStatus.CONFLICT,
                )
            self.rotkehlchen.accountant.process_history(
                start_ts=Timestamp(data['pnl_settings']['from_timestamp']),
                end_ts=Timestamp(data['pnl_settings']['to_timestamp']),
                events=data['events'],
            )
            return OK_RESULT

        def import_history_debug(
                self,
                async_query: bool,
                filepath: Union[FileStorage, Path],
        ) -> Response:
            if isinstance(filepath, FileStorage):
                _, tmpfilepath = tempfile.mkstemp()
                filepath.save(tmpfilepath)
                self.import_tmp_files[filepath] = Path(tmpfilepath)

            if async_query is True:
                return self._query_async(
                    command=self._import_history_debug,
                    filepath=filepath,
                )

            response = self._import_history_debug(filepath=filepath)
            status_code = _get_status_code_from_async_response(response)
            result_dict = _wrap_in_result(response['result'], response['message'])
            return api_response(result_dict, status_code=status_code)

    def get_history_actionable_items(self) -> Response:
        pot = self.rotkehlchen.accountant.pots[0]
        missing_acquisitions = pot.cost_basis.missing_acquisitions
        missing_prices = pot.cost_basis.missing_prices

        processed_missing_acquisitions = [entry.serialize() for entry in missing_acquisitions]
        processed_missing_prices = [entry.serialize() for entry in missing_prices]
        result_dict = _wrap_in_ok_result(
            {
                'report_id': pot.report_id,
                'missing_acquisitions': processed_missing_acquisitions,
                'missing_prices': processed_missing_prices,
            },
        )
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def export_processed_history_csv(self, directory_path: Path) -> Response:
        success, msg = self.rotkehlchen.accountant.export(directory_path)
        if success is False:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def download_processed_history_csv(self) -> Response:
        success, zipfile = self.rotkehlchen.accountant.export(directory_path=None)
        if success is False:
            return api_response(wrap_in_fail_result('Could not create a zip archive'), status_code=HTTPStatus.CONFLICT)  # noqa: E501

        try:
            return send_file(
                path_or_file=zipfile,
                mimetype='application/zip',
                as_attachment=True,
                download_name='report.zip',
            )
        except FileNotFoundError:
            return api_response(
                wrap_in_fail_result('No file was found'),
                status_code=HTTPStatus.NOT_FOUND,
            )

    def get_history_status(self) -> Response:
        result = self.rotkehlchen.get_history_query_status()
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def query_periodic_data(self) -> Response:
        data = self.rotkehlchen.query_periodic_data()
        result = process_result(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def _add_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> dict[str, Any]:
        try:
            XpubManager(self.rotkehlchen.chains_aggregator).add_bitcoin_xpub(xpub_data=xpub_data)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except TagConstraintError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        # success
        return OK_RESULT

    def add_xpub(
            self,
            xpub_data: 'XpubData',
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._add_xpub,
                xpub_data=xpub_data,
            )

        response = self._add_xpub(xpub_data=xpub_data)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def _delete_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                XpubManager(self.rotkehlchen.chains_aggregator).delete_bitcoin_xpub(
                    write_cursor=cursor,
                    xpub_data=xpub_data,
                )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        # success
        return OK_RESULT

    def delete_xpub(
            self,
            xpub_data: 'XpubData',
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._delete_xpub,
                xpub_data=xpub_data,
            )

        response = self._delete_xpub(xpub_data=xpub_data)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def edit_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                XpubManager(self.rotkehlchen.chains_aggregator).edit_bitcoin_xpub(
                    write_cursor=write_cursor,
                    xpub_data=xpub_data,
                )
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                data = self.rotkehlchen.get_blockchain_account_data(cursor, xpub_data.blockchain)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)  # noqa: E501

        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    def _add_evm_accounts(
            self,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        try:
            added_accounts = self.rotkehlchen.add_evm_accounts(account_data=account_data)
        except (EthSyncError, TagConstraintError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        result = defaultdict(list)
        for chain, address in added_accounts:
            result[chain.value].append(address)
        return _wrap_in_ok_result(result)

    def add_evm_accounts(
            self,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._add_evm_accounts,
                account_data=account_data,
            )

        response = self._add_evm_accounts(account_data=account_data)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def get_blockchain_accounts(self, blockchain: SupportedBlockchain) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            data = self.rotkehlchen.get_blockchain_account_data(cursor, blockchain)
        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    @overload
    def _add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_EVM_CHAINS,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def _add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def _add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS,
            account_data: list[SingleBlockchainAccountData[BTCAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def _add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        ...

    def _add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            self.rotkehlchen.add_single_blockchain_accounts(chain=chain, account_data=account_data)
        except (EthSyncError, TagConstraintError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        # we can be sure that all addresses from account_data were added since the addition
        # would have failed otherwise
        added_addresses = [x.address for x in account_data]
        return _wrap_in_ok_result(added_addresses)

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_EVM_CHAINS,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
            async_query: bool,
    ) -> Response:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
            async_query: bool,
    ) -> Response:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS,
            account_data: list[SingleBlockchainAccountData[BTCAddress]],
            async_query: bool,
    ) -> Response:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
            async_query: bool,
    ) -> Response:
        ...

    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._add_single_blockchain_accounts,
                chain=chain,
                account_data=account_data,
            )

        response = self._add_single_blockchain_accounts(chain=chain, account_data=account_data)
        result = response['result']  # pylint: disable=unsubscriptable-object
        msg = response['message']  # pylint: disable=unsubscriptable-object
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def edit_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.rotkehlchen.edit_single_blockchain_accounts(
                    write_cursor=write_cursor,
                    blockchain=blockchain,
                    account_data=account_data,
                )
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                # success
                data = self.rotkehlchen.get_blockchain_account_data(cursor, blockchain)
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)  # noqa: E501

        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    def _remove_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            self.rotkehlchen.remove_single_blockchain_accounts(
                blockchain=blockchain,
                accounts=accounts,
            )
            balances_update = self.rotkehlchen.chains_aggregator.get_balances_update(chain=None)  # return full update of balances  # noqa: E501
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return _wrap_in_ok_result(balances_update.serialize())

    def remove_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._remove_single_blockchain_accounts,
                blockchain=blockchain,
                accounts=accounts,
            )

        response = self._remove_single_blockchain_accounts(blockchain=blockchain, accounts=accounts)  # noqa: E501
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def _get_manually_tracked_balances(self) -> dict[str, Any]:
        db_entries = get_manually_tracked_balances(db=self.rotkehlchen.data.db, balance_type=None)
        balances = process_result(
            {
                'balances': db_entries,
            },

        )
        return _wrap_in_ok_result(balances)

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument, no-self-use
            self,
            function: Callable[['DBHandler', list[ManuallyTrackedBalance]], None],
            data_or_ids: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        ...

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument, no-self-use
            self,
            function: Callable[['DBHandler', list[int]], None],
            data_or_ids: list[int],
    ) -> dict[str, Any]:
        ...

    def _modify_manually_tracked_balances(
            self,
            function: Union[
                Callable[['DBHandler', list[ManuallyTrackedBalance]], None],
                Callable[['DBHandler', list[int]], None],
            ],
            data_or_ids: Union[list[ManuallyTrackedBalance], list[int]],
    ) -> dict[str, Any]:
        try:
            function(self.rotkehlchen.data.db, data_or_ids)  # type: ignore
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)
        except TagConstraintError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return self._get_manually_tracked_balances()

    def get_manually_tracked_balances(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_manually_tracked_balances)

        result = self._get_manually_tracked_balances()
        return api_response(result, status_code=HTTPStatus.OK)

    def _manually_tracked_balances_api_query(
            self,
            async_query: bool,
            function: Union[
                Callable[['DBHandler', list[ManuallyTrackedBalance]], None],
                Callable[['DBHandler', list[int]], None],
            ],
            data_or_ids: Union[list[ManuallyTrackedBalance], list[int]],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._modify_manually_tracked_balances,
                function=function,
                data_or_ids=data_or_ids,
            )
        result = self._modify_manually_tracked_balances(function, data_or_ids)  # type: ignore
        status_code = _get_status_code_from_async_response(result)
        return api_response(result, status_code=status_code)

    def add_manually_tracked_balances(
            self,
            async_query: bool,
            data: list[ManuallyTrackedBalance],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=add_manually_tracked_balances,
            data_or_ids=data,
        )

    def edit_manually_tracked_balances(
            self,
            async_query: bool,
            data: list[ManuallyTrackedBalance],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=edit_manually_tracked_balances,
            data_or_ids=data,
        )

    def remove_manually_tracked_balances(
            self,
            async_query: bool,
            ids: list[int],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=remove_manually_tracked_balances,
            data_or_ids=ids,
        )

    def get_ignored_assets(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = [asset.identifier for asset in self.rotkehlchen.data.db.get_ignored_assets(cursor)]  # noqa: E501
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def add_ignored_assets(self, assets: list[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.add_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def remove_ignored_assets(self, assets: list[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def add_ignored_action_ids(self, action_type: ActionType, action_ids: list[str]) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.add_to_ignored_action_ids(
                    write_cursor=cursor,
                    action_type=action_type,
                    identifiers=action_ids,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def remove_ignored_action_ids(
            self,
            action_type: ActionType,
            action_ids: list[str],
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.remove_from_ignored_action_ids(
                    write_cursor=cursor,
                    action_type=action_type,
                    identifiers=action_ids,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_queried_addresses_per_module(self) -> Response:
        result = QueriedAddresses(self.rotkehlchen.data.db).get_queried_addresses_per_module()
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def add_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> Response:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).add_queried_address_for_module(module, address)  # noqa: E501
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_queried_addresses_per_module()

    def remove_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> Response:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).remove_queried_address_for_module(module, address)  # noqa: E501
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_queried_addresses_per_module()

    def get_info(self, check_for_updates: bool) -> Response:
        version = get_current_version(check_for_updates=check_for_updates)
        result = {
            'version': process_result(version),
            'data_directory': str(self.rotkehlchen.data_dir),
            'log_level': logging.getLevelName(logging.getLogger().getEffectiveLevel()),
            'accept_docker_risk': 'ROTKI_ACCEPT_DOCKER_RISK' in os.environ,
            'backend_default_arguments': {
                'max_logfiles_num': DEFAULT_MAX_LOG_BACKUP_FILES,
                'max_size_in_mb_all_logs': DEFAULT_MAX_LOG_SIZE_IN_MB,
                'sqlite_instructions': DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            },
        }
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @staticmethod
    def ping() -> Response:
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def _import_data(
            self,
            source: DataImportSource,
            filepath: Union[FileStorage, Path],
            **kwargs: Any,
    ) -> dict[str, Any]:
        if isinstance(filepath, Path):
            success, msg = self.rotkehlchen.data_importer.import_csv(
                source=source,
                filepath=filepath,
                **kwargs,
            )
        else:
            tmpfilepath = self.import_tmp_files[filepath]
            success, msg = self.rotkehlchen.data_importer.import_csv(
                source=source,
                filepath=tmpfilepath,
                **kwargs,
            )
            tmpfilepath.unlink(missing_ok=True)
            del self.import_tmp_files[filepath]

        if success is False:
            return wrap_in_fail_result(
                message=f'Invalid CSV format, missing required field: {msg}',
                status_code=HTTPStatus.BAD_REQUEST,
            )

        return OK_RESULT

    def import_data(
            self,
            source: DataImportSource,
            filepath: Union[FileStorage, Path],
            async_query: bool,
            **kwargs: Any,
    ) -> Response:
        if not isinstance(filepath, Path):
            _, tmpfilepath = tempfile.mkstemp()
            filepath.save(tmpfilepath)
            self.import_tmp_files[filepath] = Path(tmpfilepath)

        if async_query is True:
            return self._query_async(
                command=self._import_data,
                source=source,
                filepath=filepath,
                **kwargs,
            )

        response = self._import_data(source=source, filepath=filepath, **kwargs)
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(result_dict, status_code=status_code)

    def _get_eth2_stake_deposits(self) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.chains_aggregator.get_eth2_staking_deposits()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except ModuleInactive as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': process_result_list([x.serialize() for x in result]), 'message': ''}

    def get_eth2_stake_deposits(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_eth2_stake_deposits)

        response = self._get_eth2_stake_deposits()
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def _get_eth2_stake_details(self) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.chains_aggregator.get_eth2_staking_details()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except ModuleInactive as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        current_usd_price = Inquirer().find_usd_price(A_ETH)
        return {
            'result': process_result_list([x.serialize(current_usd_price) for x in result]),
            'message': '',
        }

    def get_eth2_stake_details(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_eth2_stake_details)

        response = self._get_eth2_stake_details()
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def _get_eth2_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            only_cache: bool,
    ) -> dict[str, Any]:
        try:
            stats, filter_total_found, sum_pnl, sum_usd_value = self.rotkehlchen.chains_aggregator.get_eth2_daily_stats(  # noqa: E501
                filter_query=filter_query,
                only_cache=only_cache,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except ModuleInactive as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = {
                'entries': [x.serialize() for x in stats],
                'sum_pnl': str(sum_pnl),
                'sum_usd_value': str(sum_usd_value),
                'entries_found': filter_total_found,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor, 'eth2_daily_staking_details'),  # noqa: E501
            }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_eth2_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_eth2_daily_stats,
                filter_query=filter_query,
                only_cache=only_cache,
            )

        response = self._get_eth2_daily_stats(filter_query=filter_query, only_cache=only_cache)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def get_eth2_validators(self) -> Response:
        try:
            validators = self.rotkehlchen.chains_aggregator.get_eth2_validators()
        except ModuleInactive as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        limit = -1
        entries_found = len(validators)
        if self.rotkehlchen.premium is None:
            limit = FREE_VALIDATORS_LIMIT
            validators = validators[:4]

        result = _wrap_in_ok_result({
            'entries': [x.serialize() for x in validators],
            'entries_found': entries_found,
            'entries_limit': limit,
        })
        return api_response(
            result=result,
            status_code=HTTPStatus.OK,
        )

    def _add_eth2_validator(
            self,
            validator_index: Optional[int],
            public_key: Optional[Eth2PubKey],
            ownership_proportion: FVal,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.chains_aggregator.add_eth2_validator(
                validator_index=validator_index,
                public_key=public_key,
                ownership_proportion=ownership_proportion,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except PremiumPermissionError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.UNAUTHORIZED}  # noqa: E501
        except (InputError, ModuleInactive) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': ''}

    def add_eth2_validator(
            self,
            validator_index: Optional[int],
            public_key: Optional[Eth2PubKey],
            ownership_proportion: FVal,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._add_eth2_validator,
                validator_index=validator_index,
                public_key=public_key,
                ownership_proportion=ownership_proportion,
            )

        response = self._add_eth2_validator(
            validator_index=validator_index,
            public_key=public_key,
            ownership_proportion=ownership_proportion,
        )
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def edit_eth2_validator(self, validator_index: int, ownership_proportion: FVal) -> Response:
        try:
            self.rotkehlchen.chains_aggregator.edit_eth2_validator(
                validator_index=validator_index,
                ownership_proportion=ownership_proportion,
            )
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)
        except (InputError, ModuleInactive) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

    def delete_eth2_validator(
            self,
            validators: list[dict],
    ) -> Response:
        try:
            for validator in validators:
                self.rotkehlchen.chains_aggregator.delete_eth2_validator(
                    validator_index=validator.get('validator_index'),
                    public_key=validator.get('public_key'),
                )
            result = OK_RESULT
            status_code = HTTPStatus.OK
        except InputError as e:
            result = {'result': None, 'message': str(e)}
            status_code = HTTPStatus.CONFLICT
        except ModuleInactive as e:
            result = {'result': None, 'message': str(e)}
            status_code = HTTPStatus.CONFLICT

        return api_response(result, status_code=status_code)

    def _get_defi_balances(self) -> dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            balances = self.rotkehlchen.chains_aggregator.query_defi_balances()
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return {'result': process_result(balances), 'message': ''}

    def get_defi_balances(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_defi_balances)

        response = self._get_defi_balances()
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def _get_ethereum_airdrops(self) -> dict[str, Any]:
        try:
            data = check_airdrops(
                addresses=self.rotkehlchen.chains_aggregator.accounts.eth,
                data_dir=self.rotkehlchen.data_dir,
            )
        except (RemoteError, UnableToDecryptRemoteData) as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except OSError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.INSUFFICIENT_STORAGE)

        return _wrap_in_ok_result(process_result(data))

    def get_ethereum_airdrops(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_ethereum_airdrops)

        response = self._get_ethereum_airdrops()
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def get_rpc_nodes(self, blockchain: SupportedBlockchain) -> Response:
        nodes = self.rotkehlchen.data.db.get_rpc_nodes(blockchain=blockchain)
        result_dict = _wrap_in_ok_result(process_result_list(list(nodes)))
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def add_rpc_node(self, node: WeightedNode) -> Response:
        try:
            self.rotkehlchen.data.db.add_rpc_node(node)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Update the connected nodes
        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=node.node_info.blockchain,
            only_active=True,
        )
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(node.node_info.blockchain)
        manager.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def update_rpc_node(self, node: WeightedNode) -> Response:
        try:
            self.rotkehlchen.data.db.update_rpc_node(node)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Update the connected nodes
        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=node.node_info.blockchain,
            only_active=True,
        )
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(node.node_info.blockchain)
        manager.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_rpc_node(self, identifier: int, blockchain: SupportedBlockchain) -> Response:
        try:
            self.rotkehlchen.data.db.delete_rpc_node(identifier=identifier, blockchain=blockchain)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Update the connected nodes
        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=blockchain,
            only_active=True,
        )
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)  # type: ignore
        manager.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def purge_module_data(self, module_name: Optional[ModuleName]) -> Response:
        self.rotkehlchen.data.db.purge_module_data(module_name)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _eth_module_query(
            self,
            module_name: ModuleName,
            method: str,
            query_specific_balances_before: Optional[list[str]],
            **kwargs: Any,
    ) -> dict[str, Any]:
        """A function abstracting away calls to ethereum modules

        Can optionally specify if eth balances should be queried before the
        actual intended eth module query.
        """
        result = None
        msg = ''
        status_code = HTTPStatus.OK

        if query_specific_balances_before and 'defi' in query_specific_balances_before:

            # Make sure ethereum balances are queried (this is protected by lock and by time cache)
            # so most of the times it should have already ran
            try:
                self.rotkehlchen.chains_aggregator.query_balances(
                    blockchain=SupportedBlockchain.ETHEREUM,
                )
            except (RemoteError, EthSyncError) as e:
                return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        module_obj = self.rotkehlchen.chains_aggregator.get_module(module_name)
        if module_obj is None:
            return {
                'result': None,
                'status_code': HTTPStatus.CONFLICT,
                'message': f'{module_name} module is not activated',
            }

        try:
            result = getattr(module_obj, method)(**kwargs)
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY
        except InputError as e:
            msg = str(e)
            status_code = HTTPStatus.CONFLICT

        return {'result': result, 'message': msg, 'status_code': status_code}

    def _api_query_for_eth_module(
            self,
            async_query: bool,
            module_name: ModuleName,
            method: str,
            query_specific_balances_before: Optional[list[str]],
            **kwargs: Any,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._eth_module_query,
                module_name=module_name,
                method=method,
                query_specific_balances_before=query_specific_balances_before,
                **kwargs,
            )

        response = self._eth_module_query(
            module_name=module_name,
            method=method,
            query_specific_balances_before=query_specific_balances_before,
            **kwargs,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        status_code = _get_status_code_from_async_response(response)
        return api_response(process_result(result_dict), status_code=status_code)

    def get_makerdao_dsr_balance(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='makerdao_dsr',
            method='get_current_dsr',
            query_specific_balances_before=None,
        )

    def get_makerdao_dsr_history(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='makerdao_dsr',
            method='get_historical_dsr',
            query_specific_balances_before=None,
        )

    def get_makerdao_vaults(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='makerdao_vaults',
            method='get_vaults',
            query_specific_balances_before=None,
        )

    def get_makerdao_vault_details(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='makerdao_vaults',
            method='get_vault_details',
            query_specific_balances_before=None,
        )

    def get_aave_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='aave',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    def get_aave_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='aave',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('aave'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    def get_compound_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='compound',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    def get_compound_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='compound',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('compound'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_yearn_vaults_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='yearn_vaults',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    def get_yearn_vaults_v2_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='yearn_vaults_v2',
            method='get_balances',
            # We need to query defi balances before since eth balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the eth balances as a lambda function here so that they
            # are retrieved only after we are sure the eth balances have been
            # queried.
            given_eth_balances=lambda: self.rotkehlchen.chains_aggregator.balances.eth,
        )

    def get_yearn_vaults_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='yearn_vaults',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('yearn_vaults'),  # noqa: E501
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_yearn_vaults_v2_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='yearn_vaults_v2',
            method='get_history',
            query_specific_balances_before=['defi'],
            # Giving the eth balances as a lambda function here so that they
            # are retrieved only after we are sure the eth balances have been
            # queried.
            given_eth_balances=lambda: self.rotkehlchen.chains_aggregator.balances.eth,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module(
                'yearn_vaults_v2',
            ),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_uniswap_balances(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='uniswap',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('uniswap'),
        )

    def get_uniswap_v3_balances(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='uniswap',
            method='get_v3_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('uniswap'),
        )

    def get_uniswap_events_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='uniswap',
            method='get_events_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('uniswap'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_sushiswap_balances(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='sushiswap',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('sushiswap'),
        )

    def get_sushiswap_events_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='sushiswap',
            method='get_events_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('sushiswap'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_loopring_balances(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='loopring',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('loopring'),
        )

    def get_balancer_balances(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='balancer',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('balancer'),
        )

    def get_balancer_events_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='balancer',
            method='get_events_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('balancer'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_dill_balance(self, async_query: bool) -> Response:
        addresses = self.rotkehlchen.chains_aggregator.queried_addresses_for_module('pickle_finance')  # noqa: E501
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='pickle_finance',
            method='get_dill_balances',
            query_specific_balances_before=['defi'],
            addresses=addresses,
        )

    def get_liquity_troves(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='liquity',
            method='get_positions',
            query_specific_balances_before=None,
            addresses_list=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),  # noqa: E501
        )

    def get_liquity_staked(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='liquity',
            method='liquity_staking_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
        )

    def get_liquity_stability_pool_positions(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='liquity',
            method='get_stability_pool_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
        )

    def get_liquity_trove_events(
            self,
            async_query: bool,
            reset_db_data: bool,  # pylint: disable=unused-argument
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='liquity',
            method='get_trove_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def get_liquity_stake_events(
            self,
            async_query: bool,
            reset_db_data: bool,  # pylint: disable=unused-argument
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='liquity',
            method='get_staking_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def _watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: Optional[dict[str, Any]],
    ) -> Response:
        try:
            # we know that premium exists here due to require_premium_user
            result_json = self.rotkehlchen.premium.watcher_query(  # type:ignore
                method=method,
                data=data,
            )
        except RemoteError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumApiError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(_wrap_in_ok_result(result_json), status_code=HTTPStatus.OK)

    def get_watchers(self) -> Response:
        return self._watcher_query(method='GET', data=None)

    def add_watchers(self, watchers: list[dict[str, Any]]) -> Response:
        return self._watcher_query(method='PUT', data={'watchers': watchers})

    def edit_watchers(self, watchers: list[dict[str, Any]]) -> Response:
        return self._watcher_query(method='PATCH', data={'watchers': watchers})

    def delete_watchers(self, watchers: list[str]) -> Response:
        return self._watcher_query(method='DELETE', data={'watchers': watchers})

    def purge_exchange_data(self, location: Optional[Location]) -> Response:
        with self.rotkehlchen.data.db.user_write() as cursor:
            if location:
                self.rotkehlchen.data.db.purge_exchange_data(cursor, location)
            else:
                for exchange_location in ALL_SUPPORTED_EXCHANGES:
                    self.rotkehlchen.data.db.purge_exchange_data(cursor, exchange_location)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def purge_evm_transaction_data(self, chain_id: Optional[SUPPORTED_CHAIN_IDS]) -> Response:
        chain = None if chain_id is None else chain_id.to_blockchain()
        DBEvmTx(self.rotkehlchen.data.db).purge_evm_transaction_data(
            chain=chain,  # type: ignore  # chain_id.to_blockchain() will only give supported chain
        )
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_evm_transactions(
            self,
            only_cache: bool,
            filter_query: EvmTransactionsFilterQuery,
            event_params: dict[str, Any],
    ) -> dict[str, Any]:
        chain_ids: tuple[SUPPORTED_CHAIN_IDS]
        if filter_query.chain_id is None:  # type ignore below is due to get_args
            chain_ids = get_args(SUPPORTED_CHAIN_IDS)  # type: ignore[assignment]
        else:
            chain_ids = (filter_query.chain_id,)

        message = ''
        status_code = HTTPStatus.OK
        if only_cache is False:  # we query the chain
            for chain_id in chain_ids:
                evm_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id)
                try:
                    evm_manager.transactions.query_chain(filter_query)
                except RemoteError as e:
                    transactions = None
                    status_code = HTTPStatus.BAD_GATEWAY
                    message = str(e)
                    break
                except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                    transactions = None
                    status_code = HTTPStatus.BAD_REQUEST
                    message = str(e)
                    break

            if status_code != HTTPStatus.OK:
                return {'result': None, 'message': message, 'status_code': status_code}

        # if needed, chain will have been queried by now so let's get everything from DB
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            transactions, total_filter_count = dbevmtx.get_evm_transactions_and_limit_info(
                cursor=cursor,
                filter_=filter_query,
                has_premium=self.rotkehlchen.premium is not None,
            )

            if len(transactions) != 0:
                mapping = self.rotkehlchen.data.db.get_ignored_action_ids(cursor, ActionType.EVM_TRANSACTION)  # noqa: E501
                ignored_ids = mapping.get(ActionType.EVM_TRANSACTION, [])
                entries_result = []
                dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
                asset = None
                if event_params['asset'] is not None:
                    asset = (event_params['asset'], )
                for entry in transactions:
                    events = dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=HistoryEventFilterQuery.make(
                            event_identifiers=[entry.tx_hash],
                            assets=asset,
                            protocols=event_params['protocols'],
                            event_types=event_params['event_types'],
                            event_subtypes=event_params['event_subtypes'],
                            exclude_ignored_assets=event_params['exclude_ignored_assets'],
                        ),
                        has_premium=True,  # for this function we don't limit. We only limit txs.
                    )

                    customized_event_ids = dbevents.get_customized_event_identifiers(
                        cursor=cursor,
                        chain_id=filter_query.chain_id,
                    )
                    entries_result.append({
                        'entry': entry.serialize(),
                        'decoded_events': [
                            {
                                'entry': x.serialize_without_extra_data(),
                                'has_details': x.has_details(),
                                'customized': x.identifier in customized_event_ids,
                            } for x in events
                        ],
                        'ignored_in_accounting': entry.identifier in ignored_ids,
                    })
            else:
                entries_result = []

            result: Optional[dict[str, Any]] = None
            kwargs = {}
            if filter_query.chain_id is not None:
                kwargs['chain_id'] = filter_query.chain_id.serialize_for_db()
            result = {
                'entries': entries_result,
                'entries_found': total_filter_count,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(
                    cursor=cursor,
                    entries_table='evm_transactions',
                    **kwargs,  # type: ignore[arg-type]
                ),
                'entries_limit': FREE_ETH_TX_LIMIT if self.rotkehlchen.premium is None else -1,
            }

        return {'result': result, 'message': message, 'status_code': status_code}

    def get_evm_transactions(
            self,
            async_query: bool,
            only_cache: bool,
            filter_query: EvmTransactionsFilterQuery,
            event_params: dict[str, Any],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_evm_transactions,
                only_cache=only_cache,
                filter_query=filter_query,
                event_params=event_params,
            )

        response = self._get_evm_transactions(
            only_cache=only_cache,
            filter_query=filter_query,
            event_params=event_params,
        )
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def _decode_evm_transactions(
            self,
            ignore_cache: bool,
            data: list[EvmTransactionDecodingApiData],
    ) -> dict[str, Any]:
        """
        Decode a set of transactions selected by their transaction hash. If the tx_hashes
        value is None all the transactions for that chain  in the database will be
        attempted to be decoded. If the tx_hashes argument is provided then the USD
        price for their events will be queried.
        """
        task_manager = self.rotkehlchen.task_manager
        result = None
        message = ''
        status_code = HTTPStatus.OK

        for entry in data:
            chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(entry['evm_chain'])
            try:
                decoded_events = chain_manager.transactions_decoder.decode_transaction_hashes(
                    ignore_cache=ignore_cache,
                    tx_hashes=entry['tx_hashes'],
                )
                if entry['tx_hashes'] is not None and task_manager is not None:
                    # Trigger the task to query the missing prices for the decoded events
                    events_filter = HistoryEventFilterQuery.make(
                        event_identifiers=[event.event_identifier for event in decoded_events],
                    )
                    entries = task_manager.get_base_entries_missing_prices(events_filter)
                    task_manager.query_missing_prices_of_base_entries(
                        entries_missing_prices=entries,
                    )
            except (RemoteError, DeserializationError) as e:
                status_code = HTTPStatus.BAD_GATEWAY
                message = f'Failed to request evm transaction decoding due to {str(e)}'
                break
            except InputError as e:
                status_code = HTTPStatus.CONFLICT
                message = f'Failed to request evm transaction decoding due to {str(e)}'
                break
        else:  # no break in the for loop, success
            result = True

        return {'result': result, 'message': message, 'status_code': status_code}

    def decode_evm_transactions(
            self,
            async_query: bool,
            ignore_cache: bool,
            data: list[EvmTransactionDecodingApiData],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._decode_evm_transactions,
                ignore_cache=ignore_cache,
                data=data,
            )

        response = self._decode_evm_transactions(ignore_cache=ignore_cache, data=data)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def _decode_pending_evm_transactions(
            self,
            data: list[EvmPendingTransactionDecodingApiData],
    ) -> dict[str, Any]:
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        result = {}
        for entry in data:
            chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(entry['evm_chain'])
            # make sure that all the receipts are already queried
            chain_manager.transactions.get_receipts_for_transactions_missing_them(
                addresses=entry['addresses'],
            )
            amount_of_tx_to_decode = dbevmtx.count_hashes_not_decoded(
                addresses=entry['addresses'],
                chain_id=entry['evm_chain'],
            )
            if amount_of_tx_to_decode > 0:
                chain_manager.transactions_decoder.get_and_decode_undecoded_transactions(
                    addresses=entry['addresses'],
                )
                result[entry['evm_chain'].to_name()] = amount_of_tx_to_decode

        return {
            'result': {'decoded_tx_number': result},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def decode_pending_evm_transactions(
            self,
            async_query: bool,
            data: list[EvmPendingTransactionDecodingApiData],
    ) -> Response:
        """
        This method should be called after querying ethereum transactions and does the following:
        - Query missing receipts
        - Decode ethereum transactions

        It can be a slow process and this is why it is important to set the list of addresses
        queried per module that need to be decoded.

        This logic is executed by the frontend in pages where the set of transactions needs to be
        up to date, for example, the liquity module.
        """
        if async_query is True:
            return self._query_async(
                command=self._decode_pending_evm_transactions,
                data=data,
            )

        response = self._decode_pending_evm_transactions(data)
        status_code = _get_status_code_from_async_response(response)
        result_dict = _wrap_in_result(result=response['result'], message=response['message'])

        return api_response(result_dict, status_code=status_code)

    def get_asset_icon(
            self,
            asset: Asset,
            match_header: Optional[str],
    ) -> Response:
        file_md5 = self.rotkehlchen.icon_manager.iconfile_md5(asset)
        if file_md5 and match_header and match_header == file_md5:
            # Response content unmodified
            return make_response(
                (
                    b'',
                    HTTPStatus.NOT_MODIFIED,
                    {'mimetype': 'image/png', 'Content-Type': 'image/png'},
                ),
            )

        image_data = self.rotkehlchen.icon_manager.get_icon(asset)
        if image_data is None:
            response = make_response(
                (
                    b'',
                    HTTPStatus.NOT_FOUND, {'mimetype': 'image/png', 'Content-Type': 'image/png'}),
            )
        else:
            response = make_response(
                (
                    image_data,
                    HTTPStatus.OK, {'mimetype': 'image/png', 'Content-Type': 'image/png'}),
            )
            response.set_etag(hashlib.md5(image_data).hexdigest())

        return response

    def upload_asset_icon(self, asset: Asset, filepath: Path) -> Response:
        self.rotkehlchen.icon_manager.add_icon(asset=asset, icon_path=filepath)
        return api_response(
            result=_wrap_in_ok_result({'identifier': asset.identifier}),
            status_code=HTTPStatus.OK,
        )

    def refresh_asset_icon(self, asset: AssetWithOracles) -> Response:
        """Deletes an asset's icon from the cache and requeries it."""
        self.rotkehlchen.icon_manager.delete_icon(asset)
        try:
            is_success = self.rotkehlchen.icon_manager.query_coingecko_for_icon(
                asset=asset,
                coingecko_id=asset.to_coingecko(),
            )
        except UnsupportedAsset:
            is_success = False

        if is_success is False:
            return api_response(
                wrap_in_fail_result(f'Unable to refresh icon for {asset} at the moment'),
                status_code=HTTPStatus.NOT_FOUND,
            )
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_current_assets_price(
            self,
            assets: list[AssetWithNameAndType],
            target_asset: Asset,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        """Return the current price of the assets in the target asset currency.
        """
        log.debug(
            f'Querying the current {target_asset.identifier} price of these assets: '
            f'{", ".join([asset.identifier for asset in assets])}',
        )
        # Type is list instead of tuple here because you can't serialize a tuple
        assets_price: dict[Asset, list[Union[Price, Optional[int], bool]]] = {}
        oracle: Optional[CurrentPriceOracle]
        for asset in assets:
            if asset != target_asset:
                if asset.asset_type == AssetType.NFT:
                    nft_price_data = self._eth_module_query(
                        module_name='nfts',
                        method='get_nfts_with_price',
                        query_specific_balances_before=None,
                    )
                    oracle = CurrentPriceOracle.MANUALCURRENT if nft_price_data['manually_input'] is True else CurrentPriceOracle.BLOCKCHAIN  # noqa: E501
                    assets_price[asset] = [Price(nft_price_data['usd_price']), oracle.value, False]
                else:
                    price, oracle, used_main_currency = Inquirer().find_price_and_oracle(  # noqa: E501
                        from_asset=asset,
                        to_asset=target_asset,
                        ignore_cache=ignore_cache,
                        match_main_currency=True,
                    )
                    assets_price[asset] = [price, oracle.value, used_main_currency]
            else:
                assets_price[asset] = [Price(ONE), CurrentPriceOracle.BLOCKCHAIN.value, False]

        result = {
            'assets': assets_price,
            'target_asset': target_asset,
            'oracles': {str(oracle): oracle.value for oracle in CurrentPriceOracle},
        }
        return _wrap_in_ok_result(process_result(result))

    def get_current_assets_price(
            self,
            assets: list[AssetWithNameAndType],
            target_asset: Asset,
            ignore_cache: bool,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_current_assets_price,
                assets=assets,
                target_asset=target_asset,
                ignore_cache=ignore_cache,
            )

        response = self._get_current_assets_price(
            assets=assets,
            target_asset=target_asset,
            ignore_cache=ignore_cache,
        )
        status_code = _get_status_code_from_async_response(response)
        return api_response(_wrap_in_ok_result(response['result']), status_code=status_code)

    @staticmethod
    def _get_historical_assets_price(
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
    ) -> dict[str, Any]:
        """Return the price of the assets at the given timestamps in the target
        asset currency.
        """
        log.debug(
            f'Querying the historical {target_asset.identifier} price of these assets: '
            f'{", ".join(f"{asset.identifier} at {ts}" for asset, ts in assets_timestamp)}',
            assets_timestamp=assets_timestamp,
        )
        assets_price: DefaultDict[Asset, DefaultDict] = defaultdict(lambda: defaultdict(lambda: Price(ZERO)))  # noqa: E501
        for asset, timestamp in assets_timestamp:
            try:
                price = PriceHistorian().query_historical_price(
                    from_asset=asset,
                    to_asset=target_asset,
                    timestamp=timestamp,
                )
            except (RemoteError, NoPriceForGivenTimestamp) as e:
                log.error(
                    f'Could not query the historical {target_asset.identifier} price for '
                    f'{asset.identifier} at time {timestamp} due to: {str(e)}. Using zero price',
                )
                price = Price(ZERO)

            assets_price[asset][timestamp] = price

        result = {
            'assets': {k: dict(v) for k, v in assets_price.items()},
            'target_asset': target_asset,
        }
        return _wrap_in_ok_result(process_result(result))

    def get_historical_assets_price(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_historical_assets_price,
                assets_timestamp=assets_timestamp,
                target_asset=target_asset,
            )

        response = self._get_historical_assets_price(
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
        )
        status_code = _get_status_code_from_async_response(response)
        return api_response(_wrap_in_ok_result(response['result']), status_code=status_code)

    def _sync_data(self, action: Literal['upload', 'download']) -> dict[str, Any]:
        try:
            success, msg = self.rotkehlchen.premium_sync_manager.sync_data(action)
            if msg.startswith('Pulling failed'):
                return wrap_in_fail_result(msg, status_code=HTTPStatus.BAD_GATEWAY)
            return _wrap_in_result(success, message=msg)
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumApiError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumAuthenticationError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.UNAUTHORIZED)

    def sync_data(
            self,
            async_query: bool,
            action: Literal['upload', 'download'],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._sync_data,
                action=action,
            )

        result_dict = self._sync_data(action)
        status_code = _get_status_code_from_async_response(result_dict)
        return api_response(result_dict, status_code=status_code)

    def _create_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            purge_old: bool,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.create_oracle_cache(oracle, from_asset, to_asset, purge_old)
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except UnsupportedAsset as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return _wrap_in_ok_result(True)

    def create_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            purge_old: bool,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._create_oracle_cache,
                oracle=oracle,
                from_asset=from_asset,
                to_asset=to_asset,
                purge_old=purge_old,
            )

        response = self._create_oracle_cache(
            oracle=oracle,
            from_asset=from_asset,
            to_asset=to_asset,
            purge_old=purge_old,
        )
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    @staticmethod
    def delete_oracle_cache(
            oracle: HistoricalPriceOracle,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Response:
        GlobalDBHandler.delete_historical_prices(
            from_asset=from_asset,
            to_asset=to_asset,
            source=oracle,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    @staticmethod
    def _get_oracle_cache(oracle: HistoricalPriceOracle) -> dict[str, Any]:
        cache_data = GlobalDBHandler().get_historical_price_data(oracle)
        result = _wrap_in_ok_result(cache_data)
        result['status_code'] = HTTPStatus.OK
        return result

    def get_oracle_cache(self, oracle: HistoricalPriceOracle, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_oracle_cache, oracle=oracle)

        response = self._get_oracle_cache(oracle=oracle)
        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    @staticmethod
    def get_supported_oracles() -> Response:
        data = {
            # don't expose some sources in the api
            'history': [{'id': str(x), 'name': str(x).capitalize()} for x in HistoricalPriceOracle if x not in NOT_EXPOSED_SOURCES],  # noqa: E501
            'current': [{'id': str(x), 'name': str(x).capitalize()} for x in CurrentPriceOracle],  # noqa: E501
        }
        result_dict = _wrap_in_ok_result(data)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def _get_token_info(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        eth_manager = self.rotkehlchen.chains_aggregator.ethereum
        try:
            info = eth_manager.node_inquirer.get_erc20_contract_info(address=address)
        except BadFunctionCallOutput:
            return wrap_in_fail_result(
                f'Address {address} seems to not be a deployed contract',
                status_code=HTTPStatus.CONFLICT,
            )
        return _wrap_in_ok_result(info)

    def get_token_information(
            self,
            token_address: ChecksumEvmAddress,
            async_query: bool,
    ) -> Response:

        if async_query is True:
            return self._query_async(command=self._get_token_info, address=token_address)

        response = self._get_token_info(token_address)

        result = response['result']
        msg = response['message']
        status_code = _get_status_code_from_async_response(response)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=status_code)

        # Success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=status_code)

    def _get_assets_updates(self) -> dict[str, Any]:
        try:
            local, remote, new_changes = self.rotkehlchen.assets_updater.check_for_updates()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return _wrap_in_ok_result({'local': local, 'remote': remote, 'new_changes': new_changes})

    def get_assets_updates(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(command=self._get_assets_updates)

        response = self._get_assets_updates()
        return api_response(
            result={'result': response['result'], 'message': response['message']},
            status_code=response.get('status_code', HTTPStatus.OK),
        )

    def _perform_assets_updates(
            self,
            up_to_version: Optional[int],
            conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
    ) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.assets_updater.perform_update(up_to_version, conflicts)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        if result is None:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.add_globaldb_assetids(cursor)
            return OK_RESULT

        return {
            'result': result,
            'message': 'Found conflicts during assets upgrade',
            'status_code': HTTPStatus.CONFLICT,
        }

    def perform_assets_updates(
            self,
            async_query: bool,
            up_to_version: Optional[int],
            conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._perform_assets_updates,
                up_to_version=up_to_version,
                conflicts=conflicts,
            )

        response = self._perform_assets_updates(up_to_version, conflicts)
        return api_response(
            result={'result': response['result'], 'message': response['message']},
            status_code=response.get('status_code', HTTPStatus.OK),
        )

    def get_all_binance_pairs(self, location: Location) -> Response:
        # pylint: disable=no-self-use
        try:
            pairs = list(query_binance_exchange_pairs(location=location).keys())
        except InputError as e:
            return api_response(
                wrap_in_fail_result(
                    f'Failed to handle binance markets internally. {str(e)}',
                    status_code=HTTPStatus.BAD_GATEWAY,
                ),
            )
        if len(pairs) == 0:
            return api_response(
                wrap_in_fail_result(
                    'Failed to query binance pairs both from database and the binance API.',
                    status_code=HTTPStatus.BAD_GATEWAY,
                ),
            )
        return api_response(_wrap_in_ok_result(list(pairs)), status_code=HTTPStatus.OK)

    def get_user_binance_pairs(self, name: str, location: Location) -> Response:
        return api_response(
            _wrap_in_ok_result(
                self.rotkehlchen.exchange_manager.get_user_binance_pairs(name, location),
            ),
            status_code=HTTPStatus.OK,
        )

    def add_manual_price(  # pylint: disable=no-self-use
        self,
        from_asset: Asset,
        to_asset: Asset,
        price: Price,
        timestamp: Timestamp,
    ) -> Response:
        historical_price = HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=timestamp,
            price=price,
        )
        added = GlobalDBHandler().add_single_historical_price(historical_price)
        if added:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)
        return api_response(
            result={'result': False, 'message': 'Failed to store manual price'},
            status_code=HTTPStatus.CONFLICT,
        )

    def edit_manual_price(  # pylint: disable=no-self-use
        self,
        from_asset: Asset,
        to_asset: Asset,
        price: Price,
        timestamp: Timestamp,
    ) -> Response:
        historical_price = HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=timestamp,
            price=price,
        )
        edited = GlobalDBHandler().edit_manual_price(historical_price)
        if edited:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)
        return api_response(
            result={'result': False, 'message': 'Failed to edit manual price'},
            status_code=HTTPStatus.CONFLICT,
        )

    def get_manual_prices(  # pylint: disable=no-self-use
        self,
        from_asset: Optional[Asset],
        to_asset: Optional[Asset],
    ) -> Response:
        return api_response(
            _wrap_in_ok_result(GlobalDBHandler().get_manual_prices(from_asset, to_asset)),
            status_code=HTTPStatus.OK,
        )

    def delete_manual_price(  # pylint: disable=no-self-use
        self,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Response:
        deleted = GlobalDBHandler().delete_manual_price(from_asset, to_asset, timestamp)
        if deleted:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)
        return api_response(
            result={'result': False, 'message': 'Failed to delete manual price'},
            status_code=HTTPStatus.CONFLICT,
        )

    def _get_avalanche_transactions(
            self,
            address: ChecksumEvmAddress,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        avalanche = self.rotkehlchen.chains_aggregator.avalanche
        try:
            response = avalanche.covalent.get_transactions(
                account=address,
                from_ts=from_timestamp,
                to_ts=to_timestamp,
            )
        except RemoteError as e:
            return {
                'result': [],
                'message': f'{str(e)}',
                'status_code': HTTPStatus.BAD_GATEWAY,
            }
        if response is None:
            return {
                'result': [],
                'message': 'Not found.',
                'status_code': HTTPStatus.NOT_FOUND,
            }

        entries_result = []
        for transaction in response:
            entries_result.append(transaction.serialize())

        result = {
            'entries': entries_result,
            'entries_found': len(entries_result),
        }
        msg = ''
        return {'result': result, 'message': msg, 'status_code': HTTPStatus.OK}

    def get_avalanche_transactions(
            self,
            async_query: bool,
            address: ChecksumEvmAddress,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_avalanche_transactions,
                address=address,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        response = self._get_avalanche_transactions(
            address=address,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        result = response['result']
        if len(result) == 0:
            return api_response(
                wrap_in_fail_result('Not found.'),
                status_code=HTTPStatus.NOT_FOUND,
            )

        msg = response['message']
        status_code = _get_status_code_from_async_response(response)

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=status_code)

    def get_nfts(self, async_query: bool, ignore_cache: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module_name='nfts',
            method='get_all_info',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
            ignore_cache=ignore_cache,
        )

    def _get_nfts_balances(
            self,
            filter_query: NFTFilterQuery,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        if ignore_cache is True:
            uniswap_result = self._eth_module_query(
                module_name='uniswap',
                method='get_v3_balances',
                query_specific_balances_before=None,
                addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('uniswap'),  # noqa: E501
            )
            self._eth_module_query(
                module_name='nfts',
                method='query_balances',
                query_specific_balances_before=None,
                addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
                uniswap_nfts=uniswap_result['result'],
            )

        return self._eth_module_query(
            module_name='nfts',
            method='get_db_nft_balances',
            query_specific_balances_before=None,
            filter_query=filter_query,
        )

    def get_nfts_balances(
            self,
            async_query: bool,
            ignore_cache: bool,
            filter_query: NFTFilterQuery,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_nfts_balances,
                ignore_cache=ignore_cache,
                filter_query=filter_query,
            )

        response = self._get_nfts_balances(ignore_cache=ignore_cache, filter_query=filter_query)
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def get_manual_latest_prices(
            self,
            from_asset: Optional[Asset],
            to_asset: Optional[Asset],
    ) -> Response:
        prices = GlobalDBHandler().get_all_manual_latest_prices(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        prices_information = []
        for price_entry in prices:
            prices_information.append({
                'from_asset': price_entry[0],
                'to_asset': price_entry[1],
                'price': price_entry[2],
            })

        if (nft_module := self.rotkehlchen.chains_aggregator.get_module('nfts')) is not None:
            # query also nfts manual prices
            nft_price_data = nft_module.get_nfts_with_price(
                from_asset=from_asset,
                to_asset=to_asset,
                only_with_manual_prices=True,
            )

            for nft_data in nft_price_data:
                prices_information.append({
                    'from_asset': nft_data['asset'],
                    'to_asset': nft_data['price_asset'],
                    'price': nft_data['price_in_asset'],
                })

        return api_response(_wrap_in_ok_result(prices_information), status_code=HTTPStatus.OK)

    def get_nfts_with_price(self, lps_handling: NftLpHandling) -> Response:
        return self._api_query_for_eth_module(
            async_query=False,
            module_name='nfts',
            method='get_nfts_with_price',
            query_specific_balances_before=None,
            lps_handling=lps_handling,
        )

    def add_manual_latest_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> Response:
        if from_asset.is_nft():
            return self._api_query_for_eth_module(
                async_query=False,
                module_name='nfts',
                method='add_nft_with_price',
                query_specific_balances_before=None,
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        try:
            pairs_to_invalidate = GlobalDBHandler().add_manual_latest_price(
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(message=str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        Inquirer().remove_cache_prices_for_asset(pairs_to_invalidate)

        return api_response(result=OK_RESULT)

    def delete_manual_latest_price(
            self,
            asset: Asset,
    ) -> Response:
        if asset.is_nft():
            return self._api_query_for_eth_module(
                async_query=False,
                module_name='nfts',
                method='delete_price_for_nft',
                query_specific_balances_before=None,
                asset=asset,
            )
        try:
            pairs_to_invalidate = GlobalDBHandler().delete_manual_latest_price(asset=asset)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(message=str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        Inquirer().remove_cache_prices_for_asset(pairs_to_invalidate)

        return api_response(result=OK_RESULT)

    def get_database_info(self) -> Response:
        globaldb_schema_version = GlobalDBHandler().get_schema_version()
        globaldb_assets_version = GlobalDBHandler().get_setting_value(ASSETS_VERSION_KEY, 0)
        result_dict = {
            'globaldb': {
                'globaldb_schema_version': globaldb_schema_version,
                'globaldb_assets_version': globaldb_assets_version,
            },
            'userdb': {},
        }
        if self.rotkehlchen.user_is_logged_in:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                result_dict['userdb']['info'] = self.rotkehlchen.data.db.get_db_info(cursor)  # type: ignore  # noqa: E501
            result_dict['userdb']['backups'] = []  # type: ignore
            backups = self.rotkehlchen.data.db.get_backups()
            for entry in backups:
                result_dict['userdb']['backups'].append(entry)  # type: ignore

        return api_response(_wrap_in_ok_result(result_dict), status_code=HTTPStatus.OK)

    def create_database_backup(self) -> Response:
        try:
            db_backup_path = self.rotkehlchen.data.db.create_db_backup()
        except OSError as e:
            error_msg = f'Failed to create a DB backup due to {str(e)}'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(str(db_backup_path)), status_code=HTTPStatus.OK)

    def download_database_backup(self, filepath: Path) -> Response:
        if filepath.parent != self.rotkehlchen.data.db.user_data_dir:
            error_msg = f'DB backup file {filepath} is not in the user directory'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        return send_file(
            path_or_file=filepath,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filepath.name,
        )

    def delete_database_backups(self, files: list[Path]) -> Response:
        for filepath in files:
            if filepath.parent != self.rotkehlchen.data.db.user_data_dir:
                error_msg = f'DB backup file {filepath} is not in the user directory'
                return api_response(
                    result=wrap_in_fail_result(error_msg),
                    status_code=HTTPStatus.CONFLICT,
                )
        for filepath in files:
            filepath.unlink()  # should not raise file not found as marshmallow should check
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def purge_pnl_report_data(self, report_id: int) -> Response:
        dbreports = DBAccountingReports(self.rotkehlchen.data.db)
        try:
            dbreports.purge_report_data(report_id=report_id)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_pnl_reports(
            self,
            report_id: Optional[int],
    ) -> Response:
        with_limit = False
        entries_limit = -1
        if self.rotkehlchen.premium is None:
            with_limit = True
            entries_limit = FREE_REPORTS_LOOKUP_LIMIT

        dbreports = DBAccountingReports(self.rotkehlchen.data.db)
        reports, entries_found = dbreports.get_reports(
            report_id=report_id,
            with_limit=with_limit,
        )

        # success
        result_dict = _wrap_in_ok_result({
            'entries': reports,
            'entries_found': entries_found,
            'entries_limit': entries_limit,
        })
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def get_report_data(self, filter_query: ReportDataFilterQuery) -> Response:
        with_limit = False
        entries_limit = -1
        if self.rotkehlchen.premium is None:
            with_limit = True
            entries_limit = FREE_PNL_EVENTS_LIMIT
        dbreports = DBAccountingReports(self.rotkehlchen.data.db)
        try:
            report_data, entries_found = dbreports.get_report_data(
                filter_=filter_query,
                with_limit=with_limit,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        result = {
            'entries': [x.to_exported_dict(
                ts_converter=self.rotkehlchen.accountant.pots[0].timestamp_to_date,
                eth_explorer=None,
                for_api=True,
            ) for x in report_data],
            'entries_found': entries_found,
            'entries_limit': entries_limit,
        }
        result_dict = _wrap_in_result(result, '')
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def get_associated_locations(self) -> Response:
        locations = self.rotkehlchen.data.db.get_associated_locations()
        return api_response(
            result=_wrap_in_ok_result([str(location) for location in locations]),
            status_code=HTTPStatus.OK,
        )

    def _query_kraken_staking_events(
            self,
            only_cache: bool,
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        history_events_db = DBHistoryEvents(self.rotkehlchen.data.db)
        table_filter = HistoryEventFilterQuery.make(
            location=Location.KRAKEN,
            event_types=[
                HistoryEventType.STAKING,
            ],
            exclude_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ],
        )

        message = ''
        entries_limit = -1
        if self.rotkehlchen.premium is None:
            entries_limit = FREE_HISTORY_EVENTS_LIMIT

        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(
            Location.KRAKEN,
        )
        if exchanges_list is None:
            return wrap_in_fail_result(
                message='There is no kraken account added.',
                status_code=HTTPStatus.CONFLICT,
            )

        # After 3865 we have a recurring task that queries for missing prices but
        # we make sure that the returned values have their correct value calculated
        task_manager = self.rotkehlchen.task_manager
        if task_manager is not None:
            try:
                entries = task_manager.get_base_entries_missing_prices(query_filter)
                task_manager.query_missing_prices_of_base_entries(
                    entries_missing_prices=entries,
                )
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                return wrap_in_fail_result(
                    message=f'Database query error retrieving misssing prices {str(e)}',
                    status_code=HTTPStatus.CONFLICT,
                )

        # Query events from database
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            events_raw, entries_found = self.rotkehlchen.events_historian.query_history_events(
                cursor=cursor,
                filter_query=query_filter,
                only_cache=only_cache,
            )
            events = []
            for event in events_raw:
                try:
                    staking_event = StakingEvent.from_history_base_entry(event)
                except DeserializationError as e:
                    log.warning(f'Could not deserialize staking event: {event} due to {str(e)}')
                    continue
                events.append(staking_event)

            entries_total = history_events_db.get_history_events_count(cursor=cursor, query_filter=table_filter)  # noqa: E501
            usd_value, amounts = history_events_db.get_value_stats(cursor=cursor, query_filter=value_filter)  # noqa: E501

            result = {
                'events': events,
                'entries_found': entries_found,
                'entries_limit': entries_limit,
                'entries_total': entries_total,
                'total_usd_value': usd_value,
                'assets': history_events_db.get_entries_assets_history_events(
                    cursor=cursor,
                    query_filter=table_filter,
                ),
                'received': [
                    {
                        'asset': entry[0].identifier,
                        'amount': entry[1],
                        'usd_value': entry[2],
                    } for entry in amounts
                ],
            }

        return {'result': result, 'message': message, 'status_code': HTTPStatus.OK}

    def query_kraken_staking_events(
            self,
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
            only_cache: bool,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._query_kraken_staking_events,
                only_cache=only_cache,
                query_filter=query_filter,
                value_filter=value_filter,
            )

        response = self._query_kraken_staking_events(
            only_cache=only_cache,
            query_filter=query_filter,
            value_filter=value_filter,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def get_user_added_assets(self, path: Optional[Path]) -> Response:
        """
        Creates a zip file with the list of assets added by the user. If path is not None the zip
        file is saved in that folder and a json response including the path is returned.
        If path is None the zip file is returned with header application/zip
        """
        try:
            zip_path = export_assets_from_file(
                dirpath=path,
                db_handler=self.rotkehlchen.data.db,
            )
        except PermissionError as e:
            return api_response(
                result=wrap_in_fail_result(f'Failed to create asset export file. {str(e)}'),
                status_code=HTTPStatus.INSUFFICIENT_STORAGE,
            )

        if path is None:
            return send_file(
                path_or_file=zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='assets.zip',
            )

        return api_response(
            _wrap_in_ok_result({'file': str(zip_path)}),
            status_code=HTTPStatus.OK,
        )

    def import_user_assets(self, path: Path) -> Response:
        try:
            if path.suffix == '.json':
                import_assets_from_file(
                    path=path,
                    msg_aggregator=self.rotkehlchen.msg_aggregator,
                    db_handler=self.rotkehlchen.data.db,
                )
            else:
                zip_file = ZipFile(path)
                with tempfile.TemporaryDirectory() as tempdir:
                    for file_name in zip_file.namelist():
                        if file_name.endswith('.json'):
                            zip_file.extract(file_name, tempdir)
                            file_path = Path(tempdir) / file_name
                            import_assets_from_file(
                                path=file_path,
                                msg_aggregator=self.rotkehlchen.msg_aggregator,
                                db_handler=self.rotkehlchen.data.db,
                            )
        except ValidationError as e:
            return api_response(
                result=wrap_in_fail_result(
                    f'Provided file does not have the expected format. {str(e)}',
                ),
                status_code=HTTPStatus.CONFLICT,
            )
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(f'{str(e)}'),
                status_code=HTTPStatus.CONFLICT,
            )

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            balances = dbsnapshot.get_timed_balances(cursor, timestamp=timestamp)
            location_data = dbsnapshot.get_timed_location_data(cursor, timestamp=timestamp)
        if len(balances) == 0 or len(location_data) == 0:
            return api_response(
                wrap_in_fail_result('No snapshot data found for the given timestamp.'),
                status_code=HTTPStatus.NOT_FOUND,
            )

        serialized_balances = [entry.serialize() for entry in balances]
        serialized_location_data = [entry.serialize() for entry in location_data]
        result_dict = _wrap_in_result(
            result={
                'balances_snapshot': serialized_balances,
                'location_data_snapshot': serialized_location_data,
            },
            message='',
        )
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_user_db_snapshot(
            self,
            timestamp: Timestamp,
            location_data_snapshot: list[LocationData],
            balances_snapshot: list[DBAssetBalance],
    ) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                dbsnapshot.update(
                    write_cursor=cursor,
                    timestamp=timestamp,
                    balances_snapshot=balances_snapshot,
                    location_data_snapshot=location_data_snapshot,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def export_user_db_snapshot(self, timestamp: Timestamp, path: Path) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        is_success, message = dbsnapshot.export(timestamp=timestamp, directory_path=path)
        if is_success is False:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def download_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        is_success, zipfile_path = dbsnapshot.export(timestamp, directory_path=None)
        if is_success is False:
            return api_response(wrap_in_fail_result('Could not create a zip archive'), status_code=HTTPStatus.CONFLICT)  # noqa: E501

        try:
            return send_file(
                path_or_file=zipfile_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='snapshot.zip',
            )
        except FileNotFoundError:
            return api_response(
                wrap_in_fail_result('No file was found'),
                status_code=HTTPStatus.NOT_FOUND,
            )

    def delete_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                dbsnapshot.delete(
                    write_cursor=write_cursor,
                    timestamp=timestamp,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_ens_mappings(
            self,
            addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
    ) -> dict[str, Any]:
        mappings_to_send: dict[ChecksumEvmAddress, str] = {}
        try:
            mappings_to_send = find_ens_mappings(
                ethereum_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
                addresses=addresses,
                ignore_cache=ignore_cache,
            )
        except RemoteError as e:
            return wrap_in_fail_result(message=str(e), status_code=HTTPStatus.CONFLICT)

        return {'result': mappings_to_send, 'message': '', 'status_code': HTTPStatus.OK}

    def get_ens_mappings(
            self,
            addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
            async_query: bool,
    ) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._get_ens_mappings,
                addresses=addresses,
                ignore_cache=ignore_cache,
            )

        response = self._get_ens_mappings(
            addresses=addresses,
            ignore_cache=ignore_cache,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def import_user_snapshot(
            self,
            balances_snapshot_file: Path,
            location_data_snapshot_file: Path,
    ) -> Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        error_or_empty, processed_balances, processed_location_data = parse_import_snapshot_data(
            balances_snapshot_file=balances_snapshot_file,
            location_data_snapshot_file=location_data_snapshot_file,
        )
        if error_or_empty != '':
            return api_response(
                result=wrap_in_fail_result(error_or_empty),
                status_code=HTTPStatus.CONFLICT,
            )
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                dbsnapshot.import_snapshot(
                    write_cursor=write_cursor,
                    processed_balances_list=processed_balances,
                    processed_location_data_list=processed_location_data,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _pull_spam_assets(self) -> dict[str, Any]:
        try:
            assets_updated = update_spam_assets(
                db=self.rotkehlchen.data.db,
                make_remote_query=True,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        return {'result': assets_updated, 'message': '', 'status_code': HTTPStatus.OK}

    def pull_spam_assets(self, async_query: bool) -> Response:
        if async_query is True:
            return self._query_async(
                command=self._pull_spam_assets,
            )
        response_result = self._pull_spam_assets()
        return api_response(result=response_result, status_code=response_result['status_code'])

    def get_all_counterparties(self) -> Response:
        return api_response(
            result={
                # Converting to list since set is not json serializable
                'result': list(self.rotkehlchen.chains_aggregator.ethereum.transactions_decoder.rules.all_counterparties),  # noqa: E501
                'message': '',
            },
        )

    def get_addressbook_entries(
            self,
            book_type: AddressbookType,
            chain_addresses: Optional[list[OptionalChainAddress]],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        with db_addressbook.read_ctx(book_type) as cursor:
            entries = db_addressbook.get_addressbook_entries(
                cursor=cursor,
                optional_chain_addresses=chain_addresses,
            )
        serialized = [entry.serialize() for entry in entries]
        return api_response(_wrap_in_ok_result(serialized))

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.add_addressbook_entries(book_type=book_type, entries=entries)
            return api_response(result=OK_RESULT)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.update_addressbook_entries(book_type=book_type, entries=entries)
            return api_response(result=OK_RESULT)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            chain_addresses: list[OptionalChainAddress],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.delete_addressbook_entries(
                book_type=book_type,
                chain_addresses=chain_addresses,
            )
            return api_response(result=OK_RESULT)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )

    def search_for_names_everywhere(
            self,
            chain_addresses: list[OptionalChainAddress],
    ) -> Response:
        mappings = search_for_addresses_names(
            database=self.rotkehlchen.data.db,
            chain_addresses=chain_addresses,
        )
        return api_response(_wrap_in_ok_result(process_result_list(mappings)))

    def _detect_evm_tokens(
            self,
            only_cache: bool,
            addresses: list[ChecksumEvmAddress],
            manager: EvmManager,
    ) -> dict[str, Any]:
        try:
            account_tokens_info = manager.tokens.detect_tokens(
                only_cache=only_cache,
                addresses=addresses,
            )
        except (RemoteError, BadFunctionCallOutput) as e:
            return wrap_in_fail_result(message=str(e), status_code=HTTPStatus.CONFLICT)

        result = {}
        for account, (tokens, last_update_ts) in account_tokens_info.items():
            result[account] = {
                'tokens': [token.identifier for token in tokens] if tokens is not None else None,
                'last_update_timestamp': last_update_ts,
            }
        return {
            'result': result,
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def detect_evm_tokens(
            self,
            async_query: bool,
            only_cache: bool,
            addresses: Optional[list[ChecksumEvmAddress]],
            blockchain: SUPPORTED_EVM_CHAINS,
    ) -> Response:
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)
        if addresses is None:
            addresses = self.rotkehlchen.chains_aggregator.accounts.get(blockchain)
        if async_query is True:
            return self._query_async(
                command=self._detect_evm_tokens,
                only_cache=only_cache,
                addresses=addresses,
                manager=manager,
            )

        response = self._detect_evm_tokens(
            only_cache=only_cache,
            addresses=addresses,
            manager=manager,
        )
        status_code = _get_status_code_from_async_response(response)
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=status_code)

    def get_config_arguments(self) -> Response:
        config = {
            'max_size_in_mb_all_logs': {
                'value': self.rotkehlchen.args.max_size_in_mb_all_logs,
                'is_default': self.rotkehlchen.args.max_size_in_mb_all_logs == DEFAULT_MAX_LOG_SIZE_IN_MB,  # noqa: E501
            },
            'max_logfiles_num': {
                'value': self.rotkehlchen.args.max_logfiles_num,
                'is_default': self.rotkehlchen.args.max_logfiles_num == DEFAULT_MAX_LOG_BACKUP_FILES,  # noqa: E501
            },
            'sqlite_instructions': {
                'value': self.rotkehlchen.args.sqlite_instructions,
                'is_default': self.rotkehlchen.args.sqlite_instructions == DEFAULT_SQL_VM_INSTRUCTIONS_CB,  # noqa: E501
            },
        }
        return api_response(_wrap_in_ok_result(config), status_code=HTTPStatus.OK)

    def get_user_notes(self, filter_query: UserNotesFilterQuery) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            user_notes, entries_found = self.rotkehlchen.data.db.get_user_notes_and_limit_info(
                filter_query=filter_query,
                cursor=cursor,
                has_premium=self.rotkehlchen.premium is not None,
            )
            user_notes_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='user_notes',
            )
        entries = [entry.serialize() for entry in user_notes]
        result = {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': user_notes_total,
            'entries_limit': FREE_USER_NOTES_LIMIT if self.rotkehlchen.premium is None else -1,
        }
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def add_user_note(
            self,
            title: str,
            content: str,
            location: str,
            is_pinned: bool,
    ) -> Response:
        try:
            note_id = self.rotkehlchen.data.db.add_user_note(
                title=title,
                content=content,
                location=location,
                is_pinned=is_pinned,
                has_premium=self.rotkehlchen.premium is not None,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(result={'result': note_id, 'message': ''}, status_code=HTTPStatus.OK)

    def edit_user_note(self, user_note: UserNote) -> Response:
        try:
            self.rotkehlchen.data.db.edit_user_note(user_note=user_note)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_user_note(self, identifier: int) -> Response:
        try:
            self.rotkehlchen.data.db.delete_user_note(identifier=identifier)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_custom_assets(self, filter_query: CustomAssetsFilterQuery) -> Response:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        custom_assets_result, entries_found, entries_total = db_custom_assets.get_custom_assets_and_limit_info(  # noqa: E501
            filter_query=filter_query,
        )
        entries = [entry.to_dict() for entry in custom_assets_result]
        result = {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': entries_total,
        }
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def add_custom_asset(self, custom_asset: CustomAsset) -> Response:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        try:
            identifier = db_custom_assets.add_custom_asset(custom_asset=custom_asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        return api_response(_wrap_in_ok_result(identifier), status_code=HTTPStatus.OK)

    def edit_custom_asset(self, custom_asset: CustomAsset) -> Response:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        try:
            db_custom_assets.edit_custom_asset(custom_asset=custom_asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver to requery DB
        AssetResolver().assets_cache.remove(custom_asset.identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_custom_asset_types(self) -> Response:
        db_custom_assets = DBCustomAssets(db_handler=self.rotkehlchen.data.db)
        custom_asset_types = db_custom_assets.get_custom_asset_types()
        return api_response(_wrap_in_ok_result(custom_asset_types), status_code=HTTPStatus.OK)

    def get_event_details(self, identifier: int) -> Response:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        event = dbevents.get_history_event_by_identifier(identifier=identifier)
        if event is None:
            return api_response(wrap_in_fail_result('No event found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        details = event.get_details()
        if details is None:
            return api_response(wrap_in_fail_result('No details found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        return api_response(_wrap_in_ok_result(details), status_code=HTTPStatus.OK)
