"""Repository for managing user notes in the database."""
from typing import TYPE_CHECKING

from rotkehlchen.constants.limits import FREE_USER_NOTES_LIMIT
from rotkehlchen.db.filtering import UserNotesFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import UserNote
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


class UserNotesRepository:
    """Repository for handling all user notes operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the user notes repository."""
        self.msg_aggregator = msg_aggregator

    def add(
            self,
            write_cursor: 'DBCursor',
            title: str,
            content: str,
            location: str,
            is_pinned: bool,
            has_premium: bool,
    ) -> int:
        """Add a new user note to the database.

        May raise:
        - InputError: If note limit exceeded for free users
        """
        # Check note limit for free users
        if not has_premium:
            write_cursor.execute('SELECT COUNT(*) FROM user_notes')
            count = write_cursor.fetchone()[0]
            if count >= FREE_USER_NOTES_LIMIT:
                msg = (
                    f'The limit of {FREE_USER_NOTES_LIMIT} user notes has been '
                    f'reached in the free plan. To get more notes you can upgrade to '
                    f'premium: https://rotki.com/products'
                )
                raise InputError(msg)

        write_cursor.execute(
            'INSERT INTO user_notes(title, content, location, last_update_timestamp, is_pinned) '
            'VALUES(?, ?, ?, ?, ?)',
            (title, content, location, ts_now(), is_pinned),
        )
        return write_cursor.lastrowid

    def update(
            self,
            write_cursor: 'DBCursor',
            user_note: UserNote,
    ) -> None:
        """Update an existing user note.

        May raise:
        - InputError: If note with identifier doesn't exist
        """
        write_cursor.execute(
            'UPDATE user_notes SET title=?, content=?, last_update_timestamp=?, is_pinned=? '
            'WHERE identifier=?',
            (
                user_note.title,
                user_note.content,
                ts_now(),
                user_note.is_pinned,
                user_note.identifier,
            ),
        )
        if write_cursor.rowcount == 0:
            raise InputError(f'User note with identifier {user_note.identifier} does not exist')

    def delete(
            self,
            write_cursor: 'DBCursor',
            identifier: int,
    ) -> None:
        """Delete a user note.

        May raise:
        - InputError: If note with identifier doesn't exist
        """
        write_cursor.execute('DELETE FROM user_notes WHERE identifier=?', (identifier,))
        if write_cursor.rowcount == 0:
            raise InputError(f'User note with identifier {identifier} not found in database')

    def get_notes(
            self,
            cursor: 'DBCursor',
            filter_query: UserNotesFilterQuery,
            has_premium: bool,
    ) -> list[UserNote]:
        """Get user notes with optional filtering and pagination."""
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT identifier, title, content, location, last_update_timestamp, is_pinned FROM user_notes ' + query  # noqa: E501
            cursor.execute(query, bindings)
        else:
            query = 'SELECT identifier, title, content, location, last_update_timestamp, is_pinned FROM (SELECT identifier, title, content, location, last_update_timestamp, is_pinned from user_notes ORDER BY last_update_timestamp DESC LIMIT ?) ' + query  # noqa: E501
            cursor.execute(query, [FREE_USER_NOTES_LIMIT] + bindings)

        return [UserNote.deserialize_from_db(entry) for entry in cursor]

    def get_notes_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: UserNotesFilterQuery,
            has_premium: bool,
    ) -> tuple[list[UserNote], int]:
        """Gets all user_notes for the query from the DB

        Also returns how many are the total found for the filter
        """
        user_notes = self.get_notes(cursor, filter_query, has_premium)
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from user_notes ' + query
        total_found_result = cursor.execute(query, bindings)
        return user_notes, total_found_result.fetchone()[0]

    def get_note_by_id(
            self,
            cursor: 'DBCursor',
            identifier: int,
    ) -> UserNote | None:
        """Get a specific user note by identifier."""
        cursor.execute(
            'SELECT identifier, title, content, location, last_update_timestamp, is_pinned '
            'FROM user_notes WHERE identifier=?',
            (identifier,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return UserNote.deserialize_from_db(row)

    def get_note_count(self, cursor: 'DBCursor') -> int:
        """Get total count of user notes."""
        cursor.execute('SELECT COUNT(*) FROM user_notes')
        return cursor.fetchone()[0]
