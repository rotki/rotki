from flask import Blueprint
from flask_restful import Resource
from webargs.flaskparser import use_kwargs

from .encoding import (
    KrakenAssetPairsSchema,
    KrakenBalanceSchema,
    KrakenLedgersSchema,
    KrakenTickerSchema,
    KrakenTradesHistorySchema,
)


def create_blueprint():
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint('v1_resources', __name__)


class BaseResource(Resource):
    def __init__(self, rest_api_object, **kwargs):
        super().__init__(**kwargs)
        self.rest_api = rest_api_object


class KrakenTickerResource(BaseResource):

    @use_kwargs(KrakenTickerSchema)
    def get(self, **kwargs):
        return self.rest_api.kraken_ticker()

    @use_kwargs(KrakenTickerSchema)
    def post(self, **kwargs):
        return self.rest_api.kraken_ticker()


class KrakenAssetPairsResource(BaseResource):

    get_schema = KrakenAssetPairsSchema

    @use_kwargs(KrakenAssetPairsSchema)
    def get(self, **kwargs):
        return self.rest_api.kraken_asset_pairs()

    @use_kwargs(KrakenAssetPairsSchema)
    def post(self, **kwargs):
        return self.rest_api.kraken_asset_pairs()


class KrakenBalanceResource(BaseResource):

    @use_kwargs(KrakenBalanceSchema)
    def get(self, **kwargs):
        return self.rest_api.kraken_balances()

    @use_kwargs(KrakenBalanceSchema)
    def post(self, **kwargs):
        return self.rest_api.kraken_balances()


class KrakenTradesHistoryResource(BaseResource):

    @use_kwargs(KrakenTradesHistorySchema)
    def get(self, **kwargs):
        return self.rest_api.kraken_trade_history()

    @use_kwargs(KrakenTradesHistorySchema)
    def post(self, **kwargs):
        return self.rest_api.kraken_trade_history()


class KrakenLedgersResource(BaseResource):

    @use_kwargs(KrakenLedgersSchema)
    def get(self, **kwargs):
        return self.rest_api.kraken_ledgers()

    @use_kwargs(KrakenLedgersSchema)
    def post(self, **kwargs):
        return self.rest_api.kraken_ledgers()
