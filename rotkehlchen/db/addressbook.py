import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, List, Optional

from pysqlcipher3 import dbapi2

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.types import AddressbookEntry, AddressbookType, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class DBAddressbook:

    def __init__(self, db_handler: DBHandler) -> None:
        self.db = db_handler

    @contextmanager
    def read_ctx(self, book_type: AddressbookType) -> Generator['DBCursor', None, None]:
        if book_type == AddressbookType.GLOBAL:
            with GlobalDBHandler().conn.read_ctx() as cursor:
                yield cursor
                return
        # else
        with self.db.conn.read_ctx() as cursor:
            yield cursor

    @contextmanager
    def write_ctx(self, book_type: AddressbookType) -> Generator['DBCursor', None, None]:
        if book_type == AddressbookType.GLOBAL:
            with GlobalDBHandler().conn.write_ctx() as cursor:
                yield cursor
                return
        # else
        with self.db.user_write() as cursor:
            yield cursor

    def get_addressbook_entries(  # pylint: disable=no-self-use
            self,
            cursor: 'DBCursor',
            addresses: Optional[List[ChecksumEvmAddress]] = None,
    ) -> List[AddressbookEntry]:
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
            entries.append(AddressbookEntry(address=ChecksumEvmAddress(address), name=name))

        return entries

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: List[AddressbookEntry],
    ) -> None:
        with self.write_ctx(book_type) as write_cursor:
            # We iterate here with for loop instead of executemany in order to catch
            # which identifier is duplicated
            for entry in entries:
                try:
                    write_cursor.execute(
                        'INSERT INTO address_book (address, name) VALUES (?, ?)',
                        (entry.address, entry.name),
                    )
                # Handling both private db (pysqlcipher) and global db (raw sqlite3)
                except (dbapi2.IntegrityError, sqlite3.IntegrityError) as e:  # pylint: disable=no-member  # noqa: E501
                    raise InputError(
                        f'Addressbook entry with address "{entry.address}" and name "{entry.name}"'
                        f' already exists in the address book. Identifier must be unique.',
                    ) from e

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: List[AddressbookEntry],
    ) -> None:
        with self.write_ctx(book_type) as write_cursor:
            for entry in entries:
                write_cursor.execute(
                    'UPDATE address_book SET name = ? WHERE address = ?',
                    (entry.name, entry.address),
                )
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'Addressbook entry with address "{entry.address}" and name "{entry.name}"'
                        f' doesn\'t exist in the address book. So it cannot be modified.',
                    )

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            addresses: List[ChecksumEvmAddress],
    ) -> None:
        with self.write_ctx(book_type) as write_cursor:
            for address in addresses:
                write_cursor.execute('DELETE FROM address_book WHERE address = ?', (address,))
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'Addressbook entry with address "{address}" '
                        f'doesn\'t exist in the address book. So it cannot be deleted.',
                    )
