from typing import Any, Literal, Optional
from uuid import uuid4

import webargs
from marshmallow import Schema, ValidationError, fields, post_load, validates_schema

from rotkehlchen.api.v1.fields import (
    AssetField,
    AssetTypeField,
    DelimitedOrNormalList,
    EvmAddressField,
    EvmChainNameField,
    FloatingPercentageField,
    SerializableEnumField,
    TimestampField,
)
from rotkehlchen.assets.asset import (
    AssetWithNameAndType,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    UnderlyingToken,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.types import EvmTokenKind


def _validate_single_oracle_id(
        data: dict[str, Any],
        oracle_name: Literal['coingecko', 'cryptocompare'],
        oracle_obj: 'HistoricalPriceOracleInterface',
) -> None:
    coin_key = data.get(oracle_name)
    if coin_key is None or len(coin_key) == 0:
        return

    try:
        all_coins = oracle_obj.all_coins()
    except RemoteError as e:
        raise ValidationError(
            f'Could not validate {oracle_name} identifer {coin_key} due to '
            f'problem communicating with {oracle_name}: {e!s}',
        ) from e

    if coin_key not in all_coins:
        raise ValidationError(
            f'Given {oracle_name} identifier {coin_key} is not valid. Make sure the '
            f'identifier is correct and in the list of valid {oracle_name} identifiers',
            field_name=oracle_name,
        )


class UnderlyingTokenInfoSchema(Schema):
    address = EvmAddressField(required=True)
    token_kind = SerializableEnumField(enum_class=EvmTokenKind, required=True)
    weight = FloatingPercentageField(required=True)


class RequiredEvmAddressSchema(Schema):
    address = EvmAddressField(required=True)
    evm_chain = EvmChainNameField(required=True)


class BaseCryptoAssetSchema(Schema):
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    started = TimestampField(load_default=None)
    swapped_for = AssetField(expected_type=CryptoAsset, load_default=None)
    coingecko = fields.String(load_default=None)
    cryptocompare = fields.String(load_default=None)
    forked = AssetField(expected_type=CryptoAsset, load_default=None)


class CryptoAssetSchema(BaseCryptoAssetSchema):
    identifier = fields.String(required=False, load_default=None)
    asset_type = AssetTypeField(
        exclude_types=(AssetType.EVM_TOKEN, AssetType.NFT, AssetType.CUSTOM_ASSET),
        load_default=None,
    )

    def __init__(
            self,
            identifier_required: bool,
            expected_asset_type: Optional[AssetType] = None,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
    ) -> None:
        super().__init__()
        self.identifier_required = identifier_required
        self.expected_asset_type = expected_asset_type
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.expected_asset_type is None and data['asset_type'] is None:
            raise ValidationError(message='asset_type should be given', field_name='asset_type')
        if self.expected_asset_type is not None and data['asset_type'] is not None and data['asset_type'] != self.expected_asset_type:  # noqa: E501
            raise ValidationError(message=f'asset_type should be {self.expected_asset_type}', field_name='asset_type')  # noqa: E501
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError(message='Asset identifier should be given', field_name='identifier')  # noqa: E501
        if self.coingecko_obj is not None:
            _validate_single_oracle_id(data, 'coingecko', self.coingecko_obj)
        if self.cryptocompare_obj is not None:
            _validate_single_oracle_id(data, 'cryptocompare', self.cryptocompare_obj)

    @post_load
    def transform_data(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, CryptoAsset]:
        crypto_asset = CryptoAsset.initialize(
            # asset id needs to be unique but no combination of asset data is guaranteed to be
            # unique. And especially with the ability to edit assets we need an external uuid.
            # TODO: Asset uuid is generated only for crypto assets, but we should figure out a way
            # to generate the identifier out of the asset fields, same as we do for evm tokens.
            identifier=data['identifier'] if data['identifier'] is not None else str(uuid4()),
            name=data['name'],
            symbol=data['symbol'],
            asset_type=self.expected_asset_type if self.expected_asset_type is not None else data['asset_type'],  # noqa: E501
            started=data['started'],
            swapped_for=data['swapped_for'],
            forked=data['forked'],
            coingecko=data['coingecko'],
            cryptocompare=data['cryptocompare'],
        )
        return {'crypto_asset': crypto_asset}


class EvmTokenSchema(BaseCryptoAssetSchema, RequiredEvmAddressSchema):
    token_kind = SerializableEnumField(enum_class=EvmTokenKind, required=True)
    decimals = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            max=18,
            error='Evm token decimals should range from 0 to 18',
        ),
        required=True,
    )
    protocol = fields.String(load_default=None)
    underlying_tokens = DelimitedOrNormalList(
        fields.Nested(UnderlyingTokenInfoSchema),
        load_default=None,
    )

    def __init__(
            self,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_ethereum_token_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        given_underlying_tokens = data.get('underlying_tokens', None)
        if given_underlying_tokens is not None:
            weight_sum = sum(x['weight'] for x in given_underlying_tokens)
            if weight_sum > ONE:
                raise ValidationError(
                    f'The sum of underlying token weights for {data["address"]} '
                    f'is {weight_sum * 100} and exceeds 100%',
                )
            if weight_sum < ONE:
                raise ValidationError(
                    f'The sum of underlying token weights for {data["address"]} '
                    f'is {weight_sum * 100} and does not add up to 100%',
                )

        # most probably validation happens at ModifyEvmTokenSchema
        # so this is not needed. Kind of an ugly way to do this but can't
        # find a way around it at the moment
        if self.coingecko_obj is not None:
            _validate_single_oracle_id(data, 'coingecko', self.coingecko_obj)
        if self.cryptocompare_obj is not None:
            _validate_single_oracle_id(data, 'cryptocompare', self.cryptocompare_obj)

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> EvmToken:
        given_underlying_tokens = data.pop('underlying_tokens', None)
        chain_id = data.pop('evm_chain')
        data['chain_id'] = chain_id
        underlying_tokens = None
        if given_underlying_tokens is not None:
            underlying_tokens = []
            for entry in given_underlying_tokens:
                underlying_tokens.append(UnderlyingToken(
                    address=entry['address'],
                    token_kind=entry['token_kind'],
                    weight=entry['weight'],
                ))
        return EvmToken.initialize(**data, underlying_tokens=underlying_tokens)


class BaseCustomAssetSchema(Schema):
    name = fields.String(required=True)
    notes = fields.String(load_default=None)
    custom_asset_type = fields.String(required=True)

    @post_load
    def make_custom_asset(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, CustomAsset]:
        custom_asset = CustomAsset.initialize(
            identifier=str(uuid4()),
            name=data['name'],
            notes=data['notes'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'custom_asset': custom_asset}


class CustomAssetWithIdentifierSchema(BaseCustomAssetSchema):
    identifier = fields.UUID(required=True)

    @post_load
    def make_custom_asset(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, CustomAsset]:
        custom_asset = CustomAsset.initialize(
            identifier=str(data['identifier']),
            name=data['name'],
            notes=data['notes'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'custom_asset': custom_asset}


class AssetDataSchema(Schema):
    asset_type = AssetTypeField(required=True)
    name = fields.String(required=True)

    class Meta:
        # Set unknown = 'INCLUDE' to allow extra parameters
        unknown = 'include'

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> AssetWithNameAndType:
        """Returns a deserialized asset based on the given asset type"""
        asset_type = data.pop('asset_type')
        if asset_type == AssetType.CUSTOM_ASSET:
            return CustomAssetWithIdentifierSchema().load(data)['custom_asset']
        elif asset_type == AssetType.EVM_TOKEN:
            return EvmTokenSchema().load(data)
        else:
            return CryptoAssetSchema(
                expected_asset_type=asset_type,
                identifier_required=True,
            ).load(data)['crypto_asset']


class ExportedAssetsSchema(Schema):
    version = fields.String(required=True)
    assets = fields.List(fields.Nested(AssetDataSchema), load_default=None)
