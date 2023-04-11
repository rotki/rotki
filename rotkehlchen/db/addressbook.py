import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal, Optional, overload

from pysqlcipher3 import dbapi2

from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    AddressbookType,
    GlobalAddressbookSource,
    NamedAddressbookEntry,
    OptionalChainAddress,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import BaseAddressbookFilterQuery


class DBAddressbook:

    def __init__(self, db_handler: 'DBHandler') -> None:
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

    def get_addressbook_entries(
            self,
            filter_query: 'BaseAddressbookFilterQuery',
    ) -> list[NamedAddressbookEntry]:
        """
        Returns addressbook entries for the given pairs (address, blockchain).
        If blockchain is None for a given pair, returns all entries for the pair's address.
        """
        query, bindings = filter_query.prepare()
        with self.read_ctx(filter_query.get_book_type()) as cursor:
            entries = []
            cursor.execute(filter_query.get_base_query() + query, bindings)
            for db_entry in cursor:
                entries.append(
                    filter_query.get_book_type().get_class().deserialize_from_db(db_entry),
                )

        return entries

    def add_addressbook_entries(
            self,
            write_cursor: 'DBCursor',
            book_type: AddressbookType,
            entries: list[NamedAddressbookEntry],
    ) -> None:
        """
        Add every entry of entries to the address book table.
        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        deletion_statement = 'DELETE FROM address_book where address=? AND blockchain IS NOT NULL'
        if book_type == AddressbookType.USER:
            insertion_statement = 'INSERT INTO address_book (address, name, blockchain) VALUES (?, ?, ?)'  # noqa: E501
        else:
            insertion_statement = 'INSERT INTO address_book (address, name, blockchain, source) VALUES (?, ?, ?, ?)'  # noqa: E501
            deletion_statement += ' AND source=?'
        # We iterate here with for loop instead of executemany in order to catch
        # which identifier is duplicated
        for entry in entries:
            try:
                # in the case of given blockchain being None delete any other entry for that
                # address since they are rendered redundant
                if entry.blockchain is None:
                    bindings = [entry.address]
                    if book_type == AddressbookType.GLOBAL:
                        bindings.append(entry.source.serialize_for_db())  # type: ignore[attr-defined]  # noqa: E501
                    write_cursor.execute(deletion_statement, bindings)

                write_cursor.execute(insertion_statement, entry.serialize_for_db())
            # Handling both private db (pysqlcipher) and global db (raw sqlite3)
            except (dbapi2.IntegrityError, sqlite3.IntegrityError) as e:  # pylint: disable=no-member  # noqa: E501
                raise InputError(
                    f'{entry} already exists in the address book. Identifier must be unique.',
                ) from e

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[NamedAddressbookEntry],
    ) -> None:
        """Updates names of addressbook entries."""
        statement = 'UPDATE address_book SET name = ? WHERE address = ? AND blockchain IS ?'
        if book_type == AddressbookType.GLOBAL:
            statement += ' AND source=?'
        with self.write_ctx(book_type) as write_cursor:
            for entry in entries:
                bindings = [entry.name, entry.address, entry.blockchain.value if entry.blockchain else None]  # noqa: E501
                if book_type == AddressbookType.GLOBAL:
                    bindings.append(entry.source.serialize_for_db())  # type: ignore[attr-defined]
                write_cursor.execute(statement, bindings)
                if write_cursor.rowcount == 0:
                    raise InputError(
                        f'Entry {str(entry)} doesn\'t exist in the address book. '
                        f'So it cannot be modified.',
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
        # blockchains entries we need to count them before trying to delete
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
        if book_type == AddressbookType.GLOBAL:
            delete_without_blockchain += ' AND source=?'
        delete_with_blockchain = delete_without_blockchain + ' AND blockchain IS ?'
        bindings_without_blockchain = []
        binding_with_blockchain = []
        for properties in chain_addresses:
            binding: list[Any] = [properties.address]
            if book_type == AddressbookType.GLOBAL:
                binding.append(GlobalAddressbookSource.MANUAL.serialize_for_db())
            if properties.blockchain is not None:
                binding_with_blockchain.append([*binding, properties.blockchain.value])
            else:
                bindings_without_blockchain.append(binding)

        with self.write_ctx(book_type) as write_cursor:
            if len(binding_with_blockchain) != 0:
                write_cursor.executemany(delete_with_blockchain, binding_with_blockchain)
                if write_cursor.rowcount != len(binding_with_blockchain):
                    raise InputError('One or more of the addresses with blockchains provided do not exist in the database')  # noqa: E501
            if len(bindings_without_blockchain) != 0:
                # In this case it can happen that we delete more entries than addresses because
                # each address has one or more rows
                write_cursor.executemany(delete_without_blockchain, bindings_without_blockchain)

    @overload
    def get_addressbook_entry_name(
            self,
            book_type: Literal[AddressbookType.USER],
            chain_address: OptionalChainAddress,
    ) -> Optional[str]:
        ...

    @overload
    def get_addressbook_entry_name(
            self,
            book_type: Literal[AddressbookType.GLOBAL],
            chain_address: OptionalChainAddress,
            priorities: dict[GlobalAddressbookSource, int],
    ) -> Optional[str]:
        ...

    def get_addressbook_entry_name(
            self,
            book_type: AddressbookType,
            chain_address: OptionalChainAddress,
            priorities: Optional[dict[GlobalAddressbookSource, int]] = None,
    ) -> Optional[str]:
        """
        Returns the name for the specified address and blockchain or None if either there is
        no name set or the pair (address, blockchain) doesn't exist in the database.
        """
        if book_type == AddressbookType.USER:
            query = 'SELECT name FROM address_book WHERE address=? AND blockchain IS ?'
        else:
            query = 'SELECT name, source FROM address_book WHERE address=? AND blockchain IS ?'
        bindings = [chain_address.address, chain_address.blockchain.value if chain_address.blockchain is not None else None]  # noqa: E501
        with self.read_ctx(book_type) as cursor:
            result = cursor.execute(query, bindings).fetchall()

        if len(result) == 0:
            return None
        elif book_type == AddressbookType.USER:
            return result[0][0]  # There is always a single entry for user address book
        else:  # global address book
            deserialized_result = [
                (name, GlobalAddressbookSource.deserialize_from_db(source))
                for name, source in result
            ]
            deserialized_result.sort(key=lambda entry: priorities[entry[1]])  # type: ignore  # for global address book priorities is not None  # noqa: E501
            return deserialized_result[0][0]  # Return only the top name
