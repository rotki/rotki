from enum import Enum
from typing import Type, TypeVar

from rotkehlchen.errors import DeserializationError

T = TypeVar('T', bound=Enum)


class DBEnumMixIn(Enum):

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize_for_db(self) -> str:
        return chr(self.value + 64)

    @classmethod
    def deserialize_from_db(cls: Type[T], value: str) -> T:
        """May raise a DeserializationError if something is wrong with the DB data"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} DB value from non string value: {value}',
            )

        number = ord(value)
        if number < 65 or number > list(cls)[-1].value + 64:  # type: ignore
            raise DeserializationError(f'Failed to deserialize {cls.__name__} DB value {value}')
        return cls(number - 64)

    def serialize(self) -> str:
        return str(self)

    @classmethod
    def deserialize(cls: Type[T], value: str) -> T:
        """May raise DeserializationError if the given value can't be deserialized"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} value from non string value: {value}',
            )

        upper_value = value.replace(' ', '_').upper()
        try:
            return getattr(cls, upper_value)
        except AttributeError as e:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} value {value}') from e  # noqa: E501
