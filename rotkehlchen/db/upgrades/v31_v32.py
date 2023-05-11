from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import BINANCE_MARKETS_KEY

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def _upgrade_history_events(cursor: 'DBCursor') -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history_events_copy (
        identifier INTEGER NOT NULL PRIMARY KEY,
        event_identifier TEXT NOT NULL,
        sequence_index INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        location TEXT NOT NULL,
        location_label TEXT,
        asset TEXT NOT NULL,
        amount TEXT NOT NULL,
        usd_value TEXT NOT NULL,
        notes TEXT,
        type TEXT NOT NULL,
        subtype TEXT,
        counterparty TEXT,
        extra_data TEXT,
        UNIQUE(event_identifier, sequence_index)
    );""")
    cursor.execute('UPDATE history_events SET timestamp = timestamp / 10;')
    cursor.execute('UPDATE history_events SET subtype = "deposit asset" WHERE subtype = "staking deposit asset";')  # noqa: E501
    cursor.execute('UPDATE history_events SET subtype = "receive wrapped" WHERE subtype = "staking receive asset";')  # noqa: E501
    cursor.execute('UPDATE history_events SET subtype = "remove asset", type = "staking" WHERE subtype = "staking remove asset" AND type = "unstaking";')  # noqa: E501
    cursor.execute('UPDATE history_events SET subtype = "return wrapped", type = "staking" WHERE subtype = "staking receive asset" AND type = "unstaking";')  # noqa: E501
    cursor.execute('UPDATE history_events SET type = "informational" WHERE subtype = "unknown";')
    cursor.execute("""
    INSERT INTO history_events_copy (event_identifier, sequence_index, timestamp, location,
    location_label, asset, amount, usd_value, notes, type, subtype)
    SELECT event_identifier, sequence_index, timestamp, location, location_label, asset,
    amount, usd_value, notes, type, subtype
    FROM history_events;
    """)
    cursor.execute('DROP TABLE history_events;')
    cursor.execute('ALTER TABLE history_events_copy RENAME TO history_events;')
    cursor.execute(
        'UPDATE history_events SET subtype="reward" WHERE type="staking" AND subtype IS NULL;',
    )


def _remove_gitcoin(cursor: 'DBCursor') -> None:
    cursor.execute('DELETE from ledger_actions WHERE identifier IN (SELECT parent_id FROM ledger_actions_gitcoin_data)')  # noqa: E501
    cursor.execute('DELETE from used_query_ranges WHERE name LIKE "gitcoingrants_%"')
    cursor.execute('DROP TABLE IF exists gitcoin_grant_metadata')
    cursor.execute('DROP TABLE IF exists ledger_actions_gitcoin_data')
    cursor.execute('DROP TABLE IF exists gitcoin_tx_type')


def _add_new_tables(cursor: 'DBCursor') -> None:
    cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("d", 36)')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethereum_internal_transactions (
    parent_tx_hash BLOB NOT NULL,
    trace_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    FOREIGN KEY(parent_tx_hash) REFERENCES ethereum_transactions(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(parent_tx_hash, trace_id)
);""")  # noqa: E501
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethtx_address_mappings (
    address TEXT NOT NULL,
    tx_hash BLOB NOT NULL,
    blockchain TEXT NOT NULL,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY(tx_hash) references ethereum_transactions(tx_hash) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (address, tx_hash, blockchain)
);""")  # noqa: E501
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_tx_mappings (
    tx_hash BLOB NOT NULL,
    blockchain TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(tx_hash) references ethereum_transactions(tx_hash) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (tx_hash, value)
);""")  # noqa: E501
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history_events_mappings (
    parent_identifier INTEGER NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (parent_identifier, value)
);""")  # noqa: E501
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ens_mappings (
    address TEXT NOT NULL PRIMARY KEY,
    ens_name TEXT UNIQUE,
    last_update INTEGER NOT NULL
);
""")


