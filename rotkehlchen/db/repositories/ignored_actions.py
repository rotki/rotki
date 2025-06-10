"""Repository for managing ignored actions in the database."""
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.errors.misc import InputError

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class IgnoredActionsRepository:
    """Repository for handling all ignored action operations."""

    def add(self, write_cursor: 'DBCursor', identifiers: list[str]) -> None:
        """Adds a list of identifiers to be ignored.

        Raises InputError in case of adding already existing ignored action
        """
        tuples = [(x,) for x in identifiers]
        try:
            write_cursor.executemany(
                'INSERT INTO ignored_actions(identifier) VALUES(?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError('One of the given action ids already exists in the database') from e

    def remove(self, write_cursor: 'DBCursor', identifiers: list[str]) -> None:
        """Removes a list of identifiers to be ignored.

        Raises InputError in case of removing an action that is not in the DB
        """
        tuples = [(x,) for x in identifiers]
        write_cursor.executemany(
            'DELETE FROM ignored_actions WHERE identifier=?;',
            tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(identifiers):
            raise InputError(
                f'Tried to remove {len(identifiers) - affected_rows} '
                f'ignored actions that do not exist',
            )

    def get_all(self, cursor: 'DBCursor') -> set[str]:
        """Get all ignored action identifiers"""
        return {entry[0] for entry in cursor.execute('SELECT identifier from ignored_actions;')}
