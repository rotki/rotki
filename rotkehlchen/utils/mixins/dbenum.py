from enum import Enum
from typing import TypeVar

from rotkehlchen.errors.serialization import DeserializationError

from .serializableenum import SerializableEnumMixin

T = TypeVar('T', bound=Enum)


class DBEnumMixIn(SerializableEnumMixin):

    def serialize_for_db(self) -> str:
        return chr(self.value + 64)

    @classmethod
    def deserialize_from_db(cls: type[T], value: str) -> T:
        """May raise a DeserializationError if something is wrong with the DB data"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} DB value from non string value: {value}',
            )

        number = ord(value)
        if number < 65 or number > list(cls)[-1].value + 64:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} DB value {value}')
        return cls(number - 64)
