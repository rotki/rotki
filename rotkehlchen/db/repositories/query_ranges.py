"""Repository for managing query ranges in the database."""
from typing import TYPE_CHECKING

from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class QueryRangesRepository:
    """Repository for handling all query range operations."""

    def get(self, cursor: 'DBCursor', name: str) -> tuple[Timestamp, Timestamp] | None:
        """Get the last start/end timestamp range that has been queried for name

        Currently possible names are:
        - {exchange_location_name}_margins_{exchange_name}
        - {location}_history_events_{optional_label}
        - {exchange_location_name}_lending_history_{exchange_name}
        - gnosisbridge_{address}
        """
        cursor.execute('SELECT start_ts, end_ts FROM used_query_ranges WHERE name=?', (name,))
        result = cursor.fetchone()
        if result is None:
            return None

        return Timestamp(int(result[0])), Timestamp(int(result[1]))

    def update(
            self,
            write_cursor: 'DBCursor',
            name: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Update the used query range for a queried exchange/location"""
        write_cursor.execute(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            (name, str(start_ts), str(end_ts)),
        )

    def delete_for_exchange(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            exchange_name: str | None = None,
    ) -> None:
        """Delete the query ranges for the given exchange name"""
        names_to_delete = f'{location!s}\\_%'
        if exchange_name is not None:
            names_to_delete += f'\\_{exchange_name}'
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )
