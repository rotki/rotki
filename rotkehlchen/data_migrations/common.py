import logging
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import AddressNotSupported
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import AddressbookEntry

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def migrate_addressbook_none_to_ecosystem_key(
        connection: 'DBConnection',
        msg_aggregator: 'MessagesAggregator | None' = None,
) -> None:
    """Replace 'NONE' blockchain marker in address_book with ecosystem-specific keys.

    Some names are flagged as valid on every chain in the ecosystem. This change
    ensures those names are included in the output even when a specific chain
    filter is applied, keeping results relevant.
    """
    inserts = []
    with connection.read_ctx() as cursor:
        cursor.execute('SELECT address, name FROM address_book WHERE blockchain=?', ('NONE',))
        for address, name in cursor:
            try:
                inserts.append(
                    (address, AddressbookEntry.get_ecosystem_key_by_address(address), name),
                )
            except AddressNotSupported as e:
                log.critical(e)  # log critical so it is kept in the log file
                if msg_aggregator is not None:
                    msg_aggregator.add_error(f"Address {address} with name {name} could not be moved while updating the addressbook. Please save it if it's important for you.")  # noqa: E501

    if len(inserts) == 0:
        return

    with connection.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO address_book(address, blockchain, name) VALUES(?, ?, ?)',
            inserts,
        )
        write_cursor.execute('DELETE FROM address_book WHERE blockchain=?', ('NONE',))
