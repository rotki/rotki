from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.filtering import (
    DBEqualsFilter,
    DBFilter,
    DBFilterQuery,
    DBMultiIntegerFilter,
    DBOptionalChainAddressesFilter,
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
    auto_delete: bool
    identifier: int = 0

    def serialize(self) -> dict[str, Any]:
        data = {
            'identifier': self.identifier,
            'name': self.name,
            'timestamp': self.timestamp,
            'auto_delete': self.auto_delete,
        }
        if self.description is not None:
            data['description'] = self.description
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
        int,  # auto_delete
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
            int(self.auto_delete),
            self.identifier,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            row: tuple[
                int,
                str,
                str | None,
                str | None,
                int,
                str | None,
                str | None,
                str | None,
                int,
            ],
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
            auto_delete=bool(row[8]),
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class BaseReminderData:
    """Base fields queried for reminders"""
    secs_before: int
    identifier: int

    def serialize(self) -> dict[str, Any]:
        return {
            'identifier': self.identifier,
            'secs_before': self.secs_before,
        }


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class ReminderEntry(BaseReminderData):
    """Store basic information to warn the user based on the event timestamp"""
    event_id: int
    acknowledged: bool

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {
            'event_id': self.event_id,
            'acknowledged': self.acknowledged,
        }

    def serialize_for_db(self) -> tuple[
        int,  # event_id
        int,  # secs_before
        int,  # acknowledged
        int,  # identifier
    ]:
        return (
            self.event_id,
            self.secs_before,
            self.acknowledged,
            self.identifier,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            row: tuple[int, int, int, int],
    ) -> 'ReminderEntry':
        return cls(
            identifier=row[0],
            event_id=row[1],
            secs_before=row[2],
            acknowledged=bool(row[3]),
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
            blockchain: SupportedBlockchain | None = None,
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

        filters: list[DBFilter] = [filter_query.timestamp_filter]
        if addresses is not None:
            filters.append(DBOptionalChainAddressesFilter(
                and_op=False,
                optional_chain_addresses=addresses,
            ))
        if name is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='name',
                value=name,
            ))
        if description is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='description',
                value=description,
            ))
        if counterparty is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='counterparty',
                value=counterparty,
            ))
        if identifiers is not None:
            filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='identifier',
                values=identifiers,
            ))
        if blockchain is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='blockchain',
                value=blockchain.value,
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
                    'address, blockchain, color, auto_delete) VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
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
                'blockchain, color, auto_delete FROM calendar ' + query,
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

    def delete_entry(
            self,
            identifier: int,
            entry_type: Literal['calendar', 'calendar_reminders'],
    ) -> None:
        """
        Delete calendar entries or reminders by identifier based on the entry_type
        May raise:
        - InputError: if no event got deleted
        """
        with self.db.user_write() as write_cursor:
            write_cursor.execute(f'DELETE FROM {entry_type} WHERE identifier=?', (identifier,))
            if write_cursor.rowcount != 1:
                raise InputError(f'Tried to delete a non existent {entry_type} entry')

    def update_calendar_entry(self, calendar: CalendarEntry) -> int:
        """Update the event with the given identifier using the data provided.
        May raise:
        - InputError if no event got updated
        """
        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE calendar SET name=?, timestamp=?, description=?, counterparty=?, address=?, blockchain=?, color=?, auto_delete=? WHERE identifier=?',  # noqa: E501
                    calendar.serialize_for_db(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update calendar entry due to {e}') from e

        return calendar.identifier

    def create_reminder_entries(
            self,
            reminders: list[ReminderEntry],
    ) -> tuple[list[int], list[int]]:
        """Insert the provided list of event reminder in the database.
        May raise:
        - InputError if any db constraint is not satisfied
        """
        success_added, failed_to_add = [], []
        with self.db.user_write() as write_cursor:
            for entry in reminders:
                try:
                    write_cursor.execute(
                        'INSERT OR IGNORE INTO calendar_reminders(event_id, secs_before, acknowledged) '  # noqa: E501
                        'VALUES (?, ?, ?) RETURNING identifier',
                        entry.serialize_for_db()[:-1],  # exclude the default identifier since we need to create it  # noqa: E501
                    )
                except (sqlcipher.IntegrityError, sqlcipher.OperationalError):  # pylint: disable=no-member
                    failed_to_add.append(entry.event_id)
                else:
                    success_added.append(entry.event_id)

        return success_added, failed_to_add

    def update_reminder_entry(self, reminder: ReminderEntry) -> int:
        """Update reminder in the database
        - InputError if no event reminder got updated
        """
        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE calendar_reminders SET event_id=?, secs_before=?, acknowledged=? WHERE identifier=?',  # noqa: E501
                    reminder.serialize_for_db(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update reminder due to {e}') from e

        return reminder.identifier

    def query_reminder_entry(self, event_id: int) -> dict[str, list[ReminderEntry]]:
        """Query reminder using the id of the linked event"""
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT identifier, event_id, secs_before, acknowledged FROM calendar_reminders '
                'WHERE event_id=? ORDER BY secs_before ASC',
                (event_id,),
            )
            return {'entries': [ReminderEntry.deserialize_from_db(row) for row in cursor]}

    def count_reminder_entries(self, event_id: int) -> int:
        """Count the existing reminders using the id of the linked event"""
        with self.db.conn.read_ctx() as cursor:
            return cursor.execute(
                'SELECT COUNT(*) FROM calendar_reminders WHERE event_id=?',
                (event_id,),
            ).fetchone()[0]
