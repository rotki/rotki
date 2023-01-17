import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import LIQUITY_STAKING_DETAILS
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.db.settings import DEFAULT_ACTIVE_MODULES
from rotkehlchen.db.utils import table_exists
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _remove_adex(write_cursor: 'DBCursor') -> None:
    """Remove all adex related tables, events, data in other tables"""
    log.debug('Enter _remove_adex')

    write_cursor.execute('DROP TABLE IF EXISTS adex_events')
    if table_exists(write_cursor, 'used_query_ranges'):
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?', ('adex_events%',),
        )

    write_cursor.execute('SELECT value FROM settings where name="active_modules"')
    active_modules_result = write_cursor.fetchone()
    if active_modules_result is not None:
        active_modules_str = active_modules_result[0]
        try:
            new_value = json.loads(active_modules_str)
            if 'adex' in new_value:
                new_value.remove('adex')

        except json.decoder.JSONDecodeError:
            log.error(
                f'During v35->v36 DB upgrade a non-json active_modules entry was found: '
                f'{active_modules_str}. Reverting to default.',
            )
            new_value = DEFAULT_ACTIVE_MODULES

        write_cursor.execute(
            'UPDATE OR IGNORE settings SET value=? WHERE name="active_modules"',
            (json.dumps(new_value),),
        )
    log.debug('Exit _remove_adex')


def _upgrade_ignored_actionids(write_cursor: 'DBCursor') -> None:
    """ignored_action_ids of ActionType.ETHEREUM_TRANSACTION need chainid prepended"""
    log.debug('Enter _upgrade_ignored_actionids')
    if table_exists(write_cursor, 'used_query_ranges'):
        write_cursor.execute('UPDATE ignored_actions SET identifier = "1" || identifier WHERE type="C"')  # noqa: E501
    log.debug('Exit _upgrade_ignored_actionids')


