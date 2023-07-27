from typing import TYPE_CHECKING

from rotkehlchen.db.upgrades.v38_v39 import DEFAULT_ARBITRUM_ONE_NODES_AT_V39

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


def globaldb_data_migration_2(conn: 'DBConnection') -> None:
    """Introduced at 1.30.0
    - Ensures that globaldb is populated with arbitrum nodes and doesn't contain duplicates
    """
    endpoints = [entry[1] for entry in DEFAULT_ARBITRUM_ONE_NODES_AT_V39]
    with conn.write_ctx() as write_cursor:
        write_cursor.execute(
            f'SELECT endpoint from default_rpc_nodes WHERE endpoint IN ({",".join("?" * len(endpoints))})',  # noqa: E501
            endpoints,
        )
        existing_endpoints = {row[0] for row in write_cursor}
        insert_tuples = [row for row in DEFAULT_ARBITRUM_ONE_NODES_AT_V39 if row[1] not in existing_endpoints]  # noqa: E501
        write_cursor.executemany(
            'INSERT INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            insert_tuples,
        )
