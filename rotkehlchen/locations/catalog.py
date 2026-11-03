"""The version-controlled catalog of locations shipped by rotki.

The catalog seeds fresh user databases and supplies the built-in rows to upgrades. Every entry
is a built-in node, so the file does not repeat ``is_builtin``.
"""
import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.locations.types import (
    ROOT_LOCATION_IDENTIFIER,
    LocationIdentifier,
    LocationNode,
    LocationTreeError,
    deserialize_location_identifier,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

CATALOG_PATH: Final = Path(__file__).parent.parent / 'data' / 'locations.json'


@cache
def load_builtin_catalog() -> tuple[LocationNode, ...]:
    """Load the built-in locations, parents before their children.

    May raise LocationTreeError if the catalog file is malformed.
    """
    try:
        entries = json.loads(CATALOG_PATH.read_text(encoding='utf8'))
        nodes = tuple(
            LocationNode(
                identifier=LocationIdentifier(entry['identifier']),
                name=entry['name'],
                parent_identifier=(
                    None if (parent := entry['parent_identifier']) is None
                    else LocationIdentifier(parent)
                ),
                is_builtin=True,
                is_active=entry.get('is_active', True),
                icon=entry.get('icon'),
                image=entry.get('image'),
            ) for entry in entries
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        raise LocationTreeError(f'Malformed location catalog at {CATALOG_PATH}: {e!s}') from e

    validate_location_tree(nodes)
    return nodes


def validate_location_tree(nodes: Iterable[LocationNode]) -> None:
    """Check that the given nodes form one rooted location tree.

    Enforces unique identifiers, a single ``total`` root, existing parents, no cycles,
    case-insensitive sibling-name uniqueness and that no active node sits below an
    archived one. May raise LocationTreeError.
    """
    by_identifier: dict[LocationIdentifier, LocationNode] = {}
    for node in nodes:
        if node.identifier == '' or node.name == '':
            raise LocationTreeError(f'Location {node!r} has an empty identifier or name')
        if node.identifier in by_identifier:
            raise LocationTreeError(f'Duplicate location identifier {node.identifier}')
        by_identifier[node.identifier] = node

    roots = [x for x in by_identifier.values() if x.parent_identifier is None]
    if len(roots) != 1 or roots[0].identifier != ROOT_LOCATION_IDENTIFIER:
        raise LocationTreeError(
            f'Expected the single root {ROOT_LOCATION_IDENTIFIER}, '
            f'got {[x.identifier for x in roots]}',
        )

    sibling_names: set[tuple[LocationIdentifier | None, str]] = set()
    for node in by_identifier.values():
        if (key := (node.parent_identifier, node.name.casefold())) in sibling_names:
            raise LocationTreeError(
                f'Location name {node.name} occurs twice below {node.parent_identifier}',
            )
        sibling_names.add(key)

        if node.parent_identifier is None:
            continue
        if (parent := by_identifier.get(node.parent_identifier)) is None:
            raise LocationTreeError(
                f'Parent {node.parent_identifier} of location {node.identifier} does not exist',
            )
        if node.is_active and not parent.is_active:
            raise LocationTreeError(
                f'Active location {node.identifier} is below archived {parent.identifier}',
            )

    for node in by_identifier.values():  # every walk up must reach the root
        seen = {node.identifier}
        current = node
        while current.parent_identifier is not None:
            if current.parent_identifier in seen:
                raise LocationTreeError(f'Location {node.identifier} is part of a cycle')
            seen.add(current.parent_identifier)
            current = by_identifier[current.parent_identifier]


@cache
def builtin_location_identifiers() -> frozenset[LocationIdentifier]:
    return frozenset(x.identifier for x in load_builtin_catalog())


def deserialize_builtin_location(value: Any) -> LocationIdentifier:
    """Parse a location that must be one of the locations rotki ships.

    For outside data naming a well-known venue or chain, where anything else means the value
    is not a location at all. May raise DeserializationError.
    """
    if (location := deserialize_location_identifier(value)) not in builtin_location_identifiers():
        raise DeserializationError(f'{value} is not a location known to rotki')
    return location
