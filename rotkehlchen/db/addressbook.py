import sqlite3
from typing import List, Optional

from pysqlcipher3 import dbapi2

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.types import AddressbookEntry, AddressbookType, ChecksumEthAddress


class DBAddressbook:

    def __init__(self, db_handler: DBHandler) -> None:
        self.db = db_handler

    def _get_connection(self, book_type: AddressbookType) -> sqlite3.Connection:
        if book_type == AddressbookType.GLOBAL:
            return GlobalDBHandler().conn
        return self.db.conn

    def get_addressbook_entries(
            self,
            book_type: AddressbookType,
            addresses: Optional[List[ChecksumEthAddress]] = None,
    ) -> List[AddressbookEntry]:
        connection = self._get_connection(book_type)
        cursor = connection.cursor()
        if addresses is None:
            cursor.execute('SELECT address, name FROM address_book')
        else:
            questionmarks = ','.join('?' * len(addresses))
            cursor.execute(
                f'SELECT address, name FROM address_book WHERE address IN ({questionmarks})',
                addresses,
            )

        entries = []
        for address, name in cursor:
            entries.append(AddressbookEntry(address=ChecksumEthAddress(address), name=name))

        return entries

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: List[AddressbookEntry],
    ) -> None:
        connection = self._get_connection(book_type)
        cursor = connection.cursor()
        # We iterate here with for loop instead of executemany in order to catch
        # which identifier is duplicated
        for entry in entries:
            try:
                cursor.execute(
                    'INSERT INTO address_book (address, name) VALUES (?, ?)',
                    (entry.address, entry.name),
                )
            # Handling both private db (pysqlcipher) and global db (raw sqlite3)
            except (dbapi2.IntegrityError, sqlite3.IntegrityError) as e:  # pylint: disable=no-member  # noqa: E501
                connection.rollback()
                raise InputError(
                    f'Addressbook entry with address "{entry.address}" and name "{entry.name}"'
                    f' already exists in the address book. Identifier must be unique.',
                ) from e
        connection.commit()

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: List[AddressbookEntry],
    ) -> None:
        connection = self._get_connection(book_type)
        cursor = connection.cursor()
        for entry in entries:
            cursor.execute(
                'UPDATE address_book SET name = ? WHERE address = ?',
                (entry.name, entry.address),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                raise InputError(
                    f'Addressbook entry with address "{entry.address}" and name "{entry.name}"'
                    f' doesn\'t exist in the address book. So it cannot be modified.',
                )
        connection.commit()

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            addresses: List[ChecksumEthAddress],
    ) -> None:
        connection = self._get_connection(book_type)
        cursor = connection.cursor()
        for address in addresses:
            cursor.execute('DELETE FROM address_book WHERE address = ?', (address,))
            if cursor.rowcount == 0:
                connection.rollback()
                raise InputError(
                    f'Addressbook entry with address "{address}" '
                    f'doesn\'t exist in the address book. So it cannot be deleted.',
                )
        connection.commit()