def _upgrade_account_details(write_cursor: 'DBCursor') -> None:
    """Upgrade to account_defails table to evm_accounts_details"""
    log.debug('Enter _upgrade_account_details')

    new_data = []
    last_queried_timestamp_map: dict[str, int] = {}
    if table_exists(write_cursor, 'accounts_details'):
        write_cursor = write_cursor.execute('SELECT * FROM accounts_details')
        for entry in write_cursor:
            if entry[1] != 'eth':
                log.error(
                    f'During v35->v36 DB upgrade a non-eth accounts_details entry '
                    f'{entry[1]} was found. Skipping it.',
                )
                continue

            if entry[2] == 'last_queried_timestamp':
                # Fix duplicated last_queried timestamp as seen here:
                # https://github.com/rotki/rotki/pull/5257
                timestamp = int(entry[3])
                last_seen_timestamp = last_queried_timestamp_map.get(entry[0], 0)
                if timestamp > last_seen_timestamp:
                    last_queried_timestamp_map[entry[0]] = timestamp
                continue

            new_data.append((entry[0], 1, entry[2], entry[3]))

    for address, last_queried_timestamp in last_queried_timestamp_map.items():
        new_data.append((address, 1, 'last_queried_timestamp', str(last_queried_timestamp)))

    write_cursor.execute('DROP TABLE IF EXISTS accounts_details;')
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
    if table_exists(write_cursor, 'ethereum_transactions'):
        write_cursor.execute('SELECT * from ethereum_transactions')
        for entry in write_cursor:
            transactions.append((
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ))
    internal_transactions = []
    if table_exists(write_cursor, 'ethereum_internal_transactions'):
        write_cursor.execute('SELECT * from ethereum_internal_transactions')
        for entry in write_cursor:
            internal_transactions.append((
                entry[0],    # parent_ tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ))

    tx_receipts = []
    if table_exists(write_cursor, 'ethtx_receipts'):
        write_cursor.execute('SELECT * from ethtx_receipts')
        for entry in write_cursor:
            tx_receipts.append((
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ))
    tx_receipt_logs = []
    if table_exists(write_cursor, 'ethtx_receipt_logs'):
        write_cursor.execute('SELECT * from ethtx_receipt_logs')
        for entry in write_cursor:
            tx_receipt_logs.append((
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ))
    tx_receipt_log_topics = []
    if table_exists(write_cursor, 'ethtx_receipt_log_topics'):
        write_cursor.execute('SELECT * from ethtx_receipt_log_topics')
        for entry in write_cursor:
            tx_receipt_log_topics.append((
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ))

    tx_address_mappings = []
    if table_exists(write_cursor, 'ethtx_address_mappings'):
        write_cursor.execute('SELECT * from ethtx_address_mappings')
        for entry in write_cursor:
            tx_address_mappings.append((
                entry[0],    # address
                entry[1],    # tx_hash
                1,           # chain_id
                *entry[2:],  # all the rest are the same
            ))
    tx_mappings = []
    if table_exists(write_cursor, 'evm_tx_mappings'):
        write_cursor.execute('SELECT * from evm_tx_mappings')
        for entry in write_cursor:
            if entry[2] == 'decoded':
                value = 0
            elif entry[2] == 'customized':
                value = 1
            else:
                log.error(
                    f'During v35->v36 DB upgrade unknown evm_tx_mappings '
                    f'value {entry[1]} was found. Skipping it.',
                )
                continue

            if entry[1] != 'ETH':
                log.error(
                    f'During v35->v36 DB upgrade unknown evm_tx_mappings '
                    f'blockchain entry "{entry[1]}" was found. Skipping it.',
                )
                continue

            tx_mappings.append((entry[0], 1, value))

    # Kill tables -- TODO: foreign keys off here or not?
    write_cursor.execute('DROP TABLE IF EXISTS ethereum_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS ethereum_internal_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipts')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_logs')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_log_topics')
    write_cursor.execute('DROP TABLE IF EXISTS ethtx_address_mappings')
    write_cursor.execute('DROP TABLE IF EXISTS evm_tx_mappings')

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
            PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)
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
            type
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
            removed
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
            topic_index
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
            blockchain
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
            value
        ) VALUES (?, ?, ?)""",
        tx_mappings,
    )

    log.debug('Exit _rename_eth_to_evm_add_chainid')


def _upgrade_events_mappings(write_cursor: 'DBCursor') -> None:
    """Upgrade history_events_mappings"""
    log.debug('Enter _upgrade_events_mappings')

    new_data = []
    if table_exists(write_cursor, 'history_events_mappings'):
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

    write_cursor.execute('DROP TABLE IF EXISTS history_events_mappings')
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
            value
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


def _upgrade_rpc_nodes(write_cursor: 'DBCursor') -> None:
    """
    Change name of web3_nodes to rpc_nodes and fix the schema. Weight should be
    a float from 0 to 1 saved as string, not an integer.

    Really wonder why this was never seen before
    """
    log.debug('Enter _upgrade_rpc_nodes')

    # using "ETH" directly since at this point all blockchain column values should be ETH
    # and there may be a problem (noticed it in the premium DB pulling tests) where
    # web3_nodes did not run through v34->v35 upgrade properly so blockchain column is missing.
    # I suspect the tests I noticed it were due to the developer who created the DB error, but
    # since this is equivalent to reading the blockchain column, better safe than sorry
    nodes_tuples = write_cursor.execute(
        'SELECT name, endpoint, owned, active, weight, "ETH" from web3_nodes',
    ).fetchall()
    write_cursor.execute('DROP TABLE IF EXISTS web3_nodes')
    write_cursor.execute(
        """CREATE TABLE IF NOT EXISTS rpc_nodes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        weight TEXT NOT NULL,
        blockchain TEXT NOT NULL
        );""",
    )
    nodes_tuples.extend([
        ('optimism etherscan', '', False, True, '0.4', 'OPTIMISM'),
        ('optimism official', 'https://mainnet.optimism.io', False, True, '0.2', 'OPTIMISM'),
        ('optimism blastapi', 'https://optimism-mainnet.public.blastapi.io', False, True, '0.2', 'OPTIMISM'),  # noqa: E501
        ('optimism ankr', 'https://rpc.ankr.com/optimism', False, True, '0.1', 'OPTIMISM'),
        ('optimism 1rpc', 'https://1rpc.io/op', False, True, '0.1', 'OPTIMISM'),
    ])
    write_cursor.executemany(
        'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
        nodes_tuples,
    )

    log.debug('Exit _upgrade_rpc_nodes')


def _upgrade_tags(write_cursor: 'DBCursor') -> None:
    """All tags tied to addresses should now be tied to chain + address"""
    log.debug('Enter _upgrade_tags')
    write_cursor.execute(
        'SELECT A.blockchain, A.account, B.tag_name from blockchain_accounts AS A '
        'LEFT OUTER JOIN tag_mappings AS B on A.account = B.object_reference',
    )
    delete_tuples = []
    insert_tuples = []
    for entry in write_cursor:
        delete_tuples.append((entry[1],))
        insert_tuples.append((entry[0] + entry[1], entry[2]))

    write_cursor.executemany('DELETE from tag_mappings WHERE object_reference=?', delete_tuples)
    write_cursor.executemany(
        'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES(?, ?)',
        insert_tuples,
    )
    log.debug('Exit _upgrade_tags')


def _upgrade_address_book_table(write_cursor: 'DBCursor') -> None:
    """Upgrades the address book table by making the blockchain column optional"""
    write_cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS address_book_new (
            address TEXT NOT NULL,
            blockchain TEXT,
            name TEXT NOT NULL,
            PRIMARY KEY(address, blockchain)
        );
        """,
    )
    write_cursor.execute('INSERT INTO address_book_new SELECT address, blockchain, name FROM address_book')  # noqa: E501
    write_cursor.execute('DROP TABLE address_book')
    write_cursor.execute('ALTER TABLE address_book_new RENAME TO address_book;')


