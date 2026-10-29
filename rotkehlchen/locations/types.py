from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, NewType

from rotkehlchen.errors.serialization import DeserializationError

LocationIdentifier = NewType('LocationIdentifier', str)

ROOT_LOCATION_IDENTIFIER: Final = LocationIdentifier('total')
CUSTOM_LOCATION_PREFIX: Final = 'custom:'


def deserialize_location_identifier(value: Any) -> LocationIdentifier:
    """Parse a location identifier from outside data. Only the syntax is checked, services
    writing to the DB validate that the location exists and can be used.

    Identifiers of built-in locations are case-insensitive and accept underscores for spaces,
    e.g. KRAKEN, polygon_pos or Polygon PoS. Prefixed identifiers such as custom:<uuid> are
    taken verbatim. May raise DeserializationError.
    """
    if not isinstance(value, str) or (value := value.strip()) == '':
        raise DeserializationError(f'Failed to deserialize location from {value!r}')
    if ':' in value:
        return LocationIdentifier(value)
    return LocationIdentifier(value.lower().replace('_', ' '))


class LocationScope(StrEnum):
    """Which locations a location filter selects"""
    EXACT = 'exact'  # only the given location
    SUBTREE = 'subtree'  # the given location and every descendant


class LocationTreeError(Exception):
    """Raised when a set of location nodes does not form a valid location tree"""


@dataclass(frozen=True, slots=True)
class LocationNode:
    identifier: LocationIdentifier
    name: str
    parent_identifier: LocationIdentifier | None
    is_builtin: bool
    is_active: bool = True
    icon: str | None = None
    image: str | None = None

    def serialize(self) -> dict[str, str | bool | None]:
        return {
            'identifier': self.identifier,
            'name': self.name,
            'parent_identifier': self.parent_identifier,
            'is_builtin': self.is_builtin,
            'is_active': self.is_active,
            'icon': self.icon,
            'image': self.image,
        }
