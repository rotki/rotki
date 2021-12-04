import json
from typing import Any, Dict, NamedTuple, Tuple

import jsonschema

from rotkehlchen.errors import DeserializationError
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn  # lgtm[py/unsafe-cyclic-import]
from rotkehlchen.utils.serialization import rlk_jsondumps

ACCOUNTING_EVENT_SCHEMA = {
    'type': 'object',
    'properties': {
        'event_type': {'type': 'string'},
        'location': {'type': 'string'},
        'paid_in_profit_currency': {'type': 'string'},
        'paid_asset': {'type': 'string'},
        'paid_in_asset': {'type': 'string'},
        'taxable_amount': {'type': 'string'},
        'taxable_bought_cost_in_profit_currency': {'type': 'string'},
        'received_asset': {'type': 'string'},
        'taxable_received_in_profit_currency': {'type': 'string'},
        'received_in_asset': {'type': 'string'},
        'net_profit_or_loss': {'type': 'string'},
        'time': {'type': 'number'},
        'cost_basis': {
            'oneOf': [{'type': 'null'}, {'$ref': '#/$defs/cost_basis'}],
        },
        'is_virtual': {'type': 'boolean'},
        'link': {'oneOf': [{'type': 'string'}, {'type': 'null'}]},
        'notes': {'oneOf': [{'type': 'string'}, {'type': 'null'}]},
    },
    '$defs': {
        'cost_basis': {
            'type': 'object',
            'properties': {
                'is_complete': {'type': 'boolean'},
                'matched_acquisitions': {'type': 'array'},
                'taxable_bought_cost': {'type': 'string'},
                'taxfree_bought_cost': {'type': 'string'},
            },
        },
    },
    'required': [
        'location',
        'paid_in_profit_currency',
        'paid_in_asset',
        'taxable_amount',
        'taxable_bought_cost_in_profit_currency',
        'taxable_received_in_profit_currency',
        'received_in_asset',
        'net_profit_or_loss',
        'time',
        'cost_basis',
        'is_virtual',
        'link',
        'notes',
    ],
}


class SchemaEventType(DBEnumMixIn):
    """Supported Event Type schemas

    Keeping it as this for now since we may experiment with a different schemas
    per accounting event type.
    """
    ACCOUNTING_EVENT = 1

    def get_schema(self) -> Dict[str, Any]:
        """May raise EncodingError if schema is invalid"""
        schema: Dict[str, Any] = {}
        if self == SchemaEventType.ACCOUNTING_EVENT:
            return schema

        raise AssertionError('Should never happen')


NamedJsonDBTuple = (
    Tuple[
        str,  # type,
        str,  # data
    ]
)


class NamedJson(NamedTuple):
    event_type: SchemaEventType
    data: Dict[str, Any]

    @classmethod
    def deserialize(
            cls,
            event_type: SchemaEventType,
            data: Dict[str, Any],
    ) -> 'NamedJson':
        """Turns an event type and a data dict to a NamedJson object

        May raise:
         - a DeserializationError if something is wrong with given data or json validation fails.
        """
        schema = event_type.get_schema()
        try:
            jsonschema.validate(data, schema)
        except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
            raise DeserializationError(
                f'Failed jsonschema validation of {str(event_type)} data {data}. '
                f'Error was {str(e)}',
            ) from e

        return NamedJson(
            event_type=event_type,
            data=data,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            json_tuple: NamedJsonDBTuple,
    ) -> 'NamedJson':
        """Turns a tuple read from the database into an appropriate JsonSchema.

        May raise:
         - a DeserializationError if something is wrong with the DB data or json validation fails.

        Event_tuple index - Schema columns
        ----------------------------------
        0 - event_type
        1 - data
        """
        event_type = SchemaEventType.deserialize_from_db(json_tuple[0])
        try:
            data = json.loads(json_tuple[1])
        except json.decoder.JSONDecodeError as e:
            raise DeserializationError(
                f'Could not decode json for {json_tuple} at NamedJson deserialization: {str(e)}',
            ) from e

        return cls.deserialize(event_type=event_type, data=data)

    def to_db_tuple(self) -> NamedJsonDBTuple:
        """May raise:

        - DeserializationError if something fails during conversion to the DB tuple
        """
        event_type = self.event_type.serialize_for_db()
        try:
            string_data = rlk_jsondumps(self.data)
        except (OverflowError, ValueError, TypeError) as e:
            raise DeserializationError(
                f'Could not dump json to string for NamedJson. Error was {str(e)}',
            ) from e

        return event_type, string_data
