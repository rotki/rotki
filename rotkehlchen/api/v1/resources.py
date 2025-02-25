import json
import sys
from collections.abc import Callable, Sequence
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Any, Literal, Optional

from flask import Blueprint, Request, Response, request as flask_request
from flask.views import MethodView
from marshmallow import Schema, ValidationError
from marshmallow.utils import missing
from webargs.flaskparser import parser, use_kwargs
from webargs.multidictproxy import MultiDictProxy
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.api.rest import (
    RestAPI,
    api_response,
    make_response_from_dict,
    wrap_in_fail_result,
)
from rotkehlchen.api.v1.parser import ignore_kwarg_parser, resource_parser
from rotkehlchen.api.v1.schemas import (
    AccountingReportDataSchema,
    AccountingReportsSchema,
    AccountingRuleConflictsPagination,
    AccountingRulesQuerySchema,
    AddressbookAddressesSchema,
    AddressbookUpdateSchema,
    AllBalancesQuerySchema,
    AppInfoSchema,
    AssetIconUploadSchema,
    AssetResetRequestSchema,
    AssetsImportingFromFormSchema,
    AssetsImportingSchema,
    AssetsMappingSchema,
    AssetsPostSchema,
    AssetsReplaceSchema,
    AssetsSearchByColumnSchema,
    AssetsSearchLevenshteinSchema,
    AssetUpdatesRequestSchema,
    AsyncDirectoryPathSchema,
    AsyncFilePathSchema,
    AsyncIgnoreCacheQueryArgumentSchema,
    AsyncQueryArgumentSchema,
    AsyncTaskSchema,
    BaseXpubSchema,
    BinanceMarketsSchema,
    BinanceMarketsUserSchema,
    BinanceSavingsSchema,
    BlockchainAccountsDeleteSchema,
    BlockchainAccountsGetSchema,
    BlockchainAccountsPatchSchema,
    BlockchainAccountsPutSchema,
    BlockchainBalanceQuerySchema,
    BlockchainTransactionDeletionSchema,
    BlockchainTypeAccountsDeleteSchema,
    ChainTypeAccountSchema,
    ClearAvatarsCacheSchema,
    ClearCacheSchema,
    ClearIconsCacheSchema,
    ConnectToRPCNodes,
    CreateAccountingRuleSchema,
    CreateHistoryEventSchema,
    CurrentAssetsPriceSchema,
    CustomAssetsQuerySchema,
    DataImportSchema,
    DetectTokensSchema,
    EditAccountingRuleSchema,
    EditHistoryEventSchema,
    EditSettingsSchema,
    EnsAvatarsSchema,
    ERC20InfoSchema,
    Eth2DailyStatsSchema,
    Eth2StakePerformanceSchema,
    Eth2ValidatorDeleteSchema,
    Eth2ValidatorPatchSchema,
    Eth2ValidatorPutSchema,
    Eth2ValidatorsGetSchema,
    EventDetailsQuerySchema,
    EventsOnlineQuerySchema,
    EvmAccountsPutSchema,
    EvmlikePendingTransactionDecodingSchema,
    EvmlikeTransactionDecodingSchema,
    EvmlikeTransactionQuerySchema,
    EvmPendingTransactionDecodingSchema,
    EvmTransactionDecodingSchema,
    EvmTransactionHashAdditionSchema,
    EvmTransactionQuerySchema,
    ExchangeBalanceQuerySchema,
    ExchangeEventsQuerySchema,
    ExchangeRatesSchema,
    ExchangesDataResourceSchema,
    ExchangesResourceAddSchema,
    ExchangesResourceEditSchema,
    ExchangesResourceRemoveSchema,
    ExportHistoryDownloadSchema,
    ExportHistoryEventSchema,
    ExternalServicesResourceAddSchema,
    ExternalServicesResourceDeleteSchema,
    FileListSchema,
    HistoricalAssetsPriceSchema,
    HistoricalPerAssetBalanceSchema,
    HistoricalPricesPerAssetSchema,
    HistoryEventSchema,
    HistoryEventsDeletionSchema,
    HistoryExportingSchema,
    HistoryProcessingExportSchema,
    HistoryProcessingSchema,
    IgnoredActionsModifySchema,
    IgnoredAssetsSchema,
    IntegerIdentifierSchema,
    LocationAssetMappingsDeleteSchema,
    LocationAssetMappingsPostSchema,
    LocationAssetMappingsUpdateSchema,
    ManualBalanceQuerySchema,
    ManuallyTrackedBalancesAddSchema,
    ManuallyTrackedBalancesDeleteSchema,
    ManuallyTrackedBalancesEditSchema,
    ManualPriceDeleteSchema,
    ManualPriceRegisteredSchema,
    ManualPriceSchema,
    ModuleBalanceProcessingSchema,
    ModuleBalanceWithVersionProcessingSchema,
    ModuleHistoryProcessingSchema,
    MultipleAccountingRuleConflictsResolutionSchema,
    NameDeleteSchema,
    NamedEthereumModuleDataSchema,
    NamedOracleCacheCreateSchema,
    NamedOracleCacheGetSchema,
    NamedOracleCacheSchema,
    NewCalendarEntrySchema,
    NewCalendarReminderListSchema,
    NewUserSchema,
    NFTFilterQuerySchema,
    NFTLpFilterSchema,
    OptionalAddressesWithBlockchainsListSchema,
    QueriedAddressesSchema,
    QueryAddressbookSchema,
    QueryCalendarSchema,
    RefreshProtocolDataSchema,
    ReverseEnsSchema,
    RpcAddNodeSchema,
    RpcNodeEditSchema,
    RpcNodeListDeleteSchema,
    RpcNodeSchema,
    SingleAssetIdentifierSchema,
    SingleAssetWithOraclesIdentifierSchema,
    SingleFileSchema,
    SingleTokenSchema,
    SkippedExternalEventsExportSchema,
    SnapshotEditingSchema,
    SnapshotImportingSchema,
    SnapshotQuerySchema,
    SnapshotTimestampQuerySchema,
    SpamTokenListSchema,
    StakingQuerySchema,
    StatisticsAssetBalanceSchema,
    StatisticsNetValueSchema,
    StatisticsValueDistributionSchema,
    StringIdentifierSchema,
    TagSchema,
    TimedManualPriceSchema,
    TimestampRangeSchema,
    TradeDeleteSchema,
    TradePatchSchema,
    TradeSchema,
    TradesQuerySchema,
    UpdateCalendarReminderSchema,
    UpdateCalendarSchema,
    UserActionLoginSchema,
    UserActionSchema,
    UserNotesGetSchema,
    UserNotesPatchSchema,
    UserNotesPutSchema,
    UserPasswordChangeSchema,
    UserPremiumSyncSchema,
    WatchersAddSchema,
    WatchersDeleteSchema,
    WatchersEditSchema,
    XpubAddSchema,
    XpubPatchSchema,
)
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.modules.eth2.structures import PerformanceStatusFilter
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, ReminderEntry
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.filtering import (
    AccountingRulesFilterQuery,
    AddressbookFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    DBFilterQuery,
    Eth2DailyStatsFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryBaseEntryFilterQuery,
    LevenshteinFilterQuery,
    LocationAssetMappingsFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.serialization.schemas import (
    AssetSchema,
    BaseCustomAssetSchema,
    CustomAssetWithIdentifierSchema,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    AssetAmount,
    ChainType,
    ChecksumEvmAddress,
    Eth2PubKey,
    EvmlikeChain,
    EVMTxHash,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
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
    SupportedBlockchain,
    Timestamp,
    TradeType,
    UserNote,
)

from .types import ModuleWithBalances, ModuleWithStats

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.hdkey import HDKey
    from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
    from rotkehlchen.db.filtering import HistoryEventFilterQuery
    from rotkehlchen.exchanges.kraken import KrakenAccountType
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


def _combine_parser_data(
        data_1: MultiDictProxy,
        data_2: MultiDictProxy,
        schema: Schema,
) -> MultiDictProxy:
    if data_2 is not missing:
        if data_1 == {}:
            data_1 = MultiDictProxy(data_2, schema)
        else:
            all_data = data_1.to_dict() if isinstance(data_1, MultiDictProxy) else data_1
            for key, value in data_2.items():
                all_data[key] = value
            data_1 = MultiDictProxy(all_data, schema)
    return data_1


@parser.location_loader('json_and_view_args')
def load_json_viewargs_data(request: Request, schema: Schema) -> dict[str, Any]:
    """Load data from a request accepting either json or view_args encoded data"""
    view_args = parser.load_view_args(request, schema)
    data = parser.load_json(request, schema)
    if data is missing:
        data = {}

    return _combine_parser_data(data, view_args, schema)  # type: ignore  # MultiDictproxy is dict


@parser.location_loader('json_and_query')
def load_json_query_data(request: Request, schema: Schema) -> dict[str, Any]:
    """Load data from a request accepting either json or query encoded data"""
    data = parser.load_json(request, schema)
    if data is not missing:
        return data
    return parser.load_querystring(request, schema)


@parser.location_loader('json_and_query_and_view_args')
def load_json_query_viewargs_data(request: Request, schema: Schema) -> dict[str, Any]:
    """Load data from a request accepting either json or querystring or view_args encoded data"""
    view_args = parser.load_view_args(request, schema)
    # Get data either from json or from querystring
    data = parser.load_json(request, schema)
    if data is missing:
        data = parser.load_querystring(request, schema)

    if data is missing:
        return data

    return _combine_parser_data(data, view_args, schema)  # type: ignore  # MultiDictproxy is dict


@parser.location_loader('form_and_file')
def load_form_file_data(request: Request, schema: Schema) -> MultiDictProxy:
    """Load data from a request accepting form and file encoded data"""
    form_data = parser.load_form(request, schema)
    file_data = parser.load_files(request, schema)
    return _combine_parser_data(form_data, file_data, schema)


@parser.location_loader('view_args_and_file')
def load_view_args_file_data(request: Request, schema: Schema) -> MultiDictProxy:
    """Load data from a request accepting view_args and file encoded data"""
    view_args_data = parser.load_view_args(request, schema)
    file_data = parser.load_files(request, schema)
    return _combine_parser_data(view_args_data, file_data, schema)


def allow_async_validation() -> Callable:
    """
    Decorator to be used when validation should happen as an async task.

    This decorator should be used after resource_parser.use_args using the argument
    allow_async_validation=True. The validation and any possible error will be handled inside
    the spawned task and if validation succeeds then the endpoint logic will be executed in the
    same gevent task.
    """
    def _do_async_validation(
            rotki: RestAPI,  # pylint: disable=unused-argument
            view: BaseMethodView,
            method: Callable,
            schema: Schema,
            raw_data: dict[str, Any],
            *args: Any,
            **kwargs: Any,
    ) -> dict[str, Any]:
        """Do the validation and return error if it fails, otherwise execute the endpoint logic"""
        try:
            data = schema.load(raw_data)
            kwargs.update(data)
        except ValidationError as e:
            return {
                'result': None,
                'message': json.dumps(e.normalized_messages()),  # type: ignore[no-untyped-call]  # marshmallow doesn't have types for this function
                'status_code': HTTPStatus.BAD_REQUEST,
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.INTERNAL_SERVER_ERROR,
            }
        kwargs.pop('async_query')  # async query has already been handled so it can be removed
        return method(view, *args, **kwargs)

    def _allow_async_validation(f: Callable) -> Callable:
        """Determine if the validation logic needs to be executed in a sync or async way"""
        @wraps(f)
        def wrapper(view: BaseMethodView, *args: Any, **kwargs: Any) -> Any:
            if (async_validation := kwargs.pop('do_async_validation', None)) is None:
                kwargs.pop('async_query', None)  # we already know that it won't be async
                output = f(view, *args, **kwargs)
                return make_response_from_dict(output)

            schema = async_validation['schema']
            raw_data = async_validation['data']
            return view.rest_api._query_async(
                command=_do_async_validation,
                view=view,
                method=f,
                schema=schema,
                raw_data=raw_data,
                **kwargs,
            )

        return wrapper
    return _allow_async_validation


def require_loggedin_user() -> Callable:
    """ This is a decorator for the RestAPI class's methods requiring a logged in user.
    """
    def _require_loggedin_user(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # grab the `rest_api` attribute from the view class.
            view_class = args[0]
            rest_api = view_class.rest_api
            if rest_api.rotkehlchen.user_is_logged_in is False:
                result_dict = wrap_in_fail_result('No user is currently logged in')
                return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)
            return f(*args, **kwargs)

        return wrapper
    return _require_loggedin_user


def require_premium_user(active_check: bool) -> Callable:
    """
    Decorator only for premium

    This is a decorator for the RestAPI class's methods requiring a logged in
    user to have premium subscription.

    If active_check is true there is also an API call to the rotkehlchen server
    to check that the saved key is also valid.
    """
    def _require_premium_user(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # grab the `rest_api` attribute from the view class.
            view_class = args[0]
            rest_api = view_class.rest_api
            if rest_api.rotkehlchen.user_is_logged_in is False:
                result_dict = wrap_in_fail_result('No user is currently logged in')
                return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

            msg = (
                f'Currently logged in user {rest_api.rotkehlchen.data.username} '
                f'does not have a premium subscription'
            )
            if rest_api.rotkehlchen.premium is None:
                result_dict = wrap_in_fail_result(msg)
                return api_response(result_dict, status_code=HTTPStatus.FORBIDDEN)

            if active_check and rest_api.rotkehlchen.premium.is_active() is False:
                result_dict = wrap_in_fail_result(msg)
                return api_response(result_dict, status_code=HTTPStatus.FORBIDDEN)

            return f(*args, **kwargs)

        return wrapper
    return _require_premium_user


def create_blueprint(url_prefix: str) -> Blueprint:
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint('v1_resources', __name__, url_prefix=url_prefix)


def get_match_header() -> str | None:
    """
    Process the if-match and if-none-match headers to get final header so that comparison with
    etag can be done.
    """
    match_header = flask_request.headers.get('If-Match', None)
    if not match_header:
        match_header = flask_request.headers.get('If-None-Match', None)
    if match_header:
        match_header = match_header[1:-1]  # remove enclosing quotes

    return match_header


class BaseMethodView(MethodView):
    def __init__(self, rest_api_object: RestAPI, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.rest_api = rest_api_object


class SettingsResource(BaseMethodView):

    put_schema = EditSettingsSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            settings: ModifiableDBSettings,
    ) -> Response:
        return self.rest_api.set_settings(settings=settings)

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_settings()


class AsyncTasksResource(BaseMethodView):

    get_schema = AsyncTaskSchema(is_required=False)
    delete_schema = AsyncTaskSchema(is_required=True)

    @use_kwargs(get_schema, location='view_args')
    def get(self, task_id: int | None) -> Response:
        return self.rest_api.query_tasks_outcome(task_id=task_id)

    @use_kwargs(delete_schema, location='view_args')
    def delete(self, task_id: int) -> Response:
        return self.rest_api.delete_async_task(task_id=task_id)


class ExchangeRatesResource(BaseMethodView):

    get_schema = ExchangeRatesSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, currencies: list[AssetWithOracles | None], async_query: bool) -> Response:
        valid_currencies = [currency for currency in currencies if currency is not None]
        return self.rest_api.get_exchange_rates(given_currencies=valid_currencies, async_query=async_query)  # noqa: E501


class ExchangesResource(BaseMethodView):

    put_schema = ExchangesResourceAddSchema()
    patch_schema = ExchangesResourceEditSchema()
    delete_schema = ExchangesResourceRemoveSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_exchanges()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: list[str] | None,
    ) -> Response:
        return self.rest_api.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            binance_markets=binance_markets,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(
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
        return self.rest_api.edit_exchange(
            name=name,
            location=location,
            new_name=new_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            binance_markets=binance_markets,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, name: str, location: Location) -> Response:
        return self.rest_api.remove_exchange(name=name, location=location)


class ExchangesDataResource(BaseMethodView):

    delete_schema = ExchangesDataResourceSchema()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='view_args')
    def delete(self, location: Location | None) -> Response:
        return self.rest_api.purge_exchange_data(location=location)


