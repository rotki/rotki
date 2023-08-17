import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_ARBITRUM_ONE_NODES_AT_V39 = [
    ('arbitrum one etherscan', '', 0, 1, '0.28', 'ARBITRUM_ONE'),
    ('arbitrum one ankr', 'https://rpc.ankr.com/arbitrum', 0, 1, '0.18', 'ARBITRUM_ONE'),
    ('arbitrum one BlockPi', 'https://arbitrum.blockpi.network/v1/rpc/public', 0, 1, '0.18', 'ARBITRUM_ONE'),  # noqa: E501
    ('arbitrum one PublicNode', 'https://arbitrum-one.publicnode.com', 0, 1, '0.18', 'ARBITRUM_ONE'),  # noqa: E501
    ('arbitrum one 1rpc', 'https://1rpc.io/arb', 0, 1, '0.18', 'ARBITRUM_ONE'),
]


def _update_nfts_table(write_cursor: 'DBCursor') -> None:
    """
    Update the nft table to remove double quotes due to https://github.com/rotki/rotki/issues/6368
    """
    log.debug('Enter _update_nfts_table')
    table_exists = write_cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='evm_internal_transactions'",
    ).fetchone()[0] == 1
    table_to_create = 'nfts'
    if table_exists is True:
        table_to_create += '_new'
    write_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_to_create} (
        identifier TEXT NOT NULL PRIMARY KEY,
        name TEXT,
        last_price TEXT,
        last_price_asset TEXT,
        manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
        owner_address TEXT,
        blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
        is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
        image_url TEXT,
        collection_name TEXT,
        FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
        FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
        FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")  # noqa: E501
    if table_exists is True:
        write_cursor.execute(
            'INSERT INTO nfts_new SELECT identifier, name, last_price, last_price_asset, '
            'manual_price, owner_address, is_lp, image_url, collection_name FROM nfts')
        write_cursor.execute('DROP TABLE nfts')
        write_cursor.execute('ALTER TABLE nfts_new RENAME TO nfts')

    log.debug('Exit _update_nfts_table')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _create_new_tables')
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimism_transactions (
        tx_id INTEGER NOT NULL PRIMARY KEY,
        l1_fee TEXT,
    FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
    );""")
    log.debug('Exit _create_new_tables')


def _reduce_eventid_size(write_cursor: 'DBCursor') -> None:
    """Reduce the size of history event ids"""
    log.debug('Enter _reduce_eventid_size')
    staking_events = write_cursor.execute(
        'SELECT H.identifier, H.subtype, S.validator_index, S.is_exit_or_blocknumber, '
        'H.timestamp FROM history_events H INNER JOIN eth_staking_events_info S '
        'ON S.identifier=H.identifier',
    ).fetchall()
    updates = []
    for identifier, subtype, validator_index, blocknumber, timestamp in staking_events:
        if subtype == 'remove asset':
            days = int(timestamp / 1000 / 86400)
            updates.append((f'EW_{validator_index}_{days}', identifier))
        elif subtype in ('mev reward', 'block production'):
            updates.append((f'BP1_{blocknumber}', identifier))

    imported_events = write_cursor.execute(
        "SELECT identifier, event_identifier FROM history_events WHERE event_identifier LIKE 'rotki_events_%'",  # noqa: E501
    ).fetchall()
    for identifier, event_identifier in imported_events:
        new_event_identifer = event_identifier.replace('rotki_events_bitcoin_tax_', 'REBTX_').replace('rotki_events_', 'RE_')  # noqa: E501
        updates.append((new_event_identifer, identifier))

    write_cursor.executemany(
        'UPDATE history_events SET event_identifier=? WHERE identifier=?', updates,
    )
    log.debug('Exit _reduce_eventid_size')


def _update_evm_transaction_data(write_cursor: 'DBCursor') -> None:
    """Turn the primary key of evm transactions to be a unique integer ID instead
    of composite primary with hash + chain id. Saves lots of DB space.

    Implements https://github.com/rotki/rotki/issues/6372
    """
    log.debug('Enter _update_evm_transaction_data')
    txs = write_cursor.execute('SELECT * from evm_transactions').fetchall()
    internal_txs = write_cursor.execute('SELECT * from evm_internal_transactions').fetchall()
    receipts = write_cursor.execute('SELECT * from evmtx_receipts').fetchall()
    logs = write_cursor.execute('SELECT * from evmtx_receipt_logs').fetchall()
    topics = write_cursor.execute('SELECT * from evmtx_receipt_log_topics').fetchall()
    tx_mappings = write_cursor.execute('SELECT * from evm_tx_mappings').fetchall()
    address_mappings = write_cursor.execute('SELECT tx_hash, chain_id, address from evmtx_address_mappings').fetchall()  # noqa: E501

    write_cursor.execute('DROP TABLE IF EXISTS evm_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS evm_internal_transactions')
    write_cursor.execute('DROP TABLE IF EXISTS evmtx_receipts')
    write_cursor.execute('DROP TABLE IF EXISTS evmtx_receipt_logs')
    write_cursor.execute('DROP TABLE IF EXISTS evmtx_receipt_log_topics')
    write_cursor.execute('DROP TABLE IF EXISTS evm_tx_mappings')
    write_cursor.execute('DROP TABLE IF EXISTS evmtx_address_mappings')

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_transactions (
        identifier INTEGER NOT NULL PRIMARY KEY,
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
        UNIQUE(tx_hash, chain_id)
    );""")
    hashchain_to_id = {}
    tx_data = []
    for identifier, data in enumerate(txs):
        hashchain_to_id[data[0] + data[1].to_bytes(4, byteorder='big')] = identifier
        tx_data.append((identifier, *data))
    write_cursor.executemany(
        'INSERT INTO evm_transactions(identifier, tx_hash, chain_id, timestamp, block_number, '
        'from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '
        'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        tx_data,
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_tx_mappings (
        tx_id INTEGER NOT NULL,
        value INTEGER NOT NULL,
        FOREIGN KEY(tx_id) references evm_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY (tx_id, value)
    );""")  # noqa: E501
    write_cursor.executemany(
        'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
        [(hashchain_to_id[x[0] + x[1].to_bytes(4, byteorder='big')], *x[2:]) for x in tx_mappings],
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evmtx_address_mappings (
        tx_id INTEGER NOT NULL,
        address TEXT NOT NULL,
        FOREIGN KEY(tx_id) references evm_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY (tx_id, address)
    );""")  # noqa: E501
    write_cursor.executemany(
        'INSERT INTO evmtx_address_mappings(tx_id, address) VALUES(?, ?)',
        [(hashchain_to_id[x[0] + x[1].to_bytes(4, byteorder='big')], *x[2:]) for x in address_mappings],  # noqa: E501
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_internal_transactions (
        parent_tx INTEGER NOT NULL,
        trace_id INTEGER NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT,
        value TEXT NOT NULL,
        FOREIGN KEY(parent_tx) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY(parent_tx, trace_id, from_address, to_address, value)
    );""")  # noqa: E501
    write_cursor.executemany(
        'INSERT INTO evm_internal_transactions(parent_tx, trace_id, from_address, to_address, '
        'value) VALUES(?, ?, ?, ?, ?)',
        [(hashchain_to_id[x[0] + x[1].to_bytes(4, byteorder='big')], *x[2:]) for x in internal_txs],  # noqa: E501
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evmtx_receipts (
        tx_id INTEGER NOT NULL PRIMARY KEY,
        contract_address TEXT, /* can be null */
        status INTEGER NOT NULL CHECK (status IN (0, 1)),
        type INTEGER NOT NULL,
        FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
    );""")  # noqa: E501
    write_cursor.executemany(
        'INSERT INTO evmtx_receipts(tx_id, contract_address, status, type) '
        'VALUES(?, ?, ?, ?)',
        [(hashchain_to_id[x[0] + x[1].to_bytes(4, byteorder='big')], *x[2:]) for x in receipts],
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evmtx_receipt_logs (
        identifier INTEGER NOT NULL PRIMARY KEY,  /* adding identifier here instead of composite key in order to not duplicate in topics which are A LOT */
        tx_id INTEGER NOT NULL,
        log_index INTEGER NOT NULL,
        data BLOB NOT NULL,
        address TEXT NOT NULL,
        removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
        FOREIGN KEY(tx_id) REFERENCES evmtx_receipts(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
        UNIQUE(tx_id, log_index)
    );""")  # noqa: E501
    hashchainlog_to_id = {}
    log_data = []
    for identifier, data in enumerate(logs):
        hashchain = data[0] + data[1].to_bytes(4, byteorder='big')
        hashchainlog_to_id[hashchain + data[2].to_bytes(4, byteorder='big')] = identifier
        log_data.append((identifier, hashchain_to_id[hashchain], *data[2:]))
    write_cursor.executemany(
        'INSERT INTO evmtx_receipt_logs(identifier, tx_id, log_index, data, address, '
        'removed) VALUES(?, ?, ?, ?, ?, ?)',
        log_data,
    )

    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS evmtx_receipt_log_topics (
        log INTEGER NOT NULL,
        topic BLOB NOT NULL,
        topic_index INTEGER NOT NULL,
        FOREIGN KEY(log) REFERENCES evmtx_receipt_logs(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY(log, topic_index)
    );""")  # noqa: E501
    write_cursor.executemany(
        'INSERT INTO evmtx_receipt_log_topics(log, topic, topic_index) '
        'VALUES(?, ?, ?)',
        [(hashchainlog_to_id[x[0] + x[1].to_bytes(4, byteorder='big') + x[2].to_bytes(4, byteorder='big')], *x[3:]) for x in topics],  # noqa: E501
    )

    log.debug('Exit _update_evm_transaction_data')


def _add_arbitrum_one_location(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _add_arbitrum_one_location')
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("i", 41);')
    log.debug('Exit _add_arbitrum_one_location')


def _update_rpc_nodes_table(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _update_rpc_nodes_table')
    table_exists = write_cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='rpc_nodes'",
    ).fetchone()[0] == 1
    table_to_create = 'rpc_nodes'
    if table_exists is True:
        table_to_create += '_new'
    write_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_to_create}(
        identifier INTEGER NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        weight TEXT NOT NULL,
        blockchain TEXT NOT NULL,
        UNIQUE(endpoint, blockchain)
    );
    """)
    if table_exists is True:
        # For 1.28 we released v2 of the rpc nodes with polygon etherscan instead of
        # polygon pos etherscan. In migration 10 we ensured that if it was
        # present we delete "polygon etherscan" from the rpc nodes. Since data migrations happen
        # after db upgrades we need to be sure that there are no duplicates since in both cases
        # the chain and endpoint is the same.
        write_cursor.execute('DELETE FROM rpc_nodes WHERE name="polygon etherscan"')
        write_cursor.execute(
            'INSERT OR IGNORE INTO rpc_nodes_new SELECT identifier, name, endpoint, owned, '
            'active, weight, blockchain FROM rpc_nodes',
        )
        write_cursor.execute('DROP TABLE rpc_nodes')
        write_cursor.execute('ALTER TABLE rpc_nodes_new RENAME TO rpc_nodes')

    log.debug('Exit _update_rpc_nodes_table')


def _remove_saddle_oracle(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _remove_saddle_oracle')
    write_cursor.execute('SELECT value FROM settings WHERE name="current_price_oracles"')
    if (data := write_cursor.fetchone()) is None:
        return  # oracles not configured
    try:
        oracles: list[str] = json.loads(data[0])
    except json.JSONDecodeError as e:
        log.debug(f'Failed to read oracles from user db. {e!s}')
        return

    new_oracles = [oracle for oracle in oracles if oracle != 'saddle']
    write_cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('current_price_oracles', json.dumps(new_oracles)),
    )
    log.debug('Exit _remove_saddle_oracle')


def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
    """
    Reset all decoded evm events except the customized ones for ethereum mainnet,
    optimism and polygon.
    """
    log.debug('Enter _reset_decoded_events')
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
        '(SELECT tx_hash from_evm_transactions))'
    )
    bindings: tuple = ()
    if customized_events != 0:
        querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
        bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

    write_cursor.execute(querystr, bindings)
    write_cursor.execute(
        'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
        (HISTORY_MAPPING_STATE_DECODED,),
    )
    log.debug('Exit _reset_decoded_events')


def upgrade_v38_to_v39(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v38 to v39. This was in v1.30.0 release.
        - Update NFT table to not use double quotes
        - Reduce size of some event identifiers
        - Primary key of evm tx tables becomes unique integer
        - Reset all decoded events, except the customized ones
        - Add Arbitrum One location and nodes
    """
    log.debug('Entered userdb v38->v39 upgrade')
    progress_handler.set_total_steps(9)
    with db.user_write() as write_cursor:
        _update_nfts_table(write_cursor)
        progress_handler.new_step()
        _reduce_eventid_size(write_cursor)
        progress_handler.new_step()
        _create_new_tables(write_cursor)
        progress_handler.new_step()
        _update_evm_transaction_data(write_cursor)
        progress_handler.new_step()
        _reset_decoded_events(write_cursor)
        progress_handler.new_step()
        _add_arbitrum_one_location(write_cursor)
        progress_handler.new_step()
        _remove_saddle_oracle(write_cursor)
        progress_handler.new_step()
        _update_rpc_nodes_table(write_cursor)
        progress_handler.new_step()

    db.conn.execute('VACUUM;')
    progress_handler.new_step()

    log.debug('Finished userdb v38->v39 upgrade')
