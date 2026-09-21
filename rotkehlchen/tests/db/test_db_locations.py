from typing import TYPE_CHECKING

import pytest
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import InputError
from rotkehlchen.locations.catalog import load_builtin_catalog

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def test_fresh_db_has_the_builtin_tree(database: DBHandler) -> None:
    with database.conn.read_ctx() as cursor:
        assert {x.identifier: x for x in DBLocations.get_all(cursor)} == {
            x.identifier: x for x in load_builtin_catalog()
        }
        DBLocations().validate_tree(cursor)
        assert DBLocations().path_names(cursor, 'ethereum') == [
            'Total', 'Blockchains', 'EVM Chains', 'Ethereum Mainnet',
        ]
        assert [x.identifier for x in DBLocations.ancestors(cursor, 'qonto')] == ['total', 'banks']


def test_descendants(database: DBHandler) -> None:
    with database.conn.read_ctx() as cursor:
        evm_chains = DBLocations.descendants(cursor, ['evm chains'])
        assert {'evm chains', 'ethereum', 'optimism', 'base'} <= evm_chains
        assert 'bitcoin' not in evm_chains
        blockchains = DBLocations.descendants(cursor, ['blockchain'], include_self=False)
        assert 'blockchain' not in blockchains and evm_chains | {'bitcoin', 'solana'} <= blockchains  # noqa: E501
        assert DBLocations.descendants(cursor, ['kraken']) == {'kraken'}
        assert DBLocations.descendants(cursor, ['total']) == {x.identifier for x in load_builtin_catalog()}  # noqa: E501
        assert DBLocations.descendants(cursor, []) == set()


def test_custom_location_lifecycle(database: DBHandler) -> None:
    db_locations = DBLocations()
    with database.user_write() as write_cursor:
        ing = db_locations.add_custom(write_cursor, name=' ING ', parent_identifier='banks')
        assert ing.identifier.startswith('custom:') and ing.name == 'ING'
        assert not ing.is_builtin and ing.is_active
        savings = db_locations.add_custom(write_cursor, name='Savings', parent_identifier=ing.identifier)  # noqa: E501
        # a child below a built-in leaf refines it
        cold = db_locations.add_custom(write_cursor, name='Cold storage', parent_identifier='ethereum')  # noqa: E501
        assert db_locations.path_names(write_cursor, savings.identifier) == ['Total', 'Banks', 'ING', 'Savings']  # noqa: E501
        assert savings.identifier in DBLocations.descendants(write_cursor, ['banks'])
        assert cold.identifier in DBLocations.descendants(write_cursor, ['evm chains'])

        # rename and move keep the identifier
        renamed = db_locations.edit_custom(write_cursor, ing.identifier, name='ING DiBa', parent_identifier='other')  # noqa: E501
        assert (renamed.identifier, renamed.name, renamed.parent_identifier) == (ing.identifier, 'ING DiBa', 'other')  # noqa: E501
        assert db_locations.path_names(write_cursor, savings.identifier) == ['Total', 'Other', 'ING DiBa', 'Savings']  # noqa: E501

        # a used location can be archived but not deleted
        write_cursor.execute(
            "INSERT INTO manually_tracked_balances(asset, label, amount, location, category) VALUES ('ETH', 'savings eth', '1', ?, 'A')",  # noqa: E501
            (savings.identifier,),
        )
        assert db_locations.usage(write_cursor, savings.identifier) == {'manually_tracked_balances': 1}  # noqa: E501
        with pytest.raises(InputError, match='still in use'):
            db_locations.delete_custom(write_cursor, savings.identifier)
        with pytest.raises(InputError, match='has active children'):
            db_locations.edit_custom(write_cursor, ing.identifier, is_active=False)
        db_locations.edit_custom(write_cursor, savings.identifier, is_active=False)
        db_locations.edit_custom(write_cursor, ing.identifier, is_active=False)
        with pytest.raises(InputError, match='below archived'):
            db_locations.edit_custom(write_cursor, savings.identifier, is_active=True)
        with pytest.raises(InputError, match='is archived'):
            db_locations.add_custom(write_cursor, name='New', parent_identifier=ing.identifier)
        with pytest.raises(InputError, match='is archived'):
            db_locations.validate_assignable(write_cursor, savings.identifier)
        assert db_locations.validate_assignable(write_cursor, savings.identifier, allow_archived=True) == DBLocations.get(write_cursor, savings.identifier)  # noqa: E501
        DBLocations().validate_tree(write_cursor)

        # an unused childless location can be deleted
        db_locations.delete_custom(write_cursor, cold.identifier)
        assert DBLocations.get(write_cursor, cold.identifier) is None


