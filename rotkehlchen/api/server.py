import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple, Union

import werkzeug
from flask import Flask, Response
from flask_cors import CORS
from flask_restful import Api, Resource, abort
from gevent.pywsgi import WSGIServer
from marshmallow import Schema
from marshmallow.exceptions import ValidationError
from webargs.flaskparser import parser
from werkzeug.exceptions import NotFound

from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.v1.resources import (
    AllBalancesResource,
    AsyncTasksResource,
    BlockchainBalancesResource,
    BlockchainsAccountsResource,
    DataImportResource,
    EthereumTokensResource,
    ExchangeBalancesResource,
    ExchangesResource,
    ExchangeTradesResource,
    FiatBalancesResource,
    FiatExchangeRatesResource,
    HistoryExportingResource,
    HistoryProcessingResource,
    IgnoredAssetsResource,
    MessagesResource,
    OwnedAssetsResource,
    PeriodicDataResource,
    SettingsResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    TradesResource,
    UsersByNameResource,
    UsersResource,
    VersionResource,
    create_blueprint,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

URLS = List[
    Union[
        Tuple[str, Resource],
        Tuple[str, Resource, str],
    ]
]


URLS_V1: URLS = [
    ('/users', UsersResource),
    ('/users/<string:name>', UsersByNameResource),
    ('/settings', SettingsResource),
    ('/tasks/', AsyncTasksResource),
    ('/tasks/<int:task_id>', AsyncTasksResource, 'specific_async_tasks_resource'),
    ('/fiat_exchange_rates', FiatExchangeRatesResource),
    ('/exchanges', ExchangesResource),
    ('/exchanges/balances', ExchangeBalancesResource),
    (
        '/exchanges/balances/<string:name>',
        ExchangeBalancesResource,
        'named_exchanges_balances_resource',
    ),
    ('/trades', TradesResource),
    ('/exchanges/trades/', ExchangeTradesResource),
    ('/exchanges/trades/<string:name>', ExchangeTradesResource, 'named_exchanges_trades_resource'),
    ('/balances/blockchains', BlockchainBalancesResource),
    (
        '/balances/blockchains/<string:blockchain>',
        BlockchainBalancesResource,
        'named_blockchain_balances_resource',
    ),
    ('/balances/', AllBalancesResource),
    ('/balances/fiat', FiatBalancesResource),
    ('/statistics/netvalue', StatisticsNetvalueResource),
    ('/statistics/balance/<string:asset>', StatisticsAssetBalanceResource),
    ('/statistics/value_distribution', StatisticsValueDistributionResource),
    ('/statistics/renderer', StatisticsRendererResource),
    ('/messages/', MessagesResource),
    ('/periodic/', PeriodicDataResource),
    ('/history/', HistoryProcessingResource),
    ('/history/export/', HistoryExportingResource),
    ('/blockchains/ETH/tokens', EthereumTokensResource),
    ('/blockchains/<string:blockchain>', BlockchainsAccountsResource),
    ('/assets', OwnedAssetsResource),
    ('/assets/ignored', IgnoredAssetsResource),
    ('/version', VersionResource),
    ('/import', DataImportResource),
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
    # The isinstance check is because I am not sure if e is always going to
    # be a "NotFound" error here
    if isinstance(e, NotFound):
        msg = e.description
    return api_response(wrap_in_fail_result(msg), HTTPStatus.NOT_FOUND)


@parser.error_handler
def handle_request_parsing_error(
        err: ValidationError,
        _request: werkzeug.local.LocalProxy,
        _schema: Schema,
        _err_status_code: Optional[int],
        _err_headers: Optional[Dict],
) -> None:
    """ This handles request parsing errors generated for example by schema
    field validation failing."""
    abort(HTTPStatus.BAD_REQUEST, result=None, message=str(err))


class APIServer():

    _api_prefix = '/api/1'

    def __init__(self, rest_api: RestAPI, cors_domain_list: List[str] = None) -> None:
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
        self.flask_app = flask_app
        self.blueprint = blueprint

        self.wsgiserver: Optional[WSGIServer] = None
        self.flask_app.register_blueprint(self.blueprint)

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

    def start(self, host: str = '127.0.0.1', port: int = 5042) -> None:
        """This is used to start the API server in production"""
        wsgi_logger = logging.getLogger(__name__ + '.pywsgi')
        self.wsgiserver = WSGIServer(
            (host, port),
            self.flask_app,
            log=wsgi_logger,
            error_log=wsgi_logger,
        )
        msg = f'Rotki API server is running at: {host}:{port}'
        print(msg)
        log.info(msg)
        self.wsgiserver.start()

    def stop(self, timeout: int = 5) -> None:
        """Stops the API server. If handlers are running after timeout they are killed"""
        if self.wsgiserver is not None:
            self.wsgiserver.stop(timeout)
            self.wsgiserver = None

        self.rest_api.stop()
