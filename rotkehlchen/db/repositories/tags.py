"""Repository for managing tags in the database."""
import logging
from typing import TYPE_CHECKING, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.db.utils import Tag
from rotkehlchen.errors.misc import InputError, TagConstraintError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code
from rotkehlchen.types import HexColorCode

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


class TagsRepository:
    """Repository for handling all tag-related operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the tags repository."""
        self.msg_aggregator = msg_aggregator

    def get_all(self, cursor: 'DBCursor') -> dict[str, Tag]:
        """Get all tags from the database."""
        tags_mapping: dict[str, Tag] = {}
        cursor.execute(
            'SELECT name, description, background_color, foreground_color FROM tags;',
        )
        for result in cursor:
            name = result[0]
            description = result[1]

            if description is not None and not isinstance(description, str):
                self.msg_aggregator.add_warning(
                    f'Tag {name} with invalid description found in the DB. Skipping tag',
                )
                continue

            try:
                background_color = deserialize_hex_color_code(result[2])
                foreground_color = deserialize_hex_color_code(result[3])
            except DeserializationError as e:
                self.msg_aggregator.add_warning(
                    f'Tag {name} with invalid color code found in the DB. {e!s}. Skipping tag',
                )
                continue

            tags_mapping[name] = Tag(
                name=name,
                description=description,
                background_color=background_color,
                foreground_color=foreground_color,
            )

        return tags_mapping

    def add(
            self,
            write_cursor: 'DBCursor',
            name: str,
            description: str | None,
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> None:
        """Adds a new tag to the DB

        Raises:
        - TagConstraintError: If the tag with the given name already exists
        """
        try:
            write_cursor.execute(
                'INSERT INTO tags'
                '(name, description, background_color, foreground_color) VALUES (?, ?, ?, ?)',
                (name, description, background_color, foreground_color),
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            msg = str(e)
            if 'UNIQUE constraint failed: tags.name' in msg:
                raise TagConstraintError(
                    f'Tag with name {name} already exists. Tag name matching is case insensitive.',
                ) from e

            # else something really bad happened
            log.error(f'Unexpected DB error: {msg} while adding a tag')
            raise

    def edit(
            self,
            write_cursor: 'DBCursor',
            name: str,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
    ) -> None:
        """Edits a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to edit does not exist in the DB
        - InputError: If no field to edit was given.
        """
        query_values = []
        querystr = 'UPDATE tags SET '
        if description is not None:
            querystr += 'description = ?,'
            query_values.append(description)
        if background_color is not None:
            querystr += 'background_color = ?,'
            query_values.append(background_color)
        if foreground_color is not None:
            querystr += 'foreground_color = ?,'
            query_values.append(foreground_color)

        if len(query_values) == 0:
            raise InputError(f'No field was given to edit for tag "{name}"')

        querystr = querystr[:-1] + 'WHERE name = ?;'
        query_values.append(name)
        write_cursor.execute(querystr, query_values)
        if write_cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to edit tag with name "{name}" which does not exist',
            )

    def delete(self, write_cursor: 'DBCursor', name: str) -> None:
        """Deletes a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to delete does not exist in the DB
        """
        # Delete the tag mappings for all affected accounts
        write_cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'tag_name = ?;', (name,),
        )
        write_cursor.execute('DELETE from tags WHERE name = ?;', (name,))
        if write_cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to delete tag with name "{name}" which does not exist',
            )

    def ensure_tags_exist(
            self,
            cursor: 'DBCursor',
            given_data: (
                list[SingleBlockchainAccountData] |
                list[BlockchainAccountData] |
                list[ManuallyTrackedBalance] |
                list[XpubData]
            ),
            action: Literal['adding', 'editing'],
            data_type: Literal['blockchain accounts', 'manually tracked balances', 'bitcoin xpub', 'bitcoin cash xpub'],  # noqa: E501
    ) -> None:
        """Make sure that tags included in the data exist in the DB

        May Raise:
        - TagConstraintError if the tags don't exist in the DB
        """
        existing_tags = self.get_all(cursor)
        # tag comparison is case-insensitive
        existing_tag_keys = [key.lower() for key in existing_tags]

        unknown_tags: set[str] = set()
        for entry in given_data:
            if entry.tags is not None:
                unknown_tags.update(
                    # tag comparison is case-insensitive
                    {t.lower() for t in entry.tags}.difference(existing_tag_keys),
                )

        if len(unknown_tags) != 0:
            raise TagConstraintError(
                f'When {action} {data_type}, unknown tags '
                f'{", ".join(unknown_tags)} were found',
            )