from typing import TYPE_CHECKING, Any, Literal, Optional
from uuid import uuid4

import webargs
from marshmallow import Schema, ValidationError, fields, post_load, validates_schema

from rotkehlchen.api.v1.fields import (
    AssetField,
    AssetTypeField,
    DelimitedOrNormalList,
    EmptyAsNoneStringField,
    EvmAddressField,
    EvmChainNameField,
    FloatingPercentageField,
    NonEmptyStringField,
    SerializableEnumField,
    SolanaAddressField,
    TimestampField,
)
from rotkehlchen.assets.asset import (
    AssetWithNameAndType,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    FiatAsset,
    SolanaToken,
    UnderlyingToken,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.types import TokenKind

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.interfaces import HistoricalPriceOracleWithCoinListInterface


def _validate_single_oracle_id(
        data: dict[str, Any],
        oracle_name: Literal['coingecko', 'cryptocompare'],
        oracle_obj: 'HistoricalPriceOracleWithCoinListInterface',
) -> None:
    coin_key = data.get(oracle_name)
    if coin_key is None or len(coin_key) == 0:
        return

    try:
        all_coins = oracle_obj.all_coins()
    except RemoteError as e:
        raise ValidationError(
            f'Could not validate {oracle_name} identifier {coin_key} due to '
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
    token_kind = SerializableEnumField(
        enum_class=TokenKind,
        required=True,
        allow_only=[TokenKind.ERC20, TokenKind.ERC721],
    )
    weight = FloatingPercentageField(required=True)


class BaseAssetSchema(Schema):
    name = NonEmptyStringField(required=True)


class AssetWithOraclesSchema(BaseAssetSchema):
    identifier = EmptyAsNoneStringField(required=False, load_default=None)
    symbol = NonEmptyStringField(required=True)
    coingecko = EmptyAsNoneStringField(load_default=None)
    cryptocompare = EmptyAsNoneStringField(load_default=None)

    def __init__(
            self,
            identifier_required: bool,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
    ) -> None:
        super().__init__()
        self.identifier_required = identifier_required
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError(message='Asset identifier should be given', field_name='identifier')  # noqa: E501
        if self.coingecko_obj is not None:
            _validate_single_oracle_id(data, 'coingecko', self.coingecko_obj)
        if self.cryptocompare_obj is not None:
            _validate_single_oracle_id(data, 'cryptocompare', self.cryptocompare_obj)


class FiatAssetSchema(AssetWithOraclesSchema):
    @post_load
    def transform_data(self, data: dict[str, Any], **_kwargs: Any) -> FiatAsset:
        return FiatAsset.initialize(
            # asset id needs to be unique but no combination of asset data is guaranteed to be
            # unique. And especially with the ability to edit assets we need an external uuid.
            # TODO: Asset uuid is generated only for crypto and fiat assets, but we should figure
            # out a way to generate the identifier out of the asset fields, same as we do for
            # evm tokens.
            identifier=data['identifier'] if data['identifier'] is not None else str(uuid4()),
            name=data['name'],
            symbol=data['symbol'],
            coingecko=data['coingecko'],
            cryptocompare=data['cryptocompare'],
        )


class CryptoAssetFieldsSchema(AssetWithOraclesSchema):
    """
    Adds fields specific to crypto assets.
    We keep it separately from CryptoAssetSchema because CryptoAssetSchema has extra logic for
    checking identifier and asset_type, which is not needed for evm tokens.
    """
    started = TimestampField(load_default=None)
    swapped_for = AssetField(expected_type=CryptoAsset, load_default=None)
    forked = AssetField(expected_type=CryptoAsset, load_default=None)


class CryptoAssetSchema(CryptoAssetFieldsSchema):
    asset_type = AssetTypeField(load_default=None)

    def __init__(
            self,
            identifier_required: bool,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            expected_asset_type: AssetType | None = None,
    ) -> None:
        super().__init__(
            identifier_required=identifier_required,
            coingecko=coingecko,
            cryptocompare=cryptocompare,
        )
        self.expected_asset_type = expected_asset_type

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **kwargs: Any,
    ) -> None:
        super().validate_schema(data, **kwargs)
        if self.expected_asset_type is None and data['asset_type'] is None:
            raise ValidationError(message='asset_type should be given', field_name='asset_type')
        if self.expected_asset_type is not None and data['asset_type'] is not None and data['asset_type'] != self.expected_asset_type:  # noqa: E501
            raise ValidationError(message=f'asset_type should be {self.expected_asset_type}', field_name='asset_type')  # noqa: E501

    @post_load
    def transform_data(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, CryptoAsset]:
        crypto_asset = CryptoAsset.initialize(
            # asset id needs to be unique but no combination of asset data is guaranteed to be
            # unique. And especially with the ability to edit assets we need an external uuid.
            # TODO: Asset uuid is generated only for crypto and fiat assets, but we should figure
            # out a way to generate the identifier out of the asset fields, same as we do for
            # evm tokens.
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


class TokenWithDecimalAndProtocolSchema(CryptoAssetFieldsSchema):
    decimals = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            error='Token decimals should be greater than or equal to 0',
        ),
        required=True,
    )
    protocol = EmptyAsNoneStringField(load_default=None)

    def __init__(
            self,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            is_edit: bool = False,
    ) -> None:
        super().__init__(
            identifier_required=False,  # for evm tokens is always computed from address, token kind and chain  # noqa: E501
            coingecko=coingecko,
            cryptocompare=cryptocompare,
        )

        if is_edit is True:
            # we allow the symbol and decimals to be None since it is a valid value in the DB
            # when there are issues querying the token information and those are sent as None
            # to the frontend. For consistency we allow to have them as None when editing.
            # TODO: Fix as part of https://github.com/rotki/rotki/issues/9953
            self.fields['symbol'].allow_none = True
            self.fields['decimals'].allow_none = True


