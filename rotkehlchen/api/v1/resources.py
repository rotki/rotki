import sys
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Tuple

from flask import Blueprint, Request, Response, request as flask_request
from flask.views import MethodView
from marshmallow import Schema
from marshmallow.utils import missing
from webargs.flaskparser import parser, use_kwargs
from webargs.multidictproxy import MultiDictProxy
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.v1.parser import ignore_kwarg_parser, resource_parser
from rotkehlchen.api.v1.schemas import (
    AccountingReportDataSchema,
    AccountingReportsSchema,
    AddressbookAddressesSchema,
    AddressbookUpdateSchema,
    AllBalancesQuerySchema,
    AllNamesSchema,
    AppInfoSchema,
    AssetIconUploadSchema,
    AssetMovementsQuerySchema,
    AssetResetRequestSchema,
    AssetsImportingFromFormSchema,
    AssetsImportingSchema,
    AssetsMappingSchema,
    AssetsPostSchema,
    AssetsReplaceSchema,
    AssetsSearchByColumnSchema,
    AssetsSearchLevenshteinSchema,
    AssetUpdatesRequestSchema,
    AsyncHistoricalQuerySchema,
    AsyncIgnoreCacheQueryArgumentSchema,
    AsyncQueryArgumentSchema,
    AsyncTasksQuerySchema,
    AvalancheTransactionQuerySchema,
    BaseCustomAssetSchema,
    BaseXpubSchema,
    BinanceMarketsSchema,
    BinanceMarketsUserSchema,
    BlockchainAccountsDeleteSchema,
    BlockchainAccountsGetSchema,
    BlockchainAccountsPatchSchema,
    BlockchainAccountsPutSchema,
    BlockchainBalanceQuerySchema,
    CryptoAssetSchema,
    CurrentAssetsPriceSchema,
    CustomAssetsQuerySchema,
    DataImportSchema,
    DetectTokensSchema,
    EditCustomAssetSchema,
    EditSettingsSchema,
    ERC20InfoSchema,
    Eth2DailyStatsSchema,
    Eth2ValidatorDeleteSchema,
    Eth2ValidatorPatchSchema,
    Eth2ValidatorPutSchema,
    EthereumTransactionDecodingSchema,
    EthereumTransactionQuerySchema,
    ExchangeBalanceQuerySchema,
    ExchangeRatesSchema,
    ExchangesDataResourceSchema,
    ExchangesResourceAddSchema,
    ExchangesResourceEditSchema,
    ExchangesResourceRemoveSchema,
    ExternalServicesResourceAddSchema,
    ExternalServicesResourceDeleteSchema,
    FileListSchema,
    HistoricalAssetsPriceSchema,
    HistoryBaseEntrySchema,
    HistoryExportingSchema,
    HistoryProcessingDebugImportSchema,
    HistoryProcessingExportSchema,
    HistoryProcessingSchema,
    IdentifiersListSchema,
    IgnoredActionsGetSchema,
    IgnoredActionsModifySchema,
    IgnoredAssetsSchema,
    IntegerIdentifierListSchema,
    IntegerIdentifierSchema,
    LedgerActionSchema,
    LedgerActionsQuerySchema,
    ManuallyTrackedBalancesAddSchema,
    ManuallyTrackedBalancesDeleteSchema,
    ManuallyTrackedBalancesEditSchema,
    ManualPriceDeleteSchema,
    ManualPriceRegisteredSchema,
    ManualPriceSchema,
    ModifyEvmTokenSchema,
    NameDeleteSchema,
    NamedEthereumModuleDataSchema,
    NamedOracleCacheCreateSchema,
    NamedOracleCacheGetSchema,
    NamedOracleCacheSchema,
    NewUserSchema,
    OptionalEthereumAddressSchema,
    QueriedAddressesSchema,
    RequiredEthereumAddressSchema,
    ReverseEnsSchema,
    SingleAssetIdentifierSchema,
    SingleAssetWithOraclesIdentifierSchema,
    SingleFileSchema,
    SnapshotEditingSchema,
    SnapshotImportingSchema,
    SnapshotQuerySchema,
    SnapshotTimestampQuerySchema,
    StakingQuerySchema,
    StatisticsAssetBalanceSchema,
    StatisticsNetValueSchema,
    StatisticsValueDistributionSchema,
    StringIdentifierSchema,
    TagSchema,
    TimedManualPriceSchema,
    TradeDeleteSchema,
    TradePatchSchema,
    TradeSchema,
    TradesQuerySchema,
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
    Web3AddNodeSchema,
    Web3NodeEditSchema,
    Web3NodeListDeleteSchema,
    Web3NodeSchema,
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
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.types import NodeName, WeightedNode
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    Eth2DailyStatsFilterQuery,
    ETHTransactionsFilterQuery,
    LedgerActionsFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    AssetAmount,
    BlockchainAccountData,
    ChainID,
    ChecksumEvmAddress,
    Eth2PubKey,
    EVMChain,
    EVMTxHash,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    ModuleName,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradeType,
    UserNote,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.hdkey import HDKey
    from rotkehlchen.db.filtering import HistoryEventFilterQuery
    from rotkehlchen.exchanges.kraken import KrakenAccountType


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
def load_json_viewargs_data(request: Request, schema: Schema) -> Dict[str, Any]:
    """Load data from a request accepting either json or view_args encoded data"""
    view_args = parser.load_view_args(request, schema)  # type: ignore
    data = parser.load_json(request, schema)
    if data is missing:
        data = {}

    data = _combine_parser_data(data, view_args, schema)
    return data


@parser.location_loader('json_and_query')
def load_json_query_data(request: Request, schema: Schema) -> Dict[str, Any]:
    """Load data from a request accepting either json or query encoded data"""
    data = parser.load_json(request, schema)
    if data is not missing:
        return data
    return parser.load_querystring(request, schema)  # type: ignore


@parser.location_loader('json_and_query_and_view_args')
def load_json_query_viewargs_data(request: Request, schema: Schema) -> Dict[str, Any]:
    """Load data from a request accepting either json or querystring or view_args encoded data"""
    view_args = parser.load_view_args(request, schema)  # type: ignore
    # Get data either from json or from querystring
    data = parser.load_json(request, schema)
    if data is missing:
        data = parser.load_querystring(request, schema)  # type: ignore

    if data is missing:
        return data

    data = _combine_parser_data(data, view_args, schema)
    return data


@parser.location_loader('form_and_file')
def load_form_file_data(request: Request, schema: Schema) -> MultiDictProxy:
    """Load data from a request accepting form and file encoded data"""
    form_data = parser.load_form(request, schema)  # type: ignore
    file_data = parser.load_files(request, schema)  # type: ignore
    data = _combine_parser_data(form_data, file_data, schema)
    return data


@parser.location_loader('view_args_and_file')
def load_view_args_file_data(request: Request, schema: Schema) -> MultiDictProxy:
    """Load data from a request accepting view_args and file encoded data"""
    view_args_data = parser.load_view_args(request, schema)  # type: ignore
    file_data = parser.load_files(request, schema)  # type: ignore
    data = _combine_parser_data(view_args_data, file_data, schema)
    return data


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
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
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
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            msg = (
                f'Currently logged in user {rest_api.rotkehlchen.data.username} '
                f'does not have a premium subscription'
            )
            if rest_api.rotkehlchen.premium is None:
                result_dict = wrap_in_fail_result(msg)
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            if active_check:
                if rest_api.rotkehlchen.premium.is_active() is False:
                    result_dict = wrap_in_fail_result(msg)
                    return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            return f(*args, **kwargs)

        return wrapper
    return _require_premium_user


def create_blueprint(url_prefix: str) -> Blueprint:
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint("v1_resources", __name__, url_prefix=url_prefix)


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
        return self.rest_api.set_settings(settings)

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_settings()


class AsyncTasksResource(BaseMethodView):

    get_schema = AsyncTasksQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, task_id: Optional[int]) -> Response:
        return self.rest_api.query_tasks_outcome(task_id=task_id)


