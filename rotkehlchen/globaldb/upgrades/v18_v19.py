import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.chain.evm.decoding.aave.constants import (
    CPT_AAVE,
    CPT_AAVE_V1,
    CPT_AAVE_V2,
    CPT_AAVE_V3,
)
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.globaldb.schema import DB_CREATE_HISTORICAL_PRICE_MISSES
from rotkehlchen.locations.legacy_chars import V53_CHAR_TO_NAME
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# ERC-4626 Spark Savings V2 vaults whose symbols also start with "sp" (unlike Spark Lend aTokens).
SPARK_SAVINGS_V2_VAULT_ADDRESSES: Final = (
    '0x28B3a8fb53B741A8Fd78c0fb9A6B2393d896a43d',  # spUSDC
    '0xe2e7a17dFf93280dec073C995595155283e3C372',  # spUSDT
    '0xfE6eb3b609a7C8352A241f7F3A21CEA4e9209B8f',  # spETH
    '0x80128DbB9f07b93DDE62A6daeadb69ED14a7D354',  # spPYUSD
)


@enter_exit_debug_log(name='globaldb v18->v19 upgrade')
def migrate_to_v19(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """Add Birdeye as a historical price source, indexes for asset lookups, historical price
    misses caching table, key exchange asset mappings and binance pairs by connector
    identifier instead of a location character, and populate lending asset flags.

    This upgrade takes place in v1.45
    """

    @progress_step('Adding Birdeye to price_history_source_types')
    def _add_birdeye_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('L', 12),
        )

    @progress_step('Adding historical_price_misses table')
    def _add_historical_price_misses_table(write_cursor: DBCursor) -> None:
        write_cursor.execute(DB_CREATE_HISTORICAL_PRICE_MISSES)

    @progress_step('Adding indexes for asset lookups')
    def _add_asset_lookup_indexes(write_cursor: DBCursor) -> None:
        """Add indexes for token identity, protocol, symbol and collection lookups.

        The two NOCASE indexes match the collation the joins against assets(identifier)
        inherit, which the existing BINARY indexes cannot serve.
        """
        for query in (
            'CREATE INDEX IF NOT EXISTS idx_evm_tokens_address_chain ON evm_tokens (address, chain);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_evm_tokens_chain_protocol ON evm_tokens (chain, protocol);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_common_asset_details_symbol_nocase ON common_asset_details (symbol COLLATE NOCASE);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_multiasset_mappings_asset_nocase ON multiasset_mappings (asset COLLATE NOCASE);',  # noqa: E501
        ):
            write_cursor.execute(query)

    @progress_step('Storing exchange locations as text identifiers')
    def _convert_location_characters(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'CREATE TEMP TABLE location_char_mapping (old TEXT PRIMARY KEY, new TEXT NOT NULL)',
        )
        write_cursor.executemany(
            'INSERT INTO location_char_mapping(old, new) VALUES (?, ?)',
            list(V53_CHAR_TO_NAME.items()),
        )
        for table in ('location_asset_mappings', 'binance_pairs'):
            if (unknown := write_cursor.execute(
                f'DELETE FROM {table} WHERE location IS NOT NULL AND location NOT IN '
                '(SELECT old FROM location_char_mapping)',
            ).rowcount) != 0:
                log.warning('Removed %s %s rows with an unknown location', unknown, table)
            write_cursor.execute(
                f'UPDATE {table} SET location=(SELECT new FROM location_char_mapping '
                f'WHERE old={table}.location) WHERE location IS NOT NULL',
            )
        write_cursor.execute('DROP TABLE location_char_mapping')

    @progress_step('Keying asset mappings and binance pairs by connector')
    def _rename_to_connectors(write_cursor: DBCursor) -> None:
        """The rows describe the symbol namespace of a connector, not where an event
        happened. The converted names are already the connector identifiers."""
        write_cursor.execute('DROP INDEX IF EXISTS idx_location_mappings_identifier')
        write_cursor.execute('ALTER TABLE location_asset_mappings RENAME TO connector_asset_mappings')  # noqa: E501
        write_cursor.execute('ALTER TABLE connector_asset_mappings RENAME COLUMN location TO connector')  # noqa: E501
        write_cursor.execute('CREATE INDEX IF NOT EXISTS idx_connector_mappings_identifier ON connector_asset_mappings (local_id)')  # noqa: E501
        write_cursor.execute('ALTER TABLE binance_pairs RENAME COLUMN location TO connector')

    @progress_step('Populating asset flags for Aave and Spark lending tokens')
    def _populate_lending_asset_flags(write_cursor: DBCursor) -> None:
        # Aave v1/v2 tokens and Aave v3/Spark stable debt tokens are marked rebasing.
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT identifier, ? FROM evm_tokens WHERE protocol IN (?, ?, ?)',
            (AssetFlag.REBASING.value, CPT_AAVE, CPT_AAVE_V1, CPT_AAVE_V2),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT et.identifier, ? '
            'FROM evm_tokens AS et '
            'JOIN common_asset_details AS cad ON cad.identifier = et.identifier '
            "WHERE et.protocol IN (?, ?) AND cad.symbol GLOB 'stableDebt*'",
            (AssetFlag.REBASING.value, CPT_AAVE_V3, CPT_SPARK),
        )
        # Aave v3 & Spark Lend variable debt tokens accrue interest via variable debt index.
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT et.identifier, ? '
            'FROM evm_tokens AS et '
            'JOIN common_asset_details AS cad ON cad.identifier = et.identifier '
            "WHERE et.protocol IN (?, ?) AND cad.symbol GLOB 'variableDebt*'",
            (AssetFlag.ACCRUING_INTEREST_DEBT.value, CPT_AAVE_V3, CPT_SPARK),
        )
        # Aave v3 aTokens accrue interest via reserve liquidity index.
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT et.identifier, ? '
            'FROM evm_tokens AS et '
            'JOIN common_asset_details AS cad ON cad.identifier = et.identifier '
            "WHERE et.protocol = ? AND cad.symbol GLOB 'a*'",
            (AssetFlag.ACCRUING_INTEREST_SUPPLY.value, CPT_AAVE_V3),
        )
        # Spark Lend sp* aTokens accrue interest; exclude ERC-4626 Spark Savings V1/V2 vaults.
        vault_placeholders = ','.join('?' * len(SPARK_SAVINGS_V2_VAULT_ADDRESSES))
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT et.identifier, ? '
            'FROM evm_tokens AS et '
            'JOIN common_asset_details AS cad ON cad.identifier = et.identifier '
            "WHERE et.protocol = ? AND cad.symbol GLOB 'sp*' "
            'AND EXISTS ('
            '  SELECT 1 FROM underlying_tokens_list AS ut '
            '  WHERE ut.parent_token_entry = et.identifier'
            ') '
            f'AND et.address COLLATE NOCASE NOT IN ({vault_placeholders})',
            (
                AssetFlag.ACCRUING_INTEREST_SUPPLY.value,
                CPT_SPARK,
                *SPARK_SAVINGS_V2_VAULT_ADDRESSES,
            ),
        )

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=False,
    )
