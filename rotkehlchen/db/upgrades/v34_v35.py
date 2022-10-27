import json
import logging
from typing import TYPE_CHECKING, List, Literal, Sequence, Tuple, Type

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    evm_address_to_identifier,
)
from rotkehlchen.db.constants import (
    ACCOUNTS_DETAILS_LAST_QUERIED_TS,
    ACCOUNTS_DETAILS_TOKENS,
    HISTORY_MAPPING_CUSTOMIZED,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER, HistoricalPriceOracle
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind, OracleSource, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _refactor_time_columns(write_cursor: 'DBCursor') -> None:
    """
    The tables that contained time instead of timestamp as column names and need
    to be changed were:
    - timed_balances
    - timed_location_data
    - trades
    - asset_movements
    """
    log.debug('Enter _refactor_time_columns')
    write_cursor.execute('ALTER TABLE timed_balances RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE timed_location_data RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE trades RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE asset_movements RENAME COLUMN time TO timestamp')
    log.debug('Exit _refactor_time_columns')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_notes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        location TEXT NOT NULL,
        last_update_timestamp INTEGER NOT NULL,
        is_pinned INTEGER NOT NULL CHECK (is_pinned IN (0, 1))
    );
    """)


def _remove_unused_assets(write_cursor: 'DBCursor') -> None:
    """Remove any entries in the assets table that are not used at all. By not used
    we mean to look at all foreign key relations and find assets that have None.

    TODO: This probably needs to be happening more often as some DBs seem to have
    gathered a lot of entries in the assets table.
    """
    log.debug('Deleting unused asset ids')
    write_cursor.execute("""
    WITH unique_assets AS (SELECT DISTINCT asset FROM(
        SELECT currency AS asset FROM timed_balances UNION
        SELECT asset1 AS asset FROM aave_events UNION
        SELECT asset2 AS asset FROM aave_events UNION
        SELECT from_asset AS asset FROM yearn_vaults_events UNION
        SELECT to_asset AS asset FROM yearn_vaults_events UNION
        SELECT asset FROM manually_tracked_balances UNION
        SELECT base_asset AS asset FROM trades UNION
        SELECT quote_asset AS asset FROM trades UNION
        SELECT fee_currency AS asset FROM trades UNION
        SELECT pl_currency AS asset FROM margin_positions UNION
        SELECT fee_currency AS asset FROM margin_positions UNION
        SELECT asset FROM asset_movements UNION
        SELECT fee_asset AS asset FROM asset_movements UNION
        SELECT asset FROM ledger_actions UNION
        SELECT rate_asset AS asset FROM ledger_actions UNION
        SELECT token0_identifier AS asset FROM amm_events UNION
        SELECT token1_identifier AS asset FROM amm_events UNION
        SELECT token AS asset FROM adex_events UNION
        SELECT pool_address_token AS asset FROM balancer_events UNION
        SELECT identifier AS asset FROM nfts UNION
        SELECT last_price_asset AS asset FROM nfts UNION
        SELECT asset from history_events
    ) WHERE asset IS NOT NULL)
    DELETE FROM assets WHERE identifier NOT IN unique_assets AND identifier IS NOT NULL
    """)


def _rename_assets_identifiers(write_cursor: 'DBCursor') -> None:
    """Version 1.26 includes the migration for the global db and the references to assets
    need to be updated also in this database.
    We do an update and relay on the cascade effect to update the assets identifiers in the rest
    of the tables.
    """
    log.debug('Enter _rename_assets_identifiers')
    write_cursor.execute('SELECT identifier FROM assets')
    old_id_to_new = {}
    for (identifier,) in write_cursor:
        # We only need to update the ethereum assets and those that will be replaced by evm assets
        # Any other asset should keep the identifier they have now.
        if identifier.startswith(ETHEREUM_DIRECTIVE):
            old_id_to_new[identifier] = evm_address_to_identifier(
                address=identifier[ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
        elif identifier in OTHER_EVM_CHAINS_ASSETS:
            old_id_to_new[identifier] = OTHER_EVM_CHAINS_ASSETS[identifier]

    sqlite_tuples = [(new_id, old_id) for old_id, new_id in old_id_to_new.items()]
    log.debug('About to execute the asset id update with executemany')
    write_cursor.executemany('UPDATE assets SET identifier=? WHERE identifier=?', sqlite_tuples)  # noqa: E501
    log.debug('Exit _rename_assets_identifiers')


def _change_xpub_mappings_primary_key(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """This upgrade includes xpub_mappings' `blockchain` column in primary key.
    After this upgrade it will become possible to create mapping for the same bitcoin address
    and xpub on different blockchains.

    Despite `blockchain` was not previously in the primary key, data in this table should not
    be broken since it has FOREIGN KEY (which includes `blockchain`) referencing xpubs table.
    """
    log.debug('Enter _change_xpub_mappings_primary_key')
    with conn.read_ctx() as read_cursor:
        xpub_mappings = read_cursor.execute('SELECT * from xpub_mappings').fetchall()
    write_cursor.execute("""CREATE TABLE xpub_mappings_copy (
        address TEXT NOT NULL,
        xpub TEXT NOT NULL,
        derivation_path TEXT NOT NULL,
        account_index INTEGER,
        derived_index INTEGER,
        blockchain TEXT NOT NULL,
        FOREIGN KEY(blockchain, address)
        REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
        FOREIGN KEY(xpub, derivation_path, blockchain) REFERENCES xpubs(
            xpub,
            derivation_path,
            blockchain
        ) ON DELETE CASCADE
        PRIMARY KEY (address, xpub, derivation_path, blockchain)
    );
    """)
    write_cursor.executemany('INSERT INTO xpub_mappings_copy VALUES (?, ?, ?, ?, ?, ?)', xpub_mappings)  # noqa: E501
    write_cursor.execute('DROP TABLE xpub_mappings')
    write_cursor.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings')
    log.debug('Exit _change_xpub_mappings_primary_key')


def _clean_amm_swaps(cursor: 'DBCursor') -> None:
    """Since we remove the amm swaps, clean all related DB tables and entries"""
    log.debug('Enter _clean_amm_swaps')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "uniswap_trades%";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "sushiswap_trades%";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "balancer_trades%";')
    cursor.execute('DROP VIEW IF EXISTS combined_trades_view;')
    cursor.execute('DROP TABLE IF EXISTS amm_swaps;')
    log.debug('Exit _clean_amm_swaps')


def _add_blockchain_column_web3_nodes(cursor: 'DBCursor') -> None:
    log.debug('Enter _add_blockchain_column_web3_nodes')
    cursor.execute('ALTER TABLE web3_nodes RENAME TO web3_nodes_old')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web3_nodes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        weight INTEGER NOT NULL,
        blockchain TEXT NOT NULL
    );
    """)
    cursor.execute("INSERT INTO web3_nodes SELECT identifier, name, endpoint, owned, active, weight, 'ETH' FROM web3_nodes_old")  # noqa: E501
    cursor.execute('DROP TABLE web3_nodes_old')
    log.debug('Exit _add_blockchain_column_web3_nodes')


