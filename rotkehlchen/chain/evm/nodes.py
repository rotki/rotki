from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBCursor, DBWriterClient


def populate_rpc_nodes_in_database(
        db_write_cursor: 'DBWriterClient',
        globaldb_cursor: 'DBCursor',
) -> None:
    """Populates the rpc nodes in the user database from the global DB.

    This is supposed to run for a clean new DB.
    """
    nodes = globaldb_cursor.execute(
        'SELECT name, endpoint, owned, active, weight, blockchain FROM default_rpc_nodes',
    ).fetchall()

    db_write_cursor.executemany(
        'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        nodes,
    )
