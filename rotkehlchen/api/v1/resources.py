from pathlib import Path
from typing import Dict, List, Optional

from flask import Blueprint, Response
from flask_restful import Resource
from typing_extensions import Literal
from webargs.flaskparser import use_kwargs

from rotkehlchen.api.v1.encoding import (
    AllBalancesQuerySchema,
    AsyncTasksQuerySchema,
    BlockchainBalanceQuerySchema,
    BlockchainsAccountsSchema,
    DataImportSchema,
    EthTokensSchema,
    ExchangeBalanceQuerySchema,
    ExchangesResourceAddSchema,
    ExchangesResourceRemoveSchema,
    ExchangeTradesQuerySchema,
    FiatBalancesSchema,
    FiatExchangeRatesSchema,
    HistoryExportingSchema,
    HistoryProcessingSchema,
    IgnoredAssetsSchema,
    ModifiableSettingsSchema,
    NewUserSchema,
    StatisticsAssetBalanceSchema,
    StatisticsValueDistributionSchema,
    TradeDeleteSchema,
    TradePatchSchema,
    TradeSchema,
    TradesQuerySchema,
    UserActionSchema,
)
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    BlockchainAddress,
    Fee,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradePair,
    TradeType,
)


def create_blueprint():
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint("v1_resources", __name__)


class BaseResource(Resource):
    def __init__(self, rest_api_object, **kwargs):
        super().__init__(**kwargs)
        self.rest_api = rest_api_object


class SettingsResource(BaseResource):

    put_schema = ModifiableSettingsSchema()

    @use_kwargs(put_schema, locations=('json',))
    def put(
            self,
            premium_should_sync: Optional[bool],
            include_crypto2crypto: Optional[bool],
            anonymized_logs: Optional[bool],
            ui_floating_precision: Optional[int],
            taxfree_after_period: Optional[int],
            balance_save_frequency: Optional[int],
            include_gas_costs: Optional[bool],
            historical_data_start: Optional[str],
            eth_rpc_endpoint: Optional[str],
            main_currency: Optional[Asset],
            date_display_format: Optional[str],
    ) -> Response:
        settings = ModifiableDBSettings(
            premium_should_sync=premium_should_sync,
            include_crypto2crypto=include_crypto2crypto,
            anonymized_logs=anonymized_logs,
            ui_floating_precision=ui_floating_precision,
            taxfree_after_period=taxfree_after_period,
            balance_save_frequency=balance_save_frequency,
            include_gas_costs=include_gas_costs,
            historical_data_start=historical_data_start,
            eth_rpc_endpoint=eth_rpc_endpoint,
            main_currency=main_currency,
            date_display_format=date_display_format,
        )
        return self.rest_api.set_settings(settings)

    def get(self) -> Response:
        return self.rest_api.get_settings()


class AsyncTasksResource(BaseResource):

    get_schema = AsyncTasksQuerySchema()

    @use_kwargs(get_schema, locations=('view_args',))
    def get(self, task_id: Optional[int]) -> Response:
        return self.rest_api.query_tasks_outcome(task_id=task_id)


class FiatExchangeRatesResource(BaseResource):

    get_schema = FiatExchangeRatesSchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(self, currencies: Optional[List[Asset]]) -> Response:
        return self.rest_api.get_fiat_exchange_rates(currencies=currencies)


class ExchangesResource(BaseResource):

    put_schema = ExchangesResourceAddSchema()
    delete_schema = ExchangesResourceRemoveSchema()

    def get(self) -> Response:
        return self.rest_api.get_exchanges()

    @use_kwargs(put_schema, locations=('json',))
    def put(self, name: str, api_key: ApiKey, api_secret: ApiSecret) -> Response:
        return self.rest_api.setup_exchange(name, api_key, api_secret)

    @use_kwargs(delete_schema, locations=('json',))
    def delete(self, name: str) -> Response:
        return self.rest_api.remove_exchange(name=name)


