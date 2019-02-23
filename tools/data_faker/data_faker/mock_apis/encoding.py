from marshmallow import Schema, SchemaOpts, fields, post_load
from marshmallow.exceptions import ValidationError


class BytesField(fields.Field):
    def _serialize(self, value):
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode()
        # else
        raise ValidationError('Invalid input type for BytesField')


class BaseOpts(SchemaOpts):
    """
    This allows for having the Object the Schema encodes to inside of the class Meta
    """
    def __init__(self, meta):
        SchemaOpts.__init__(self, meta)
        self.decoding_class = getattr(meta, 'decoding_class', None)


class BaseSchema(Schema):
    OPTIONS_CLASS = BaseOpts

    @post_load
    def make_object(self, data):
        # this will depend on the Schema used, which has its object class in
        # the class Meta attributes
        decoding_class = self.opts.decoding_class  # pylint: disable=no-member
        return decoding_class(**data)


class KrakenTickerSchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class KrakenAssetPairsSchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class KrakenBalanceSchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class KrakenTradesHistorySchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class BinanceAccountSchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class BinanceExchangeInfoSchema(BaseSchema):

    class Meta:
        strict = True
        decoding_class = dict


class BinanceMyTradesSchema(BaseSchema):

    symbol = fields.String(required=True)

    class Meta:
        strict = True
        decoding_class = dict
