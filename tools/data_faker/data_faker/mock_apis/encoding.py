from marshmallow import Schema, SchemaOpts, fields, post_load


class BaseOpts(SchemaOpts):
    """
    This allows for having the Object the Schema encodes to inside of the class Meta
    """
    def __init__(self, meta, ordered):
        SchemaOpts.__init__(self, meta, ordered=ordered)
        self.decoding_class = getattr(meta, 'decoding_class', None)


class BaseSchema(Schema):
    OPTIONS_CLASS = BaseOpts

    @post_load
    def make_object(self, data):
        # this will depend on the Schema used, which has its object class in
        # the class Meta attributes
        decoding_class = self.opts.decoding_class  # pylint: disable=no-member
        return decoding_class(**data)


class BinanceMyTradesSchema(BaseSchema):

    symbol = fields.String(required=True)

    class Meta:
        strict = True
        decoding_class = dict