class ExchangeRatesResource(BaseMethodView):

    get_schema = ExchangeRatesSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, currencies: List[Optional[AssetWithOracles]], async_query: bool) -> Response:
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
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: Optional[List[str]],
            ftx_subaccount: Optional[str],
    ) -> Response:
        return self.rest_api.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            binance_markets=binance_markets,
            ftx_subaccount=ftx_subaccount,
        )

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(
            self,
            name: str,
            location: Location,
            new_name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: Optional[List[str]],
            ftx_subaccount: Optional[str],
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
            ftx_subaccount=ftx_subaccount,
        )

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, name: str, location: Location) -> Response:
        return self.rest_api.remove_exchange(name=name, location=location)


class ExchangesDataResource(BaseMethodView):

    delete_schema = ExchangesDataResourceSchema()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='view_args')
    def delete(self, location: Optional[Location]) -> Response:
        return self.rest_api.purge_exchange_data(location=location)


class AssociatedLocations(BaseMethodView):
    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_associated_locations()


class EthereumTransactionsResource(BaseMethodView):
    get_schema = EthereumTransactionQuerySchema()
    post_schema = EthereumTransactionDecodingSchema()

    @require_loggedin_user()
    @ignore_kwarg_parser.use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            async_query: bool,
            only_cache: bool,
            filter_query: ETHTransactionsFilterQuery,
            event_params: Dict[str, Any],
    ) -> Response:
        return self.rest_api.get_ethereum_transactions(
            async_query=async_query,
            only_cache=only_cache,
            filter_query=filter_query,
            event_params=event_params,
        )

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            async_query: bool,
            ignore_cache: bool,
            tx_hashes: Optional[List[EVMTxHash]],
    ) -> Response:
        return self.rest_api.decode_ethereum_transactions(
            async_query=async_query,
            ignore_cache=ignore_cache,
            tx_hashes=tx_hashes,
        )

    @require_loggedin_user()
    def delete(self) -> Response:
        return self.rest_api.purge_ethereum_transaction_data()


class EthereumAirdropsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_ethereum_airdrops(async_query)


class Web3NodesResource(BaseMethodView):

    get_schema = Web3NodeSchema()
    put_schema = Web3AddNodeSchema()
    patch_schema = Web3NodeEditSchema()
    delete_schema = Web3NodeListDeleteSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, blockchain: SupportedBlockchain) -> Response:
        return self.rest_api.get_web3_nodes(blockchain=blockchain)

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
        return self.rest_api.add_web3_node(node)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_query_and_view_args')
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
        return self.rest_api.update_web3_node(node)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query_and_view_args')
    def delete(
            self,
            blockchain: SupportedBlockchain,  # pylint: disable=unused-argument
            identifier: int,
    ) -> Response:
        return self.rest_api.delete_web3_node(identifier=identifier, blockchain=blockchain)


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
            services: List[ExternalServiceApiCredentials],
    ) -> Response:
        return self.rest_api.add_external_services(services=services)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, services: List[ExternalService]) -> Response:
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
    def get(self, location: Optional[Location], async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.query_exchange_balances(
            location=location,
            async_query=async_query,
            ignore_cache=ignore_cache,
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
    def delete(self, files: List[Path]) -> Response:
        return self.rest_api.delete_database_backups(files=files)


class AllAssetsResource(BaseMethodView):

    delete_schema = StringIdentifierSchema()

    def make_post_schema(self) -> AssetsPostSchema:
        return AssetsPostSchema(
            db=self.rest_api.rotkehlchen.data.db,
        )

    def make_add_schema(self) -> CryptoAssetSchema:
        return CryptoAssetSchema(
            identifier_required=False,
            coingecko=self.rest_api.rotkehlchen.coingecko,
            cryptocompare=self.rest_api.rotkehlchen.cryptocompare,
        )

    def make_edit_schema(self) -> CryptoAssetSchema:
        return CryptoAssetSchema(
            identifier_required=True,
            coingecko=self.rest_api.rotkehlchen.coingecko,
            cryptocompare=self.rest_api.rotkehlchen.cryptocompare,
        )

    @resource_parser.use_kwargs(make_post_schema, location='json')
    def post(self, filter_query: AssetsFilterQuery, identifiers: Optional[List[str]]) -> Response:
        return self.rest_api.query_list_of_all_assets(
            filter_query=filter_query,
            identifiers=identifiers,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_add_schema, location='json')
    def put(self, asset_type: AssetType, **kwargs: Any) -> Response:
        return self.rest_api.add_user_asset(asset_type, **kwargs)

    @resource_parser.use_kwargs(make_edit_schema, location='json')
    def patch(self, **kwargs: Any) -> Response:
        return self.rest_api.edit_user_asset(kwargs)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifier: str) -> Response:
        return self.rest_api.delete_asset(identifier)


class AssetsMappingResource(BaseMethodView):
    post_schema = AssetsMappingSchema()

    @use_kwargs(post_schema, location='json')
    def post(self, identifiers: List[str]) -> Response:
        return self.rest_api.get_assets_mappings(identifiers)


class AssetsSearchResource(BaseMethodView):
    post_schema = AssetsSearchByColumnSchema()

    @use_kwargs(post_schema, location='json')
    def post(self, filter_query: AssetsFilterQuery) -> Response:
        return self.rest_api.search_assets(filter_query)


class AssetsSearchLevenshteinResource(BaseMethodView):
    post_schema = AssetsSearchLevenshteinSchema()

    @use_kwargs(post_schema, location='json')
    def post(
            self,
            filter_query: AssetsFilterQuery,
            substring_search: str,
            limit: Optional[int],
    ) -> Response:
        return self.rest_api.search_assets_levenshtein(
            filter_query=filter_query,
            substring_search=substring_search,
            limit=limit,
        )


class AssetsTypesResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.get_asset_types()


class AssetsReplaceResource(BaseMethodView):

    put_schema = AssetsReplaceSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, source_identifier: str, target_asset: Asset) -> Response:
        return self.rest_api.replace_asset(source_identifier, target_asset)


class EthereumAssetsResource(BaseMethodView):

    get_schema = OptionalEthereumAddressSchema()
    delete_schema = RequiredEthereumAddressSchema()

    def make_edit_schema(self) -> ModifyEvmTokenSchema:
        return ModifyEvmTokenSchema(
            coingecko=self.rest_api.rotkehlchen.coingecko,
            cryptocompare=self.rest_api.rotkehlchen.cryptocompare,
        )

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, address: Optional[ChecksumEvmAddress], chain: Optional[ChainID]) -> Response:
        return self.rest_api.get_custom_ethereum_tokens(address=address, chain=chain)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_edit_schema, location='json')
    def put(self, token: EvmToken) -> Response:
        return self.rest_api.add_custom_ethereum_token(token=token)

    @resource_parser.use_kwargs(make_edit_schema, location='json')
    def patch(self, token: EvmToken) -> Response:
        return self.rest_api.edit_custom_ethereum_token(token=token)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, address: ChecksumEvmAddress, chain: ChainID) -> Response:
        return self.rest_api.delete_custom_ethereum_token(address, chain)


class AssetUpdatesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()
    post_schema = AssetUpdatesRequestSchema()
    delete_schema = AssetResetRequestSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_assets_updates(async_query)

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            async_query: bool,
            up_to_version: Optional[int],
            conflicts: Optional[Dict[Asset, Literal['remote', 'local']]],
    ) -> Response:
        return self.rest_api.perform_assets_updates(async_query, up_to_version, conflicts)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json_and_query')
    def delete(self, reset: Literal['soft', 'hard'], ignore_warnings: bool) -> Response:
        return self.rest_api.rebuild_assets_information(reset, ignore_warnings)


class BlockchainBalancesResource(BaseMethodView):

    get_schema = BlockchainBalanceQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            blockchain: Optional[SupportedBlockchain],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        return self.rest_api.query_blockchain_balances(
            blockchain=blockchain,
            async_query=async_query,
            ignore_cache=ignore_cache,
        )


class ManuallyTrackedBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()
    put_schema = ManuallyTrackedBalancesAddSchema()
    patch_schema = ManuallyTrackedBalancesEditSchema()
    delete_schema = ManuallyTrackedBalancesDeleteSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_manually_tracked_balances(async_query)

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, async_query: bool, balances: List[ManuallyTrackedBalance]) -> Response:
        return self.rest_api.add_manually_tracked_balances(async_query=async_query, data=balances)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, async_query: bool, balances: List[ManuallyTrackedBalance]) -> Response:
        return self.rest_api.edit_manually_tracked_balances(async_query=async_query, data=balances)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, async_query: bool, ids: List[int]) -> Response:
        return self.rest_api.remove_manually_tracked_balances(
            async_query=async_query,
            ids=ids,
        )


class TradesResource(BaseMethodView):

    def make_get_schema(self) -> TradesQuerySchema:
        with self.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rest_api.rotkehlchen.data.db.get_settings(cursor)
        return TradesQuerySchema(
            treat_eth2_as_eth=settings.treat_eth2_as_eth,
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
    ) -> Response:
        return self.rest_api.get_trades(
            async_query=async_query,
            only_cache=only_cache,
            filter_query=filter_query,
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
            fee: Optional[Fee],
            fee_currency: Optional[Asset],
            link: Optional[str],
            notes: Optional[str],
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
            fee: Optional[Fee],
            fee_currency: Optional[Asset],
            link: Optional[str],
            notes: Optional[str],
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
    def delete(self, trades_ids: List[str]) -> Response:
        return self.rest_api.delete_trades(trades_ids=trades_ids)


class AssetMovementsResource(BaseMethodView):

    def make_get_schema(self) -> AssetMovementsQuerySchema:
        with self.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rest_api.rotkehlchen.data.db.get_settings(cursor)
        return AssetMovementsQuerySchema(
            treat_eth2_as_eth=settings.treat_eth2_as_eth,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def get(
            self,
            filter_query: AssetMovementsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        return self.rest_api.get_asset_movements(
            filter_query=filter_query,
            async_query=async_query,
            only_cache=only_cache,
        )


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
            description: Optional[str],
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
            description: Optional[str],
            background_color: Optional[HexColorCode],
            foreground_color: Optional[HexColorCode],
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


class LedgerActionsResource(BaseMethodView):

    def make_get_schema(self) -> LedgerActionsQuerySchema:
        with self.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rest_api.rotkehlchen.data.db.get_settings(cursor)
        return LedgerActionsQuerySchema(
            treat_eth2_as_eth=settings.treat_eth2_as_eth,
        )

    put_schema = LedgerActionSchema(identifier_required=False)
    patch_schema = LedgerActionSchema(identifier_required=True)
    delete_schema = IntegerIdentifierListSchema()

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_get_schema, location='json_and_query')
    def get(
            self,
            filter_query: LedgerActionsFilterQuery,
            async_query: bool,
            only_cache: bool,
    ) -> Response:
        return self.rest_api.get_ledger_actions(
            filter_query=filter_query,
            async_query=async_query,
            only_cache=only_cache,
        )

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            action: LedgerAction,
    ) -> Response:
        return self.rest_api.add_ledger_action(action)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, action: LedgerAction) -> Response:
        return self.rest_api.edit_ledger_action(action=action)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifiers: List[int]) -> Response:
        return self.rest_api.delete_ledger_actions(identifiers=identifiers)


