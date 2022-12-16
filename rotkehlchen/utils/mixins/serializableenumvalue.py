from enum import Enum
from typing import TypeVar

from rotkehlchen.errors.serialization import DeserializationError

T = TypeVar('T', bound=Enum)


class SerializableEnumValueMixin(Enum):
    """An enum that uses lowercase value for serialization and does same for __str__"""

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.value.split('_'))  # pylint: disable=no-member  # noqa: E501

    def serialize(self) -> str:
        return str(self)

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


class SerializableEnumValueMixin2(Enum):
    """An enum that uses lowercase value for serialization but uses name for __str__

    TODO: Perhaps consolidate both Enums to 1? Created a 2nd one here since changing
    SerializableEnumValueMixin to look like this may have unintended consequences
    and did not want to complicate things. We have to make sure that `serialize()` is
    used for DB and str() for showing to user and see if all places SerializableEnumValueMixin
    is used should use the functionality of 1 or of 2 and consolidate if needed.
    If not they can stay different and this TODO can go away.
    """

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
