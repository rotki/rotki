from flask import Blueprint
from flask_restful import Resource
from webargs.flaskparser import use_kwargs

from .encoding import KrakenTickerSchema


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

    get_schema = KrakenTickerSchema

    @use_kwargs(get_schema)
    def get(self, **kwargs):
        return self.rest_api.kraken_ticker()
