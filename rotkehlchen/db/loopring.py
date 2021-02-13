from typing import TYPE_CHECKING, Optional

from rotkehlchen.typing import ChecksumEthAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBLoopring():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_accountid_mapping(self, address: ChecksumEthAddress, account_id: int) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            (f'loopring_{address}_account_id', str(account_id)),
        )
        self.db.conn.commit()
        self.db.update_last_write()

    def remove_accountid_mapping(self, address: ChecksumEthAddress) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE FROM multisettings WHERE name=?;',
            (f'loopring_{address}_account_id',),
        )
        self.db.conn.commit()
        self.db.update_last_write()

    def get_accountid_mapping(self, address: ChecksumEthAddress) -> Optional[int]:
        cursor = self.db.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM multisettings WHERE name=?;',
            (f'loopring_{address}_account_id',),
        )
        query = query.fetchall()
        if len(query) == 0 or query[0][0] is None:
            return None

        return int(query[0][0])
