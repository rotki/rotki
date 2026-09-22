"""The single data-access implementation of integration connections.

A connection is one configured account of an exchange or bank connector. Its identifier never
changes, so everything that tracks a connection's progress (query ranges, cursors, sessions,
connector settings, the non-syncing setting) is keyed by it and survives renames.
"""
from typing import TYPE_CHECKING, Any, Final

from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.connections.types import (
    CONNECTION_RANGE_KINDS,
    ConnectionIdentifier,
    ConnectionRangeKind,
    ConnectorIdentifier,
    IntegrationConnection,
    connection_cache_prefix,
    connection_range_name,
    new_connection_identifier,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import InputError
from rotkehlchen.locations.types import LocationIdentifier
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.types import ExchangeAuthCredentials

_COLUMNS: Final = 'identifier, name, connector_identifier, location_identifier, api_key, api_secret, passphrase'  # noqa: E501


def _connection_from_row(row: tuple) -> IntegrationConnection:
    return IntegrationConnection(
        identifier=ConnectionIdentifier(row[0]),
        name=row[1],
        connector=ConnectorIdentifier(row[2]),
        location=LocationIdentifier(row[3]),
        api_key=ApiKey(row[4]),
        # databases written by old versions may hold the secret as a blob
        api_secret=None if row[5] is None else ApiSecret(row[5] if isinstance(row[5], bytes) else row[5].encode()),  # noqa: E501
        passphrase=row[6],
    )


class DBConnections:

    def __init__(self, database: DBHandler) -> None:
        self.db = database

    @staticmethod
    def get(cursor: DBCursor, identifier: str) -> IntegrationConnection | None:
        row = cursor.execute(
            f'SELECT {_COLUMNS} FROM integration_connections WHERE identifier=?',
            (identifier,),
        ).fetchone()
        return None if row is None else _connection_from_row(row)

    @staticmethod
    def get_by_name(
            cursor: DBCursor,
            connector: str,
            name: str,
    ) -> IntegrationConnection | None:
        row = cursor.execute(
            f'SELECT {_COLUMNS} FROM integration_connections '
            'WHERE connector_identifier=? AND name=?',
            (connector, name),
        ).fetchone()
        return None if row is None else _connection_from_row(row)

    @staticmethod
    def get_all(
            cursor: DBCursor,
            connectors: Collection[str] | None = None,
    ) -> list[IntegrationConnection]:
        bindings: tuple[str, ...] = ()
        if connectors is None:
            query = f'SELECT {_COLUMNS} FROM integration_connections'
        else:
            query = (
                f'SELECT {_COLUMNS} FROM integration_connections WHERE connector_identifier '
                f'IN ({",".join("?" * len(connectors))})'
            )
            bindings = tuple(connectors)
        return [_connection_from_row(row) for row in cursor.execute(query, bindings)]

    @staticmethod
    def identifiers_at_location(cursor: DBCursor, location: str) -> list[ConnectionIdentifier]:
        return [ConnectionIdentifier(row[0]) for row in cursor.execute(
            'SELECT identifier FROM integration_connections WHERE location_identifier=?',
            (location,),
        )]

    @staticmethod
    def add(
            write_cursor: DBCursor,
            name: str,
            connector: ConnectorIdentifier,
            location: LocationIdentifier,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            passphrase: str | None = None,
            identifier: ConnectionIdentifier | None = None,
    ) -> IntegrationConnection:
        """Persist a new connection. A connection whose identifier was handed out before it
        was saved (a bank setup waiting for authentication) passes that identifier.

        May raise InputError if the location can not hold data or the connector already has
        a connection with this name.
        """
        DBLocations().validate_assignable(write_cursor, location)
        connection = IntegrationConnection(
            identifier=new_connection_identifier() if identifier is None else identifier,
            name=name,
            connector=connector,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        try:
            write_cursor.execute(
                f'INSERT INTO integration_connections({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    connection.identifier,
                    name,
                    connector,
                    location,
                    api_key,
                    None if api_secret is None else api_secret.decode(),
                    passphrase,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(f'A {connector} connection named {name} already exists') from e
        return connection

    def edit(
            self,
            write_cursor: DBCursor,
            identifier: str,
            new_name: str | None,
            credentials: ExchangeAuthCredentials,
    ) -> None:
        """Rename a connection and/or replace the given credential fields. Everything keyed
        by the identifier follows by construction. Only the location label of the
        connection's events holds its name, so a rename updates it.

        May raise InputError if the connection does not exist or the name is taken.
        """
        if (connection := self.get(write_cursor, identifier)) is None:
            raise InputError(f'Connection {identifier} does not exist')
        assignments, bindings = [], []
        for column, value in (
                ('name', new_name),
                ('api_key', credentials.api_key),
                ('api_secret', credentials.api_secret.decode() if credentials.api_secret is not None else None),  # noqa: E501
                ('passphrase', credentials.passphrase),
        ):
            if value is not None:
                assignments.append(f'{column}=?')
                bindings.append(value)
        if len(assignments) == 0:
            return
        try:
            write_cursor.execute(
                f'UPDATE integration_connections SET {", ".join(assignments)} WHERE identifier=?',
                (*bindings, identifier),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'A {connection.connector} connection named {new_name} already exists',
            ) from e
        if new_name is not None and new_name != connection.name:
            DBHistoryEvents(database=self.db).update_events_and_track(
                write_cursor=write_cursor,
                where_clause='WHERE location=? AND location_label=?',
                where_bindings=(connection.location, connection.name),
                set_clause='SET location_label=?',
                set_bindings=(new_name,),
            )

    @staticmethod
    def delete_progress(
            write_cursor: DBCursor,
            identifiers: Iterable[str],
            kinds: Collection[ConnectionRangeKind] = CONNECTION_RANGE_KINDS,
    ) -> None:
        """Forget what the connections queried, so that they query everything again. Only
        forgetting all kinds also drops their per-account cursors and sessions."""
        for identifier in identifiers:
            write_cursor.executemany(
                'DELETE FROM used_query_ranges WHERE name=?',
                [(connection_range_name(identifier, kind),) for kind in kinds],
            )
            if len(kinds) == len(CONNECTION_RANGE_KINDS):
                prefix = connection_cache_prefix(identifier)
                write_cursor.execute(
                    'DELETE FROM key_value_cache WHERE substr(name, 1, ?)=?',
                    (len(prefix), prefix),
                )

    def delete(self, write_cursor: DBCursor, identifier: str) -> None:
        """Delete a connection with its settings and progress and stop excluding it from
        syncing. May raise InputError if it does not exist."""
        if write_cursor.execute(
            'DELETE FROM integration_connections WHERE identifier=?', (identifier,),
        ).rowcount == 0:
            raise InputError(f'Connection {identifier} does not exist')
        self.delete_progress(write_cursor, [identifier])
        if identifier in (non_syncing := self.db.get_settings(write_cursor).non_syncing_exchanges):
            self.db.set_non_syncing_exchanges(write_cursor, non_syncing - {identifier})

    @staticmethod
    def get_settings(cursor: DBCursor, identifier: str) -> dict[str, Any]:
        """The raw connector specific settings of a connection"""
        return dict(cursor.execute(
            'SELECT setting_name, setting_value FROM integration_connection_settings '
            'WHERE connection_identifier=?',
            (identifier,),
        ))

    @staticmethod
    def set_settings(write_cursor: DBCursor, identifier: str, settings: dict[str, Any]) -> None:
        """Values are stored as given, a secret keeps its bytes"""
        write_cursor.executemany(
            'INSERT OR REPLACE INTO integration_connection_settings'
            '(connection_identifier, setting_name, setting_value) VALUES (?, ?, ?)',
            [(identifier, name, value) for name, value in settings.items()],
        )