def test_custom_location_rules(database: DBHandler) -> None:
    db_locations = DBLocations()
    with database.user_write() as write_cursor:
        ing = db_locations.add_custom(write_cursor, name='ING', parent_identifier='banks')
        child = db_locations.add_custom(write_cursor, name='Child', parent_identifier=ing.identifier)  # noqa: E501
        db_locations.add_custom(write_cursor, name='ING', parent_identifier='exchanges')  # other branch  # noqa: E501
        for name, parent, error in (
                ('ing', 'banks', 'already exists'),  # case-insensitive sibling names
                ('Qonto', 'banks', 'already exists'),  # built-in siblings too
                ('  ', 'banks', 'can not be empty'),
                ('New', 'missing', 'does not exist'),
        ):
            with pytest.raises(InputError, match=error):
                db_locations.add_custom(write_cursor, name=name, parent_identifier=parent)

        with pytest.raises(InputError, match='below itself'):
            db_locations.edit_custom(write_cursor, ing.identifier, parent_identifier=child.identifier)  # noqa: E501
        with pytest.raises(InputError, match='below itself'):
            db_locations.edit_custom(write_cursor, ing.identifier, parent_identifier=ing.identifier)  # noqa: E501
        with pytest.raises(InputError, match='already exists'):
            db_locations.edit_custom(write_cursor, ing.identifier, parent_identifier='exchanges')
        with pytest.raises(InputError, match='still in use'):  # it has a child
            db_locations.delete_custom(write_cursor, ing.identifier)

        for builtin in ('total', 'banks', 'kraken', 'ethereum'):  # every built-in is immutable
            with pytest.raises(InputError, match='shipped by rotki'):
                db_locations.edit_custom(write_cursor, builtin, name='Renamed')
            with pytest.raises(InputError, match='shipped by rotki'):
                db_locations.delete_custom(write_cursor, builtin)

        with pytest.raises(InputError, match='cannot be assigned directly'):
            db_locations.validate_assignable(write_cursor, 'total')
        assert db_locations.validate_assignable(write_cursor, 'banks').identifier == 'banks'


def test_location_foreign_keys(database: DBHandler) -> None:
    """Data can only reference existing locations and used locations can not be removed"""
    with database.user_write() as write_cursor:
        with pytest.raises(sqlcipher.IntegrityError, match='FOREIGN KEY'):  # pylint: disable=no-member
            write_cursor.execute(
                "INSERT INTO manually_tracked_balances(asset, label, amount, location, category) VALUES ('ETH', 'x', '1', 'fints', 'A')",  # noqa: E501
            )
        write_cursor.execute(
            "INSERT INTO manually_tracked_balances(asset, label, amount, location, category) VALUES ('ETH', 'y', '1', 'kraken', 'A')",  # noqa: E501
        )
        with pytest.raises(sqlcipher.IntegrityError, match='FOREIGN KEY'):  # pylint: disable=no-member
            write_cursor.execute("DELETE FROM locations WHERE identifier='kraken'")


def test_location_resolution(database: DBHandler) -> None:
    """Imported values resolve by identifier, then alias, then a unique name. Ambiguous names,
    the total and archived locations never resolve."""
    db_locations = DBLocations()
    with database.user_write() as write_cursor:
        ing = db_locations.add_custom(write_cursor, name='ING', parent_identifier='banks')
        other_ing = db_locations.add_custom(write_cursor, name='ing', parent_identifier='other')
        old = db_locations.add_custom(write_cursor, name='My old exchange', parent_identifier='exchanges')  # noqa: E501
        closed = db_locations.add_custom(write_cursor, name='Closed bank', parent_identifier='banks')  # noqa: E501
        db_locations.set_alias(write_cursor, 'ING Diba', ing.identifier)
        db_locations.set_alias(write_cursor, 'Kraken', old.identifier)  # an identifier wins
        db_locations.edit_custom(write_cursor, closed.identifier, is_active=False)

        for value, status, location, candidates in (
            ('KRAKEN', 'resolved', 'kraken', ()),
            ('polygon_pos', 'resolved', 'polygon pos', ()),
            (f' {old.identifier} ', 'resolved', old.identifier, ()),
            ('ing diba', 'resolved', ing.identifier, ()),
            ('my OLD exchange', 'resolved', old.identifier, ()),
            ('Coinbase Pro', 'resolved', 'coinbasepro', ()),
            ('ING', 'ambiguous', None, tuple(sorted((ing.identifier, other_ing.identifier)))),
            ('total', 'unresolved', None, ()),
            ('Closed bank', 'unresolved', None, ()),
            (closed.identifier, 'unresolved', None, ()),
            ('luno', 'unresolved', None, ()),
            ('', 'unresolved', None, ()),
        ):
            resolution = db_locations.resolve(write_cursor, value)
            assert (resolution.status, resolution.location, resolution.candidates) == (status, location, candidates), value  # noqa: E501

        # aliases can not point at what data can not be assigned to, and go with their location
        for alias, target, message in (
            (' ', 'kraken', 'can not be empty'),
            ('Everything', 'total', 'is the total'),
            ('Closed', closed.identifier, 'is archived'),
            ('Nowhere', 'custom:missing', 'does not exist'),
        ):
            with pytest.raises(InputError, match=message):
                db_locations.set_alias(write_cursor, alias, target)
        db_locations.set_alias(write_cursor, 'ing diba', other_ing.identifier)  # case-insensitive replace  # noqa: E501
        assert db_locations.get_aliases(write_cursor) == {'Kraken': old.identifier, 'ing diba': other_ing.identifier}  # noqa: E501
        db_locations.delete_custom(write_cursor, other_ing.identifier)
        assert db_locations.get_aliases(write_cursor) == {'Kraken': old.identifier}
        db_locations.delete_alias(write_cursor, 'KRAKEN')
        with pytest.raises(InputError, match='does not exist'):
            db_locations.delete_alias(write_cursor, 'kraken')
