import json
from typing import Any, NamedTuple

import jsonschema

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn
from rotkehlchen.utils.serialization import rlk_jsondumps


class SchemaEventType(DBCharEnumMixIn):
    """Supported Event Type schemas

    Keeping it as this for now since we may experiment with a different schemas
    per accounting event type.
    """
    ACCOUNTING_EVENT = 1

    def get_schema(self) -> dict[str, Any]:
        """May raise EncodingError if schema is invalid"""
        schema: dict[str, Any] = {}
        if self == SchemaEventType.ACCOUNTING_EVENT:
            return schema

        raise AssertionError('Should never happen')


NamedJsonDBTuple = (
    tuple[
        str,  # type,
        str,  # data
    ]
)


class NamedJson(NamedTuple):
    event_type: SchemaEventType
    data: dict[str, Any]

    @classmethod
    def deserialize(
            cls,
            event_type: SchemaEventType,
            data: dict[str, Any],
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
                f'Failed jsonschema validation of {event_type!s} data {data}. '
                f'Error was {e!s}',
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
                f'Could not decode json for {json_tuple} at NamedJson deserialization: {e!s}',
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
                f'Could not dump json to string for NamedJson. Error was {e!s}',
            ) from e

        return event_type, string_data


class MissingAcquisition(NamedTuple):
    asset: Asset
    time: Timestamp
    found_amount: FVal
    missing_amount: FVal

    def serialize(self) -> dict[str, str | int]:
        return {
            'asset': self.asset.identifier,
            'time': self.time,
            'found_amount': str(self.found_amount),
            'missing_amount': str(self.missing_amount),
        }


class MissingPrice(NamedTuple):
    from_asset: Asset
    to_asset: Asset
    time: Timestamp
    rate_limited: bool

    def serialize(self) -> dict[str, str | (int | bool)]:
        return {
            'from_asset': self.from_asset.identifier,
            'to_asset': self.to_asset.identifier,
            'time': self.time,
            'rate_limited': self.rate_limited,
        }
