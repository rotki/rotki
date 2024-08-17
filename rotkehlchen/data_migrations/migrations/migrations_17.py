import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_17(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """
    Introduced at v1.34.3

    For both the user db and the globaldb ensure that if there are duplicates in the
    table for the address book we delete them except the one with the highest rowid
    (latest inserted) and set the blockchain value with the constant
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE to avoid having NULL values.
    """
    progress_handler.set_total_steps(2)

    for conn in (rotki.data.db.conn, GlobalDBHandler().conn):
        with conn.read_ctx() as cursor:
            cursor.execute('SELECT address FROM address_book WHERE blockchain IS NULL GROUP BY address HAVING COUNT(address) > 1;')  # noqa: E501
            invalid_addresses = [(x[0], x[0]) for x in cursor]

        with conn.write_ctx() as write_cursor:
            if len(invalid_addresses) != 0:
                write_cursor.executemany(
                    'DELETE FROM address_book WHERE address=? AND rowid NOT IN (SELECT MAX(rowid) FROM address_book WHERE blockchain IS NULL AND address=?);',  # noqa: E501
                    invalid_addresses,
                )

            write_cursor.execute(
                'UPDATE address_book SET blockchain=? WHERE blockchain IS NULL',
                (ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,),
            )

        progress_handler.new_step()
