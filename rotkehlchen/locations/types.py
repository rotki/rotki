from dataclasses import dataclass
from typing import Final, NewType

LocationIdentifier = NewType('LocationIdentifier', str)

ROOT_LOCATION_IDENTIFIER: Final = LocationIdentifier('total')
CUSTOM_LOCATION_PREFIX: Final = 'custom:'


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
