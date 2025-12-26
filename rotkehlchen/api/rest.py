import datetime
import json
import logging
import os
import sys
import tempfile
import traceback
from collections import defaultdict
from collections.abc import Callable, Sequence
from contextlib import suppress
from functools import partial
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, get_args, overload
from zipfile import BadZipFile, ZipFile

import gevent
from flask import Response, after_this_request, make_response, send_file
from gevent.event import Event
from gevent.lock import Semaphore
from marshmallow.exceptions import ValidationError
from pysqlcipher3 import dbapi2 as sqlcipher
from solders.solders import Signature
from web3.exceptions import BadFunctionCallOutput
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.constants import (
    ACCOUNTING_EVENTS_ICONS,
    EVENT_CATEGORY_DETAILS,
    EVENT_CATEGORY_MAPPINGS,
    EVENT_GROUPING_ORDER,
)
from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.accounting.entry_type_mappings import ENTRY_TYPE_MAPPINGS
from rotkehlchen.accounting.export.csv import (
    FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV,
    CSVWriteError,
    dict_to_csv_file,
)
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, BalanceType
from rotkehlchen.accounting.structures.processed_event import AccountingEventExportType
from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.api.rest_helpers.history_events import edit_grouped_events_with_optional_fee
from rotkehlchen.api.rest_helpers.wrap import calculate_wrap_score
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
    FiatAsset,
    SolanaToken,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import ASSET_TYPES_EXCLUDED_FOR_USERS, AssetType
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
    get_manually_tracked_balances,
    remove_manually_tracked_balances,
)
from rotkehlchen.chain.accounts import OptionalBlockchainAccount, SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import check_airdrops, fetch_airdrops_metadata
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import PerformanceStatusFilter
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.chain.ethereum.modules.liquity.statistics import get_stats as get_liquity_stats
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import try_download_ens_avatar
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    query_balancer_data,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    query_curve_data,
)
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    query_gearbox_data,
)
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
)
from rotkehlchen.chain.evm.names import (
    find_ens_mappings,
    maybe_resolve_name,
    search_for_addresses_names,
)
from rotkehlchen.chain.evm.types import (
    ChainID,
    EvmIndexer,
    NodeName,
    RemoteDataQueryStatus,
    WeightedNode,
)
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.chain.zksync_lite.constants import ZKL_IDENTIFIER
from rotkehlchen.constants import HOUR_IN_SECONDS, ONE
from rotkehlchen.constants.limits import (
    FREE_USER_NOTES_LIMIT,
)
from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.constants.misc import (
    AIRDROPS_TOLERANCE,
    AVATARIMAGESDIR_NAME,
    DEFAULT_LOGLEVEL,
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    HTTP_STATUS_INTERNAL_DB_ERROR,
    IMAGESDIR_NAME,
    ZERO,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.timing import ENS_AVATARS_REFRESH
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.accounting_rules import DBAccountingRules, query_missing_accounting_rules
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, DBCalendar, ReminderEntry
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
    AssetsFilterQuery,
    CounterpartyAssetMappingsFilterQuery,
    CustomAssetsFilterQuery,
    DBFilterQuery,
    EvmTransactionsNotDecodedFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
    LevenshteinFilterQuery,
    LocationAssetMappingsFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.db.snapshots import DBSnapshot
from rotkehlchen.db.solanatx import DBSolanaTx
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
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import (
    AccountingError,
    AlreadyExists,
    DBSchemaError,
    DBUpgradeError,
    EthSyncError,
    GreenletKilledError,
    InputError,
    ModuleInactive,
    NotERC20Conformant,
    NotFoundError,
    RemoteError,
    SystemPermissionError,
    TagConstraintError,
)
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES, SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.utils import query_binance_exchange_pairs
from rotkehlchen.externalapis.github import Github
from rotkehlchen.externalapis.gnosispay import (
    fetch_gnosis_pay_siwe_nonce,
    init_gnosis_pay,
    verify_gnosis_pay_siwe_signature as external_verify_gnosis_pay_siwe_signature,
)
from rotkehlchen.externalapis.google_calendar import GoogleCalendarAPI
from rotkehlchen.externalapis.monerium import Monerium, init_monerium
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.asset_updates.manager import ASSETS_VERSION_KEY
from rotkehlchen.globaldb.assets_management import export_assets_from_file, import_assets_from_file
from rotkehlchen.globaldb.cache import (
    globaldb_delete_general_cache_values,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
    get_event_type_identifier,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import (
    generate_events_export_filename,
    history_event_to_staking_for_api,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.skipped import (
    export_skipped_external_events,
    get_skipped_external_events_summary,
    reprocess_skipped_external_events,
)
from rotkehlchen.history.types import NOT_EXPOSED_SOURCES, HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.icons import (
    check_if_image_is_cached,
    maybe_create_image_response,
)
from rotkehlchen.inquirer import CurrentPriceOracle, Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    PremiumCredentials,
    UserLimitType,
    get_user_limit,
    has_premium_check,
)
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.tasks.assets import (
    update_aave_v3_underlying_assets,
    update_spark_underlying_assets,
)
from rotkehlchen.tasks.events import (
    find_asset_movement_matches,
    get_unmatched_asset_movements,
    update_asset_movement_matched_event,
)
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    BLOCKSCOUT_TO_CHAINID,
    CHAINS_WITH_NODES,
    CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
    CHAINS_WITH_TRANSACTIONS,
    CHAINS_WITH_TRANSACTIONS_TYPE,
    CHAINS_WITH_TX_DECODING_TYPE,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_CHAINS_WITH_TRANSACTIONS,
    EVM_CHAINS_WITH_TRANSACTIONS_TYPE,
    EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE,
    SOLANA_TOKEN_KINDS_TYPE,
    SPAM_PROTOCOL,
    SUPPORTED_BITCOIN_CHAINS_TYPE,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_SUBSTRATE_CHAINS_TYPE,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    BlockchainAddress,
    BTCAddress,
    BTCTxId,
    CacheType,
    ChainType,
    ChecksumEvmAddress,
    CounterpartyAssetMappingDeleteEntry,
    CounterpartyAssetMappingUpdateEntry,
    Eth2PubKey,
    EVMTxHash,
    ExternalService,
    ExternalServiceApiCredentials,
    HexColorCode,
    HistoryEventQueryType,
    ListOfBlockchainAddresses,
    Location,
    LocationAssetMappingDeleteEntry,
    LocationAssetMappingUpdateEntry,
    ModuleName,
    OptionalChainAddress,
    Price,
    ProtocolsWithCache,
    PurgeableModuleName,
    SolanaAddress,
    SubstrateAddress,
    SupportedBlockchain,
    Timestamp,
    UserNote,
)
from rotkehlchen.utils.misc import combine_dicts, ts_ms_to_sec, ts_now
from rotkehlchen.utils.snapshots import parse_import_snapshot_data
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.manager import ChainManagerWithNodesMixin
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.exchanges.kraken import KrakenAccountType
    from rotkehlchen.exchanges.okx import OkxLocation
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

OK_RESULT = {'result': True, 'message': ''}


def _wrap_in_ok_result(result: Any, status_code: HTTPStatus | None = None) -> dict[str, Any]:
    result = {'result': result, 'message': ''}
    if status_code:
        result['status_code'] = status_code
    return result


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

    return make_response(
        (
            data,
            status_code,
            {
                'mimetype': 'application/json',
                'Content-Type': 'application/json',
                'rotki-log-result': log_result,  # popped by after request callback
            }),
    )


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
    This decorator reads the dictionary and transforms it to a Response object.
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
            if isinstance(response, Response):  # the case of returning a file in a async response
                return response
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


def register_post_download_cleanup(temp_file: Path) -> None:
    @after_this_request
    def do_cleanup(response: Response) -> Response:
        try:
            temp_file.unlink()
            temp_file.parent.rmdir()
        except (FileNotFoundError, PermissionError, OSError) as e:
            log.warning(f'Failed to clean up after download of {temp_file}: {e!s}')
        return response


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
        self.migration_lock = Semaphore()
        self.task_id = 0
        self.task_results: dict[int, Any] = {}

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
        self.rotkehlchen.api_task_greenlets.clear()
        log.debug('Cleaning up global DB')
        GlobalDBHandler().cleanup()
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
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        result_dict = {'result': new_settings | cache, 'message': ''}
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    def get_settings(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = process_result(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        result_dict = _wrap_in_ok_result(settings | cache)
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

    def delete_async_task(self, task_id: int) -> Response:
        """Tries to find and cancel the async task with the given task id"""
        with self.task_lock:
            for idx, greenlet in enumerate(self.rotkehlchen.api_task_greenlets):  # noqa: B007 # var used right after loop
                if (
                        greenlet.dead is False and
                        getattr(greenlet, 'task_id', None) == task_id
                ):
                    log.debug(f'Killing api task greenlet with {task_id=}')
                    greenlet.kill(exception=GreenletKilledError('Killed due to api request'))
                    break
            else:  # greenlet not found
                return api_response(wrap_in_fail_result(f'Did not cancel task with id {task_id} because it could not be found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        self.rotkehlchen.api_task_greenlets.pop(idx)  # also pop from greenlets
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @async_api_call()
    def get_exchange_rates(self, given_currencies: list[AssetWithOracles]) -> dict[str, Any]:
        currencies = given_currencies
        fiat_currencies: list[FiatAsset] = []
        asset_rates = {}
        for asset in currencies:
            if asset.is_fiat():
                fiat_currencies.append(asset.resolve_to_fiat_asset())
                continue

            usd_price = Inquirer.find_usd_price(asset)
            if usd_price == ZERO_PRICE:
                asset_rates[asset] = ZERO_PRICE
            else:
                asset_rates[asset] = Price(ONE / usd_price)

        asset_rates.update(Inquirer.get_fiat_usd_exchange_rates(fiat_currencies))  # type: ignore  # type narrowing does not work here
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
        response_dict: dict[str, Any] = {}
        response_dict['blockscout'] = {chain_id.to_name(): None for _, chain_id in BLOCKSCOUT_TO_CHAINID.items()}  # noqa: E501
        for credential in credentials_list:
            name, key_info = credential.serialize_for_api()
            if (chain := credential.service.get_chain_for_blockscout()) is not None:
                response_dict['blockscout'][chain.to_name()] = key_info
            else:
                response_dict[name] = key_info

        return api_response(_wrap_in_ok_result(response_dict), status_code=HTTPStatus.OK)

    def get_external_services(self) -> Response:
        return self._return_external_services_response()

    def add_external_services(self, services: list[ExternalServiceApiCredentials]) -> Response:
        should_renable_etherscan = False
        for x in services:
            if x.service.premium_only() and not has_premium_check(self.rotkehlchen.premium):
                return api_response(
                    wrap_in_fail_result(f'You can only use {x.service} with rotki premium'),
                    status_code=HTTPStatus.FORBIDDEN,
                )
            if x.service == ExternalService.GNOSIS_PAY:
                return api_response(
                    wrap_in_fail_result('GnosisPay credentials are set using /services/gnosispay/token'),  # noqa: E501
                    status_code=HTTPStatus.FORBIDDEN,
                )
            if x.service == ExternalService.ETHERSCAN:
                should_renable_etherscan = True

        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=services,
            )

        if should_renable_etherscan:
            self.rotkehlchen.chains_aggregator.renable_etherscan_indixer()

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
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: list[str] | None,
            okx_location: Optional['OkxLocation'],
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
            okx_location=okx_location,
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
            okx_location: Optional['OkxLocation'],
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
            okx_location=okx_location,
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

    def _query_all_exchange_balances(
            self,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
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
        else:  # Filter balances by threshold for each exchange
            if value_threshold is not None:
                filtered_balances = {}
                for location, balances in final_balances.items():
                    filtered_balances[location] = {
                        asset: balance for asset, balance in balances.items()
                        if balance.value > value_threshold
                    }
                result = filtered_balances
            else:
                result = final_balances
            status_code = HTTPStatus.OK

        return {'result': result, 'message': error_msg, 'status_code': status_code}

    @async_api_call()
    def query_exchange_history_events(
            self,
            location: Location,
            name: str | None,
    ) -> dict[str, Any]:
        """Queries new history events for the specified exchange and saves them in the database."""
        try:
            self.rotkehlchen.exchange_manager.query_exchange_history_events(
                name=name,
                location=location,
            )
        except RemoteError as e:
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.BAD_GATEWAY,
            )
        except InputError as e:
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.CONFLICT,
            )

        return OK_RESULT

    @async_api_call()
    def query_exchange_history_events_in_range(
            self,
            location: Location,
            name: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> dict[str, Any]:
        try:
            total_events, stored_events, skipped_events, actual_end_ts = (
                self.rotkehlchen.exchange_manager.requery_exchange_history_events(
                    location=location,
                    name=name,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
            )
        except RemoteError as e:
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.BAD_GATEWAY,
            )
        except (InputError, DeserializationError, sqlcipher.IntegrityError) as e:  # pylint: disable=no-member
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.CONFLICT,
            )

        result = {
            'queried_events': total_events,
            'stored_events': stored_events,
            'skipped_events': skipped_events,
            'actual_end_ts': actual_end_ts,
        }

        return _wrap_in_ok_result(result)

    @async_api_call()
    def query_exchange_balances(
            self,
            location: Location | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        if location is None:
            # Query all exchanges
            return self._query_all_exchange_balances(
                ignore_cache=ignore_cache,
                value_threshold=value_threshold,
            )

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

        # Filter balances by threshold for a single exchange
        if value_threshold is not None:
            balances = {
                asset: balance for asset, balance in balances.items()
                if balance.value > value_threshold
            }

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
                'type': blockchain.get_chain_type().serialize(),
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
            value_threshold: FVal | None = None,
            addresses: ListOfBlockchainAddresses | None = None,
    ) -> dict[str, Any]:
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            balances = self.rotkehlchen.chains_aggregator.query_balances(
                blockchain=blockchain,
                ignore_cache=ignore_cache,
                addresses=addresses,
            )

            # Filter balances before serialization
            if value_threshold is not None:
                for _, chain_balances in balances.per_account:
                    filtered_balances: dict[BlockchainAddress, BalanceSheet | Balance] = {}
                    for account, account_data in chain_balances.items():
                        if isinstance(account_data, BalanceSheet):
                            filtered_assets: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501
                            filtered_liabilities: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501

                            for asset, asset_balances in account_data.assets.items():
                                for key, balance in asset_balances.items():
                                    if balance.value > value_threshold:
                                        filtered_assets[asset][key] = balance

                            for asset, asset_balances in account_data.liabilities.items():
                                for key, balance in asset_balances.items():
                                    if balance.value > value_threshold:
                                        filtered_liabilities[asset][key] = balance

                            if len(filtered_assets) != 0 or len(filtered_liabilities) != 0:
                                new_balance_sheet = BalanceSheet(
                                    assets=filtered_assets,
                                    liabilities=filtered_liabilities,
                                )
                                filtered_balances[account] = new_balance_sheet
                        elif isinstance(account_data, Balance):
                            # For BTC and BCH, account_data is a single Balance object
                            if account_data.value > value_threshold:
                                filtered_balances[account] = account_data

                    chain_balances.clear()
                    chain_balances.update(filtered_balances)

            result = balances.serialize()

        except EthSyncError as e:
            msg = str(e)
            status_code = HTTPStatus.CONFLICT
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY

        return {'result': result, 'message': msg, 'status_code': status_code}

    @async_api_call()
    def get_xpub_balances(
            self,
            xpub_data: 'XpubData',
            ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Get balances for all addresses derived from an xpub

        If ignore_cache is True, checks for new xpub addresses and includes them.
        If ignore_cache is False, uses only existing derived addresses from database.
        """
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            if ignore_cache:
                XpubManager(chains_aggregator=self.rotkehlchen.chains_aggregator).check_for_new_xpub_addresses(
                    blockchain=xpub_data.blockchain,
                    xpub_data=xpub_data,
                )

            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                addresses = self.rotkehlchen.data.db.get_xpub_derived_addresses(cursor=cursor, xpub_data=xpub_data)  # noqa: E501

            result = self.rotkehlchen.chains_aggregator.query_balances(
                blockchain=xpub_data.blockchain,
                ignore_cache=ignore_cache,
                addresses=addresses,
            ).serialize()

        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY

        return {'result': result, 'message': msg, 'status_code': status_code}

    def _ensure_event_tx_existence(self, event: 'HistoryBaseEntry') -> Response | None:
        """Check if an evm/evmlike event tx is present in the DB and if not, query it from onchain.
        Returns None if the tx was successfully found, or if the event is not an evm event,
        otherwise returns an error response.
        """
        if not isinstance(event, EvmEvent):
            return None  # don't try to check the tx if we're not add/editing an EVM event.

        blockchain = SupportedBlockchain.from_location(event.location)  # type: ignore[arg-type]  # EVM event locations will work with from_location
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            table = 'zksynclite_transactions' if blockchain.is_evmlike() else 'evm_transactions'
            if cursor.execute(
                f'SELECT COUNT(*) FROM {table} WHERE tx_hash=?',
                (event.tx_ref,),
            ).fetchone()[0] != 0:
                return None

        try:
            associated_address = deserialize_evm_address(event.location_label)  # type: ignore  # if label is None TypeError will be caught
        except (DeserializationError, TypeError):
            return api_response(
                result=wrap_in_fail_result('The location_label must be set to a valid EVM address to pull the tx for the given hash from onchain.'),  # noqa: E501
                status_code=HTTPStatus.BAD_REQUEST,
            )

        if blockchain.is_evmlike():
            if self.rotkehlchen.chains_aggregator.zksync_lite.query_single_transaction(
                tx_hash=event.tx_ref,
                concerning_address=associated_address,
            ) is not None:
                return None
        else:  # chain is EVM
            with suppress(KeyError, DeserializationError, RemoteError, AlreadyExists, InputError):
                self.rotkehlchen.chains_aggregator.get_chain_manager(  # type: ignore[call-overload]  # Will only be EVM chains
                    blockchain=blockchain,
                ).transactions.add_transaction_by_hash(
                    tx_hash=event.tx_ref,
                    associated_address=associated_address,
                )
                return None

        return api_response(
            result=wrap_in_fail_result(f'The provided transaction hash does not exist for {event.location.name.lower()}.'),  # noqa: E501
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def add_history_events(self, events: list['HistoryBaseEntry']) -> Response:
        """Add list of history events to DB. Returns identifier of first event.
        The first event is the main event, subsequent events are related (e.g. fees).
        """
        if (error_response := self._ensure_event_tx_existence(events[0])) is not None:
            return error_response

        db = DBHistoryEvents(self.rotkehlchen.data.db)
        main_identifier = None
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                for idx, event in enumerate(events):
                    identifier = db.add_history_event(
                        write_cursor=cursor,
                        event=event,
                        mapping_values={
                            HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED,
                        },
                    )
                    if idx == 0:
                        main_identifier = identifier
        except (sqlcipher.DatabaseError, OverflowError) as e:  # pylint: disable=no-member
            error_msg = f'Failed to add event to the DB due to a DB error: {e!s}'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        if main_identifier is None:
            error_msg = 'Failed to add event to the DB. It already exists'
            return api_response(wrap_in_fail_result(error_msg), status_code=HTTPStatus.CONFLICT)

        # success
        result_dict = _wrap_in_ok_result({'identifier': main_identifier})
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def edit_history_events(
            self,
            events: list['HistoryBaseEntry'],
            identifiers: list[int] | None,
    ) -> Response:
        if (error_response := self._ensure_event_tx_existence(events[0])) is not None:
            return error_response

        events_db = DBHistoryEvents(self.rotkehlchen.data.db)
        if (events_type := events[0].entry_type) in {
            HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
            HistoryBaseEntryType.SWAP_EVENT,
            HistoryBaseEntryType.EVM_SWAP_EVENT,
            HistoryBaseEntryType.SOLANA_SWAP_EVENT,
        }:
            try:
                with events_db.db.conn.write_ctx() as write_cursor:
                    edit_grouped_events_with_optional_fee(
                        events_db=events_db,
                        write_cursor=write_cursor,
                        events=events,
                        events_type=events_type,
                        identifiers=identifiers,
                    )
            except InputError as e:
                return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
            else:
                return api_response(OK_RESULT, status_code=HTTPStatus.OK)

        try:  # case where we just edit the events
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                for event in events:
                    events_db.edit_history_event(
                        event=event,
                        write_cursor=write_cursor,
                    )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

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
            new_name: str | None,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.edit_tag(
                    write_cursor=cursor,
                    name=name,
                    new_name=new_name,
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
                (premium_api_key != '' and premium_api_secret == '') or
                (premium_api_secret != '' and premium_api_key == '')
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
                'settings': process_result(self.rotkehlchen.get_settings(cursor)) |
                self.rotkehlchen.data.db.get_cache_for_api(cursor),
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
            settings |= self.rotkehlchen.data.db.get_cache_for_api(cursor)

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
        self.rotkehlchen.api_task_greenlets.clear()
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
            return api_response(result_dict, status_code=HTTPStatus.FORBIDDEN)

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
        assets, assets_found = GlobalDBHandler.retrieve_assets(userdb=self.rotkehlchen.data.db, filter_query=filter_query)  # noqa: E501
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
            asset_mappings, asset_collections = GlobalDBHandler.get_assets_mappings(identifiers)
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
        result = GlobalDBHandler.search_assets(
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
        # There is no good way to figure out if an asset already exists in the DB
        # Best approximation we can do is this.
        if isinstance(asset, EvmToken):
            try:
                asset.check_existence()  # for evm token we know the uniqueness of the identifier
                identifiers = [asset.identifier]
            except UnknownAsset:
                identifiers = None
        else:
            identifiers = GlobalDBHandler.check_asset_exists(asset)

        if identifiers is not None:
            return api_response(
                result=wrap_in_fail_result(
                    f'Failed to add {asset.asset_type!s} {asset.name} '
                    f'since it already exists. Existing ids: {",".join(identifiers)}'),
                status_code=HTTPStatus.CONFLICT,
            )
        try:
            GlobalDBHandler.add_asset(asset)
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
            GlobalDBHandler.edit_user_asset(asset)
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

            GlobalDBHandler.delete_asset_by_identifier(identifier)
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
            return OK_RESULT
        return wrap_in_fail_result(msg, status_code=HTTPStatus.CONFLICT)

    def query_netvalue_data(self, include_nfts: bool) -> Response:
        from_ts = Timestamp(0)
        premium = self.rotkehlchen.premium

        if premium is None or not premium.is_active():
            today = datetime.datetime.now(tz=datetime.UTC)
            start_of_day_today = datetime.datetime(today.year, today.month, today.day, tzinfo=datetime.UTC)  # noqa: E501
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
        assert self.rotkehlchen.premium is not None, 'Should not be None since we use @require_premium_user() decorator'  # noqa: E501
        result_dict = {'result': None, 'message': ''}
        try:
            result = self.rotkehlchen.premium.query_premium_components()
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
        try:
            report_id, error_or_empty = self.rotkehlchen.process_history(
                start_ts=from_timestamp,
                end_ts=to_timestamp,
            )
        except AccountingError as e:
            return {
                'result': e.report_id,
                'message': str(e),
                'status_code': HTTPStatus.CONFLICT,
            }

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
        error_or_empty, events = self.rotkehlchen.history_querying_manager.get_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            has_premium=has_premium_check(self.rotkehlchen.premium),
        )
        if error_or_empty != '':
            return wrap_in_fail_result(error_or_empty, status_code=HTTPStatus.CONFLICT)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rotkehlchen.get_settings(cursor)
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
            ignored_ids = self.rotkehlchen.data.db.get_ignored_action_ids(cursor)
        debug_info = {
            'events': [entry.serialize_for_debug_import() for entry in events],
            'settings': settings.serialize() | cache,
            'ignored_events_ids': list(ignored_ids),
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
        def import_history_debug(self, filepath: Path) -> dict[str, Any]:
            """Imports the PnL debug data for processing and report generation"""
            json_importer = DebugHistoryImporter(self.rotkehlchen.data.db)
            success, msg, data = json_importer.import_history_debug(filepath=filepath)

            if success is False:
                return wrap_in_fail_result(
                    message=msg,
                    status_code=HTTPStatus.CONFLICT,
                )
            log.debug(f'extracted {len(data["events"])} events from {filepath}')
            self.rotkehlchen.accountant.process_history(
                start_ts=Timestamp(data['pnl_settings']['from_timestamp']),
                end_ts=Timestamp(data['pnl_settings']['to_timestamp']),
                events=data['events'],
            )
            return OK_RESULT

    @async_api_call()
    def export_accounting_rules(self, directory_path: Path | None) -> dict[str, Any]:
        """Exports all the accounting rules and linked properties into a json file
        in the given directory."""
        db_accounting = DBAccountingRules(self.rotkehlchen.data.db)
        rules_and_properties = db_accounting.get_accounting_rules_and_properties()

        if directory_path is None:
            return _wrap_in_ok_result(rules_and_properties)

        directory_path.mkdir(parents=True, exist_ok=True)
        try:
            with open(directory_path / 'accounting_rules.json', mode='w', encoding='utf-8') as file:  # noqa: E501
                json.dump(rules_and_properties, file)
        except (PermissionError, json.JSONDecodeError) as e:
            return wrap_in_fail_result(
                message=f'Failed to export accounting rules due to: {e!s}',
                status_code=HTTPStatus.BAD_REQUEST,
            )

        return OK_RESULT

    @async_api_call()
    def import_accounting_rules(self, filepath: Path) -> dict[str, Any]:
        """Imports the accounting rules from the given json file and stores them in the DB."""
        try:
            with open(filepath, encoding='utf-8') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            return wrap_in_fail_result(
                message=f'Failed to import accounting rules due to: {e!s}',
                status_code=HTTPStatus.BAD_REQUEST,
            )
        except PermissionError as e:
            return wrap_in_fail_result(
                message=f'Failed to import accounting rules due to: {e!s}',
                status_code=HTTPStatus.CONFLICT,
            )

        db_accounting_rules = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            success, error_msg = db_accounting_rules.import_accounting_rules(
                accounting_rules=json_data['accounting_rules'],
                linked_properties=json_data['linked_properties'],
            )
        except KeyError as e:
            success = False
            error_msg = f'Key {e!s} not found in the accounting rules json file'

        if success is False:
            return wrap_in_fail_result(
                message=error_msg,
                status_code=HTTPStatus.CONFLICT,
            )

        for rule_info in json_data['accounting_rules'].values():
            self._invalidate_cache_for_accounting_rule(
                event_ids=rule_info['event_ids'],
                event_type=HistoryEventType.deserialize(rule_info['event_type']),
                event_subtype=HistoryEventSubType.deserialize(rule_info['event_subtype']),
                counterparty=rule_info['counterparty'],
            )

        return OK_RESULT

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
            register_post_download_cleanup(Path(zipfile))
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
            (
                added_accounts,
                existed_accounts,
                failed_accounts,
                no_activity_accounts,
                evm_contract_addresses,
            ) = self.rotkehlchen.add_evm_accounts(account_data=account_data)
        except (EthSyncError, TagConstraintError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        result_dicts: dict[str, dict[ChecksumEvmAddress, list[str]]] = defaultdict(lambda: defaultdict(list))  # noqa: E501

        all_key = 'all'  # key used when all the evm chains are returned
        for response_key, list_of_accounts in (
            ('added', added_accounts),
            ('failed', failed_accounts),
            ('existed', existed_accounts),
            ('no_activity', no_activity_accounts),
            ('evm_contracts', evm_contract_addresses),
        ):
            for chain, address in list_of_accounts:
                result_dicts[response_key][address].append(chain.serialize())
                if len(result_dicts[response_key][address]) == len(SUPPORTED_EVM_EVMLIKE_CHAINS):
                    result_dicts[response_key][address] = [all_key]

        return _wrap_in_ok_result(result_dicts)

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
            chain: SUPPORTED_EVM_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE,
            account_data: list[SingleBlockchainAccountData[SubstrateAddress]],
    ) -> dict[str, Any]:
        ...

    @overload
    def add_single_blockchain_accounts(
            self,
            chain: SUPPORTED_BITCOIN_CHAINS_TYPE,
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

    @async_api_call()
    def edit_chain_type_accounts_labels(
            self,
            accounts: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        """Edit the provided accounts in all the chains where they are present.
        The names in the address book are replaced with the one provided and the tags
        are also replaced in all the supported chains where the address is present.
        """
        try:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                self.rotkehlchen.edit_chain_type_accounts_labels(
                    cursor=cursor,
                    account_data=accounts,
                )
        except TagConstraintError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)

        return OK_RESULT

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

    @async_api_call()
    def remove_chain_type_accounts(
            self,
            chain_type: ChainType,
            accounts: ListOfBlockchainAddresses,
    ) -> dict[str, Any]:
        """Remove an address from multiple chains of the same type"""
        try:
            self.rotkehlchen.remove_chain_type_accounts(
                chain_type=chain_type,
                accounts=accounts,
            )
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)

        return OK_RESULT

    def _get_manually_tracked_balances(self, value_threshold: FVal | None) -> dict[str, Any]:
        db_entries = get_manually_tracked_balances(
            db=self.rotkehlchen.data.db,
            balance_type=None,
            include_entries_with_missing_assets=True,
        )
        # Filter balances if threshold is set
        if value_threshold is not None:
            db_entries = [
                entry for entry in db_entries
                if entry.value.value > value_threshold
            ]

        balances = process_result({'balances': db_entries})
        return _wrap_in_ok_result(balances)

    @async_api_call()
    def get_manually_tracked_balances(self, value_threshold: FVal | None) -> dict[str, Any]:
        return self._get_manually_tracked_balances(value_threshold=value_threshold)

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

        return self._get_manually_tracked_balances(value_threshold=None)

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

    def add_ignored_assets(self, assets_to_ignore: list[Asset]) -> Response:
        """Add the provided assets to the list of ignored assets"""
        newly_ignored, already_ignored = self.rotkehlchen.data.add_ignored_assets(assets=assets_to_ignore)  # noqa: E501
        result = {'successful': list(newly_ignored), 'no_action': list(already_ignored)}
        return api_response(_wrap_in_ok_result(process_result(result)), status_code=HTTPStatus.OK)

    def remove_ignored_assets(self, assets: list[Asset]) -> Response:
        succeeded, no_action = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        result = {'successful': list(succeeded), 'no_action': list(no_action)}
        return api_response(_wrap_in_ok_result(process_result(result)), status_code=HTTPStatus.OK)

    def add_ignored_action_ids(self, action_ids: list[str]) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.add_to_ignored_action_ids(
                    write_cursor=cursor,
                    identifiers=action_ids,
                )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def remove_ignored_action_ids(
            self,
            action_ids: list[str],
    ) -> Response:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.remove_from_ignored_action_ids(
                    write_cursor=cursor,
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

    def get_lido_csm_node_operators(self) -> Response:
        return api_response(
            _wrap_in_ok_result(self._serialize_lido_csm_node_operators()),
            status_code=HTTPStatus.OK,
        )

    def _serialize_lido_csm_node_operators(self) -> list[dict[str, Any]]:
        """Serialize the tracked Lido node operators as returned by the API."""
        entries = DBLidoCsm(self.rotkehlchen.data.db).get_node_operators()
        return [
            {
                'address': entry.address,
                'node_operator_id': entry.node_operator_id,
                'metrics': entry.metrics.serialize() if entry.metrics else None,
            }
            for entry in entries
        ]

    def add_lido_csm_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
    ) -> Response:
        try:
            DBLidoCsm(self.rotkehlchen.data.db).add_node_operator(
                address=address,
                node_operator_id=node_operator_id,
            )
        except (InputError, NotFoundError) as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        # Compute and persist metrics for the newly added operator. If it fails
        # we still return the list but metrics will be empty until refreshed.
        status_code = HTTPStatus.OK
        message = ''
        try:
            metrics = LidoCsmMetricsFetcher(
                evm_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
            ).get_operator_stats(node_operator_id)
            DBLidoCsm(self.rotkehlchen.data.db).set_metrics(
                node_operator_id=node_operator_id,
                metrics=metrics,
            )
        except RemoteError as e:
            log.error(
                f'Failed to fetch Lido CSM metrics for new operator {node_operator_id}: {e}',
            )
            status_code = HTTPStatus.BAD_GATEWAY
            message = f'Failed to fetch metrics for node operator {node_operator_id}'

        payload = _wrap_in_ok_result(self._serialize_lido_csm_node_operators())
        if message:
            payload['message'] = message
        return api_response(payload, status_code=status_code)

    def remove_lido_csm_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
    ) -> Response:
        try:
            DBLidoCsm(self.rotkehlchen.data.db).remove_node_operator(
                address=address,
                node_operator_id=node_operator_id,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return api_response(
            _wrap_in_ok_result(self._serialize_lido_csm_node_operators()),
            status_code=HTTPStatus.OK,
        )

    def refresh_lido_csm_metrics(self) -> Response:
        """Recompute metrics for a given node operator id,
        or for all tracked operators if omitted."""
        metrics_fetcher = LidoCsmMetricsFetcher(
            evm_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        )

        result = []
        failed_ids: list[int] = []
        for entry in DBLidoCsm(self.rotkehlchen.data.db).get_node_operators():
            try:
                metrics = metrics_fetcher.get_operator_stats(entry.node_operator_id)
                metrics_payload = metrics.serialize()
                DBLidoCsm(self.rotkehlchen.data.db).set_metrics(
                    node_operator_id=entry.node_operator_id,
                    metrics=metrics,
                )
            except RemoteError as e:
                log.error(f'Failed to refresh Lido CSM metrics for {entry}: {e}')
                metrics_payload = None
                failed_ids.append(entry.node_operator_id)

            result.append({
                'address': entry.address,
                'node_operator_id': entry.node_operator_id,
                'metrics': metrics_payload,
            })
        payload = _wrap_in_ok_result(result)
        if failed_ids:
            payload['message'] = (
                'Failed to refresh metrics for node operators: '
                f"{', '.join(str(node_id) for node_id in failed_ids)}"
            )
            return api_response(payload, status_code=HTTPStatus.BAD_GATEWAY)
        return api_response(payload, status_code=HTTPStatus.OK)

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
    def get_eth2_staking_performance(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            limit: int,
            offset: int,
            ignore_cache: bool,
            addresses: list[ChecksumEvmAddress] | None,
            validator_indices: list[int] | None,
            status: PerformanceStatusFilter,
    ) -> dict[str, Any]:
        eth2 = self.rotkehlchen.chains_aggregator.get_module('eth2')
        if eth2 is None:
            return {'result': None, 'message': 'Cant query eth2 staking performance since eth2 module is not active', 'status_code': HTTPStatus.CONFLICT}  # noqa: E501

        try:
            result = eth2.get_performance(
                from_ts=from_ts,
                to_ts=to_ts,
                limit=limit,
                offset=offset,
                ignore_cache=ignore_cache,
                addresses=addresses,
                validator_indices=validator_indices,
                status=status,
            )
        except PremiumPermissionError as e:
            response_data = {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.FORBIDDEN,
            }
            if e.extra_dict:  # include any extra information for the error
                response_data.update(e.extra_dict)
            return response_data
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return {'result': process_result(result), 'message': ''}

    @async_api_call()
    def get_eth2_validators(
            self,
            ignore_cache: bool,
            validator_indices: set[int] | None,
    ) -> dict[str, Any]:
        try:
            validators = self.rotkehlchen.chains_aggregator.get_eth2_validators(
                ignore_cache=ignore_cache,
                validator_indices=validator_indices,
            )
        except ModuleInactive as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        entries_found = len(validators)

        return _wrap_in_ok_result(result={
            'entries': [x.serialize() for x in validators],
            'entries_found': entries_found,
            'entries_limit': -1,
        }, status_code=HTTPStatus.OK)

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
            response_data = {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.FORBIDDEN,
            }
            if e.extra_dict:  # include any extra information for the error
                response_data.update(e.extra_dict)
            return response_data
        except (InputError, ModuleInactive) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': ''}

    def edit_eth2_validator(self, validator_index: int, ownership_proportion: FVal) -> Response:
        try:
            self.rotkehlchen.chains_aggregator.edit_eth2_validator(
                validator_index=validator_index,
                ownership_proportion=ownership_proportion,
            )
        except PremiumPermissionError as e:
            response_data = wrap_in_fail_result(str(e))
            if e.extra_dict:  # include any extra information for the error
                response_data.update(e.extra_dict)
            return api_response(response_data, status_code=HTTPStatus.FORBIDDEN)
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
    def redecode_eth2_block_events(
            self,
            block_numbers: list[int] | None,
    ) -> dict[str, Any]:
        DBEth2(self.rotkehlchen.data.db).redecode_block_production_events(block_numbers)
        return OK_RESULT

    @async_api_call()
    def get_airdrops(self) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                data = check_airdrops(
                    addresses=self.rotkehlchen.data.db.get_evm_accounts(cursor),
                    database=self.rotkehlchen.data.db,
                    tolerance_for_amount_check=AIRDROPS_TOLERANCE,
                )
        except RemoteError as e:
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

        # node will be connected automatically when the order requires it
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def update_and_connect_rpc_node(self, node: WeightedNode) -> Response:
        """
        Updates the RPC node matching the provided identifier in the database, then
        forces a reconnection by clearing the cached Web3 object and re-establishing
        connections to all nodes.
        """
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            # get the current rpc endpoint so we can identify the node and remove it
            # from node_inquirer.rpc_mapping
            if (old_endpoint := cursor.execute(
                'SELECT endpoint FROM rpc_nodes WHERE identifier=?',
                (node.identifier,),
            ).fetchone()) is None:
                return api_response(
                    wrap_in_fail_result(message=f"Node with identifier {node.identifier} doesn't exist"),  # noqa: E501
                    status_code=HTTPStatus.CONFLICT,
                )

        try:
            self.rotkehlchen.data.db.update_rpc_node(node)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=node.node_info.blockchain,
            only_active=True,
        )

        manager: ChainManagerWithNodesMixin = self.rotkehlchen.chains_aggregator.get_chain_manager(  # type: ignore  # will be manager with nodes
            blockchain=node.node_info.blockchain,
        )
        for entry in list(manager.node_inquirer.rpc_mapping):  # remove old node from memory
            if entry.endpoint == old_endpoint:
                manager.node_inquirer.rpc_mapping.pop(entry, None)
                break
        else:
            log.debug(
                f'Failed to find node with endpoint {old_endpoint} in web3 mappings. Skipping',
            )

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

    @async_api_call()
    def connect_rpc_node(
            self,
            identifier: int | None,
            blockchain: SupportedBlockchain,
    ) -> dict[str, Any]:
        """Attempt a connection to a node and return status"""
        if blockchain not in CHAINS_WITH_NODES:
            return {
                'result': None,
                'message': f'{blockchain} nodes are connected at login',
                'status_code': HTTPStatus.BAD_REQUEST,
            }

        bindings: tuple[Any]
        if identifier is not None:
            query, bindings = 'SELECT name, endpoint, owned, blockchain FROM rpc_nodes WHERE identifier=?', (identifier,)  # noqa: E501
        else:
            query, bindings = 'SELECT name, endpoint, owned, blockchain FROM rpc_nodes WHERE blockchain=?', (blockchain.value,)  # noqa: E501

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if len(db_entries := cursor.execute(query, bindings).fetchall()) == 0:
                return {
                    'result': None,
                    'message': 'RPC node not found',
                    'status_code': HTTPStatus.BAD_REQUEST,
                }

        manager: ChainManagerWithNodesMixin = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)  # type: ignore  # will be manager with nodes  # noqa: E501
        errors = []
        for row in db_entries:
            success, msg = manager.node_inquirer.attempt_connect(node=(node := NodeName(
                name=row[0],
                endpoint=row[1],
                owned=bool(row[2]),
                blockchain=blockchain,  # type: ignore  # we have already limited the set of blockchains
            )))
            if success is False:
                errors.append({'name': node.name, 'error': msg})

        return {'result': {'errors': errors}, 'status_code': HTTPStatus.OK}

    def purge_module_data(self, module_name: PurgeableModuleName | None) -> Response:
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
    def get_amm_platform_balances(
            self,
            module: Literal['uniswap', 'sushiswap'],
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

    def reset_eth_staking_data(
            self,
            entry_type: Literal[HistoryBaseEntryType.ETH_BLOCK_EVENT, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT],  # noqa: E501
    ) -> Response:
        DBHistoryEvents(self.rotkehlchen.data.db).reset_eth_staking_data(entry_type=entry_type)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _delete_zksync_tx_data(
            self,
            write_cursor: 'DBCursor',
            tx_hash: EVMTxHash | None = None,
    ) -> None:
        """Purge ZKSyncLite transaction data from the DB."""
        querystr, bindings = 'DELETE FROM zksynclite_transactions', ()
        if tx_hash is not None:
            querystr += ' WHERE tx_hash=?'
            bindings = (tx_hash,)  # type: ignore

        write_cursor.execute(querystr, bindings)

    def _delete_bitcoin_tx_data(
            self,
            write_cursor: 'DBCursor',
            cache_key: Literal[DBCacheDynamic.LAST_BTC_TX_BLOCK, DBCacheDynamic.LAST_BCH_TX_BLOCK],
    ) -> None:
        """Purge last queried bitcoin tx block from the cache."""
        self.rotkehlchen.data.db.delete_dynamic_caches(
            write_cursor=write_cursor,
            key_parts=[cache_key.value[0].removesuffix('{address}')],
        )

    @overload
    def delete_blockchain_transaction_data(
            self,
            chain: CHAINS_WITH_TRANSACTIONS_TYPE | None,
            tx_ref: None,
    ) -> Response:
        ...

    @overload
    def delete_blockchain_transaction_data(
            self,
            chain: EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE,
            tx_ref: EVMTxHash,
    ) -> Response:
        ...

    @overload
    def delete_blockchain_transaction_data(
            self,
            chain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
            tx_ref: BTCTxId,
    ) -> Response:
        ...

    @overload
    def delete_blockchain_transaction_data(
            self,
            chain: Literal[SupportedBlockchain.SOLANA],
            tx_ref: Signature,
    ) -> Response:
        ...

    def delete_blockchain_transaction_data(
            self,
            chain: CHAINS_WITH_TRANSACTIONS_TYPE | None,
            tx_ref: EVMTxHash | Signature | BTCTxId | None,
    ) -> Response:
        """Delete transactions and events.
        May be limited to a specific chain or further limited to a specific tx hash on that chain.

        Note that the overloads here are too complicated for mypy to understand currently, so
        we have to use a number of type ignores.
        """
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            # First delete events related to the transactions being removed
            if tx_ref is not None:
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=[tx_ref],
                    location=Location.from_chain(chain),  # type: ignore[arg-type] # chain cannot be None if tx_ref is set
                )
            else:
                chains = [chain] if chain is not None else CHAINS_WITH_TRANSACTIONS
                for chain_location in [Location.from_chain(i_chain) for i_chain in chains]:
                    dbevents.reset_events_for_redecode(
                        write_cursor=write_cursor,
                        location=chain_location,
                    )

            # Then delete the transaction data
            if not chain:  # no chain specified, delete data for all supported types.
                DBEvmTx(self.rotkehlchen.data.db).delete_evm_transaction_data(write_cursor=write_cursor)
                DBSolanaTx(self.rotkehlchen.data.db).delete_transaction_data(write_cursor=write_cursor)
                self._delete_zksync_tx_data(write_cursor=write_cursor)
                for cache_key in (DBCacheDynamic.LAST_BTC_TX_BLOCK, DBCacheDynamic.LAST_BCH_TX_BLOCK):  # noqa: E501
                    self._delete_bitcoin_tx_data(write_cursor=write_cursor, cache_key=cache_key)
            elif chain.is_evm():
                DBEvmTx(self.rotkehlchen.data.db).delete_evm_transaction_data(
                    write_cursor=write_cursor,
                    chain=chain,  # type: ignore[arg-type] # mypy doesn't understand the is_evm check
                    tx_hash=tx_ref,  # type: ignore[arg-type] # will be EVMTxHash
                )
            elif chain == SupportedBlockchain.SOLANA:
                DBSolanaTx(self.rotkehlchen.data.db).delete_transaction_data(
                    write_cursor=write_cursor,
                    signature=tx_ref,  # type: ignore[arg-type]  # will be Signature
                )
            elif chain == SupportedBlockchain.ZKSYNC_LITE:
                self._delete_zksync_tx_data(write_cursor=write_cursor, tx_hash=tx_ref)  # type: ignore[arg-type] # will be EVMTxHash
            elif chain.is_bitcoin() and tx_ref is None:
                # only delete cached btc/bch last tx block if we're deleting all events.
                self._delete_bitcoin_tx_data(
                    write_cursor=write_cursor,
                    cache_key=DBCacheDynamic.LAST_BTC_TX_BLOCK if chain == SupportedBlockchain.BITCOIN else DBCacheDynamic.LAST_BCH_TX_BLOCK,  # noqa: E501
                )

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @async_api_call()
    def refresh_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            accounts: list[OptionalBlockchainAccount] | None,
    ) -> dict[str, Any]:
        blockchain_addresses: dict[CHAINS_WITH_TRANSACTIONS_TYPE, ListOfBlockchainAddresses]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if accounts is None or len(accounts) == 0:  # No accounts specified. Get all accounts from DB.  # noqa: E501
                blockchain_addresses = {
                    chain: addr_list for chain in CHAINS_WITH_TRANSACTIONS
                    if len(addr_list := self.rotkehlchen.data.db.get_single_blockchain_addresses(
                        cursor=cursor,
                        blockchain=chain,
                    )) != 0
                }
            else:  # Use specified accounts, getting all chains in which an account is tracked if the chain is not specified.  # noqa: E501
                blockchain_addresses = defaultdict(list)
                unspecified_chain_addresses: list[BlockchainAddress] = []
                for account in accounts:
                    if account.chain is not None and account.chain in CHAINS_WITH_TRANSACTIONS:
                        blockchain_addresses[account.chain].append(account.address)  # type: ignore  # there will only be accounts for chains with transactions here
                    else:
                        unspecified_chain_addresses.append(account.address)

                if len(unspecified_chain_addresses) > 0:
                    for address, chain in self.rotkehlchen.data.db.get_blockchains_for_accounts(
                        cursor=cursor,
                        accounts=unspecified_chain_addresses,
                    ):
                        if chain not in CHAINS_WITH_TRANSACTIONS:
                            continue

                        blockchain_addresses[chain].append(address)  # type: ignore  # same as above

        result, message, status_code = True, '', HTTPStatus.OK
        for blockchain, addresses in blockchain_addresses.items():
            try:
                self.rotkehlchen.chains_aggregator.get_chain_manager(
                    blockchain=blockchain,
                ).query_transactions(
                    addresses=addresses,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )
            except AttributeError:
                result = False
                message = f'Transaction querying for {blockchain} is not implemented.'
                status_code = HTTPStatus.BAD_REQUEST
                break
            except RemoteError as e:
                result, message, status_code = False, str(e), HTTPStatus.BAD_GATEWAY
                break
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                result, message, status_code = False, str(e), HTTPStatus.BAD_REQUEST
                break

        return {'result': result, 'message': message, 'status_code': status_code}

    @async_api_call()
    def decode_given_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            tx_refs: list[EVMTxHash | Signature],
            delete_custom: bool,
            custom_indexers_order: list[EvmIndexer] | None = None,
    ) -> dict[str, Any]:
        """Re-pull data for the specified tx_refs in the given chain
        and redecode all related events.
        """
        decode_function: Callable[[EVMTxHash, bool], None] | Callable[[Signature, bool], None]
        if chain.is_evm():
            decode_function = partial(
                lambda _tx_ref, _delete_custom, _chain: self._decode_given_evm_tx(
                    chain=_chain,
                    tx_ref=_tx_ref,
                    delete_custom=_delete_custom,
                ),
                _chain=chain,
            )
        elif chain.is_evmlike():
            decode_function = self._decode_given_evmlike_tx
        else:  # solana
            decode_function = self._decode_given_solana_tx

        success, message, status_code = True, '', HTTPStatus.OK
        indexer_order_customized = CachedSettings().evm_indexers_order_override_var.set(tuple(custom_indexers_order)) if custom_indexers_order else None  # noqa: E501
        try:
            for tx_ref in tx_refs:
                try:
                    decode_function(tx_ref, delete_custom)  # type: ignore[arg-type]  # schema ensures all tx refs match the type required for the given chain
                except (RemoteError, DeserializationError, InputError) as e:
                    success = False
                    message = f'Failed to request {chain.name.lower()} transaction decoding due to {e!s}'  # noqa: E501
                    status_code = HTTPStatus.CONFLICT if isinstance(e, InputError) else HTTPStatus.BAD_GATEWAY  # noqa: E501
                    break
        finally:
            if indexer_order_customized:
                CachedSettings().evm_indexers_order_override_var.reset(indexer_order_customized)

        return {'result': success, 'message': message, 'status_code': status_code}

    def _decode_given_evm_tx(
            self,
            chain: EVM_CHAINS_WITH_TRANSACTIONS_TYPE,
            tx_ref: EVMTxHash,
            delete_custom: bool,
    ) -> None:
        """Re-pull and decode the given evm transaction.
        May raise RemoteError, DeserializationError or InputError.
        """
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                (tx_ref, chain.to_chain_id().serialize_for_db()),
            )

        try:
            (chain_manager := self.rotkehlchen.chains_aggregator.get_chain_manager(
                blockchain=chain,
            )).transactions.get_or_query_transaction_receipt(tx_hash=tx_ref)
        except RemoteError as e:
            raise InputError(f'hash {tx_ref!s} does not correspond to a transaction at {chain.name}. {e!s}') from e  # noqa: E501
        except DeserializationError as e:
            raise InputError(str(e)) from e

        events = chain_manager.transactions_decoder.decode_and_get_transaction_hashes(
            tx_hashes=[tx_ref],
            send_ws_notifications=True,
            ignore_cache=True,  # always redecode from here
            delete_customized=delete_custom,
        )

        # notify user if gnosis pay or monerium tx was redecoded but api key is missing
        if not has_premium_check(self.rotkehlchen.premium):
            return

        has_gnosis_pay, has_monerium = False, False
        for event in events:
            if chain == SupportedBlockchain.GNOSIS and event.counterparty == CPT_GNOSIS_PAY:
                has_gnosis_pay = True
                break
            elif event.counterparty == CPT_MONERIUM:
                has_monerium = True
                break
        else:
            return

        if (
            has_gnosis_pay and
            self.rotkehlchen.data.db.get_external_service_credentials(
                service_name=ExternalService.GNOSIS_PAY,
            ) is None
        ):
            self.rotkehlchen.msg_aggregator.add_message(
                message_type=WSMessageType.MISSING_API_KEY,
                data={'service': HistoryEventQueryType.GNOSIS_PAY.serialize()},
            )

        elif has_monerium and init_monerium(self.rotkehlchen.data.db) is None:
            self.rotkehlchen.msg_aggregator.add_message(
                message_type=WSMessageType.MISSING_API_KEY,
                data={'service': HistoryEventQueryType.MONERIUM.serialize()},
            )

    def _decode_given_evmlike_tx(self, tx_ref: EVMTxHash, delete_custom: bool) -> None:
        """Re-pull and decode the given evmlike transaction.
        First deletes the existing tx and events and then re-queries and decodes it.
        May raise RemoteError if the transaction can not be queried.
        """
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            concerning_address = write_cursor.execute('DELETE FROM zksynclite_transactions WHERE tx_hash=? RETURNING from_address', (tx_ref,)).fetchone()  # noqa: E501
            deleted_event_data = write_cursor.execute(
                'DELETE FROM history_events WHERE group_identifier=? RETURNING location_label',
                (ZKL_IDENTIFIER.format(tx_hash=str(tx_ref)),),
            ).fetchone()
            if deleted_event_data is not None:
                concerning_address = deleted_event_data[0]

        if (transaction := self.rotkehlchen.chains_aggregator.zksync_lite.query_single_transaction(
            tx_hash=tx_ref,
            concerning_address=concerning_address,
        )) is None:
            raise RemoteError(f'Failed to fetch transaction {tx_ref!s} from the zksync lite API')

        self.rotkehlchen.chains_aggregator.zksync_lite.decode_transaction(
            transaction=transaction,
            tracked_addresses=self.rotkehlchen.chains_aggregator.accounts.zksync_lite,
        )

    def _decode_given_solana_tx(self, tx_ref: Signature, delete_custom: bool) -> None:
        """Re-pull and decode the given solana transaction.
        May raise RemoteError, DeserializationError or InputError.
        """
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM solana_transactions WHERE signature=?',
                (tx_ref.to_bytes(),),
            )

        self.rotkehlchen.chains_aggregator.solana.transactions_decoder.decode_and_get_transaction_hashes(
            tx_hashes=[tx_ref],
            send_ws_notifications=True,
            ignore_cache=True,  # always redecode from here
            delete_customized=delete_custom,
        )

    @async_api_call()
    def decode_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            force_redecode: bool,
    ) -> dict[str, Any]:
        """This method should be called after querying transactions to perform event decoding.

        For EVM chains, any missing tx receipts are queried first. For Ethereum, block production
        events are also redecoded.

        It can be a slow process and this is why it is important to set the list of addresses
        queried per module that need to be decoded.

        This logic is executed by the frontend in pages where the set of transactions needs to be
        up to date, for example, the liquity module.

        If force redecode is True, all related uncustomized events are deleted and re-decoded.

        Returns the number of decoded transactions (not events in transactions)
        """
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        if chain.is_evmlike():
            decoded_count = self.rotkehlchen.chains_aggregator.zksync_lite.decode_undecoded_transactions(  # noqa: E501
                force_redecode=force_redecode,
                send_ws_notifications=True,
            )
        else:  # evm or solana
            if force_redecode:
                with self.rotkehlchen.data.db.user_write() as write_cursor:
                    dbevents.reset_events_for_redecode(
                        write_cursor=write_cursor,
                        location=Location.from_chain(chain),
                    )

                if chain == SupportedBlockchain.ETHEREUM:
                    DBEth2(self.rotkehlchen.data.db).redecode_block_production_events()

            chain_manager = self.rotkehlchen.chains_aggregator.get_chain_manager(chain)
            if chain.is_evm():
                # make sure that all the evm tx receipts are already queried
                chain_manager.transactions.get_receipts_for_transactions_missing_them()  # type: ignore[attr-defined]  # will be evm chain manager with transactions
                decoded_count = dbevmtx.count_hashes_not_decoded(
                    filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=chain.to_chain_id()),
                )
            else:  # solana
                decoded_count = DBSolanaTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
                    filter_query=SolanaTransactionsNotDecodedFilterQuery.make(),
                )

            if decoded_count > 0:
                chain_manager.transactions_decoder.get_and_decode_undecoded_transactions(  # type: ignore[attr-defined]  # evm and solana chain managers have a transactions_decoder
                    send_ws_notifications=True,
                )

        return _wrap_in_ok_result({'decoded_tx_number': decoded_count})

    @async_api_call()
    def get_history_status_summary(self) -> dict[str, Any]:
        """Get the last timestamp when evm transactions and exchanges were queried and how many
        transactions are waiting to be decoded.
        """
        evm_where_str = ' OR '.join(['name LIKE ?'] * len(EVM_CHAINS_WITH_TRANSACTIONS))
        evm_bindings = [
            f'{blockchain.to_range_prefix("txs")}_%'
            for blockchain in EVM_CHAINS_WITH_TRANSACTIONS
        ]
        exchanges_where_str = ' OR '.join(['name LIKE ?'] * len(SUPPORTED_EXCHANGES))
        exchanges_bindings = [
            f'{location!s}_history_events_%'
            for location in SUPPORTED_EXCHANGES
        ]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            evm_last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {evm_where_str}',
                evm_bindings,
            ).fetchone()[0] or Timestamp(0)
            exchanges_last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {exchanges_where_str}',
                exchanges_bindings,
            ).fetchone()[0] or Timestamp(0)
            has_evm_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain IN ({",".join(["?"] * len(EVM_CHAINS_WITH_TRANSACTIONS))})',  # noqa: E501
                [blockchain.value for blockchain in EVM_CHAINS_WITH_TRANSACTIONS],
            ).fetchone()[0] > 0
            exchanges_bindings_with_rotkehlchen = [
                location.serialize_for_db() for location in SUPPORTED_EXCHANGES
            ] + ['rotkehlchen']
            has_exchanges_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM user_credentials WHERE location IN ({",".join(["?"] * len(SUPPORTED_EXCHANGES))}) AND name != ?',  # noqa: E501
                exchanges_bindings_with_rotkehlchen,
            ).fetchone()[0] > 0

        undecoded_count = DBEvmTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=EvmTransactionsNotDecodedFilterQuery.make(),
        )
        return _wrap_in_ok_result({
            'evm_last_queried_ts': evm_last_queried_ts,
            'exchanges_last_queried_ts': exchanges_last_queried_ts,
            'undecoded_tx_count': undecoded_count,
            'has_evm_accounts': has_evm_accounts,
            'has_exchanges_accounts': has_exchanges_accounts,
        })

    @async_api_call()
    def get_evm_transactions_status(self) -> dict[str, Any]:
        """Get the last timestamp when evm transactions were queried and how many
        transactions are waiting to be decoded.
        """
        where_str = ' OR '.join(['name LIKE ?'] * len(EVM_CHAINS_WITH_TRANSACTIONS))
        bindings = [
            f'{blockchain.to_range_prefix("txs")}_%'
            for blockchain in EVM_CHAINS_WITH_TRANSACTIONS
        ]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {where_str}',
                bindings,
            ).fetchone()[0] or Timestamp(0)
            has_evm_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain IN ({",".join(["?"] * len(EVM_CHAINS_WITH_TRANSACTIONS))})',  # noqa: E501
                [blockchain.value for blockchain in EVM_CHAINS_WITH_TRANSACTIONS],
            ).fetchone()[0] > 0

        undecoded_count = DBEvmTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=EvmTransactionsNotDecodedFilterQuery.make(),
        )
        return _wrap_in_ok_result({
            'last_queried_ts': last_queried_ts,
            'undecoded_tx_count': undecoded_count,
            'has_evm_accounts': has_evm_accounts,
        })

    @async_api_call()
    def get_count_transactions_not_decoded(self) -> dict[str, Any]:
        tx_info: dict[str, dict[str, int]] = defaultdict(dict)
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)

        for chain in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            if (undecoded_count := dbevmtx.count_hashes_not_decoded(
                filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=chain),
            )) == 0:
                continue

            tx_info[chain_name := chain.name.lower()]['undecoded'] = undecoded_count
            tx_info[chain_name]['total'] = dbevmtx.count_evm_transactions(chain_id=chain)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if (undecoded_count := cursor.execute(
                'SELECT COUNT(*) FROM zksynclite_transactions WHERE is_decoded=0',
            ).fetchone()[0]) != 0:
                tx_info[chain_name := SupportedBlockchain.ZKSYNC_LITE.name.lower()]['undecoded'] = undecoded_count  # noqa: E501
                tx_info[chain_name]['total'] = cursor.execute('SELECT COUNT(*) FROM zksynclite_transactions').fetchone()[0]  # noqa: E501

        if (undecoded_count := DBSolanaTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=SolanaTransactionsNotDecodedFilterQuery.make(),
        )) != 0:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                tx_info[chain_name := SupportedBlockchain.SOLANA.name.lower()]['undecoded'] = undecoded_count  # noqa: E501
                tx_info[chain_name]['total'] = cursor.execute('SELECT COUNT(*) FROM solana_transactions').fetchone()[0]  # noqa: E501

        return _wrap_in_ok_result(tx_info)

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
        """Return the current price of the assets in the target asset currency."""
        log.debug(
            f'Querying the current {target_asset.identifier} price of these assets: '
            f'{", ".join([asset.identifier for asset in assets])}',
        )
        # Type is list instead of tuple here because you can't serialize a tuple
        assets_price: dict[Asset, list[Price | (int | None)]] = {}
        non_nft_assets = []
        for asset in assets:
            if asset.asset_type == AssetType.NFT:
                nft_price_data = self._eth_module_query(
                    module_name='nfts',
                    method='get_nfts_with_price',
                    query_specific_balances_before=None,
                )
                oracle = CurrentPriceOracle.MANUALCURRENT if nft_price_data['manually_input'] is True else CurrentPriceOracle.BLOCKCHAIN  # noqa: E501
                assets_price[asset] = [Price(nft_price_data['price']), oracle.value]
            else:
                non_nft_assets.append(asset)

        if len(non_nft_assets) != 0:
            found_prices = Inquirer.find_prices_and_oracles(
                from_assets=non_nft_assets,
                to_asset=target_asset,
                ignore_cache=ignore_cache,
            )
            assets_price.update({
                asset: [price_and_oracle[0], price_and_oracle[1].value]
                for asset, price_and_oracle in found_prices.items()
            })

        result = {
            'assets': assets_price,
            'target_asset': target_asset,
            'oracles': {str(oracle): oracle.value for oracle in CurrentPriceOracle},
        }
        return _wrap_in_ok_result(process_result(result))

    def query_asset_mappings_by_type(
            self,
            dict_keys: tuple[str, str, str],
            mapping_type: Literal['location', 'counterparty'],
            location_or_counterparty_reader_callback: Callable,
            filter_query: LocationAssetMappingsFilterQuery | CounterpartyAssetMappingsFilterQuery,
            query_columns: Literal['local_id, location, exchange_symbol', 'local_id, counterparty, symbol'],  # noqa: E501
    ) -> Response:
        """Query the location/counterparty asset mappings using the provided filter_query
        and return them in a paginated format"""
        mappings, mappings_found, mappings_total = GlobalDBHandler.query_asset_mappings_by_type(
            mapping_type=mapping_type,
            filter_query=filter_query,
            dict_keys=dict_keys,
            query_columns=query_columns,
            location_or_counterparty_reader_callback=location_or_counterparty_reader_callback,
        )

        result = {
            'entries': mappings,
            'entries_found': mappings_found,
            'entries_total': mappings_total,
        }
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @staticmethod
    def perform_asset_mapping_operation(
            mapping_fn: Callable,
            entries: Sequence[LocationAssetMappingUpdateEntry | LocationAssetMappingDeleteEntry | CounterpartyAssetMappingUpdateEntry | CounterpartyAssetMappingDeleteEntry],  # noqa: E501
    ) -> Response:
        """Perform an asset mapping database operation based on the given function and entries."""
        try:
            mapping_fn(entries=entries)
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )
        else:
            return api_response(result=OK_RESULT)

    @async_api_call()
    def get_historical_assets_price(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            only_cache_period: int | None = None,
    ) -> dict[str, Any]:
        if only_cache_period is not None:
            result: dict[str, Any] = {
                'assets': defaultdict(lambda: defaultdict(lambda: ZERO_PRICE)),
                'target_asset': target_asset.identifier,
            }
            for price_result in GlobalDBHandler.get_historical_prices(
                query_data=[(entry[0], target_asset, entry[1]) for entry in assets_timestamp],
                max_seconds_distance=only_cache_period,
            ):
                if price_result is not None:
                    result['assets'][price_result.from_asset.identifier][price_result.timestamp] = str(price_result.price)  # noqa: E501

            return _wrap_in_ok_result(result)

        assets_price = PriceHistorian.query_multiple_prices(
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        result = {
            'assets': {k: dict(v) for k, v in assets_price.items()},
            'target_asset': target_asset,
        }
        return _wrap_in_ok_result(process_result(result))

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
        cache_data = GlobalDBHandler.get_historical_price_data(oracle)
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
        except (BadFunctionCallOutput, NotERC20Conformant):
            return wrap_in_fail_result(
                f'{chain_id!s} address {address} seems to not be a deployed contract or not a valid erc20 token',  # noqa: E501
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
        added = GlobalDBHandler.add_single_historical_price(historical_price)
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
        edited = GlobalDBHandler.edit_manual_price(historical_price)
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
            _wrap_in_ok_result(GlobalDBHandler.get_manual_prices(from_asset, to_asset)),
            status_code=HTTPStatus.OK,
        )

    def delete_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Response:
        deleted = GlobalDBHandler.delete_manual_price(from_asset, to_asset, timestamp)
        if deleted:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)
        return api_response(
            result={'result': False, 'message': 'Failed to delete manual price'},
            status_code=HTTPStatus.CONFLICT,
        )

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
            self._eth_module_query(
                module_name='nfts',
                method='query_balances',
                query_specific_balances_before=None,
                addresses=self.rotkehlchen.chains_aggregator.queried_addresses_for_module('nfts'),
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
        prices = GlobalDBHandler.get_all_manual_latest_prices(
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
            assets_to_invalidate = GlobalDBHandler.add_manual_latest_price(
                from_asset=from_asset,
                to_asset=to_asset,
                price=price,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)
        Inquirer.remove_cache_prices_for_asset(assets_to_invalidate)

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
            assets_to_invalidate = GlobalDBHandler.delete_manual_latest_price(asset=asset)
        except InputError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)
        Inquirer.remove_cache_prices_for_asset(assets_to_invalidate)

        return api_response(OK_RESULT)

    def get_database_info(self) -> Response:
        globaldb_schema_version = GlobalDBHandler.get_schema_version()
        globaldb_assets_version = GlobalDBHandler.get_setting_value(ASSETS_VERSION_KEY, 0)
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
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.PNL_REPORTS_LOOKUP,
        )

        dbreports = DBAccountingReports(self.rotkehlchen.data.db)
        reports, entries_found = dbreports.get_reports(
            report_id=report_id,
            limit=entries_limit,
        )

        # success
        result_dict = _wrap_in_ok_result({
            'entries': reports,
            'entries_found': entries_found,
            'entries_limit': entries_limit,
        })
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def get_report_data(self, filter_query: ReportDataFilterQuery) -> Response:
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.PNL_EVENTS,
        )

        dbreports = DBAccountingReports(self.rotkehlchen.data.db)
        try:
            report_data, entries_found, entries_total = dbreports.get_report_data(
                filter_=filter_query,
                limit=entries_limit,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        result = {
            'entries': [x.to_exported_dict(
                ts_converter=self.rotkehlchen.accountant.pots[0].timestamp_to_date,
                export_type=AccountingEventExportType.API,
            ) for x in report_data],
            'entries_found': entries_found,
            'entries_total': entries_total,
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

    def get_location_labels(self) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            # Get distinct location_labels with their corresponding location
            # Ordered by frequency (most frequent first)
            # When multiple locations exist for a label, we take the first one
            # Only include labels that correspond to tracked blockchain accounts
            # For exchanges, include all labels since users' credentials can be removed.
            exchange_locations = tuple(loc.serialize_for_db() for loc in SUPPORTED_EXCHANGES)
            placeholders = ','.join(['?' for _ in exchange_locations])
            labels = [{
                'location_label': row[0],
                'location': Location.deserialize_from_db(row[1]).serialize(),
            } for row in cursor.execute(
                f'SELECT location_label, MIN(location) as location, COUNT(*) as frequency '
                f'FROM history_events '
                f'WHERE location_label IS NOT NULL '
                f'AND (location_label IN (SELECT account FROM blockchain_accounts) '
                f'OR location IN ({placeholders})) '
                f'GROUP BY location_label '
                f'ORDER BY frequency DESC',
                exchange_locations,
            )]

        return api_response(
            result=_wrap_in_ok_result(labels),
            status_code=HTTPStatus.OK,
        )

    @async_api_call()
    def query_online_events(self, query_type: HistoryEventQueryType) -> dict[str, Any]:
        """Query the specified event type for data and add/update the events in the DB."""
        try:
            if query_type in (HistoryEventQueryType.GNOSIS_PAY, HistoryEventQueryType.MONERIUM):
                pretty_name = query_type.name.replace('_', ' ').title()
                if not has_premium_check(self.rotkehlchen.premium):
                    return wrap_in_fail_result(
                        message=f'You can only use {pretty_name} with rotki premium',
                        status_code=HTTPStatus.FORBIDDEN,
                    )

                if (
                    query_type == HistoryEventQueryType.GNOSIS_PAY and
                    (gnosis_pay := init_gnosis_pay(self.rotkehlchen.data.db)) is not None
                ):
                    gnosis_pay.get_and_process_transactions(after_ts=Timestamp(0))
                    return OK_RESULT
                elif (
                    query_type == HistoryEventQueryType.MONERIUM and
                    (monerium := init_monerium(self.rotkehlchen.data.db)) is not None
                ):
                    monerium.get_and_process_orders()
                    return OK_RESULT
                # else: the init function for the requested query_type failed, indicating missing credentials.  # noqa: E501
                return wrap_in_fail_result(
                    message=f'Unable to refresh {pretty_name} data due to missing credentials',
                    status_code=HTTPStatus.CONFLICT,
                )

            # else query_type is either ETH_WITHDRAWALS or BLOCK_PRODUCTIONS and eth2 is needed
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
            else:  # block production  # noqa: PLR5501, E501  # ruff thinks this should be elif but that makes the logic confusing
                if len(indices := eth2.beacon_inquirer.beaconchain.get_validators_to_query_for_blocks()) != 0:  # noqa: E501
                    log.debug(f'Querying block production information for validator indices {indices}')  # noqa: E501
                    eth2.beacon_inquirer.beaconchain.get_and_store_produced_blocks(indices)
                    eth2.combine_block_with_tx_events()
                else:
                    log.debug('No active or un-queried validators found. Skipping query of block production information.')  # noqa: E501
        except RemoteError as e:
            return wrap_in_fail_result(
                message=str(e),
                status_code=HTTPStatus.BAD_GATEWAY,
            )

        return OK_RESULT

    @staticmethod
    def _serialize_and_group_history_events(
            events: list['HistoryBaseEntry'],
            event_accounting_rule_statuses: list[EventAccountingRuleStatus],
            grouped_events_nums: list[int | None],
            customized_event_ids: list[int],
            ignored_ids: set[str],
            hidden_event_ids: list[int],
    ) -> list[dict[str, Any] | list[dict[str, Any]]]:
        """Serialize and group history events for the api.
        Groups evm & solana swap and multi trade events into sub-lists. Uses the order defined in
        EVENT_GROUPING_ORDER to decide which events belong in which group.

        Args:
        - events: list of events to serialize and group
        - event_accounting_rule_statuses and grouped_events_nums: lists with each element
           corresponding to an event.
        - customized_event_ids, ignored_ids, and hidden_event_ids: arguments applying to all events
           that are passed directly to serialize_for_api for all events.

        Returns a list of serialized events with grouped events in sub-lists.
        """
        entries: list[dict[str, Any] | list[dict[str, Any]]] = []
        current_group: list[dict[str, Any]] = []
        last_subtype_index: int | None = None
        for event, event_accounting_rule_status, grouped_events_num in zip(
            events,
            event_accounting_rule_statuses,
            grouped_events_nums,
            strict=False,  # guaranteed to have same length. event_accounting_rule_statuses and grouped_events_nums are created directly from the events list.  # noqa: E501
        ):
            serialized = event.serialize_for_api(
                customized_event_ids=customized_event_ids,
                ignored_ids=ignored_ids,
                hidden_event_ids=hidden_event_ids,
                event_accounting_rule_status=event_accounting_rule_status,
                grouped_events_num=grouped_events_num,
            )
            if event.entry_type in (HistoryBaseEntryType.EVM_SWAP_EVENT, HistoryBaseEntryType.SOLANA_SWAP_EVENT):  # noqa: E501
                if (event_subtype_index := EVENT_GROUPING_ORDER[event.event_type].get(event.event_subtype)) is None:  # noqa: E501
                    log.error(
                        'Unable to determine group order for event type/subtype '
                        f'{event.event_type}/{event.event_subtype}',
                    )
                    event_subtype_index = 0

                if (
                    len(current_group) == 0 or
                    (last_subtype_index is not None and event_subtype_index >= last_subtype_index)
                ):
                    current_group.append(serialized)
                else:  # Start a new group because the order is broken
                    if len(current_group) > 0:
                        entries.append(current_group)
                    current_group = [serialized]

                last_subtype_index = event_subtype_index
            else:  # Non-groupable event
                if len(current_group) > 0:
                    entries.append(current_group)
                    current_group, last_subtype_index = [], None
                entries.append(serialized)

        if len(current_group) > 0:  # Append any remaining group
            entries.append(current_group)

        return entries

    def get_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            aggregate_by_group_ids: bool,
    ) -> Response:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        entries_limit, has_premium = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            events_result, entries_found, entries_with_limit = dbevents.get_history_events_and_limit_info(  # noqa: E501
                cursor=cursor,
                filter_query=filter_query,
                entries_limit=entries_limit,
                aggregate_by_group_ids=aggregate_by_group_ids,
                match_exact_events=True,  # set to True since the frontend requests the group_identifiers manually in their second call to this endpoint. https://github.com/orgs/rotki/projects/11?pane=issue&itemId=110464193  # noqa: E501
            )
            entries_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='history_events',
                group_by='group_identifier' if aggregate_by_group_ids else None,
            )
            customized_event_ids = dbevents.get_customized_group_identifiers(
                cursor=cursor,
                location=filter_query.location,
            )
            hidden_event_ids = dbevents.get_hidden_event_ids(cursor)
            ignored_ids = self.rotkehlchen.data.db.get_ignored_action_ids(cursor=cursor)

        accountant_pot = AccountingPot(
            database=self.rotkehlchen.data.db,
            evm_accounting_aggregators=EVMAccountingAggregators([self.rotkehlchen.chains_aggregator.get_evm_manager(x).accounting_aggregator for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS]),  # noqa: E501
            msg_aggregator=self.rotkehlchen.msg_aggregator,
            is_dummy_pot=True,
        )
        events: list[HistoryBaseEntry]
        grouped_events_nums: list[int | None]
        grouped_events_nums, events = (
            zip(*events_result, strict=False)  # type: ignore  # mypy doesn't understand significance of boolean check.
            if aggregate_by_group_ids is True and len(events_result) != 0 else
            ([None] * len(events_result), events_result)
        )
        result = {
            'entries': self._serialize_and_group_history_events(
                events=events,
                event_accounting_rule_statuses=query_missing_accounting_rules(
                    db=self.rotkehlchen.data.db,
                    accounting_pot=accountant_pot,
                    evm_accounting_aggregator=accountant_pot.events_accountant.evm_accounting_aggregators,
                    events=events,
                    accountant=self.rotkehlchen.accountant,
                ),  # length of missing_accounting_rules and events guaranteed by function
                grouped_events_nums=grouped_events_nums,
                customized_event_ids=customized_event_ids,
                ignored_ids=ignored_ids,
                hidden_event_ids=hidden_event_ids,
            ),
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
            register_post_download_cleanup(zip_path)
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

                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:  # needed on windows, see https://tinyurl.com/tmp-win-err  # noqa: E501
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
            register_post_download_cleanup(Path(zipfile_path))
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

    @async_api_call()
    def resolve_ens_name(
            self,
            name: str,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        address = maybe_resolve_name(
            ethereum_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
            name=name,
            ignore_cache=ignore_cache,
        )
        return {'result': address, 'message': '', 'status_code': HTTPStatus.OK if address else HTTPStatus.NOT_FOUND}  # noqa: E501

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
            update_existing: bool,
    ) -> Response:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            with db_addressbook.write_ctx(book_type) as write_cursor:
                db_addressbook.add_or_update_addressbook_entries(
                    write_cursor=write_cursor,
                    entries=entries,
                    update_existing=update_existing,
                )
        except InputError as e:
            return api_response(
                result=wrap_in_fail_result(str(e)),
                status_code=HTTPStatus.CONFLICT,
            )

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
            prioritizer=self.rotkehlchen.addressbook_prioritizer,
            chain_addresses=chain_addresses,
        )
        return api_response(_wrap_in_ok_result(process_result_list(mappings)))

    @async_api_call()
    def detect_evm_tokens(
            self,
            only_cache: bool,
            addresses: Sequence[ChecksumEvmAddress] | None,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
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
            'loglevel': {
                'value': (current_level := logging.getLevelName(logger.getEffectiveLevel())),
                'is_default': current_level == DEFAULT_LOGLEVEL,
            },
        }
        return api_response(_wrap_in_ok_result(config), status_code=HTTPStatus.OK)

    def update_log_level(self, loglevel: str) -> Response:
        """Update the current log level"""
        (global_logger := logging.getLogger()).setLevel(numeric_level := getattr(logging, loglevel))  # noqa: E501
        for handler in global_logger.handlers:
            handler.setLevel(numeric_level)

        return self.get_config_arguments()

    def get_user_notes(self, filter_query: UserNotesFilterQuery) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            user_notes, entries_found = self.rotkehlchen.data.db.get_user_notes_and_limit_info(
                filter_query=filter_query,
                cursor=cursor,
                has_premium=has_premium_check(self.rotkehlchen.premium),
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
    def add_transaction_by_reference(
            self,
            blockchain: CHAINS_WITH_TRANSACTIONS_TYPE,
            tx_ref: EVMTxHash | Signature,
            associated_address: ChecksumEvmAddress | SolanaAddress,
    ) -> dict[str, Any]:
        """
        Adds a transaction to the DB and associates it with the address provided.
        If successful, the transaction is then decoded.
        """
        chain_manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)
        try:
            if blockchain == SupportedBlockchain.SOLANA:
                chain_manager.transactions.get_or_create_transaction(  # type: ignore[attr-defined]  # Solana manager has transactions
                    signature=tx_ref,
                    relevant_address=associated_address,
                )
            else:
                chain_manager.transactions.add_transaction_by_hash(  # type: ignore[attr-defined]  # EVM manager has transactions
                    tx_hash=tx_ref,
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
                    f'Unable to add transaction with reference {tx_ref!s} for blockchain '
                    f'{blockchain} and associated address {associated_address} due to {e!s}'
                ),
                status_code=status_code,
            )

        chain_manager.transactions_decoder.decode_transaction_hashes(  # type: ignore[attr-defined]  # EVM manager has transactions_decoder
            ignore_cache=True,
            tx_hashes=[tx_ref],
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
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )
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
                events_raw, entries_found = self.rotkehlchen.history_querying_manager.query_history_events(  # noqa: E501
                    cursor=cursor,
                    location=location,
                    filter_query=query_filter,
                    only_cache=only_cache,
                )
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                return wrap_in_fail_result(
                    message=f'Database query error retrieving missing prices {e!s}',
                    status_code=HTTPStatus.CONFLICT,
                )

            events = []
            for event in events_raw:
                try:
                    event_data = history_event_to_staking_for_api(event)
                except DeserializationError as e:
                    log.warning(f'Could not deserialize staking event: {event} due to {e!s}')
                    continue
                events.append(event_data)

            entries_total, _ = history_events_db.get_history_events_count(
                cursor=cursor,
                query_filter=table_filter,
                entries_limit=entries_limit,
            )
            value_query_filters, value_bindings = value_filter.prepare(with_pagination=False, with_order=False)  # noqa: E501
            asset_amounts_and_value, total_value = history_events_db.get_amount_and_value_stats(
                cursor=cursor,
                query_filters=value_query_filters,
                bindings=value_bindings,
                counterparty=CPT_KRAKEN,
            )
            result = {
                'entries': events,
                'entries_found': entries_found,
                'entries_limit': entries_limit,
                'entries_total': entries_total,
                'total_value': total_value,
                'assets': history_events_db.get_entries_assets_history_events(
                    cursor=cursor,
                    query_filter=table_filter,
                ),
                'received': [
                    {
                        'asset': entry[0],
                        'amount': entry[1],
                        'value': entry[2],
                    } for entry in asset_amounts_and_value
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
        avatars_dir = self.rotkehlchen.data_dir / IMAGESDIR_NAME / AVATARIMAGESDIR_NAME
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
                if entry.is_file():
                    entry.unlink()

            return api_response(OK_RESULT)

        for icon in icons:
            self.rotkehlchen.icon_manager.delete_icon(icon)

        return api_response(OK_RESULT)

    def clear_avatars_cache(self, avatars: list[str] | None) -> Response:
        """Clears cache entries for the specified avatars of ENS names.

        If no avatars are provided, the avatars cache is cleared entirely.
        """
        avatars_dir = self.rotkehlchen.data_dir / IMAGESDIR_NAME / AVATARIMAGESDIR_NAME
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
            'entry_type_mappings': ENTRY_TYPE_MAPPINGS,
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

    def get_counterparties_details(self) -> Response:
        """Collect the counterparties from exchanges and EVM/Solana protocol decoders"""
        counterparties = {(exchange_id := x.name.lower()): CounterpartyDetails(
            identifier=exchange_id,
            label=LOCATION_DETAILS[x].get('label', x.name.capitalize()),
            image=LOCATION_DETAILS[x].get('image'),
        ) for x in ALL_SUPPORTED_EXCHANGES}
        for counterparty in self.rotkehlchen.chains_aggregator.get_all_counterparties():
            counterparties.setdefault(counterparty.identifier, counterparty)

        return api_response(
            result=process_result(_wrap_in_ok_result(result=list(counterparties.values()))),
            status_code=HTTPStatus.OK,
        )

    @async_api_call()
    def refresh_protocol_data(self, cache_protocol: ProtocolsWithCache) -> dict[str, Any]:
        eth_node_inquirer = self.rotkehlchen.chains_aggregator.ethereum.node_inquirer
        optimism_inquirer = self.rotkehlchen.chains_aggregator.optimism.node_inquirer
        base_inquirer = self.rotkehlchen.chains_aggregator.base.node_inquirer
        arbitrum_inquirer = self.rotkehlchen.chains_aggregator.arbitrum_one.node_inquirer
        gnosis_inquirer = self.rotkehlchen.chains_aggregator.gnosis.node_inquirer
        polygon_inquirer = self.rotkehlchen.chains_aggregator.polygon_pos.node_inquirer
        cache_rules: list[tuple[str, CacheType, Callable, ChainID | None, EvmNodeInquirer]] = []

        match cache_protocol:
            case ProtocolsWithCache.CURVE:
                cache_rules.extend([
                    (
                        'curve pools',
                        CacheType.CURVE_LP_TOKENS,
                        query_curve_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.POLYGON_POS, polygon_inquirer),
                    )
                ])
            case ProtocolsWithCache.VELODROME:
                cache_rules.append((
                    'velodrome pools',
                    CacheType.VELODROME_POOL_ADDRESS,
                    query_velodrome_like_data,
                    None,
                    optimism_inquirer,
                ))
            case ProtocolsWithCache.AERODROME:
                cache_rules.append((
                    'aerodrome pools',
                    CacheType.AERODROME_POOL_ADDRESS,
                    query_velodrome_like_data,
                    None,
                    base_inquirer,
                ))
            case ProtocolsWithCache.CONVEX:
                cache_rules.append((
                    'convex pools',
                    CacheType.CONVEX_POOL_ADDRESS,
                    query_convex_data,
                    None,
                    eth_node_inquirer,
                ))
            case ProtocolsWithCache.GEARBOX:
                cache_rules.append((
                    'gearbox pools',
                    CacheType.GEARBOX_POOL_ADDRESS,
                    query_gearbox_data,
                    ChainID.ETHEREUM,
                    eth_node_inquirer,
                ))
            case ProtocolsWithCache.YEARN:
                try:
                    query_yearn_vaults(
                        db=self.rotkehlchen.data.db,
                        ethereum_inquirer=eth_node_inquirer,
                    )
                except RemoteError as e:
                    return wrap_in_fail_result(
                        message=f'Failed to refresh yearn vaults cache due to: {e!s}',
                        status_code=HTTPStatus.CONFLICT,
                    )
            case ProtocolsWithCache.MAKER:
                try:
                    query_ilk_registry_and_maybe_update_cache(eth_node_inquirer)
                except RemoteError as e:
                    return wrap_in_fail_result(
                        message=f'Failed to refresh makerdao vault ilk cache due to: {e!s}',
                        status_code=HTTPStatus.CONFLICT,
                    )
            case ProtocolsWithCache.SPARK | ProtocolsWithCache.AAVE:
                fn = (
                    update_aave_v3_underlying_assets
                    if cache_protocol == ProtocolsWithCache.AAVE
                    else update_spark_underlying_assets
                )
                try:
                    fn(chains_aggregator=self.rotkehlchen.chains_aggregator)
                except RemoteError as e:
                    return wrap_in_fail_result(
                        message=f'Failed to refresh {cache_protocol.name.lower()} cache due to: {e!s}',  # noqa: E501
                        status_code=HTTPStatus.CONFLICT,
                    )
            case ProtocolsWithCache.BALANCER_V1:
                cache_rules.extend([
                    (
                        'balancer v1 pools',
                        CacheType.BALANCER_V1_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.BALANCER_V2:
                cache_rules.extend([
                    (
                        'balancer v2 pools',
                        CacheType.BALANCER_V2_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.POLYGON_POS, polygon_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.BALANCER_V3:
                cache_rules.extend([
                    (
                        'balancer v3 pools',
                        CacheType.BALANCER_V3_POOLS,
                        query_balancer_data,
                        chain_id,
                        node_inquirer,
                    )
                    for chain_id, node_inquirer in (
                        (ChainID.BASE, base_inquirer),
                        (ChainID.GNOSIS, gnosis_inquirer),
                        (ChainID.ETHEREUM, eth_node_inquirer),
                        (ChainID.OPTIMISM, optimism_inquirer),
                        (ChainID.ARBITRUM_ONE, arbitrum_inquirer),
                    )
                ])
            case ProtocolsWithCache.ETH_WITHDRAWALS:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    self.rotkehlchen.data.db.delete_dynamic_caches(
                        write_cursor=write_cursor,
                        key_parts=[
                            DBCacheDynamic.WITHDRAWALS_TS.value[0].split('_')[0],
                            DBCacheDynamic.WITHDRAWALS_IDX.value[0].split('_')[0],
                        ],
                    )
            case ProtocolsWithCache.ETH_BLOCKS:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    self.rotkehlchen.data.db.delete_dynamic_caches(
                        write_cursor=write_cursor,
                        key_parts=[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS.value[0][:30]],
                    )
            case ProtocolsWithCache.ETH_VALIDATORS_DATA:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute('DELETE FROM eth_validators_data_cache')
            case ProtocolsWithCache.MERKL:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM unique_cache WHERE key LIKE ?',
                        (f'{CacheType.MERKL_REWARD_PROTOCOLS.serialize()}%',),
                    )
            case ProtocolsWithCache.BEEFY_FINANCE:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM unique_cache WHERE key LIKE ?',
                        (f'{CacheType.BEEFY_VAULTS.serialize()}%',),
                    )

        failed_to_update = []
        for (cache, cache_type, query_method, chain_id, inquirer) in cache_rules:
            if inquirer.ensure_cache_data_is_updated(
                cache_type=cache_type,
                query_method=query_method,
                chain_id=chain_id,
                cache_key_parts=None if chain_id is None else (str(chain_id.serialize_for_db()),),
                force_refresh=True,
            ) == RemoteDataQueryStatus.FAILED:
                failed_to_update.append(cache)

        if len(failed_to_update) != 0:
            return wrap_in_fail_result(
                message=f'Failed to refresh caches for: {", ".join(failed_to_update)}',
                status_code=HTTPStatus.CONFLICT,
            )

        return OK_RESULT

    def get_airdrops_metadata(self) -> Response:
        """Returns a list of airdrops metadata"""
        result = []
        try:
            for identifier, airdrop in fetch_airdrops_metadata(self.rotkehlchen.data.db)[0].items():  # noqa: E501
                result.append({
                    'identifier': identifier,
                    'name': airdrop.name,
                    'icon': airdrop.icon,
                })
                if airdrop.icon_url is not None:
                    result[-1]['icon_url'] = airdrop.icon_url
        except RemoteError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_GATEWAY)
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
                register_post_download_cleanup(exportpath)
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

    @async_api_call()
    def export_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            directory_path: Path | None,
            match_exact_events: bool,
    ) -> dict[str, Any] | Response:
        """Export history events data to a CSV file."""
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            history_events, _, _ = dbevents.get_history_events_and_limit_info(
                cursor=cursor,
                filter_query=filter_query,
                match_exact_events=match_exact_events,
                entries_limit=entries_limit,
            )

        if len(history_events) == 0:
            return wrap_in_fail_result(
                message='No history processed in order to perform an export',
                status_code=HTTPStatus.CONFLICT,
            )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rotkehlchen.get_settings(cursor)
            currency = settings.main_currency.resolve_to_asset_with_oracles()

        serialized_history_events = []
        headers: dict[str, None] = {}
        query_data, unique_data = [], set()
        for event in history_events:
            if (entry := (event.asset, currency, ts_ms_to_sec(event.timestamp))) not in unique_data:  # noqa: E501
                unique_data.add(entry)
                query_data.append(entry)

        prices_from_db = GlobalDBHandler.get_historical_prices(
            query_data=query_data,  # type: ignore[arg-type]  # currency is a subclass of Asset
            max_seconds_distance=HOUR_IN_SECONDS,
        )
        missing_prices: list[tuple[Asset, Timestamp]] = []
        cached_db_prices: defaultdict[Asset, defaultdict[Timestamp, FVal]] = defaultdict(lambda: defaultdict(lambda: ZERO))  # noqa: E501
        for idx, (asset, _, timestamp) in enumerate(query_data):
            if (db_price := prices_from_db[idx]) is not None:
                cached_db_prices[db_price.from_asset][db_price.timestamp] = db_price.price
            elif (asset, timestamp) not in missing_prices:
                missing_prices.append((asset, timestamp))

        for asset, timestamped_prices in PriceHistorian.query_multiple_prices(
            assets_timestamp=missing_prices,
            target_asset=currency,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        ).items():
            cached_db_prices[asset].update(timestamped_prices)

        for event in history_events:
            serialized_event = event.serialize_for_csv(
                fiat_value=event.amount * cached_db_prices[event.asset][ts_ms_to_sec(event.timestamp)],  # noqa: E501
                settings=settings,
            )
            serialized_history_events.append(serialized_event)
            # maintain insertion order without storing extra info
            headers.update(dict.fromkeys(serialized_event))

        try:
            filename = generate_events_export_filename(filter_query=filter_query, use_localtime=settings.display_date_in_localtime)  # noqa: E501
            if directory_path is None:  # file will be downloaded later via download_history_events_csv endpoint  # noqa: E501
                file_path = Path(tempfile.mkdtemp()) / filename
                dict_to_csv_file(
                    path=file_path,
                    dictionary_list=serialized_history_events,
                    csv_delimiter=settings.csv_export_delimiter,
                    headers=headers.keys(),
                )
                return {
                    'result': {'file_path': str(file_path)},
                    'message': '',
                    'status_code': HTTPStatus.OK,
                }

            # else do a direct export to filesystem
            directory_path.mkdir(parents=True, exist_ok=True)
            file_path = directory_path / filename
            dict_to_csv_file(
                path=file_path,
                dictionary_list=serialized_history_events,
                csv_delimiter=settings.csv_export_delimiter,
                headers=headers.keys(),
            )
        except (CSVWriteError, PermissionError) as e:
            return wrap_in_fail_result(message=str(e), status_code=HTTPStatus.CONFLICT)

        return OK_RESULT

    @staticmethod
    def download_history_events_csv(file_path: str) -> Response:
        """Download history events data CSV file."""
        register_post_download_cleanup(path := Path(file_path))
        return send_file(
            path_or_file=file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=path.name,
        )

    def _invalidate_cache_for_accounting_rule(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            event_ids: list[int] | None = None,
    ) -> None:
        if event_ids is None:
            cache_keys = [get_event_type_identifier(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
            )]
        else:
            cache_keys = [get_event_type_identifier(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                event_id=event_id,
            ) for event_id in event_ids]

        accountant = self.rotkehlchen.accountant
        for cache_key in cache_keys:
            affected_events = accountant.processable_events_cache_signatures.get(cache_key)
            for event_idx in affected_events:
                accountant.processable_events_cache.remove(event_idx)

    def add_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> Response:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            db.add_accounting_rule(
                event_ids=event_ids,
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        self._invalidate_cache_for_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def update_accounting_rule(
            self,
            event_ids: list[int] | None,
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
                event_ids=event_ids,
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
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def delete_accounting_rule(self, rule_id: int) -> Response:
        db = DBAccountingRules(self.rotkehlchen.data.db)
        try:
            event_ids, event_type, event_subtype, counterparty = db.remove_accounting_rule(rule_id=rule_id)  # noqa: E501
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        self._invalidate_cache_for_accounting_rule(
            event_ids=event_ids,
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

    def add_to_spam_assets_false_positive(self, token: EvmToken) -> Response:
        """
        Add spam asset to the list of false positives. It also removes the SPAM value
        in the protocol field of the token and removes the token from the ignore list.
        We also clean the cache in AssetResolver.
        """
        globaldb = GlobalDBHandler()
        with globaldb.conn.write_ctx() as write_cursor:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                values=(token.identifier,),
            )

            if token.protocol == SPAM_PROTOCOL:  # remove the spam protocol if it was set
                set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=False)

        with self.rotkehlchen.data.db.user_write() as write_cursor:  # remove it from the ignored assets  # noqa: E501
            self.rotkehlchen.data.db.remove_from_ignored_assets(
                write_cursor=write_cursor,
                asset=token,
            )

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def remove_from_spam_assets_false_positives(self, token: EvmToken) -> Response:
        """Delete a spam asset from the list of whitelisted assets"""
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_delete_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                values=(token.identifier,),
            )

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def get_spam_assets_false_positives(self) -> Response:
        with GlobalDBHandler().conn.read_ctx() as cursor:
            whitelisted_tokens = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
            )

        return api_response(_wrap_in_ok_result(whitelisted_tokens), status_code=HTTPStatus.OK)

    def add_tokens_to_spam(self, tokens: list[EvmToken]) -> Response:
        """
        Change the protocol value for the provided token to spam if it isn't spam.
        It also adds the token to the list of ignored assets and removes it from
        the whitelisted tokens.
        """
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            for token in tokens:
                if token.protocol != SPAM_PROTOCOL:
                    set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=True)

                # remove the asset from the whitelist if it was there
                globaldb_delete_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                    values=(token.identifier,),
                )
                AssetResolver.clean_memory_cache(token.identifier)

                # Finally if the token was in any cached balances, that cache is cleared,
                # so it can be requeried later without the ignored token.
                for balances in self.rotkehlchen.chains_aggregator.balances.get(
                    chain=(blockchain := token.chain_id.to_blockchain()),
                ).values():
                    # variables below can only be dicts because we mark as spam only evm tokens
                    in_assets = balances.assets.pop(token, None)  # type: ignore
                    in_liabilities = balances.liabilities.pop(token, None)  # type: ignore

                    if in_assets is not None or in_liabilities is not None:
                        # If the token was found in balances, flush relevant caches so
                        # subsequent calls reflect its removal without re-querying the chain.
                        self.rotkehlchen.chains_aggregator.flush_cache('query_balances')
                        self.rotkehlchen.chains_aggregator.flush_cache(
                            name='query_balances',
                            blockchain=blockchain,
                        )
                        log.debug(f'Flushed query_balances cache after setting {token} as spam')

        # add to ignored assets if it wasn't there
        self.rotkehlchen.data.add_ignored_assets(assets=tokens)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def remove_token_from_spam(self, token: EvmToken) -> Response:
        """
        Change the protocol value of the token to None if its current value is spam
        Also removes the asset from the list of ignored assets
        """
        if token.protocol == SPAM_PROTOCOL:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=False)

        self.rotkehlchen.data.remove_ignored_assets(assets=[token])
        AssetResolver().clean_memory_cache(token.identifier)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def create_calendar_entry(self, calendar: CalendarEntry) -> Response:
        """Create a new calendar entry with the information provided"""
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).create_calendar_entry(
                calendar=calendar,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
        return api_response(_wrap_in_ok_result(
            {'entry_id': calendar_event_id}),
            status_code=HTTPStatus.OK,
        )

    def delete_calendar_entry(self, identifier: int) -> Response:
        """Delete a calendar entry by its id"""
        try:
            DBCalendar(self.rotkehlchen.data.db).delete_entry(
                identifier=identifier,
                entry_type='calendar',
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def query_calendar(self, filter_query: CalendarFilterQuery) -> Response:
        """Query the calendar table using the provided filter"""
        result = DBCalendar(self.rotkehlchen.data.db).query_calendar_entry(
            filter_query=filter_query,
        )
        return api_response(_wrap_in_ok_result(
            result=process_result(result),
            status_code=HTTPStatus.OK,
        ))

    def update_calendar_entry(self, calendar: CalendarEntry) -> Response:
        """Update the calendar entry with the given identifier using the information provided"""
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).update_calendar_entry(
                calendar=calendar,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(_wrap_in_ok_result(
            {'entry_id': calendar_event_id}),
            status_code=HTTPStatus.OK,
        )

    def create_calendar_reminder(self, reminders: list[ReminderEntry]) -> Response:
        """Store in the database the reminder for an event and return the id of the new entry"""
        success, failed = DBCalendar(self.rotkehlchen.data.db).create_reminder_entries(
            reminders=reminders,
        )
        result = {'success': success}
        if len(failed):
            result['failed'] = failed

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def delete_reminder_entry(self, identifier: int) -> Response:
        """Delete a reminder entry by its id"""
        try:
            DBCalendar(self.rotkehlchen.data.db).delete_entry(
                identifier=identifier,
                entry_type='calendar_reminders',
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def update_reminder_entry(self, reminder: ReminderEntry) -> Response:
        """Update the calendar reminder entry with the given identifier using the
        information provided"""
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).update_reminder_entry(
                reminder=reminder,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(_wrap_in_ok_result(
            {'entry_id': calendar_event_id}),
            status_code=HTTPStatus.OK,
        )

    def query_reminders(self, event_id: int) -> Response:
        """Query the calendar table using the provided filter"""
        result = DBCalendar(self.rotkehlchen.data.db).query_reminder_entry(event_id=event_id)
        return api_response(_wrap_in_ok_result(
            result=process_result(result),
            status_code=HTTPStatus.OK,
        ))

    def get_google_calendar_status(self) -> Response:
        """Get Google Calendar authentication status."""
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            is_authenticated = google_calendar.is_authenticated()

            # Get user email if authenticated
            user_email = None
            if is_authenticated:
                user_email = google_calendar.get_connected_user_email()

            return api_response(_wrap_in_ok_result({
                'authenticated': is_authenticated,
                'user_email': user_email,
            }))
        except Exception as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

    def sync_google_calendar(self) -> Response:
        """Manually sync rotki calendar events to Google Calendar."""
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)

            # Get all calendar entries from rotki
            db_calendar = DBCalendar(self.rotkehlchen.data.db)
            calendar_result = db_calendar.query_calendar_entry(
                CalendarFilterQuery.make(),
            )
            calendar_entries = calendar_result['entries']

            # Sync to Google Calendar
            result = google_calendar.sync_events(calendar_entries)
            return api_response(_wrap_in_ok_result(result))
        except Exception as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

    def disconnect_google_calendar(self) -> Response:
        """Disconnect Google Calendar integration."""
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            success = google_calendar.disconnect()

            if success:
                return api_response(_wrap_in_ok_result({'success': True}))
            else:
                return api_response(
                    wrap_in_fail_result('Failed to disconnect Google Calendar'),
                    status_code=HTTPStatus.BAD_REQUEST,
                )
        except Exception as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

    def complete_google_calendar_oauth(self, access_token: str, refresh_token: str) -> Response:
        """Complete Google Calendar OAuth2 flow with an access token from external OAuth flow."""
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            result = google_calendar.complete_oauth_with_token(access_token, refresh_token)
            return api_response(_wrap_in_ok_result(result))
        except Exception as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

    def get_monerium_status(self) -> Response:
        monerium = Monerium(self.rotkehlchen.data.db)
        return api_response(_wrap_in_ok_result(monerium.oauth_client.get_status()))

    def complete_monerium_oauth(self, access_token: str, refresh_token: str, expires_in: int) -> Response:  # noqa: E501
        try:
            result = Monerium(self.rotkehlchen.data.db).oauth_client.complete_oauth(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )
        except RemoteError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(_wrap_in_ok_result(result))

    def disconnect_monerium(self) -> Response:
        Monerium(self.rotkehlchen.data.db).oauth_client.clear_credentials()
        return api_response(OK_RESULT)

    def query_wrap_stats(self, from_ts: Timestamp, to_ts: Timestamp) -> Response:
        """Query starts in the time range selected.
        This endpoint is temporary and will be removed.
        """
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        stats = db.query_wrap_stats(from_ts=from_ts, to_ts=to_ts)
        score = calculate_wrap_score(
            num_of_trades=sum(stats['trades_by_exchange'].values()),
            num_of_transactions=sum(stats['transactions_per_chain'].values()),
            num_of_chains=len(stats['transactions_per_chain']),
            eth_spent_on_gas=FVal(stats['eth_on_gas']),
            gnosis_user=len(stats['gnosis_max_payments_by_currency']) > 0,
        )
        stats['score'] = score
        return api_response(_wrap_in_ok_result(result=stats, status_code=HTTPStatus.OK))

    @async_api_call()
    def get_historical_balance(self, timestamp: Timestamp) -> dict[str, Any]:
        """Query historical balances for all assets at a given timestamp
        by processing historical events
        """
        try:
            balances = HistoricalBalancesManager(self.rotkehlchen.data.db).get_balances(timestamp)
        except DeserializationError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
        except NotFoundError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.NOT_FOUND)

        return _wrap_in_ok_result(
            result=process_result(balances),
            status_code=HTTPStatus.OK,
        )

    @async_api_call()
    def get_historical_asset_balance(self, asset: Asset, timestamp: Timestamp) -> dict[str, Any]:
        """Query historical balance of a specific asset at a given timestamp
        by processing historical events
        """
        try:
            balance = HistoricalBalancesManager(self.rotkehlchen.data.db).get_asset_balance(
                asset=asset,
                timestamp=timestamp,
            )
        except DeserializationError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
        except NotFoundError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.NOT_FOUND)

        return _wrap_in_ok_result(result=balance)

    def get_historical_asset_amounts(
            self,
            asset: Asset | None,
            collection_id: int | None,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        assets: tuple[Asset, ...]
        try:
            if asset is not None:
                assets = (asset,)
            else:  # collection_id is present due to validation.
                with GlobalDBHandler().conn.read_ctx() as cursor:
                    cursor.execute(
                        'SELECT asset FROM multiasset_mappings WHERE collection_id=?',
                        (collection_id,),
                    )
                    assets = tuple(Asset(row[0]) for row in cursor)

            balances, last_group_identifier = HistoricalBalancesManager(self.rotkehlchen.data.db).get_assets_amounts(  # noqa: E501
                assets=assets,
                from_ts=from_timestamp,
                to_ts=to_timestamp,
            )
        except DeserializationError as e:
            return api_response(wrap_in_fail_result(str(e), status_code=HTTPStatus.INTERNAL_SERVER_ERROR))  # noqa: E501
        except NotFoundError as e:
            return api_response(wrap_in_fail_result(str(e), status_code=HTTPStatus.NOT_FOUND))

        result = {
            'times': list(balances),
            'values': [str(x) for x in balances.values()],
        }
        if last_group_identifier is not None:
            result['last_group_identifier'] = last_group_identifier

        return api_response(_wrap_in_ok_result(result=result))

    def get_historical_netvalue(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        try:
            netvalue, missing_prices, last_event_id = HistoricalBalancesManager(self.rotkehlchen.data.db).get_historical_netvalue(  # noqa: E501
                from_ts=from_timestamp,
                to_ts=to_timestamp,
            )
        except DeserializationError as e:
            return api_response(wrap_in_fail_result(str(e), status_code=HTTPStatus.INTERNAL_SERVER_ERROR))  # noqa: E501
        except NotFoundError as e:
            return api_response(wrap_in_fail_result(str(e), status_code=HTTPStatus.NOT_FOUND))

        result = {
            'times': list(netvalue),
            'missing_prices': missing_prices,
            'values': [str(x) for x in netvalue.values()],
        }
        if last_event_id is not None:
            result['last_group_identifier'] = last_event_id

        return api_response(_wrap_in_ok_result(result=result))

    @async_api_call()
    def get_historical_prices_per_asset(
            self,
            asset: Asset,
            interval: int,
            to_timestamp: Timestamp,
            from_timestamp: Timestamp,
            exclude_timestamps: set[Timestamp],
            only_cache_period: int | None = None,
    ) -> dict[str, Any]:
        prices = {}
        no_prices_ts: list[Timestamp] = []
        rate_limited_prices_ts: list[Timestamp] = []
        with (db := self.rotkehlchen.data.db).conn.read_ctx() as cursor:
            main_currency = db.get_setting(cursor=cursor, name='main_currency')

        # Generate timestamps at regular intervals up to current time or
        # to_timestamp (whichever comes first). Skip any timestamps found in exclude_timestamps
        timestamps = [
            ts for i in range((min(ts_now(), to_timestamp) - from_timestamp) // interval + 1)
            if (ts := Timestamp(from_timestamp + (i * interval))) not in exclude_timestamps
        ]
        if only_cache_period is not None:
            # try special assets first: they use custom logic not stored in global DB
            for ts in timestamps:
                special_asset_price = PriceHistorian().get_price_for_special_asset(
                    from_asset=asset,
                    to_asset=main_currency,
                    timestamp=ts,
                    max_seconds_distance=only_cache_period,
                )
                if special_asset_price is not None:
                    prices[ts] = str(special_asset_price)

            if (missing_timestamps := [ts for ts in timestamps if ts not in prices]):
                for price_result in GlobalDBHandler.get_historical_prices(
                    query_data=[(asset, main_currency, ts) for ts in missing_timestamps],
                    max_seconds_distance=only_cache_period,
                ):
                    if price_result is not None:
                        prices[price_result.timestamp] = str(price_result.price)

            return _wrap_in_ok_result(result={
                'prices': prices,
                'no_prices_timestamps': [ts for ts in missing_timestamps if ts not in prices],
                'rate_limited_prices_timestamps': rate_limited_prices_ts,
            })

        total = len(timestamps)
        for processed_count, current_ts in enumerate(timestamps, 1):
            try:
                price = PriceHistorian.query_historical_price(
                    from_asset=asset,
                    to_asset=main_currency,
                    timestamp=current_ts,
                )
            except NoPriceForGivenTimestamp as e:
                if e.rate_limited:
                    rate_limited_prices_ts.append(current_ts)
                else:
                    no_prices_ts.append(current_ts)
            else:
                prices[current_ts] = str(price)

            if processed_count % 10 == 0:  # Send progress update every 10 price queries
                db.msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'total': total,
                        'processed': processed_count,
                        'subtype': str(ProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS),
                    },
                )

        return _wrap_in_ok_result(result={
            'prices': prices,
            'no_prices_timestamps': no_prices_ts,
            'rate_limited_prices_timestamps': rate_limited_prices_ts,
        })

    @async_api_call()
    def force_refetch_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            chain: CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
            address: ChecksumEvmAddress | SolanaAddress | None = None,
    ) -> dict[str, Any]:
        """Re-query transactions for a given time range, adding only missing transactions.

        This function requests a force refetch of transactions for the specified time range,
        bypassing the normal query range checks. This can be useful in cases where transactions
        might have been missed due to API issues or other temporary problems.

        The schema validates that if an address is passed it is a valid tracked address
        in the specified chain.
        """
        log.debug(
            'Force refetching transactions',
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            chain=chain.name if chain else 'all supported chains',
            address=address or 'all addresses',
        )

        if chain == SupportedBlockchain.SOLANA:
            transaction_count = self._query_txs_for_range(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                address=address,
                blockchain=SupportedBlockchain.SOLANA,
                get_count_fn=DBSolanaTx(self.rotkehlchen.data.db).count_transactions_in_range,
                query_for_range_fn=self.rotkehlchen.chains_aggregator.solana.transactions.query_transactions_in_range,
            )
        else:  # EVM chain
            db_evmtx = DBEvmTx(self.rotkehlchen.data.db)
            chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(
                chain_id=(chain_id := chain.to_chain_id()),
            )
            transaction_count = self._query_txs_for_range(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                address=address,
                blockchain=chain,
                get_count_fn=lambda from_ts, to_ts, _chain_id=chain_id: db_evmtx.count_transactions_in_range(  # type: ignore[misc]  # noqa: E501
                    chain_id=_chain_id,
                    from_ts=from_ts,
                    to_ts=to_ts,
                ),
                query_for_range_fn=chain_manager.transactions.refetch_transactions_for_address,
            )

        return _wrap_in_ok_result({'new_transactions_count': transaction_count})

    def _query_txs_for_range(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            address: ChecksumEvmAddress | SolanaAddress | None,
            blockchain: CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
            get_count_fn: Callable[[Timestamp, Timestamp], int],
            query_for_range_fn: Callable[[ChecksumEvmAddress, Timestamp, Timestamp], None] | Callable[[SolanaAddress, Timestamp, Timestamp], None],  # noqa: E501
    ) -> int:
        if address:
            addresses_to_query: tuple[ChecksumEvmAddress | SolanaAddress, ...] = (address,)
        else:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                addresses_to_query = self.rotkehlchen.data.db.get_blockchain_accounts(cursor).get(blockchain)  # noqa: E501

        if len(addresses_to_query) == 0:
            return 0

        # Get total count before query
        before_count = get_count_fn(from_timestamp, to_timestamp)
        for addr in addresses_to_query:
            try:
                query_for_range_fn(addr, from_timestamp, to_timestamp)  # type: ignore[arg-type]
            except (sqlcipher.OperationalError, RemoteError, DeserializationError) as e:  # pylint: disable=no-member
                log.debug(
                    f'Skipping transaction refetching for {addr} on {blockchain.name.lower()} due to: {e!s}')  # noqa: E501
                continue

        # Get total count after query and count the difference as addition
        after_count = get_count_fn(from_timestamp, to_timestamp)
        return after_count - before_count

    def addresses_interacted_before(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
    ) -> Response:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM history_events JOIN chain_events_info ON '
                'history_events.identifier=chain_events_info.identifier WHERE '
                'location_label=? AND address=?',
                (from_address, to_address),
            )
            return api_response(_wrap_in_ok_result(result=cursor.fetchone()[0] > 0))

    @async_api_call()
    def prepare_token_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            blockchain: 'SUPPORTED_EVM_CHAINS_TYPE',
            token: EvmToken,
            amount: FVal,
    ) -> dict[str, Any]:
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain=blockchain)

        try:
            payload = manager.active_management.create_token_transfer(
                from_address=from_address,
                to_address=to_address,
                token=token,
                amount=amount,
            )
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)

        return _wrap_in_ok_result(result=payload)

    @async_api_call()
    def get_gnosis_pay_safe_admin_addresses(self) -> dict[str, Any]:
        if not (tracked_addresses := self.rotkehlchen.chains_aggregator.accounts.gnosis):
            return _wrap_in_ok_result({})

        gnosis_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(ChainID.GNOSIS)

        try:
            addresses_with_admins = gnosis_manager.node_inquirer.get_safe_admins_for_addresses(tracked_addresses)  # type: ignore  # mypy doesn't identify the inquirer as GnosisInquirer  # noqa: E501
        except (RemoteError, DeserializationError) as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return _wrap_in_ok_result(addresses_with_admins)

    @async_api_call()
    def fetch_gnosis_pay_nonce(self) -> dict[str, Any]:
        try:
            nonce = fetch_gnosis_pay_siwe_nonce()
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return _wrap_in_ok_result(nonce)

    @async_api_call()
    def verify_gnosis_pay_siwe_signature(self, message: str, signature: str) -> dict[str, Any]:
        try:
            token = external_verify_gnosis_pay_siwe_signature(
                message=message,
                signature=signature,
            )
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        # save the queried token in the db
        log.debug('Got a valid token from gnosis pay. Saving it in credentials')
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=[ExternalServiceApiCredentials(
                    service=ExternalService.GNOSIS_PAY,
                    api_key=ApiKey(token),
                )],
            )

        chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(ChainID.GNOSIS)
        gnosispay_decoder = chain_manager.transactions_decoder.decoders.get('GnosisPay')
        if gnosispay_decoder is not None:
            gnosispay_decoder.reload_data()  # type: ignore
            if gnosispay_decoder.gnosispay_api is not None:  # type: ignore
                gevent.spawn(
                    gnosispay_decoder.gnosispay_api.backfill_missing_events,  # type: ignore
                )

        return OK_RESULT

    @async_api_call()
    def prepare_native_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            chain: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            amount: FVal,
    ) -> dict[str, Any]:
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(chain.to_blockchain())  # type: ignore[call-overload]

        try:
            payload = manager.active_management.transfer_native_token(
                from_address=from_address,
                to_address=to_address,
                amount=amount,
            )
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)

        return _wrap_in_ok_result(result=payload)

    @async_api_call()
    def fetch_token_balance_for_address(
            self,
            address: ChecksumEvmAddress,
            evm_chain: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            asset: 'CryptoAsset',
    ) -> dict[str, Any]:
        node_inquirer = self.rotkehlchen.chains_aggregator.get_evm_manager(evm_chain).node_inquirer
        try:
            if asset == node_inquirer.native_token:
                balance = node_inquirer.get_multi_balance([address])[address]
            elif (token := asset.resolve_to_evm_token()).chain_id == evm_chain:
                balance = token_normalized_value(
                    token_amount=node_inquirer.call_contract(
                        contract_address=token.evm_address,
                        abi=node_inquirer.contracts.erc20_abi,
                        method_name='balanceOf',
                        arguments=[address],
                    ),
                    token=token,
                )
            else:
                return wrap_in_fail_result(
                    message='Token exists on different chain than requested',
                    status_code=HTTPStatus.CONFLICT,
                )
        except (RemoteError, WrongAssetType, InputError) as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return _wrap_in_ok_result(result=balance)

    @async_api_call()
    def migrate_solana_token(
            self,
            old_asset: 'CryptoAsset',
            address: 'SolanaAddress',
            decimals: int,
            token_kind: 'SOLANA_TOKEN_KINDS_TYPE',
    ) -> dict[str, Any]:
        """This is a temporary endpoint to correct custom user input
        solana tokens input before release 1.40.

        Creates a new solana token with the provided address and metadata,
        replaces all references in the database and cleans up the migration table if necessary.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if cursor.execute(
                'SELECT COUNT(*) FROM user_added_solana_tokens WHERE identifier = ?',
                (old_asset.identifier,),
            ).fetchone()[0] == 0:
                return wrap_in_fail_result(
                    message='Token does not exist in user_added_solana_tokens table',
                    status_code=HTTPStatus.CONFLICT,
                )
        with self.migration_lock:  # prevent race conditions when migrating last few tokens simultaneously  # noqa: E501
            try:
                GlobalDBHandler.add_asset(solana_token := SolanaToken.initialize(
                    address=address,
                    token_kind=token_kind,
                    decimals=decimals,
                    name=old_asset.name,
                    symbol=old_asset.symbol,
                    started=old_asset.started,
                    forked=old_asset.forked,
                    swapped_for=old_asset.swapped_for,
                    coingecko=old_asset.coingecko,
                    cryptocompare=old_asset.cryptocompare,
                ))
            except InputError as e:
                return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

            try:
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    self.rotkehlchen.data.db.add_asset_identifiers(
                        write_cursor=write_cursor,
                        asset_identifiers=[solana_token.identifier],
                    )
                self.rotkehlchen.data.db.replace_asset_identifier(
                    source_identifier=old_asset.identifier,
                    target_asset=solana_token,
                )
            except (UnknownAsset, InputError) as e:
                # delete newly created asset from global db, safe since we just added it above
                GlobalDBHandler.delete_asset_by_identifier(solana_token.identifier)
                with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                    # delete won't fail, either asset doesn't exist or has no references
                    self.rotkehlchen.data.db.delete_asset_identifier(
                        write_cursor=write_cursor,
                        asset_id=solana_token.identifier,
                    )
                return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                if write_cursor.execute('SELECT COUNT(*) FROM user_added_solana_tokens').fetchone()[0] == 0:  # noqa: E501
                    write_cursor.execute('DROP TABLE user_added_solana_tokens')

        return OK_RESULT

    def get_premium_registered_devices(self) -> Response:
        """Get list of devices registered to the premium account."""
        assert self.rotkehlchen.premium is not None, 'Should not be None since we use @require_premium_user() decorator'  # noqa: E501
        try:
            result = self.rotkehlchen.premium.get_remote_devices_information()
        except RemoteError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(result))

    def get_premium_capabilities(self) -> Response:
        """Get capabilities for the premium account."""
        assert self.rotkehlchen.premium is not None, 'Should not be None since we use @require_premium_user() decorator'  # noqa: E501
        try:
            capabilities = self.rotkehlchen.premium.get_capabilities()
        except (PremiumAuthenticationError, RemoteError) as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(capabilities))

    def delete_premium_registered_device(self, device_identifier: str) -> Response:
        """Delete a device from the premium account by identifier."""
        assert self.rotkehlchen.premium is not None, 'Should not be None since we use @require_premium_user() decorator'  # noqa: E501
        try:
            self.rotkehlchen.premium.delete_device(device_identifier)
        except InputError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)
        except RemoteError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.BAD_GATEWAY)

        return api_response(OK_RESULT)

    def edit_premium_registered_device(self, device_identifier: str, device_name: str) -> Response:
        """Edit a device's name in the premium account by identifier."""
        assert self.rotkehlchen.premium is not None, 'Should not be None since we use @require_premium_user() decorator'  # noqa: E501
        try:
            self.rotkehlchen.premium.edit_device(device_identifier, device_name)
        except RemoteError as e:
            return api_response(wrap_in_fail_result(message=str(e)), HTTPStatus.CONFLICT)

        return api_response(OK_RESULT)

    def match_asset_movements(
            self,
            asset_movement_identifier: int,
            matched_event_identifier: int,
    ) -> Response:
        """Match an exchange asset movement to an onchain event."""
        events_db = DBHistoryEvents(database=self.rotkehlchen.data.db)
        asset_movement = matched_event = None
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            for event in events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    identifiers=[asset_movement_identifier, matched_event_identifier],
                ),
            ):
                if event.identifier == asset_movement_identifier:
                    asset_movement = event
                elif event.identifier == matched_event_identifier:
                    matched_event = event

        if asset_movement is None or not isinstance(asset_movement, AssetMovement):
            error_msg = f'No asset movement event found in the DB for identifier {asset_movement_identifier}'  # noqa: E501
        elif matched_event is None:
            error_msg = f'No event found in the DB for identifier {matched_event_identifier}'
        else:
            success, error_msg = update_asset_movement_matched_event(
                events_db=events_db,
                asset_movement=asset_movement,
                matched_event=matched_event,
                is_deposit=asset_movement.event_type == HistoryEventType.DEPOSIT,
            )
            if success:
                return api_response(OK_RESULT)

        return api_response(wrap_in_fail_result(message=error_msg), HTTPStatus.BAD_REQUEST)

    def get_unmatched_asset_movements(self) -> Response:
        """Get the group identifiers of all unmatched asset movements."""
        asset_movements, _ = get_unmatched_asset_movements(database=self.rotkehlchen.data.db)
        return api_response(_wrap_in_ok_result(
            result=list(dict.fromkeys(event.group_identifier for event in asset_movements)),
        ))

    def get_matches_for_asset_movement(
            self,
            asset_movement_group_identifier: str,
            time_range: int,
    ) -> Response:
        events_db = DBHistoryEvents(database=self.rotkehlchen.data.db)
        asset_movement = fee_event = None
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            for event in events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    group_identifiers=[asset_movement_group_identifier],
                    entry_types=IncludeExcludeFilterData([HistoryBaseEntryType.ASSET_MOVEMENT_EVENT]),
                ),
            ):
                if event.event_subtype == HistoryEventSubType.FEE:
                    fee_event = event
                else:  # deposit or withdrawal
                    asset_movement = event

        if asset_movement is None:
            return api_response(wrap_in_fail_result(
                message=f'No asset movement event found in the DB for group identifier {asset_movement_group_identifier}',  # noqa: E501
            ), HTTPStatus.BAD_REQUEST)

        close_match_identifiers = [x.identifier for x in find_asset_movement_matches(
            events_db=events_db,
            asset_movement=asset_movement,  # type: ignore  # filtered by entry_types
            is_deposit=asset_movement.event_type == HistoryEventType.DEPOSIT,
            fee_event=fee_event,  # type: ignore  # filtered by entry_types
            match_window=time_range,
        )]

        asset_movement_timestamp = ts_ms_to_sec(asset_movement.timestamp)
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            other_events = events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=Timestamp(asset_movement_timestamp - time_range),
                    to_ts=Timestamp(asset_movement_timestamp + time_range),
                    ignored_ids=[str(x) for x in close_match_identifiers] + [str(asset_movement.identifier)],  # noqa: E501
                ),
            )

        return api_response(_wrap_in_ok_result(result={
            'close_matches': close_match_identifiers,
            'other_events': [x.identifier for x in other_events],
        }))
