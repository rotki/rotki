from pathlib import Path
from typing import Dict

from marshmallow import Schema, SchemaOpts, fields, post_load, validates_schema
from marshmallow.exceptions import ValidationError
from webargs import fields as webargs_fields, validate

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
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
    HexColorCode,
    Location,
    SupportedBlockchain,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now


class TimestampField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return value

    def _deserialize(self, value, attr, data, **kwargs):  # pylint: disable=unused-argument
        try:
            timestamp = deserialize_timestamp(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return timestamp


class ColorField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return value

    def _deserialize(self, value, attr, data, **kwargs) -> HexColorCode:
        try:
            color_code = deserialize_hex_color_code(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return color_code


class TaxFreeAfterPeriodField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs) -> str:  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value,
            attr,
            data,
            **kwargs,
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


class AmountField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs) -> str:  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value,
            attr,
            data,
            **kwargs,
    ) -> AssetAmount:
        try:
            amount = deserialize_asset_amount(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return amount


class PositiveOrZeroAmountField(AmountField):

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value,
            attr,
            data,
            **kwargs,
    ) -> AssetAmount:
        amount = super()._deserialize(value, attr, data, **kwargs)
        if amount < ZERO:
            raise ValidationError(f'Negative amount {value} given. Amount should be >= 0')

        return amount


class PositiveAmountField(AmountField):

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value,
            attr,
            data,
            **kwargs,
    ) -> AssetAmount:
        amount = super()._deserialize(value, attr, data, **kwargs)
        if amount <= ZERO:
            raise ValidationError(f'Non-positive amount {value} given. Amount should be > 0')

        return amount


class PriceField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):  # pylint: disable=unused-argument
        try:
            price = deserialize_price(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return price


class FeeField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):  # pylint: disable=unused-argument
        try:
            fee = deserialize_fee(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return fee


class BlockchainField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):  # pylint: disable=unused-argument
        if value in ('btc', 'BTC'):
            blockchain = SupportedBlockchain.BITCOIN
        elif value in ('eth', 'ETH'):
            blockchain = SupportedBlockchain.ETHEREUM
        else:
            raise ValidationError(f'Unrecognized value {value} given for blockchain name')

        return blockchain


class AssetField(fields.Field):

    @staticmethod
    def _serialize(value: Asset, attr, obj, **kwargs) -> str:  # pylint: disable=unused-argument
        return str(value.identifier)

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value: str,
            attr,
            data,
            **kwargs,
    ) -> Asset:
        try:
            asset = Asset(value)
        except (DeserializationError, UnknownAsset) as e:
            raise ValidationError(str(e))

        return asset


class FiatAssetField(AssetField):

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value: str,
            attr,
            data,
            **kwargs,
    ) -> Asset:
        asset = super()._deserialize(value, attr, data, **kwargs)
        if not asset.is_fiat():
            raise ValidationError(f'Asset {asset.identifier} is not a FIAT asset')

        return asset