class AssociatedLocations(BaseMethodView):
    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_associated_locations()


class BlockchainTransactionsResource(BaseMethodView):
    delete_schema = BlockchainTransactionDeletionSchema()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(
            self,
            chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE | None,
            tx_hash: EVMTxHash | None,
    ) -> Response:
        return self.rest_api.delete_blockchain_transaction_data(chain=chain, tx_hash=tx_hash)


class EvmTransactionsResource(BaseMethodView):
    post_schema = EvmTransactionQuerySchema()
    put_schema = EvmTransactionDecodingSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            filter_query: EvmTransactionsFilterQuery,
    ) -> Response:
        return self.rest_api.refresh_evm_transactions(
            async_query=async_query,
            filter_query=filter_query,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_query')
    def put(
            self,
            async_query: bool,
            transactions: list[dict[str, Any]],
            delete_custom: bool,
    ) -> Response:
        return self.rest_api.decode_given_evm_transactions(
            async_query=async_query,
            transactions=[(x['evm_chain'], x['tx_hash']) for x in transactions],
            delete_custom=delete_custom,
        )


class EvmlikeTransactionsResource(BaseMethodView):
    post_schema = EvmlikeTransactionQuerySchema()
    put_schema = EvmlikeTransactionDecodingSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            accounts: list[ChecksumEvmAddress] | None,
            chain: EvmlikeChain | None,
    ) -> Response:
        return self.rest_api.refresh_evmlike_transactions(
            async_query=async_query,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            accounts=accounts,
            chain=chain,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_query')
    def put(
            self,
            async_query: bool,
            transactions: list[dict[str, Any]],
    ) -> Response:
        return self.rest_api.decode_evmlike_transactions(
            async_query=async_query,
            transactions=[(x['chain'], x['tx_hash']) for x in transactions],
        )


class EvmPendingTransactionsDecodingResource(BaseMethodView):
    post_schema = EvmPendingTransactionDecodingSchema()
    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            ignore_cache: bool,
            chains: list[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
    ) -> Response:
        return self.rest_api.decode_evm_transactions(
            async_query=async_query,
            evm_chains=chains,
            force_redecode=ignore_cache,
        )

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_count_transactions_not_decoded(async_query=async_query)


class EvmlikePendingTransactionsDecodingResource(BaseMethodView):
    post_schema = EvmlikePendingTransactionDecodingSchema()
    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            ignore_cache: bool,
            chains: list[EvmlikeChain],
    ) -> Response:
        return self.rest_api.decode_pending_evmlike_transactions(
            async_query=async_query,
            ignore_cache=ignore_cache,
            evmlike_chains=chains,
        )

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_count_evmlike_transactions_not_decoded(async_query=async_query)


class EthereumAirdropsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_ethereum_airdrops(async_query=async_query)


