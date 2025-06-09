from typing import TYPE_CHECKING

from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor


class DBLoopring:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_accountid_mapping(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            account_id: int,
    ) -> None:
        write_cursor.execute(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            (f'loopring_{address}_account_id', str(account_id)),
        )

    def remove_accountid_mapping(self, write_cursor: 'DBCursor', address: ChecksumEvmAddress) -> None:  # noqa: E501
        write_cursor.execute(
            'DELETE FROM multisettings WHERE name=?;',
            (f'loopring_{address}_account_id',),
        )

    def get_accountid_mapping(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
    ) -> int | None:
        cursor.execute(
            'SELECT value FROM multisettings WHERE name=?;',
            (f'loopring_{address}_account_id',),
        )
        query = cursor.fetchone()
        if query is None or query[0] is None:
            return None

        return int(query[0])
