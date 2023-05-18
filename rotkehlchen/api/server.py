import json
import logging
import sys
from http import HTTPStatus
from typing import Any, Optional, Union

import werkzeug
from flask import Blueprint, Flask, Response, abort, jsonify, request
from flask.views import MethodView
from flask_cors import CORS
from gevent.pywsgi import WSGIServer
from geventwebsocket import Resource as WebsocketResource
from geventwebsocket.handler import WebSocketHandler
from marshmallow import Schema
from marshmallow.exceptions import ValidationError
from webargs.flaskparser import parser
from werkzeug.exceptions import NotFound

from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.v1.parser import ignore_kwarg_parser, resource_parser
from rotkehlchen.api.v1.resources import (
    AaveBalancesResource,
    AaveHistoryResource,
    AccountingReportDataResource,
    AccountingReportsResource,
    AddressbookResource,
    AllAssetsResource,
    AllBalancesResource,
    AllEvmChainsResource,
    AllLatestAssetsPriceResource,
    AllNamesResource,
    AssetIconFileResource,
    AssetIconsResource,
    AssetMovementsResource,
    AssetsMappingResource,
    AssetsReplaceResource,
    AssetsSearchLevenshteinResource,
    AssetsSearchResource,
    AssetsTypesResource,
    AssetUpdatesResource,
    AssociatedLocations,
    AsyncTasksResource,
    AvalancheTransactionsResource,
    BalancerBalancesResource,
    BalancerEventsHistoryResource,
    BinanceAvailableMarkets,
    BinanceSavingsResource,
    BinanceUserMarkets,
    BlockchainBalancesResource,
    BlockchainsAccountsResource,
    BTCXpubResource,
    ClearCacheResource,
    CompoundBalancesResource,
    CompoundHistoryResource,
    ConfigurationsResource,
    CustomAssetsResource,
    CustomAssetsTypesResource,
    DatabaseBackupsResource,
    DatabaseInfoResource,
    DataImportResource,
    DBSnapshotsResource,
    DefiBalancesResource,
    DetectTokensResource,
    EnsAvatarsResource,
    ERC20TokenInfo,
    Eth2DailyStatsResource,
    Eth2StakeDetailsResource,
    Eth2ValidatorsResource,
    EthereumAirdropsResource,
    EthereumAssetsResource,
    EthereumModuleDataResource,
    EthereumModuleResource,
    EventDetailsResource,
    EventsOnlineQueryResource,
    EvmAccountsResource,
    EvmCounterpartiesResource,
    EvmPendingTransactionsDecodingResource,
    EvmTransactionsHashResource,
    EvmTransactionsResource,
    ExchangeBalancesResource,
    ExchangeRatesResource,
    ExchangesDataResource,
    ExchangesResource,
    ExternalServicesResource,
    HistoricalAssetsPriceResource,
    HistoryActionableItemsResource,
    HistoryDownloadingResource,
    HistoryEventResource,
    HistoryExportingResource,
    HistoryProcessingDebugResource,
    HistoryProcessingResource,
    HistoryStatusResource,
    IgnoredActionsResource,
    IgnoredAssetsResource,
    InfoResource,
    LatestAssetsPriceResource,
    LedgerActionsResource,
    LiquityStabilityPoolResource,
    LiquityStakingResource,
    LiquityStakingStats,
    LiquityTrovesResource,
    LocationResource,
    LoopringBalancesResource,
    MakerdaoDSRBalanceResource,
    MakerdaoDSRHistoryResource,
    MakerdaoVaultDetailsResource,
    MakerdaoVaultsResource,
    ManuallyTrackedBalancesResource,
    MessagesResource,
    NamedEthereumModuleDataResource,
    NamedOracleCacheResource,
    NFTSBalanceResource,
    NFTSPricesResource,
    NFTSResource,
    OraclesResource,
    OwnedAssetsResource,
    PeriodicDataResource,
    PickleDillResource,
    PingResource,
    QueriedAddressesResource,
    RefreshGeneralCacheResource,
    ReverseEnsResource,
    RpcNodesResource,
    SettingsResource,
    StakingResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    SupportedChainsResource,
    SushiswapBalancesResource,
    SushiswapEventsHistoryResource,
    TagsResource,
    TradesResource,
    TypesMappingsResource,
    UniswapBalancesResource,
    UniswapEventsHistoryResource,
    UniswapV3BalancesResource,
    UserAssetsResource,
    UserNotesResource,
    UserPasswordChangeResource,
    UserPremiumKeyResource,
    UserPremiumSyncResource,
    UsersByNameResource,
    UsersResource,
    WatchersResource,
    YearnVaultsBalancesResource,
    YearnVaultsHistoryResource,
    YearnVaultsV2BalancesResource,
    YearnVaultsV2HistoryResource,
    create_blueprint,
)
from rotkehlchen.api.websockets.notifier import RotkiNotifier, RotkiWSApp
from rotkehlchen.logging import RotkehlchenLogsAdapter