def _add_okx(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _add_okx')
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("e", 37);')
    log.debug('Exit _add_okx')


def _upgrade_liquity_staking_events(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """
    Since we changed the format of `extra_data`, we have to upgrade the liquity staking events.
    In this upgrade function we make sure that the staking data is stored under the
    appropriate key (LIQUITY_STAKING_DETAILS).
    """
    log.debug('Enter _upgrade_liquity_staking_events')
    upgraded_data_tuples = []
    with conn.read_ctx() as read_cursor:
        read_cursor.execute(
            'SELECT identifier, extra_data FROM history_events WHERE type=? AND subtype IN (?, ?) AND counterparty=? AND extra_data IS NOT NULL',  # noqa: E501
            (
                HistoryEventType.STAKING.serialize(),
                HistoryEventSubType.DEPOSIT_ASSET.serialize(),
                HistoryEventSubType.REMOVE_ASSET.serialize(),
                CPT_LIQUITY,
            ),
        )
        for (identifier, serialized_extra_data) in read_cursor:
            extra_data = json.loads(serialized_extra_data)
            upgraded_extra_data = {LIQUITY_STAKING_DETAILS: extra_data}
            upgraded_data_tuples.append((json.dumps(upgraded_extra_data), identifier))

    write_cursor.executemany(
        'UPDATE history_events SET extra_data=? WHERE identifier=?',
        upgraded_data_tuples,
    )
    log.debug('Exit _upgrade_liquity_staking_events')


def _remove_old_tables(write_cursor: 'DBCursor') -> None:
    """In 1.27.0 we added a check for old tables in the DB.

    This found that many old DBs still have an eth_tokens table which was left there
    and was not removed in some old upgrade. Time to clean up."""
    log.debug('Enter _remove_old_tables')
    write_cursor.execute('DROP TABLE IF EXISTS eth_tokens')
    log.debug('Exit _remove_old_tables')


def upgrade_v35_to_v36(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v35 to v36

        - Remove adex data
        - upgrade ignored actions ids for transactions
        - upgrade accounts details table to add chain id
        - rename all eth tables to evm and add chain id
        - upgrade history_events_mappings to have key/value schema
        - Upgrade nfts table to add image url, collection name and whether
          it's a uniswap LP NFT
        - rename web3_nodes to rpc_nodes
    """
    log.debug('Entered userdb v35->v36 upgrade')
    progress_handler.set_total_steps(12)
    with db.user_write() as write_cursor:
        _remove_adex(write_cursor)
        progress_handler.new_step()
        _upgrade_ignored_actionids(write_cursor)
        progress_handler.new_step()
        _upgrade_account_details(write_cursor)
        progress_handler.new_step()
        _rename_eth_to_evm_add_chainid(write_cursor)
        progress_handler.new_step()
        _upgrade_events_mappings(write_cursor)
        progress_handler.new_step()
        _upgrade_nfts_table(write_cursor)
        progress_handler.new_step()
        _upgrade_rpc_nodes(write_cursor)
        progress_handler.new_step()
        _upgrade_tags(write_cursor)
        progress_handler.new_step()
        _upgrade_address_book_table(write_cursor)
        progress_handler.new_step()
        _add_okx(write_cursor)
        progress_handler.new_step()
        _upgrade_liquity_staking_events(write_cursor, db.conn)
        progress_handler.new_step()
        _remove_old_tables(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v35->v36 upgrade')
