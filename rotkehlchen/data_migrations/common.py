from typing import TYPE_CHECKING

from rotkehlchen.types import AddressbookEntry

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


def migrate_addressbook_none_to_ecosystem_key(connection: 'DBConnection') -> None:
    """Replace 'NONE' blockchain marker in address_book with ecosystem-specific keys.

    Some names are flagged as valid on every chain in the ecosystem. This change
    ensures those names are included in the output even when a specific chain
    filter is applied, keeping results relevant.
    """

    with connection.read_ctx() as cursor:
        cursor.execute('SELECT address, name FROM address_book WHERE blockchain=?', ('NONE',))
        inserts = [
            (address, AddressbookEntry.get_ecosystem_key_by_address(address), name)
            for address, name in cursor
        ]

    if len(inserts) == 0:
        return

    with connection.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO address_book(address, blockchain, name) VALUES(?, ?, ?)',
            inserts,
        )
        write_cursor.execute('DELETE FROM address_book WHERE blockchain=?', ('NONE',))
