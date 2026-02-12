import datetime
import json
import logging
import os
import sys
import tempfile
import traceback
from collections import defaultdict
from collections.abc import Callable, Sequence
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, overload

import gevent
from flask import Response, make_response, send_file
from gevent.event import Event
from gevent.lock import Semaphore
from solders.solders import Signature
from sqlcipher3 import dbapi2 as sqlcipher
from web3.exceptions import BadFunctionCallOutput
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.export.csv import (
    FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV,
    CSVWriteError,
)
from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, BalanceType
from rotkehlchen.accounting.structures.processed_event import AccountingEventExportType
from rotkehlchen.api.rest_helpers.downloads import register_post_download_cleanup
from rotkehlchen.api.rest_helpers.wrap import calculate_wrap_score
from rotkehlchen.api.services.accounting import AccountingService
from rotkehlchen.api.services.accounts import AccountsService
from rotkehlchen.api.services.assets import AssetsService
from rotkehlchen.api.services.balances import BalancesService
from rotkehlchen.api.services.exchanges import ExchangesService
from rotkehlchen.api.services.external_services import ExternalServicesService
from rotkehlchen.api.services.history import HistoryService
from rotkehlchen.api.services.history_events import HistoryEventsService
from rotkehlchen.api.services.integrations import IntegrationsService
from rotkehlchen.api.services.settings import SettingsService
from rotkehlchen.api.services.transactions import TransactionsService
from rotkehlchen.api.services.user_data import UserDataService
from rotkehlchen.api.v1.types import IncludeExcludeFilterData, TaskName
from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
    SolanaToken,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import OptionalBlockchainAccount, SingleBlockchainAccountData
from rotkehlchen.chain.ethereum.airdrops import check_airdrops
from rotkehlchen.chain.ethereum.modules.eth2.structures import PerformanceStatusFilter
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.chain.ethereum.modules.liquity.statistics import get_stats as get_liquity_stats
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.evm.types import (
    ChainID,
    EvmIndexer,
    WeightedNode,
)
from rotkehlchen.constants.misc import (
    AIRDROPS_TOLERANCE,
    DEFAULT_LOGLEVEL,
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    HTTP_STATUS_INTERNAL_DB_ERROR,
)
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, ReminderEntry
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import (
    AccountingRulesFilterQuery,
    AddressbookFilterQuery,
    AssetsFilterQuery,
    CounterpartyAssetMappingsFilterQuery,
    CustomAssetsFilterQuery,
    DBFilterQuery,
    HistoricalBalancesFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
    LevenshteinFilterQuery,
    LocationAssetMappingsFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.api import (
    AuthenticationError,
    IncorrectApiKeyFormat,
    PremiumApiError,
    PremiumAuthenticationError,
    PremiumPermissionError,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    DBSchemaError,
    DBUpgradeError,
    EthSyncError,
    GreenletKilledError,
    InputError,
    ModuleInactive,
    NotFoundError,
    RemoteError,
    SystemPermissionError,
)
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES, SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.utils import query_binance_exchange_pairs
from rotkehlchen.externalapis.github import Github
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.asset_updates.manager import ASSETS_VERSION_KEY
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.skipped import (
    export_skipped_external_events,
    get_skipped_external_events_summary,
    reprocess_skipped_external_events,
)
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    PremiumCredentials,
    UserLimitType,
    get_user_limit,
)
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.tasks.events import (
    ENTRY_TYPES_TO_EXCLUDE_FROM_MATCHING,
    find_asset_movement_matches,
    find_customized_event_duplicate_groups,
    get_already_matched_event_ids,
    get_unmatched_asset_movements,
    process_asset_movements,
    should_exclude_possible_match,
    update_asset_movement_matched_event,
)
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
    CHAINS_WITH_TRANSACTIONS_TYPE,
    CHAINS_WITH_TX_DECODING_TYPE,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE,
    SOLANA_TOKEN_KINDS_TYPE,
    SUPPORTED_BITCOIN_CHAINS_TYPE,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS_TYPE,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    BlockchainAddress,
    BTCAddress,
    BTCTxId,
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
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.chain.evm.manager import EvmManager
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


