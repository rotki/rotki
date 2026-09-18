import re
from pathlib import Path

import pytest

from rotkehlchen.locations import constants as location_constants
from rotkehlchen.locations.catalog import load_builtin_catalog, validate_location_tree
from rotkehlchen.locations.legacy_chars import (
    LEGACY_LOCATIONS_PARENT,
    V53_LEGACY_LOCATION_CHARS,
    V53_LOCATION_CHAR_TO_IDENTIFIER,
)
from rotkehlchen.locations.types import LocationIdentifier, LocationNode, LocationTreeError
from rotkehlchen.tests.utils.locations import V53_ENUM_CHAR_TO_SERIALIZATION
from rotkehlchen.types import SupportedBlockchain

PACKAGED_IMAGES_DIR = Path(__file__).parents[3] / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols'  # noqa: E501


def _node(identifier: str, parent: str | None, name: str | None = None, is_active: bool = True) -> LocationNode:  # noqa: E501
    return LocationNode(
        identifier=LocationIdentifier(identifier),
        name=identifier if name is None else name,
        parent_identifier=None if parent is None else LocationIdentifier(parent),
        is_builtin=False,
        is_active=is_active,
    )


def test_catalog_shape():
    catalog = {x.identifier: x for x in load_builtin_catalog()}
    assert len(catalog) == len(load_builtin_catalog())
    path, current = [], catalog[LocationIdentifier('ethereum')]
    while current.parent_identifier is not None:
        path.append(current.name)
        current = catalog[current.parent_identifier]
    assert [current.name, *reversed(path)] == ['Total', 'Blockchains', 'EVM Chains', 'Ethereum Mainnet']  # noqa: E501
    assert all(x.is_builtin for x in catalog.values())
    assert 'fints' not in catalog
    assert not any(x.startswith('legacy') for x in catalog)


def test_every_old_location_has_one_migration_rule():
    """Every location a v53 database can hold maps to exactly one catalog or legacy node"""
    catalog_ids = {x.identifier for x in load_builtin_catalog()}
    assert set(V53_LOCATION_CHAR_TO_IDENTIFIER).isdisjoint(V53_LEGACY_LOCATION_CHARS)
    assert set(V53_LOCATION_CHAR_TO_IDENTIFIER.values()) <= catalog_ids
    assert len(set(V53_LOCATION_CHAR_TO_IDENTIFIER.values())) == len(V53_LOCATION_CHAR_TO_IDENTIFIER)  # noqa: E501
    assert catalog_ids.isdisjoint(x[0] for x in V53_LEGACY_LOCATION_CHARS.values())

    for char, serialization in V53_ENUM_CHAR_TO_SERIALIZATION.items():
        if char in V53_LEGACY_LOCATION_CHARS:
            assert V53_LEGACY_LOCATION_CHARS[char][0] == f'legacy:{serialization}'
        else:  # built-ins keep their API serialization as identifier
            assert V53_LOCATION_CHAR_TO_IDENTIFIER[char] == serialization
    assert len(V53_LOCATION_CHAR_TO_IDENTIFIER) + len(V53_LEGACY_LOCATION_CHARS) == len(V53_ENUM_CHAR_TO_SERIALIZATION)  # noqa: E501
    # added by the unreleased v54 itself and never stored as a character
    assert {'sonic', 'robinhood', 'ink', 'qonto'} <= catalog_ids


def test_every_supported_blockchain_has_a_node():
    catalog_ids = {x.identifier for x in load_builtin_catalog()}
    for chain in SupportedBlockchain:
        expected = 'ethereum' if chain == SupportedBlockchain.ETHEREUM_BEACONCHAIN else chain.name.lower().replace('_', ' ')  # noqa: E501
        assert expected in catalog_ids, f'{chain} has no location node'


def test_catalog_visuals():
    for node in load_builtin_catalog():
        assert (node.icon is None) != (node.image is None), f'{node.identifier} needs exactly one of icon/image'  # noqa: E501
        if node.icon is not None:
            assert re.fullmatch(r'lu-[a-z0-9-]+', node.icon), node.icon

    if not PACKAGED_IMAGES_DIR.is_dir():
        pytest.skip('packaged frontend images are not available')
    images = [x.image for x in load_builtin_catalog() if x.image is not None]
    images += [x[2] for x in V53_LEGACY_LOCATION_CHARS.values()]
    for image in images:
        assert (PACKAGED_IMAGES_DIR / image).is_file(), f'missing packaged image {image}'


def test_catalog_with_legacy_branch_is_valid():
    """The conditional legacy branch is inactive and remains a valid part of the tree"""
    parent_id, parent_name, grandparent, _ = LEGACY_LOCATIONS_PARENT
    validate_location_tree([
        *load_builtin_catalog(),
        _node(parent_id, grandparent, name=parent_name, is_active=False),
        *(_node(x[0], parent_id, name=x[1], is_active=False) for x in V53_LEGACY_LOCATION_CHARS.values()),  # noqa: E501
    ])


@pytest.mark.parametrize(('nodes', 'error'), [
    ([_node('total', None), _node('a', 'total'), _node('a', 'total')], 'Duplicate'),
    ([_node('total', None), _node('other', None)], 'single root'),
    ([_node('root', None)], 'single root'),
    ([_node('total', None), _node('a', 'missing')], 'does not exist'),
    ([_node('total', None), _node('a', 'b'), _node('b', 'a')], 'cycle'),
    ([_node('total', None), _node('a', 'a')], 'cycle'),
    ([_node('total', None), _node('a', 'total', name='ING'), _node('b', 'total', name='ing')], 'occurs twice'),  # noqa: E501
    ([_node('total', None), _node('a', 'total', is_active=False), _node('b', 'a')], 'below archived'),  # noqa: E501
    ([_node('total', None), _node('a', 'total', name='')], 'empty'),
])
def test_invalid_trees_are_rejected(nodes, error):
    with pytest.raises(LocationTreeError, match=error):
        validate_location_tree(nodes)


def test_same_name_in_different_branches_is_allowed():
    validate_location_tree([
        _node('total', None),
        _node('a', 'total'),
        _node('b', 'total'),
        _node('c', 'a', name='ING'),
        _node('d', 'b', name='ING'),
    ])


def test_location_constants_match_catalog():
    constants = {
        value for name, value in vars(location_constants).items() if name.startswith('LOCATION_')
    }
    assert constants == {x.identifier for x in load_builtin_catalog()}