def _refactor_manual_balance_id(cursor: 'DBCursor') -> None:
    cursor.execute("""
    CREATE TABLE manually_tracked_balances_copy (
        id INTEGER PRIMARY KEY,
        asset TEXT NOT NULL,
        label TEXT NOT NULL,
        amount TEXT,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
        FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")
    cursor.execute("""
    INSERT INTO manually_tracked_balances_copy(asset, label, amount, location, category)
    SELECT asset, label, amount, location, category
    FROM manually_tracked_balances;
    """)
    cursor.execute('DROP TABLE manually_tracked_balances;')
    cursor.execute(
        'ALTER TABLE manually_tracked_balances_copy RENAME TO '
        'manually_tracked_balances;',
    )


def _update_fee_for_existing_trades(cursor: 'DBCursor') -> None:
    cursor.execute('UPDATE trades SET fee = NULL WHERE fee_currency IS NULL')
    cursor.execute('UPDATE trades SET fee_currency = NULL WHERE fee IS NULL')


def _update_history_entries_from_kraken(cursor: 'DBCursor') -> None:
    """The logic for kraken was adding additional entries for trades when fee + kfee was
    being used. This function makes the state of the database consistent with the upgraded
    logic by:
    - Removing extra row additions
    - Make sure that no other event has duplicated sequence indexes
    """
    cursor.execute("""
    DELETE FROM history_events where location="B" AND asset="KFEE" AND
     type="trade" AND subtype=NULL;
    """)

    cursor.execute('SELECT event_identifier, sequence_index from history_events')
    eventid_to_indices: dict[str, set[int]] = defaultdict(set)
    for event_identifier, sequence_index in cursor:
        eventid_to_indices[event_identifier].add(sequence_index)

    cursor.execute("""
    SELECT e.event_identifier, e.sequence_index, e.identifier from history_events e JOIN (SELECT event_identifier,
    sequence_index, COUNT(*) as cnt FROM history_events GROUP BY event_identifier, sequence_index)
    other ON e.event_identifier = other.event_identifier and e.sequence_index=other.sequence_index
    WHERE other.cnt > 1;
    """)  # noqa: E501
    update_tuples = []
    for event_identifier, sequence_index, identifier in cursor:
        new_index = sequence_index + 1
        while new_index in eventid_to_indices[event_identifier]:
            new_index += 1
        eventid_to_indices[event_identifier].add(new_index)
        update_tuples.append((new_index, identifier))

    if len(update_tuples) != 0:
        cursor.executemany(
            'UPDATE history_events SET sequence_index=? WHERE identifier=?',
            update_tuples,
        )


def _update_settings_name_for_selected_binance_markets(cursor: 'DBCursor') -> None:
    cursor.execute("""
    UPDATE user_credentials_mappings SET setting_name = ? WHERE setting_name = "PAIRS"
    """, (BINANCE_MARKETS_KEY,))


def _update_manual_balances_tags(cursor_fetch: 'DBCursor', cursor_update: 'DBCursor') -> None:
    manual_balances = cursor_fetch.execute('SELECT id, label FROM manually_tracked_balances')
    for balance_id, label in manual_balances:
        cursor_update.execute('UPDATE tag_mappings SET object_reference=? WHERE object_reference=?', (balance_id, label))  # noqa: E501


def upgrade_v31_to_v32(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v31 to v32
    - use new identifiers for the history_events table. The id will be generated by sqlite
    and will be the column rowid

    -Add the subtype REWARD to staking rewards (before they had type staking
    and no subtype)

    -Remove all gitcoin grant related data that was pulled from their API and saved in
    specific tables along with the tables themselves

    -Sets fee to null for existing trades if fee_currency is missing.
    """
    progress_handler.set_total_steps(8)
    with db.user_write() as write_cursor, db.conn.read_ctx() as read_cursor:
        _update_history_entries_from_kraken(write_cursor)
        progress_handler.new_step()
        _upgrade_history_events(write_cursor)
        progress_handler.new_step()
        _remove_gitcoin(write_cursor)
        progress_handler.new_step()
        _add_new_tables(write_cursor)
        progress_handler.new_step()
        _refactor_manual_balance_id(write_cursor)
        progress_handler.new_step()
        _update_fee_for_existing_trades(write_cursor)
        progress_handler.new_step()
        _update_settings_name_for_selected_binance_markets(write_cursor)
        progress_handler.new_step()
        _update_manual_balances_tags(cursor_fetch=read_cursor, cursor_update=write_cursor)
        progress_handler.new_step()
