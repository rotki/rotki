from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor, DBWriterClient
    from rotkehlchen.db.filtering import AddressbookFilterQuery


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
    def write_ctx(self, book_type: AddressbookType) -> Generator['DBWriterClient', None, None]:
        if book_type == AddressbookType.GLOBAL:
            with GlobalDBHandler().conn.write_ctx() as cursor:
                yield cursor
                return
        # else
        with self.db.user_write() as cursor:
            yield cursor

    def get_addressbook_entries(
            self,
            cursor: 'DBCursor',
            filter_query: 'AddressbookFilterQuery',
    ) -> tuple[list[AddressbookEntry], int]:
        """
        Returns paginated addressbook entries for the given pairs (address, blockchain).
        If blockchain is None for a given pair, returns all entries for the pair's address.
        """
        query, bindings = filter_query.prepare(with_pagination=False) if filter_query is not None else ('', [])  # noqa: E501
        query = 'SELECT COUNT(*) FROM address_book ' + query
        total_found_result: int = cursor.execute(query, bindings).fetchone()[0]

        query, bindings = filter_query.prepare() if filter_query is not None else ('', [])
        query = 'SELECT address, name, blockchain FROM address_book ' + query
        cursor.execute(query, bindings)
        entries = [
            AddressbookEntry(
                address=ChecksumEvmAddress(address),
                name=name,
                blockchain=SupportedBlockchain(blockchain_str) if blockchain_str != ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE else None,  # noqa: E501
            ) for address, name, blockchain_str in cursor
        ]
        return entries, total_found_result

    def add_or_update_addressbook_entries(
            self,
            write_cursor: 'DBWriterClient',
            entries: list[AddressbookEntry],
    ) -> None:
        """Adds new or updates existing addressbook entries.

        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        # We iterate here with for loop instead of executemany in order to catch
        # which identifier is duplicated
        for entry in entries:
            # in the case of given blockchain being None delete any other entry for that
            # address since they are rendered redundant
            if entry.blockchain is None:
                write_cursor.execute(
                    'DELETE FROM address_book where address=? AND blockchain IS NOT ?',
                    (entry.address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE),
                )

            write_cursor.execute(
                'INSERT OR REPLACE INTO address_book (address, name, blockchain) VALUES (?, ?, ?)',
                entry.serialize_for_db(),
            )

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> None:
        """Updates names of addressbook entries.
        Add entry if it doesn't exist. Delete entry if the name is blank
        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        with self.write_ctx(book_type) as write_cursor:
            for entry in entries:
                if entry.name == '':   # Handle deletion case
                    entry_blockchain_value = (
                        entry.blockchain.value if entry.blockchain
                        else ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE
                    )
                    write_cursor.execute(
                        'DELETE FROM address_book WHERE address = ? AND blockchain = ?',
                        (entry.address, entry_blockchain_value),
                    )
                    if write_cursor.rowcount == 0:
                        raise InputError(
                            f'Entry with address "{entry.address}" and blockchain {entry.blockchain} '  # noqa: E501
                            f"doesn't exist in the address book. So it cannot be modified.",
                        )
                else:  # insert or update
                    self.add_or_update_addressbook_entries(write_cursor, [entry])

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
                f'SELECT DISTINCT address FROM address_book WHERE address IN ({",".join("?" * len(chain_addresses))})',  # noqa: E501
                list(addresses),
            )
            db_addresses = {row[0] for row in read_cursor}
            if len(addresses) != len(db_addresses):
                raise InputError(f'Addresses {addresses} are not present in the database')

        delete_without_blockchain = 'DELETE FROM address_book WHERE address = ?'
        delete_with_blockchain = delete_without_blockchain + ' AND blockchain IS ?'
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
    ) -> str | None:
        """
        Returns the name for the specified address and blockchain.
        It will search for the pair of address and the exact blockchain (or null).
        If it's not found, it will search for the pair of address
        with blockchain=NULL (meaning, for all chains).
        Otherwise, it will return None.

        The `ORDER BY` part on the query is to prioritize the one with exact blockchain
        instead of the NULL one.
        """
        with self.read_ctx(book_type) as read_cursor:
            read_cursor.execute(
                'SELECT name FROM address_book WHERE address=? AND (blockchain IS ? OR blockchain IS ?) ORDER BY blockchain DESC',  # noqa: E501
                (
                    chain_address.address,
                    chain_address.blockchain.value if chain_address.blockchain is not None else ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,  # noqa: E501
                    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
                ),
            )
            result = read_cursor.fetchone()

        return None if result is None else result[0]

    def maybe_make_entry_name_multichain(
            self,
            address: ChecksumEvmAddress,
            book_type: AddressbookType = AddressbookType.PRIVATE,
    ) -> None:
        """Make the existing name for the specified address apply to all chains.
        If there is no existing name or if there are different names for it in different chains,
        then no action is taken.
        """
        with self.read_ctx(book_type) as cursor:
            if (entry_count := len(names := cursor.execute(
                'SELECT name FROM address_book WHERE address=?',
                (address,),
            ).fetchall())) == 0 or len(set(names)) > 1:
                return  # If no name, or different names on different chains, leave as is.

        # else, make the name multichain
        with self.write_ctx(book_type) as write_cursor:
            if entry_count == 1:  # Only one entry. Just update it.
                write_cursor.execute(
                    'UPDATE address_book SET blockchain=? WHERE address=?',
                    (ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, address),
                )
            else:  # Same label is set on multiple chains. Delete existing entries and add new one.
                self.add_or_update_addressbook_entries(
                    write_cursor=write_cursor,
                    entries=[AddressbookEntry(address=address, name=names[0][0], blockchain=None)],
                )
