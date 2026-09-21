import json
import logging
import re
import uuid
from typing import TYPE_CHECKING, Final

from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.locations.legacy_chars import (
    LEGACY_LOCATIONS_PARENT,
    V53_LEGACY_LOCATION_CHARS,
    V53_LOCATION_CHAR_TO_IDENTIFIER,
)
from rotkehlchen.locations.types import LocationTreeError
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# v54 definitions of every table whose location column moves from the one-character encoding to
# a text identifier, with the name of that column. `{table}` is the name to create the table as.
# Every column but credential locations references the location tree. Derived tables may lose
# rows with an unknown location, all other tables fail the upgrade instead.
_V54_LOCATION_TABLES: Final = (
    ('history_events', 'location', False, """
CREATE TABLE {table} (
    identifier INTEGER NOT NULL PRIMARY KEY,
    entry_type INTEGER NOT NULL,
    group_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL REFERENCES locations(identifier),
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    extra_data TEXT,
    ignored INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(group_identifier, sequence_index)
);"""),
    ('history_events_backup', 'location', False, """
CREATE TABLE {table} (
    identifier INTEGER NOT NULL PRIMARY KEY,
    entry_type INTEGER NOT NULL,
    group_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL REFERENCES locations(identifier),
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    extra_data TEXT,
    ignored INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(group_identifier, sequence_index)
);"""),
    ('timed_location_data', 'location', False, """
CREATE TABLE {table} (
    timestamp INTEGER,
    location TEXT NOT NULL REFERENCES locations(identifier),
    usd_value TEXT,
    PRIMARY KEY (timestamp, location)
);"""),
    ('manually_tracked_balances', 'location', False, """
CREATE TABLE {table} (
    id INTEGER PRIMARY KEY,
    asset TEXT NOT NULL,
    label TEXT NOT NULL UNIQUE,
    amount TEXT,
    location TEXT NOT NULL REFERENCES locations(identifier),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);"""),
    ('margin_positions', 'location', False, """
CREATE TABLE {table} (
    id TEXT PRIMARY KEY,
    location TEXT NOT NULL REFERENCES locations(identifier),
    open_time INTEGER,
    close_time INTEGER,
    profit_loss TEXT,
    pl_currency TEXT NOT NULL,
    fee TEXT,
    fee_currency TEXT,
    link TEXT,
    notes TEXT,
    FOREIGN KEY(pl_currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(fee_currency) REFERENCES assets(identifier) ON UPDATE CASCADE
);"""),
    ('skipped_external_events', 'location', False, """
CREATE TABLE {table} (
    identifier INTEGER NOT NULL PRIMARY KEY,
    data TEXT NOT NULL,
    location TEXT NOT NULL REFERENCES locations(identifier),
    extra_data TEXT,
    UNIQUE(data, location)
);"""),
    ('bitcoin_transactions', 'location', False, """
CREATE TABLE {table} (
    identifier INTEGER NOT NULL PRIMARY KEY,
    location TEXT NOT NULL REFERENCES locations(identifier),
    tx_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    block_height INTEGER NOT NULL,
    fee INTEGER NOT NULL,
    vin_count INTEGER,
    vout_count INTEGER,
    UNIQUE(location, tx_id)
);"""),
    ('event_metrics', 'location', True, """
CREATE TABLE {table} (
    id INTEGER NOT NULL PRIMARY KEY,
    event_identifier INTEGER NOT NULL REFERENCES history_events(identifier) ON DELETE CASCADE,
    location TEXT NOT NULL REFERENCES locations(identifier),
    location_label TEXT,
    protocol TEXT,
    metric_key TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    asset TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    sequence_index INTEGER NOT NULL,
    sort_key INTEGER NOT NULL,
    UNIQUE(event_identifier, location_label, protocol, metric_key, asset)
);"""),
    ('data_issues', 'location', True, """
CREATE TABLE {table} (
    id INTEGER NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL,
    location TEXT NOT NULL REFERENCES locations(identifier),
    location_label TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    asset TEXT NOT NULL DEFAULT '',
    event_identifier INTEGER,
    ts_start INTEGER NOT NULL,
    ts_end INTEGER NOT NULL,
    severity TEXT NOT NULL,
    state TEXT NOT NULL,
    auto_remediation_attempts_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);"""),
    ('user_credentials', 'location', False, """
CREATE TABLE {table} (
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT,
    PRIMARY KEY (name, location)
);"""),
    ('user_credentials_mappings', 'credential_location', False, """
CREATE TABLE {table} (
    credential_name TEXT NOT NULL,
    credential_location TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    FOREIGN KEY(credential_name, credential_location) REFERENCES user_credentials(name, location) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY (credential_name, credential_location, setting_name)
);"""),  # noqa: E501
)