class RestAPI:
    """ The Object holding the logic that runs inside all the API calls"""
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self.accounts_service = AccountsService(rotkehlchen)
        self.accounting_service = AccountingService(rotkehlchen)
        self.assets_service = AssetsService(rotkehlchen)
        self.balances_service = BalancesService(rotkehlchen)
        self.exchanges_service = ExchangesService(rotkehlchen)
        self.external_services_service = ExternalServicesService(rotkehlchen)
        self.history_events_service = HistoryEventsService(rotkehlchen)
        self.history_service = HistoryService(rotkehlchen)
        self.integrations_service = IntegrationsService(rotkehlchen)
        self.settings_service = SettingsService(rotkehlchen)
        self.transactions_service = TransactionsService(rotkehlchen)
        self.user_data_service = UserDataService(rotkehlchen)
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
        success, message, new_settings = self.settings_service.set_settings(settings)
        if not success:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        result_dict = _wrap_in_ok_result(new_settings)
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    def get_settings(self) -> Response:
        settings = self.settings_service.get_settings()
        result_dict = _wrap_in_ok_result(settings)
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
        result = self.balances_service.get_exchange_rates(given_currencies)
        return _wrap_in_ok_result(result)

    @async_api_call()
    def query_all_balances(
            self,
            save_data: bool,
            ignore_errors: bool,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        return self.balances_service.query_all_balances(
            save_data=save_data,
            ignore_errors=ignore_errors,
            ignore_cache=ignore_cache,
        )

    def get_external_services(self) -> Response:
        response_dict = self.external_services_service.get_services()
        return api_response(_wrap_in_ok_result(response_dict), status_code=HTTPStatus.OK)

    def add_external_services(self, services: list[ExternalServiceApiCredentials]) -> Response:
        success, message, response_dict, status_code = (
            self.external_services_service.add_services(services)
        )
        if not success:
            return api_response(wrap_in_fail_result(message), status_code=status_code)
        return api_response(_wrap_in_ok_result(response_dict), status_code=status_code)

    def delete_external_services(self, services: list[ExternalService]) -> Response:
        response_dict = self.external_services_service.delete_services(services)
        return api_response(_wrap_in_ok_result(response_dict), status_code=HTTPStatus.OK)

    def get_exchanges(self) -> Response:
        exchanges = self.exchanges_service.get_exchanges()
        return api_response(
            _wrap_in_ok_result(exchanges),
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
            kraken_futures_api_key: ApiKey | None,
            kraken_futures_api_secret: ApiSecret | None,
            binance_markets: list[str] | None,
            okx_location: Optional['OkxLocation'],
    ) -> Response:
        result, msg, status_code = self.exchanges_service.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            kraken_futures_api_key=kraken_futures_api_key,
            kraken_futures_api_secret=kraken_futures_api_secret,
            binance_markets=binance_markets,
            okx_location=okx_location,
        )
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
            kraken_futures_api_key: ApiKey | None,
            kraken_futures_api_secret: ApiSecret | None,
            binance_markets: list[str] | None,
            okx_location: Optional['OkxLocation'],
    ) -> Response:
        result, msg, status_code = self.exchanges_service.edit_exchange(
            name=name,
            location=location,
            new_name=new_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            kraken_futures_api_key=kraken_futures_api_key,
            kraken_futures_api_secret=kraken_futures_api_secret,
            binance_markets=binance_markets,
            okx_location=okx_location,
        )
        return api_response(_wrap_in_result(result, msg), status_code=status_code)

    def remove_exchange(self, name: str, location: Location) -> Response:
        result, message, status_code = self.exchanges_service.remove_exchange(
            name=name,
            location=location,
        )
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    @async_api_call()
    def query_exchange_history_events(
            self,
            location: Location,
            name: str | None,
    ) -> dict[str, Any]:
        """Queries new history events for the specified exchange and saves them in the database."""
        return self.exchanges_service.query_exchange_history_events(
            location=location,
            name=name,
        )

    @async_api_call()
    def query_exchange_history_events_in_range(
            self,
            location: Location,
            name: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> dict[str, Any]:
        response = self.exchanges_service.query_exchange_history_events_in_range(
            location=location,
            name=name,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        if response.get('result') is None:
            return response
        return _wrap_in_ok_result(response['result'])

    @async_api_call()
    def query_exchange_balances(
            self,
            location: Location | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        return self.exchanges_service.query_exchange_balances(
            location=location,
            ignore_cache=ignore_cache,
            value_threshold=value_threshold,
        )

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
        return self.accounts_service.get_xpub_balances(
            xpub_data=xpub_data,
            ignore_cache=ignore_cache,
        )

    def add_history_events(self, events: list['HistoryBaseEntry']) -> Response:
        """Add list of history events to DB. Returns identifier of first event.
        The first event is the main event, subsequent events are related (e.g. fees).
        """
        response_data = self.history_events_service.add_history_events(events)
        return make_response_from_dict(response_data)

    def edit_history_events(
            self,
            events: list['HistoryBaseEntry'],
            identifiers: list[int] | None,
    ) -> Response:
        response_data = self.history_events_service.edit_history_events(
            events=events,
            identifiers=identifiers,
        )
        return make_response_from_dict(response_data)

    def delete_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            force_delete: bool,
            requested_identifiers: list[int] | None = None,
    ) -> Response:
        response_data = self.history_events_service.delete_history_events(
            filter_query=filter_query,
            force_delete=force_delete,
            requested_identifiers=requested_identifiers,
        )
        return make_response_from_dict(response_data)

    def get_tags(self) -> Response:
        response_data = self.user_data_service.get_tags()
        return make_response_from_dict(response_data)

    def add_tag(
            self,
            name: str,
            description: str | None,
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> Response:
        response_data = self.user_data_service.add_tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        return make_response_from_dict(response_data)

    def edit_tag(
            self,
            name: str,
            new_name: str | None,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
    ) -> Response:
        response_data = self.user_data_service.edit_tag(
            name=name,
            new_name=new_name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        return make_response_from_dict(response_data)

    def delete_tag(self, name: str) -> Response:
        response_data = self.user_data_service.delete_tag(name)
        return make_response_from_dict(response_data)

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
        response_data = self.assets_service.query_list_of_all_assets(filter_query)
        return make_response_from_dict(response_data)

    def get_assets_mappings(self, identifiers: list[str]) -> Response:
        response_data = self.assets_service.get_assets_mappings(identifiers)
        return make_response_from_dict(response_data)

    def search_assets(self, filter_query: AssetsFilterQuery) -> Response:
        response_data = self.assets_service.search_assets(filter_query)
        return make_response_from_dict(response_data)

    def search_assets_levenshtein(
            self,
            filter_query: LevenshteinFilterQuery,
            limit: int | None,
            search_nfts: bool,
    ) -> Response:
        response_data = self.assets_service.search_assets_levenshtein(
            filter_query=filter_query,
            limit=limit,
            search_nfts=search_nfts,
        )
        return make_response_from_dict(response_data)

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
        response_data = self.assets_service.query_owned_assets()
        return make_response_from_dict(response_data)

    def get_asset_types(self) -> Response:
        response_data = self.assets_service.get_asset_types()
        return make_response_from_dict(response_data)

    def add_user_asset(self, asset: AssetWithOracles) -> Response:
        response_data = self.assets_service.add_user_asset(asset)
        return make_response_from_dict(response_data)

    def edit_user_asset(self, asset: AssetWithOracles) -> Response:
        response_data = self.assets_service.edit_user_asset(asset)
        return make_response_from_dict(response_data)

    def delete_asset(self, identifier: str) -> Response:
        response_data = self.assets_service.delete_asset(identifier)
        return make_response_from_dict(response_data)

    def replace_asset(self, source_identifier: str, target_asset: Asset) -> Response:
        response_data = self.assets_service.replace_asset(source_identifier, target_asset)
        return make_response_from_dict(response_data)

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
        return self.history_service.process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

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
        return self.history_service.get_history_debug(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            directory_path=directory_path,
        )

    if getattr(sys, 'frozen', False) is False:
        @async_api_call()
        def import_history_debug(self, filepath: Path) -> dict[str, Any]:
            """Imports the PnL debug data for processing and report generation"""
            return self.history_service.import_history_debug(filepath=filepath)

    @async_api_call()
    def export_accounting_rules(self, directory_path: Path | None) -> dict[str, Any]:
        """Exports all the accounting rules and linked properties into a json file
        in the given directory."""
        return self.accounting_service.export_accounting_rules(directory_path)

    @async_api_call()
    def import_accounting_rules(self, filepath: Path) -> dict[str, Any]:
        """Imports the accounting rules from the given json file and stores them in the DB."""
        return self.accounting_service.import_accounting_rules(filepath)

    def get_history_actionable_items(self) -> Response:
        response_data = self.history_service.get_history_actionable_items()
        return make_response_from_dict(response_data)

    def get_history_status(self) -> Response:
        response_data = self.history_service.get_history_status()
        return make_response_from_dict(response_data)

    def query_periodic_data(self) -> Response:
        data = self.rotkehlchen.query_periodic_data()
        result = process_result(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @async_api_call()
    def add_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> dict[str, Any]:
        return self.accounts_service.add_xpub(xpub_data)

    @async_api_call()
    def delete_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> dict[str, Any]:
        return self.accounts_service.delete_xpub(xpub_data)

    def edit_xpub(
            self,
            xpub_data: 'XpubData',
    ) -> Response:
        response_data = self.accounts_service.edit_xpub(xpub_data)
        return make_response_from_dict(response_data)

    def add_evm_accounts(
            self,
            account_data: list[SingleBlockchainAccountData[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        return self.accounts_service.add_evm_accounts(account_data)

    @async_api_call()
    def refresh_evm_accounts(self) -> dict[str, Any]:
        return self.accounts_service.refresh_evm_accounts()

    def get_blockchain_accounts(self, blockchain: SupportedBlockchain) -> Response:
        response_data = self.accounts_service.get_blockchain_accounts(blockchain)
        return make_response_from_dict(response_data)

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
        return self.accounts_service.add_single_blockchain_accounts(
            chain=chain,
            account_data=account_data,
        )

    def edit_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        return self.accounts_service.edit_single_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
        )

    @async_api_call()
    def edit_chain_type_accounts_labels(
            self,
            accounts: list[SingleBlockchainAccountData],
    ) -> dict[str, Any]:
        return self.accounts_service.edit_chain_type_accounts_labels(accounts)

    def remove_single_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> dict[str, Any]:
        return self.accounts_service.remove_single_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )

    @async_api_call()
    def remove_chain_type_accounts(
            self,
            chain_type: ChainType,
            accounts: ListOfBlockchainAddresses,
    ) -> dict[str, Any]:
        return self.accounts_service.remove_chain_type_accounts(
            chain_type=chain_type,
            accounts=accounts,
        )

    @async_api_call()
    def get_manually_tracked_balances(self, value_threshold: FVal | None) -> dict[str, Any]:
        return self.accounts_service.get_manually_tracked_balances(value_threshold=value_threshold)

    @async_api_call()
    def add_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        return self.accounts_service.add_manually_tracked_balances(data=data)

    @async_api_call()
    def edit_manually_tracked_balances(
            self,
            data: list[ManuallyTrackedBalance],
    ) -> dict[str, Any]:
        return self.accounts_service.edit_manually_tracked_balances(data=data)

    @async_api_call()
    def remove_manually_tracked_balances(
            self,
            ids: list[int],
    ) -> dict[str, Any]:
        return self.accounts_service.remove_manually_tracked_balances(ids=ids)

    def get_ignored_assets(self) -> Response:
        response_data = self.accounts_service.get_ignored_assets()
        return make_response_from_dict(response_data)

    def add_ignored_assets(self, assets_to_ignore: list[Asset]) -> Response:
        response_data = self.accounts_service.add_ignored_assets(assets_to_ignore)
        return make_response_from_dict(response_data)

    def remove_ignored_assets(self, assets: list[Asset]) -> Response:
        response_data = self.accounts_service.remove_ignored_assets(assets)
        return make_response_from_dict(response_data)

    def add_ignored_action_ids(self, action_ids: list[str]) -> Response:
        response_data = self.user_data_service.add_ignored_action_ids(action_ids)
        return make_response_from_dict(response_data)

    def remove_ignored_action_ids(
            self,
            action_ids: list[str],
    ) -> Response:
        response_data = self.user_data_service.remove_ignored_action_ids(action_ids)
        return make_response_from_dict(response_data)

    def get_queried_addresses_per_module(self) -> Response:
        response_data = self.user_data_service.get_queried_addresses_per_module()
        return make_response_from_dict(response_data)

    def add_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> Response:
        response_data = self.user_data_service.add_queried_address_per_module(
            module=module,
            address=address,
        )
        return make_response_from_dict(response_data)

    def remove_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> Response:
        response_data = self.user_data_service.remove_queried_address_per_module(
            module=module,
            address=address,
        )
        return make_response_from_dict(response_data)

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
        response_data = self.transactions_service.get_rpc_nodes(blockchain)
        return make_response_from_dict(response_data)

    def add_rpc_node(self, node: WeightedNode) -> Response:
        response_data = self.transactions_service.add_rpc_node(node)
        return make_response_from_dict(response_data)

    def update_and_connect_rpc_node(self, node: WeightedNode) -> Response:
        response_data = self.transactions_service.update_and_connect_rpc_node(node)
        return make_response_from_dict(response_data)

    def delete_rpc_node(self, identifier: int, blockchain: SupportedBlockchain) -> Response:
        response_data = self.transactions_service.delete_rpc_node(
            identifier=identifier,
            blockchain=blockchain,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def connect_rpc_node(
            self,
            identifier: int | None,
            blockchain: SupportedBlockchain,
    ) -> dict[str, Any]:
        return self.transactions_service.connect_rpc_node(
            identifier=identifier,
            blockchain=blockchain,
        )

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

    def get_watchers(self) -> Response:
        response_data = self.transactions_service.get_watchers()
        return make_response_from_dict(response_data)

    def add_watchers(self, watchers: list[dict[str, Any]]) -> Response:
        response_data = self.transactions_service.add_watchers(watchers)
        return make_response_from_dict(response_data)

    def edit_watchers(self, watchers: list[dict[str, Any]]) -> Response:
        response_data = self.transactions_service.edit_watchers(watchers)
        return make_response_from_dict(response_data)

    def delete_watchers(self, watchers: list[str]) -> Response:
        response_data = self.transactions_service.delete_watchers(watchers)
        return make_response_from_dict(response_data)

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

    @async_api_call()
    def refetch_staking_events(
            self,
            entry_type: Literal[HistoryEventQueryType.BLOCK_PRODUCTIONS, HistoryEventQueryType.ETH_WITHDRAWALS],  # noqa: E501
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            validator_indices: list[int],
            addresses: list[ChecksumEvmAddress],
    ) -> dict[str, Any]:
        return self.history_service.refetch_staking_events(
            entry_type=entry_type,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            validator_indices=validator_indices,
            addresses=addresses,
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
        response_data = self.transactions_service.delete_blockchain_transaction_data(
            chain=chain,
            tx_ref=tx_ref,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def refresh_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            accounts: list[OptionalBlockchainAccount] | None,
    ) -> dict[str, Any]:
        return self.transactions_service.refresh_transactions(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            accounts=accounts,
        )

    @async_api_call()
    def decode_given_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            tx_refs: list[EVMTxHash | Signature],
            delete_custom: bool,
            custom_indexers_order: list[EvmIndexer] | None = None,
    ) -> dict[str, Any]:
        return self.transactions_service.decode_given_transactions(
            chain=chain,
            tx_refs=tx_refs,
            delete_custom=delete_custom,
            custom_indexers_order=custom_indexers_order,
        )

    @async_api_call()
    def decode_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            force_redecode: bool,
    ) -> dict[str, Any]:
        return self.transactions_service.decode_transactions(
            chain=chain,
            force_redecode=force_redecode,
        )

    @async_api_call()
    def get_history_status_summary(self) -> dict[str, Any]:
        """Get the last timestamp when evm transactions and exchanges were queried and how many
        transactions are waiting to be decoded.
        """
        return self.history_service.get_history_status_summary()

    @async_api_call()
    def get_evm_transactions_status(self) -> dict[str, Any]:
        return self.transactions_service.get_evm_transactions_status()

    @async_api_call()
    def get_count_transactions_not_decoded(self) -> dict[str, Any]:
        return self.transactions_service.get_count_transactions_not_decoded()

    def upload_asset_icon(self, asset: Asset, filepath: Path) -> Response:
        response_data = self.assets_service.upload_asset_icon(asset=asset, filepath=filepath)
        return make_response_from_dict(response_data)

    def refresh_asset_icon(self, asset: AssetWithOracles) -> Response:
        response_data = self.assets_service.refresh_asset_icon(asset)
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_current_assets_price(
            self,
            assets: list[AssetWithNameAndType],
            target_asset: Asset,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        return self.assets_service.get_current_assets_price(
            assets=assets,
            target_asset=target_asset,
            ignore_cache=ignore_cache,
        )

    def query_asset_mappings_by_type(
            self,
            dict_keys: tuple[str, str, str],
            mapping_type: Literal['location', 'counterparty'],
            location_or_counterparty_reader_callback: Callable,
            filter_query: LocationAssetMappingsFilterQuery | CounterpartyAssetMappingsFilterQuery,
            query_columns: Literal['local_id, location, exchange_symbol', 'local_id, counterparty, symbol'],  # noqa: E501
    ) -> Response:
        response_data = self.assets_service.query_asset_mappings_by_type(
            dict_keys=dict_keys,
            mapping_type=mapping_type,
            location_or_counterparty_reader_callback=location_or_counterparty_reader_callback,
            filter_query=filter_query,
            query_columns=query_columns,
        )
        return make_response_from_dict(response_data)

    def perform_asset_mapping_operation(
            self,
            mapping_fn: Callable,
            entries: Sequence[LocationAssetMappingUpdateEntry | LocationAssetMappingDeleteEntry | CounterpartyAssetMappingUpdateEntry | CounterpartyAssetMappingDeleteEntry],  # noqa: E501
    ) -> Response:
        response_data = self.assets_service.perform_asset_mapping_operation(
            mapping_fn=mapping_fn,
            entries=entries,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_historical_assets_price(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            only_cache_period: int | None = None,
    ) -> dict[str, Any]:
        return self.assets_service.get_historical_assets_price(
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
            only_cache_period=only_cache_period,
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
        return self.assets_service.create_oracle_cache(
            oracle=oracle,
            from_asset=from_asset,
            to_asset=to_asset,
            purge_old=purge_old,
        )

    def delete_oracle_cache(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Response:
        response_data = self.assets_service.delete_oracle_cache(
            oracle=oracle,
            from_asset=from_asset,
            to_asset=to_asset,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_oracle_cache(self, oracle: HistoricalPriceOracle) -> dict[str, Any]:
        return self.assets_service.get_oracle_cache(oracle)

    def get_supported_oracles(self) -> Response:
        response_data = self.assets_service.get_supported_oracles()
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_token_info(self, address: ChecksumEvmAddress, chain_id: SUPPORTED_CHAIN_IDS) -> dict[str, Any]:  # noqa: E501
        return self.assets_service.get_token_info(address=address, chain_id=chain_id)

    @async_api_call()
    def get_assets_updates(self) -> dict[str, Any]:
        return self.assets_service.get_assets_updates()

    @async_api_call()
    def perform_assets_updates(
            self,
            up_to_version: int | None,
            conflicts: dict[Asset, Literal['remote', 'local']] | None,
    ) -> dict[str, Any]:
        return self.assets_service.perform_assets_updates(
            up_to_version=up_to_version,
            conflicts=conflicts,
        )

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
        response_data = self.assets_service.add_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
            timestamp=timestamp,
        )
        return make_response_from_dict(response_data)

    def edit_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> Response:
        response_data = self.assets_service.edit_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
            timestamp=timestamp,
        )
        return make_response_from_dict(response_data)

    def get_manual_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> Response:
        response_data = self.assets_service.get_manual_prices(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        return make_response_from_dict(response_data)

    def delete_manual_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Response:
        response_data = self.assets_service.delete_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_nfts(self, ignore_cache: bool) -> dict[str, Any]:
        return self.assets_service.get_nfts(ignore_cache=ignore_cache)

    @async_api_call()
    def get_nfts_balances(
            self,
            filter_query: NFTFilterQuery,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        return self.assets_service.get_nfts_balances(
            filter_query=filter_query,
            ignore_cache=ignore_cache,
        )

    def get_manual_latest_prices(
            self,
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> Response:
        response_data = self.assets_service.get_manual_latest_prices(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_nfts_with_price(self, lps_handling: NftLpHandling) -> dict[str, Any]:
        return self.assets_service.get_nfts_with_price(lps_handling=lps_handling)

    def add_manual_latest_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> Response:
        response_data = self.assets_service.add_manual_latest_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
        )
        return make_response_from_dict(response_data)

    def delete_manual_latest_price(
            self,
            asset: Asset,
    ) -> Response:
        response_data = self.assets_service.delete_manual_latest_price(asset=asset)
        return make_response_from_dict(response_data)

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
        return self.history_service.query_online_events(query_type=query_type)

    def get_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            aggregate_by_group_ids: bool,
    ) -> Response:
        response_data = self.history_service.get_history_events(
            filter_query=filter_query,
            aggregate_by_group_ids=aggregate_by_group_ids,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def query_kraken_staking_events(
            self,
            only_cache: bool,
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        return self.history_service.query_kraken_staking_events(
            only_cache=only_cache,
            query_filter=query_filter,
            value_filter=value_filter,
        )

    @async_api_call()
    def export_user_assets(self, path: Path | None) -> dict[str, Any]:
        return self.assets_service.export_user_assets(path)

    @async_api_call()
    def import_user_assets(self, path: Path) -> dict[str, Any]:
        return self.assets_service.import_user_assets(path)

    def download_user_assets(self, file_path: str) -> Response:
        return self.assets_service.download_user_assets(file_path)

    def get_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        response_data = self.user_data_service.get_user_db_snapshot(timestamp)
        return make_response_from_dict(response_data)

    def edit_user_db_snapshot(
            self,
            timestamp: Timestamp,
            location_data_snapshot: list[LocationData],
            balances_snapshot: list[DBAssetBalance],
    ) -> Response:
        response_data = self.user_data_service.edit_user_db_snapshot(
            timestamp=timestamp,
            location_data_snapshot=location_data_snapshot,
            balances_snapshot=balances_snapshot,
        )
        return make_response_from_dict(response_data)

    def export_user_db_snapshot(self, timestamp: Timestamp, path: Path) -> Response:
        response_data = self.user_data_service.export_user_db_snapshot(
            timestamp=timestamp,
            path=path,
        )
        return make_response_from_dict(response_data)

    def download_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        response = self.user_data_service.download_user_db_snapshot(timestamp)
        if isinstance(response, Response):
            return response
        return make_response_from_dict(response)

    def delete_user_db_snapshot(self, timestamp: Timestamp) -> Response:
        response_data = self.user_data_service.delete_user_db_snapshot(timestamp)
        return make_response_from_dict(response_data)

    @async_api_call()
    def get_ens_mappings(
            self,
            addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
    ) -> dict[str, Any]:
        return self.user_data_service.get_ens_mappings(
            addresses=addresses,
            ignore_cache=ignore_cache,
        )

    @async_api_call()
    def resolve_ens_name(
            self,
            name: str,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        return self.user_data_service.resolve_ens_name(
            name=name,
            ignore_cache=ignore_cache,
        )

    def import_user_snapshot(
            self,
            balances_snapshot_file: Path,
            location_data_snapshot_file: Path,
    ) -> Response:
        response_data = self.user_data_service.import_user_snapshot(
            balances_snapshot_file=balances_snapshot_file,
            location_data_snapshot_file=location_data_snapshot_file,
        )
        return make_response_from_dict(response_data)

    def get_addressbook_entries(
            self,
            book_type: AddressbookType,
            filter_query: AddressbookFilterQuery,
    ) -> Response:
        response_data = self.user_data_service.get_addressbook_entries(
            book_type=book_type,
            filter_query=filter_query,
        )
        return make_response_from_dict(response_data)

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
            update_existing: bool,
    ) -> Response:
        response_data = self.user_data_service.add_addressbook_entries(
            book_type=book_type,
            entries=entries,
            update_existing=update_existing,
        )
        return make_response_from_dict(response_data)

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        response_data = self.user_data_service.update_addressbook_entries(
            book_type=book_type,
            entries=entries,
        )
        return make_response_from_dict(response_data)

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            chain_addresses: list[OptionalChainAddress],
    ) -> Response:
        response_data = self.user_data_service.delete_addressbook_entries(
            book_type=book_type,
            chain_addresses=chain_addresses,
        )
        return make_response_from_dict(response_data)

    def search_for_names_everywhere(
            self,
            chain_addresses: list[OptionalChainAddress],
    ) -> Response:
        response_data = self.user_data_service.search_for_names_everywhere(chain_addresses)
        return make_response_from_dict(response_data)

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
        response_data = self.user_data_service.get_user_notes(filter_query)
        return make_response_from_dict(response_data)

    def add_user_note(
            self,
            title: str,
            content: str,
            location: str,
            is_pinned: bool,
    ) -> Response:
        response_data = self.user_data_service.add_user_note(
            title=title,
            content=content,
            location=location,
            is_pinned=is_pinned,
        )
        return make_response_from_dict(response_data)

    def edit_user_note(self, user_note: UserNote) -> Response:
        response_data = self.user_data_service.edit_user_note(user_note)
        return make_response_from_dict(response_data)

    def delete_user_note(self, identifier: int) -> Response:
        response_data = self.user_data_service.delete_user_note(identifier)
        return make_response_from_dict(response_data)

    def get_custom_assets(self, filter_query: CustomAssetsFilterQuery) -> Response:
        response_data = self.assets_service.get_custom_assets(filter_query)
        return make_response_from_dict(response_data)

    def add_custom_asset(self, custom_asset: CustomAsset) -> Response:
        response_data = self.assets_service.add_custom_asset(custom_asset)
        return make_response_from_dict(response_data)

    def edit_custom_asset(self, custom_asset: CustomAsset) -> Response:
        response_data = self.assets_service.edit_custom_asset(custom_asset)
        return make_response_from_dict(response_data)

    def get_custom_asset_types(self) -> Response:
        response_data = self.assets_service.get_custom_asset_types()
        return make_response_from_dict(response_data)

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

    def get_history_event_group_position(
            self,
            group_identifier: str,
            filter_query: HistoryBaseEntryFilterQuery,
    ) -> Response:
        """Gets the 0-based group position of a history event group in the filtered sorted list."""
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        position = dbevents.get_history_event_group_position(
            group_identifier=group_identifier,
            filter_query=filter_query,
        )
        if position is None:
            return api_response(wrap_in_fail_result('No event found'), status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

        return api_response(_wrap_in_ok_result({'position': position}), status_code=HTTPStatus.OK)

    @async_api_call()
    def add_transaction_by_reference(
            self,
            blockchain: CHAINS_WITH_TRANSACTIONS_TYPE,
            tx_ref: EVMTxHash | Signature,
            associated_address: ChecksumEvmAddress | SolanaAddress,
    ) -> dict[str, Any]:
        return self.transactions_service.add_transaction_by_reference(
            blockchain=blockchain,
            tx_ref=tx_ref,
            associated_address=associated_address,
        )

    @async_api_call()
    def get_binance_savings_history(
            self,
            only_cache: bool,
            location: Literal[Location.BINANCE, Location.BINANCEUS],
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        """Returns a summary of Binance savings events that match the filter provided."""
        return self.history_service.get_binance_savings_history(
            only_cache=only_cache,
            location=location,
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
        return self.assets_service.get_ens_avatar(ens_name=ens_name, match_header=match_header)

    def clear_icons_cache(self, icons: list[AssetWithNameAndType] | None) -> Response:
        response_data = self.assets_service.clear_icons_cache(icons)
        return make_response_from_dict(response_data)

    def clear_avatars_cache(self, avatars: list[str] | None) -> Response:
        response_data = self.assets_service.clear_avatars_cache(avatars)
        return make_response_from_dict(response_data)

    def get_types_mappings(self) -> Response:
        response_data = self.assets_service.get_types_mappings()
        return make_response_from_dict(response_data)

    def get_counterparties_details(self) -> Response:
        response_data = self.assets_service.get_counterparties_details()
        return make_response_from_dict(response_data)

    @async_api_call()
    def refresh_protocol_data(self, cache_protocol: ProtocolsWithCache) -> dict[str, Any]:
        return self.assets_service.refresh_protocol_data(cache_protocol)

    def get_airdrops_metadata(self) -> Response:
        response_data = self.assets_service.get_airdrops_metadata()
        return make_response_from_dict(response_data)

    def get_defi_metadata(self) -> Response:
        response_data = self.assets_service.get_defi_metadata()
        return make_response_from_dict(response_data)

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
        return self.history_service.export_history_events(
            filter_query=filter_query,
            directory_path=directory_path,
            match_exact_events=match_exact_events,
        )

    def download_history_events_csv(self, file_path: str) -> Response:
        """Download history events data CSV file."""
        return self.history_service.download_history_events_csv(file_path)

    def add_accounting_rule(
            self,
            event_ids: list[int] | None,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> Response:
        response_data = self.accounting_service.add_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            links=links,
        )
        return make_response_from_dict(response_data)

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
        response_data = self.accounting_service.update_accounting_rule(
            event_ids=event_ids,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            links=links,
            identifier=identifier,
        )
        return make_response_from_dict(response_data)

    def delete_accounting_rule(self, rule_id: int) -> Response:
        response_data = self.accounting_service.delete_accounting_rule(rule_id)
        return make_response_from_dict(response_data)

    def query_accounting_rules(self, filter_query: AccountingRulesFilterQuery) -> Response:
        response_data = self.accounting_service.query_accounting_rules(filter_query)
        return make_response_from_dict(response_data)

    def linkable_accounting_properties(self) -> Response:
        response_data = self.accounting_service.linkable_accounting_properties()
        return make_response_from_dict(response_data)

    def solve_multiple_accounting_rule_conflicts(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
            solve_all_using: Literal['remote', 'local'] | None,
    ) -> Response:
        response_data = self.accounting_service.solve_multiple_accounting_rule_conflicts(
            conflicts=conflicts,
            solve_all_using=solve_all_using,
        )
        return make_response_from_dict(response_data)

    def list_accounting_rules_conflicts(self, filter_query: DBFilterQuery) -> Response:
        response_data = self.accounting_service.list_accounting_rules_conflicts(filter_query)
        return make_response_from_dict(response_data)

    def add_to_spam_assets_false_positive(self, token: EvmToken) -> Response:
        response_data = self.assets_service.add_to_spam_assets_false_positive(token)
        return make_response_from_dict(response_data)

    def remove_from_spam_assets_false_positives(self, token: EvmToken) -> Response:
        response_data = self.assets_service.remove_from_spam_assets_false_positives(token)
        return make_response_from_dict(response_data)

    def get_spam_assets_false_positives(self) -> Response:
        response_data = self.assets_service.get_spam_assets_false_positives()
        return make_response_from_dict(response_data)

    def add_tokens_to_spam(self, tokens: list[EvmToken]) -> Response:
        response_data = self.assets_service.add_tokens_to_spam(tokens)
        return make_response_from_dict(response_data)

    def remove_token_from_spam(self, token: EvmToken) -> Response:
        response_data = self.assets_service.remove_token_from_spam(token)
        return make_response_from_dict(response_data)

    def create_calendar_entry(self, calendar: CalendarEntry) -> Response:
        response_data = self.integrations_service.create_calendar_entry(calendar)
        return make_response_from_dict(response_data)

    def delete_calendar_entry(self, identifier: int) -> Response:
        response_data = self.integrations_service.delete_calendar_entry(identifier)
        return make_response_from_dict(response_data)

    def query_calendar(self, filter_query: CalendarFilterQuery) -> Response:
        response_data = self.integrations_service.query_calendar(filter_query)
        return make_response_from_dict(response_data)

    def update_calendar_entry(self, calendar: CalendarEntry) -> Response:
        response_data = self.integrations_service.update_calendar_entry(calendar)
        return make_response_from_dict(response_data)

    def create_calendar_reminder(self, reminders: list[ReminderEntry]) -> Response:
        response_data = self.integrations_service.create_calendar_reminder(reminders)
        return make_response_from_dict(response_data)

    def delete_reminder_entry(self, identifier: int) -> Response:
        response_data = self.integrations_service.delete_reminder_entry(identifier)
        return make_response_from_dict(response_data)

    def update_reminder_entry(self, reminder: ReminderEntry) -> Response:
        response_data = self.integrations_service.update_reminder_entry(reminder)
        return make_response_from_dict(response_data)

    def query_reminders(self, event_id: int) -> Response:
        response_data = self.integrations_service.query_reminders(event_id)
        return make_response_from_dict(response_data)

    def get_google_calendar_status(self) -> Response:
        response_data = self.integrations_service.get_google_calendar_status()
        return make_response_from_dict(response_data)

    def sync_google_calendar(self) -> Response:
        response_data = self.integrations_service.sync_google_calendar()
        return make_response_from_dict(response_data)

    def disconnect_google_calendar(self) -> Response:
        response_data = self.integrations_service.disconnect_google_calendar()
        return make_response_from_dict(response_data)

    def complete_google_calendar_oauth(self, access_token: str, refresh_token: str) -> Response:
        response_data = self.integrations_service.complete_google_calendar_oauth(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        return make_response_from_dict(response_data)

    def get_monerium_status(self) -> Response:
        response_data = self.integrations_service.get_monerium_status()
        return make_response_from_dict(response_data)

    def complete_monerium_oauth(self, access_token: str, refresh_token: str, expires_in: int) -> Response:  # noqa: E501
        response_data = self.integrations_service.complete_monerium_oauth(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
        return make_response_from_dict(response_data)

    def disconnect_monerium(self) -> Response:
        response_data = self.integrations_service.disconnect_monerium()
        return make_response_from_dict(response_data)

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
    def get_historical_balance(
            self,
            filter_query: HistoricalBalancesFilterQuery,
    ) -> dict[str, Any]:
        """Query historical balances for all assets at a given timestamp
        by processing historical events
        """
        processing_required, balances = HistoricalBalancesManager(
            self.rotkehlchen.data.db,
        ).get_balances(filter_query=filter_query)

        result: dict[str, Any] = {'processing_required': processing_required}
        if balances is not None:
            result['entries'] = {
                asset.identifier: str(amount)
                for asset, amount in balances.items()
            }

        return _wrap_in_ok_result(result=result, status_code=HTTPStatus.OK)

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
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.INTERNAL_SERVER_ERROR)  # noqa: E501
        except NotFoundError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.NOT_FOUND)

        result = {
            'times': list(balances),
            'values': [str(x) for x in balances.values()],
        }
        if last_group_identifier is not None:
            result['last_group_identifier'] = last_group_identifier

        return api_response(_wrap_in_ok_result(result=result))

    def get_historical_asset_amounts_event_metrics(
            self,
            asset: Asset | None,
            collection_id: int | None,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        """Get historical asset amounts via the event metrics table.
        TODO (balances): Replace get_historical_asset_amounts with this.
        """
        assets: tuple[Asset, ...]
        if asset is not None:
            assets = (asset,)
        else:  # collection_id is present due to validation.
            with GlobalDBHandler().conn.read_ctx() as cursor:
                cursor.execute(
                    'SELECT asset FROM multiasset_mappings WHERE collection_id=?',
                    (collection_id,),
                )
                assets = tuple(Asset(row[0]) for row in cursor)

        processing_required, amounts = HistoricalBalancesManager(self.rotkehlchen.data.db).get_assets_amounts_event_metrics(  # noqa: E501
            assets=assets,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )

        result: dict[str, Any] = {'processing_required': processing_required}
        if amounts is not None:
            result['times'] = list(amounts)
            result['values'] = [str(x) for x in amounts.values()]
        return api_response(_wrap_in_ok_result(result=result))

    @async_api_call()
    def trigger_task(self, task: TaskName) -> dict[str, Any]:
        """Trigger the specified async task."""
        if task == TaskName.HISTORICAL_BALANCE_PROCESSING:
            return wrap_in_fail_result('Historical balance processing is temporarily disabled.')
        else:  # task == TaskName.ASSET_MOVEMENT_MATCHING
            process_asset_movements(database=self.rotkehlchen.data.db)

        return OK_RESULT

    def set_scheduler_state(self, enabled: bool) -> Response:
        """Enable or disable the periodic task scheduler.

        This should be called by the frontend once initial data loading is complete
        (transaction decoding, balances fetch, asset movement matching, historical
        balance processing). This ensures background tasks that require exclusive
        database write access (like backup sync) don't run during DB upgrades,
        migrations, and asset updates.
        """
        self.rotkehlchen.task_manager.should_schedule = enabled  # type: ignore[union-attr]  # should exist here
        return api_response(_wrap_in_ok_result(result={'enabled': enabled}))

    def get_historical_netvalue(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        """Gets daily asset balances within a given time range.

        The processing_required flag indicates whether unprocessed events exist.
        Balance data is None when no processed data is available in the range.
        """
        processing_required, data = HistoricalBalancesManager(
            db=self.rotkehlchen.data.db,
        ).get_historical_netvalue(
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )

        result: dict[str, Any] = {'processing_required': processing_required}
        if data is not None:
            times, balances = data
            result['times'] = times
            result['values'] = [
                {asset_id: str(amount) for asset_id, amount in day_balances.items()}
                for day_balances in balances
            ]

        return api_response(_wrap_in_ok_result(result=result))

    @async_api_call()
    def get_onchain_historical_balance(
            self,
            evm_chain: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            address: ChecksumEvmAddress,
            asset: Asset,
            timestamp: Timestamp,
    ) -> dict[str, Any]:
        evm_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(chain_id=evm_chain)
        if not evm_manager.node_inquirer.has_archive_node():
            return wrap_in_fail_result(
                message=f'No archive node available for {evm_chain.to_name()} to query historical balance',  # noqa: E501
                status_code=HTTPStatus.CONFLICT,
            )

        try:
            block_number = evm_manager.node_inquirer.get_blocknumber_by_time(ts=timestamp)
        except RemoteError as e:
            return wrap_in_fail_result(
                message=f'Failed to get block number for timestamp {timestamp}: {e!s}',
                status_code=HTTPStatus.BAD_GATEWAY,
            )

        if asset == evm_manager.node_inquirer.native_token:
            balance = evm_manager.node_inquirer.get_historical_native_balance(
                address=address,
                block_number=block_number,
                queried_timestamp=timestamp,
            )
        else:
            balance = evm_manager.node_inquirer.get_historical_token_balance(
                token=asset.resolve_to_evm_token(),
                address=address,
                block_number=block_number,
                queried_timestamp=timestamp,
            )

        if balance is None:
            return wrap_in_fail_result(
                message=(
                    f'Failed to query historical balance for {asset.identifier} at block {block_number}. '  # noqa: E501
                    f'The token may not have been deployed at this block or may not be ERC20 compatible.'  # noqa: E501
                ),
                status_code=HTTPStatus.CONFLICT,
            )

        return _wrap_in_ok_result(result={asset.identifier: str(balance)})

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
        return self.transactions_service.force_refetch_transactions(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            chain=chain,
            address=address,
        )

    def addresses_interacted_before(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
    ) -> Response:
        response_data = self.transactions_service.addresses_interacted_before(
            from_address=from_address,
            to_address=to_address,
        )
        return make_response_from_dict(response_data)

    @async_api_call()
    def prepare_token_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            blockchain: 'SUPPORTED_EVM_CHAINS_TYPE',
            token: EvmToken,
            amount: FVal,
    ) -> dict[str, Any]:
        return self.transactions_service.prepare_token_transfer(
            from_address=from_address,
            to_address=to_address,
            blockchain=blockchain,
            token=token,
            amount=amount,
        )

    @async_api_call()
    def get_gnosis_pay_safe_admin_addresses(self) -> dict[str, Any]:
        return self.integrations_service.get_gnosis_pay_safe_admin_addresses()

    @async_api_call()
    def fetch_gnosis_pay_nonce(self) -> dict[str, Any]:
        return self.integrations_service.fetch_gnosis_pay_nonce()

    @async_api_call()
    def verify_gnosis_pay_siwe_signature(self, message: str, signature: str) -> dict[str, Any]:
        return self.integrations_service.verify_gnosis_pay_siwe_signature(
            message=message,
            signature=signature,
        )

    @async_api_call()
    def prepare_native_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            chain: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            amount: FVal,
    ) -> dict[str, Any]:
        return self.transactions_service.prepare_native_transfer(
            from_address=from_address,
            to_address=to_address,
            chain=chain,
            amount=amount,
        )

    @async_api_call()
    def fetch_token_balance_for_address(
            self,
            address: ChecksumEvmAddress,
            evm_chain: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            asset: 'CryptoAsset',
    ) -> dict[str, Any]:
        return self.transactions_service.fetch_token_balance_for_address(
            address=address,
            evm_chain=evm_chain,
            asset=asset,
        )

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
            matched_event_identifiers: list[int],
    ) -> Response:
        """Match an exchange asset movement to onchain event(s), or mark the movement as having
        no match if no matched_event_identifiers are specified.
        """
        if len(matched_event_identifiers) == 0:
            # No matched event specified. Mark as having no match so this movement will be ignored.
            with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR IGNORE INTO history_event_link_ignores(event_id, link_type) '
                    'VALUES(?, ?)',
                    (asset_movement_identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
                )
            return api_response(OK_RESULT)

        events_db = DBHistoryEvents(database=self.rotkehlchen.data.db)
        asset_movement, matched_events, fee_event = None, [], None
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            for event in events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    identifiers=[asset_movement_identifier, *matched_event_identifiers],
                ),
            ):
                if event.identifier == asset_movement_identifier:
                    asset_movement = event
                elif event.identifier in matched_event_identifiers:
                    matched_events.append(event)

            if (
                asset_movement is not None and
                len(matched_events) > 0 and
                len(fee_events := events_db.get_history_events_internal(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(
                        entry_types=IncludeExcludeFilterData(
                            values=[HistoryBaseEntryType.ASSET_MOVEMENT_EVENT],
                        ),
                        group_identifiers=[asset_movement.group_identifier],
                        event_subtypes=[HistoryEventSubType.FEE],
                    ),
                )) == 1
            ):
                fee_event = fee_events[0]  # Asset movements only support one fee

        if asset_movement is None or not isinstance(asset_movement, AssetMovement):
            error_msg = f'No asset movement event found in the DB for identifier {asset_movement_identifier}'  # noqa: E501
        elif len(matched_events) != len(matched_event_identifiers):
            error_msg = f'Some of the specified matched event identifiers {matched_event_identifiers} are missing from the DB.'  # noqa: E501
        else:  # Successfully found events for the provided ids. Update the matched events.
            # Don't allow adding any adjustment events when multi-matching since there are
            # expected to be differences between the movement amount and each individual matched
            # event's amount in that case.
            allow_adding_adjustments = len(matched_events) == 1
            for matched_event in matched_events:
                update_asset_movement_matched_event(
                    events_db=events_db,
                    asset_movement=asset_movement,
                    fee_event=fee_event,  # type: ignore[arg-type]  # Will be asset movement fee. Query is filtered by entry type above.
                    matched_event=matched_event,
                    is_deposit=asset_movement.event_subtype == HistoryEventSubType.RECEIVE,
                    allow_adding_adjustments=allow_adding_adjustments,
                )
            return api_response(OK_RESULT)

        return api_response(wrap_in_fail_result(message=error_msg), HTTPStatus.BAD_REQUEST)

    def get_unmatched_asset_movements(self, only_ignored: bool) -> Response:
        """Get the group identifiers of unmatched asset movements.
        Gets the movements that are marked as having no match if only_ignored is True otherwise
        gets all the movements that have not been matched or ignored yet.
        """
        if only_ignored:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                movement_group_ids = [x[0] for x in cursor.execute(
                    'SELECT DISTINCT history_events.group_identifier FROM history_events '
                    'JOIN history_event_link_ignores ON '
                    'history_events.identifier=history_event_link_ignores.event_id '
                    'WHERE history_event_link_ignores.link_type=? '
                    'ORDER BY timestamp, sequence_index',
                    (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
                )]
        else:
            asset_movements, _ = get_unmatched_asset_movements(database=self.rotkehlchen.data.db)
            # convert to id list using dict.fromkeys to remove duplicates but retain original order
            movement_group_ids = list(dict.fromkeys(event.group_identifier for event in asset_movements))  # noqa: E501

        return api_response(_wrap_in_ok_result(result=movement_group_ids))

    @async_api_call()
    def get_customized_event_duplicates(self) -> dict[str, Any]:
        """Get customized event duplicate candidates grouped by fixability."""
        auto_fix_group_ids, manual_review_group_ids, _ = find_customized_event_duplicate_groups(
            database=self.rotkehlchen.data.db,
        )
        return _wrap_in_ok_result(result={
            'auto_fix_group_ids': auto_fix_group_ids,
            'manual_review_group_ids': manual_review_group_ids,
        })

    @async_api_call()
    def fix_customized_event_duplicates(
            self,
            group_identifiers: list[str] | None,
    ) -> dict[str, Any]:
        """Remove exact duplicate non-customized events that only differ by sequence index.

        When group_identifiers is provided, only those groups are processed.
        """
        events_db = DBHistoryEvents(database=self.rotkehlchen.data.db)
        auto_fix_group_ids, manual_review_group_ids, duplicate_ids = find_customized_event_duplicate_groups(  # noqa: E501
            database=self.rotkehlchen.data.db,
            group_identifiers=group_identifiers,
        )
        if not duplicate_ids:
            return _wrap_in_ok_result(result={
                'removed_event_identifiers': [],
                'auto_fix_group_ids': auto_fix_group_ids,
                'manual_review_group_ids': manual_review_group_ids,
            })

        if (error := events_db.delete_history_events_by_identifier(
            identifiers=duplicate_ids,
            force_delete=False,
        )) is not None:
            return wrap_in_fail_result(message=error, status_code=HTTPStatus.CONFLICT)

        auto_fix_group_ids, manual_review_group_ids, _ = find_customized_event_duplicate_groups(
            database=self.rotkehlchen.data.db,
        )
        return _wrap_in_ok_result(result={
            'removed_event_identifiers': duplicate_ids,
            'auto_fix_group_ids': auto_fix_group_ids,
            'manual_review_group_ids': manual_review_group_ids,
        })

    def unlink_matched_asset_movements(
            self,
            identifier: int,
    ) -> Response:
        """Unlink an asset movement from its matched event. Also attempts to remove an entry for
        the matched event's identifier since it could be two asset movements matched to each other
        in which case there is an entry for both.

        For matches created by this app, events are restored from backups saved prior to matching,
        including event type/subtype, notes, and counterparty.
        """
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            linked_ids = defaultdict(list)
            for movement_id, matched_id in cursor.execute(
                'SELECT left_event_id, right_event_id FROM history_event_links '
                'WHERE link_type=? AND (left_event_id=? OR right_event_id=?)',
                (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(), identifier, identifier),  # noqa: E501
            ):
                linked_ids[movement_id].append(matched_id)

        if len(linked_ids) == 0:
            with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
                if write_cursor.execute(
                    'DELETE FROM history_event_link_ignores WHERE event_id=? AND link_type=?',
                    (identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),
                ).rowcount == 0:
                    return api_response(wrap_in_fail_result(message=(
                        f'The specified identifier {identifier} does not correspond to either the '
                        'asset movement or its match for any matched pairs in the DB.'
                    )), HTTPStatus.BAD_REQUEST)

                return api_response(OK_RESULT)

        with self.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
            for asset_movement_identifier, matched_event_identifiers in linked_ids.items():
                write_cursor.execute(
                    'DELETE FROM history_event_links WHERE left_event_id=? AND link_type=?',
                    (asset_movement_identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
                )
                write_cursor.executemany(
                    'DELETE FROM history_event_links WHERE left_event_id=? AND right_event_id=? '
                    'AND link_type=?',
                    [(
                        matched_event_identifier,
                        asset_movement_identifier,
                        HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                    ) for matched_event_identifier in matched_event_identifiers],
                )
                # Remove any adjustment event that was added during matching
                write_cursor.executemany(
                    'DELETE FROM history_events WHERE type=? AND group_identifier IN '
                    '(SELECT group_identifier FROM history_events WHERE identifier IN (?, ?))'
                    'AND identifier IN (SELECT parent_identifier FROM history_events_mappings '
                    'WHERE name=? AND value=?)',
                    [(
                        HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),
                        asset_movement_identifier,
                        matched_event_identifier,
                        HISTORY_MAPPING_KEY_STATE,
                        HistoryMappingState.AUTO_MATCHED.serialize_for_db(),
                    ) for matched_event_identifier in matched_event_identifiers],
                )
                # Restore events from the backup created before matching
                DBHistoryEvents.maybe_restore_history_events_from_backup(
                    write_cursor=write_cursor,
                    identifiers=[*matched_event_identifiers, asset_movement_identifier],
                )
                # Remove the auto-matched event state
                placeholders = ','.join(['?'] * (len(matched_event_identifiers) + 1))
                write_cursor.execute(
                    'DELETE FROM history_events_mappings '
                    f'WHERE parent_identifier IN({placeholders}) AND name=? AND value=?',
                    (
                        *matched_event_identifiers,
                        asset_movement_identifier,
                        HISTORY_MAPPING_KEY_STATE,
                        HistoryMappingState.AUTO_MATCHED.serialize_for_db(),
                    ),
                )

        return api_response(OK_RESULT)

    def get_matches_for_asset_movement(
            self,
            asset_movement_group_identifier: str,
            time_range: int,
            only_expected_assets: bool,
            tolerance: FVal,
    ) -> Response:
        """Get possible matches for an asset movement within the given time range, limiting to only
        events with assets in the same collection depending on the `only_expected_assets` flag."""
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

        asset_movement_timestamp = ts_ms_to_sec(asset_movement.timestamp)
        assets_in_collection = GlobalDBHandler.get_assets_in_same_collection(
            identifier=asset_movement.asset.identifier,
        )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            blockchain_accounts = self.rotkehlchen.data.db.get_blockchain_accounts(cursor=cursor)
            already_matched_event_ids = get_already_matched_event_ids(cursor=cursor)
            close_match_identifiers = [x.identifier for x in find_asset_movement_matches(
                events_db=events_db,
                asset_movement=asset_movement,  # type: ignore  # filtered by entry_types
                is_deposit=asset_movement.event_subtype == HistoryEventSubType.RECEIVE,
                fee_event=fee_event,  # type: ignore  # filtered by entry_types
                match_window=time_range,
                cursor=cursor,
                assets_in_collection=assets_in_collection,
                blockchain_accounts=blockchain_accounts,
                already_matched_event_ids=already_matched_event_ids,
                tolerance=tolerance,
            )]

            other_events = events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    order_by_rules=[(f'ABS(timestamp - {asset_movement.timestamp})', True)],
                    from_ts=Timestamp(asset_movement_timestamp - time_range),
                    to_ts=Timestamp(asset_movement_timestamp + time_range),
                    ignored_ids=close_match_identifiers + [asset_movement.identifier],  # type: ignore[arg-type]  # ids from db will not be none
                    assets=assets_in_collection if only_expected_assets else None,
                    entry_types=IncludeExcludeFilterData(
                        values=ENTRY_TYPES_TO_EXCLUDE_FROM_MATCHING,
                        operator='NOT IN',
                    ),
                ),
            )

        # Return the close_matches and filtered other_events.
        return api_response(_wrap_in_ok_result(result={
            'close_matches': close_match_identifiers,
            'other_events': [
                event.identifier for event in other_events
                if not should_exclude_possible_match(
                    asset_movement=asset_movement,  # type: ignore[arg-type]  # will be an asset movement - the query is filtered by entry type
                    event=event,
                    blockchain_accounts=blockchain_accounts,
                    already_matched_event_ids=already_matched_event_ids,
                    exclude_protocol_counterparty=False,
                )
            ],
        }))
