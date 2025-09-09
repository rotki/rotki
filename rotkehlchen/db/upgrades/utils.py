from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def fix_address_book_duplications(write_cursor: 'DBCursor') -> None:
    """
    Ensure that there are no invalid addresses when upgrading the table.
    This code is moved here from migration 17. It could happen that migration 17 wasn't
    executed when running this upgrade. After this fix we upgrade the address book table.

    This logic is used both in the globaldb upgrade and the userdb upgrade.
    """
    write_cursor.execute('SELECT address FROM address_book WHERE blockchain IS NULL GROUP BY address HAVING COUNT(address) > 1;')  # noqa: E501
    invalid_addresses = [(x[0], x[0]) for x in write_cursor]

    if len(invalid_addresses) != 0:
        write_cursor.executemany(
            'DELETE FROM address_book WHERE address=? AND rowid NOT IN (SELECT MAX(rowid) FROM address_book WHERE blockchain IS NULL AND address=?);',  # noqa: E501
            invalid_addresses,
        )

    write_cursor.execute(
        'UPDATE address_book SET blockchain=? WHERE blockchain IS NULL',
        ('NONE',),
    )

    update_table_schema(
        write_cursor=write_cursor,
        table_name='address_book',
        schema="""address TEXT NOT NULL,
        blockchain TEXT NOT NULL,
        name TEXT NOT NULL,
        PRIMARY KEY(address, blockchain)""",
    )
