
import logging
from http import HTTPStatus
from typing import List, Tuple, Union

from flask import Flask, Response
from flask_restful import Api, Resource, abort
from gevent.pywsgi import WSGIServer
from webargs.flaskparser import parser
from werkzeug.exceptions import NotFound

from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.v1.resources import (
    BlockchainBalancesResource,
    BlockchainsAccountsResource,
    EthereumTokensResource,
    ExchangeBalancesResource,
    ExchangesResource,
    FiatBalancesResource,
    FiatExchangeRatesResource,
    HistoryExportingResource,
    HistoryProcessingResource,
    IgnoredAssetsResource,
    MessagesResource,
    PeriodicDataResource,
    SettingsResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    TaskOutcomeResource,
    TradesResource,
    UsersByNameResource,
    UsersResource,
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
    ('/task_outcome', TaskOutcomeResource),
    ('/fiat_exchange_rates', FiatExchangeRatesResource),
    ('/exchanges', ExchangesResource),
    ('/exchanges/balances>', ExchangeBalancesResource),
    (
        '/exchanges/balances/<string:name>',
        ExchangeBalancesResource,
        'named_exchanges_balances_resource',
    ),
    ('/trades', TradesResource),
    ('/balances/blockchains', BlockchainBalancesResource),
    (
        '/balances/blockchains/<string:name>',
        BlockchainBalancesResource,
        'named_blockchain_balances_resource',
    ),
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
    ('/blockchains/<string:name>', BlockchainsAccountsResource),
    ('/assets/ignored', IgnoredAssetsResource),
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
def handle_request_parsing_error(err, _req, _schema, _err_status_code, _err_headers):
    """ This handles request parsing errors generated for example by schema
    field validation failing."""
    abort(HTTPStatus.BAD_REQUEST, errors=err.messages)


class APIServer():

    _api_prefix = '/api/1'

    def __init__(self, rest_api: RestAPI) -> None:
        flask_app = Flask(__name__)
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
        self.flask_api_context = flask_api_context

        self.wsgiserver = None
        self.flask_app.register_blueprint(self.blueprint)

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)
        self.flask_app.register_error_handler(Exception, self.unhandled_exception)

    @staticmethod
    def unhandled_exception(exception: Exception):
        """ Flask.errorhandler when an exception wasn't correctly handled """
        log.critical(
            "Unhandled exception when processing endpoint request",
            exc_info=True,
        )
        return api_response(wrap_in_fail_result(str(exception)), HTTPStatus.INTERNAL_SERVER_ERROR)

    def run(self, host='127.0.0.1', port=5042, **kwargs):
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(self, host='127.0.0.1', port=5042):
        wsgi_logger = logging.getLogger(__name__ + '.pywsgi')
        self.wsgiserver = WSGIServer(
            (host, port),
            self.flask_app,
            log=wsgi_logger,
            error_log=wsgi_logger,
        )
        self.wsgiserver.start()

    def stop(self, timeout=5):
        if getattr(self, 'wsgiserver', None):
            self.wsgiserver.stop(timeout)
            self.wsgiserver = None

        self.rest_api.stop()
