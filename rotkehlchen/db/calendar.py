from typing import TYPE_CHECKING, Any, NamedTuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.filtering import (
    DBFilter,
    DBFilterQuery,
    DBMultiIntegerFilter,
    DBOptionalChainAddressesFilter,
    DBSubStringFilter,
    DBTimestampFilter,
    FilterWithTimestamp,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import (
    BlockchainAddress,
    HexColorCode,
    OptionalBlockchainAddress,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class CalendarEntry(NamedTuple):
    """Represents a calendar entry in the database"""
    name: str
    timestamp: Timestamp
    description: str | None
    counterparty: str | None
    address: BlockchainAddress | None
    blockchain: SupportedBlockchain | None
    color: HexColorCode | None
    identifier: int = 0

    def serialize(self) -> dict[str, Any]:
        data = {
            'identifier': self.identifier,
            'name': self.name,
            'description': self.description,
            'timestamp': self.timestamp,
        }
        if self.color is not None:
            data['color'] = self.color
        if self.counterparty is not None:
            data['counterparty'] = self.counterparty
        if self.address is not None:
            data['address'] = self.address
        if self.blockchain is not None:
            data['blockchain'] = self.blockchain.serialize()

        return data

    def serialize_for_db(self) -> tuple[
        str,  # name
        int,  # timestamp
        str | None,  # description
        str | None,  # counterparty
        str | None,  # address
        str | None,  # blockchain
        str | None,  # color
        int,  # identifier
    ]:
        return (
            self.name,
            self.timestamp,
            self.description,
            self.counterparty,
            self.address,
            self.blockchain.value if self.blockchain else None,
            self.color,
            self.identifier,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            row: tuple[int, str, str | None, str | None, int, str | None, str | None, str | None],
    ) -> 'CalendarEntry':
        return cls(
            identifier=row[0],
            name=row[1],
            description=row[2],
            counterparty=row[3],
            timestamp=Timestamp(row[4]),
            address=row[5],  # type: ignore  # it is a str here
            blockchain=SupportedBlockchain.deserialize(row[6]) if row[6] else None,
            color=HexColorCode(row[7]) if row[7] else None,
        )


class CalendarFilterQuery(DBFilterQuery, FilterWithTimestamp):
    """Filter used to query calendar events"""

    @classmethod
    def make(
            cls: type['CalendarFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            addresses: list[OptionalBlockchainAddress] | None = None,
            name: str | None = None,
            description: str | None = None,
            counterparty: str | None = None,
            identifiers: list[int] | None = None,
    ) -> 'CalendarFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )

        filters: list['DBFilter'] = [filter_query.timestamp_filter]
        if addresses is not None:
            filters.append(DBOptionalChainAddressesFilter(
                and_op=False,
                optional_chain_addresses=addresses,
            ))
        if name is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=name,
            ))
        if description is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='description',
                search_string=description,
            ))
        if counterparty is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='counterparty',
                search_string=counterparty,
            ))
        if identifiers is not None:
            filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='identifier',
                values=identifiers,
            ))

        filter_query.filters = filters
        return filter_query


class DBCalendar:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def create_calendar_entry(self, calendar: CalendarEntry) -> int:
        """Insert the provided event in the database.
        May raise:
        - InputError if any db constraint is not satisfied
        """
        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    'INSERT OR IGNORE INTO calendar(name, timestamp, description, counterparty, '
                    'address, blockchain, color) VALUES (?, ?, ?, ?, ?, ?, ?) '
                    'RETURNING identifier',
                    calendar.serialize_for_db()[:-1],  # exclude the default identifier since we need to create it  # noqa: E501
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(f'Could not add calendar entry due to {e}') from e

            if (identifier_row := write_cursor.fetchone()) is None:
                raise InputError(
                    'Could not add the calendar entry because an event with the same name, '
                    'address and blockchain already exist',
                )

            return identifier_row[0]

    def query_calendar_entry(self, filter_query: CalendarFilterQuery) -> dict[str, Any]:
        """Query events using the provided filter and return the result along with the
        attributes used in pagination
        """
        query, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT identifier, name, description, counterparty, timestamp, address, '
                'blockchain, color FROM calendar ' + query,
                bindings,
            )
            result = [CalendarEntry.deserialize_from_db(entry) for entry in cursor]
            query, bindings = filter_query.prepare(with_pagination=False)
            cursor.execute('SELECT COUNT(*) FROM calendar ' + query, bindings)
            entries_found = cursor.fetchone()[0]
            return {
                'entries': result,
                'entries_found': entries_found,
                'entries_total': self.db.get_entries_count(cursor=cursor, entries_table='calendar'),  # noqa: E501
                'entries_limit': -1,
            }

    def delete_calendar_entry(self, identifier: int) -> None:
        """May raise:
        - InputError: if no event got deleted
        """
        with self.db.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM calendar WHERE identifier=?', (identifier,))
            if write_cursor.rowcount != 1:
                raise InputError('Tried to delete a non existent calendar entry')

    def update_calendar_entry(self, calendar: CalendarEntry) -> int:
        """Update the event with the given identifier using the data provided.
        May raise:
        - InputError if no event got updated
        """
        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE calendar SET name=?, timestamp=?, description=?, counterparty=?, address=?, blockchain=?, color=? WHERE identifier=?',  # noqa: E501
                    calendar.serialize_for_db(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update calendar entry due to {e}') from e

        return calendar.identifier