URLS = list[
    Union[
        tuple[str, type[MethodView]],
        tuple[str, type[MethodView], str],
    ]
]


URLS_V1: URLS = [
    ('/users', UsersResource),
    ('/watchers', WatchersResource),
    ('/users/<string:name>', UsersByNameResource),
    ('/users/<string:name>/password', UserPasswordChangeResource),
    ('/premium', UserPremiumKeyResource),
    ('/premium/sync', UserPremiumSyncResource),
    ('/settings', SettingsResource),
    ('/settings/configuration', ConfigurationsResource),
    ('/tasks', AsyncTasksResource),
    ('/tasks/<int:task_id>', AsyncTasksResource, 'specific_async_tasks_resource'),
    ('/exchange_rates', ExchangeRatesResource),
    ('/external_services', ExternalServicesResource),
    ('/oracles', OraclesResource),
    ('/oracles/<string:oracle>/cache', NamedOracleCacheResource),
    ('/exchanges', ExchangesResource),
    ('/exchanges/balances', ExchangeBalancesResource),
    (
        '/exchanges/balances/<string:location>',
        ExchangeBalancesResource,
        'named_exchanges_balances_resource',
    ),
    ('/assets/icon', AssetIconFileResource),
    ('/assets/icon/modify', AssetIconsResource),
    ('/trades', TradesResource),
    ('/ledgeractions', LedgerActionsResource),
    ('/asset_movements', AssetMovementsResource),
    ('/tags', TagsResource),
    ('/exchanges/binance/pairs', BinanceAvailableMarkets),
    ('/exchanges/<string:location>/savings', BinanceSavingsResource),  # this can only be Binance/BinanceUS  # noqa: E501
    ('/exchanges/binance/pairs/<string:name>', BinanceUserMarkets),
    ('/exchanges/data', ExchangesDataResource),
    ('/exchanges/data/<string:location>', ExchangesDataResource, 'named_exchanges_data_resource'),
    ('/balances/blockchains', BlockchainBalancesResource),
    (
        '/balances/blockchains/<string:blockchain>',
        BlockchainBalancesResource,
        'named_blockchain_balances_resource',
    ),
    ('/balances', AllBalancesResource),
    ('/balances/manual', ManuallyTrackedBalancesResource),
    ('/statistics/netvalue', StatisticsNetvalueResource),
    ('/statistics/balance', StatisticsAssetBalanceResource),
    ('/statistics/value_distribution', StatisticsValueDistributionResource),
    ('/statistics/renderer', StatisticsRendererResource),
    ('/messages', MessagesResource),
    ('/periodic', PeriodicDataResource),
    ('/history', HistoryProcessingResource),
    ('/history/debug', HistoryProcessingDebugResource),
    ('/history/status', HistoryStatusResource),
    ('/history/export', HistoryExportingResource),
    ('/history/download', HistoryDownloadingResource),
    ('/history/events', HistoryEventResource),
    ('/history/events/query', EventsOnlineQueryResource),
    ('/history/events/type_mappings', TypesMappingsResource),
    ('/history/events/counterparties', EvmCounterpartiesResource),
    ('/history/events/details', EventDetailsResource),
    ('/history/actionable_items', HistoryActionableItemsResource),
    ('/reports', AccountingReportsResource),
    (
        '/reports/<int:report_id>',
        AccountingReportsResource,
        'per_report_resource',
    ),
    (
        '/reports/<int:report_id>/data',
        AccountingReportDataResource,
        'per_report_data_resource',
    ),
    ('/queried_addresses', QueriedAddressesResource),
    ('/blockchains/supported', SupportedChainsResource),
    ('blockchains/evm/all', AllEvmChainsResource),
    ('/blockchains/evm/transactions', EvmTransactionsResource),
    ('/blockchains/evm/transactions/decode', EvmPendingTransactionsDecodingResource),
    ('/blockchains/eth2/validators', Eth2ValidatorsResource),
    ('/blockchains/eth2/stake/details', Eth2StakeDetailsResource),
    ('/blockchains/eth2/stake/dailystats', Eth2DailyStatsResource),
    ('/blockchains/eth/defi', DefiBalancesResource),
    ('/blockchains/eth/airdrops', EthereumAirdropsResource),
    ('/blockchains/eth/erc20details', ERC20TokenInfo),
    ('/blockchains/eth/modules/<string:module_name>/data', NamedEthereumModuleDataResource),
    ('/blockchains/eth/modules/data', EthereumModuleDataResource),
    ('/blockchains/eth/modules', EthereumModuleResource),
    ('/blockchains/eth/modules/makerdao/dsrbalance', MakerdaoDSRBalanceResource),
    ('/blockchains/eth/modules/makerdao/dsrhistory', MakerdaoDSRHistoryResource),
    ('/blockchains/eth/modules/makerdao/vaults', MakerdaoVaultsResource),
    ('/blockchains/eth/modules/makerdao/vaultdetails', MakerdaoVaultDetailsResource),
    ('/blockchains/eth/modules/aave/balances', AaveBalancesResource),
    ('/blockchains/eth/modules/aave/history', AaveHistoryResource),
    ('/blockchains/eth/modules/balancer/balances', BalancerBalancesResource),
    ('/blockchains/eth/modules/balancer/history/events', BalancerEventsHistoryResource),
    ('/blockchains/eth/modules/compound/balances', CompoundBalancesResource),
    ('/blockchains/eth/modules/compound/history', CompoundHistoryResource),
    ('/blockchains/eth/modules/uniswap/v2/balances', UniswapBalancesResource),
    ('/blockchains/eth/modules/uniswap/v3/balances', UniswapV3BalancesResource),
    ('/blockchains/eth/modules/uniswap/history/events', UniswapEventsHistoryResource),
    ('/blockchains/eth/modules/sushiswap/balances', SushiswapBalancesResource),
    ('/blockchains/eth/modules/sushiswap/history/events', SushiswapEventsHistoryResource),
    ('/blockchains/eth/modules/yearn/vaults/balances', YearnVaultsBalancesResource),
    ('/blockchains/eth/modules/yearn/vaults/history', YearnVaultsHistoryResource),
    ('/blockchains/eth/modules/yearn/vaultsv2/balances', YearnVaultsV2BalancesResource),
    ('/blockchains/eth/modules/yearn/vaultsv2/history', YearnVaultsV2HistoryResource),
    ('/blockchains/eth/modules/liquity/balances', LiquityTrovesResource),
    ('/blockchains/eth/modules/liquity/staking', LiquityStakingResource),
    ('/blockchains/eth/modules/liquity/pool', LiquityStabilityPoolResource),
    ('/blockchains/eth/modules/liquity/stats', LiquityStakingStats),
    ('/blockchains/eth/modules/pickle/dill', PickleDillResource),
    ('/blockchains/eth/modules/loopring/balances', LoopringBalancesResource),
    ('/blockchains/evm/accounts', EvmAccountsResource),
    ('/blockchains/<string:blockchain>/accounts', BlockchainsAccountsResource),
    ('/blockchains/<string:blockchain>/nodes', RpcNodesResource),
    ('/blockchains/<string:blockchain>/tokens/detect', DetectTokensResource),
    ('/blockchains/<string:blockchain>/xpub', BTCXpubResource),
    ('/blockchains/evm/transactions/add-hash', EvmTransactionsHashResource),
    ('/blockchains/AVAX/transactions', AvalancheTransactionsResource),
    (
        '/blockchains/AVAX/transactions/<string:address>',
        AvalancheTransactionsResource,
        'per_address_avalanche_transactions_resource',
    ),
    ('/assets', OwnedAssetsResource),
    ('/assets/types', AssetsTypesResource),
    ('/assets/replace', AssetsReplaceResource),
    ('/assets/all', AllAssetsResource),
    ('/assets/mappings', AssetsMappingResource),
    ('/assets/search', AssetsSearchResource),
    ('/assets/search/levenshtein', AssetsSearchLevenshteinResource),
    ('/assets/ethereum', EthereumAssetsResource),
    ('/assets/prices/latest', LatestAssetsPriceResource),
    ('/assets/prices/latest/all', AllLatestAssetsPriceResource),
    ('/assets/prices/historical', HistoricalAssetsPriceResource),
    ('/assets/ignored', IgnoredAssetsResource),
    ('/assets/updates', AssetUpdatesResource),
    ('/assets/user', UserAssetsResource),
    ('/assets/custom', CustomAssetsResource),
    ('/assets/custom/types', CustomAssetsTypesResource),
    ('/actions/ignored', IgnoredActionsResource),
    ('/info', InfoResource),
    ('/ping', PingResource),
    ('/import', DataImportResource),
    ('/nfts', NFTSResource),
    ('/nfts/balances', NFTSBalanceResource),
    ('/nfts/prices', NFTSPricesResource),
    ('/database/info', DatabaseInfoResource),
    ('/database/backups', DatabaseBackupsResource),
    ('/locations/all', LocationResource),
    ('/locations/associated', AssociatedLocations),
    ('/staking/kraken', StakingResource),
    ('/names', AllNamesResource),
    ('/names/ens/reverse', ReverseEnsResource),
    ('/avatars/ens/<string:ens_name>', EnsAvatarsResource),
    ('/names/addressbook/<string:book_type>', AddressbookResource),
    ('/snapshots', DBSnapshotsResource),
    (
        '/snapshots/<int:timestamp>',
        DBSnapshotsResource,
        'per_timestamp_db_snapshots_resource',
    ),
    ('/notes', UserNotesResource),
    ('/cache/<string:cache_type>/clear', ClearCacheResource),
    ('/cache/general/refresh', RefreshGeneralCacheResource),
]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def setup_urls(
        rest_api: RestAPI,
        blueprint: Blueprint,
        urls: URLS,
) -> None:
    for url_tuple in urls:
        if len(url_tuple) == 2:
            route, resource_cls = url_tuple  # type: ignore
            endpoint = resource_cls.__name__.lower()
        elif len(url_tuple) == 3:
            route, resource_cls, endpoint = url_tuple  # type: ignore
        else:
            raise ValueError(f'Invalid URL format: {url_tuple!r}')
        blueprint.add_url_rule(
            route,
            view_func=resource_cls.as_view(endpoint, rest_api_object=rest_api),
        )


