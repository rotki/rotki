from enum import Enum
from typing import TypeVar

from rotkehlchen.errors.serialization import DeserializationError

T = TypeVar('T', bound=Enum)


class SerializableEnumValueMixin(Enum):
    """An enum that uses lowercase value for serialization but uses name for __str__"""

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member  # noqa: E501

    def serialize(self) -> str:
        return ' '.join(word.lower() for word in self.value.split('_'))  # pylint: disable=no-member  # noqa: E501

    @classmethod
    def deserialize(cls: type[T], value: str) -> T:
        """May raise DeserializationError if the given value can't be deserialized"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} value from non string value: {value}',
            )

        upper_value = value.replace(' ', '_').upper()
        try:
            return cls(upper_value)
        except ValueError as e:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} value {value}') from e  # noqa: E501
