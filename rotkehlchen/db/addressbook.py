import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional

from pysqlcipher3 import dbapi2

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


ADDRESSBOOK_DATA_OPTIONAL_BLOCKCHAIN = tuple[ChecksumEvmAddress, str, Optional[SupportedBlockchain]]  # noqa: E501


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
            addresses: Optional[list[
                tuple[ChecksumEvmAddress, Optional[SupportedBlockchain]]
            ]] = None,
    ) -> list[AddressbookEntry]:
        """
        Returns addressbook entries for the given pairs (address, blockhain).
        If blockchain is None, returns all entries for the given address.
        """
        entries = []
        if addresses is None:
            cursor.execute('SELECT address, name, blockchain FROM address_book')
            for address, name, blockchain_str in cursor:
                deserialized_blockchain = SupportedBlockchain(blockchain_str)
                entries.append(AddressbookEntry(
                    address=ChecksumEvmAddress(address),
                    name=name,
                    blockchain=deserialized_blockchain,
                ))
        else:
            for address, blockchain in addresses:
                query = 'SELECT address, name, blockchain FROM address_book WHERE address = ?'
                bindings = [address]
                if blockchain is not None:
                    query += ' AND blockchain = ?'
                    bindings.append(blockchain.value)
                cursor.execute(query, bindings)

                for address, name, blockchain_str in cursor:
                    deserialized_blockchain = SupportedBlockchain(blockchain_str)
                    entries.append(AddressbookEntry(
                        address=ChecksumEvmAddress(address),
                        name=name,
                        blockchain=deserialized_blockchain,
                    ))

        return entries

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> None:
        with self.write_ctx(book_type) as write_cursor:
            # We iterate here with for loop instead of executemany in order to catch
            # which identifier is duplicated
            for entry in entries:
                try:
                    write_cursor.execute(
                        'INSERT INTO address_book (address, name, blockchain) VALUES (?, ?, ?)',
                        (entry.address, entry.name, entry.blockchain.value),
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
            entries: list[ADDRESSBOOK_DATA_OPTIONAL_BLOCKCHAIN],
    ) -> None:
        """
        Updates names of addressbook entries.
        If blockchain is None then update all entries with the specified address.
        """
        with self.write_ctx(book_type) as write_cursor:
            for address, name, blockchain in entries:
                query = 'UPDATE address_book SET name = ? WHERE address = ?'
                bindings = [name, address]
                if blockchain is not None:
                    query += 'AND blockchain = ?'
                    bindings.append(blockchain.value)
                write_cursor.execute(query, bindings)
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'Addressbook entry with address "{address}" and name "{name}"'
                        f' doesn\'t exist in the address book. So it cannot be modified.',
                    )

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            addresses: list[tuple[ChecksumEvmAddress, Optional[SupportedBlockchain]]],
    ) -> None:
        with self.write_ctx(book_type) as write_cursor:
            for address, blockchain in addresses:
                query = 'DELETE FROM address_book WHERE address = ?'
                bindings: list[str] = [address]
                if blockchain is not None:
                    query += ' AND blockchain = ?'
                    bindings.append(blockchain.value)
                write_cursor.execute(query, bindings)
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'Addressbook entry with address "{address}" '
                        f'{f"and blockchain {blockchain.value} " if blockchain is not None else ""}doesnt '  # noqa: E501
                        f'exist in the address book. So it cannot be deleted.',
                    )

    def get_addressbook_entry_name(
            self,
            book_type: AddressbookType,
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
    ) -> Optional[str]:
        """
        Returns the name for the specified address and blockchain.
        Returns None if either there is no name set or pair (address, blockchain)
        doesn't exist in database.
        """
        with self.read_ctx(book_type) as read_cursor:
            query = read_cursor.execute(
                'SELECT name FROM address_book WHERE address=? AND blockchain=?',
                (address, blockchain.value),
            )

            result = query.fetchone()

        return None if result is None else result[0]