class HistoryBaseEntryResource(BaseMethodView):

    put_schema = HistoryBaseEntrySchema(identifier_required=False)
    patch_schema = HistoryBaseEntrySchema(identifier_required=True)
    delete_schema = IdentifiersListSchema()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(self, event: HistoryBaseEntry) -> Response:
        return self.rest_api.add_history_event(event)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, event: HistoryBaseEntry) -> Response:
        return self.rest_api.edit_history_event(event=event)

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='json')
    def delete(self, identifiers: List[int]) -> Response:
        return self.rest_api.delete_history_events(identifiers=identifiers)


class UsersResource(BaseMethodView):

    put_schema = NewUserSchema()

    def get(self) -> Response:
        return self.rest_api.get_users()

    @use_kwargs(put_schema, location='json')
    def put(
            self,
            name: str,
            password: str,
            premium_api_key: str,
            premium_api_secret: str,
            sync_database: bool,
            initial_settings: Optional[ModifiableDBSettings],
    ) -> Response:
        return self.rest_api.create_new_user(
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
            action: Optional[str],
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
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
    ) -> Response:
        return self.rest_api.user_login(
            name=name,
            password=password,
            sync_approval=sync_approval,
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
        return self.rest_api.sync_data(async_query, action)


class StatisticsNetvalueResource(BaseMethodView):

    get_schema = StatisticsNetValueSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, include_nfts: bool) -> Response:
        return self.rest_api.query_netvalue_data(include_nfts)


