from typing import Any, Dict, List

from flask import Blueprint, response_class
from flask_restful import Resource

from rotkehlchen.api.v1.encoding import x


def create_blueprint():
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint("v1_resources", __name__)


class BaseResource(Resource):
    def __init__(self, rest_api_object, **kwargs):
        super().__init__(**kwargs)
        self.rest_api = rest_api_object


class LogoutResource(BaseResource):
    def get(self) -> response_class:
        return self.rest_api.logout()


class SettingsResource(BaseResource):

    def put(self, settings: Dict[str, Any]) -> response_class:
        return self.rest_api.set_settings(settings)

    def get(self) -> response_class:
        return self.rest_api.get_settings()


class TaskOutcomeResource(BaseResource):

    def get(self, task_id: int) -> response_class:
        return self.rest_api.query_task_outcome(task_id=task_id)


class FiatExchangeRatesResource(BaseResource):

    def get(self, currencies: List[str]) -> response_class:
        return self.rest_api.get_fiat_exchange_rates(currencies=currencies)


class ExchangeResource(BaseResource):

    def put(self, name: str, api_key: str, api_secret: str) -> response_class:
        return self.rest_api.setup_exchange(name, api_key, api_secret)

    def delete(self, name: str) -> response_class:
        return self.rest_api.remove_exchange(name=name)
