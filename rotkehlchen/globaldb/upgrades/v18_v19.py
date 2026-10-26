from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v18->v19 upgrade')
def migrate_to_v19(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """Add Birdeye as a historical price source and indexes for asset lookups.

    This upgrade takes place in v1.45
    """

    @progress_step('Adding Birdeye to price_history_source_types')
    def _add_birdeye_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('L', 12),
        )

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

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=False,
    )