class RpcNodesResource(BaseMethodView):

    get_schema = RpcNodeSchema()
    put_schema = RpcAddNodeSchema()
    post_schema = ConnectToRPCNodes()

    def make_patch_schema(self) -> RpcNodeEditSchema:
        return RpcNodeEditSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    def make_delete_schema(self) -> RpcNodeListDeleteSchema:
        return RpcNodeListDeleteSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, blockchain: SupportedBlockchain) -> Response:
        return self.rest_api.get_rpc_nodes(blockchain=blockchain)

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_query_and_view_args')
    def put(
            self,
            blockchain: SupportedBlockchain,
            name: str,
            endpoint: str,
            owned: bool,
            weight: FVal,
            active: bool,
    ) -> Response:
        node = WeightedNode(
            node_info=NodeName(
                name=name,
                endpoint=endpoint,
                owned=owned,
                blockchain=blockchain,  # type: ignore
            ),
            weight=weight,
            active=active,
        )
        return self.rest_api.add_rpc_node(node=node)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_patch_schema, location='json_and_query_and_view_args')
    def patch(
            self,
            blockchain: SupportedBlockchain,
            identifier: int,
            name: str,
            endpoint: str,
            owned: bool,
            weight: FVal,
            active: bool,
    ) -> Response:
        node = WeightedNode(
            identifier=identifier,
            node_info=NodeName(
                name=name,
                endpoint=endpoint,
                owned=owned,
                blockchain=blockchain,  # type: ignore
            ),
            weight=weight,
            active=active,
        )
        return self.rest_api.update_and_connect_rpc_node(node=node)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_delete_schema, location='json_and_query_and_view_args')
    def delete(
            self,
            blockchain: SupportedBlockchain,
            identifier: int,
    ) -> Response:
        return self.rest_api.delete_rpc_node(identifier=identifier, blockchain=blockchain)

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query_and_view_args')
    def post(self, identifier: int | None, blockchain: SupportedBlockchain) -> Response:
        return self.rest_api.connect_rpc_node(identifier=identifier, blockchain=blockchain)


class ExternalServicesResource(BaseMethodView):

    put_schema = ExternalServicesResourceAddSchema()
    delete_schema = ExternalServicesResourceDeleteSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_external_services()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            services: list[ExternalServiceApiCredentials],
    ) -> Response:
        return self.rest_api.add_external_services(services=services)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, services: list[ExternalService]) -> Response:
        return self.rest_api.delete_external_services(services=services)


class AllBalancesResource(BaseMethodView):

    get_schema = AllBalancesQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            save_data: bool,
            ignore_errors: bool,
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        return self.rest_api.query_all_balances(
            save_data=save_data,
            ignore_errors=ignore_errors,
            async_query=async_query,
            ignore_cache=ignore_cache,
        )


class ExchangeBalancesResource(BaseMethodView):

    get_schema = ExchangeBalanceQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            location: Location | None,
            async_query: bool,
            ignore_cache: bool,
            usd_value_threshold: FVal | None,
    ) -> Response:
        return self.rest_api.query_exchange_balances(
            location=location,
            async_query=async_query,
            ignore_cache=ignore_cache,
            usd_value_threshold=usd_value_threshold,
        )


class OwnedAssetsResource(BaseMethodView):

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.query_owned_assets()


class DatabaseInfoResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_database_info()


class DatabaseBackupsResource(BaseMethodView):

    delete_schema = FileListSchema()
    get_schema = SingleFileSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, file: Path) -> Response:
        return self.rest_api.download_database_backup(filepath=file)

    @require_loggedin_user()
    def put(self) -> Response:
        return self.rest_api.create_database_backup()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, files: list[Path]) -> Response:
        return self.rest_api.delete_database_backups(files=files)


class AllAssetsResource(BaseMethodView):
    """
    Supports querying of all assets and modification of fiat assets / crypto assets / evm tokens.
    """

    delete_schema = StringIdentifierSchema()

    def make_post_schema(self) -> AssetsPostSchema:
        return AssetsPostSchema(
            db=self.rest_api.rotkehlchen.data.db,
        )

    def make_add_schema(self) -> AssetSchema:
        return AssetSchema(
            identifier_required=False,
            disallowed_asset_types=[AssetType.CUSTOM_ASSET],  # custom assets are handled on a separate endpoint  # noqa: E501
            coingecko=self.rest_api.rotkehlchen.coingecko,
            cryptocompare=self.rest_api.rotkehlchen.cryptocompare,
        )

    def make_edit_schema(self) -> AssetSchema:
        return AssetSchema(
            identifier_required=True,
            disallowed_asset_types=[AssetType.CUSTOM_ASSET],  # custom assets are handled on a separate endpoint  # noqa: E501
            coingecko=self.rest_api.rotkehlchen.coingecko,
            cryptocompare=self.rest_api.rotkehlchen.cryptocompare,
        )

    @resource_parser.use_kwargs(make_post_schema, location='json')
    def post(self, filter_query: AssetsFilterQuery) -> Response:
        return self.rest_api.query_list_of_all_assets(filter_query=filter_query)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_add_schema, location='json')
    def put(self, asset: AssetWithOracles) -> Response:  # is asset with oracles since we disallow custom assets  # noqa: E501
        return self.rest_api.add_user_asset(asset)

    @resource_parser.use_kwargs(make_edit_schema, location='json')
    def patch(self, asset: AssetWithOracles) -> Response:  # is asset with oracles since we disallow custom assets  # noqa: E501
        return self.rest_api.edit_user_asset(asset)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifier: str) -> Response:
        return self.rest_api.delete_asset(identifier=identifier)


class AssetsMappingResource(BaseMethodView):
    post_schema = AssetsMappingSchema()

    @require_loggedin_user()  # since it uses the user DB too
    @use_kwargs(post_schema, location='json')
    def post(self, identifiers: list[str]) -> Response:
        return self.rest_api.get_assets_mappings(identifiers=identifiers)


class AssetsSearchResource(BaseMethodView):

    def make_post_schema(self) -> AssetsSearchByColumnSchema:
        return AssetsSearchByColumnSchema(db=self.rest_api.rotkehlchen.data.db)

    @resource_parser.use_kwargs(make_post_schema, location='json')
    def post(self, filter_query: AssetsFilterQuery) -> Response:
        return self.rest_api.search_assets(filter_query=filter_query)


class AssetsSearchLevenshteinResource(BaseMethodView):
    def make_post_schema(self) -> AssetsSearchLevenshteinSchema:
        return AssetsSearchLevenshteinSchema(db=self.rest_api.rotkehlchen.data.db)

    @resource_parser.use_kwargs(make_post_schema, location='json')
    def post(
            self,
            filter_query: LevenshteinFilterQuery,
            limit: int | None,
            search_nfts: bool,
    ) -> Response:
        return self.rest_api.search_assets_levenshtein(
            filter_query=filter_query,
            limit=limit,
            search_nfts=search_nfts,
        )


class AssetsTypesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_asset_types()


class AssetsReplaceResource(BaseMethodView):

    put_schema = AssetsReplaceSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, source_identifier: str, target_asset: Asset) -> Response:
        return self.rest_api.replace_asset(
            source_identifier=source_identifier,
            target_asset=target_asset,
        )


class AssetUpdatesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()
    post_schema = AssetUpdatesRequestSchema()
    delete_schema = AssetResetRequestSchema()

    @use_kwargs(get_schema, location='json_and_query')
    @require_loggedin_user()
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_assets_updates(async_query=async_query)

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            async_query: bool,
            up_to_version: int | None,
            conflicts: dict[Asset, Literal['remote', 'local']] | None,
    ) -> Response:
        return self.rest_api.perform_assets_updates(
            async_query=async_query,
            up_to_version=up_to_version,
            conflicts=conflicts,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(
            self,
            async_query: bool,
            reset: Literal['soft', 'hard'],
            ignore_warnings: bool,
    ) -> Response:
        return self.rest_api.rebuild_assets_information(
            async_query=async_query,
            reset=reset,
            ignore_warnings=ignore_warnings,
        )


class SupportedChainsResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_supported_chains()


class BlockchainBalancesResource(BaseMethodView):

    get_schema = BlockchainBalanceQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            blockchain: SupportedBlockchain | None,
            async_query: bool,
            ignore_cache: bool,
            usd_value_threshold: FVal | None,
    ) -> Response:
        return self.rest_api.query_blockchain_balances(
            blockchain=blockchain,
            async_query=async_query,
            ignore_cache=ignore_cache,
            usd_value_threshold=usd_value_threshold,
        )


class ManuallyTrackedBalancesResource(BaseMethodView):

    get_schema = ManualBalanceQuerySchema()
    put_schema = ManuallyTrackedBalancesAddSchema()
    patch_schema = ManuallyTrackedBalancesEditSchema()
    delete_schema = ManuallyTrackedBalancesDeleteSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool, usd_value_threshold: FVal | None) -> Response:
        return self.rest_api.get_manually_tracked_balances(
            async_query=async_query,
            usd_value_threshold=usd_value_threshold,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, async_query: bool, balances: list[ManuallyTrackedBalance]) -> Response:
        return self.rest_api.add_manually_tracked_balances(async_query=async_query, data=balances)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, async_query: bool, balances: list[ManuallyTrackedBalance]) -> Response:
        return self.rest_api.edit_manually_tracked_balances(async_query=async_query, data=balances)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, async_query: bool, ids: list[int]) -> Response:
        return self.rest_api.remove_manually_tracked_balances(
            async_query=async_query,
            ids=ids,
        )


