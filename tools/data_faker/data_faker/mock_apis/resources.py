from flask import Blueprint, request
from flask_restful import Resource
from webargs.flaskparser import use_kwargs

from .encoding import BinanceMyTradesSchema


def create_blueprint() -> Blueprint:
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint('v1_resources', __name__)


class BaseResource(Resource):
    def __init__(self, rest_api_object, **kwargs):
        super().__init__(**kwargs)
        self.rest_api = rest_api_object


class KrakenTickerResource(BaseResource):
    def post(self):
        return self.rest_api.kraken_ticker()


class KrakenAssetPairsResource(BaseResource):
    def post(self):
        return self.rest_api.kraken_asset_pairs()


class KrakenBalanceResource(BaseResource):
    def post(self):
        return self.rest_api.kraken_balances()


class KrakenTradesHistoryResource(BaseResource):
    def post(self):
        return self.rest_api.kraken_trade_history()


class KrakenLedgersResource(BaseResource):

    def post(
            self,
            **kwargs,  # pylint: disable=unused-argument
    ):
        # Not using a marshmallow schema here because no schema worked with
        # the way rotkehlchen queries kraken. Not sure why yet. But one hacky way
        # is to inspect the flask request directly
        content_length = int(request.environ['CONTENT_LENGTH'])
        data = str(request.environ['wsgi.input'].peek(content_length))
        if 'deposit' in data:
            ledger_type = 'deposit'
        elif 'withdrawal' in data:
            ledger_type = 'withdrawal'
        else:
            ledger_type = 'all'
        return self.rest_api.kraken_ledgers(ledger_type=ledger_type)


class BinanceAccountResource(BaseResource):
    def get(self):
        return self.rest_api.binance_account()


class BinanceExchangeInfoResource(BaseResource):
    def get(self):
        return self.rest_api.binance_exchange_info()


class BinanceMyTradesResource(BaseResource):

    @use_kwargs(BinanceMyTradesSchema)
    def get(self, **kwargs):
        return self.rest_api.binance_my_trades(symbol=kwargs['symbol'])
