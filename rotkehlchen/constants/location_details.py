"""Display details of every location the backend can report, keyed by location identifier.

Names, icons and images come from the location tree catalog. Which exchange and bank connectors
exist and what they need is connector metadata, served by /exchanges/supported and
/banks/supported instead.
"""
from typing import Any, Final

from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.locations.catalog import load_builtin_catalog
from rotkehlchen.locations.legacy_chars import V53_LEGACY_LOCATION_CHARS
from rotkehlchen.locations.types import LocationIdentifier


def _visuals(name: str, icon: str | None, image: str | None) -> dict[str, Any]:
    return {'label': name} | ({'image': image} if image is not None else {'icon': icon})


def _location_details() -> dict[LocationIdentifier, dict[str, Any]]:
    details = {
        node.identifier: _visuals(node.name, node.icon, node.image)
        for node in load_builtin_catalog()
    }
    for identifier, name, image in V53_LEGACY_LOCATION_CHARS.values():  # only in upgraded DBs
        details[LocationIdentifier(identifier)] = _visuals(name, None, image)
    for key, value in details.items():
        if key in ALL_SUPPORTED_EXCHANGES:
            value['is_exchange'] = True

    return details


LOCATION_DETAILS: Final = _location_details()


def get_formatted_location_name(location: LocationIdentifier) -> str:
    """The display name of a built-in location, or the identifier itself for any other"""
    if (details := LOCATION_DETAILS.get(location)) is not None:
        return details['label']

    return location