def _update_ignored_assets_identifiers_to_caip_format(cursor: 'DBCursor') -> None:
    log.debug('Enter _update_ignored_assets_identifiers_to_caip_format')
    cursor.execute('SELECT value FROM multisettings WHERE name="ignored_asset";')
    old_ids_to_caip_ids_mappings: List[Tuple[str, str]] = []
    for (old_identifier,) in cursor:
        if old_identifier is not None and old_identifier.startswith(ETHEREUM_DIRECTIVE):
            old_ids_to_caip_ids_mappings.append(
                (
                    evm_address_to_identifier(
                        address=old_identifier[ETHEREUM_DIRECTIVE_LENGTH:],
                        chain=ChainID.ETHEREUM,
                        token_type=EvmTokenKind.ERC20,
                    ),
                    old_identifier,
                ),
            )

    cursor.executemany(
        'UPDATE multisettings SET value=? WHERE value=? AND name="ignored_asset"',
        old_ids_to_caip_ids_mappings,
    )
    log.debug('Exit _update_ignored_assets_identifiers_to_caip_format')


def _update_history_event_assets_identifiers_to_caip_format(cursor: 'DBCursor') -> None:
    """Make sure assets in history events table are upgraded to CAIP format"""
    log.debug('Enter _update_history_event_assets_identifiers_to_caip_format')
    cursor.execute('SELECT * FROM history_events;')
    new_entries = []
    for entry in cursor:
        new_id = entry[6]
        if entry[6].startswith(ETHEREUM_DIRECTIVE):
            new_id = evm_address_to_identifier(
                address=entry[6][ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
        new_entries.append((
            entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], new_id,
            entry[7], entry[8], entry[9], entry[10], entry[11], entry[12], entry[13],
        ))

    cursor.execute('DROP TABLE history_events;')
    cursor.execute("""CREATE TABLE IF NOT EXISTS history_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    event_identifier BLOB NOT NULL,
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
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(event_identifier, sequence_index)
    );""")
    cursor.executemany(
        'INSERT INTO history_events( '
        'identifier, '
        'event_identifier, '
        'sequence_index, '
        'timestamp, '
        'location, '
        'location_label, '
        'asset, '
        'amount, '
        'usd_value, '
        'notes, '
        'type, '
        'subtype, '
        'counterparty, '
        'extra_data) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        new_entries,
    )
    log.debug('Exit _update_history_event_assets_identifiers_to_caip_format')


def _update_assets_in_user_queried_tokens(cursor: 'DBCursor') -> None:
    """ethereum_accounts_details has the column tokens_list as a json list with identifiers
    using the _ceth_ format. Those need to be upgraded to the CAIPS format.
    The approach we took was to refactor this table adding a key-value table with the chain
    attribute to map properties of accounts to different chains
    """
    log.debug('Enter _update_assets_in_user_queried_tokens')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts_details (
        account VARCHAR[42] NOT NULL,
        blockchain TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (account, blockchain, key, value)
    );
    """)
    cursor.execute('SELECT account, tokens_list, time FROM ethereum_accounts_details')
    now = str(ts_now())
    update_rows = []
    for address, token_list, _ in cursor:
        tokens = json.loads(token_list)
        for token in tokens.get('tokens', []):
            new_id = evm_address_to_identifier(
                address=token[ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
            update_rows.append(
                (
                    address,
                    SupportedBlockchain.ETHEREUM.serialize(),
                    ACCOUNTS_DETAILS_TOKENS,
                    new_id,
                ),
            )
        update_rows.append(
            (
                address,
                SupportedBlockchain.ETHEREUM.serialize(),
                ACCOUNTS_DETAILS_LAST_QUERIED_TS,
                now,
            ),
        )
    cursor.executemany(
        'INSERT OR IGNORE INTO accounts_details(account, blockchain, key, value) VALUES(?, ?, ?, ?);',  # noqa: E501
        update_rows,
    )
    cursor.execute('DROP TABLE ethereum_accounts_details')
    log.debug('Enter _update_assets_in_user_queried_tokens')


def _add_manual_current_price_oracle(cursor: 'DBCursor') -> None:
    """
    If user had current price oracles order specified, adds manual current price as the most
    prioritized oracle.
    """
    log.debug('Enter _add_manual_current_price_oracle')
    current_oracles_order = cursor.execute(
        'SELECT value FROM settings WHERE name="current_price_oracles"',
    ).fetchone()
    if current_oracles_order is None:
        return

    list_oracles_order: List = json.loads(current_oracles_order[0])
    list_oracles_order.insert(0, 'manualcurrent')
    cursor.execute(
        'UPDATE settings SET value=? WHERE name="current_price_oracles"',
        (json.dumps(list_oracles_order),),
    )
    log.debug('Exit _add_manual_current_price_oracle')


def _add_defillama_to_oracles(cursor: 'DBCursor', setting_name: Literal['current_price_oracles', 'historical_price_oracles']) -> None:  # noqa: E501
    """
    Adds defillama to the list of current price oracles and historical prices oracles.
    If coingecko is in the list is added just after it, otherwise is added at the end.
    """
    cursor.execute('SELECT value FROM settings WHERE name=?', (setting_name,))
    price_oracles = cursor.fetchone()

    if setting_name == 'current_price_oracles':
        oracle_cls: Type[OracleSource] = CurrentPriceOracle
        default_oracles: Sequence[OracleSource] = DEFAULT_CURRENT_PRICE_ORACLES_ORDER
    else:
        oracle_cls = HistoricalPriceOracle
        default_oracles = DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER

    oracle_list = default_oracles
    if price_oracles is not None:
        oracles = json.loads(price_oracles[0])
        oracle_list = [oracle_cls.deserialize(oracle) for oracle in oracles]
        try:
            # Type ignores here are needed since OracleSource can't have any member
            # or otherwise we would be re-defining them in their subclasses (they take different
            # values).
            coingecko_pos = oracle_list.index(oracle_cls.COINGECKO)  # type: ignore
            oracle_list.insert(coingecko_pos + 1, oracle_cls.DEFILLAMA)  # type: ignore
        except ValueError:
            # If coingecko is not in the list add at the end defillama
            oracle_list.append(oracle_cls.DEFILLAMA)  # type: ignore

    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        (setting_name, json.dumps([x.serialize() for x in oracle_list])),
    )


def _add_defillama_to_all_oracles(write_cursor: 'DBCursor') -> None:
    """Wrapper around _add_defillama_to_oracles to add it in the two possible oracle lists"""
    log.debug('Enter _add_defillama_to_all_oracles')
    _add_defillama_to_oracles(write_cursor, 'current_price_oracles')
    _add_defillama_to_oracles(write_cursor, 'historical_price_oracles')
    log.debug('Exit _add_defillama_to_all_oracles')


def _reset_decoded_events(db: 'DBHandler', write_cursor: 'DBCursor') -> None:
    """Reset all non-user customized decoded events"""
    log.debug('Enter _reset_decoded_events')
    tx_hashes = []
    with db.conn.read_ctx() as cursor:
        for entry in cursor:
            tx_hashes.append(entry[0])
    db_events = DBHistoryEvents(db)
    db_events.delete_events_by_tx_hash(write_cursor, tx_hashes)
    write_cursor.execute(
        'DELETE from evm_tx_mappings WHERE value !=?',
        (HISTORY_MAPPING_CUSTOMIZED,),
    )
    log.debug('Exit _reset_decoded_events')


def upgrade_v34_to_v35(db: 'DBHandler') -> None:
    """Upgrades the DB from v34 to v35
    - Change tables where time is used as column name to timestamp
    - Add user_notes table
    - Renames the asset identifiers to use CAIPS
    """
    log.debug('Entered userdb v34->v35 upgrade')
    with db.user_write() as write_cursor:
        _clean_amm_swaps(write_cursor)
        _remove_unused_assets(write_cursor)
        _rename_assets_identifiers(write_cursor)
        _update_ignored_assets_identifiers_to_caip_format(write_cursor)
        _refactor_time_columns(write_cursor)
        _create_new_tables(write_cursor)
        _change_xpub_mappings_primary_key(write_cursor=write_cursor, conn=db.conn)
        _add_blockchain_column_web3_nodes(write_cursor)
        _update_assets_in_user_queried_tokens(write_cursor)
        _update_history_event_assets_identifiers_to_caip_format(write_cursor)
        _add_manual_current_price_oracle(write_cursor)
        update_spam_assets(write_cursor=write_cursor, db=db, make_remote_query=False)
        _add_defillama_to_all_oracles(write_cursor=write_cursor)
        _reset_decoded_events(db=db, write_cursor=write_cursor)
    log.debug('Finished userdb v34->v35 upgrade')