def _add_location_tree(write_cursor: DBCursor) -> None:
    """Create and seed the location tree, add the legacy protocol-labelled locations that
    user data still references and fill the temporary old-to-new mapping table."""
    write_cursor.execute("""
    CREATE TABLE locations (
        identifier TEXT PRIMARY KEY NOT NULL,
        name TEXT NOT NULL,
        parent_identifier TEXT REFERENCES locations(identifier),
        is_builtin INTEGER NOT NULL CHECK(is_builtin IN (0, 1)),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
        icon TEXT,
        image TEXT,
        CHECK(identifier != ''),
        CHECK(name != ''),
        CHECK(parent_identifier IS NULL OR parent_identifier != identifier)
    );""")
    write_cursor.execute(
        'CREATE INDEX idx_locations_parent ON locations(parent_identifier);',
    )
    write_cursor.execute(
        'CREATE UNIQUE INDEX unique_locations_sibling_name '
        'ON locations(parent_identifier, name COLLATE NOCASE);',
    )
    write_cursor.execute("""
    CREATE TABLE location_aliases (
        alias TEXT NOT NULL COLLATE NOCASE PRIMARY KEY,
        location_identifier TEXT NOT NULL REFERENCES locations(identifier) ON DELETE CASCADE,
        CHECK(alias != '')
    );""")
    DBLocations.seed_builtin_locations(write_cursor)

    # the old location table lists every enum member, so only real references count as usage
    legacy_placeholders = ','.join('?' * len(V53_LEGACY_LOCATION_CHARS))
    referenced_legacy: set[str] = set()
    for table, column, _, _ in _V54_LOCATION_TABLES:
        referenced_legacy.update(row[0] for row in write_cursor.execute(
            f'SELECT DISTINCT {column} FROM {table} WHERE {column} IN ({legacy_placeholders})',
            tuple(V53_LEGACY_LOCATION_CHARS),
        ))

    mapping = dict(V53_LOCATION_CHAR_TO_IDENTIFIER)
    if len(referenced_legacy) != 0:
        parent_id, parent_name, grandparent_id, parent_icon = LEGACY_LOCATIONS_PARENT
        write_cursor.execute(
            'INSERT INTO locations(identifier, name, parent_identifier, is_builtin, is_active, '
            'icon, image) VALUES (?, ?, ?, 1, 0, ?, NULL)',
            (parent_id, parent_name, grandparent_id, parent_icon),
        )
        for char in sorted(referenced_legacy):
            identifier, name, image = V53_LEGACY_LOCATION_CHARS[char]
            write_cursor.execute(
                'INSERT INTO locations(identifier, name, parent_identifier, is_builtin, '
                'is_active, icon, image) VALUES (?, ?, ?, 1, 0, NULL, ?)',
                (identifier, name, parent_id, image),
            )
            mapping[char] = identifier

    write_cursor.execute(
        'CREATE TEMP TABLE location_char_mapping (old TEXT PRIMARY KEY, new TEXT NOT NULL)',
    )
    write_cursor.executemany(
        'INSERT INTO location_char_mapping(old, new) VALUES (?, ?)', list(mapping.items()),
    )


def _rebuild_location_table(
        write_cursor: DBCursor,
        table: str,
        column: str,
        derived: bool,
        create_sql: str,
) -> None:
    """Recreate a table with a text location column, mapping every old character through
    location_char_mapping. Foreign keys must be off so that dropping the old table does not
    cascade into its children. Indexes are recreated as they were.

    May raise DBUpgradeError if a non-derived table holds an unknown location.
    """
    columns = [row[1] for row in write_cursor.execute(f'PRAGMA table_info({table})')]
    indexes = [row[0] for row in write_cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
        (table,),
    )]
    old_count = write_cursor.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    unmapped = write_cursor.execute(
        f'SELECT COUNT(*) FROM {table} WHERE {column} NOT IN '
        '(SELECT old FROM location_char_mapping)',
    ).fetchone()[0]
    if unmapped != 0:
        if not derived:
            raise DBUpgradeError(f'{unmapped} rows of {table} have an unknown location')
        log.warning('Dropping %s rows of %s with an unknown location', unmapped, table)

    write_cursor.execute(create_sql.format(table=f'{table}_new'))
    write_cursor.execute(
        f'INSERT INTO {table}_new({", ".join(columns)}) SELECT '
        f'{", ".join("M.new" if x == column else f"T.{x}" for x in columns)} '
        f'FROM {table} T JOIN location_char_mapping M ON T.{column}=M.old',
    )
    if (new_count := write_cursor.execute(f'SELECT COUNT(*) FROM {table}_new').fetchone()[0]) != old_count - unmapped:  # noqa: E501
        raise DBUpgradeError(f'{table} has {new_count} rows after the upgrade instead of {old_count - unmapped}')  # noqa: E501
    write_cursor.execute(f'DROP TABLE {table}')
    write_cursor.execute(f'ALTER TABLE {table}_new RENAME TO {table}')
    for index_sql in indexes:
        write_cursor.execute(index_sql)


