from abc import ABCMeta, abstractmethod
from enum import Enum, EnumMeta
from typing import Any, Self, TypeVar

from rotkehlchen.errors.serialization import DeserializationError

T = TypeVar('T')


class ABCEnumMeta(EnumMeta, ABCMeta):
    """Taken from https://stackoverflow.com/questions/56131308/create-an-abstract-enum-class"""
    def __new__(cls: type[T], *args: Any, **kw: Any) -> T:
        abstract_enum_cls = super().__new__(cls, *args, **kw)  # type: ignore
        # Only check abstractions if members were defined.
        if abstract_enum_cls._member_map_:
            try:  # Handle existence of undefined abstract methods.
                absmethods = list(abstract_enum_cls.__abstractmethods__)
                if absmethods:
                    missing = ', '.join(f'{method!r}' for method in absmethods)
                    plural = 's' if len(absmethods) > 1 else ''
                    raise TypeError(
                        f'cannot instantiate abstract class {abstract_enum_cls.__name__!r}'
                        f' with abstract method{plural} {missing}')
            except AttributeError:
                pass
        return abstract_enum_cls


E = TypeVar('E', bound=Enum)


class SerializableEnumMixin(Enum, metaclass=ABCEnumMeta):
    """Base interface for serializable Enum Mixins which go in/out to the API"""

    @abstractmethod
    def __str__(self) -> str:
        """string constructor"""

    @abstractmethod
    def serialize(self) -> str:
        """The method to serialize this enum for api consumption"""

    @classmethod
    @abstractmethod
    def deserialize(cls: type[E], value: str) -> E:
        """The method to deserialize a string to an enum object"""


S = TypeVar('S', bound=SerializableEnumMixin)


class DBEnumMixIn(SerializableEnumMixin, metaclass=ABCEnumMeta):
    """Base interface for a serializable enum that also gets saved to and read from the DB"""

    @abstractmethod
    def serialize_for_db(self) -> str:
        """Method to serialize enum for saving in the DB"""

    @classmethod
    @abstractmethod
    def deserialize_from_db(cls: type[S], value: Any) -> S:
        """Method to deserialize a DB value and create an object of this enum.

        -May raise a DeserializationError if something is wrong with the DB data"""


class SerializableEnumNameMixin(SerializableEnumMixin):
    """An enum that uses the name of the enum to serialize/deserialize"""

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return str(self)

    @classmethod
    def deserialize(cls, value: str) -> Self:
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


class SerializableEnumValueMixin(SerializableEnumMixin):
    """An enum that uses lowercase value for serialization but uses name for __str__"""

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return ' '.join(word.lower() for word in self.value.split('_'))  # pylint: disable=no-member

    @classmethod
    def deserialize(cls, value: str) -> Self:
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


class SerializableEnumIntValueMixin(SerializableEnumMixin):
    """An enum that uses name for serialization to/from api but has an int value.
    For serialization to/from DB the int value is used"""

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return ' '.join(word.lower() for word in self.value.split('_'))  # pylint: disable=no-member

    @classmethod
    def deserialize(cls, value: str) -> Self:
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


class DBCharEnumMixIn(SerializableEnumNameMixin, DBEnumMixIn):
    """A serializable enum with an int value that also goes into
    the DB and gets saved as an ASCII character"""

    def serialize_for_db(self) -> str:
        return chr(self.value + 64)

    @classmethod
    def deserialize_from_db(cls, value: str) -> Self:
        """May raise a DeserializationError if something is wrong with the DB data"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} DB value from non string value: {value}',
            )

        try:
            number = ord(value)
        except TypeError as e:
            raise DeserializationError(
                f'Failed to deserialize {cls.__name__} DB value from multi-character value: {value}',  # noqa: E501
            ) from e

        if number < 65 or number > list(cls)[-1].value + 64:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} DB value {value}')
        return cls(number - 64)


class DBIntEnumMixIn(SerializableEnumNameMixin, DBEnumMixIn):
    """A serializable enum with an int value that also goes into
    the DB and gets saved as an int there but gets serialized/to from API as a string"""

    def serialize_for_db(self) -> int:  # type: ignore[override]  # changed return on purpose
        return self.value

    @classmethod
    def deserialize_from_db(cls, value: int) -> Self:
        """May raise a DeserializationError if something is wrong with the DB data"""
        try:
            return cls(value)
        except ValueError as e:
            raise DeserializationError(f'Could not deserialize {cls.__name__} from value {value}') from e  # noqa: E501