def endpoint_not_found(e: NotFound) -> Response:
    msg = 'invalid endpoint'
    # The isinstance check is because I am not sure if `e` is always going to
    # be a "NotFound" error here
    if isinstance(e, NotFound):
        msg = e.description
    return api_response(wrap_in_fail_result(msg), HTTPStatus.NOT_FOUND)


@parser.error_handler  # type: ignore
@resource_parser.error_handler
@ignore_kwarg_parser.error_handler
def handle_request_parsing_error(
        err: ValidationError,
        _request: werkzeug.local.LocalProxy,
        _schema: Schema,
        error_status_code: Optional[int],  # pylint: disable=unused-argument
        error_headers: Optional[dict],  # pylint: disable=unused-argument
) -> None:
    """ This handles request parsing errors generated for example by schema
    field validation failing."""
    msg = str(err)
    if isinstance(err.messages, dict):
        # first key is just the location. Ignore
        key = list(err.messages.keys())[0]
        msg = json.dumps(err.messages[key])
    elif isinstance(err.messages, list):
        msg = ','.join(err.messages)

    err_response = jsonify(result=None, message=msg)
    err_response.status_code = HTTPStatus.BAD_REQUEST
    abort(err_response)


class APIServer():

    _api_prefix = '/api/1'

    def __init__(
            self,
            rest_api: RestAPI,
            ws_notifier: RotkiNotifier,
            cors_domain_list: Optional[list[str]] = None,
    ) -> None:
        flask_app = Flask(__name__)
        if cors_domain_list:
            CORS(flask_app, origins=cors_domain_list)
        blueprint = create_blueprint(self._api_prefix)
        setup_urls(
            blueprint=blueprint,
            rest_api=rest_api,
            urls=URLS_V1,
        )

        self.rest_api = rest_api
        self.rotki_notifier = ws_notifier
        self.flask_app = flask_app
        self.blueprint = blueprint

        self.wsgiserver: Optional[WSGIServer] = None
        self.flask_app.register_blueprint(self.blueprint)

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)
        self.flask_app.register_error_handler(Exception, self.unhandled_exception)
        self.flask_app.before_request(self.before_request_callback)
        self.flask_app.after_request(self.after_request_callback)

    @staticmethod
    def unhandled_exception(exception: Exception) -> Response:
        """ Flask.errorhandler when an exception wasn't correctly handled """
        if __debug__:
            logger.exception(exception)
        log.critical(
            'Unhandled exception when processing endpoint request',
            exc_info=True,
            exception=str(exception),
        )
        return api_response(wrap_in_fail_result(str(exception)), HTTPStatus.INTERNAL_SERVER_ERROR)

    @staticmethod
    def before_request_callback() -> None:
        """Function that runs before each request"""
        log.debug(
            f'start rotki api {request.method} {request.path}',
            view_args=request.view_args,
            query_string=request.query_string,
        )

    @staticmethod
    def after_request_callback(response: Response) -> Response:
        """Function that runs after each completed request

        Logs the response if required. This is determined by the
        fake header rotki-log-result passed to all responses.
        """
        if response.headers.pop('rotki-log-result', 'True') == 'True':
            result = response.json
        else:
            result = 'redacted'

        log.debug(
            f'end rotki api {request.method} {request.path}',
            view_args=request.view_args,
            query_string=request.query_string,
            status_code=response.status_code,
            result=result,
        )
        return response

    def run(self, host: str = '127.0.0.1', port: int = 5042, **kwargs: Any) -> None:
        """This is only used for the data faker and not used in production"""
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(
            self,
            host: str = '127.0.0.1',
            rest_port: int = 5042,
    ) -> None:
        """This is used to start the API server in production"""
        wsgi_logger = logging.getLogger(__name__ + '.pywsgi')
        self.wsgiserver = WSGIServer(
            listener=(host, rest_port),
            application=WebsocketResource([
                ('^/ws', RotkiWSApp),
                ('^/', self.flask_app),
            ]),
            log=None,
            handler_class=WebSocketHandler,
            environ={'rotki_notifier': self.rotki_notifier},
            error_log=wsgi_logger,
        )
        # this is to prevent littering logs with geventwebsocket upgrade messages
        logging.getLogger('geventwebsocket.handler').setLevel(logging.ERROR)

        if 'pytest' not in sys.modules:  # do not check
            if __debug__:
                msg = 'rotki is running in __debug__ mode'
                print(msg)
                log.info(msg)
            msg = f'rotki REST API server is running at: {host}:{rest_port} with loglevel {logging.getLevelName(logging.root.level)}'  # noqa: E501
            print(msg)
            log.info(msg)
        self.wsgiserver.start()

    def stop(self, timeout: int = 5) -> None:
        """Stops the API server. If handlers are running after timeout they are killed"""
        if self.wsgiserver is not None:
            self.wsgiserver.stop(timeout)
            self.wsgiserver = None

        self.rest_api.stop()
