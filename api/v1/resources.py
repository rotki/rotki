from typing import Any, Dict, List, Optional

from flask import Blueprint, response_class
from flask_restful import Resource
from webargs.flaskparser import use_kwargs

from rotkehlchen.api.v1.encoding import TradePatchSchema, TradeSchema, TradesQuerySchema
from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import AssetAmount, Fee, Location, Price, Timestamp, TradeType


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


class TradeResource(BaseResource):

    get_schema = TradesQuerySchema()
    put_schema = TradeSchema()
    patch_schema = TradePatchSchema()

    @use_kwargs(get_schema, locations=('json',))
    def get(
            self,
            from_timestamp: Optional[Timestamp],
            to_timestamp: Optional[Timestamp],
            location: Optional[Location],
    ) -> response_class:
        return self.rest_api.get_trades(
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            location=location,
        )

    @use_kwargs(put_schema, locations=('json',))
    def put(
            self,
            timestamp: Timestamp,
            location: Location,
            pair: str,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> response_class:
        return self.rest_api.add_trade(
            timestamp=timestamp,
            location=location,
            pair=pair,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )

    @use_kwargs(patch_schema, locations=('json',))
    def patch(
            self,
            trade_id: str,
            timestamp: Timestamp,
            pair: str,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> response_class:
        return self.rest_api.edit_trade(
            trade_id=trade_id,
            timestamp=timestamp,
            pair=pair,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )

    def delete(self, trade_id: str) -> response_class:
        return self.rest_api.delete_external_trade(trade_id=trade_id)
