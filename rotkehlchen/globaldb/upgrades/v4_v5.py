import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _create_new_tables(cursor: 'DBCursor') -> None:
    log.debug('Enter _create_new_tables')

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS default_rpc_nodes (
            identifier INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            weight TEXT NOT NULL,
            blockchain TEXT NOT NULL
        );
        """,
    )

    log.debug('Exit _create_new_tables')


def _populate_rpc_nodes(cursor: 'DBCursor', root_dir: Path) -> None:
    log.debug('Enter _populate_rpc_nodes')

    with open(root_dir / 'data' / 'nodes.json') as f:
        nodes_info = json.loads(f.read())

    nodes_tuples = [
        (node['name'], node['endpoint'], False, True, str(FVal(node['weight'])), node['blockchain'])  # noqa: E501
        for node in nodes_info
    ]
    log.debug(nodes_tuples)
    cursor.executemany(
        'INSERT INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
        'VALUES (?, ?, ?, ?, ?, ?)',
        nodes_tuples,
    )

    log.debug('Exit _populate_rpc_nodes')


def _reset_curve_cache(write_cursor: 'DBCursor') -> None:
    """Resets curve cache to query gauges and update format of the lp tokens"""
    write_cursor.execute('DELETE FROM general_cache WHERE key LIKE "%CURVE%"')


def _remove_name_from_contracts(cursor: 'DBCursor') -> None:
    """Removes the name column from contract_data table if it exists"""
    cursor.execute(
        'SELECT COUNT(*) from sqlite_master WHERE type="table" AND name="contract_data"',
    )
    table_exists = cursor.fetchone()[0] == 1
    table_creation = 'contract_data'
    if table_exists:
        table_creation = 'contract_data_new'
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_creation} (
        address VARCHAR[42] NOT NULL,
        chain_id INTEGER NOT NULL,
        abi INTEGER NOT NULL,
        deployed_block INTEGER,
        FOREIGN KEY(abi) REFERENCES contract_abi(id) ON UPDATE CASCADE ON DELETE SET NULL,
        PRIMARY KEY(address, chain_id)
    );
    """)

    if table_exists:
        cursor.execute(
            'INSERT INTO contract_data_new SELECT address, chain_id, abi, deployed_block '
            'FROM contract_data',
        )
        cursor.execute('DROP TABLE contract_data')
        cursor.execute('ALTER TABLE contract_data_new RENAME TO contract_data')


def migrate_to_v5(connection: 'DBConnection') -> None:
    """This globalDB upgrade is introduced at 1.28.0 and does the following:
    - Adds the `default_rpc_nodes` table.
    - Resets curve cache.
    """
    log.debug('Entered globaldb v4->v5 upgrade')
    root_dir = Path(__file__).resolve().parent.parent.parent

    with connection.write_ctx() as cursor:
        _create_new_tables(cursor)
        _populate_rpc_nodes(cursor, root_dir)
        _reset_curve_cache(cursor)
        _remove_name_from_contracts(cursor)

    log.debug('Finished globaldb v4->v5 upgrade')