# Tails, after `{location}_{name}_`, of every v53 key_value_cache key of one exchange or bank
# connection. Each placeholder is one underscore-free segment, so that the keys of `main` are
# not confused with those of `main_backup`.
_V53_CONNECTION_CACHE_TAILS: Final = tuple(re.compile(pattern) for pattern in (
    'last_cryptotx_offset',
    'bank_session',
    '[^_]+_last_query_ts',  # a per account cursor or binance pair progress
    '[^_]+_last_query_id',
    '[^_]+',  # binance pair progress
))
_V53_CONNECTION_RANGE_KINDS: Final = ('history_events', 'history_events_futures', 'margins', 'lending_history')  # noqa: E501
_V53_BANK_CONNECTORS: Final = ('qonto', 'fints')


def _move_credentials_to_connections(write_cursor: DBCursor) -> None:
    """Give every exchange and bank credential a stable connection identifier, and key its
    settings, query ranges, caches and non-syncing entry by that identifier instead of by
    location and name. Premium credentials stay in user_credentials.

    FinTS was only ever stored by the unreleased v54, keyed by its connector. Its connections
    point at the broad Banks location.
    """
    write_cursor.execute("""
CREATE TABLE IF NOT EXISTS integration_connections (
    identifier TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    connector_identifier TEXT NOT NULL,
    location_identifier TEXT NOT NULL REFERENCES locations(identifier),
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT,
    UNIQUE(connector_identifier, name)
);""")
    write_cursor.execute("""
CREATE TABLE IF NOT EXISTS integration_connection_settings (
    connection_identifier TEXT NOT NULL REFERENCES integration_connections(identifier) ON DELETE CASCADE,
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    PRIMARY KEY (connection_identifier, setting_name)
);""")  # noqa: E501
    locations = {row[0] for row in write_cursor.execute('SELECT identifier FROM locations')}
    credentials = write_cursor.execute(
        'SELECT name, location, api_key, api_secret, passphrase FROM user_credentials '
        "WHERE name != 'rotkehlchen'",
    ).fetchall()
    identifiers: dict[tuple[str, str], str] = {}
    # longer names first, so that a name that prefixes another one never claims its caches
    for name, connector, api_key, api_secret, passphrase in sorted(credentials, key=lambda x: -len(x[0])):  # noqa: E501
        location = 'banks' if connector == 'fints' else connector
        if location not in locations:
            log.warning('Dropping %s credentials %s of an unknown connector', connector, name)
            continue

        identifiers[connector, name] = (identifier := str(uuid.uuid4()))
        write_cursor.execute(
            'INSERT INTO integration_connections(identifier, name, connector_identifier, '
            'location_identifier, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (identifier, name, connector, location, api_key, api_secret, passphrase),
        )
        write_cursor.execute(
            'INSERT INTO integration_connection_settings(connection_identifier, setting_name, '
            'setting_value) SELECT ?, setting_name, setting_value FROM user_credentials_mappings '
            'WHERE credential_name=? AND credential_location=?',
            (identifier, name, connector),
        )
        write_cursor.executemany(
            'UPDATE OR REPLACE used_query_ranges SET name=? WHERE name=?',
            [(f'{identifier}_{kind}', f'{connector}_{kind}_{name}') for kind in _V53_CONNECTION_RANGE_KINDS],  # noqa: E501
        )
        cache_name = name.encode().hex() if connector in _V53_BANK_CONNECTORS else name
        old_prefix = f'{connector}_{cache_name}_'
        write_cursor.executemany(
            'UPDATE OR REPLACE key_value_cache SET name=? WHERE name=?',
            [
                (f'{identifier}_{key.removeprefix(old_prefix)}', key)
                for key, in write_cursor.execute(
                    'SELECT name FROM key_value_cache WHERE substr(name, 1, ?)=?',
                    (len(old_prefix), old_prefix),
                ).fetchall()
                if any(x.fullmatch(key.removeprefix(old_prefix)) for x in _V53_CONNECTION_CACHE_TAILS)  # noqa: E501
            ],
        )

    if (row := write_cursor.execute(
        "SELECT value FROM settings WHERE name='non_syncing_exchanges'",
    ).fetchone()) is not None:
        write_cursor.execute(
            "UPDATE settings SET value=? WHERE name='non_syncing_exchanges'",
            (json.dumps(sorted(
                identifiers[key] for entry in json.loads(row[0])
                if (key := (entry['location'], entry['name'])) in identifiers
            )),),
        )

    write_cursor.execute("DELETE FROM user_credentials WHERE name != 'rotkehlchen'")
    write_cursor.execute('DROP TABLE user_credentials_mappings')
    if len(violations := write_cursor.execute('PRAGMA foreign_key_check(integration_connections)').fetchall()) != 0:  # noqa: E501
        raise DBUpgradeError(f'Connections with unknown locations: {violations}')


