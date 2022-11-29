import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _remove_adex(write_cursor: 'DBCursor') -> None:
    """Remove all adex related tables, events, data in other tables"""
    log.debug('Enter _remove_adex')
    write_cursor.execute('DROP TABLE IF EXISTS adex_events')
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ?', ('adex_events%',),
    )
    log.debug('Exit _remove_adex')


def _upgrade_ignored_actionids(write_cursor: 'DBCursor') -> None:
    """ignored_action_ids of ActionType.ETHEREUM_TRANSACTION need chainid prepended"""
    log.debug('Enter _upgrade_ignored_actionids')
    write_cursor.execute('UPDATE ignored_actions SET identifier = "1"+identifier WHERE type="C"')
    log.debug('Exit _upgrade_ignored_actionids')


def _upgrade_account_details(write_cursor: 'DBCursor') -> None:
    """Upgrade to account_defails table to evm_accounts_details"""
    log.debug('Enter _upgrade_account_details')

    write_cursor = write_cursor.execute('SELECT * FROM accounts_details')
    new_data = []
    for entry in write_cursor:
        if entry[1] != 'eth':
            log.error(
                f'During v35->v36 DB upgrade a non-eth accounts_details entry '
                f'{entry[1]} was found. Skipping it.',
            )
            continue

        new_data.append((entry[0], 1, entry[2], entry[3]))

    write_cursor.execute('DROP TABLE accounts_details;')
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_accounts_details (
        account VARCHAR[42] NOT NULL,
        chain_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (account, chain_id, key, value)
    );
    """)
    write_cursor.executemany(
        """INSERT OR IGNORE INTO evm_accounts_details(
        account, chain_id, key, value
        ) VALUES (?, ?, ?, ?)""",
        new_data,
    )

    log.debug('Exit _upgrade_account_details')


def _rename_eth_to_evm_add_chainid(write_cursor: 'DBCursor') -> None:
    """Rename all eth to evm tables, add chain id and adjust tx mappings"""
    log.debug('Enter _rename_eth_to_evm_add_chainid')

    # Get all data in memory and upgrade it
    transactions = []
    write_cursor.execute('SELECT * from ethereum_transactions')
    for entry in write_cursor:
        transactions.append((
            entry[0],    # tx_hash
            1,           # chain_id
            *entry[1:],  # all the rest are the same
        ))
    internal_transactions = []
    write_cursor.execute('SELECT * from ethereum_internal_transactions')
    for entry in write_cursor:
        internal_transactions.append((
            entry[0],    # parent_ tx_hash
            1,           # chain_id
            *entry[1:],  # all the rest are the same
        ))

    tx_receipts = []
    write_cursor.execute('SELECT * from ethtx_receipts')
    for entry in write_cursor:
        tx_receipts.append((
            entry[0],    # tx_hash
            1,           # chain_id
            *entry[1:],  # all the rest are the same
        ))
    tx_receipt_logs = []
    write_cursor.execute('SELECT * from ethtx_receipt_logs')
    for entry in write_cursor:
        tx_receipt_logs.append((
            entry[0],    # tx_hash
            1,           # chain_id
            *entry[1:],  # all the rest are the same
        ))
    tx_receipt_log_topics = []
    write_cursor.execute('SELECT * from ethtx_receipt_log_topics')
    for entry in write_cursor:
        tx_receipt_log_topics.append((
            entry[0],    # tx_hash
            1,           # chain_id
            *entry[1:],  # all the rest are the same
        ))

    tx_address_mappings = []
    write_cursor.execute('SELECT * from ethtx_address_mappings')
    for entry in write_cursor:
        tx_address_mappings.append((
            entry[0],    # address
            entry[1],    # tx_hash
            1,           # chain_id
            *entry[2:],  # all the rest are the same
        ))
    tx_mappings = []
    write_cursor.execute('SELECT * from evm_tx_mappings')
    for entry in write_cursor:
        if entry[1] == 'decoded':
            value = 0
        elif entry[1] == 'customized':
            value = 1
        else:
            log.error(
                f'During v35->v36 DB upgrade unknown evm_tx_mappings '
                f'value {entry[1]} was found. Skipping it.',
            )
            continue
        tx_mappings.append((1, value))

    # Kill tables: Figure out if foreign keys should go off during
    # write_cursor.execute('PRAGMA foreign_keys = 0;')
    write_cursor.execute('DROP TABLE IF EXISTS ethereum_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS ethereum_internal_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipts')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_logs')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_log_topics')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_address_mappings')
    write_cursor.execute('DROP TABLE IF EXISTS evm_tx_mappings')
    # write_cursor.execute('PRAGMA foreign_keys = 1;')

    # Create new tables and populate them
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evm_transactions (
        tx_hash BLOB NOT NULL,
        chain_id INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        block_number INTEGER NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT,
        value TEXT NOT NULL,
        gas TEXT NOT NULL,
        gas_price TEXT NOT NULL,
        gas_used TEXT NOT NULL,
        input_data BLOB NOT NULL,
        nonce INTEGER NOT NULL,
        PRIMARY KEY(tx_hash, chain_id)
        );""",
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evm_transactions(
            tx_hash,
            chain_id,
            timestamp,
            block_number,
            from_address,
            to_address,
            value,
            gas,
            gas_price,
            gas_used,
            input_data,
            nonce
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,?)""",
        transactions,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evm_internal_transactions (
            parent_tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            trace_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            FOREIGN KEY(parent_tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(parent_tx_hash, chain_id, trace_id)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evm_internal_transactions(
            parent_tx_hash,
            chain_id,
            trace_id,
            timestamp,
            block_number,
            from_address,
            to_address,
            value
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        internal_transactions,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evmtx_receipts (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            contract_address TEXT, /* can be null */
            status INTEGER NOT NULL CHECK (status IN (0, 1)),
            type INTEGER NOT NULL,
            FOREIGN KEY(tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_hash, chain_id)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evmtx_receipts(
            tx_hash,
            chain_id,
            contract_address,
            status,
            type,
        ) VALUES (?, ?, ?, ?, ?)""",
        tx_receipts,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evmtx_receipt_logs (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            log_index INTEGER NOT NULL,
            data BLOB NOT NULL,
            address TEXT NOT NULL,
            removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
            FOREIGN KEY(tx_hash, chain_id) REFERENCES evmtx_receipts(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_hash, chain_id, log_index)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evmtx_receipt_logs(
            tx_hash,
            chain_id,
            log_index,
            data,
            address,
            removed,
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        tx_receipt_logs,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evmtx_receipt_log_topics (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            log_index INTEGER NOT NULL,
            topic BLOB NOT NULL,
            topic_index INTEGER NOT NULL,
            FOREIGN KEY(tx_hash, chain_id, log_index) REFERENCES evmtx_receipt_logs(tx_hash, chain_id, log_index) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_hash, chain_id, log_index, topic_index)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evmtx_receipt_log_topics(
            tx_hash,
            chain_id,
            log_index,
            topic,
            topic_index,
        ) VALUES (?, ?, ?, ?, ?)""",
        tx_receipt_log_topics,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evmtx_address_mappings (
            address TEXT NOT NULL,
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            blockchain TEXT NOT NULL,
            FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
            FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (address, tx_hash, chain_id)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evmtx_address_mappings(
            address,
            tx_hash,
            chain_id,
            blockchain,
        ) VALUES (?, ?, ?, ?)""",
        tx_address_mappings,
    )
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evm_tx_mappings (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (tx_hash, chain_id, value)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO evm_tx_mappings(
            tx_hash,
            chain_id,
            value,
        ) VALUES (?, ?, ?)""",
        tx_mappings,
    )

    log.debug('Exit _rename_eth_to_evm_add_chainid')


def _upgrade_events_mappings(write_cursor: 'DBCursor') -> None:
    """Upgrade history_events_mappings"""
    log.debug('Enter _upgrade_events_mappings')

    new_data = []
    write_cursor = write_cursor.execute('SELECT * FROM history_events_mappings')
    for entry in write_cursor:
        if entry[1] == 'decoded':
            value = 0
        elif entry[1] == 'customized':
            value = 1
        else:
            log.error(
                f'During v35->v36 DB upgrade unknown history_events_mappings '
                f'value {entry[1]} was found. Skipping it.',
            )
            continue
        new_data.append((entry[0], 'state', value))

    write_cursor.execute('DROP TABBLE IF EXISTS history_events_mappings')
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history_events_mappings (
            parent_identifier INTEGER NOT NULL,
            name TEXT NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (parent_identifier, name, value)
        );""",  # noqa: E501
    )
    write_cursor.executemany(
        """
        INSERT OR IGNORE INTO history_events_mappings(
            parent_identifier,
            name,
            value,
        ) VALUES (?, ?, ?)""",
        new_data,
    )

    log.debug('Exit _upgrade_events_mappings')


def _upgrade_nfts_table(write_cursor: 'DBCursor') -> None:
    """Upgrade nfts table to add image url, collection name and whether it's a uniswap LP NFT"""
    log.debug('Enter _upgrade_nfts_table')

    write_cursor.execute('DROP TABLE IF EXISTS nfts')
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nfts (
            identifier TEXT NOT NULL PRIMARY KEY,
            name TEXT,
            last_price TEXT,
            last_price_asset TEXT,
            manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
            owner_address TEXT,
            blockchain TEXT GENERATED ALWAYS AS ("ETH") VIRTUAL,
            is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
            image_url TEXT,
            collection_name TEXT,
            FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
            FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );""",  # noqa: E501
    )

    log.debug('Exit _upgrade_nfts_table')


def upgrade_v35_to_v36(db: 'DBHandler') -> None:
    """Upgrades the DB from v35 to v36
    - Rename all ethereum transaction tables and add chainid to them
    - Upgrade history_events_mappings to the new format
    """
    log.debug('Entered userdb v35->v36 upgrade')

    with db.user_write() as write_cursor:
        _remove_adex(write_cursor)
        _upgrade_ignored_actionids(write_cursor)
        _upgrade_account_details(write_cursor)
        _rename_eth_to_evm_add_chainid(write_cursor)
        _upgrade_events_mappings(write_cursor)
        _upgrade_nfts_table(write_cursor)
        write_cursor.execute('ALTER TABLE web3_nodes RENAME TO rpc_nodes;')

    log.debug('Finished userdb v35->v36 upgrade')
