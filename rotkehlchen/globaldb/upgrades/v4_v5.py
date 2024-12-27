import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='GlobalDB v4->v5 upgrade')
def migrate_to_v5(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade is introduced at 1.28.0 and does the following:
    - Adds the `default_rpc_nodes` table.
    - Resets curve cache.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent

    @progress_step('Creating default_rpc_nodes table.')
    def _create_new_tables(cursor: 'DBCursor') -> None:
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

    @progress_step('Populating default_rpc_nodes.')
    def _populate_rpc_nodes(cursor: 'DBCursor') -> None:
        nodes_info = json.loads((root_dir / 'data' / 'nodes.json').read_text(encoding='utf8'))
        nodes_tuples = [
            (node['name'], node['endpoint'], False, True, str(FVal(node['weight'])), node['blockchain'])  # noqa: E501
            for node in nodes_info
        ]
        log.debug(nodes_tuples)
        cursor.executemany(
            'INSERT INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            nodes_tuples,
        )

    @progress_step('Resetting curve cache.')
    def _reset_curve_cache(write_cursor: 'DBCursor') -> None:
        """Resets curve cache to query gauges and update format of the lp tokens"""
        write_cursor.execute("DELETE FROM general_cache WHERE key LIKE '%CURVE%'")

    @progress_step('Removing name column from contract_data table.')
    def _remove_name_from_contracts(cursor: 'DBCursor') -> None:
        """Removes the name column from contract_data table if it exists"""
        update_table_schema(
            write_cursor=cursor,
            table_name='contract_data',
            schema="""address VARCHAR[42] NOT NULL,
            chain_id INTEGER NOT NULL,
            abi INTEGER NOT NULL,
            deployed_block INTEGER,
            FOREIGN KEY(abi) REFERENCES contract_abi(id) ON UPDATE CASCADE ON DELETE SET NULL,
            PRIMARY KEY(address, chain_id)""",
            insert_columns='address, chain_id, abi, deployed_block',
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