class TradesResource(BaseMethodView):

    def make_get_schema(self) -> TradesQuerySchema:
        return TradesQuerySchema(
            db=self.rest_api.rotkehlchen.data.db,
        )

    put_schema = TradeSchema()
    patch_schema = TradePatchSchema()
    delete_schema = TradeDeleteSchema()

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            only_cache: bool,
            filter_query: TradesFilterQuery,
            include_ignored_trades: bool,
    ) -> Response:
        return self.rest_api.get_trades(
            async_query=async_query,
            only_cache=only_cache,
            filter_query=filter_query,
            include_ignored_trades=include_ignored_trades,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
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
        return self.rest_api.add_trade(
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

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(
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
        return self.rest_api.edit_trade(
            trade_id=trade_id,
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

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, trades_ids: list[str]) -> Response:
        return self.rest_api.delete_trades(trades_ids=trades_ids)


class TagsResource(BaseMethodView):

    put_schema = TagSchema(color_required=True)
    patch_schema = TagSchema(color_required=False)
    delete_schema = NameDeleteSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_tags()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            name: str,
            description: str | None,
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> Response:
        return self.rest_api.add_tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(
            self,
            name: str,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
    ) -> Response:
        return self.rest_api.edit_tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, name: str) -> Response:
        return self.rest_api.delete_tag(name=name)


class EventsOnlineQueryResource(BaseMethodView):

    post_schema = EventsOnlineQuerySchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, async_query: bool, query_type: HistoryEventQueryType) -> Response:
        return self.rest_api.query_online_events(
            async_query=async_query,
            query_type=query_type,
        )


class ExchangeEventsQueryResource(BaseMethodView):

    post_schema = ExchangeEventsQuerySchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            location: Location,
            async_query: bool,
            name: str | None,
    ) -> Response:
        return self.rest_api.query_exchange_history_events(
            name=name,
            location=location,
            async_query=async_query,
        )


class HistorySkippedExternalEventResource(BaseMethodView):

    put_schema = SkippedExternalEventsExportSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_skipped_external_events_summary()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, directory_path: Path) -> Response:
        return self.rest_api.export_skipped_external_events(directory_path=directory_path)

    @require_loggedin_user()
    def patch(self) -> Response:
        return self.rest_api.export_skipped_external_events(directory_path=None)

    @require_loggedin_user()
    def post(self) -> Response:
        return self.rest_api.reprocess_skipped_external_events()


class HistoryEventResource(BaseMethodView):

    post_schema = HistoryEventSchema()
    delete_schema = HistoryEventsDeletionSchema()

    def make_put_schema(self) -> CreateHistoryEventSchema:
        return CreateHistoryEventSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    def make_patch_schema(self) -> EditHistoryEventSchema:
        return EditHistoryEventSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, filter_query: 'HistoryBaseEntryFilterQuery', group_by_event_ids: bool) -> Response:  # noqa: E501
        return self.rest_api.get_history_events(filter_query=filter_query, group_by_event_ids=group_by_event_ids)  # noqa: E501

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_put_schema, location='json')
    def put(self, events: list['HistoryBaseEntry']) -> Response:
        return self.rest_api.add_history_events(events)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_patch_schema, location='json')
    def patch(self, events: list['HistoryBaseEntry']) -> Response:
        return self.rest_api.edit_history_events(events)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifiers: list[int], force_delete: bool) -> Response:
        return self.rest_api.delete_history_events(
            identifiers=identifiers,
            force_delete=force_delete,
        )


class UsersResource(BaseMethodView):

    put_schema = NewUserSchema()

    def get(self) -> Response:
        return self.rest_api.get_users()

    @use_kwargs(put_schema, location='json')
    def put(
            self,
            async_query: bool,
            name: str,
            password: str,
            premium_api_key: str,
            premium_api_secret: str,
            sync_database: bool,
            initial_settings: ModifiableDBSettings | None,
    ) -> Response:
        return self.rest_api.create_new_user(
            async_query=async_query,
            name=name,
            password=password,
            premium_api_key=premium_api_key,
            premium_api_secret=premium_api_secret,
            sync_database=sync_database,
            initial_settings=initial_settings,
        )


class UsersByNameResource(BaseMethodView):
    patch_schema = UserActionSchema()
    post_schema = UserActionLoginSchema()

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_view_args')
    def patch(
            self,
            name: str,
            action: str | None,
            premium_api_key: str,
            premium_api_secret: str,
    ) -> Response:
        if action == 'logout':
            return self.rest_api.user_logout(name=name)

        return self.rest_api.user_set_premium_credentials(
            name=name,
            api_key=premium_api_key,
            api_secret=premium_api_secret,
        )

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            async_query: bool,
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
            resume_from_backup: bool,
    ) -> Response:
        return self.rest_api.user_login(
            async_query=async_query,
            name=name,
            password=password,
            sync_approval=sync_approval,
            resume_from_backup=resume_from_backup,
        )


class UserPasswordChangeResource(BaseMethodView):
    patch_schema = UserPasswordChangeSchema

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(
            self,
            name: str,
            current_password: str,
            new_password: str,
    ) -> Response:
        return self.rest_api.user_change_password(
            name=name,
            current_password=current_password,
            new_password=new_password,
        )


class UserPremiumKeyResource(BaseMethodView):

    @require_premium_user(active_check=False)
    def delete(self) -> Response:
        return self.rest_api.user_premium_key_remove()


class UserPremiumSyncResource(BaseMethodView):
    put_schema = UserPremiumSyncSchema()

    @use_kwargs(put_schema, location='json_and_view_args')
    def put(self, async_query: bool, action: Literal['upload', 'download']) -> Response:
        return self.rest_api.sync_data(
            async_query=async_query,
            action=action,
        )


class StatisticsNetvalueResource(BaseMethodView):

    get_schema = StatisticsNetValueSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, include_nfts: bool) -> Response:
        return self.rest_api.query_netvalue_data(include_nfts=include_nfts)


class StatisticsAssetBalanceResource(BaseMethodView):

    post_schema = StatisticsAssetBalanceSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            asset: Asset | None,
            collection_id: int | None,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.query_timed_balances_data(
            asset=asset,  # note that from marshmallow asset and collection_id are guaranteed to exist and be mutually exclusive  # noqa: E501
            collection_id=collection_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class StatisticsValueDistributionResource(BaseMethodView):

    get_schema = StatisticsValueDistributionSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, distribution_by: str) -> Response:
        return self.rest_api.query_value_distribution_data(
            distribution_by=distribution_by,
        )


class StatisticsRendererResource(BaseMethodView):

    @require_premium_user(active_check=False)
    def get(self) -> Response:
        return self.rest_api.query_premium_components()


class MessagesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_messages()


class HistoryStatusResource(BaseMethodView):

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_history_status()


class HistoryProcessingResource(BaseMethodView):

    get_schema = HistoryProcessingSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        return self.rest_api.process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            async_query=async_query,
        )


class HistoryProcessingDebugResource(BaseMethodView):
    post_schema = HistoryProcessingExportSchema()
    upload_schema = AsyncFilePathSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Path | None,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_history_debug(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            directory_path=directory_path,
            async_query=async_query,
        )

    if getattr(sys, 'frozen', False) is False:
        @require_loggedin_user()
        @use_kwargs(upload_schema, location='json')
        def put(self, async_query: bool, filepath: Path) -> Response:
            return self.rest_api.import_history_debug(
                async_query=async_query,
                filepath=filepath,
            )

        @require_loggedin_user()
        @use_kwargs(upload_schema, location='form_and_file')
        def patch(self, async_query: bool, filepath: Path) -> Response:
            return self.rest_api.import_history_debug(
                async_query=async_query,
                filepath=filepath,
            )


class AccountingRulesImportResource(BaseMethodView):
    upload_schema = AsyncFilePathSchema()

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='json')
    def put(self, async_query: bool, filepath: Path) -> Response:
        return self.rest_api.import_accounting_rules(
            async_query=async_query,
            filepath=filepath,
        )

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='form_and_file')
    def patch(self, async_query: bool, filepath: Path) -> Response:
        return self.rest_api.import_accounting_rules(
            async_query=async_query,
            filepath=filepath,
        )


class AccountingRulesExportResource(BaseMethodView):
    post_schema = AsyncDirectoryPathSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, async_query: bool, directory_path: Path | None) -> Response:
        return self.rest_api.export_accounting_rules(
            async_query=async_query,
            directory_path=directory_path,
        )


class HistoryActionableItemsResource(BaseMethodView):
    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_history_actionable_items()


class AccountingReportsResource(BaseMethodView):

    get_schema = AccountingReportsSchema(required_report_id=False)
    delete_schema = AccountingReportsSchema(required_report_id=True)

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, report_id: int | None) -> Response:
        return self.rest_api.get_pnl_reports(report_id=report_id)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='view_args')
    def delete(self, report_id: int) -> Response:
        return self.rest_api.purge_pnl_report_data(report_id=report_id)


class AccountingReportDataResource(BaseMethodView):

    post_schema = AccountingReportDataSchema()

    @require_loggedin_user()
    @ignore_kwarg_parser.use_kwargs(post_schema, location='json_and_query_and_view_args')
    def post(self, filter_query: ReportDataFilterQuery) -> Response:
        return self.rest_api.get_report_data(filter_query=filter_query)


class HistoryExportingResource(BaseMethodView):

    get_schema = HistoryExportingSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, directory_path: Path) -> Response:
        return self.rest_api.export_processed_history_csv(directory_path=directory_path)


class HistoryDownloadingResource(BaseMethodView):

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.download_processed_history_csv()


class PeriodicDataResource(BaseMethodView):

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.query_periodic_data()


