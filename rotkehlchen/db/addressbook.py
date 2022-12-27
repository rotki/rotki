import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional, Union

from pysqlcipher3 import dbapi2

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)

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
            optional_chain_addresses: Optional[list[OptionalChainAddress]] = None,
    ) -> list[AddressbookEntry]:
        """
        Returns addressbook entries for the given pairs (address, blockhain).
        If blockchain is None for a given pair, returns all entries for the pair's address.
        """
        entries = []
        if optional_chain_addresses is None:
            cursor.execute('SELECT address, name, blockchain FROM address_book')
            for address, name, blockchain_str in cursor:
                deserialized_blockchain = SupportedBlockchain(blockchain_str) if blockchain_str is not None else None  # noqa: E501
                entries.append(AddressbookEntry(
                    address=ChecksumEvmAddress(address),
                    name=name,
                    blockchain=deserialized_blockchain,
                ))
        else:  # group the addresses by blockchain to minimize the number of db queries
            query_filters = []
            bindings: list[Union[str, ChecksumEvmAddress]] = []
            for optional_chain_address in optional_chain_addresses:
                query_part = 'address = ?'
                bindings.append(optional_chain_address.address)
                if optional_chain_address.blockchain is not None:
                    query_part += ' AND blockchain = ?'
                    bindings.append(optional_chain_address.blockchain.value)

                query_filters.append(query_part)

            query_str_filter = ' OR '.join(query_filters)
            query = 'SELECT address, name, blockchain FROM address_book WHERE ' + query_str_filter  # noqa: E501
            cursor.execute(query, bindings)
            for address, name, blockchain_str in cursor:
                entries.append(AddressbookEntry(
                    address=ChecksumEvmAddress(address),
                    name=name,
                    blockchain=SupportedBlockchain(blockchain_str) if blockchain_str is not None else None,  # noqa: E501
                ))

        return entries

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> None:
        """
        Add every entry of entries to the address book table.
        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        with self.write_ctx(book_type) as write_cursor:
            # We iterate here with for loop instead of executemany in order to catch
            # which identifier is duplicated
            for entry in entries:
                try:
                    # in the case of given blockchain being None delete any other entry for that
                    # address since they are rendered redundant
                    if entry.blockchain is None:
                        write_cursor.execute(
                            'DELETE FROM address_book where address=? AND blockchain IS NOT NULL',
                            (entry.address,),
                        )

                    write_cursor.execute(
                        'INSERT INTO address_book (address, name, blockchain) VALUES (?, ?, ?)',
                        entry.serialize_for_db(),
                    )
                # Handling both private db (pysqlcipher) and global db (raw sqlite3)
                except (dbapi2.IntegrityError, sqlite3.IntegrityError) as e:  # pylint: disable=no-member  # noqa: E501
                    raise InputError(
                        f'{entry} already exists in the address book. Identifier must be unique.',
                    ) from e

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> None:
        """Updates names of addressbook entries."""
        with self.write_ctx(book_type) as write_cursor:
            for entry in entries:
                query = 'UPDATE address_book SET name = ? WHERE address = ? AND blockchain = ?'
                bindings = (entry.name, entry.address, entry.blockchain.value if entry.blockchain else None)  # noqa: E501
                write_cursor.execute(query, bindings)
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'{entry} doesn\'t exist in the address book. So it cannot be modified.',
                    )

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            chain_addresses: list[OptionalChainAddress],
    ) -> None:
        """Delete addressbook entries.
        May raise:
        - InputError: if any of the addresses that need to be deleted is not present in the
        addressbook
        """
        # fist check that all addresses exist locally. Since each address can have multiple
        # blockchains entry we need to count them before trying to delete
        addresses = {chain_address.address for chain_address in chain_addresses}
        with self.read_ctx(book_type) as read_cursor:
            read_cursor.execute(
                f'SELECT DISTINCT address FROM address_book WHERE address IN ({",".join("?"*len(chain_addresses))})',  # noqa: E501
                list(addresses),
            )
            db_addresses = {row[0] for row in read_cursor}
            if len(addresses) != len(db_addresses):
                raise InputError(f'Addresses {addresses} are not present in the database')

        delete_without_blockchain = 'DELETE FROM address_book WHERE address = ?'
        delete_with_blockchain = delete_without_blockchain + ' AND blockchain = ?'
        bindings_without_blockchain = []
        binding_with_blockchain = []
        for address, blockchain in chain_addresses:
            if blockchain is not None:
                binding_with_blockchain.append((address, blockchain.value))
            else:
                bindings_without_blockchain.append((address,))

        with self.write_ctx(book_type) as write_cursor:
            if len(binding_with_blockchain) != 0:
                write_cursor.executemany(delete_with_blockchain, binding_with_blockchain)
                if write_cursor.rowcount != len(binding_with_blockchain):
                    raise InputError('One or more of the addresses with blockchains provided do not exist in the database')  # noqa: E501
            if len(bindings_without_blockchain) != 0:
                # In this case it can happen that we delete more entries than addresses because
                # each address has one or more rows
                write_cursor.executemany(delete_without_blockchain, bindings_without_blockchain)

    def get_addressbook_entry_name(
            self,
            book_type: AddressbookType,
            chain_address: OptionalChainAddress,
    ) -> Optional[str]:
        """
        Returns the name for the specified address and blockchain or None if either there is
        no name set or the pair (address, blockchain) doesn't exist in the database.
        """
        with self.read_ctx(book_type) as read_cursor:
            query = read_cursor.execute(
                'SELECT name FROM address_book WHERE address=? AND blockchain=?',
                (chain_address.address, chain_address.blockchain.value if chain_address.blockchain is not None else None),  # noqa: E501
            )
            result = query.fetchone()

        return None if result is None else result[0]
