import json
import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple, Union

import werkzeug
from flask import Flask, Response
from flask_cors import CORS
from flask_restful import Api, Resource, abort
from gevent.pywsgi import WSGIServer
from geventwebsocket import Resource as WebsocketResource, WebSocketServer
from marshmallow import Schema
from marshmallow.exceptions import ValidationError
from webargs.flaskparser import parser
from werkzeug.exceptions import NotFound

from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.v1.parser import resource_parser
from rotkehlchen.api.v1.resources import (
    AaveBalancesResource,
    AaveHistoryResource,
    AdexBalancesResource,
    AdexHistoryResource,
    AllAssetsResource,
    AllBalancesResource,
    AssetIconsResource,
    AssetMovementsResource,
    AssetsReplaceResource,
    AssetsTypesResource,
    AssetUpdatesResource,
    AsyncTasksResource,
    BalancerBalancesResource,
    BalancerEventsHistoryResource,
    BalancerTradesHistoryResource,
    BinanceAvailableMarkets,
    BinanceUserMarkets,
    BlockchainBalancesResource,
    BlockchainsAccountsResource,
    BTCXpubResource,
    CompoundBalancesResource,
    CompoundHistoryResource,
    CurrentAssetsPriceResource,
    DataImportResource,
    DefiBalancesResource,
    ERC20TokenInfo,
    Eth2StakeDepositsResource,
    Eth2StakeDetailsResource,
    EthereumAirdropsResource,
    EthereumAssetsResource,
    EthereumModuleDataResource,
    EthereumModuleResource,
    EthereumTransactionsResource,
    ExchangeBalancesResource,
    ExchangeRatesResource,
    ExchangesDataResource,
    ExchangesResource,
    ExternalServicesResource,
    GitcoinEventsResource,
    GitcoinReportResource,
    HistoricalAssetsPriceResource,
    HistoryDownloadingResource,
    HistoryExportingResource,
    HistoryProcessingResource,
    HistoryStatusResource,
    IgnoredActionsResource,
    IgnoredAssetsResource,
    InfoResource,
    LedgerActionsResource,
    LoopringBalancesResource,
    MakerdaoDSRBalanceResource,
    MakerdaoDSRHistoryResource,
    MakerdaoVaultDetailsResource,
    MakerdaoVaultsResource,
    ManuallyTrackedBalancesResource,
    MessagesResource,
    NamedEthereumModuleDataResource,
    NamedOracleCacheResource,
    OraclesResource,
    OwnedAssetsResource,
    PeriodicDataResource,
    PingResource,
    QueriedAddressesResource,
    SettingsResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    TagsResource,
    TradesResource,
    UniswapBalancesResource,
    UniswapEventsHistoryResource,
    UniswapTradesHistoryResource,
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

URLS = List[
    Union[
        Tuple[str, Resource],
        Tuple[str, Resource, str],
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
    ('/tasks/', AsyncTasksResource),
    ('/tasks/<int:task_id>', AsyncTasksResource, 'specific_async_tasks_resource'),
    ('/exchange_rates', ExchangeRatesResource),
    ('/external_services/', ExternalServicesResource),
    ('/oracles', OraclesResource),
    ('/oracles/<string:oracle>/cache', NamedOracleCacheResource),
    ('/exchanges', ExchangesResource),
    ('/exchanges/balances', ExchangeBalancesResource),
    (
        '/exchanges/balances/<string:location>',
        ExchangeBalancesResource,
        'named_exchanges_balances_resource',
    ),
    ('/assets/<string:asset>/icon', AssetIconsResource),
    ('/trades', TradesResource),
    ('/ledgeractions', LedgerActionsResource),
    ('/asset_movements', AssetMovementsResource),
    ('/tags', TagsResource),
    ('/exchanges/binance/pairs', BinanceAvailableMarkets),
    ('/exchanges/binance/pairs/<string:name>', BinanceUserMarkets),
    ('/exchanges/data/', ExchangesDataResource),
    ('/exchanges/data/<string:location>', ExchangesDataResource, 'named_exchanges_data_resource'),
    ('/balances/blockchains', BlockchainBalancesResource),
    (
        '/balances/blockchains/<string:blockchain>',
        BlockchainBalancesResource,
        'named_blockchain_balances_resource',
    ),
    ('/balances/', AllBalancesResource),
    ('/balances/manual', ManuallyTrackedBalancesResource),
    ('/statistics/netvalue', StatisticsNetvalueResource),
    ('/statistics/balance/<string:asset>', StatisticsAssetBalanceResource),
    ('/statistics/value_distribution', StatisticsValueDistributionResource),
    ('/statistics/renderer', StatisticsRendererResource),
    ('/messages/', MessagesResource),
    ('/periodic/', PeriodicDataResource),
    ('/history/', HistoryProcessingResource),
    ('/history/status', HistoryStatusResource),
    ('/history/export/', HistoryExportingResource),
    ('/history/download/', HistoryDownloadingResource),
    ('/queried_addresses', QueriedAddressesResource),
    ('/blockchains/ETH/transactions', EthereumTransactionsResource),
    (
        '/blockchains/ETH/transactions/<string:address>',
        EthereumTransactionsResource,
        'per_address_ethereum_transactions_resource',
    ),
    ('/blockchains/ETH2/stake/deposits', Eth2StakeDepositsResource),
    ('/blockchains/ETH2/stake/details', Eth2StakeDetailsResource),
    ('/blockchains/ETH/defi', DefiBalancesResource),
    ('/blockchains/ETH/airdrops', EthereumAirdropsResource),
    ('/blockchains/ETH/erc20details/', ERC20TokenInfo),
    ('/blockchains/ETH/modules/<string:module_name>/data', NamedEthereumModuleDataResource),
    ('/blockchains/ETH/modules/data', EthereumModuleDataResource),
    ('/blockchains/ETH/modules/', EthereumModuleResource),
    ('/blockchains/ETH/modules/makerdao/dsrbalance', MakerdaoDSRBalanceResource),
    ('/blockchains/ETH/modules/makerdao/dsrhistory', MakerdaoDSRHistoryResource),
    ('/blockchains/ETH/modules/makerdao/vaults', MakerdaoVaultsResource),
    ('/blockchains/ETH/modules/makerdao/vaultdetails', MakerdaoVaultDetailsResource),
    ('/blockchains/ETH/modules/aave/balances', AaveBalancesResource),
    ('/blockchains/ETH/modules/aave/history', AaveHistoryResource),
    ('/blockchains/ETH/modules/adex/balances', AdexBalancesResource),
    ('/blockchains/ETH/modules/adex/history', AdexHistoryResource),
    ('/blockchains/ETH/modules/balancer/balances', BalancerBalancesResource),
    ('/blockchains/ETH/modules/balancer/history/trades', BalancerTradesHistoryResource),
    ('/blockchains/ETH/modules/balancer/history/events', BalancerEventsHistoryResource),
    ('/blockchains/ETH/modules/compound/balances', CompoundBalancesResource),
    ('/blockchains/ETH/modules/compound/history', CompoundHistoryResource),
    ('/blockchains/ETH/modules/uniswap/balances', UniswapBalancesResource),
    ('/blockchains/ETH/modules/uniswap/history/events', UniswapEventsHistoryResource),
    ('/blockchains/ETH/modules/uniswap/history/trades', UniswapTradesHistoryResource),
    ('/blockchains/ETH/modules/yearn/vaults/balances', YearnVaultsBalancesResource),
    ('/blockchains/ETH/modules/yearn/vaults/history', YearnVaultsHistoryResource),
    ('/blockchains/ETH/modules/yearn/vaultsv2/balances', YearnVaultsV2BalancesResource),
    ('/blockchains/ETH/modules/yearn/vaultsv2/history', YearnVaultsV2HistoryResource),
    ('/blockchains/ETH/modules/loopring/balances', LoopringBalancesResource),
    ('/blockchains/<string:blockchain>', BlockchainsAccountsResource),
    ('/blockchains/BTC/xpub', BTCXpubResource),
    ('/assets', OwnedAssetsResource),
    ('/assets/types', AssetsTypesResource),
    ('/assets/replace', AssetsReplaceResource),
    ('/assets/all', AllAssetsResource),
    ('/assets/ethereum', EthereumAssetsResource),
    ('/assets/prices/current', CurrentAssetsPriceResource),
    ('/assets/prices/historical', HistoricalAssetsPriceResource),
    ('/assets/ignored', IgnoredAssetsResource),
    ('/assets/updates', AssetUpdatesResource),
    ('/actions/ignored', IgnoredActionsResource),
    ('/info', InfoResource),
    ('/ping', PingResource),
    ('/import', DataImportResource),
    ('/gitcoin/events', GitcoinEventsResource),
    ('/gitcoin/report', GitcoinReportResource),
]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def setup_urls(
        flask_api_context: Api,
        rest_api: RestAPI,
        urls: URLS,
) -> None:
    for url_tuple in urls:
        if len(url_tuple) == 2:
            route, resource_cls = url_tuple  # type: ignore
            endpoint = resource_cls.__name__.lower()
        elif len(url_tuple) == 3:
            route, resource_cls, endpoint = url_tuple  # type: ignore
        else:
            raise ValueError(f"Invalid URL format: {url_tuple!r}")
        flask_api_context.add_resource(
            resource_cls,
            route,
            resource_class_kwargs={"rest_api_object": rest_api},
            endpoint=endpoint,
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
def handle_request_parsing_error(
        err: ValidationError,
        _request: werkzeug.local.LocalProxy,
        _schema: Schema,
        error_status_code: Optional[int],  # pylint: disable=unused-argument
        error_headers: Optional[Dict],  # pylint: disable=unused-argument
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

    abort(HTTPStatus.BAD_REQUEST, result=None, message=msg)


class APIServer():

    _api_prefix = '/api/1'

    def __init__(
            self,
            rest_api: RestAPI,
            ws_notifier: RotkiNotifier,
            cors_domain_list: List[str] = None,
    ) -> None:
        flask_app = Flask(__name__)
        if cors_domain_list:
            CORS(flask_app, origins=cors_domain_list)
        blueprint = create_blueprint()
        flask_api_context = Api(blueprint, prefix=self._api_prefix)
        setup_urls(
            flask_api_context=flask_api_context,
            rest_api=rest_api,
            urls=URLS_V1,
        )

        self.rest_api = rest_api
        self.rotki_notifier = ws_notifier
        self.flask_app = flask_app
        self.blueprint = blueprint

        self.wsgiserver: Optional[WSGIServer] = None
        self.flask_app.register_blueprint(self.blueprint)
        self.ws_server: Optional[WebSocketServer] = None

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)
        self.flask_app.register_error_handler(Exception, self.unhandled_exception)

    @staticmethod
    def unhandled_exception(exception: Exception) -> Response:
        """ Flask.errorhandler when an exception wasn't correctly handled """
        log.critical(
            "Unhandled exception when processing endpoint request",
            exc_info=True,
        )
        return api_response(wrap_in_fail_result(str(exception)), HTTPStatus.INTERNAL_SERVER_ERROR)

    def run(self, host: str = '127.0.0.1', port: int = 5042, **kwargs: Any) -> None:
        """This is only used for the data faker and not used in production"""
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(
            self,
            host: str = '127.0.0.1',
            rest_port: int = 5042,
            websockets_port: int = 5043,
    ) -> None:
        """This is used to start the API server in production"""
        wsgi_logger = logging.getLogger(__name__ + '.pywsgi')
        self.wsgiserver = WSGIServer(
            listener=(host, rest_port),
            application=self.flask_app,
            log=wsgi_logger,
            error_log=wsgi_logger,
        )
        msg = f'rotki REST API server is running at: {host}:{rest_port}'
        print(msg)
        log.info(msg)
        self.wsgiserver.start()
        self.ws_server = WebSocketServer(
            listener=(host, websockets_port),
            application=WebsocketResource([
                ('^/', RotkiWSApp),
            ]),
            debug=False,
            environ={'rotki_notifier': self.rotki_notifier},
        )
        msg = f'rotki Websockets API server is running at: {host}:{websockets_port}'
        print(msg)
        log.info(msg)
        self.ws_server.start()

    def stop(self, timeout: int = 5) -> None:
        """Stops the API server. If handlers are running after timeout they are killed"""
        if self.wsgiserver is not None:
            self.wsgiserver.stop(timeout)
            self.wsgiserver = None
        if self.ws_server is not None:
            self.ws_server.stop(timeout)
            self.wsgiserver = None

        self.rest_api.stop()
