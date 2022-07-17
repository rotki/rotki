from typing import Any, Dict, Union

from marshmallow import Schema, fields, post_load

from rotkehlchen.api.v1.fields import (
    AssetField,
    AssetTypeField,
    EthereumAddressField,
    TimestampField,
)
from rotkehlchen.api.v1.schemas import UnderlyingTokenInfoSchema
from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetType


class AssetDataSchema(Schema):
    identifier = fields.String(required=True)
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    asset_type = AssetTypeField(required=True)
    forked = AssetField(required=True, allow_none=True)
    swapped_for = AssetField(required=True, allow_none=True)
    cryptocompare = fields.String(required=True, allow_none=True)
    coingecko = fields.String(required=True, allow_none=True)
    evm_address = EthereumAddressField(required=False)
    decimals = fields.Integer(required=False)
    protocol = fields.String(allow_none=True)
    underlying_tokens = fields.List(fields.Nested(UnderlyingTokenInfoSchema), allow_none=True)
    started = TimestampField(required=True, allow_none=True)

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        """Returns the a dictionary with:
        - The identifier
        - extra_information used by the globaldb handler
        - name
        - symbol
        - asset_type as instance of AssetType
        """
        given_underlying_tokens = data.pop('underlying_tokens', None)
        underlying_tokens = None
        if given_underlying_tokens is not None:
            underlying_tokens = []
            for entry in given_underlying_tokens:
                underlying_tokens.append(UnderlyingToken(
                    address=entry['address'],
                    weight=entry['weight'],
                    chain=data['chain'],
                    token_kind=data['token_kind'],
                ))

        asset_type = data['asset_type']
        extra_information: Union[Dict[str, Any], EvmToken]
        swapped_for, swapped_for_ident = data.pop('swapped_for'), None
        if swapped_for is not None:
            swapped_for_ident = swapped_for.identifier

        if asset_type == AssetType.ETHEREUM_TOKEN:
            extra_information = EvmToken.initialize(
                address=data.pop('evm_address'),
                chain=data.pop('chain'),
                token_kind=data.pop('token_kind'),
                name=data.get('name'),
                symbol=data.get('symbol'),
                decimals=data.pop('decimals'),
                started=data.pop('started'),
                swapped_for=swapped_for_ident,
                coingecko=data.pop('coingecko'),
                cryptocompare=data.pop('cryptocompare'),
                underlying_tokens=underlying_tokens,
            )
        else:
            forked, forked_ident = data.pop('forked'), None
            if forked is not None:
                forked_ident = forked.identifier

            extra_information = {
                'name': data.get('name'),
                'symbol': data.get('symbol'),
                'started': data.pop('started'),
                'forked': forked_ident,
                'swapper_for': swapped_for_ident,
                'coingecko': data.pop('coingecko'),
                'cryptocompare': data.pop('cryptocompare'),
            }

        data['underlying_tokens'] = underlying_tokens
        data['asset_type'] = asset_type
        data['extra_information'] = extra_information
        return data


class ExportedAssetsSchema(Schema):
    version = fields.String(required=True)
    assets = fields.List(fields.Nested(AssetDataSchema), load_default=None)