class EvmAccountsResource(BaseMethodView):

    post_schema = AsyncQueryArgumentSchema()

    def make_put_schema(self) -> EvmAccountsPutSchema:
        return EvmAccountsPutSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        )

    @require_loggedin_user()
    @resource_parser.use_args(
        make_put_schema,
        location='json_and_query',
        allow_async_validation=True,
        as_kwargs=True,
    )
    @allow_async_validation()
    def put(self, accounts: list[dict[str, Any]]) -> dict[str, Any]:
        account_data = [
            SingleBlockchainAccountData[ChecksumEvmAddress](
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.add_evm_accounts(account_data=account_data)

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, async_query: bool) -> Response:
        return self.rest_api.refresh_evm_accounts(async_query=async_query)


class BlockchainsAccountsResource(BaseMethodView):

    get_schema = BlockchainAccountsGetSchema()

    def make_put_schema(self) -> BlockchainAccountsPutSchema:
        return BlockchainAccountsPutSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        )

    def make_patch_schema(self) -> BlockchainAccountsPatchSchema:
        return BlockchainAccountsPatchSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        )

    def make_delete_schema(self) -> BlockchainAccountsDeleteSchema:
        return BlockchainAccountsDeleteSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        )

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, blockchain: SupportedBlockchain) -> Response:
        return self.rest_api.get_blockchain_accounts(blockchain=blockchain)

    @require_loggedin_user()
    @resource_parser.use_args(make_put_schema, location='json_and_view_args', allow_async_validation=True, as_kwargs=True)  # noqa: E501
    @allow_async_validation()
    def put(
            self,
            blockchain: SupportedBlockchain,
            accounts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        account_data = [
            SingleBlockchainAccountData(
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.add_single_blockchain_accounts(
            chain=blockchain,
            account_data=account_data,
        )

    @require_loggedin_user()
    @resource_parser.use_args(make_patch_schema, location='json_and_view_args', allow_async_validation=True, as_kwargs=True)  # noqa: E501
    @allow_async_validation()
    def patch(
            self,
            accounts: list[dict[str, Any]],
            blockchain: SupportedBlockchain,
    ) -> dict[str, Any]:
        account_data = [
            SingleBlockchainAccountData(
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.edit_single_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
        )

    @require_loggedin_user()
    @resource_parser.use_args(make_delete_schema, location='json_and_view_args', allow_async_validation=True, as_kwargs=True)  # noqa: E501
    @allow_async_validation()
    def delete(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> dict[str, Any]:
        return self.rest_api.remove_single_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
        )


class ChainTypeAccountResource(BaseMethodView):

    @require_loggedin_user()
    @use_kwargs(ChainTypeAccountSchema(), location='json_and_view_args')
    def patch(
            self,
            chain_type: ChainType,  # pylint: disable=unused-argument
            accounts: list[dict[str, Any]],
            async_query: bool,
    ) -> Response:
        account_data = [
            SingleBlockchainAccountData(
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.edit_chain_type_accounts_labels(
            async_query=async_query,
            accounts=account_data,
        )

    @require_loggedin_user()
    @use_kwargs(BlockchainTypeAccountsDeleteSchema(), location='json_and_view_args')
    def delete(
            self,
            chain_type: ChainType,
            accounts: ListOfBlockchainAddresses,
            async_query: bool,
    ) -> Response:
        return self.rest_api.remove_chain_type_accounts(
            async_query=async_query,
            chain_type=chain_type,
            accounts=accounts,
        )


class BTCXpubResource(BaseMethodView):

    put_schema = XpubAddSchema()
    delete_schema = BaseXpubSchema()
    patch_schema = XpubPatchSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_view_args')
    def put(
            self,
            xpub: 'HDKey',
            derivation_path: str | None,
            label: str | None,
            tags: list[str] | None,
            async_query: bool,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> Response:
        return self.rest_api.add_xpub(
            xpub_data=XpubData(
                xpub=xpub,
                blockchain=blockchain,
                derivation_path=derivation_path,
                label=label,
                tags=tags,
            ),
            async_query=async_query,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_view_args')
    def delete(
            self,
            xpub: 'HDKey',
            derivation_path: str | None,
            async_query: bool,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> Response:
        return self.rest_api.delete_xpub(
            xpub_data=XpubData(
                xpub=xpub,
                blockchain=blockchain,
                derivation_path=derivation_path,
                label=None,
                tags=None,
            ),
            async_query=async_query,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_view_args')
    def patch(
            self,
            xpub: 'HDKey',
            derivation_path: str | None,
            label: str | None,
            tags: list[str] | None,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> Response:
        return self.rest_api.edit_xpub(
            xpub_data=XpubData(
                xpub=xpub,
                blockchain=blockchain,
                derivation_path=derivation_path,
                label=label,
                tags=tags,
            ),
        )


class IgnoredAssetsResource(BaseMethodView):

    modify_schema = IgnoredAssetsSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_ignored_assets()

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def put(self, assets: list[Asset]) -> Response:
        return self.rest_api.add_ignored_assets(assets_to_ignore=assets)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def delete(self, assets: list[Asset]) -> Response:
        return self.rest_api.remove_ignored_assets(assets=assets)


class IgnoredActionsResource(BaseMethodView):

    modify_schema = IgnoredActionsModifySchema()

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def put(self, action_type: ActionType, data: list[str]) -> Response:
        return self.rest_api.add_ignored_action_ids(action_type=action_type, action_ids=data)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def delete(self, action_type: ActionType, data: list[str]) -> Response:
        return self.rest_api.remove_ignored_action_ids(
            action_type=action_type,
            action_ids=data,
        )


class QueriedAddressesResource(BaseMethodView):

    modify_schema = QueriedAddressesSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_queried_addresses_per_module()

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def put(self, module: ModuleName, address: ChecksumEvmAddress) -> Response:
        return self.rest_api.add_queried_address_per_module(module=module, address=address)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def delete(self, module: ModuleName, address: ChecksumEvmAddress) -> Response:
        return self.rest_api.remove_queried_address_per_module(module=module, address=address)


class InfoResource(BaseMethodView):

    get_schema = AppInfoSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, check_for_updates: bool) -> Response:
        return self.rest_api.get_info(check_for_updates=check_for_updates)


class PingResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.ping()


class DataImportResource(BaseMethodView):

    upload_schema = DataImportSchema()

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='json')
    def put(
            self,
            async_query: bool,
            source: DataImportSource,
            file: Path,
            **kwargs: Any,
    ) -> Response:
        return self.rest_api.import_data(
            source=source,
            filepath=file,
            async_query=async_query,
            **kwargs,
        )

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='form_and_file')
    def post(
            self,
            async_query: bool,
            source: DataImportSource,
            file: FileStorage,
            **kwargs: Any,
    ) -> Response:
        return self.rest_api.import_data(
            source=source,
            filepath=file,
            async_query=async_query,
            **kwargs,
        )


class Eth2DailyStatsResource(BaseMethodView):

    def make_post_schema(self) -> Eth2DailyStatsSchema:
        return Eth2DailyStatsSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    @require_premium_user(active_check=False)
    @resource_parser.use_kwargs(make_post_schema, location='json_and_query')
    def post(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        return self.rest_api.get_eth2_daily_stats(
            filter_query=filter_query,
            async_query=async_query,
            only_cache=only_cache,
        )


class Eth2ValidatorsResource(BaseMethodView):

    patch_schema = Eth2ValidatorPatchSchema()
    put_schema = Eth2ValidatorPutSchema()
    delete_schema = Eth2ValidatorDeleteSchema()

    def make_get_schema(self) -> Eth2ValidatorsGetSchema:
        return Eth2ValidatorsGetSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            ignore_cache: bool,
            validator_indices: set[int] | None,
    ) -> Response:
        return self.rest_api.get_eth2_validators(
            async_query=async_query,
            ignore_cache=ignore_cache,
            validator_indices=validator_indices,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            validator_index: int | None,
            public_key: Eth2PubKey | None,
            ownership_percentage: FVal,
            async_query: bool,
    ) -> Response:
        return self.rest_api.add_eth2_validator(
            validator_index=validator_index,
            public_key=public_key,
            ownership_proportion=ownership_percentage,
            async_query=async_query,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, validators: list[int]) -> Response:
        return self.rest_api.delete_eth2_validator(validators=validators)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, validator_index: int, ownership_percentage: FVal) -> Response:
        return self.rest_api.edit_eth2_validator(
            validator_index=validator_index,
            ownership_proportion=ownership_percentage,
        )


class Eth2StakePerformanceResource(BaseMethodView):

    def make_put_schema(self) -> Eth2StakePerformanceSchema:
        return Eth2StakePerformanceSchema(
            dbhandler=self.rest_api.rotkehlchen.data.db,
        )

    @require_premium_user(active_check=False)
    @resource_parser.use_kwargs(make_put_schema, location='json_and_query')
    def put(
            self,
            async_query: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            limit: int,
            offset: int,
            ignore_cache: bool,
            addresses: list[ChecksumEvmAddress] | None,
            validator_indices: list[int] | None,
            status: PerformanceStatusFilter,
    ) -> Response:
        return self.rest_api.get_eth2_staking_performance(
            async_query=async_query,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            limit=limit,
            offset=offset,
            ignore_cache=ignore_cache,
            addresses=addresses,
            validator_indices=validator_indices,
            status=status,
        )


class NamedEthereumModuleDataResource(BaseMethodView):
    delete_schema = NamedEthereumModuleDataSchema()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='view_args')
    def delete(self, module_name: ModuleName) -> Response:
        return self.rest_api.purge_module_data(module_name=module_name)


class EthereumModuleDataResource(BaseMethodView):

    def delete(self) -> Response:
        return self.rest_api.purge_module_data(module_name=None)


class EthereumModuleResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.supported_modules()


class LoopringBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_loopring_balances(async_query=async_query)


class LiquityTrovesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_liquity_troves(async_query=async_query)


class LiquityStakingResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_liquity_staked(async_query=async_query)


class EvmModuleBalancesResource(BaseMethodView):

    get_schema = ModuleBalanceProcessingSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            module: ModuleWithBalances,
            async_query: bool,
    ) -> Response:
        if module in (
            ModuleWithBalances.SUSHISWAP,
            ModuleWithBalances.BALANCER,
        ):
            return self.rest_api.get_amm_platform_balances(
                async_query=async_query,
                module=module.serialize(),
            )

        # this shouldn't happen since we have validation in marshmallow
        return api_response(wrap_in_fail_result(
            message='unknown module provided for balances',
            status_code=HTTPStatus.BAD_REQUEST,
        ))


class EvmModuleBalancesWithVersionResource(BaseMethodView):

    get_schema = ModuleBalanceWithVersionProcessingSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            module: ModuleWithBalances,
            version: int,
            async_query: bool,
    ) -> Response:
        if module != ModuleWithBalances.UNISWAP:
            return api_response(wrap_in_fail_result(
                message='unknown module provided for balances',
                status_code=HTTPStatus.BAD_REQUEST,
            ))

        if version == 2:
            return self.rest_api.get_amm_platform_balances(
                async_query=async_query,
                module=module.serialize(),
            )

        # this shouldn't happen since we have validation in marshmallow
        return api_response(wrap_in_fail_result(
            message='unknown module provided for balances',
            status_code=HTTPStatus.BAD_REQUEST,
        ))


class ModuleStatsResource(BaseMethodView):

    get_schema = ModuleHistoryProcessingSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            module: ModuleWithStats,
            async_query: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        if module == ModuleWithStats.LIQUITY:
            return self.rest_api.get_liquity_stats(async_query=async_query)

        # this shouldn't happen since we have validation in marshmallow
        return api_response(wrap_in_fail_result(
            message='unknown module provided for balances',
            status_code=HTTPStatus.BAD_REQUEST,
        ))


class LiquityStabilityPoolResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_liquity_stability_pool_positions(async_query=async_query)


class PickleDillResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_dill_balance(async_query=async_query)


class WatchersResource(BaseMethodView):

    put_schema = WatchersAddSchema
    patch_schema = WatchersEditSchema
    delete_schema = WatchersDeleteSchema

    @require_premium_user(active_check=False)
    def get(self) -> Response:
        return self.rest_api.get_watchers()

    @require_premium_user(active_check=False)
    @use_kwargs(put_schema, location='json')
    def put(self, watchers: list[dict[str, Any]]) -> Response:
        return self.rest_api.add_watchers(watchers=watchers)

    @require_premium_user(active_check=False)
    @use_kwargs(patch_schema, location='json')
    def patch(self, watchers: list[dict[str, Any]]) -> Response:
        return self.rest_api.edit_watchers(watchers=watchers)

    @require_premium_user(active_check=False)
    @use_kwargs(delete_schema, location='json')
    def delete(self, watchers: list[str]) -> Response:
        return self.rest_api.delete_watchers(watchers=watchers)


class AssetIconsResource(BaseMethodView):

    patch_schema = SingleAssetWithOraclesIdentifierSchema()
    upload_schema = AssetIconUploadSchema()

    @use_kwargs(upload_schema, location='json')
    def put(self, asset: Asset, file: Path) -> Response:
        return self.rest_api.upload_asset_icon(asset=asset, filepath=file)

    @use_kwargs(upload_schema, location='form_and_file')
    def post(self, asset: Asset, file: FileStorage) -> Response:
        """
        This endpoint uses form_and_file instead of accepting json because is not possible
        to send multiform data and a json body in the same request.
        """
        with TemporaryDirectory() as temp_directory:
            filename = file.filename or f'{asset.identifier}.png'
            filepath = Path(temp_directory) / filename
            file.save(str(filepath))
            return self.rest_api.upload_asset_icon(asset=asset, filepath=filepath)

    @use_kwargs(patch_schema, location='json')
    def patch(self, asset: AssetWithOracles) -> Response:
        return self.rest_api.refresh_asset_icon(asset=asset)


class LocationAssetMappingsResource(BaseMethodView):
    post_schema = LocationAssetMappingsPostSchema()
    put_and_patch_schema = LocationAssetMappingsUpdateSchema()
    delete_schema = LocationAssetMappingsDeleteSchema()

    @use_kwargs(post_schema, location='json')
    def post(self, filter_query: LocationAssetMappingsFilterQuery) -> Response:
        return self.rest_api.query_location_asset_mappings(filter_query=filter_query)

    @use_kwargs(put_and_patch_schema, location='json')
    def put(
            self,
            entries: list[LocationAssetMappingUpdateEntry],
    ) -> Response:
        return self.rest_api.add_location_asset_mappings(entries=entries)

    @use_kwargs(put_and_patch_schema, location='json')
    def patch(
            self,
            entries: list[LocationAssetMappingUpdateEntry],
    ) -> Response:
        return self.rest_api.update_location_asset_mappings(entries=entries)

    @use_kwargs(delete_schema, location='json')
    def delete(
            self,
            entries: list[LocationAssetMappingDeleteEntry],
    ) -> Response:
        return self.rest_api.delete_location_asset_mappings(entries=entries)


class AllLatestAssetsPriceResource(BaseMethodView):

    post_schema = ManualPriceRegisteredSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, from_asset: Asset | None, to_asset: Asset | None) -> Response:
        return self.rest_api.get_manual_latest_prices(from_asset=from_asset, to_asset=to_asset)


class LatestAssetsPriceResource(BaseMethodView):

    put_schema = ManualPriceSchema()
    post_schema = CurrentAssetsPriceSchema()
    delete_schema = SingleAssetIdentifierSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> Response:
        return self.rest_api.add_manual_latest_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
        )

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            assets: list[AssetWithNameAndType],
            target_asset: Asset,
            ignore_cache: bool,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_current_assets_price(
            assets=assets,
            target_asset=target_asset,
            ignore_cache=ignore_cache,
            async_query=async_query,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, asset: Asset) -> Response:
        return self.rest_api.delete_manual_latest_price(asset=asset)


class HistoricalAssetsPriceResource(BaseMethodView):

    post_schema = HistoricalAssetsPriceSchema()
    put_schema = TimedManualPriceSchema()
    patch_schema = TimedManualPriceSchema()
    get_schema = ManualPriceRegisteredSchema()
    delete_schema = ManualPriceDeleteSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            async_query: bool,
            only_cache_period: int | None = None,
    ) -> Response:
        return self.rest_api.get_historical_assets_price(
            only_cache_period=only_cache_period,
            assets_timestamp=assets_timestamp,
            target_asset=target_asset,
            async_query=async_query,
        )

    @use_kwargs(put_schema, location='json')
    def put(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.add_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
            timestamp=timestamp,
        )

    @use_kwargs(patch_schema, location='json')
    def patch(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
            timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.edit_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            price=price,
            timestamp=timestamp,
        )

    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(self, from_asset: Asset | None, to_asset: Asset | None) -> Response:
        return self.rest_api.get_manual_prices(from_asset=from_asset, to_asset=to_asset)

    @use_kwargs(delete_schema)
    def delete(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.delete_manual_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )


class NamedOracleCacheResource(BaseMethodView):

    post_schema = NamedOracleCacheCreateSchema()
    delete_schema = NamedOracleCacheSchema()
    get_schema = NamedOracleCacheGetSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(self, oracle: HistoricalPriceOracle, async_query: bool) -> Response:
        return self.rest_api.get_oracle_cache(oracle=oracle, async_query=async_query)

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            purge_old: bool,
            async_query: bool,
    ) -> Response:
        return self.rest_api.create_oracle_cache(
            oracle=oracle,
            from_asset=from_asset,
            to_asset=to_asset,
            purge_old=purge_old,
            async_query=async_query,
        )

    @use_kwargs(delete_schema, location='json_and_view_args')
    def delete(
            self,
            oracle: HistoricalPriceOracle,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Response:
        return self.rest_api.delete_oracle_cache(
            oracle=oracle,
            from_asset=from_asset,
            to_asset=to_asset,
        )


class OraclesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_supported_oracles()


class ERC20TokenInfo(BaseMethodView):

    get_schema = ERC20InfoSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            address: ChecksumEvmAddress,
            evm_chain: SUPPORTED_CHAIN_IDS,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_token_info(async_query=async_query, address=address, chain_id=evm_chain)  # noqa: E501


class BinanceAvailableMarkets(BaseMethodView):

    get_schema = BinanceMarketsSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, location: Location) -> Response:
        return self.rest_api.get_all_binance_pairs(location=location)