class StatisticsAssetBalanceResource(BaseMethodView):

    post_schema = StatisticsAssetBalanceSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json')
    def post(
            self,
            asset: Asset,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.query_timed_balances_data(
            asset=asset,
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
    upload_schema = HistoryProcessingDebugImportSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_query')
    def post(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Optional[Path],
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
        def patch(self, async_query: bool, filepath: FileStorage) -> Response:
            return self.rest_api.import_history_debug(
                async_query=async_query,
                filepath=filepath,
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
    def get(self, report_id: Optional[int]) -> Response:
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


class BlockchainsAccountsResource(BaseMethodView):

    get_schema = BlockchainAccountsGetSchema()

    def make_put_schema(self) -> BlockchainAccountsPutSchema:
        return BlockchainAccountsPutSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum,
        )

    def make_patch_schema(self) -> BlockchainAccountsPatchSchema:
        return BlockchainAccountsPatchSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum,
        )

    def make_delete_schema(self) -> BlockchainAccountsDeleteSchema:
        return BlockchainAccountsDeleteSchema(
            self.rest_api.rotkehlchen.chains_aggregator.ethereum,
        )

    @require_loggedin_user()
    @use_kwargs(get_schema, location='view_args')
    def get(self, blockchain: SupportedBlockchain) -> Response:
        return self.rest_api.get_blockchain_accounts(blockchain)

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_put_schema, location='json_and_view_args')
    def put(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[Dict[str, Any]],
            async_query: bool,
    ) -> Response:
        account_data = [
            BlockchainAccountData(
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.add_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
            async_query=async_query,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_patch_schema, location='json_and_view_args')
    def patch(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[Dict[str, Any]],
    ) -> Response:
        account_data = [
            BlockchainAccountData(
                address=entry['address'],
                label=entry['label'],
                tags=entry['tags'],
            ) for entry in accounts
        ]
        return self.rest_api.edit_blockchain_accounts(
            blockchain=blockchain,
            account_data=account_data,
        )

    @require_loggedin_user()
    @resource_parser.use_kwargs(make_delete_schema, location='json_and_view_args')
    def delete(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            async_query: bool,
    ) -> Response:
        return self.rest_api.remove_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            async_query=async_query,
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
            derivation_path: Optional[str],
            label: Optional[str],
            tags: Optional[List[str]],
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
            derivation_path: Optional[str],
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
            derivation_path: Optional[str],
            label: Optional[str],
            tags: Optional[List[str]],
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
    post_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_ignored_assets()

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def put(self, assets: List[Asset]) -> Response:
        return self.rest_api.add_ignored_assets(assets=assets)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def delete(self, assets: List[Asset]) -> Response:
        return self.rest_api.remove_ignored_assets(assets=assets)

    @use_kwargs(post_schema, location='json_and_query')
    def post(self, async_query: bool) -> Response:
        return self.rest_api.pull_spam_assets(async_query)


class IgnoredActionsResource(BaseMethodView):

    get_schema = IgnoredActionsGetSchema()
    modify_schema = IgnoredActionsModifySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, action_type: Optional[ActionType]) -> Response:
        return self.rest_api.get_ignored_action_ids(action_type=action_type)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def put(self, action_type: ActionType, action_ids: List[str]) -> Response:
        return self.rest_api.add_ignored_action_ids(action_type=action_type, action_ids=action_ids)

    @require_loggedin_user()
    @use_kwargs(modify_schema, location='json')
    def delete(self, action_type: ActionType, action_ids: List[str]) -> Response:
        return self.rest_api.remove_ignored_action_ids(
            action_type=action_type,
            action_ids=action_ids,
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
        return self.rest_api.get_info(check_for_updates)


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
    post_schema = Eth2DailyStatsSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(post_schema, location='json_and_query')
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

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_eth2_validators()

    @require_loggedin_user()
    @use_kwargs(put_schema, location='json')
    def put(
            self,
            validator_index: Optional[int],
            public_key: Optional[Eth2PubKey],
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
    def delete(self, validators: List[Dict[str, Any]]) -> Response:
        return self.rest_api.delete_eth2_validator(validators)

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json')
    def patch(self, validator_index: int, ownership_percentage: FVal) -> Response:
        return self.rest_api.edit_eth2_validator(
            validator_index=validator_index,
            ownership_proportion=ownership_percentage,
        )


class Eth2StakeDepositsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_eth2_stake_deposits(async_query)


class Eth2StakeDetailsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_eth2_stake_details(async_query)


class DefiBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_defi_balances(async_query)


class NamedEthereumModuleDataResource(BaseMethodView):
    delete_schema = NamedEthereumModuleDataSchema()

    @require_loggedin_user()
    @use_kwargs(delete_schema, location='view_args')
    def delete(self, module_name: ModuleName) -> Response:
        return self.rest_api.purge_module_data(module_name)


class EthereumModuleDataResource(BaseMethodView):

    def delete(self) -> Response:
        return self.rest_api.purge_module_data(module_name=None)


class EthereumModuleResource(BaseMethodView):

    def get(self) -> Response:
        return self.rest_api.supported_modules()


class MakerdaoDSRBalanceResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_makerdao_dsr_balance(async_query)


class MakerdaoDSRHistoryResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_makerdao_dsr_history(async_query)


class MakerdaoVaultsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_makerdao_vaults(async_query)


class MakerdaoVaultDetailsResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_makerdao_vault_details(async_query)


class AaveBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_aave_balances(async_query)


class AaveHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_aave_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class AdexBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_adex_balances(async_query=async_query)


class AdexHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_adex_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class CompoundBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_compound_balances(async_query)


class CompoundHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_compound_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class YearnVaultsBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_yearn_vaults_balances(async_query)


class YearnVaultsV2BalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_yearn_vaults_v2_balances(async_query)


class YearnVaultsHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_yearn_vaults_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class YearnVaultsV2HistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_yearn_vaults_v2_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class UniswapBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_uniswap_balances(async_query=async_query)


class UniswapEventsHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_uniswap_events_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class UniswapV3BalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_uniswap_v3_balances(async_query=async_query)


class SushiswapBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_sushiswap_balances(async_query=async_query)


class SushiswapEventsHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_sushiswap_events_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


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


class LiquityTrovesHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
        self,
        async_query: bool,
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_liquity_trove_events(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class LiquityStakingHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
        self,
        async_query: bool,
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_liquity_stake_events(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class LiquityStakingResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_liquity_staked(async_query=async_query)


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


class BalancerBalancesResource(BaseMethodView):

    get_schema = AsyncQueryArgumentSchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool) -> Response:
        return self.rest_api.get_balancer_balances(async_query=async_query)


class BalancerEventsHistoryResource(BaseMethodView):

    get_schema = AsyncHistoricalQuerySchema()

    @require_premium_user(active_check=False)
    @use_kwargs(get_schema, location='json_and_query')
    def get(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_balancer_events_history(
            async_query=async_query,
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class WatchersResource(BaseMethodView):

    put_schema = WatchersAddSchema
    patch_schema = WatchersEditSchema
    delete_schema = WatchersDeleteSchema

    @require_premium_user(active_check=False)
    def get(self) -> Response:
        return self.rest_api.get_watchers()

    @require_premium_user(active_check=False)
    @use_kwargs(put_schema, location='json')
    def put(self, watchers: List[Dict[str, Any]]) -> Response:
        return self.rest_api.add_watchers(watchers)

    @require_premium_user(active_check=False)
    @use_kwargs(patch_schema, location='json')
    def patch(self, watchers: List[Dict[str, Any]]) -> Response:
        return self.rest_api.edit_watchers(watchers)

    @require_premium_user(active_check=False)
    @use_kwargs(delete_schema, location='json')
    def delete(self, watchers: List[str]) -> Response:
        return self.rest_api.delete_watchers(watchers)


class AssetIconFileResource(BaseMethodView):

    get_schema = SingleAssetIdentifierSchema()

    @use_kwargs(get_schema, location='query')
    def get(self, asset: Asset) -> Response:
        # Process the if-match and if-none-match headers so that comparison with etag can be done
        match_header = flask_request.headers.get('If-Match', None)
        if not match_header:
            match_header = flask_request.headers.get('If-None-Match', None)
        if match_header:
            match_header = match_header[1:-1]  # remove enclosing quotes

        return self.rest_api.get_asset_icon(asset, match_header)


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
            filename = file.filename if file.filename else f'{asset.identifier}.png'
            filepath = Path(temp_directory) / filename
            file.save(str(filepath))
            response = self.rest_api.upload_asset_icon(asset=asset, filepath=filepath)

        return response

    @use_kwargs(patch_schema, location='json')
    def patch(self, asset: AssetWithOracles) -> Response:
        return self.rest_api.refresh_asset_icon(asset)


class AllLatestAssetsPriceResource(BaseMethodView):

    post_schema = ManualPriceRegisteredSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, from_asset: Optional[Asset], to_asset: Optional[Asset]) -> Response:
        return self.rest_api.get_manual_latest_prices(from_asset, to_asset)


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
            assets: List[AssetWithNameAndType],
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
        return self.rest_api.delete_manual_latest_price(asset)


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
            assets_timestamp: List[Tuple[Asset, Timestamp]],
            target_asset: Asset,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_historical_assets_price(
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
    def get(self, from_asset: Optional[Asset], to_asset: Optional[Asset]) -> Response:
        return self.rest_api.get_manual_prices(from_asset, to_asset)

    @use_kwargs(delete_schema)
    def delete(
        self,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.delete_manual_price(from_asset, to_asset, timestamp)


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
    def get(self, address: ChecksumEvmAddress, async_query: bool) -> Response:
        return self.rest_api.get_token_information(address, async_query)


class BinanceAvailableMarkets(BaseMethodView):

    get_schema = BinanceMarketsSchema()

    @use_kwargs(get_schema, location='json_and_query')
    def get(self, location: Location) -> Response:
        return self.rest_api.get_all_binance_pairs(location)


class BinanceUserMarkets(BaseMethodView):

    get_schema = BinanceMarketsUserSchema()

    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(self, name: str, location: Location) -> Response:
        return self.rest_api.get_user_binance_pairs(name, location)


class AvalancheTransactionsResource(BaseMethodView):
    get_schema = AvalancheTransactionQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
        self,
        async_query: bool,
        address: ChecksumEvmAddress,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.get_avalanche_transactions(
            async_query=async_query,
            address=address,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class NFTSResource(BaseMethodView):
    get_schema = AsyncIgnoreCacheQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.get_nfts(async_query=async_query, ignore_cache=ignore_cache)


class NFTSBalanceResource(BaseMethodView):
    get_schema = AsyncIgnoreCacheQueryArgumentSchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query')
    def get(self, async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.get_nfts_balances(async_query=async_query, ignore_cache=ignore_cache)


class NFTSPricesResource(BaseMethodView):

    @require_loggedin_user()
    def get(self) -> Response:
        return self.rest_api.get_nfts_with_price()


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
    def put(self, file: Optional[Path], destination: Optional[Path], action: str) -> Response:
        if action == 'upload':
            if file is None:
                return api_response(wrap_in_fail_result(
                    message='file is required for upload action.',
                    status_code=HTTPStatus.BAD_REQUEST,
                ))
            return self.rest_api.import_user_assets(path=file)
        return self.rest_api.get_user_added_assets(path=destination)

    @require_loggedin_user()
    @use_kwargs(import_from_form, location='form_and_file')
    def post(self, file: FileStorage) -> Response:
        with TemporaryDirectory() as temp_directory:
            filename = file.filename if file.filename else 'assets.zip'
            filepath = Path(temp_directory) / filename
            file.save(str(filepath))
            response = self.rest_api.import_user_assets(path=filepath)
        return response


class DBSnapshotsResource(BaseMethodView):
    get_schema = SnapshotQuerySchema()
    upload_schema = SnapshotImportingSchema()
    patch_schema = SnapshotEditingSchema()
    delete_schema = SnapshotTimestampQuerySchema()

    @require_loggedin_user()
    @use_kwargs(get_schema, location='json_and_query_and_view_args')
    def get(
            self,
            action: Optional[Literal['export', 'download']],
            timestamp: Timestamp,
            path: Optional[Path],
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
            balance_snapshot_filename = balances_snapshot_file.filename if balances_snapshot_file.filename else 'balances_snapshot_import.csv'  # noqa: 501
            location_data_snapshot_filename = location_data_snapshot_file.filename if location_data_snapshot_file.filename else 'location_data_snapshot.csv'  # noqa: 501
            balance_snapshot_filepath = Path(temp_directory) / balance_snapshot_filename
            location_data_snapshot_filepath = Path(temp_directory) / location_data_snapshot_filename  # noqa: 501
            balances_snapshot_file.save(balance_snapshot_filepath)
            location_data_snapshot_file.save(location_data_snapshot_filepath)
            response = self.rest_api.import_user_snapshot(
                balances_snapshot_file=balance_snapshot_filepath,
                location_data_snapshot_file=location_data_snapshot_filepath,
            )
        return response

    @require_loggedin_user()
    @use_kwargs(patch_schema, location='json_and_view_args')
    def patch(
            self,
            timestamp: Timestamp,
            balances_snapshot: List[DBAssetBalance],
            location_data_snapshot: List[LocationData],
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
            ethereum_addresses: List[ChecksumEvmAddress],
            ignore_cache: bool,
            async_query: bool,
    ) -> Response:
        return self.rest_api.get_ens_mappings(
            addresses=ethereum_addresses,
            ignore_cache=ignore_cache,
            async_query=async_query,
        )


class CounterpartiesResource(BaseMethodView):
    def get(self) -> Response:
        return self.rest_api.get_all_counterparties()


class AddressbookResource(BaseMethodView):
    post_delete_schema = AddressbookAddressesSchema()
    update_schema = AddressbookUpdateSchema()

    @require_loggedin_user()
    @use_kwargs(post_delete_schema, location='json_and_view_args')
    def post(
        self,
        book_type: AddressbookType,
        addresses: Optional[List[ChecksumEvmAddress]],
    ) -> Response:
        return self.rest_api.get_addressbook_entries(
            book_type=book_type,
            addresses=addresses,
        )

    @require_loggedin_user()
    @use_kwargs(update_schema, location='json_and_view_args')
    def put(self, book_type: AddressbookType, entries: List[AddressbookEntry]) -> Response:
        return self.rest_api.add_addressbook_entries(book_type=book_type, entries=entries)

    @require_loggedin_user()
    @use_kwargs(update_schema, location='json_and_view_args')
    def patch(self, book_type: AddressbookType, entries: List[AddressbookEntry]) -> Response:
        return self.rest_api.update_addressbook_entries(book_type=book_type, entries=entries)

    @require_loggedin_user()
    @use_kwargs(post_delete_schema, location='json_and_view_args')
    def delete(self, book_type: AddressbookType, addresses: List[ChecksumEvmAddress]) -> Response:
        return self.rest_api.delete_addressbook_entries(book_type=book_type, addresses=addresses)


class AllNamesResource(BaseMethodView):
    post_schema = AllNamesSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json')
    def post(self, addresses: List[ChecksumEvmAddress]) -> Response:
        return self.rest_api.search_for_names_everywhere(addresses=addresses)


class DetectTokensResource(BaseMethodView):
    post_schema = DetectTokensSchema()

    @require_loggedin_user()
    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            blockchain: EVMChain,
            async_query: bool,
            only_cache: bool,
            addresses: Optional[List[ChecksumEvmAddress]],
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
    patch_schema = EditCustomAssetSchema()
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
