from marshmallow import Schema, fields

from rotkehlchen.api.v1.encoding import UnderlyingTokenInfoSchema


class AssetListSchema(Schema):
    identifier = fields.String(required=True)
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    asset_type = fields.String(required=True)
    forked = fields.String(required=True, allow_none=True)
    swapped_for = fields.String(required=True, allow_none=True)
    cryptocompare = fields.String(required=True, allow_none=True)
    coingecko = fields.String(required=True, allow_none=True)
    ethereum_address = fields.String()
    decimals = fields.Integer()
    protocol = fields.String(allow_none=True)
    underlying_tokens = fields.List(fields.Nested(UnderlyingTokenInfoSchema), allow_none=True)
    started = fields.Integer(required=True, allow_none=True)


class ExportedAssetsSchema(Schema):
    version = fields.String(required=True)
    assets = fields.List(fields.Nested(AssetListSchema), load_default=[])
