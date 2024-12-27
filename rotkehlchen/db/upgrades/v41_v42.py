import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import ChainID, Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v41->v42 upgrade')
def upgrade_v41_to_v42(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v41 to v42. This was in v1.33 release.

        - Create new tables for zksync lite
        - Add new supported locations
        - Add a new table to handle the calendar
        - Remove the manualcurrent oracle from settings
        - Remove balancer old events
        - Remove yearn v1 and v2 old events
        - remove evm events that link to a transaction not in the database
    """
    @progress_step(description='Adding zkSync Lite.')
    def _add_zksynclite(write_cursor: 'DBCursor') -> None:
        """Add zksynclite related table"""
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS zksynclite_tx_type (
        type    CHAR(1)       PRIMARY KEY NOT NULL,
        seq     INTEGER UNIQUE
        );""")

        write_cursor.execute("""
        /* Transfer Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('A', 1);""")
        write_cursor.execute("""
        /* Deposit Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('B', 2);""")
        write_cursor.execute("""
        /* Withdraw Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('C', 3);""")
        write_cursor.execute("""
        /* ChangePubKey Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('D', 4);""")
        write_cursor.execute("""
        /* ForcedExit Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('E', 5);""")
        write_cursor.execute("""
        /* FullExit Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('F', 6);""")
        write_cursor.execute("""
        /* Swap Type */
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('G', 7);""")
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS zksynclite_transactions (
        identifier INTEGER NOT NULL PRIMARY KEY,
        tx_hash BLOB NOT NULL UNIQUE,
        type CHAR(1) NOT NULL DEFAULT('A') REFERENCES zksynclite_tx_type(type),
        is_decoded INTEGER NOT NULL DEFAULT 0 CHECK (is_decoded IN (0, 1)),
        timestamp INTEGER NOT NULL,
        block_number INTEGER NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT,
        asset TEXT NOT NULL,
        amount TEXT NOT NULL,
        fee TEXT,
        FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS zksynclite_swaps (
        tx_id INTEGER NOT NULL,
        from_asset TEXT NOT NULL,
        from_amount TEXT NOT NULL,
        to_asset TEXT NOT NULL,
        to_amount TEXT_NOT NULL,
        FOREIGN KEY(tx_id) REFERENCES zksynclite_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
        FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );""")  # noqa: E501

    @progress_step(description='Adding new supported locations.')
    def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            [('n', Location.SCROLL.value), ('o', Location.ZKSYNC_LITE.value)],
        )

    @progress_step(description='Upgrading evmchains to skip detection.')
    def _upgrade_evmchains_to_skip_detection(write_cursor: 'DBCursor') -> None:
        """We used to have it only in EVM Chain IDs serialized as names.
        Now turning it into all supported chains due to evmlike introduction"""
        write_cursor.execute("SELECT value from settings WHERE name='evmchains_to_skip_detection'")
        if (result := write_cursor.fetchone()) is None:
            return
        try:
            evmchains_to_skip = json.loads(result[0])
        except json.JSONDecodeError as e:
            log.error(f'During Upgrade could not parse {result[0]} as JSON due to {e}')
            return

        evmchains_to_skip = [ChainID.deserialize_from_name(x) for x in evmchains_to_skip]
        chains_to_skip = [x.to_blockchain().value for x in evmchains_to_skip]
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('evmchains_to_skip_detection', json.dumps(chains_to_skip)),
        )

    @progress_step(description='Adding calendar tables.')
    def _add_calendar_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""CREATE TABLE IF NOT EXISTS calendar (
        identifier INTEGER PRIMARY KEY NOT NULL,
        name TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        description TEXT,
        counterparty TEXT,
        address TEXT,
        blockchain TEXT,
        color TEXT,
        auto_delete INTEGER NOT NULL CHECK (auto_delete IN (0, 1)),
        FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
        UNIQUE(name, address, blockchain)
        );""")  # noqa: E501
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_reminders (
            identifier INTEGER PRIMARY KEY NOT NULL,
            event_id INTEGER NOT NULL,
            secs_before INTEGER NOT NULL,
            FOREIGN KEY(event_id) REFERENCES calendar(identifier) ON DELETE CASCADE
        );""")

    @progress_step(description='Removing manual current price oracle.')
    def _remove_manualcurrent_oracle(write_cursor: 'DBCursor') -> None:
        """Removes the manualcurrent oracle from the current_price_oracles setting"""
        write_cursor.execute("SELECT value FROM settings WHERE name='current_price_oracles'")
        if (data := write_cursor.fetchone()) is None:
            return  # oracles not configured

        try:
            oracles: list[str] = json.loads(data[0])
        except json.JSONDecodeError as e:
            log.error(f'Failed to read oracles from user db. {e!s}')
            return

        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (
                'current_price_oracles',
                json.dumps([oracle for oracle in oracles if oracle != 'manualcurrent']),
            ),
        )

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except the customized ones."""
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
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
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
                (0,),  # decoded tx state
            )

    @progress_step(description='Removing balancer events table.')
    def _remove_balancer_events_table(write_cursor: 'DBCursor') -> None:
        """Delete the table with balancer events"""
        write_cursor.execute('DROP TABLE balancer_events')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            ('balancer_events%',),
        )

    @progress_step(description='Removing yearn events table.')
    def _remove_yearn_events_table(write_cursor: 'DBCursor') -> None:
        """Delete the table with balancer events"""
        write_cursor.execute('DROP TABLE yearn_vaults_events')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
            ('yearn\\_vaults%', '\\'),
        )

    @progress_step(description='Deleting orphan events.')
    def _delete_orphan_events(write_cursor: 'DBCursor') -> None:
        """
        Delete all the evm events that have a tx_hash that is not present in the db.
        This can for example happen for customized events of addresses that got deleted
        from the database or when all transactions are purged.

        This query assumes that an evm event always has a evm_transactions but this is not the case
        for zksync lite. Since prior to 1.33 that assumption holds this query is safe.
        """
        write_cursor.execute(
            'DELETE FROM history_events WHERE identifier IN (SELECT identifier FROM evm_events_info '  # noqa: E501
            'WHERE identifier NOT IN (SELECT eei.identifier FROM evm_events_info eei JOIN '
            'evm_transactions et ON eei.tx_hash = et.tx_hash))',
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