class BinanceUserMarkets(BaseMethodView):

    get_schema = BinanceMarketsUserSchema()

    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(self, name: str, location: Location) -> Response:
        return self.rest_api.get_user_binance_pairs(name=name, location=location)


class BinanceSavingsResource(BaseMethodView):

    post_schema = BinanceSavingsSchema()

    @use_kwargs(post_schema, location='json_and_query_and_view_args')
    def post(
            self,
            async_query: bool,
            only_cache: bool,
            location: Literal[Location.BINANCE, Location.BINANCEUS],
            query_filter: 'HistoryEventFilterQuery',
            value_filter: 'HistoryEventFilterQuery',
    ) -> Response:
        return self.rest_api.get_binance_savings_history(
            async_query=async_query,
            location=location,
            only_cache=only_cache,
            query_filter=query_filter,
            value_filter=value_filter,
        )


class NFTSResource(BaseMethodView):
    get_schema = AsyncIgnoreCacheQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.get_nfts(async_query=async_query, ignore_cache=ignore_cache)


class NFTSBalanceResource(BaseMethodView):
    def make_get_schema(self) -> NFTFilterQuerySchema:
        return NFTFilterQuerySchema(chains_aggregator=self.rest_api.rotkehlchen.chains_aggregator)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def get(self, async_query: bool, ignore_cache: bool, filter_query: NFTFilterQuery) -> Response:
        return self.rest_api.get_nfts_balances(
            async_query=async_query,
            ignore_cache=ignore_cache,
            filter_query=filter_query,
        )