class AllBalancesResource(BaseResource):

    get_schema = AllBalancesQuerySchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(self, save_data: bool, async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.query_all_balances(
            save_data=save_data,
            async_query=async_query,
            ignore_cache=ignore_cache,
        )


class ExchangeBalancesResource(BaseResource):

    get_schema = ExchangeBalanceQuerySchema()

    @use_kwargs(get_schema, locations=('json', 'view_args', 'query'))
    def get(self, name: Optional[str], async_query: bool, ignore_cache: bool) -> Response:
        return self.rest_api.query_exchange_balances(
            name=name,
            async_query=async_query,
            ignore_cache=ignore_cache,
        )


class OwnedAssetsResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.query_owned_assets()


class ExchangeTradesResource(BaseResource):

    get_schema = ExchangeTradesQuerySchema()

    @use_kwargs(get_schema, locations=('json', 'view_args', 'query'))
    def get(
            self,
            name: Optional[str],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        return self.rest_api.query_exchange_trades(
            name=name,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            async_query=async_query,
        )


class BlockchainBalancesResource(BaseResource):

    get_schema = BlockchainBalanceQuerySchema()

    @use_kwargs(get_schema, locations=('json', 'view_args', 'query'))
    def get(
            self,
            blockchain: Optional[SupportedBlockchain],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        return self.rest_api.query_blockchain_balances(
            blockchain=blockchain,
            async_query=async_query,
            ignore_cache=ignore_cache,
        )


class FiatBalancesResource(BaseResource):

    patch_schema = FiatBalancesSchema()

    def get(self) -> Response:
        return self.rest_api.query_fiat_balances()

    @use_kwargs(patch_schema, locations=('json',))
    def patch(self, balances: Dict[Asset, AssetAmount]) -> Response:
        # The passsed assets are guaranteed to be FIAT assets thanks to marshmallow
        return self.rest_api.set_fiat_balances(balances)


class TradesResource(BaseResource):

    get_schema = TradesQuerySchema()
    put_schema = TradeSchema()
    patch_schema = TradePatchSchema()
    delete_schema = TradeDeleteSchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            location: Optional[Location],
    ) -> Response:
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
            pair: TradePair,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> Response:
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
            location: Location,
            pair: TradePair,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> Response:
        return self.rest_api.edit_trade(
            trade_id=trade_id,
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

    @use_kwargs(delete_schema, locations=('json',))
    def delete(self, trade_id: str) -> Response:
        return self.rest_api.delete_trade(trade_id=trade_id)


class UsersResource(BaseResource):

    put_schema = NewUserSchema()

    def get(self) -> Response:
        return self.rest_api.get_users()

    @use_kwargs(put_schema, locations=('json',))
    def put(
            self,
            name: str,
            password: str,
            sync_approval: str,
            premium_api_key: str,
            premium_api_secret: str,
    ) -> Response:
        return self.rest_api.create_new_user(
            name=name,
            password=password,
            sync_approval=sync_approval,
            premium_api_key=premium_api_key,
            premium_api_secret=premium_api_secret,
        )


class UsersByNameResource(BaseResource):
    patch_schema = UserActionSchema()

    @use_kwargs(patch_schema, locations=('json', 'view_args'))
    def patch(
            self,
            action: Optional[str],
            name: str,
            password: Optional[str],
            sync_approval: str,
            premium_api_key: str,
            premium_api_secret: str,
    ) -> Response:
        if action is None:
            return self.rest_api.user_set_premium_credentials(
                name=name,
                api_key=premium_api_key,
                api_secret=premium_api_secret,
            )

        if action == 'login':
            assert password is not None, 'Marshmallow validation should not let password=None here'
            return self.rest_api.user_login(
                name=name,
                password=password,
                sync_approval=sync_approval,
            )
        else:  # Can only be logout -- checked by marshmallow
            return self.rest_api.user_logout(name=name)


class StatisticsNetvalueResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.query_netvalue_data()


class StatisticsAssetBalanceResource(BaseResource):

    get_schema = StatisticsAssetBalanceSchema()

    @use_kwargs(get_schema, locations=('json', 'view_args', 'query'))
    def get(
            self,
            asset: Asset,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self.rest_api.query_timed_balances_data(
            asset=asset,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


class StatisticsValueDistributionResource(BaseResource):

    get_schema = StatisticsValueDistributionSchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(self, distribution_by: str) -> Response:
        return self.rest_api.query_value_distribution_data(
            distribution_by=distribution_by,
        )


class StatisticsRendererResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.query_statistics_renderer()


class MessagesResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.get_messages()


class HistoryProcessingResource(BaseResource):

    get_schema = HistoryProcessingSchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        return self.rest_api.process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            async_query=async_query,
        )


class HistoryExportingResource(BaseResource):

    get_schema = HistoryExportingSchema()

    @use_kwargs(get_schema, locations=('json', 'query'))
    def get(self, directory_path: Path) -> Response:
        return self.rest_api.export_processed_history_csv(directory_path=directory_path)


class PeriodicDataResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.query_periodic_data()


class EthereumTokensResource(BaseResource):

    modify_schema = EthTokensSchema()

    def get(self) -> Response:
        return self.rest_api.get_eth_tokens()

    @use_kwargs(modify_schema, locations=('json',))
    def put(
            self,
            eth_tokens: List[EthereumToken],
            async_query: bool,
    ) -> Response:
        return self.rest_api.add_owned_eth_tokens(tokens=eth_tokens, async_query=async_query)

    @use_kwargs(modify_schema, locations=('json',))
    def delete(
            self,
            eth_tokens: List[EthereumToken],
            async_query: bool,
    ) -> Response:
        return self.rest_api.remove_owned_eth_tokens(tokens=eth_tokens, async_query=async_query)


class BlockchainsAccountsResource(BaseResource):

    modify_schema = BlockchainsAccountsSchema()

    @use_kwargs(modify_schema, locations=('json', 'view_args'))
    def put(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
            async_query: bool,
    ) -> Response:
        return self.rest_api.add_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            async_query=async_query,
        )

    @use_kwargs(modify_schema, locations=('json', 'view_args'))
    def delete(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
            async_query: bool,
    ) -> Response:
        return self.rest_api.remove_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            async_query=async_query,
        )


class IgnoredAssetsResource(BaseResource):

    modify_schema = IgnoredAssetsSchema()

    def get(self) -> Response:
        return self.rest_api.get_ignored_assets()

    @use_kwargs(modify_schema, locations=('json',))
    def put(self, assets: List[Asset]) -> Response:
        return self.rest_api.add_ignored_assets(assets=assets)

    @use_kwargs(modify_schema, locations=('json',))
    def delete(self, assets: List[Asset]) -> Response:
        return self.rest_api.remove_ignored_assets(assets=assets)


class VersionResource(BaseResource):

    def get(self) -> Response:
        return self.rest_api.version_check()


class DataImportResource(BaseResource):

    put_schema = DataImportSchema()

    @use_kwargs(put_schema, locations=('json',))
    def put(self, source: Literal['cointracking.info'], filepath: Path) -> None:
        return self.rest_api.import_data(source=source, filepath=filepath)
