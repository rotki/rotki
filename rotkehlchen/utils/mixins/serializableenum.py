from enum import Enum
from typing import Type, TypeVar

from rotkehlchen.errors import DeserializationError  # lgtm[py/unsafe-cyclic-import]

T = TypeVar('T', bound=Enum)


class SerializableEnumMixin(Enum):

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

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
