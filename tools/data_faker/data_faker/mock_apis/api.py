import json
import logging
from http import HTTPStatus

from data_faker.mock_apis.resources import (
    KrakenAssetPairsResource,
    KrakenBalanceResource,
    KrakenLedgersResource,
    KrakenTickerResource,
    KrakenTradesHistoryResource,
    create_blueprint,
)
from flask import Flask, make_response
from flask_restful import Api
from gevent.pywsgi import WSGIServer

logger = logging.getLogger(__name__)

URLS = [
    ('/kraken/mock/public/Ticker', KrakenTickerResource),
    ('/kraken/mock/public/AssetPairs', KrakenAssetPairsResource),
    ('/kraken/mock/private/Balance', KrakenBalanceResource),
    ('/kraken/mock/private/TradesHistory', KrakenTradesHistoryResource),
    ('/kraken/mock/private/Ledgers', KrakenLedgersResource),
]

ERROR_STATUS_CODES = [
    HTTPStatus.CONFLICT,
    HTTPStatus.REQUEST_TIMEOUT,
    HTTPStatus.PAYMENT_REQUIRED,
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.NOT_FOUND,
    HTTPStatus.UNAUTHORIZED,
]


def api_error(error, status_code):
    assert status_code in ERROR_STATUS_CODES, 'Programming error, unexpected error status code'
    response = make_response((
        json.dumps(dict(error=error)),
        status_code,
        {'mimetype': 'application/json', 'Content-Type': 'application/json'},
    ))
    return response


def endpoint_not_found(e):
    return api_error('invalid endpoint', HTTPStatus.NOT_FOUND)


def restapi_setup_urls(flask_api_context, rest_api, urls):
    for route, resource_cls in urls:
        flask_api_context.add_resource(
            resource_cls,
            route,
            resource_class_kwargs={'rest_api_object': rest_api},
        )


class APIServer(object):

    def __init__(self, rest_api):
        flask_app = Flask(__name__)
        blueprint = create_blueprint()
        flask_api_context = Api(blueprint)

        restapi_setup_urls(
            flask_api_context,
            rest_api,
            URLS,
        )

        self.rest_api = rest_api
        self.flask_app = flask_app
        self.blueprint = blueprint
        self.flask_api_context = flask_api_context

        self.wsgiserver = None
        self.flask_app.register_blueprint(self.blueprint)

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)

    def run(self, host='127.0.0.1', port=5001, **kwargs):
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(self, host='127.0.0.1', port=5001):
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


class RestAPI(object):
    def __init__(self, fake_kraken):
        self.kraken = fake_kraken

    def kraken_ticker(self):
        return self.kraken.query_ticker()

    def kraken_asset_pairs(self):
        return self.kraken.query_asset_pairs()

    def kraken_balances(self):
        return self.kraken.query_balances()

    def kraken_trade_history(self):
        return self.kraken.query_trade_history()

    def kraken_ledgers(self):
        return self.kraken.query_ledgers()
