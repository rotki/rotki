import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.upgrades.upgrade_utils import process_solana_asset_migration
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v12->v13 upgrade')
def migrate_to_v13(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Add new token kinds (SPL Tokens & NFTs) for the solana ecosystem.
    - Add solana_tokens table and migrate solana tokens to that.
    - Convert legacy protocol names in evm_tokens to standardized counterparty identifiers.
    - Migrate BALANCER_GAUGES cache entries to version-specific BALANCER_V1_GAUGES and BALANCER_V2_GAUGES.

    This upgrade takes place in v1.40.0"""  # noqa: E501
    @progress_step('Add new token kinds for Solana')
    def _update_token_kinds_to_include_solana(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
            /* SPL TOKEN */
            INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('D', 4);
            /* SPL NFT */
            INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('E', 5);
        """)

    @progress_step('Add solana tokens table and populate from CSV')
    def _add_and_populate_solana_tokens(write_cursor: 'DBCursor') -> None:
        """Create solana tokens table and update asset identifiers to use new solana format"""
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS solana_tokens (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            token_kind CHAR(1) NOT NULL DEFAULT('D') REFERENCES token_kinds(token_kind),
            address VARCHAR[44] NOT NULL,
            decimals INTEGER,
            protocol TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        )""")  # noqa: E501

        write_cursor.switch_foreign_keys('OFF')
        if len(solana_tokens_data := process_solana_asset_migration(
            write_cursor=write_cursor,
            table_updates=[
                ('assets', 'identifier'),
                ('common_asset_details', 'identifier'),
                ('asset_collections', 'main_asset'),
                ('multiasset_mappings', 'asset'),
                ('user_owned_assets', 'asset_id'),
                ('price_history', 'from_asset'),
                ('price_history', 'to_asset'),
                ('binance_pairs', 'base_asset'),
                ('binance_pairs', 'quote_asset'),
                ('counterparty_asset_mappings', 'local_id'),
                ('location_asset_mappings', 'local_id'),
            ],
        )) == 0:
            log.error('Missing required CSV file. This should not happen. Bailing...')
            return

        write_cursor.executemany(
            'INSERT INTO solana_tokens(identifier, token_kind, address, decimals, protocol) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            solana_tokens_data,
        )
        write_cursor.execute('CREATE INDEX IF NOT EXISTS idx_solana_tokens_identifier ON solana_tokens (identifier, protocol);')  # noqa: E501
        write_cursor.switch_foreign_keys('ON')
        # Delete the known duplicates
        write_cursor.execute('DELETE FROM assets WHERE identifier IN (?, ?)', ('TRISIG', 'HODLSOL'))  # noqa: E501

    @progress_step('Move user-added solana tokens to different type')
    def _migrate_user_solana_tokens(write_cursor: 'DBCursor') -> None:
        if len(user_tokens := write_cursor.execute(
            'SELECT identifier FROM assets WHERE type = ? AND identifier NOT LIKE ?',
            ('Y', 'solana%'),
        ).fetchall()) == 0:
            return  # no user added solana tokens present.

        write_cursor.executemany(  # change these tokens to generic 'W' type
            'UPDATE assets SET type = ? WHERE identifier = ?',
            [('W', t[0]) for t in user_tokens],
        )

        # create tracking table for user-added solana tokens
        write_cursor.execute("""
       CREATE TABLE IF NOT EXISTS user_added_solana_tokens (
           identifier TEXT NOT NULL UNIQUE,
           FOREIGN KEY (identifier) REFERENCES assets(identifier) ON DELETE CASCADE
       );
       """)
        write_cursor.executemany(  # record which tokens were user-added for manual upgrade
            'INSERT INTO user_added_solana_tokens(identifier) VALUES (?)',
            user_tokens,
        )

    @progress_step('Update token protocols to use counterparty identifiers')
    def _update_token_protocols_to_counterparties(write_cursor: 'DBCursor') -> None:
        """Updates token protocol identifiers to use their corresponding counterparty values."""
        write_cursor.execute("""
            UPDATE evm_tokens SET protocol = CASE protocol
                WHEN 'aerodrome_pool' THEN 'aerodrome'
                WHEN 'velodrome_pool' THEN 'velodrome'
                WHEN 'pickle_jar' THEN 'pickle finance'
                WHEN 'SLP' THEN 'sushiswap-v2'
                WHEN 'UNI-V2' THEN 'uniswap-v2'
                WHEN 'UNI-V3' THEN 'uniswap-v3'
                WHEN 'yearn_vaults_v1' THEN 'yearn-v1'
                WHEN 'yearn_vaults_v2' THEN 'yearn-v2'
                WHEN 'yearn_vaults_v3' THEN 'yearn-v3'
                WHEN 'curve_pool' THEN 'curve'
                WHEN 'curve_lending_vaults' THEN 'curve'
                WHEN 'pendle' THEN 'pendle'
                WHEN 'hop_lp' THEN 'hop'
                WHEN 'morpho_vaults' THEN 'morpho'
                ELSE protocol
            END
            WHERE protocol IN (
                'aerodrome_pool', 'velodrome_pool', 'pickle_jar', 'SLP', 'UNI-V2', 'UNI-V3',
                'yearn_vaults_v1', 'yearn_vaults_v2', 'yearn_vaults_v3', 'curve_pool',
                'curve_lending_vaults', 'pendle', 'hop_lp', 'morpho_vaults'
            )
        """)

    @progress_step('Migrate balancer gauge cache entries to version-specific keys')
    def _migrate_balancer_gauges_cache_entries(write_cursor: 'DBCursor') -> None:
        """Migrate BALANCER_GAUGES cache entries to separate V1/V2 cache types.

        Old format: BALANCER_GAUGES<chain_id><version>
        New format: BALANCER_V1_GAUGES<chain_id> or BALANCER_V2_GAUGES<chain_id>
        """
        write_cursor.execute("""
            UPDATE general_cache
            SET key = CASE
                -- Balancer V1 chains
                WHEN key = 'BALANCER_GAUGES1001' THEN 'BALANCER_V1_GAUGES100'    -- Gnosis V1
                WHEN key = 'BALANCER_GAUGES11' THEN 'BALANCER_V1_GAUGES1'        -- Ethereum V1
                WHEN key = 'BALANCER_GAUGES421611' THEN 'BALANCER_V1_GAUGES42161' -- Arbitrum V1
                -- Balancer V2 chains
                WHEN key = 'BALANCER_GAUGES84532' THEN 'BALANCER_V2_GAUGES8453'   -- Base V2
                WHEN key = 'BALANCER_GAUGES1002' THEN 'BALANCER_V2_GAUGES100'     -- Gnosis V2
                WHEN key = 'BALANCER_GAUGES12' THEN 'BALANCER_V2_GAUGES1'         -- Ethereum V2
                WHEN key = 'BALANCER_GAUGES102' THEN 'BALANCER_V2_GAUGES10'       -- Optimism V2
                WHEN key = 'BALANCER_GAUGES1372' THEN 'BALANCER_V2_GAUGES137'     -- Polygon V2
                WHEN key = 'BALANCER_GAUGES421612' THEN 'BALANCER_V2_GAUGES42161' -- Arbitrum V2
                ELSE key
            END
            WHERE key LIKE 'BALANCER_GAUGES%'
        """)
        write_cursor.execute("DELETE FROM general_cache WHERE key LIKE 'BALANCER_GAUGES%'")

    @progress_step('Combine exchange asset mappings')
    def _combine_exchange_asset_mappings(write_cursor: 'DBCursor') -> None:
        """Combine the mappings for exchanges that have multiple locations but common mappings."""
        for old_location, new_location in (
            ('S', 'E'),  # BinanceUS, Binance
            ('u', 'G'),  # CoinbasePrime, Coinbase
        ):
            write_cursor.execute(
                'UPDATE OR IGNORE location_asset_mappings SET location=? WHERE location=?',
                (new_location, old_location),
            )
            write_cursor.execute(
                'DELETE FROM location_asset_mappings WHERE location=?',
                (old_location,),
            )

    perform_globaldb_upgrade_steps(connection, progress_handler)
