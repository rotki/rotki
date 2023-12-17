import datetime
import json
import logging
import os
import sys
import tempfile
import traceback
from collections import defaultdict
from collections.abc import Callable, Sequence
from functools import reduce
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, cast, get_args, overload
from zipfile import BadZipFile, ZipFile

import gevent
from flask import Response, make_response, send_file
from gevent.event import Event
from gevent.lock import Semaphore
from marshmallow.exceptions import ValidationError
from pysqlcipher3 import dbapi2 as sqlcipher
from web3.exceptions import BadFunctionCallOutput
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.constants import (
    ACCOUNTING_EVENTS_ICONS,
    EVENT_CATEGORY_DETAILS,
    EVENT_CATEGORY_MAPPINGS,
    FREE_PNL_EVENTS_LIMIT,
    FREE_REPORTS_LOOKUP_LIMIT,
)
from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.accounting.export.csv import (
    FILENAME_HISTORY_EVENTS_CSV,
    FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV,
    CSVWriteError,
    dict_to_csv_file,
)
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntryType,
    StakingEvent,
    get_event_type_identifier,
)
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.processed_event import AccountingEventExportType
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.api.v1.schemas import TradeSchema
from rotkehlchen.api.v1.types import EvmTransactionDecodingApiData, IncludeExcludeFilterData
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
    FiatAsset,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import ASSET_TYPES_EXCLUDED_FOR_USERS, AssetType
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
    get_manually_tracked_balances,
    remove_manually_tracked_balances,
)
from rotkehlchen.chain.accounts import SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.airdrops import AIRDROPS, check_airdrops
from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    save_convex_data_to_cache,
)
from rotkehlchen.chain.ethereum.modules.curve.curve_cache import (
    query_curve_data,
    save_curve_data_to_cache,
)
from rotkehlchen.chain.ethereum.modules.eth2.constants import FREE_VALIDATORS_LIMIT
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.ethereum.modules.liquity.statistics import get_stats as get_liquity_stats
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import try_download_ens_avatar
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.chain.evm.names import find_ens_mappings, search_for_addresses_names
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.optimism.modules.velodrome.velodrome_cache import (
    query_velodrome_data,
    save_velodrome_data_to_cache,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.limits import (
    FREE_ASSET_MOVEMENTS_LIMIT,
    FREE_ETH_TX_LIMIT,
    FREE_HISTORY_EVENTS_LIMIT,
    FREE_TRADES_LIMIT,
    FREE_USER_NOTES_LIMIT,
)
from rotkehlchen.constants.misc import (
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    HTTP_STATUS_INTERNAL_DB_ERROR,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.constants.timing import ENS_AVATARS_REFRESH
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.accounting_rules import DBAccountingRules, query_missing_accounting_rules
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    AccountingRulesFilterQuery,
    AddressbookFilterQuery,
    AssetMovementsFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    DBFilterQuery,
    Eth2DailyStatsFilterQuery,
    EthStakingEventFilterQuery,
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
    LevenshteinFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.snapshots import DBSnapshot
from rotkehlchen.db.unresolved_conflicts import DBRemoteConflicts
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
    AlreadyExists,
    DBSchemaError,
    DBUpgradeError,
    EthSyncError,
    GreenletKilledError,
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
from rotkehlchen.externalapis.github import Github
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.assets_management import export_assets_from_file, import_assets_from_file
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.updates import ASSETS_VERSION_KEY
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.skipped import (
    export_skipped_external_events,
    get_skipped_external_events_summary,
    reprocess_skipped_external_events,
)
from rotkehlchen.history.types import NOT_EXPOSED_SOURCES, HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.icons import (
    check_if_image_is_cached,
    create_image_response,
    maybe_create_image_response,
)
from rotkehlchen.inquirer import CurrentPriceOracle, Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.tasks.utils import query_missing_prices_of_base_entries
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_LOCATIONS,
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
    CacheType,
    ChecksumEvmAddress,
    Eth2PubKey,
    EVMTxHash,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    HistoryEventQueryType,
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
from rotkehlchen.utils.misc import combine_dicts, ts_now
from rotkehlchen.utils.snapshots import parse_import_snapshot_data
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.base import HistoryBaseEntry
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.manager import EvmManager
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


def wrap_in_fail_result(message: str, status_code: HTTPStatus | None = None) -> dict[str, Any]:
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


def make_response_from_dict(response_data: dict[str, Any]) -> Response:
    result = response_data.get('result')
    message = response_data.get('message', '')
    status_code = response_data.get('status_code', HTTPStatus.OK)
    return api_response(
        result=process_result(_wrap_in_result(result=result, message=message)),
        status_code=status_code,
    )


def async_api_call() -> Callable:
    """
    This is a decorator that should be used with endpoints that can be called asynchronously.
    It reads `async_query` argument from the wrapped function to determine whether to call
    asynchronously or not. Defaults to synchronous mode.

    Endpoints that it wraps must return a dictionary with result, message and optionally a
    status code.
    This decorator reads the dictionary and transforms it to a Reponse object.
    """
    def wrapper(func: Callable[..., dict[str, Any]]) -> Callable[..., Response]:
        def inner(rest_api: 'RestAPI', async_query: bool = False, **kwargs: Any) -> Response:
            response: dict[str, Any]
            if async_query is True:
                return rest_api._query_async(
                    command=func,
                    **kwargs,
                )

            response = func(rest_api, **kwargs)
            return make_response_from_dict(response)

        return inner
    return wrapper


def login_lock() -> Callable:
    """
    This is a decorator that uses the login lock at RestAPI to avoid a race condition between
    async tasks using the user unlock logic.
    """
    def wrapper(func: Callable[..., Response]) -> Callable[..., Response]:
        def inner(rest_api: 'RestAPI', **kwargs: Any) -> Response:
            with rest_api.login_lock:
                return func(rest_api, **kwargs)
        return inner
    return wrapper


class RestAPI:
    """ The Object holding the logic that runs inside all the API calls"""
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self._handle_killed_greenlets)
        # Greenlets that will be waited for when we shutdown (just main loop)
        self.waited_greenlets = [mainloop_greenlet]
        self.task_lock = Semaphore()
        self.login_lock = Semaphore()
        self.task_id = 0
        self.task_results: dict[int, Any] = {}
        self.trade_schema = TradeSchema()

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

        if isinstance(greenlet.exception, GreenletKilledError):
            log.debug(
                f'Greenlet for task id {task_id} with name {task_str} was killed. '
                f'{greenlet.exception!s}',
            )
            # Setting empty message to signify that the death of the greenlet is expected.
            self._write_task_result(task_id, {'result': None, 'message': ''})
            return

        log.error(
            f'{task_str} dies with exception: {greenlet.exception}.\n'
            f'Exception Name: {greenlet.exc_info[0]}\n'
            f'Exception Info: {greenlet.exc_info[1]}\n'
            f'Traceback:\n {"".join(traceback.format_tb(greenlet.exc_info[2]))}',
        )
        # also write an error for the task result if it's not the main greenlet
        if task_id is not None:
            result = {
                'result': None,
                'message': f'The backend query task died unexpectedly: {greenlet.exception!s}',
            }
            self._write_task_result(task_id, result)

    def _do_query_async(self, command: Callable, task_id: int, **kwargs: Any) -> None:
        log.debug(f'Async task with task id {task_id} started')
        result = command(self, **kwargs)
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

    def query_tasks_outcome(self, task_id: int | None) -> Response:
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

    @async_api_call()
    def get_exchange_rates(self, given_currencies: list[AssetWithOracles]) -> dict[str, Any]:
        currencies = given_currencies
        fiat_currencies: list[FiatAsset] = []
        asset_rates = {}
        for asset in currencies:
            if asset.is_fiat():
                fiat_currencies.append(asset.resolve_to_fiat_asset())
                continue

            usd_price = Inquirer().find_usd_price(asset)
            if usd_price == ZERO_PRICE:
                asset_rates[asset] = ZERO_PRICE
            else:
                asset_rates[asset] = Price(ONE / usd_price)

        asset_rates.update(Inquirer().get_fiat_usd_exchange_rates(fiat_currencies))  # type: ignore  # type narrowing does not work here
        return _wrap_in_ok_result(process_result(asset_rates))

    @async_api_call()
    def query_all_balances(
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

    def _return_external_services_response(self) -> Response:
        credentials_list = self.rotkehlchen.data.db.get_all_external_service_credentials()
        response_dict: dict[str, dict[str, ApiKey] | dict[str, dict[str, ApiKey]]] = {}
        for credential in credentials_list:
            name = credential.service.name.lower()
            key_info = {'api_key': credential.api_key}
            if (chain := credential.service.get_chain_for_etherscan()) is not None:
                if 'etherscan' not in response_dict:
                    response_dict['etherscan'] = cast(dict[str, dict[str, ApiKey]], {})
                response_dict['etherscan'][chain.to_name()] = key_info  # type: ignore  # mypy fails to understand that this is the second branch on the union type defined before
            else:
                response_dict[name] = key_info

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
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: list[str] | None,
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
        )
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT

        return api_response(_wrap_in_result(result, msg), status_code=status_code)

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: list[str] | None,
    ) -> Response:
        edited, msg = self.rotkehlchen.exchange_manager.edit_exchange(
            name=name,
            location=location,
            new_name=new_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            binance_selected_trade_pairs=binance_markets,
        )
        result: bool | None = True
        status_code = HTTPStatus.OK
        if not edited:
            result = None
            status_code = HTTPStatus.CONFLICT

        return api_response(_wrap_in_result(result, msg), status_code=status_code)

    def remove_exchange(self, name: str, location: Location) -> Response:
        result: bool | None
        result, message = self.rotkehlchen.exchange_manager.delete_exchange(
            name=name,
            location=location,
        )
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

    @async_api_call()
    def query_exchange_balances(self, location: Location | None, ignore_cache: bool) -> dict[str, Any]:  # noqa: E501
        if location is None:
            # Query all exchanges
            return self._query_all_exchange_balances(ignore_cache=ignore_cache)

        # else query only the specific exchange
        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return {
                'result': None,
                'message': f'Could not query balances for {location!s} since it is not registered',
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

    def get_supported_chains(self) -> Response:
        result = []
        for blockchain in SupportedBlockchain:
            data = {
                'id': blockchain.serialize(),
                'name': str(blockchain),
                'type': blockchain.get_chain_type(),
                'native_token': blockchain.get_native_token_id(),
                'image': blockchain.get_image_name(),
            }
            if blockchain.is_evm() is True:
                data['evm_chain_name'] = blockchain.to_chain_id().to_name()
            result.append(data)

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @async_api_call()
    def query_blockchain_balances(
            self,
            blockchain: SupportedBlockchain | None,
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

    @async_api_call()
    def get_trades(
            self,
            only_cache: bool,
            filter_query: TradesFilterQuery,
            include_ignored_trades: bool,
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
            ignored_ids = mapping.get(ActionType.TRADE, set())
            entries_result = []
            for entry in trades_result:
                is_trade_ignored = entry['trade_id'] in ignored_ids
                if include_ignored_trades is False and is_trade_ignored is True:
                    continue

                entries_result.append(
                    {'entry': entry, 'ignored_in_accounting': is_trade_ignored},
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

    def add_trade(
            self,
            timestamp: Timestamp,
            location: Location,
            base_asset: Asset,
            quote_asset: Asset,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee | None,
            fee_currency: Asset | None,
            link: str | None,
            notes: str | None,
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
            fee: Fee | None,
            fee_currency: Asset | None,
            link: str | None,
            notes: str | None,
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

    @async_api_call()
    def get_asset_movements(
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
            ignored_ids = mapping.get(ActionType.ASSET_MOVEMENT, set())
            entries_result = [{
                'entry': x,
                'ignored_in_accounting': x['identifier'] in ignored_ids,
            } for x in serialized_movements]
            result = {
                'entries': entries_result,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor, 'asset_movements'),  # noqa: E501
                'entries_found': filter_total_found,
                'entries_limit': limit,
            }

        return {'result': result, 'message': msg, 'status_code': status_code}

    def add_history_event(self, event: 'HistoryBaseEntry') -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.user_write() as cursor:
            try:
                identifier = db.add_history_event(
                    write_cursor=cursor,
                    event=event,
                    mapping_values={
                        HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED,
                    },
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                error_msg = f'Failed to add event to the DB due to a DB error: {e!s}'
                return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)  # noqa: E501

        if identifier is None:
            error_msg = 'Failed to add event to the DB. It already exists'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        # success
        result_dict = _wrap_in_ok_result({'identifier': identifier})
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_history_event(self, event: 'HistoryBaseEntry') -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        result, msg = db.edit_history_event(event)
        if result is False:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_history_events(self, identifiers: list[int], force_delete: bool) -> Response:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        error_msg = db.delete_history_events_by_identifier(
            identifiers=identifiers,
            force_delete=force_delete,
        )
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
            description: str | None,
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
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
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
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
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

    @login_lock()
    @async_api_call()
    def create_new_user(
            self,
            name: str,
            password: str,
            premium_api_key: str,
            premium_api_secret: str,
            sync_database: bool,
            initial_settings: ModifiableDBSettings | None,
    ) -> dict[str, Any]:

        if self.rotkehlchen.user_is_logged_in:
            message = (
                f'Can not create a new user because user '
                f'{self.rotkehlchen.data.username} is already logged in. '
                f'Log out of that user first'
            )
            return {
                'result': None,
                'message': message,
                'status_code': HTTPStatus.CONFLICT,
            }

        if (
                premium_api_key != '' and premium_api_secret == '' or
                premium_api_secret != '' and premium_api_key == ''
        ):
            return {
                'result': None,
                'message': 'Must provide both or neither of api key/secret',
                'status_code': HTTPStatus.BAD_REQUEST,
            }

        premium_credentials = None
        if premium_api_key != '' and premium_api_secret != '':
            try:
                premium_credentials = PremiumCredentials(
                    given_api_key=premium_api_key,
                    given_api_secret=premium_api_secret,
                )
            except IncorrectApiKeyFormat:
                return {
                    'result': None,
                    'message': 'Provided API/Key secret format is invalid',
                    'status_code': HTTPStatus.BAD_REQUEST,
                }

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
                resume_from_backup=False,
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
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        # Success!
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = {
                'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchanges_info(),
                'settings': process_result(self.rotkehlchen.get_settings(cursor)),
            }
        return {
            'result': result,
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    @login_lock()
    @async_api_call()
    def user_login(
            self,
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
            resume_from_backup: bool,
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
                resume_from_backup=resume_from_backup,
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
                message=f'Unexpected database error: {e!s}',
                status_code=HTTP_STATUS_INTERNAL_DB_ERROR,  # type: ignore  # Is a custom status code, not a member of HTTPStatus
            )

        # Success!
        exchanges = self.rotkehlchen.exchange_manager.get_connected_exchanges_info()
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = process_result(self.rotkehlchen.get_settings(cursor))

        return _wrap_in_ok_result({
            'exchanges': exchanges,
            'settings': settings,
        })

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

        if current_password != self.rotkehlchen.data.db.password:
            result_dict['message'] = 'Provided current password is not correct'
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        success: bool
        try:
            success = self.rotkehlchen.data.db.change_password(new_password=new_password)
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

    def query_list_of_all_assets(self, filter_query: AssetsFilterQuery) -> Response:
        """Query assets using the provided filter_query and return them in a paginated format"""
        assets, assets_found = GlobalDBHandler().retrieve_assets(userdb=self.rotkehlchen.data.db, filter_query=filter_query)  # noqa: E501
        with GlobalDBHandler().conn.read_ctx() as cursor:
            assets_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='assets',
            )

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
            limit: int | None,
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

    def add_user_asset(self, asset: AssetWithOracles) -> Response:
        globaldb = GlobalDBHandler()
        # There is no good way to figure out if an asset already exists in the DB
        # Best approximation we can do is this.
        if isinstance(asset, EvmToken):
            try:
                asset.check_existence()  # for evm token we know the uniqueness of the identifier
                identifiers = [asset.identifier]
            except UnknownAsset:
                identifiers = None
        else:
            identifiers = globaldb.check_asset_exists(asset)

        if identifiers is not None:
            return api_response(
                result=wrap_in_fail_result(
                    f'Failed to add {asset.asset_type!s} {asset.name} '
                    f'since it already exists. Existing ids: {",".join(identifiers)}'),
                status_code=HTTPStatus.CONFLICT,
            )
        try:
            globaldb.add_asset(asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.user_write() as cursor:
            self.rotkehlchen.data.db.add_asset_identifiers(cursor, [asset.identifier])
        return api_response(
            _wrap_in_ok_result({'identifier': asset.identifier}),
            status_code=HTTPStatus.OK,
        )

    def edit_user_asset(self, asset: AssetWithOracles) -> Response:
        try:
            GlobalDBHandler().edit_user_asset(asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver to requery DB
        AssetResolver().assets_cache.remove(asset.identifier)
        # clear the icon cache in case the coingecko id was edited
        self.rotkehlchen.icon_manager.failed_asset_ids.remove(asset.identifier)
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
        # clear the icon cache in case the asset was there
        self.rotkehlchen.icon_manager.failed_asset_ids.remove(identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def replace_asset(self, source_identifier: str, target_asset: Asset) -> Response:
        try:
            self.rotkehlchen.data.db.replace_asset_identifier(source_identifier, target_asset)
        except (UnknownAsset, InputError) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Also clear the in-memory cache of the asset resolver
        AssetResolver().assets_cache.remove(source_identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @async_api_call()
    def rebuild_assets_information(
            self,
            reset: Literal['soft', 'hard'],
            ignore_warnings: bool,
    ) -> dict[str, Any]:
        msg = 'Invalid value for reset'
        if reset == 'soft':
            success, msg = GlobalDBHandler().soft_reset_assets_list()
        elif reset == 'hard':
            success, msg = GlobalDBHandler().hard_reset_assets_list(
                user_db=self.rotkehlchen.data.db,
                force=ignore_warnings,
            )

        if success:
            AssetResolver.clean_memory_cache()  # clean the cache after deleting any possible asset
            return _wrap_in_ok_result(OK_RESULT)
        return wrap_in_fail_result(msg, status_code=HTTPStatus.CONFLICT)

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
            asset: Asset | None,
            collection_id: int | None,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if asset is not None:
                # TODO: Think about this, but for now this is only balances, not liabilities
                data = self.rotkehlchen.data.db.query_timed_balances(
                    cursor=cursor,
                    from_ts=from_timestamp,
                    to_ts=to_timestamp,
                    asset=asset,
                    balance_type=BalanceType.ASSET,
                )
            else:  # marshmallow check guarantees collection_id exists
                data = self.rotkehlchen.data.db.query_collection_timed_balances(
                    cursor=cursor,
                    collection_id=collection_id,  # type: ignore  # collection_id exists here
                    from_ts=from_timestamp,
                    to_ts=to_timestamp,
                )

        result = process_result_list(data)
        return api_response(
            result=_wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    def query_value_distribution_data(self, distribution_by: str) -> Response:
        data: list[DBAssetBalance] | list[LocationData]
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

    @async_api_call()
    def process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        report_id, error_or_empty = self.rotkehlchen.process_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        return {'result': report_id, 'message': error_or_empty}

    @async_api_call()
    def get_history_debug(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Path | None,
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
            'ignored_events_ids': {k.serialize(): list(v) for k, v in ignored_ids.items()},
            'pnl_settings': {
                'from_timestamp': int(from_timestamp),
                'to_timestamp': int(to_timestamp),
            },
        }
        if directory_path is not None:
            with open(f'{directory_path}/pnl_debug.json', mode='w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2)
            return OK_RESULT
        return _wrap_in_ok_result(debug_info)

    if getattr(sys, 'frozen', False) is False:
        @async_api_call()
        def _import_history_debug(self, filepath: Path) -> dict[str, Any]:
            """Imports the PnL debug data for processing and report generation"""
            json_importer = DebugHistoryImporter(self.rotkehlchen.data.db)
            success, msg, data = json_importer.import_history_debug(filepath=filepath)

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
                filepath: FileStorage | Path,
        ) -> Response:
            if isinstance(filepath, FileStorage):
                _, tmpfilepath = tempfile.mkstemp()
                filepath.save(tmpfilepath)
                filepath = Path(tmpfilepath)

            return self._import_history_debug(async_query=async_query, filepath=filepath)  # pylint: disable=unexpected-keyword-arg  # pylint doesn't see the async decorator

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

    @async_api_call()
    def add_xpub(
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

    @async_api_call()
    def delete_xpub(
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
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    def add_evm_accounts(
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
            result[chain.serialize()].append(address)
        return _wrap_in_ok_result(result)

    @async_api_call()
    def refresh_evm_accounts(self) -> dict[str, Any]:
        chains = self.rotkehlchen.data.db.get_chains_to_detect_evm_accounts()
        try:
            self.rotkehlchen.chains_aggregator.detect_evm_accounts(chains=chains)
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return OK_RESULT

    def get_blockchain_accounts(self, blockchain: SupportedBlockchain) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            data = self.rotkehlchen.get_blockchain_account_data(cursor, blockchain)
        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_EVM_CHAINS,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS,
            account_data: list[SingleBlockchainAccountData[BTCAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        ...

    def add_single_blockchain_accounts(
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

    def edit_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
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
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)

        return process_result(_wrap_in_result(data, ''))

    def remove_single_blockchain_accounts(
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

    def _get_manually_tracked_balances(self) -> dict[str, Any]:
        db_entries = get_manually_tracked_balances(db=self.rotkehlchen.data.db, balance_type=None)
        balances = process_result(
            {
                'balances': db_entries,
            },

        )
        return _wrap_in_ok_result(balances)

    @async_api_call()
    def get_manually_tracked_balances(self) -> dict[str, Any]:
        return self._get_manually_tracked_balances()

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument
            self,
            function: Callable[['DBHandler', list[ManuallyTrackedBalance]], None],
            data_or_ids: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        ...

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument
            self,
            function: Callable[['DBHandler', list[int]], None],
            data_or_ids: list[int],
    ) -> dict[str, Any]:
        ...

    def _modify_manually_tracked_balances(
            self,
            function: (
                Callable[['DBHandler', list[ManuallyTrackedBalance]], None] |
                Callable[['DBHandler', list[int]], None]
            ),
            data_or_ids: list[ManuallyTrackedBalance] | list[int],
    ) -> dict[str, Any]:
        try:
            function(self.rotkehlchen.data.db, data_or_ids)  # type: ignore
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)
        except TagConstraintError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return self._get_manually_tracked_balances()

    @async_api_call()
    def add_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        return self._modify_manually_tracked_balances(
            function=add_manually_tracked_balances,
            data_or_ids=data,
        )

    @async_api_call()
    def edit_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        return self._modify_manually_tracked_balances(
            function=edit_manually_tracked_balances,
            data_or_ids=data,
        )

    @async_api_call()
    def remove_manually_tracked_balances(
            self,
            ids: list[int],
    ) -> dict[str, Any]:
        return self._modify_manually_tracked_balances(
            function=remove_manually_tracked_balances,
            data_or_ids=ids,
        )

    def get_ignored_assets(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = self.rotkehlchen.data.db.get_ignored_asset_ids(cursor)
        return api_response(_wrap_in_ok_result(list(result)), status_code=HTTPStatus.OK)

    def add_ignored_assets(self, assets: list[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.add_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def remove_ignored_assets(self, assets: list[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(list(result), msg)
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
        github = None
        if check_for_updates is True:
            github = Github()
        version = get_current_version(github)
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

    @async_api_call()
    def _import_data(
            self,
            source: DataImportSource,
            filepath: Path,
            **kwargs: Any,
    ) -> dict[str, Any]:
        success, msg = self.rotkehlchen.data_importer.import_csv(
            source=source,
            filepath=filepath,
            **kwargs,
        )
        if success is False:
            return wrap_in_fail_result(
                message=f'Invalid CSV format: {msg}',
                status_code=HTTPStatus.BAD_REQUEST,
            )

        return OK_RESULT

    def import_data(
            self,
            async_query: bool,
            source: DataImportSource,
            filepath: FileStorage | Path,
            **kwargs: Any,
    ) -> Response:
        if isinstance(filepath, FileStorage):
            _, tmpfilepath = tempfile.mkstemp()
            filepath.save(tmpfilepath)
            filepath = Path(tmpfilepath)

        return self._import_data(
            async_query=async_query,
            source=source,
            filepath=filepath,
            **kwargs,
        )

    @async_api_call()
    def get_eth2_stake_details(
            self,
            addresses: set[ChecksumEvmAddress],
            validator_indices: set[int],
            ignore_cache: bool,
    ) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.chains_aggregator.get_eth2_staking_details(ignore_cache=ignore_cache)  # noqa: E501
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except ModuleInactive as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        if len(addresses) != 0 or len(validator_indices) != 0:
            result = [entry for entry in result if entry.validator_index in validator_indices or entry.eth1_depositor in addresses]  # noqa: E501

        current_usd_price = Inquirer().find_usd_price(A_ETH)
        return {
            'result': process_result_list([x.serialize(current_usd_price) for x in result]),
            'message': '',
        }

    def get_eth2_stake_stats(
            self,
            withdrawals_filter_query: EthStakingEventFilterQuery,
            execution_filter_query: EthStakingEventFilterQuery,
    ) -> Response:
        dbeth2 = DBEth2(self.rotkehlchen.data.db)
        withdrawn_amount, execution_layer_rewards = dbeth2.get_validators_profit(
            withdrawals_filter_query=withdrawals_filter_query,
            execution_filter_query=execution_filter_query,
        )
        result = _wrap_in_ok_result({
            'withdrawn_consensus_layer_rewards': str(withdrawn_amount),
            'execution_layer_rewards': str(execution_layer_rewards),
        })
        return api_response(
            result=result,
            status_code=HTTPStatus.OK,
        )

    @async_api_call()
    def get_eth2_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            only_cache: bool,
    ) -> dict[str, Any]:
        try:
            stats, filter_total_found, sum_pnl = self.rotkehlchen.chains_aggregator.get_eth2_daily_stats(  # noqa: E501
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
                'entries_found': filter_total_found,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor, 'eth2_daily_staking_details'),  # noqa: E501
            }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

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

    @async_api_call()
    def add_eth2_validator(
            self,
            validator_index: int | None,
            public_key: Eth2PubKey | None,
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
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.UNAUTHORIZED}
        except (InputError, ModuleInactive) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': ''}

    def edit_eth2_validator(self, validator_index: int, ownership_proportion: FVal) -> Response:
        try:
            self.rotkehlchen.chains_aggregator.edit_eth2_validator(
                validator_index=validator_index,
                ownership_proportion=ownership_proportion,
            )
        except (InputError, ModuleInactive) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        else:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def delete_eth2_validator(
            self,
            validators: list[int],
    ) -> Response:
        try:
            self.rotkehlchen.chains_aggregator.delete_eth2_validators(validators)
            result = OK_RESULT
            status_code = HTTPStatus.OK
        except InputError as e:
            result = {'result': None, 'message': str(e)}
            status_code = HTTPStatus.CONFLICT
        except ModuleInactive as e:
            result = {'result': None, 'message': str(e)}
            status_code = HTTPStatus.CONFLICT

        return api_response(result, status_code=status_code)

    @async_api_call()
    def get_defi_balances(self) -> dict[str, Any]:
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

    @async_api_call()
    def get_ethereum_airdrops(self) -> dict[str, Any]:
        try:
            data = check_airdrops(
                addresses=self.rotkehlchen.chains_aggregator.accounts.eth,
                database=self.rotkehlchen.data.db,
                tolerance_for_amount_check=FVal('0.00000000000001000'),
            )
        except (RemoteError, UnableToDecryptRemoteData) as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except OSError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.INSUFFICIENT_STORAGE)

        return _wrap_in_ok_result(process_result(data))

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

    def purge_module_data(self, module_name: ModuleName | None) -> Response:
        self.rotkehlchen.data.db.purge_module_data(module_name)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _eth_module_query(
            self,
            module_name: ModuleName,
            method: str,
            query_specific_balances_before: list[str] | None,
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

    @async_api_call()
    def get_makerdao_dsr_balance(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='makerdao_dsr',
            method='get_current_dsr',
            query_specific_balances_before=None,
        )

    @async_api_call()
    def get_makerdao_dsr_history(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='makerdao_dsr',
            method='get_historical_dsr',
            query_specific_balances_before=None,
        )

    @async_api_call()
    def get_makerdao_vaults(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='makerdao_vaults',
            method='get_vaults',
            query_specific_balances_before=None,
        )

    @async_api_call()
    def get_makerdao_vault_details(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='makerdao_vaults',
            method='get_vault_details',
            query_specific_balances_before=None,
        )

    @async_api_call()
    def get_aave_balances(self) -> dict[str, Any]:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._eth_module_query(
            module_name='aave',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    @async_api_call()
    def get_module_stats_using_balances(
            self,
            module: Literal['aave', 'compound'],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        """
        Query the provided module for statistics using the tracked addresses for such module.
        This function uses the defi balances to enrich statistics.
        """
        return self._eth_module_query(
            module_name=module,
            method='get_stats_for_addresses',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module(module),
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    @async_api_call()
    def get_module_stats(
            self,
            module: Literal['uniswap', 'sushiswap'],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        return self._eth_module_query(
            module_name=module,
            method='get_stats_for_addresses',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module(module),
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    @async_api_call()
    def get_compound_balances(self) -> dict[str, Any]:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._eth_module_query(
            module_name='compound',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    @async_api_call()
    def get_yearn_vaults_balances(self) -> dict[str, Any]:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._eth_module_query(
            module_name='yearn_vaults',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
        )

    @async_api_call()
    def get_yearn_vaults_v2_balances(self) -> dict[str, Any]:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._eth_module_query(
            module_name='yearn_vaults_v2',
            method='get_balances',
            # We need to query defi balances before since eth balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the eth balances as a lambda function here so that they
            # are retrieved only after we are sure the eth balances have been
            # queried.
            given_eth_balances=lambda: self.rotkehlchen.chains_aggregator.balances.eth,
        )

    @async_api_call()
    def get_yearn_vaults_history(
            self,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='yearn_vaults',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chains_aggregator.defi_balances,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('yearn_vaults'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    @async_api_call()
    def get_yearn_vaults_v2_history(
            self,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        return self._eth_module_query(
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

    @async_api_call()
    def get_amm_platform_balances(
            self,
            module: Literal['uniswap', 'sushiswap', 'balancer'],
            method: str = 'get_balances',
    ) -> dict[str, Any]:
        return self._eth_module_query(
            module_name=module,
            method=method,
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module(module),
        )

    @async_api_call()
    def get_loopring_balances(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='loopring',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('loopring'),
        )

    @async_api_call()
    def get_balancer_events_history(
            self,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='balancer',
            method='get_events_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('balancer'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    @async_api_call()
    def get_dill_balance(self) -> dict[str, Any]:
        addresses = self.rotkehlchen.chains_aggregator.queried_addresses_for_module('pickle_finance')  # noqa: E501
        return self._eth_module_query(
            module_name='pickle_finance',
            method='get_dill_balances',
            query_specific_balances_before=['defi'],
            addresses=addresses,
        )

    @async_api_call()
    def get_liquity_troves(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='liquity',
            method='get_positions',
            query_specific_balances_before=None,
            given_addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
        )

    @async_api_call()
    def get_liquity_staked(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='liquity',
            method='liquity_staking_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
        )

    @async_api_call()
    def get_liquity_stability_pool_positions(self) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='liquity',
            method='get_stability_pool_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity'),
        )

    @async_api_call()
    def get_liquity_stats(self) -> dict[str, Any]:
        liquity_addresses = self.rotkehlchen.chains_aggregator.queried_addresses_for_module('liquity')  # noqa: E501
        # make sure that all the entries that need it have the usd value queried
        task_manager = self.rotkehlchen.task_manager
        if task_manager is not None:
            history_events_db = DBHistoryEvents(task_manager.database)
            entries_missing_prices = history_events_db.get_base_entries_missing_prices(
                query_filter=EvmEventFilterQuery.make(counterparties=[CPT_LIQUITY]),
            )
            query_missing_prices_of_base_entries(
                database=task_manager.database,
                entries_missing_prices=entries_missing_prices,
                base_entries_ignore_set=task_manager.base_entries_ignore_set,
            )

        stats = get_liquity_stats(
            database=self.rotkehlchen.data.db,
            addresses=liquity_addresses,
        )
        return _wrap_in_ok_result(stats)

    def _watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: dict[str, Any] | None,
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

    def purge_exchange_data(self, location: Location | None) -> Response:
        with self.rotkehlchen.data.db.user_write() as cursor:
            if location:
                self.rotkehlchen.data.db.purge_exchange_data(cursor, location)
            else:
                for exchange_location in ALL_SUPPORTED_EXCHANGES:
                    self.rotkehlchen.data.db.purge_exchange_data(cursor, exchange_location)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def purge_evm_transaction_data(self, chain_id: SUPPORTED_CHAIN_IDS | None) -> Response:
        chain = None if chain_id is None else chain_id.to_blockchain()
        DBEvmTx(self.rotkehlchen.data.db).purge_evm_transaction_data(
            chain=chain,  # type: ignore  # chain_id.to_blockchain() will only give supported chain
        )
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @async_api_call()
    def get_evm_transactions(
            self,
            only_cache: bool,
            filter_query: EvmTransactionsFilterQuery,
    ) -> dict[str, Any]:
        chain_ids: tuple[SUPPORTED_CHAIN_IDS]
        if filter_query.chain_id is None:
            chain_ids = get_args(SUPPORTED_CHAIN_IDS)
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

            entries_result = [{'entry': entry.serialize()} for entry in transactions]
            result: dict[str, Any] | None = None
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

    @async_api_call()
    def decode_evm_transactions(
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
                    send_ws_notifications=True,
                )
                if entry['tx_hashes'] is not None and task_manager is not None:
                    # Trigger the task to query the missing prices for the decoded events
                    events_filter = EvmEventFilterQuery.make(
                        tx_hashes=[event.tx_hash for event in decoded_events],
                    )
                    history_events_db = DBHistoryEvents(task_manager.database)
                    entries = history_events_db.get_base_entries_missing_prices(events_filter)
                    query_missing_prices_of_base_entries(
                        database=task_manager.database,
                        entries_missing_prices=entries,
                        base_entries_ignore_set=task_manager.base_entries_ignore_set,
                    )
            except (RemoteError, DeserializationError) as e:
                status_code = HTTPStatus.BAD_GATEWAY
                message = f'Failed to request evm transaction decoding due to {e!s}'
                break
            except InputError as e:
                status_code = HTTPStatus.CONFLICT
                message = f'Failed to request evm transaction decoding due to {e!s}'
                break
        else:  # no break in the for loop, success
            result = True

        return {'result': result, 'message': message, 'status_code': status_code}

    @async_api_call()
    def decode_pending_evm_transactions(
            self,
            evm_chains: list[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
    ) -> dict[str, Any]:
        """
        This method should be called after querying ethereum transactions and does the following:
        - Query missing receipts
        - Decode ethereum transactions

        It can be a slow process and this is why it is important to set the list of addresses
        queried per module that need to be decoded.

        This logic is executed by the frontend in pages where the set of transactions needs to be
        up to date, for example, the liquity module.
        """
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        result = {}
        for evm_chain in evm_chains:
            chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(evm_chain)
            # make sure that all the receipts are already queried
            chain_manager.transactions.get_receipts_for_transactions_missing_them()
            amount_of_tx_to_decode = dbevmtx.count_hashes_not_decoded(chain_id=evm_chain)
            if amount_of_tx_to_decode > 0:
                chain_manager.transactions_decoder.get_and_decode_undecoded_transactions(
                    send_ws_notifications=True,
                )
                result[evm_chain.to_name()] = amount_of_tx_to_decode

        return {
            'result': {'decoded_tx_number': result},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    @async_api_call()
    def get_count_transactions_not_decoded(self) -> dict[str, Any]:
        pending_transactions_to_decode = {}
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        for chain in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            if (tx_count := dbevmtx.count_hashes_not_decoded(chain_id=chain)) != 0:
                pending_transactions_to_decode[chain.to_name()] = tx_count

        return _wrap_in_ok_result(pending_transactions_to_decode)

    def get_asset_icon(
            self,
            asset: AssetWithNameAndType,
            match_header: str | None,
    ) -> Response:
        icon_path = self.rotkehlchen.icon_manager.asset_icon_path(asset)
        if icon_path is not None:
            response = check_if_image_is_cached(
                image_path=icon_path,
                match_header=match_header,
            )
            if response is not None:
                return response
            else:
                # here icon_path comes from asset_icon_path where the existence has been
                # already checked
                return create_image_response(image_path=icon_path)

        image_path, launched_remote_query = self.rotkehlchen.icon_manager.get_icon(asset)
        if image_path is None and launched_remote_query is True:
            return make_response(
                (
                    b'',
                    HTTPStatus.ACCEPTED, {'mimetype': 'image/png', 'Content-Type': 'image/png'},
                ),
            )
        return maybe_create_image_response(image_path=image_path)

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

    @async_api_call()
    def get_current_assets_price(
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
        assets_price: dict[Asset, list[Price | (int | None | bool)]] = {}
        oracle: CurrentPriceOracle | None
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
                    price, oracle, used_main_currency = Inquirer().find_price_and_oracle(
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
        assets_price: defaultdict[Asset, defaultdict] = defaultdict(lambda: defaultdict(lambda: ZERO_PRICE))  # noqa: E501
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
                    f'{asset.identifier} at time {timestamp} due to: {e!s}. Using zero price',
                )
                price = ZERO_PRICE

            assets_price[asset][timestamp] = price

        result = {
            'assets': {k: dict(v) for k, v in assets_price.items()},
            'target_asset': target_asset,
        }
        return _wrap_in_ok_result(process_result(result))

    @async_api_call()
    def get_historical_assets_price(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
    ) -> dict[str, Any]:
        return self._get_historical_assets_price(
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
        )

    @async_api_call()
    def sync_data(self, action: Literal['upload', 'download']) -> dict[str, Any]:
        try:
            success, msg = self.rotkehlchen.premium_sync_manager.sync_data(
                action=action,
                perform_migrations=True,  # we can do it now since all is initialized
            )
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumApiError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumAuthenticationError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.UNAUTHORIZED)
        else:
            if msg.startswith('Pulling failed'):
                return wrap_in_fail_result(msg, status_code=HTTPStatus.BAD_GATEWAY)
            return _wrap_in_result(success, message=msg)

    @async_api_call()
    def create_oracle_cache(
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

    @async_api_call()
    def get_oracle_cache(self, oracle: HistoricalPriceOracle) -> dict[str, Any]:
        return self._get_oracle_cache(oracle)

    @staticmethod
    def get_supported_oracles() -> Response:
        data = {
            # don't expose some sources in the api
            'history': [{'id': str(x), 'name': str(x).capitalize()} for x in HistoricalPriceOracle if x not in NOT_EXPOSED_SOURCES],  # noqa: E501
            'current': [{'id': str(x), 'name': str(x).capitalize()} for x in CurrentPriceOracle],
        }
        result_dict = _wrap_in_ok_result(data)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @async_api_call()
    def get_token_info(self, address: ChecksumEvmAddress, chain_id: SUPPORTED_CHAIN_IDS) -> dict[str, Any]:  # noqa: E501
        evm_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id)
        try:
            info = evm_manager.node_inquirer.get_erc20_contract_info(address=address)
        except BadFunctionCallOutput:
            return wrap_in_fail_result(
                f'{chain_id!s} address {address} seems to not be a deployed contract',
                status_code=HTTPStatus.CONFLICT,
            )
        return _wrap_in_ok_result(info)

    @async_api_call()
    def get_assets_updates(self) -> dict[str, Any]:
        try:
            local, remote, new_changes = self.rotkehlchen.assets_updater.check_for_updates()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return _wrap_in_ok_result({'local': local, 'remote': remote, 'new_changes': new_changes})

    @async_api_call()
    def perform_assets_updates(
            self,
            up_to_version: int | None,
            conflicts: dict[Asset, Literal['remote', 'local']] | None,
    ) -> dict[str, Any]:
        try:
            result = self.rotkehlchen.assets_updater.perform_update(up_to_version, conflicts)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        if result is None:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.sync_globaldb_assets(cursor)
            return OK_RESULT

        return {
            'result': result,  # returned conflicts
            'message': 'Found conflicts during assets upgrade',
            'status_code': HTTPStatus.CONFLICT,
        }

    def get_all_binance_pairs(self, location: Location) -> Response:
        try:
            pairs = list(query_binance_exchange_pairs(location=location).keys())
        except InputError as e:
            return api_response(
                wrap_in_fail_result(
                    f'Failed to handle binance markets internally. {e!s}',
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

    def add_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> Response:
        """
        Add a manual historical price.
        If the price for the specified pair and timestamp already exists, it is replaced.
        """
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

    def edit_manual_price(
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

    def get_manual_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> Response:
        return api_response(
            _wrap_in_ok_result(GlobalDBHandler().get_manual_prices(from_asset, to_asset)),
            status_code=HTTPStatus.OK,
        )

    def delete_manual_price(
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

    @async_api_call()
    def get_avalanche_transactions(
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
        except RemoteError:
            return wrap_in_fail_result(message='Not found.', status_code=HTTPStatus.NOT_FOUND)
        if response is None:
            return wrap_in_fail_result(message='Not found.', status_code=HTTPStatus.NOT_FOUND)

        entries_result = [transaction.serialize() for transaction in response]
        result = {
            'entries': entries_result,
            'entries_found': len(entries_result),
        }
        return _wrap_in_ok_result(result)

    @async_api_call()
    def get_nfts(self, ignore_cache: bool) -> dict[str, Any]:
        return self._eth_module_query(
            module_name='nfts',
            method='get_all_info',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
            ignore_cache=ignore_cache,
        )

    @async_api_call()
    def get_nfts_balances(
            self,
            filter_query: NFTFilterQuery,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        if ignore_cache is True:
            uniswap_result = self._eth_module_query(
                module_name='uniswap',
                method='get_v3_balances',
                query_specific_balances_before=None,
                addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('uniswap'),
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

    def get_manual_latest_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> Response:
        prices = GlobalDBHandler().get_all_manual_latest_prices(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        prices_information = [{
            'from_asset': x[0],
            'to_asset': x[1],
            'price': x[2],
        } for x in prices]
        if (nft_module := self.rotkehlchen.chains_aggregator.get_module('nfts')) is not None:
            # query also nfts manual prices
            nft_price_data = nft_module.get_nfts_with_price(
                from_asset=from_asset,
                to_asset=to_asset,
                only_with_manual_prices=True,
            )
            prices_information.extend([{
                'from_asset': nft_data['asset'],
                'to_asset': nft_data['price_asset'],
                'price': nft_data['price_in_asset'],
            } for nft_data in nft_price_data])

        return api_response(_wrap_in_ok_result(prices_information), status_code=HTTPStatus.OK)

    @async_api_call()
    def get_nfts_with_price(self, lps_handling: NftLpHandling) -> dict[str, Any]:
        return self._eth_module_query(
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
            module_query_result = self._eth_module_query(
                module_name='nfts',
                method='add_nft_with_price',
                query_specific_balances_before=None,
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
            return make_response_from_dict(module_query_result)
        try:
            pairs_to_invalidate = GlobalDBHandler().add_manual_latest_price(
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)
        Inquirer().remove_cache_prices_for_asset(pairs_to_invalidate)

        return api_response(OK_RESULT)

    def delete_manual_latest_price(
            self,
            asset: Asset,
    ) -> Response:
        if asset.is_nft():
            module_query_result = self._eth_module_query(
                module_name='nfts',
                method='delete_price_for_nft',
                query_specific_balances_before=None,
                asset=asset,
            )
            return make_response_from_dict(module_query_result)
        try:
            pairs_to_invalidate = GlobalDBHandler().delete_manual_latest_price(asset=asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)
        Inquirer().remove_cache_prices_for_asset(pairs_to_invalidate)

        return api_response(OK_RESULT)

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
                result_dict['userdb']['info'] = self.rotkehlchen.data.db.get_db_info(cursor)  # type: ignore
            result_dict['userdb']['backups'] = self.rotkehlchen.data.db.get_backups()  # type: ignore

        return api_response(_wrap_in_ok_result(result_dict), status_code=HTTPStatus.OK)

    def create_database_backup(self) -> Response:
        try:
            db_backup_path = self.rotkehlchen.data.db.create_db_backup()
        except OSError as e:
            error_msg = f'Failed to create a DB backup due to {e!s}'
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
            report_id: int | None,
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
                export_type=AccountingEventExportType.API,
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

    @async_api_call()
    def query_online_events(self, query_type: HistoryEventQueryType) -> dict[str, Any]:
        """Queries the specified event type for any new events and saves them in the DB"""
        try:
            if query_type == HistoryEventQueryType.EXCHANGES:
                self.rotkehlchen.exchange_manager.query_history_events()
                return OK_RESULT

            # else we query eth staking events
            eth2 = self.rotkehlchen.chains_aggregator.get_module('eth2')
            if eth2 is None:
                return wrap_in_fail_result(
                    message='eth2 module is not active',
                    status_code=HTTPStatus.CONFLICT,
                )

            if query_type == HistoryEventQueryType.ETH_WITHDRAWALS:
                eth2.query_services_for_validator_withdrawals(
                    addresses=self.rotkehlchen.chains_aggregator.accounts.eth,
                    to_ts=ts_now(),
                )
            else:  # block production
                with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                    cursor.execute('SELECT validator_index FROM eth2_validators')
                    indices = [row[0] for row in cursor]
                if len(indices) != 0:
                    log.debug(f'Querying information for validator indices {indices}')
                    eth2.beaconchain.get_and_store_produced_blocks(indices)
                    eth2.combine_block_with_tx_events()
        except RemoteError as e:
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.BAD_GATEWAY,
            )

        return OK_RESULT

    def get_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            group_by_event_ids: bool,
    ) -> Response:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        has_premium = False
        entries_limit = FREE_HISTORY_EVENTS_LIMIT
        if self.rotkehlchen.premium is not None:
            has_premium = True
            entries_limit = - 1

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            events_result, entries_found, entries_with_limit = dbevents.get_history_events_and_limit_info(  # noqa: E501
                cursor=cursor,
                filter_query=filter_query,
                has_premium=has_premium,
                group_by_event_ids=group_by_event_ids,
                entries_limit=entries_limit if entries_limit != -1 else None,
            )
            entries_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='history_events',
                group_by='event_identifier' if group_by_event_ids else None,
            )
            location = filter_query.location
            chain_id = ChainID(Location.to_chain_id(location)) if location in EVM_LOCATIONS else None  # noqa: E501

            customized_event_ids = dbevents.get_customized_event_identifiers(
                cursor=cursor,
                chain_id=chain_id,  # type: ignore
            )
            hidden_event_ids = dbevents.get_hidden_event_ids(cursor)
            ignored_ids_mapping = self.rotkehlchen.data.db.get_ignored_action_ids(
                cursor=cursor,
                action_type=ActionType.HISTORY_EVENT,
            )

        accountant_pot = AccountingPot(
            database=self.rotkehlchen.data.db,
            evm_accounting_aggregators=EVMAccountingAggregators([self.rotkehlchen.chains_aggregator.get_evm_manager(x).accounting_aggregator for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS]),  # noqa: E501
            msg_aggregator=self.rotkehlchen.msg_aggregator,
            is_dummy_pot=True,
        )
        if group_by_event_ids is True:
            missing_accounting_rules = query_missing_accounting_rules(
                db=self.rotkehlchen.data.db,
                accounting_pot=accountant_pot,
                evm_accounting_aggregator=accountant_pot.events_accountant.evm_accounting_aggregators,
                events=[x for _, x in events_result],  # type: ignore
                accountant=self.rotkehlchen.accountant,
            )  # length of missing_accounting_rules and events guaranteeed by function
            entries = [  # type: ignore  # mypy doesn't understand significance of boolean check
                x.serialize_for_api(  # type: ignore
                    customized_event_ids=customized_event_ids,
                    ignored_ids_mapping=ignored_ids_mapping,
                    hidden_event_ids=hidden_event_ids,
                    missing_accounting_rule=missing_accounting_rule,
                    grouped_events_num=grouped_events_num,  # type: ignore
                ) for (grouped_events_num, x), missing_accounting_rule in zip(events_result, missing_accounting_rules, strict=True)  # noqa: E501
            ]
        else:
            missing_accounting_rules = query_missing_accounting_rules(
                db=self.rotkehlchen.data.db,
                accounting_pot=accountant_pot,
                evm_accounting_aggregator=accountant_pot.events_accountant.evm_accounting_aggregators,
                events=events_result,  # type: ignore
                accountant=self.rotkehlchen.accountant,
            )
            entries = [
                x.serialize_for_api(  # type: ignore
                    customized_event_ids=customized_event_ids,
                    ignored_ids_mapping=ignored_ids_mapping,
                    hidden_event_ids=hidden_event_ids,
                    missing_accounting_rule=missing_accounting_rule,
                ) for x, missing_accounting_rule in zip(events_result, missing_accounting_rules, strict=True)  # noqa: E501
            ]
        result = {
            'entries': entries,
            'entries_found': entries_with_limit,
            'entries_limit': entries_limit,
            'entries_total': entries_total,
        }
        if has_premium is False:
            result['entries_found_total'] = entries_found

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @async_api_call()
    def query_kraken_staking_events(
            self,
            only_cache: bool,
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        return self._get_exchange_staking_or_savings_history(
            only_cache=only_cache,
            location=Location.KRAKEN,
            query_filter=query_filter,
            value_filter=value_filter,
            event_types=[HistoryEventType.STAKING],
            exclude_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ],
            event_subtypes=None,
        )

    def get_user_added_assets(self, path: Path | None) -> Response:
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
                result=wrap_in_fail_result(f'Failed to create asset export file. {e!s}'),
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

    @async_api_call()
    def import_user_assets(self, path: Path) -> dict[str, Any]:
        try:
            if path.suffix == '.json':
                import_assets_from_file(
                    path=path,
                    msg_aggregator=self.rotkehlchen.msg_aggregator,
                    db_handler=self.rotkehlchen.data.db,
                )
            else:
                try:
                    zip_file = ZipFile(path)
                except BadZipFile as e:
                    raise ValidationError('Provided file could not be unzipped') from e

                if 'assets.json' not in zip_file.namelist():
                    raise ValidationError('assets.json could not be found in the provided zip file.')  # noqa: E501

                with tempfile.TemporaryDirectory() as tempdir:
                    zip_file.extract('assets.json', tempdir)
                    import_assets_from_file(
                        path=Path(tempdir) / 'assets.json',
                        msg_aggregator=self.rotkehlchen.msg_aggregator,
                        db_handler=self.rotkehlchen.data.db,
                    )
        except ValidationError as e:
            return wrap_in_fail_result(
                message=f'Provided file does not have the expected format. {e!s}',
                status_code=HTTPStatus.CONFLICT,
            )
        except InputError as e:
            return wrap_in_fail_result(f'{e!s}', status_code=HTTPStatus.CONFLICT)

        return OK_RESULT

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

    @async_api_call()
    def get_ens_mappings(
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

    def get_addressbook_entries(
            self,
            book_type: AddressbookType,
            filter_query: AddressbookFilterQuery,
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        with db_addressbook.read_ctx(book_type) as cursor:
            entries, entries_found = db_addressbook.get_addressbook_entries(
                cursor=cursor,
                filter_query=filter_query,
            )
            entries_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='address_book',
            )
        serialized = [entry.serialize() for entry in entries]
        result = {
            'entries': serialized,
            'entries_found': entries_found,
            'entries_total': entries_total,
        }
        return api_response(_wrap_in_ok_result(result))

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            with db_addressbook.write_ctx(book_type) as write_cursor:
                db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=entries)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        else:
            return api_response(result=OK_RESULT)

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.update_addressbook_entries(book_type=book_type, entries=entries)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        else:
            return api_response(result=OK_RESULT)

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
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        else:
            return api_response(result=OK_RESULT)

    def search_for_names_everywhere(
            self,
            chain_addresses: list[OptionalChainAddress],
    ) -> Response:
        mappings = search_for_addresses_names(
            database=self.rotkehlchen.data.db,
            chain_addresses=chain_addresses,
        )
        return api_response(_wrap_in_ok_result(process_result_list(mappings)))

    @async_api_call()
    def detect_evm_tokens(
            self,
            only_cache: bool,
            addresses: Sequence[ChecksumEvmAddress] | None,
            blockchain: SUPPORTED_EVM_CHAINS,
    ) -> dict[str, Any]:
        manager: EvmManager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)
        if addresses is None:
            addresses = self.rotkehlchen.chains_aggregator.accounts.get(blockchain)

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
        entries = [entry.to_dict(export_with_type=False) for entry in custom_assets_result]
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
        """Gets an evm event details"""
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        event = dbevents.get_evm_event_by_identifier(identifier=identifier)
        if event is None:
            return api_response(wrap_in_fail_result('No event found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        details = event.get_details()
        if details is None:
            return api_response(wrap_in_fail_result('No details found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        return api_response(_wrap_in_ok_result(details), status_code=HTTPStatus.OK)

    @async_api_call()
    def add_evm_transaction_by_hash(
            self,
            evm_chain: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
            associated_address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        """
        Adds an evm transaction to the DB and associates it with the address provided.
        If successful, the transaction is then decoded.
        """
        evm_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(evm_chain)
        try:
            evm_manager.transactions.add_transaction_by_hash(
                tx_hash=tx_hash,
                associated_address=associated_address,
            )
        except (KeyError, DeserializationError, RemoteError, AlreadyExists, InputError) as e:  # pylint: disable=no-member
            if isinstance(e, AlreadyExists):  # pylint: disable=no-member
                status_code = HTTPStatus.CONFLICT
            elif isinstance(e, InputError):
                status_code = HTTPStatus.NOT_FOUND
            else:
                status_code = HTTPStatus.BAD_GATEWAY

            return wrap_in_fail_result(
                message=(
                    f'Unable to add transaction with hash {tx_hash.hex()} for chain '
                    f'{evm_chain} and associated address {associated_address} due to {e!s}'
                ),
                status_code=status_code,
            )

        evm_manager.transactions_decoder.decode_transaction_hashes(
            ignore_cache=True,
            tx_hashes=[tx_hash],
        )
        return OK_RESULT

    def _get_exchange_staking_or_savings_history(
            self,
            only_cache: bool,
            location: Literal[Location.KRAKEN, Location.BINANCE, Location.BINANCEUS],
            event_types: list[HistoryEventType],
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
    ) -> dict[str, Any]:
        """Query exchanges for either staking or savings history.

        If `only_cache` is False, only data stored in the database is returned. Otherwise,
        the latest data is fetched from the exchange.
        """
        history_events_db = DBHistoryEvents(self.rotkehlchen.data.db)
        table_filter = HistoryEventFilterQuery.make(
            location=location,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
        )

        message = ''
        entries_limit = -1
        if self.rotkehlchen.premium is None:
            entries_limit = FREE_HISTORY_EVENTS_LIMIT

        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(
            location,
        )
        if exchanges_list is None:
            return wrap_in_fail_result(
                message=f'There is no {location.name} account added.',
                status_code=HTTPStatus.CONFLICT,
            )

        # query events from db and remote data(if `only_cache` is false).
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            try:
                events_raw, entries_found = self.rotkehlchen.events_historian.query_history_events(
                    cursor=cursor,
                    location=location,
                    filter_query=query_filter,
                    only_cache=only_cache,
                    task_manager=self.rotkehlchen.task_manager,
                )
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                return wrap_in_fail_result(
                    message=f'Database query error retrieving missing prices {e!s}',
                    status_code=HTTPStatus.CONFLICT,
                )

            events = []
            for event in events_raw:
                try:
                    staking_event = StakingEvent.from_history_base_entry(event)
                except DeserializationError as e:
                    log.warning(f'Could not deserialize staking event: {event} due to {e!s}')
                    continue
                events.append(staking_event)

            entries_total, _ = history_events_db.get_history_events_count(
                cursor=cursor,
                query_filter=table_filter,
            )
            value_query_filters, value_bindings = value_filter.prepare(with_pagination=False, with_order=False)  # noqa: E501
            usd_value, amounts = history_events_db.get_value_stats(
                cursor=cursor,
                query_filters=value_query_filters,
                bindings=value_bindings,
            )
            result = {
                'entries': events,
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
                        'asset': entry[0],
                        'amount': entry[1],
                        'usd_value': entry[2],
                    } for entry in amounts
                ],
            }

        return {'result': result, 'message': message, 'status_code': HTTPStatus.OK}

    @async_api_call()
    def get_binance_savings_history(
            self,
            only_cache: bool,
            location: Literal[Location.BINANCE, Location.BINANCEUS],
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        """Returns a summary of Binance savings events that match the filter provided."""
        return self._get_exchange_staking_or_savings_history(
            only_cache=only_cache,
            location=location,
            event_types=[HistoryEventType.RECEIVE],
            event_subtypes=[HistoryEventSubType.REWARD],
            query_filter=query_filter,
            value_filter=value_filter,
        )

    def get_all_evm_chains(self) -> Response:
        """Returns a list of all EVM chain ids."""
        result = []
        for chain in ChainID:
            name, label = chain.name_and_label()
            result.append({'id': chain.value, 'name': name, 'label': label})
        return api_response(result=_wrap_in_ok_result(result=result))

    def get_ens_avatar(self, ens_name: str, match_header: str | None) -> Response:
        """
        Searches for the ENS avatar of the given `ens_name`.
        If found returns a response with the avatar, otherwise a 404 empty response if
        the avatar is not found or a 409 empty response if there is any error.

        Also supports etag mechanism that helps with caching on the client side.
        """
        avatars_dir = self.rotkehlchen.data_dir / 'icons' / 'avatars'
        avatar_path = avatars_dir / f'{ens_name}.png'
        if avatar_path.is_file():
            response = check_if_image_is_cached(image_path=avatar_path, match_header=match_header)
            if response is not None:
                return response

        dbens = DBEns(self.rotkehlchen.data.db)
        try:
            last_update = dbens.get_last_avatar_update(ens_name)
        except InputError:
            log.error(f'Got unexpected ens name {ens_name} at ens avatars endpoint')
            return make_response(
                (
                    b'',
                    HTTPStatus.CONFLICT, {'mimetype': 'image/png', 'Content-Type': 'image/png'},
                ),
            )

        if ts_now() - last_update > ENS_AVATARS_REFRESH:
            # If avatar for this ens name has never been checked or the avatar has expired
            # then we try to download.
            try:
                nft_module = self.rotkehlchen.chains_aggregator.get_module('nfts')
                try_download_ens_avatar(
                    eth_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
                    opensea=nft_module.opensea if nft_module is not None else None,
                    avatars_dir=avatars_dir,
                    ens_name=ens_name,
                )
            except RemoteError as e:
                log.error(f'Got a remote error during querying an ens avatar: {e!s}')
                return make_response(
                    (
                        b'',
                        HTTPStatus.CONFLICT, {'mimetype': 'image/png', 'Content-Type': 'image/png'},  # noqa: E501
                    ),
                )

        return maybe_create_image_response(image_path=avatar_path)

    def clear_icons_cache(self, icons: list[AssetWithNameAndType] | None) -> Response:
        """Clears cache entries for the specified icons.

        If no icons are provided, the icons cache is cleared entirely.
        """
        icons_dir = self.rotkehlchen.icon_manager.icons_dir
        if icons is None:
            for entry in icons_dir.iterdir():
                if entry.is_file() and entry.parent != icons_dir / 'avatars':
                    entry.unlink()

            return api_response(OK_RESULT)

        for icon in icons:
            self.rotkehlchen.icon_manager.delete_icon(icon)

        return api_response(OK_RESULT)

    def clear_avatars_cache(self, avatars: list[str] | None) -> Response:
        """Clears cache entries for the specified avatars of ENS names.

        If no avatars are provided, the avatars cache is cleared entirely.
        """
        avatars_dir = self.rotkehlchen.icon_manager.icons_dir / 'avatars'
        if avatars is None:
            for entry in avatars_dir.iterdir():
                if entry.is_file():
                    entry.unlink()

            with self.rotkehlchen.data.db.user_write() as delete_cursor:
                delete_cursor.execute('UPDATE ens_mappings SET last_avatar_update=?', (Timestamp(0),))  # noqa: E501

            return api_response(OK_RESULT)

        avatars_to_delete = [avatars_dir / f'{avatar_name}.png' for avatar_name in avatars]
        for avatar in avatars_to_delete:
            if avatar.is_file():
                avatar.unlink()

        with self.rotkehlchen.data.db.user_write() as delete_cursor:
            delete_cursor.executemany(
                'UPDATE ens_mappings SET last_avatar_update=? WHERE ens_name=?',
                [(Timestamp(0), avatar_name) for avatar_name in avatars],
            )

        return api_response(OK_RESULT)

    def get_types_mappings(self) -> Response:
        result = {
            'global_mappings': EVENT_CATEGORY_MAPPINGS,
            'event_category_details': {
                category: {'counterparty_mappings': entries, 'direction': category.direction.serialize()}  # noqa: E501
                for category, entries in EVENT_CATEGORY_DETAILS.items()
            },
            'accounting_events_icons': ACCOUNTING_EVENTS_ICONS,
        }
        return api_response(
            result=_wrap_in_ok_result(process_result(result)),
            status_code=HTTPStatus.OK,
        )

    def get_evm_counterparties_details(self) -> Response:
        """
        Collect the counterparties from decoders in the different evm chains and combine them
        removing duplicates.
        """
        counterparties: set[CounterpartyDetails] = reduce(
            lambda x, y: x | y,
            [
                self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id).transactions_decoder.rules.all_counterparties
                for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
            ],
        )
        return api_response(
            result=process_result(_wrap_in_ok_result(list(counterparties))),
            status_code=HTTPStatus.OK,
        )

    def get_evm_products(self) -> Response:
        """
        Collect the mappings of counterparties to the products they list
        """
        products_mappings = reduce(
            lambda x, y: x | y,
            [
                self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id).transactions_decoder.get_decoders_products()
                for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
            ],
        )
        return api_response(
            result=process_result(_wrap_in_ok_result(
                {
                    'mappings': products_mappings,
                    'products': [product.serialize() for product in EvmProduct],
                },
            )),
            status_code=HTTPStatus.OK,
        )

    @async_api_call()
    def refresh_general_cache(self) -> dict[str, Any]:
        eth_node_inquirer = self.rotkehlchen.chains_aggregator.ethereum.node_inquirer
        optimism_inquirer = self.rotkehlchen.chains_aggregator.optimism.node_inquirer
        caches = (
            ('curve pools', CacheType.CURVE_LP_TOKENS, query_curve_data, save_curve_data_to_cache, eth_node_inquirer),  # noqa: E501
            ('convex pools', CacheType.CONVEX_POOL_ADDRESS, query_convex_data, save_convex_data_to_cache, eth_node_inquirer),  # noqa: E501
            ('velodrome pools', CacheType.VELODROME_POOL_ADDRESS, query_velodrome_data, save_velodrome_data_to_cache, optimism_inquirer),  # noqa: E501
        )
        for (cache, cache_type, query_method, save_method, inquirer) in caches:
            if inquirer.ensure_cache_data_is_updated(
                cache_type=cache_type,
                query_method=query_method,
                save_method=save_method,
                force_refresh=True,
            ) is False:
                return wrap_in_fail_result(
                    message=f'Failed to refresh {cache} cache',
                    status_code=HTTPStatus.CONFLICT,
                )

        try:
            ethereum_manager: EthereumManager = self.rotkehlchen.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)  # noqa: E501
            query_yearn_vaults(
                db=self.rotkehlchen.data.db,
                ethereum_inquirer=ethereum_manager.node_inquirer,
            )
        except RemoteError as e:
            return wrap_in_fail_result(
                message=f'Failed to refresh yearn vaults cache due to: {e!s}',
                status_code=HTTPStatus.CONFLICT,
            )
        try:
            query_ilk_registry_and_maybe_update_cache(eth_node_inquirer)
        except RemoteError as e:
            return wrap_in_fail_result(
                message=f'Failed to refresh makerdao vault ilk cache due to: {e!s}',
                status_code=HTTPStatus.CONFLICT,
            )
        return OK_RESULT

    def get_airdrops_metadata(self) -> Response:
        """Returns a list of airdrops metadata"""
        result = []
        for identifier, airdrop in AIRDROPS.items():
            result.append({
                'identifier': identifier,
                'name': airdrop.name,
                'icon': airdrop.icon,
            })
        return api_response(result=_wrap_in_ok_result(result=result))

    def get_defi_metadata(self) -> Response:
        """Returns a list of defi metadata"""
        result = []
        for identifier, protocol in DEFI_PROTOCOLS.items():
            result.append({
                'identifier': identifier,
                'name': protocol.name,
                'icon': protocol.icon,
            })
        return api_response(result=_wrap_in_ok_result(result=result))

    def get_skipped_external_events_summary(self) -> Response:
        summary = get_skipped_external_events_summary(self.rotkehlchen)
        return api_response(result=_wrap_in_ok_result(summary), status_code=HTTPStatus.OK)

    def export_skipped_external_events(self, directory_path: Path | None) -> Response:
        try:
            exportpath = export_skipped_external_events(
                rotki=self.rotkehlchen,
                directory=directory_path,
            )
        except CSVWriteError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        if directory_path is None:
            try:
                return send_file(
                    path_or_file=exportpath,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV,
                )
            except FileNotFoundError:
                return api_response(
                    wrap_in_fail_result('No file was found'),
                    status_code=HTTPStatus.NOT_FOUND,
                )
        else:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def reprocess_skipped_external_events(self) -> Response:
        total, successful = reprocess_skipped_external_events(self.rotkehlchen)
        return api_response(
            result=_wrap_in_ok_result({'total': total, 'successful': successful}),
            status_code=HTTPStatus.OK,
        )

    def export_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            directory_path: Path | None,
    ) -> Response:
        """ Export or Download history events data to a CSV file."""
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            history_events, _, _ = dbevents.get_history_events_and_limit_info(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=True,
                entries_limit=None,
            )

        if len(history_events) == 0:
            return api_response(
                wrap_in_fail_result('No history processed in order to perform an export'),
                status_code=HTTPStatus.CONFLICT,
            )

        serialized_history_events = []
        headers: dict[str, None] = {}
        for event in history_events:
            serialized_event = event.serialize_for_csv()
            serialized_history_events.append(serialized_event)
            # maintain insertion order without storing extra info
            headers.update({key: None for key in serialized_event})

        if directory_path is None:  # on download
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = Path(temp_dir) / FILENAME_HISTORY_EVENTS_CSV

                try:
                    dict_to_csv_file(
                        file_path,
                        serialized_history_events,
                        headers.keys(),
                    )
                    return send_file(
                        path_or_file=file_path,
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=FILENAME_HISTORY_EVENTS_CSV,
                    )
                except (CSVWriteError, PermissionError) as e:
                    return api_response(
                        wrap_in_fail_result(str(e)),
                        status_code=HTTPStatus.CONFLICT,
                    )
                except FileNotFoundError:
                    return api_response(
                        wrap_in_fail_result('No file was found'),
                        status_code=HTTPStatus.NOT_FOUND,
                    )

        try:  # from here and below we do a direct export to filesystem
            directory_path.mkdir(parents=True, exist_ok=True)
            file_path = directory_path / FILENAME_HISTORY_EVENTS_CSV
            dict_to_csv_file(
                file_path,
                serialized_history_events,
                headers.keys(),
            )
        except (CSVWriteError, PermissionError) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _invalidate_cache_for_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
    ) -> None:
        accountant = self.rotkehlchen.accountant
        type_identifier = get_event_type_identifier(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        affected_events = accountant.processable_events_cache_signatures.get(type_identifier)
        for event_id in affected_events:
            accountant.processable_events_cache.remove(event_id)

    def add_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> Response:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.add_accounting_rule(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        self._invalidate_cache_for_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def update_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            identifier: int,
    ) -> Response:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.update_accounting_rule(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
                identifier=identifier,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        self._invalidate_cache_for_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def delete_accounting_rule(self, rule_id: int) -> Response:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            event_type, event_subtype, counterparty = db.remove_accounting_rule(rule_id=rule_id)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        self._invalidate_cache_for_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def query_accounting_rules(self, filter_query: AccountingRulesFilterQuery) -> Response:
        db = self.rotkehlchen.data.db
        entries, total_filter_count = DBAccountingRules(db).query_rules_and_serialize(filter_query=filter_query)  # noqa: E501
        with db.conn.read_ctx() as cursor:
            result = {
                'entries': entries,
                'entries_found': total_filter_count,
                'entries_total': self.rotkehlchen.data.db.get_entries_count(cursor=cursor, entries_table='accounting_rules'),  # noqa: E501
                'entries_limit': -1,
            }

        return api_response(process_result(_wrap_in_ok_result(result)), status_code=HTTPStatus.OK)

    def linkable_accounting_properties(self) -> Response:
        possible_accounting_setting_names = get_args(LINKABLE_ACCOUNTING_SETTINGS_NAME)
        result = {
            'count_entire_amount_spend': possible_accounting_setting_names,
            'count_cost_basis_pnl': possible_accounting_setting_names,
            'taxable': possible_accounting_setting_names,
        }

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def solve_multiple_accounting_rule_conflicts(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
            solve_all_using: Literal['remote', 'local'] | None,
    ) -> Response:
        conflict_db = DBRemoteConflicts(self.rotkehlchen.data.db)
        try:
            if solve_all_using is None:
                conflict_db.solve_accounting_rule_conflicts(conflicts=conflicts)
            else:
                conflict_db.solve_all_conflicts(solve_all_using=solve_all_using)
        except (InputError, KeyError) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def list_accounting_rules_conflicts(self, filter_query: DBFilterQuery) -> Response:
        conflict_db = DBRemoteConflicts(self.rotkehlchen.data.db)
        conflicts = conflict_db.list_accounting_conflicts(filter_query=filter_query)
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            total_entries = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='unresolved_remote_conflicts',
            )
        result = {
            'entries': conflicts,
            'entries_found': total_entries,
            'entries_total': total_entries,  # there is no filter, only pagination
            'entries_limit': -1,
        }
        return api_response(process_result(_wrap_in_ok_result(result)), status_code=HTTPStatus.OK)
