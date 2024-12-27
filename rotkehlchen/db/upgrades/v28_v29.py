from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def _create_new_tables(cursor: 'DBCursor') -> None:
    """Create new tables added at this upgrade

    Should be called at the end of the upgrade as it depends on the changes
    done to the transactions table
    """
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethtx_receipts (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    contract_address TEXT, /* can be null */
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    type INTEGER NOT NULL,
    FOREIGN KEY(tx_hash) REFERENCES ethereum_transactions(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE
    );""")  # noqa: E501
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethtx_receipt_logs (
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    data BLOB NOT NULL,
    address TEXT NOT NULL,
    removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
    FOREIGN KEY(tx_hash) REFERENCES ethtx_receipts(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(tx_hash, log_index)
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethtx_receipt_log_topics (
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    topic BLOB NOT NULL,
    topic_index INTEGER NOT NULL,
    FOREIGN KEY(tx_hash, log_index) REFERENCES ethtx_receipt_logs(tx_hash, log_index) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(tx_hash, log_index, topic_index)
    );""")  # noqa: E501
    cursor.execute("""CREATE TABLE IF NOT EXISTS nfts (
    identifier TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    last_price TEXT,
    last_price_asset TEXT,
    manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
    owner_address TEXT,
    blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
    FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")  # noqa: E501


def _upgrade_existing_tables(
        cursor: 'DBCursor',
        progress_handler: 'DBUpgradeProgressHandler',
) -> None:
    query = cursor.execute('SELECT blockchain, account, label FROM blockchain_accounts;')
    accounts_data = query.fetchall()
    query = cursor.execute('SELECT address, xpub, derivation_path, account_index, derived_index FROM xpub_mappings;')  # noqa: E501
    xpub_mappings_data = query.fetchall()
    query = cursor.execute('SELECT tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM ethereum_transactions;')  # noqa: E501
    transactions_data = [entry for entry in query if entry[10] >= 0]  # non-internal
    cursor.execute('DROP TABLE IF EXISTS blockchain_accounts;')
    cursor.execute('DROP TABLE IF EXISTS xpub_mappings;')
    cursor.execute('DROP TABLE IF EXISTS ethereum_transactions;')
    progress_handler.new_step(name='Creating blockchain_accounts table.')
    # create the new tables and insert all values into it
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24] NOT NULL,
    account TEXT NOT NULL,
    label TEXT,
    PRIMARY KEY (blockchain, account)
    );
    """)
    cursor.executemany(
        'INSERT INTO blockchain_accounts(blockchain, account, label) VALUES(?, ?, ?);',
        accounts_data,
    )
    progress_handler.new_step(name='Creating xpub_mappings table.')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS xpub_mappings (
    address TEXT NOT NULL,
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    account_index INTEGER,
    derived_index INTEGER,
    blockchain TEXT GENERATED ALWAYS AS ('BTC') VIRTUAL,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
    FOREIGN KEY(xpub, derivation_path) REFERENCES xpubs(xpub, derivation_path) ON DELETE CASCADE
    PRIMARY KEY (address, xpub, derivation_path)
    );
    """)  # noqa: E501
    cursor.executemany(
        'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index) '
        'VALUES(?, ?, ?, ?, ?);',
        xpub_mappings_data,
    )
    progress_handler.new_step(name='Creating ethereum_transactions table.')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethereum_transactions (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    gas TEXT NOT NULL,
    gas_price TEXT NOT NULL,
    gas_used TEXT NOT NULL,
    input_data BLOB NOT NULL,
    nonce INTEGER NOT NULL
    );
    """)
    cursor.executemany(
        'INSERT INTO ethereum_transactions(tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '  # noqa: E501
        'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
        transactions_data,
    )


def upgrade_v28_to_v29(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v28 to v29

    - Alters the primary key of blockchain accounts to be blockchain type + account
    - Alters the xpub_mappings to reference the new blockchain accounts
    - Alters the ethereum transactions table to have tx_hash as primary key
    """
    progress_handler.set_total_steps(6)
    with db.user_read_write() as cursor:
        progress_handler.new_step(name='Updating existing tables.')
        _upgrade_existing_tables(cursor=cursor, progress_handler=progress_handler)
        progress_handler.new_step(name='Creating new tables.')
        _create_new_tables(cursor)

        progress_handler.new_step(name='Renaming uniswap_events to amm_events.')
        # Rename uniswap_events table. Drop amm_events first if it was created at initialization
        # of the db handler
        cursor.execute('DROP TABLE IF EXISTS amm_events;')
        cursor.execute('ALTER TABLE uniswap_events RENAME TO amm_events;')
