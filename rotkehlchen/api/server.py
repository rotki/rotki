import json
import logging
import sys
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple, Type, Union

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
    AdexBalancesResource,
    AdexHistoryResource,
    AllAssetsResource,
    AllBalancesResource,
    AllNamesResource,
    AssetIconsResource,
    AssetMovementsResource,
    AssetsReplaceResource,
    AssetsTypesResource,
    AssetUpdatesResource,
    AssociatedLocations,
    AsyncTasksResource,
    AvalancheTransactionsResource,
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
    CounterpartiesResource,
    CurrentAssetsPriceResource,
    DatabaseBackupsResource,
    DatabaseInfoResource,
    DataImportResource,
    DBSnapshotsResource,
    DefiBalancesResource,
    ERC20TokenInfo,
    ERC20TokenInfoAVAX,
    Eth2DailyStatsResource,
    Eth2StakeDepositsResource,
    Eth2StakeDetailsResource,
    Eth2ValidatorsResource,
    EthereumAirdropsResource,
    EthereumAssetsResource,
    EthereumModuleDataResource,
    EthereumModuleResource,
    EthereumNodesResource,
    EthereumTransactionsResource,
    ExchangeBalancesResource,
    ExchangeRatesResource,
    ExchangesDataResource,
    ExchangesResource,
    ExternalServicesResource,
    HistoricalAssetsPriceResource,
    HistoryActionableItemsResource,
    HistoryBaseEntryResource,
    HistoryDownloadingResource,
    HistoryExportingResource,
    HistoryProcessingDebugResource,
    HistoryProcessingResource,
    HistoryStatusResource,
    IgnoredActionsResource,
    IgnoredAssetsResource,
    InfoResource,
    LedgerActionsResource,
    LiquityStakingHistoryResource,
    LiquityStakingResource,
    LiquityTrovesHistoryResource,
    LiquityTrovesResource,
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
    NFTSResource,
    OraclesResource,
    OwnedAssetsResource,
    PeriodicDataResource,
    PickleDillResource,
    PingResource,
    QueriedAddressesResource,
    ReverseEnsResource,
    SettingsResource,
    StakingResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    SushiswapBalancesResource,
    SushiswapEventsHistoryResource,
    SushiswapTradesHistoryResource,
    TagsResource,
    TradesResource,
    UniswapBalancesResource,
    UniswapEventsHistoryResource,
    UniswapTradesHistoryResource,
    UniswapV3BalancesResource,
    UserAssetsResource,
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
        Tuple[str, Type[MethodView]],
        Tuple[str, Type[MethodView], str],
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
    ('/history/debug', HistoryProcessingDebugResource),
    ('/history/status', HistoryStatusResource),
    ('/history/export/', HistoryExportingResource),
    ('/history/download/', HistoryDownloadingResource),
    ('/history/events', HistoryBaseEntryResource),
    ('/history/actionable_items', HistoryActionableItemsResource),
    ('/reports/', AccountingReportsResource),
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
    ('/blockchains/ETH/transactions', EthereumTransactionsResource),
    (
        '/blockchains/ETH/transactions/<string:address>',
        EthereumTransactionsResource,
        'per_address_ethereum_transactions_resource',
    ),
    ('/blockchains/ETH2/validators', Eth2ValidatorsResource),
    ('/blockchains/ETH2/stake/deposits', Eth2StakeDepositsResource),
    ('/blockchains/ETH2/stake/details', Eth2StakeDetailsResource),
    ('/blockchains/ETH2/stake/dailystats', Eth2DailyStatsResource),
    ('/blockchains/ETH/defi', DefiBalancesResource),
    ('/blockchains/ETH/airdrops', EthereumAirdropsResource),
    ('/blockchains/ETH/erc20details/', ERC20TokenInfo),
    ('/blockchains/ETH/modules/<string:module_name>/data', NamedEthereumModuleDataResource),
    ('/blockchains/ETH/modules/data', EthereumModuleDataResource),
    ('/blockchains/ETH/modules/data/counterparties', CounterpartiesResource),
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
    ('/blockchains/ETH/modules/uniswap/v2/balances', UniswapBalancesResource),
    ('/blockchains/ETH/modules/uniswap/v3/balances', UniswapV3BalancesResource),
    ('/blockchains/ETH/modules/uniswap/history/events', UniswapEventsHistoryResource),
    ('/blockchains/ETH/modules/uniswap/history/trades', UniswapTradesHistoryResource),
    ('/blockchains/ETH/modules/sushiswap/balances', SushiswapBalancesResource),
    ('/blockchains/ETH/modules/sushiswap/history/events', SushiswapEventsHistoryResource),
    ('/blockchains/ETH/modules/sushiswap/history/trades', SushiswapTradesHistoryResource),
    ('/blockchains/ETH/modules/yearn/vaults/balances', YearnVaultsBalancesResource),
    ('/blockchains/ETH/modules/yearn/vaults/history', YearnVaultsHistoryResource),
    ('/blockchains/ETH/modules/yearn/vaultsv2/balances', YearnVaultsV2BalancesResource),
    ('/blockchains/ETH/modules/yearn/vaultsv2/history', YearnVaultsV2HistoryResource),
    ('/blockchains/ETH/modules/liquity/balances', LiquityTrovesResource),
    ('/blockchains/ETH/modules/liquity/events/trove', LiquityTrovesHistoryResource),
    ('/blockchains/ETH/modules/liquity/events/staking', LiquityStakingHistoryResource),
    ('/blockchains/ETH/modules/liquity/staking', LiquityStakingResource),
    ('/blockchains/ETH/modules/pickle/dill', PickleDillResource),
    ('/blockchains/ETH/modules/loopring/balances', LoopringBalancesResource),
    ('/blochchains/ETH/nodes', EthereumNodesResource),
    ('/blockchains/<string:blockchain>', BlockchainsAccountsResource),
    ('/blockchains/<string:blockchain>/xpub', BTCXpubResource),
    ('/blockchains/AVAX/transactions', AvalancheTransactionsResource),
    (
        '/blockchains/AVAX/transactions/<string:address>',
        AvalancheTransactionsResource,
        'per_address_avalanche_transactions_resource',
    ),
    ('/blockchains/AVAX/erc20details/', ERC20TokenInfoAVAX),
    ('/assets', OwnedAssetsResource),
    ('/assets/types', AssetsTypesResource),
    ('/assets/replace', AssetsReplaceResource),
    ('/assets/all', AllAssetsResource),
    ('/assets/ethereum', EthereumAssetsResource),
    ('/assets/prices/current', CurrentAssetsPriceResource),
    ('/assets/prices/historical', HistoricalAssetsPriceResource),
    ('/assets/ignored', IgnoredAssetsResource),
    ('/assets/updates', AssetUpdatesResource),
    ('/assets/user', UserAssetsResource),
    ('/actions/ignored', IgnoredActionsResource),
    ('/info', InfoResource),
    ('/ping', PingResource),
    ('/import', DataImportResource),
    ('/nfts', NFTSResource),
    ('/nfts/balances', NFTSBalanceResource),
    ('/database/info', DatabaseInfoResource),
    ('/database/backups', DatabaseBackupsResource),
    ('/locations/associated', AssociatedLocations),
    ('/staking/kraken', StakingResource),
    ('/names', AllNamesResource),
    ('/names/ens/reverse', ReverseEnsResource),
    ('/names/addressbook/<string:book_type>', AddressbookResource),
    ('/snapshots', DBSnapshotsResource),
    (
        '/snapshots/<int:timestamp>',
        DBSnapshotsResource,
        'per_timestamp_db_snapshots_resource',
    ),
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
            raise ValueError(f"Invalid URL format: {url_tuple!r}")
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

    err_response = jsonify(result=None, message=msg)
    err_response.status_code = HTTPStatus.BAD_REQUEST
    abort(err_response)


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
        self.flask_app.after_request(self.after_request_callback)  # type: ignore

    @staticmethod
    def unhandled_exception(exception: Exception) -> Response:
        """ Flask.errorhandler when an exception wasn't correctly handled """
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