class EvmTokenSchema(TokenWithDecimalAndProtocolSchema):
    address = EvmAddressField(required=True)
    evm_chain = EvmChainNameField(required=True)
    token_kind = SerializableEnumField(
        enum_class=TokenKind,
        required=True,
        allow_only=[TokenKind.ERC20, TokenKind.ERC721],
    )
    underlying_tokens = DelimitedOrNormalList(
        fields.Nested(UnderlyingTokenInfoSchema),
        load_default=None,
    )

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **kwargs: Any,
    ) -> None:
        super().validate_schema(data, **kwargs)
        given_underlying_tokens = data.get('underlying_tokens')
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

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> EvmToken:
        given_underlying_tokens = data.pop('underlying_tokens', None)
        underlying_tokens = None
        if given_underlying_tokens is not None:
            underlying_tokens = [UnderlyingToken(
                address=entry['address'],
                token_kind=entry['token_kind'],
                weight=entry['weight'],
            ) for entry in given_underlying_tokens]

        return EvmToken.initialize(
            address=data['address'],
            chain_id=data['evm_chain'],
            token_kind=data['token_kind'],
            name=data['name'],
            symbol=data['symbol'],
            started=data['started'],
            forked=data['forked'],
            swapped_for=data['swapped_for'],
            coingecko=data['coingecko'],
            cryptocompare=data['cryptocompare'],
            decimals=data['decimals'],
            protocol=data['protocol'],
            underlying_tokens=underlying_tokens,
        )


class SolanaTokenSchema(TokenWithDecimalAndProtocolSchema):
    address = SolanaAddressField(required=True)
    token_kind = SerializableEnumField(
        enum_class=TokenKind,
        required=True,
        allow_only=[TokenKind.SPL_TOKEN, TokenKind.SPL_NFT],
    )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> SolanaToken:
        return SolanaToken.initialize(
            address=data['address'],
            token_kind=data['token_kind'],
            name=data['name'],
            symbol=data['symbol'],
            started=data['started'],
            forked=data['forked'],
            swapped_for=data['swapped_for'],
            coingecko=data['coingecko'],
            cryptocompare=data['cryptocompare'],
            decimals=data['decimals'],
            protocol=data['protocol'],
        )


class BaseCustomAssetSchema(BaseAssetSchema):
    notes = EmptyAsNoneStringField(load_default=None)
    custom_asset_type = NonEmptyStringField(required=True)

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


class AssetSchema(Schema):
    asset_type = AssetTypeField(required=True)

    class Meta:
        # Set unknown = 'INCLUDE' to allow extra parameters
        unknown = 'include'

    def __init__(
            self,
            identifier_required: bool,
            disallowed_asset_types: list[AssetType] | None = None,
            coingecko: Optional['Coingecko'] = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            is_edit: bool = False,
            **kwargs: Any,
    ) -> None:
        """
        Initializes an asset schema depending on the given asset type.

        If identifier_required is True then the identifier field is required.
        Provided asset_type must not be in disallowed_asset_types list.
        If coingecko is not None then the coingecko identifier has to be valid.
        If cryptocompare is not None then the cryptocompare identifier has to be valid.
        """
        super().__init__(**kwargs)
        self.identifier_required = identifier_required
        self.disallowed_asset_types = disallowed_asset_types
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare
        self.is_edit = is_edit

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, AssetWithNameAndType]:
        """Returns a deserialized asset based on the given asset type"""
        asset_type = data.pop('asset_type')
        if self.disallowed_asset_types is not None and asset_type in self.disallowed_asset_types:
            raise ValidationError(
                field_name='asset_type',
                message=f'Asset type {asset_type} is not allowed in this context',
            )

        if asset_type == AssetType.CUSTOM_ASSET:
            asset = CustomAssetWithIdentifierSchema().load(data)['custom_asset']
        elif asset_type == AssetType.FIAT:
            asset = FiatAssetSchema(
                identifier_required=self.identifier_required,
                coingecko=self.coingecko_obj,
                cryptocompare=self.cryptocompare_obj,
            ).load(data)
        elif asset_type == AssetType.EVM_TOKEN:
            asset = EvmTokenSchema(
                coingecko=self.coingecko_obj,
                cryptocompare=self.cryptocompare_obj,
                is_edit=self.is_edit,
            ).load(data)
        elif asset_type == AssetType.SOLANA_TOKEN:
            asset = SolanaTokenSchema(
                coingecko=self.coingecko_obj,
                cryptocompare=self.cryptocompare_obj,
                is_edit=self.is_edit,
            ).load(data)
        else:  # only other case is generic crypto asset
            asset = CryptoAssetSchema(
                expected_asset_type=asset_type,
                identifier_required=self.identifier_required,
                coingecko=self.coingecko_obj,
                cryptocompare=self.cryptocompare_obj,
            ).load(data)['crypto_asset']

        return {'asset': asset}


class ExportedAssetsSchema(Schema):
    version = NonEmptyStringField(required=True)
    assets = fields.List(fields.Nested(AssetSchema(identifier_required=True)), load_default=None)
