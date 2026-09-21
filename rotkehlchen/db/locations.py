"""The single data-access implementation of the location tree.

All location SQL, ancestry and descendant queries and the mutation rules live here, so that
importers, filters and connection setup agree on what the tree contains.
"""
import uuid
from typing import TYPE_CHECKING, Final

from rotkehlchen.errors.misc import InputError
from rotkehlchen.locations.catalog import load_builtin_catalog, validate_location_tree
from rotkehlchen.locations.types import (
    CUSTOM_LOCATION_PREFIX,
    ROOT_LOCATION_IDENTIFIER,
    LocationIdentifier,
    LocationNode,
    LocationTreeError,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from rotkehlchen.db.drivers.sqlite import DBCursor

# Every (table, column) of the user DB holding a real location
LOCATION_REFERENCES: Final = (
    ('history_events', 'location'),
    ('history_events_backup', 'location'),
    ('timed_location_data', 'location'),
    ('manually_tracked_balances', 'location'),
    ('margin_positions', 'location'),
    ('skipped_external_events', 'location'),
    ('bitcoin_transactions', 'location'),
    ('event_metrics', 'location'),
    ('data_issues', 'location'),
)
_NODE_COLUMNS: Final = 'identifier, name, parent_identifier, is_builtin, is_active, icon, image'


def subtree_query(placeholders: str) -> str:
    """A query selecting the identifiers of the locations bound to the given placeholders and of
    all their descendants.

    Filters use it as an uncorrelated `location IN (...)` subquery. SQLite evaluates that once
    per statement and probes the location index with the result, so the tree is not joined
    against every data row.
    """
    return (
        'WITH RECURSIVE subtree(identifier) AS ('
        f'SELECT identifier FROM locations WHERE identifier IN ({placeholders}) '
        'UNION SELECT L.identifier FROM locations L JOIN subtree S '
        'ON L.parent_identifier=S.identifier) SELECT identifier FROM subtree'
    )


def _node_from_row(row: tuple) -> LocationNode:
    return LocationNode(
        identifier=LocationIdentifier(row[0]),
        name=row[1],
        parent_identifier=None if row[2] is None else LocationIdentifier(row[2]),
        is_builtin=bool(row[3]),
        is_active=bool(row[4]),
        icon=row[5],
        image=row[6],
    )


class DBLocations:

    @staticmethod
    def seed_builtin_locations(write_cursor: DBCursor) -> None:
        """Insert every catalog location missing from the DB. Existing rows stay untouched."""
        write_cursor.executemany(
            f'INSERT OR IGNORE INTO locations({_NODE_COLUMNS}) VALUES (?, ?, ?, 1, ?, ?, ?)',
            [
                (x.identifier, x.name, x.parent_identifier, x.is_active, x.icon, x.image)
                for x in load_builtin_catalog()
            ],
        )

    @staticmethod
    def get_all(cursor: DBCursor) -> list[LocationNode]:
        return [
            _node_from_row(row)
            for row in cursor.execute(f'SELECT {_NODE_COLUMNS} FROM locations')
        ]

    @staticmethod
    def get(cursor: DBCursor, identifier: str) -> LocationNode | None:
        row = cursor.execute(
            f'SELECT {_NODE_COLUMNS} FROM locations WHERE identifier=?', (identifier,),
        ).fetchone()
        return None if row is None else _node_from_row(row)

    @staticmethod
    def descendants(
            cursor: DBCursor,
            identifiers: Collection[str],
            include_self: bool = True,
    ) -> set[LocationIdentifier]:
        """Identifiers of every descendant of the given locations. Resolve a subtree with this
        once and filter data rows with an IN predicate instead of joining the tree per row."""
        if len(identifiers) == 0:
            return set()
        result = {
            LocationIdentifier(row[0]) for row in cursor.execute(
                subtree_query(','.join('?' * len(identifiers))),
                tuple(identifiers),
            )
        }
        return result if include_self else result - {LocationIdentifier(x) for x in identifiers}

    @staticmethod
    def ancestor_identifiers(
            cursor: DBCursor,
            identifiers: Collection[str],
    ) -> set[LocationIdentifier]:
        """Identifiers of every proper ancestor of the given locations, the root included"""
        if len(identifiers) == 0:
            return set()
        return {
            LocationIdentifier(row[0]) for row in cursor.execute(
                'WITH RECURSIVE path(identifier) AS ('
                'SELECT parent_identifier FROM locations '
                f'WHERE identifier IN ({",".join("?" * len(identifiers))}) '
                'AND parent_identifier IS NOT NULL '
                'UNION SELECT L.parent_identifier FROM locations L JOIN path P '
                'ON L.identifier=P.identifier WHERE L.parent_identifier IS NOT NULL) '
                'SELECT identifier FROM path',
                tuple(identifiers),
            )
        }

    @staticmethod
    def ancestors(cursor: DBCursor, identifier: str) -> list[LocationNode]:
        """The path from the root down to the parent of the given location"""
        rows = cursor.execute(
            'WITH RECURSIVE path(identifier, parent_identifier, depth) AS ('
            'SELECT identifier, parent_identifier, 0 FROM locations WHERE identifier=? '
            'UNION ALL SELECT L.identifier, L.parent_identifier, P.depth + 1 FROM locations L '
            'JOIN path P ON L.identifier=P.parent_identifier) '
            f'SELECT {", ".join(f"L.{x.strip()}" for x in _NODE_COLUMNS.split(","))} '
            'FROM path P JOIN locations L ON L.identifier=P.identifier '
            'WHERE P.depth > 0 ORDER BY P.depth DESC',
            (identifier,),
        ).fetchall()
        return [_node_from_row(row) for row in rows]

    def display_paths(self, cursor: DBCursor) -> dict[LocationIdentifier, str]:
        """The display path of every location, e.g. Blockchains > EVM Chains > Ethereum Mainnet.
        The root is left out since every path starts there, so its own path is its name."""
        nodes = {x.identifier: x for x in self.get_all(cursor)}
        paths: dict[LocationIdentifier, str] = {}

        def path_of(node: LocationNode) -> str:
            if (path := paths.get(node.identifier)) is not None:
                return path
            if node.parent_identifier is None or node.parent_identifier == ROOT_LOCATION_IDENTIFIER:  # noqa: E501
                path = node.name
            else:
                path = f'{path_of(nodes[node.parent_identifier])} > {node.name}'
            paths[node.identifier] = path
            return path

        for node in nodes.values():
            path_of(node)
        return paths

    def path_names(self, cursor: DBCursor, identifier: str) -> list[str]:
        """Display names from the root to the given location, itself included"""
        if (node := self.get(cursor, identifier)) is None:
            return []
        return [x.name for x in self.ancestors(cursor, identifier)] + [node.name]

    def validate_tree(self, cursor: DBCursor) -> None:
        """May raise LocationTreeError if the stored locations do not form a valid tree"""
        nodes = self.get_all(cursor)
        validate_location_tree(nodes)
        builtin = {x.identifier: x for x in nodes if x.is_builtin}
        for node in nodes:
            if not node.is_builtin and node.parent_identifier is None:
                raise LocationTreeError(f'Custom location {node.identifier} has no parent')
        missing = {x.identifier for x in load_builtin_catalog()} - builtin.keys()
        if len(missing) != 0:
            raise LocationTreeError(f'Built-in locations {missing} are missing from the DB')

    def validate_assignable(
            self,
            cursor: DBCursor,
            identifier: str,
            allow_archived: bool = False,
    ) -> LocationNode:
        """Check that data can be assigned directly to the given location.

        May raise InputError if the location does not exist, is the root, or is archived
        and allow_archived is False.
        """
        if (node := self.get(cursor, identifier)) is None:
            raise InputError(f'Location {identifier} does not exist')
        if node.identifier == ROOT_LOCATION_IDENTIFIER:
            raise InputError(f'Location {identifier} is the total and cannot be assigned directly')
        if not allow_archived and not node.is_active:
            raise InputError(f'Location {identifier} is archived')
        return node

    def usage(self, cursor: DBCursor, identifier: str) -> dict[str, int]:
        """Rows referencing the location directly and its number of children, only counting
        non-zero entries. A location with an empty usage can be deleted."""
        counts = {
            table: count for table, column in LOCATION_REFERENCES
            if (count := cursor.execute(
                f'SELECT COUNT(*) FROM {table} WHERE {column}=?', (identifier,),
            ).fetchone()[0]) != 0
        }
        if (children := cursor.execute(
            'SELECT COUNT(*) FROM locations WHERE parent_identifier=?', (identifier,),
        ).fetchone()[0]) != 0:
            counts['children'] = children
        return counts

    def _check_name(
            self,
            cursor: DBCursor,
            name: str,
            parent_identifier: str,
            exclude_identifier: str | None = None,
    ) -> str:
        if (name := name.strip()) == '':
            raise InputError('Location name can not be empty')
        if cursor.execute(
            'SELECT COUNT(*) FROM locations WHERE parent_identifier=? AND name=? COLLATE NOCASE '
            'AND identifier IS NOT ?',
            (parent_identifier, name, exclude_identifier),
        ).fetchone()[0] != 0:
            raise InputError(f'A location named {name} already exists at the same level')
        return name

    def _get_custom(self, cursor: DBCursor, identifier: str) -> LocationNode:
        if (node := self.get(cursor, identifier)) is None:
            raise InputError(f'Location {identifier} does not exist')
        if node.is_builtin:
            raise InputError(f'Location {identifier} is shipped by rotki and can not be modified')
        return node

    def add_custom(
            self,
            write_cursor: DBCursor,
            name: str,
            parent_identifier: str,
            icon: str | None = None,
    ) -> LocationNode:
        """Create a custom location below an active location.

        May raise InputError if the parent does not exist or is archived, or if the name
        is empty or already used by a sibling.
        """
        if (parent := self.get(write_cursor, parent_identifier)) is None:
            raise InputError(f'Parent location {parent_identifier} does not exist')
        if not parent.is_active:
            raise InputError(f'Parent location {parent_identifier} is archived')
        node = LocationNode(
            identifier=LocationIdentifier(f'{CUSTOM_LOCATION_PREFIX}{uuid.uuid4()}'),
            name=self._check_name(write_cursor, name, parent_identifier),
            parent_identifier=parent.identifier,
            is_builtin=False,
            icon=icon,
        )
        write_cursor.execute(
            f'INSERT INTO locations({_NODE_COLUMNS}) VALUES (?, ?, ?, 0, 1, ?, NULL)',
            (node.identifier, node.name, node.parent_identifier, node.icon),
        )
        return node

    def edit_custom(
            self,
            write_cursor: DBCursor,
            identifier: str,
            name: str | None = None,
            parent_identifier: str | None = None,
            icon: str | None = None,
            is_active: bool | None = None,
    ) -> LocationNode:
        """Rename, move, change the icon of or (un)archive a custom location. Only the
        given fields change.

        May raise InputError if the location is built-in, the move would create a cycle or
        place an active location below an archived one, archiving would leave active
        children below an archived location, or the name collides with a sibling.
        """
        node = self._get_custom(write_cursor, identifier)
        new_parent_id = node.parent_identifier if parent_identifier is None else parent_identifier
        assert new_parent_id is not None, 'custom locations always have a parent'
        if (new_parent := self.get(write_cursor, new_parent_id)) is None:
            raise InputError(f'Parent location {new_parent_id} does not exist')
        if new_parent.identifier in self.descendants(write_cursor, [identifier]):
            raise InputError(f'Can not move location {identifier} below itself or its descendants')

        new_active = node.is_active if is_active is None else is_active
        if new_active and not new_parent.is_active:
            raise InputError(f'An active location can not be below archived location {new_parent_id}')  # noqa: E501
        if not new_active and write_cursor.execute(
            'SELECT COUNT(*) FROM locations WHERE parent_identifier=? AND is_active=1',
            (identifier,),
        ).fetchone()[0] != 0:
            raise InputError(f'Location {identifier} has active children. Archive them first')

        new_name = self._check_name(
            cursor=write_cursor,
            name=node.name if name is None else name,
            parent_identifier=new_parent_id,
            exclude_identifier=identifier,
        )
        new_icon = node.icon if icon is None else icon
        write_cursor.execute(
            'UPDATE locations SET name=?, parent_identifier=?, icon=?, is_active=? '
            'WHERE identifier=?',
            (new_name, new_parent_id, new_icon, new_active, identifier),
        )
        return LocationNode(
            identifier=node.identifier,
            name=new_name,
            parent_identifier=LocationIdentifier(new_parent_id),
            is_builtin=False,
            is_active=new_active,
            icon=new_icon,
            image=node.image,
        )

    def delete_custom(self, write_cursor: DBCursor, identifier: str) -> None:
        """Delete a custom location that has no children and is referenced by no data.

        May raise InputError if the location is built-in, still has children or is used.
        """
        self._get_custom(write_cursor, identifier)
        if len(usage := self.usage(write_cursor, identifier)) != 0:
            raise InputError(f'Location {identifier} is still in use: {usage}')
        write_cursor.execute('DELETE FROM locations WHERE identifier=?', (identifier,))