@enter_exit_debug_log(name='UserDB v53->v54 upgrade')
def upgrade_v53_to_v54(db: DBHandler, progress_handler: DBUpgradeProgressHandler) -> None:
    """Upgrades the DB from v53 to v54. This happened in 1.45."""

    @progress_step(description='Add capability statuses to RPC nodes.')
    def _add_rpc_node_capabilities(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'ALTER TABLE rpc_nodes ADD COLUMN is_archive INTEGER CHECK (is_archive IN (0, 1))',
        )
        write_cursor.execute(
            'ALTER TABLE rpc_nodes ADD COLUMN is_pruned INTEGER CHECK (is_pruned IN (0, 1))',
        )

    @progress_step(description='Remove notes that rotki now generates from event data.')
    def _remove_generated_notes(write_cursor: DBCursor) -> None:
        """Notes of gas, approvals, deploys, transactions to self, plain transfers, ETH staking
        events and Solana fees are since this version generated at read time from the event's
        other columns. Null every stored note that equals the text rotki generated for it,
        matching the templates of the decoders of this version. Any other note, be it edited by
        the user, extended by a protocol decoder or written with a symbol the asset no longer
        has, stays stored.

        The asset symbols the decoders wrote into the notes are only in the global DB, so they
        are copied into a temporary table for the exact comparison.
        """
        write_cursor.execute(  # staking event notes were never read back from the DB
            'UPDATE history_events SET notes=NULL WHERE entry_type IN (3, 4, 5)',  # withdrawal, block, deposit  # noqa: E501
        )
        user_assets = {row[0] for row in write_cursor.execute('SELECT identifier FROM assets')}
        with GlobalDBHandler().conn.read_ctx() as global_cursor:
            symbols = [
                (identifier, symbol) for identifier, symbol in global_cursor.execute(
                    'SELECT A.identifier, COALESCE(C.symbol, A.name) FROM assets AS A '
                    'LEFT JOIN common_asset_details AS C ON A.identifier=C.identifier',
                ) if identifier in user_assets and symbol is not None
            ]
        write_cursor.execute('CREATE TEMP TABLE asset_symbols(identifier TEXT PRIMARY KEY COLLATE NOCASE, symbol TEXT NOT NULL)')  # noqa: E501
        write_cursor.executemany('INSERT OR IGNORE INTO asset_symbols VALUES (?, ?)', symbols)
        evm_basics = (
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier '
            'JOIN asset_symbols S ON S.identifier=H.asset WHERE H.entry_type=2 AND ('  # evm event
        )
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            f'{evm_basics}'
            "(H.subtype='fee' AND C.counterparty='gas' AND ("
            "(H.type='spend' AND H.notes='Burn ' || H.amount || ' ' || S.symbol || ' for gas') OR "
            "(H.type='fail' AND H.notes='Burn ' || H.amount || ' ' || S.symbol || ' for gas of a failed transaction')"  # noqa: E501
            ')) OR '
            "(H.type='informational' AND H.subtype='approve' AND C.counterparty IS NULL AND ("
            "(H.amount='0' AND H.notes='Revoke ' || S.symbol || ' spending approval of ' || H.location_label || ' by ' || C.address) OR "  # noqa: E501
            "(H.amount!='0' AND H.notes='Set ' || S.symbol || ' spending approval of ' || H.location_label || ' by ' || C.address || ' to ' || H.amount)"  # noqa: E501
            ')) OR '
            "(H.type='deploy' AND H.notes='Deploy a new contract at ' || C.address) OR "
            "(H.type='transaction to self' AND H.subtype='none' AND ("
            "(H.amount='0' AND H.notes='No value transaction to self') OR "
            "(H.amount!='0' AND H.notes='Transaction to self of ' || H.amount || ' ' || S.symbol)"
            '))'
            '))',
        )
        # Plain transfers. The verb and preposition follow the type. Native asset transfers
        # name only the other side, token transfers both. The location codes and native asset
        # identifiers are those of the EVM chains with transactions at this version.
        verb = "CASE H.type WHEN 'spend' THEN 'Send' WHEN 'receive' THEN 'Receive' WHEN 'transfer' THEN 'Transfer' WHEN 'deposit' THEN 'Deposit' ELSE 'Withdraw' END"  # noqa: E501
        outgoing = "H.type IN ('spend', 'transfer', 'deposit')"
        other_side = 'COALESCE(C.counterparty, C.address)'
        amount_and_symbol = "H.amount || ' ' || S.symbol"
        native_asset = (
            "((H.location IN ('f', 'g', 'i', 'j', 'n', 'o', char(127)) AND H.asset='ETH') OR "  # ethereum, optimism, arbitrum, base, scroll, zksync lite, robinhood  # noqa: E501
            "(H.location='h' AND H.asset='eip155:137/erc20:0x0000000000000000000000000000000000001010') OR "  # polygon  # noqa: E501
            "(H.location='k' AND H.asset='XDAI') OR (H.location='v' AND H.asset='BNB') OR "  # gnosis, bsc  # noqa: E501
            "(H.location='y' AND H.asset='HYPE') OR (H.location='z' AND H.asset='MON') OR "  # hyperliquid, monad  # noqa: E501
            "(H.location='~' AND H.asset='S'))"  # sonic
        )
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            f'{evm_basics}'
            "((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            ') AND ('
            f"({native_asset} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side}) OR "  # noqa: E501
            f"(NOT {native_asset} AND H.asset NOT LIKE '%/erc721:%' AND ("
            f"({outgoing} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' from ' || H.location_label || ' to ' || {other_side}) OR "  # noqa: E501
            f"(NOT {outgoing} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' from ' || {other_side} || ' to ' || H.location_label)"  # noqa: E501
            '))'
            ')))',
        )
        write_cursor.execute(  # solana fees and plain transfers naming the other side
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier '
            'JOIN asset_symbols S ON S.identifier=H.asset WHERE H.entry_type=9 AND ('  # solana event  # noqa: E501
            "(H.type='spend' AND H.subtype='fee' AND C.counterparty='gas' AND H.notes='Spend ' || H.amount || ' SOL as transaction fee') OR "  # noqa: E501
            "(((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            f") AND H.notes={verb} || ' ' || {amount_and_symbol} || ' ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side})"  # noqa: E501
            '))',
        )
        write_cursor.execute('DROP TABLE asset_symbols')

    @progress_step(description='Create the location tree.')
    def _create_location_tree(write_cursor: DBCursor) -> None:
        _add_location_tree(write_cursor)

    @progress_step(description='Convert the locations of history events.')
    def _convert_history_event_locations(write_cursor: DBCursor) -> None:
        write_cursor.switch_foreign_keys('OFF')
        for entry in _V54_LOCATION_TABLES[:2]:
            _rebuild_location_table(write_cursor, *entry)
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Convert the locations of balances, snapshots and credentials.')
    def _convert_other_locations(write_cursor: DBCursor) -> None:
        write_cursor.switch_foreign_keys('OFF')
        for entry in _V54_LOCATION_TABLES[2:]:
            _rebuild_location_table(write_cursor, *entry)
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Remove the old location table and verify the location tree.')
    def _finish_location_tree(write_cursor: DBCursor) -> None:
        write_cursor.execute('DROP TABLE location')
        write_cursor.execute('DROP TABLE location_char_mapping')
        for table, _, _, _ in _V54_LOCATION_TABLES:
            if len(violations := [
                row for row in write_cursor.execute(f'PRAGMA foreign_key_check({table})')
                if row[2] == 'locations'
            ]) != 0:
                raise DBUpgradeError(f'{table} has rows with unknown locations: {violations}')
        try:
            DBLocations().validate_tree(write_cursor)
        except LocationTreeError as e:
            raise DBUpgradeError(f'Invalid location tree after the upgrade: {e!s}') from e

    @progress_step(description='Move exchange and bank credentials to connections.')
    def _move_credentials(write_cursor: DBCursor) -> None:
        _move_credentials_to_connections(write_cursor)

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
