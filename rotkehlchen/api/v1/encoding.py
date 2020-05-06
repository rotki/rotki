from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

import marshmallow
import webargs
from eth_utils import is_checksum_address
from marshmallow import Schema, fields, post_load, validates_schema
from marshmallow.exceptions import ValidationError
from webargs.compat import MARSHMALLOW_VERSION_INFO

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin import is_valid_btc_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_hex_color_code,
    deserialize_location,
    deserialize_price,
    deserialize_timestamp,
    deserialize_trade_pair,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now


class DelimitedOrNormalList(webargs.fields.DelimitedList):
    """This is equal to DelimitedList in webargs v5.6.0

    Essentially accepting either a delimited string or a list-like object

    We introduce it due to them implementing https://github.com/marshmallow-code/webargs/issues/423
    """

    def __init__(
            self,
            cls_or_instance: Any,
            *,
            _delimiter: Optional[str] = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(cls_or_instance, **kwargs)

    def _deserialize(
            self,
            value: Union[List[str], str],
            attr: str,
            data: Dict[str, Any],
            **kwargs: Any,
    ) -> List[Any]:
        """Adjusting code for _deserialize so that it also works for list-like objects

        Adjusting code from
        https://github.com/marshmallow-code/webargs/blob/dev/src/webargs/fields.py#L71
        so that it uses the list-like detection seen in
        https://github.com/marshmallow-code/webargs/blob/f1ae764973b6492e3c69109060c95240b7cc3d41/src/webargs/fields.py#L69
        which was removed as part of https://github.com/marshmallow-code/webargs/issues/423
        """
        try:
            ret = (
                value
                if marshmallow.utils.is_iterable_but_not_string(value)
                else value.split(self.delimiter)  # type: ignore
            )
        except AttributeError:
            if MARSHMALLOW_VERSION_INFO[0] < 3:
                self.fail("invalid")
            else:
                raise self.make_error("invalid")
        return super(webargs.fields.DelimitedList, self)._deserialize(ret, attr, data, **kwargs)


class TimestampField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Timestamp:
        try:
            timestamp = deserialize_timestamp(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return timestamp


class ColorField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> HexColorCode:
        try:
            color_code = deserialize_hex_color_code(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return color_code


class TaxFreeAfterPeriodField(fields.Field):

    def _deserialize(
            self,
            value: int,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> int:
        try:
            value = int(value)
        except ValueError:
            raise ValidationError(f'{value} is not a valid integer')

        if value < -1:
            raise ValidationError(
                'The taxfree_after_period value can not be negative, except for '
                'the value of -1 to disable the setting',
            )
        if value == 0:
            raise ValidationError('The taxfree_after_period value can not be set to zero')

        return value


class KrakenAccountTypeField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> KrakenAccountType:
        try:
            acc_type = KrakenAccountType.deserialize(value)
        except DeserializationError:
            raise ValidationError(f'{value} is not a valid kraken account type')

        return acc_type


class AmountField(fields.Field):

    @staticmethod
    def _serialize(
            value: AssetAmount,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> AssetAmount:
        try:
            amount = deserialize_asset_amount(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return amount


class PositiveOrZeroAmountField(AmountField):

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> AssetAmount:
        amount = super()._deserialize(value, attr, data, **kwargs)
        if amount < ZERO:
            raise ValidationError(f'Negative amount {value} given. Amount should be >= 0')

        return amount


class PositiveAmountField(AmountField):

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> AssetAmount:
        amount = super()._deserialize(value, attr, data, **kwargs)
        if amount <= ZERO:
            raise ValidationError(f'Non-positive amount {value} given. Amount should be > 0')

        return amount


class PriceField(fields.Field):

    @staticmethod
    def _serialize(
            value: FVal,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Price:
        try:
            price = deserialize_price(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return price


class FeeField(fields.Field):

    @staticmethod
    def _serialize(
            value: Fee,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Fee:
        try:
            fee = deserialize_fee(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return fee


class BlockchainField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> SupportedBlockchain:
        if value in ('btc', 'BTC'):
            blockchain = SupportedBlockchain.BITCOIN
        elif value in ('eth', 'ETH'):
            blockchain = SupportedBlockchain.ETHEREUM
        else:
            raise ValidationError(f'Unrecognized value {value} given for blockchain name')

        return blockchain


class AssetField(fields.Field):

    @staticmethod
    def _serialize(
            value: Asset,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value.identifier)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Asset:
        try:
            asset = Asset(value)
        except (DeserializationError, UnknownAsset) as e:
            raise ValidationError(str(e))

        return asset


class FiatAssetField(AssetField):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> Asset:
        asset = super()._deserialize(value, attr, data, **kwargs)
        if not asset.is_fiat():
            raise ValidationError(f'Asset {asset.identifier} is not a FIAT asset')

        return asset


class EthereumTokenAssetField(AssetField):

    @staticmethod
    def _serialize(  # type: ignore
            value: EthereumToken,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value.identifier)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Asset:
        try:
            token = EthereumToken(value)
        except (DeserializationError, UnknownAsset) as e:
            raise ValidationError(str(e))

        return token


class TradeTypeField(fields.Field):

    @staticmethod
    def _serialize(
            value: TradeType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> TradeType:
        try:
            trade_type = deserialize_trade_type(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return trade_type


class TradePairField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> TradePair:
        if not isinstance(value, str):
            raise ValidationError(f'Provided non-string trade pair value {value}')
        try:
            trade_pair = deserialize_trade_pair(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return trade_pair


class LocationField(fields.Field):

    @staticmethod
    def _serialize(
            value: Location,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Location:
        try:
            location = deserialize_location(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return location


class ExternalServiceNameField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ExternalService:
        if not isinstance(value, str):
            raise ValidationError('External service name should be a string')
        service = ExternalService.serialize(value)
        if not service:
            raise ValidationError(f'External service {value} is not known')

        return service


class ExchangeNameField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        if not isinstance(value, str):
            raise ValidationError('Exchange name should be a string')
        if value not in SUPPORTED_EXCHANGES:
            raise ValidationError(f'Exchange {value} is not supported')

        return value


class ApiKeyField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ApiKey:
        if not isinstance(value, str):
            raise ValidationError('Given API Key should be a string')
        return ApiKey(value)


class ApiSecretField(fields.Field):

    @staticmethod
    def _serialize(
            value: ApiSecret,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value.decode())

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ApiSecret:
        if not isinstance(value, str):
            raise ValidationError('Given API Secret should be a string')
        return ApiSecret(value.encode())


class DirectoryField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Path:
        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_dir():
            raise ValidationError(f'Given path {value} is not a directory')

        return path


class FileField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Path:
        if not isinstance(value, str):
            raise ValidationError('Provided non string type for filepath')

        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_file():
            raise ValidationError(f'Given path {value} is not a file')

        return path


class AsyncTasksQuerySchema(Schema):
    task_id = fields.Integer(strict=True, missing=None)


class TradesQuerySchema(Schema):
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    location = LocationField(missing=None)


class TradeSchema(Schema):
    timestamp = TimestampField(required=True)
    location = LocationField(required=True)
    pair = TradePairField(required=True)
    trade_type = TradeTypeField(required=True)
    amount = PositiveAmountField(required=True)
    rate = PriceField(required=True)
    fee = FeeField(required=True)
    fee_currency = AssetField(required=True)
    link = fields.String(missing='')
    notes = fields.String(missing='')


class FiatBalancesSchema(Schema):
    balances = fields.Dict(
        keys=FiatAssetField(),
        values=PositiveOrZeroAmountField(),
        required=True,
    )


class ManuallyTrackedBalanceSchema(Schema):
    asset = AssetField(required=True)
    label = fields.String(required=True)
    amount = PositiveAmountField(required=True)
    location = LocationField(required=True)
    tags = fields.List(fields.String(), missing=None)

    @post_load  # type: ignore
    def make_manually_tracked_balances(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> ManuallyTrackedBalance:
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalancesSchema(Schema):
    balances = fields.List(fields.Nested(ManuallyTrackedBalanceSchema), required=True)


class ManuallyTrackedBalancesDeleteSchema(Schema):
    labels = fields.List(fields.String(required=True), required=True)


class TradePatchSchema(TradeSchema):
    trade_id = fields.String(required=True)


class TradeDeleteSchema(Schema):
    trade_id = fields.String(required=True)


class TagSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(missing=None)
    background_color = ColorField(required=True)
    foreground_color = ColorField(required=True)


class TagEditSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(missing=None)
    background_color = ColorField(missing=None)
    foreground_color = ColorField(missing=None)


class TagDeleteSchema(Schema):
    name = fields.String(required=True)


class ModifiableSettingsSchema(Schema):
    """This is the Schema for the settings that can be modified via the API"""
    premium_should_sync = fields.Bool(missing=None)
    include_crypto2crypto = fields.Bool(missing=None)
    anonymized_logs = fields.Bool(missing=None)
    submit_usage_analytics = fields.Bool(missing=None)
    ui_floating_precision = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            max=8,
            error='Floating numbers precision in the UI must be between 0 and 8',
        ),
        missing=None,
    )
    taxfree_after_period = TaxFreeAfterPeriodField(missing=None)
    balance_save_frequency = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=1,
            error='The number of hours after which balances should be saved should be >= 1',
        ),
        missing=None,
    )
    include_gas_costs = fields.Bool(missing=None)
    # TODO: Add some validation to this field
    historical_data_start = fields.String(missing=None)
    # TODO: Add some validation to this field
    # even though it gets validated since we try to connect to it
    eth_rpc_endpoint = fields.String(missing=None)
    main_currency = FiatAssetField(missing=None)
    # TODO: Add some validation to this field
    date_display_format = fields.String(missing=None)
    kraken_account_type = KrakenAccountTypeField(missing=None)


class BaseUserSchema(Schema):
    name = fields.String(required=True)
    password = fields.String(required=True)


class UserActionSchema(Schema):
    name = fields.String(required=True)
    # All the fields below are not needed for logout/modification so are not required=True
    password = fields.String(missing=None)
    sync_approval = fields.String(
        missing='unknown',
        validate=webargs.validate.OneOf(choices=('unknown', 'yes', 'no')),
    )
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('login', 'logout')),
        missing=None,
    )
    premium_api_key = fields.String(missing='')
    premium_api_secret = fields.String(missing='')

    @validates_schema  # type: ignore
    def validate_user_action_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['action'] == 'login':
            if data['password'] is None:
                raise ValidationError('Missing password field for login')
        elif data['action'] is None:
            if data['premium_api_key'] == '' or data['premium_api_secret'] == '':
                raise ValidationError(
                    'Without an action premium api key and secret must be provided',
                )


class UserPasswordChangeSchema(Schema):
    name = fields.String(required=True)
    current_password = fields.String(required=True)
    new_password = fields.String(required=True)


class NewUserSchema(BaseUserSchema):
    premium_api_key = fields.String(missing='')
    premium_api_secret = fields.String(missing='')


class AllBalancesQuerySchema(Schema):
    async_query = fields.Boolean(missing=False)
    save_data = fields.Boolean(missing=True)
    ignore_cache = fields.Boolean(missing=False)


class ExternalServiceSchema(Schema):
    name = ExternalServiceNameField(required=True)
    api_key = fields.String(required=True)

    @post_load  # type: ignore
    def make_external_service(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> ExternalServiceApiCredentials:
        """Used when encoding an external resource given in via the API"""
        return ExternalServiceApiCredentials(service=data['name'], api_key=data['api_key'])


class ExternalServicesResourceAddSchema(Schema):
    services = fields.List(fields.Nested(ExternalServiceSchema), required=True)


class ExternalServicesResourceDeleteSchema(Schema):
    services = fields.List(ExternalServiceNameField(), required=True)


class ExchangesResourceAddSchema(Schema):
    name = ExchangeNameField(required=True)
    api_key = ApiKeyField(required=True)
    api_secret = ApiSecretField(required=True)
    passphrase = fields.String(missing=None)


class ExchangesResourceRemoveSchema(Schema):
    name = ExchangeNameField(required=True)


class ExchangeBalanceQuerySchema(Schema):
    name = ExchangeNameField(missing=None)
    async_query = fields.Boolean(missing=False)
    ignore_cache = fields.Boolean(missing=False)


class ExchangeTradesQuerySchema(Schema):
    name = ExchangeNameField(missing=None)
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    async_query = fields.Boolean(missing=False)


class BlockchainBalanceQuerySchema(Schema):
    blockchain = BlockchainField(missing=None)
    async_query = fields.Boolean(missing=False)
    ignore_cache = fields.Boolean(missing=False)


class StatisticsAssetBalanceSchema(Schema):
    asset = AssetField(required=True)
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)


class StatisticsValueDistributionSchema(Schema):
    distribution_by = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('location', 'asset')),
    )


class HistoryProcessingSchema(Schema):
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    async_query = fields.Boolean(missing=False)


class HistoryExportingSchema(Schema):
    directory_path = DirectoryField(required=True)


class EthTokensSchema(Schema):
    eth_tokens = fields.List(EthereumTokenAssetField(), required=True)
    async_query = fields.Boolean(missing=False)


class BlockchainAccountDataSchema(Schema):
    address = fields.String(required=True)
    label = fields.String(missing=None)
    tags = fields.List(fields.String(), missing=None)


class BlockchainAccountsGetSchema(Schema):
    blockchain = BlockchainField(required=True)


def _validate_blockchain_account_schemas(
        data: Dict[str, Any],
        address_getter: Callable,
) -> None:
    """Validates schema input for the PUT/PATCH/DELETE on blockchain account data"""
    # Make sure no duplicates addresses are given
    given_addresses = set()
    # Make sure ethereum addresses are checksummed
    if data['blockchain'] == SupportedBlockchain.ETHEREUM:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            if not is_checksum_address(address):
                raise ValidationError(
                    f'Given value {address} is not a checksummed ethereum address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                )
            given_addresses.add(address)

    # Make sure bitcoin addresses are valid
    elif data['blockchain'] == SupportedBlockchain.BITCOIN:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            if not is_valid_btc_address(address):
                raise ValidationError(
                    f'Given value {address} is not a valid bitcoin address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                )
            given_addresses.add(address)


class BlockchainAccountsPatchSchema(Schema):
    blockchain = BlockchainField(required=True)
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)

    @validates_schema  # type: ignore
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x['address'])


class BlockchainAccountsPutSchema(BlockchainAccountsPatchSchema):
    async_query = fields.Boolean(missing=False)


class BlockchainAccountsDeleteSchema(Schema):
    blockchain = BlockchainField(required=True)
    accounts = fields.List(fields.String(), required=True)
    async_query = fields.Boolean(missing=False)

    @validates_schema  # type: ignore
    def validate_blockchain_accounts_patch_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x)


class IgnoredAssetsSchema(Schema):
    assets = fields.List(AssetField(), required=True)


class DataImportSchema(Schema):
    source = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('cointracking.info',)),
    )
    filepath = FileField(required=True)


class FiatExchangeRatesSchema(Schema):
    currencies = DelimitedOrNormalList(FiatAssetField(), missing=None)


class AsyncQueryArgumentSchema(Schema):
    """A schema for getters that only have one argument enabling async query"""
    async_query = fields.Boolean(missing=False)
