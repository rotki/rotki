"""Display details of every location the backend can report, keyed by location identifier.

Names, icons and images come from the location tree catalog. Exchange and bank connector details
are merged in for the locations that have a connector.
"""
from typing import Any, Final

from rotkehlchen.banks.constants import FINTS_CONNECTOR
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    EXPERIMENTAL_EXCHANGES,
    SUPPORTED_EXCHANGES,
)
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
    # FinTS is a connector, not a location, but the bank setup still reads its details here
    details[FINTS_CONNECTOR] = _visuals('FinTS', 'lu-landmark', None)

    for key, value in details.items():
        if key in ALL_SUPPORTED_EXCHANGES:
            if key in SUPPORTED_EXCHANGES:
                value['exchange_details'] = {'is_exchange_with_key': True}
                if key in EXCHANGES_WITH_PASSPHRASE:
                    value['exchange_details']['is_exchange_with_passphrase'] = True
                if key in EXCHANGES_WITHOUT_API_SECRET:
                    value['exchange_details']['is_exchange_without_api_secret'] = True
                if key in EXPERIMENTAL_EXCHANGES:
                    value['exchange_details']['experimental'] = True
                continue
            value['is_exchange'] = True
        elif key in BANK_MANIFESTS:
            value['is_bank'] = True
            value['bank_details'] = BANK_MANIFESTS[key].serialize()

    return details


LOCATION_DETAILS: Final = _location_details()


def get_formatted_location_name(location: LocationIdentifier) -> str:
    """The display name of a built-in location, or the identifier itself for any other"""
    if (details := LOCATION_DETAILS.get(location)) is not None:
        return details['label']

    return location