class NFTSPricesResource(BaseMethodView):
    post_schema = NFTLpFilterSchema

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, lps_handling: NftLpHandling) -> Response:
        return self.rest_api.get_nfts_with_price(lps_handling=lps_handling)


class StakingResource(BaseMethodView):

    def make_get_schema(self) -> StakingQuerySchema:
        with self.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rest_api.rotkehlchen.data.db.get_settings(cursor)
        return StakingQuerySchema(
            treat_eth2_as_eth=settings.treat_eth2_as_eth,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            only_cache: bool,
            query_filter: 'HistoryEventFilterQuery',
            value_filter: 'HistoryEventFilterQuery',
    ) -> Response:
        return self.rest_api.query_kraken_staking_events(
            async_query=async_query,
            only_cache=only_cache,
            query_filter=query_filter,
            value_filter=value_filter,
        )


class UserAssetsResource(BaseMethodView):
    importing_schema = AssetsImportingSchema
    import_from_form = AssetsImportingFromFormSchema

    @require_loggedin_user()
    @use_kwargs(importing_schema, location='json')
    def put(
            self,
            async_query: bool,
            file: Path | None,
            destination: Path | None,
            action: str,
    ) -> Response:
        if action == 'upload':
            if file is None:
                return api_response(wrap_in_fail_result(
                    message='file is required for upload action.',
                    status_code=HTTPStatus.BAD_REQUEST,
                ))
            return self.rest_api.import_user_assets(async_query=async_query, path=file)
        return self.rest_api.get_user_added_assets(path=destination)

    @require_loggedin_user()
    @use_kwargs(import_from_form, location='form_and_file')
    def post(self, async_query: bool, file: FileStorage) -> Response:
        with NamedTemporaryFile(
            delete=False,  # don't delete it on close
            suffix=file.filename or 'assets.zip',
        ) as temp_file:
            file.save(temp_file.name)
            return self.rest_api.import_user_assets(
                async_query=async_query,
                path=Path(temp_file.name),
            )


class DBSnapshotsResource(BaseMethodView):
    get_schema = SnapshotQuerySchema()
    upload_schema = SnapshotImportingSchema()
    patch_schema = SnapshotEditingSchema()
    delete_schema = SnapshotTimestampQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            action: Literal['export', 'download'] | None,
            timestamp: Timestamp,
            path: Path | None,
    ) -> Response:
        """The behaviour of this method is as a result of the exhaustion of HTTP verbs
        for this resource.

        - GET with `?action=download` is for downloading a snapshot(Docker).
        - GET with `?action=export&path=/home/xyz` is for exporting a snapshot(Electron).
        - GET without action query parameter is for returning the snapshot as JSON
        for editing the snapshot.
        """
        if action == 'export':
            # path cannot be `None` here because it is caught during schema validation.
            return self.rest_api.export_user_db_snapshot(
                timestamp=timestamp,
                path=path,  # type: ignore
            )
        if action == 'download':
            return self.rest_api.download_user_db_snapshot(timestamp=timestamp)

        return self.rest_api.get_user_db_snapshot(timestamp=timestamp)

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='json')
    def put(self, balances_snapshot_file: Path, location_data_snapshot_file: Path) -> Response:
        return self.rest_api.import_user_snapshot(
            balances_snapshot_file=balances_snapshot_file,
            location_data_snapshot_file=location_data_snapshot_file,
        )

    @require_loggedin_user()
    @use_kwargs(upload_schema, location='form_and_file')
    def post(
            self,
            balances_snapshot_file: FileStorage,
            location_data_snapshot_file: FileStorage,
    ) -> Response:
        with TemporaryDirectory() as temp_directory:
            balance_snapshot_filename = balances_snapshot_file.filename or 'balances_snapshot_import.csv'  # noqa: E501
            location_data_snapshot_filename = location_data_snapshot_file.filename or 'location_data_snapshot.csv'  # noqa: E501
            balance_snapshot_filepath = Path(temp_directory) / balance_snapshot_filename
            location_data_snapshot_filepath = Path(temp_directory) / location_data_snapshot_filename  # noqa: E501
            balances_snapshot_file.save(balance_snapshot_filepath)
            location_data_snapshot_file.save(location_data_snapshot_filepath)
            return self.rest_api.import_user_snapshot(
                balances_snapshot_file=balance_snapshot_filepath,
                location_data_snapshot_file=location_data_snapshot_filepath,
            )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_view_args')
    def patch(
            self,
            timestamp: Timestamp,
            balances_snapshot: list[DBAssetBalance],
            location_data_snapshot: list[LocationData],
    ) -> Response:
        return self.rest_api.edit_user_db_snapshot(
            timestamp=timestamp,
            balances_snapshot=balances_snapshot,
            location_data_snapshot=location_data_snapshot,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, timestamp: Timestamp) -> Response:
        return self.rest_api.delete_user_db_snapshot(timestamp=timestamp)


class ReverseEnsResource(BaseMethodView):
    post_schema = ReverseEnsSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            ethereum_addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_ens_mappings(
            addresses=ethereum_addresses,
            ignore_cache=ignore_cache,
            async_query=async_query,
        )


class AddressbookResource(BaseMethodView):
    delete_schema = AddressbookAddressesSchema()
    post_schema = QueryAddressbookSchema()
    update_schema = AddressbookUpdateSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            filter_query: AddressbookFilterQuery,
            book_type: AddressbookType,
    ) -> Response:
        return self.rest_api.get_addressbook_entries(
            book_type=book_type,
            filter_query=filter_query,
        )

    @require_loggedin_user()
    @use_kwargs(update_schema, location='json_and_view_args')
    def put(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        return self.rest_api.add_addressbook_entries(book_type=book_type, entries=entries)

    @require_loggedin_user()
    @use_kwargs(update_schema, location='json_and_view_args')
    def patch(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> Response:
        return self.rest_api.update_addressbook_entries(book_type=book_type, entries=entries)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_view_args')
    def delete(
            self,
            book_type: AddressbookType,
            addresses: list[OptionalChainAddress],
    ) -> Response:
        return self.rest_api.delete_addressbook_entries(
            book_type=book_type,
            chain_addresses=addresses,
        )


class AllNamesResource(BaseMethodView):
    post_schema = OptionalAddressesWithBlockchainsListSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            addresses: list[OptionalChainAddress],
    ) -> Response:
        return self.rest_api.search_for_names_everywhere(chain_addresses=addresses)


class DetectTokensResource(BaseMethodView):
    post_schema = DetectTokensSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            async_query: bool,
            only_cache: bool,
            addresses: Sequence[ChecksumEvmAddress] | None,
    ) -> Response:
        return self.rest_api.detect_evm_tokens(
            async_query=async_query,
            only_cache=only_cache,
            addresses=addresses,
            blockchain=blockchain,
        )


class ConfigurationsResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_config_arguments()


class UserNotesResource(BaseMethodView):
    get_schema = UserNotesGetSchema()
    put_schema = UserNotesPutSchema()
    patch_schema = UserNotesPatchSchema()
    delete_schema = IntegerIdentifierSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json')
    def post(self, filter_query: UserNotesFilterQuery) -> Response:
        return self.rest_api.get_user_notes(filter_query=filter_query)

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, title: str, content: str, location: str, is_pinned: bool) -> Response:
        return self.rest_api.add_user_note(
            title=title,
            content=content,
            location=location,
            is_pinned=is_pinned,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, user_note: UserNote) -> Response:
        return self.rest_api.edit_user_note(user_note=user_note)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifier: int) -> Response:
        return self.rest_api.delete_user_note(identifier=identifier)


class CustomAssetsResource(BaseMethodView):
    post_schema = CustomAssetsQuerySchema()
    put_schema = BaseCustomAssetSchema()
    patch_schema = CustomAssetWithIdentifierSchema()
    delete_schema = StringIdentifierSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, filter_query: CustomAssetsFilterQuery) -> Response:
        return self.rest_api.get_custom_assets(filter_query=filter_query)

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, custom_asset: CustomAsset) -> Response:
        return self.rest_api.add_custom_asset(custom_asset=custom_asset)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, custom_asset: CustomAsset) -> Response:
        return self.rest_api.edit_custom_asset(custom_asset=custom_asset)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifier: str) -> Response:
        return self.rest_api.delete_asset(identifier=identifier)


class CustomAssetsTypesResource(BaseMethodView):
    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_custom_asset_types()


class EventDetailsResource(BaseMethodView):
    get_schema = EventDetailsQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, identifier: int) -> Response:
        return self.rest_api.get_event_details(identifier=identifier)


class EvmTransactionsHashResource(BaseMethodView):
    def make_put_schema(self) -> EvmTransactionHashAdditionSchema:
        return EvmTransactionHashAdditionSchema(
            db=self.rest_api.rotkehlchen.data.db,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_put_schema, location='json')
    def put(
            self,
            async_query: bool,
            evm_chain: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
            associated_address: ChecksumEvmAddress,
    ) -> Response:
        return self.rest_api.add_evm_transaction_by_hash(
            async_query=async_query,
            evm_chain=evm_chain,
            tx_hash=tx_hash,
            associated_address=associated_address,
        )


class AllEvmChainsResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_all_evm_chains()


class EnsAvatarsResource(BaseMethodView):
    get_schema = EnsAvatarsSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, ens_name: str) -> Response:
        return self.rest_api.get_ens_avatar(ens_name=ens_name, match_header=get_match_header())


class ClearCacheResource(BaseMethodView):
    post_schema = ClearCacheSchema()
    icons_schema = ClearIconsCacheSchema()
    avatars_schema = ClearAvatarsCacheSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='view_args')
    def post(self, cache_type: Literal['icons', 'avatars']) -> Response:
        req_body = flask_request.get_json(force=True, silent=True)
        req_body = {} if req_body is None else req_body
        if cache_type == 'icons':
            data = self.icons_schema.load(req_body)
            return self.rest_api.clear_icons_cache(data['entries'])

        # can only be avatars
        data = self.avatars_schema.load(req_body)
        return self.rest_api.clear_avatars_cache(data['entries'])


class TypesMappingsResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_types_mappings()


class EvmCounterpartiesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_evm_counterparties_details()


class EvmProductsResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_evm_products()


class LocationResource(BaseMethodView):

    def get(self) -> Response:
        result = process_result({'locations': LOCATION_DETAILS})
        return api_response(
            result={'result': result, 'message': ''},
            status_code=HTTPStatus.OK,
        )


class ProtocolDataRefreshResource(BaseMethodView):
    post_schema = RefreshProtocolDataSchema()

    @use_kwargs(post_schema, location='json_and_query')
    def post(self, async_query: bool, cache_protocol: ProtocolsWithCache) -> Response:
        return self.rest_api.refresh_protocol_data(
            async_query=async_query,
            cache_protocol=cache_protocol,
        )

    def get(self) -> Response:
        return api_response(
            result={
                'result': [protocol.serialize() for protocol in ProtocolsWithCache],
                'message': '',
            },
            status_code=HTTPStatus.OK,
        )


class AirdropsMetadataResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_airdrops_metadata()


class DefiMetadataResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_defi_metadata()


class ExportHistoryEventResource(BaseMethodView):

    post_schema = ExportHistoryEventSchema()
    put_schema = ExportHistoryEventSchema(exclude=('directory_path',))

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, async_query: bool, filter_query: 'HistoryBaseEntryFilterQuery', directory_path: Path) -> dict[str, Any]:  # noqa: E501
        return self.rest_api.export_history_events(filter_query=filter_query, directory_path=directory_path, async_query=async_query)  # noqa: E501

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_query')
    def put(self, async_query: bool, filter_query: 'HistoryBaseEntryFilterQuery') -> Response | dict[str, Any]:  # noqa: E501
        return self.rest_api.export_history_events(filter_query=filter_query, directory_path=None, async_query=async_query)  # noqa: E501


class ExportHistoryDownloadResource(BaseMethodView):

    get_schema = ExportHistoryDownloadSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, file_path: str) -> Response:
        return self.rest_api.download_history_events_csv(file_path=file_path)


class AccountingRulesResource(BaseMethodView):

    put_schema = CreateAccountingRuleSchema()
    delete_schema = IntegerIdentifierSchema()
    post_schema = AccountingRulesQuerySchema()
    patch_schema = EditAccountingRuleSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json_and_query')
    def put(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> Response:
        return self.rest_api.add_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            links=links,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_query')
    def patch(
            self,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            counterparty: str | None,
            rule: 'BaseEventSettings',
            links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
            identifier: int,
    ) -> Response:
        return self.rest_api.update_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            identifier=identifier,
            links=links,
        )

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, filter_query: 'AccountingRulesFilterQuery') -> Response:
        return self.rest_api.query_accounting_rules(filter_query)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(self, identifier: int) -> Response:
        return self.rest_api.delete_accounting_rule(rule_id=identifier)


class AccountingLinkablePropertiesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.linkable_accounting_properties()


class AccountingRulesConflictsResource(BaseMethodView):

    post_schema = AccountingRuleConflictsPagination()
    patch_schema = MultipleAccountingRuleConflictsResolutionSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, filter_query: DBFilterQuery) -> Response:
        return self.rest_api.list_accounting_rules_conflicts(
            filter_query=filter_query,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_query')
    def patch(
            self,
            conflicts: list[tuple[int, Literal['remote', 'local']]],
            solve_all_using: Literal['remote', 'local'] | None,
    ) -> Response:
        return self.rest_api.solve_multiple_accounting_rule_conflicts(
            conflicts=conflicts,
            solve_all_using=solve_all_using,
        )


class FalsePositiveSpamTokenResource(BaseMethodView):

    post_delete_schema = SingleTokenSchema()

    @require_loggedin_user()
    @use_kwargs(post_delete_schema, location='json_and_query')
    def post(self, token: EvmToken) -> Response:
        return self.rest_api.add_to_spam_assets_false_positive(token=token)

    @require_loggedin_user()
    @use_kwargs(post_delete_schema, location='json_and_query')
    def delete(self, token: EvmToken) -> Response:
        return self.rest_api.remove_from_spam_assets_false_positives(token=token)

    def get(self) -> Response:
        return self.rest_api.get_spam_assets_false_positives()


class SpamEvmTokenResource(BaseMethodView):

    delete_schema = SingleTokenSchema()
    post_schema = SpamTokenListSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(self, tokens: list[EvmToken]) -> Response:
        return self.rest_api.add_tokens_to_spam(tokens)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(self, token: EvmToken) -> Response:
        return self.rest_api.remove_token_from_spam(token=token)


class CalendarResource(BaseMethodView):

    def make_create_schema(self) -> NewCalendarEntrySchema:
        return NewCalendarEntrySchema(
            self.rest_api.rotkehlchen.chains_aggregator,
        )

    def make_update_schema(self) -> UpdateCalendarSchema:
        return UpdateCalendarSchema(
            self.rest_api.rotkehlchen.chains_aggregator,
        )

    def make_query_schema(self) -> QueryCalendarSchema:
        return QueryCalendarSchema(
            self.rest_api.rotkehlchen.chains_aggregator,
        )

    delete_schema = IntegerIdentifierSchema()

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_create_schema, location='json_and_query')
    def put(self, calendar: CalendarEntry) -> Response:
        return self.rest_api.create_calendar_entry(calendar=calendar)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(self, identifier: int) -> Response:
        return self.rest_api.delete_calendar_entry(identifier=identifier)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_update_schema, location='json_and_query')
    def patch(self, calendar: CalendarEntry) -> Response:
        return self.rest_api.update_calendar_entry(calendar)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_query_schema, location='json_and_query')
    def post(self, filter_query: CalendarFilterQuery) -> Response:
        return self.rest_api.query_calendar(filter_query=filter_query)


class CalendarRemindersResource(BaseMethodView):

    create_schema = NewCalendarReminderListSchema()
    update_schema = UpdateCalendarReminderSchema()
    delete_schema = IntegerIdentifierSchema()
    query_schema = IntegerIdentifierSchema()

    @require_loggedin_user()
    @use_kwargs(create_schema, location='json_and_query')
    def put(self, reminders: list[ReminderEntry]) -> Response:
        return self.rest_api.create_calendar_reminder(reminders=reminders)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(self, identifier: int) -> Response:
        return self.rest_api.delete_reminder_entry(identifier=identifier)

    @require_loggedin_user()
    @use_kwargs(update_schema, location='json_and_query')
    def patch(self, reminder: ReminderEntry) -> Response:
        return self.rest_api.update_reminder_entry(reminder)

    @require_loggedin_user()
    @use_kwargs(query_schema, location='json_and_query')
    def post(self, identifier: int) -> Response:
        return self.rest_api.query_reminders(event_id=identifier)


class StatsWrapResource(BaseMethodView):
    """Endpoint for the wrap stats. It is temporary and will be removed."""

    query_schema = TimestampRangeSchema()

    @require_loggedin_user()
    @use_kwargs(query_schema, location='json_and_query')
    def post(self, from_timestamp: Timestamp, to_timestamp: Timestamp) -> Response:
        return self.rest_api.query_wrap_stats(
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )


class TimestampHistoricalBalanceResource(BaseMethodView):

    post_schema = HistoricalPerAssetBalanceSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            async_query: bool,
            timestamp: Timestamp,
            asset: Asset | None = None,
    ) -> Response:
        if asset is None:
            return self.rest_api.get_historical_balance(
                timestamp=timestamp,
                async_query=async_query,
            )

        return self.rest_api.get_historical_asset_balance(
            asset=asset,
            timestamp=timestamp,
            async_query=async_query,
        )


class HistoricalAssetAmountsResource(BaseMethodView):

    post_schema = StatisticsAssetBalanceSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            asset: Asset | None,
            collection_id: int | None,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_historical_asset_amounts(
            asset=asset,  # note that from marshmallow asset and collection_id are guaranteed to exist and be mutually exclusive  # noqa: E501
            collection_id=collection_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class HistoricalNetValueResource(BaseMethodView):

    post_schema = TimestampRangeSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json')
    def post(self, from_timestamp: Timestamp, to_timestamp: Timestamp) -> Response:
        return self.rest_api.get_historical_netvalue(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class HistoricalPricesPerAssetResource(BaseMethodView):

    post_schema = HistoricalPricesPerAssetSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            asset: Asset,
            interval: int,
            async_query: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_historical_prices_per_asset(
            asset=asset,
            interval=interval,
            async_query=async_query,
            to_timestamp=to_timestamp,
            from_timestamp=from_timestamp,
        )
