
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


DEFAULT_POLYGON_NODES_AT_V38 = [
    ('polygon pos etherscan', '', 0, 1, '0.25', 'POLYGON_POS'),
    ('ankr', 'https://rpc.ankr.com/polygon', 0, 1, '0.15', 'POLYGON_POS'),
    ('BlockPi', 'https://polygon.blockpi.network/v1/rpc/public', 0, 1, '0.15', 'POLYGON_POS'),
    ('PublicNode', 'https://polygon-bor.publicnode.com', 0, 1, '0.15', 'POLYGON_POS'),
    ('DefiLlama', 'https://polygon.llamarpc.com', 0, 1, '0.15', 'POLYGON_POS'),
    ('1rpc', 'https://1rpc.io/matic', 0, 1, '0.15', 'POLYGON_POS'),
]


@enter_exit_debug_log(name='UserDB v37->v38 upgrade')
def upgrade_v37_to_v38(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v37 to v38. This was in v1.29.0 release.
        - Reset decoded events
        - Reduce the data stored per internal transaction
        - Add Polygon POS location and nodes
        - Drop the unused aave events
        - Remove potential duplicate block mev reward events
    """
    @progress_step(description='Adding Polygon PoS location.')
    def _add_polygon_pos_location(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('h', 40);")

    @progress_step(description='Adding Polygon PoS nodes.')
    def _add_polygon_pos_nodes(write_cursor: 'DBCursor') -> None:
        write_cursor.executemany(
            'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            DEFAULT_POLYGON_NODES_AT_V38,
        )

    @progress_step(description='Reducing internal transactions.')
    def _reduce_internal_txs(write_cursor: 'DBCursor') -> None:
        """Reduce the size of the evm internal transactions table by removing unused columns"""
        update_table_schema(
            write_cursor=write_cursor,
            table_name='evm_internal_transactions',
            schema="""parent_tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            trace_id INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            FOREIGN KEY(parent_tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)""",  # noqa: E501
            insert_columns='parent_tx_hash, chain_id, trace_id, from_address, to_address, value',
        )

    @progress_step(description='Dropping Aave events.')
    def _drop_aave_events(write_cursor: 'DBCursor') -> None:
        """
        Delete aave events from the database since we don't need them anymore
        """
        write_cursor.execute('DROP TABLE IF EXISTS aave_events;')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
            ('aave\\_events%', '\\'),
        )

    @progress_step(description='Deleting Uniswap/Sushiswap events.')
    def _delete_uniswap_sushiswap_events(write_cursor: 'DBCursor') -> None:
        """
        Delete query ranges and events for uniswap/sushiswap
        """
        write_cursor.execute('DROP TABLE IF EXISTS amm_events;')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
            ('uniswap\\_events\\_%', '\\'),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
            ('sushiswap\\_events\\_%', '\\'),
        )

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """
        Reset all decoded evm events except the customized ones for ethereum mainnet and optimism.
        """
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] == 0:
            return

        customized_events = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0]
        querystr = (
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN evm_events_info E '
            'ON H.identifier=E.identifier AND E.tx_hash IN '
            '(SELECT tx_hash FROM evm_transactions))'
        )
        bindings: tuple = ()
        if customized_events != 0:
            querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

        write_cursor.execute(querystr, bindings)
        write_cursor.execute(
            'DELETE from evm_tx_mappings WHERE tx_hash IN (SELECT tx_hash FROM evm_transactions) AND value=?',  # noqa: E501
            (0,),  # decoded tx state
        )

    @progress_step(description='Removing duplicate block mev rewards.')
    def _remove_duplicate_block_mev_rewards(write_cursor: 'DBCursor') -> None:
        """If mev reward is exact same as block production reward then it's a duplicate event.
        In that case it needs to be deleted.
        """
        write_cursor.execute(
            "DELETE FROM history_events WHERE identifier IN ("
            "SELECT B.identifier from history_events A INNER JOIN history_events B "
            "ON A.event_identifier=B.event_identifier AND A.subtype='block production' "
            "AND B.subtype='mev reward' AND A.amount=B.amount WHERE A.entry_type=4);",
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