class EthereumTokenAssetField(AssetField):

    @staticmethod
    def _serialize(  # pylint: disable=unused-argument
            value: EthereumToken,
            attr,
            obj,
            **kwargs,
    ) -> str:
        return str(value.identifier)

    def _deserialize(  # pylint: disable=unused-argument
            self,
            value: str,
            attr,
            data,
            **kwargs,
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
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> TradeType:
        try:
            trade_type = deserialize_trade_type(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return trade_type


class TradePairField(fields.Field):

    @staticmethod
    def _serialize(
            value: str,
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
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
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> Location:
        try:
            location = deserialize_location(value)
        except DeserializationError as e:
            raise ValidationError(str(e))

        return location


class ExternalServiceNameField(fields.Field):

    @staticmethod
    def _serialize(
            value: str,
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return value

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> ExternalService:
        if not isinstance(value, str):
            raise ValidationError('External service name should be a string')
        service = ExternalService.serialize(value)
        if not service:
            raise ValidationError(f'External service {value} is not known')

        return service


class ExchangeNameField(fields.Field):

    @staticmethod
    def _serialize(
            value: str,
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return value

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        if not isinstance(value, str):
            raise ValidationError('Exchange name should be a string')
        if value not in SUPPORTED_EXCHANGES:
            raise ValidationError(f'Exchange {value} is not supported')

        return value


class ApiKeyField(fields.Field):

    @staticmethod
    def _serialize(
            value: ApiKey,
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> ApiKey:
        if not isinstance(value, str):
            raise ValidationError('Given API Key should be a string')
        return ApiKey(value)


class ApiSecretField(fields.Field):

    @staticmethod
    def _serialize(
            value: ApiSecret,
            attr,  # pylint: disable=unused-argument
            obj,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> str:
        return str(value.decode())

    def _deserialize(
            self,
            value: str,
            attr,  # pylint: disable=unused-argument
            data,  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
    ) -> ApiSecret:
        if not isinstance(value, str):
            raise ValidationError('Given API Secret should be a string')
        return ApiSecret(value.encode())


class DirectoryField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(self, value: str, attr, data, **kwargs):  # pylint: disable=unused-argument
        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_dir():
            raise ValidationError(f'Given path {value} is not a directory')

        return path


class FileField(fields.Field):

    @staticmethod
    def _serialize(value, attr, obj, **kwargs):  # pylint: disable=unused-argument
        return str(value)

    def _deserialize(self, value: str, attr, data, **kwargs):  # pylint: disable=unused-argument
        if not isinstance(value, str):
            raise ValidationError('Provided non string type for filepath')

        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_file():
            raise ValidationError(f'Given path {value} is not a file')

        return path


class BaseOpts(SchemaOpts):
    """
    This allows for having the Object the Schema encodes to inside of the class Meta
    """

    def __init__(self, meta, ordered):
        SchemaOpts.__init__(self, meta, ordered=ordered)
        self.decoding_class = getattr(meta, "decoding_class", None)


class BaseSchema(Schema):
    OPTIONS_CLASS = BaseOpts

    @post_load
    def make_object(self, data, **kwargs):  # pylint: disable=unused-argument
        # this will depend on the Schema used, which has its object class in
        # the class Meta attributes
        decoding_class = self.opts.decoding_class  # pylint: disable=no-member
        return decoding_class(**data)


class AsyncTasksQuerySchema(BaseSchema):
    task_id = fields.Integer(strict=True, missing=None)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TradesQuerySchema(BaseSchema):
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    location = LocationField(missing=None)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TradeSchema(BaseSchema):
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

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class FiatBalancesSchema(BaseSchema):
    balances = fields.Dict(
        keys=FiatAssetField(),
        values=PositiveOrZeroAmountField(),
        required=True,
    )

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TradePatchSchema(TradeSchema):
    trade_id = fields.String(required=True)


class TradeDeleteSchema(BaseSchema):
    trade_id = fields.String(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TagSchema(BaseSchema):
    name = fields.String(required=True)
    description = fields.String(missing=None)
    background_color = ColorField(required=True)
    foreground_color = ColorField(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TagEditSchema(BaseSchema):
    name = fields.String(required=True)
    description = fields.String(missing=None)
    background_color = ColorField(missing=None)
    foreground_color = ColorField(missing=None)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class TagDeleteSchema(BaseSchema):
    name = fields.String(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ModifiableSettingsSchema(BaseSchema):
    """This is the Schema for the settings that can be modified via the API"""
    premium_should_sync = fields.Bool(missing=None)
    include_crypto2crypto = fields.Bool(missing=None)
    anonymized_logs = fields.Bool(missing=None)
    submit_usage_analytics = fields.Bool(missing=None)
    ui_floating_precision = fields.Integer(
        strict=True,
        validate=validate.Range(
            min=0,
            max=8,
            error='Floating numbers precision in the UI must be between 0 and 8',
        ),
        missing=None,
    )
    taxfree_after_period = TaxFreeAfterPeriodField(missing=None)
    balance_save_frequency = fields.Integer(
        strict=True,
        validate=validate.Range(
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

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BaseUserSchema(BaseSchema):
    name = fields.String(required=True)
    password = fields.String(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class UserActionSchema(BaseSchema):
    name = fields.String(required=True)
    # All the fields below are not needed for logout/modification so are not required=True
    password = fields.String(missing=None)
    sync_approval = fields.String(
        missing='unknown',
        validate=validate.OneOf(choices=('unknown', 'yes', 'no')),
    )
    action = fields.String(
        validate=validate.OneOf(choices=('login', 'logout')),
        missing=None,
    )
    premium_api_key = fields.String(missing='')
    premium_api_secret = fields.String(missing='')

    @validates_schema
    def validate_user_action_schema(self, data, **kwargs):
        if data['action'] == 'login':
            if data['password'] is None:
                raise ValidationError('Missing password field for login')
        elif data['action'] is None:
            if data['premium_api_key'] == '' or data['premium_api_secret'] == '':
                raise ValidationError(
                    'Without an action premium api key and secret must be provided',
                )

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class NewUserSchema(BaseUserSchema):
    premium_api_key = fields.String(missing='')
    premium_api_secret = fields.String(missing='')


class AllBalancesQuerySchema(BaseSchema):
    async_query = fields.Boolean(missing=False)
    save_data = fields.Boolean(missing=True)
    ignore_cache = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExternalServiceSchema(Schema):
    name = ExternalServiceNameField(required=True)
    api_key = fields.String(required=True)

    @post_load
    def make_external_service(self, data: Dict, **kwargs) -> ExternalServiceApiCredentials:
        """Used when encoding an external resource given in via the API"""
        return ExternalServiceApiCredentials(service=data['name'], api_key=data['api_key'])


class ExternalServicesResourceAddSchema(BaseSchema):
    services = fields.List(fields.Nested(ExternalServiceSchema), required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExternalServicesResourceDeleteSchema(BaseSchema):
    services = fields.List(ExternalServiceNameField(), required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExchangesResourceAddSchema(BaseSchema):
    name = ExchangeNameField(required=True)
    api_key = ApiKeyField(required=True)
    api_secret = ApiSecretField(required=True)
    passphrase = fields.String(missing=None)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExchangesResourceRemoveSchema(BaseSchema):
    name = ExchangeNameField(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExchangeBalanceQuerySchema(BaseSchema):
    name = ExchangeNameField(missing=None)
    async_query = fields.Boolean(missing=False)
    ignore_cache = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class ExchangeTradesQuerySchema(BaseSchema):
    name = ExchangeNameField(missing=None)
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    async_query = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BlockchainBalanceQuerySchema(BaseSchema):
    blockchain = BlockchainField(missing=None)
    async_query = fields.Boolean(missing=False)
    ignore_cache = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class StatisticsAssetBalanceSchema(BaseSchema):
    asset = AssetField(required=True)
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class StatisticsValueDistributionSchema(BaseSchema):
    distribution_by = fields.String(
        required=True,
        validate=validate.OneOf(choices=('location', 'asset')),
    )

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class HistoryProcessingSchema(BaseSchema):
    from_timestamp = TimestampField(missing=Timestamp(0))
    to_timestamp = TimestampField(missing=ts_now)
    async_query = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class HistoryExportingSchema(BaseSchema):
    directory_path = DirectoryField(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class EthTokensSchema(BaseSchema):
    eth_tokens = fields.List(EthereumTokenAssetField(), required=True)
    async_query = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BlockchainAccountDataSchema(Schema):
    address = fields.String(required=True)
    label = fields.String(missing=None)
    tags = fields.List(fields.String(), missing=None)


class BlockchainAccountsGetSchema(BaseSchema):
    blockchain = BlockchainField(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BlockchainAccountsPatchSchema(BaseSchema):
    blockchain = BlockchainField(required=True)
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BlockchainAccountsPutSchema(BlockchainAccountsPatchSchema):
    async_query = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class BlockchainAccountsDeleteSchema(BaseSchema):
    blockchain = BlockchainField(required=True)
    accounts = fields.List(fields.String(), required=True)
    async_query = fields.Boolean(missing=False)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class IgnoredAssetsSchema(BaseSchema):
    assets = fields.List(AssetField(), required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class DataImportSchema(BaseSchema):
    source = fields.String(
        required=True,
        validate=validate.OneOf(choices=('cointracking.info',)),
    )
    filepath = FileField(required=True)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict


class FiatExchangeRatesSchema(BaseSchema):
    currencies = webargs_fields.DelimitedList(FiatAssetField(), missing=None)

    class Meta:
        strict = True
        # decoding to a dict is required by the @use_kwargs decorator from webargs
        decoding_class = dict
