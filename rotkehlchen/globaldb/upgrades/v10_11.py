from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v10->v11 upgrade')
def migrate_to_v11(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:

    1. Adds alchemy to the historical price sources table.

    This upgrade took place in v1.38
    """

    @progress_step('Adding alchemy to price_history_source_types')
    def update_price_history_source_types_entries(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'INSERT INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('I', 9),
        )

    @progress_step('Create indexes')
    def create_assets_indexes(write_cursor: 'DBCursor') -> None:
        for query in (
            'CREATE INDEX IF NOT EXISTS idx_assets_identifier ON assets (identifier);',
            'CREATE INDEX IF NOT EXISTS idx_evm_tokens_identifier ON evm_tokens (identifier, chain, protocol);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_multiasset_mappings_asset ON multiasset_mappings (asset);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_asset_collections_main_asset ON asset_collections (main_asset);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_user_owned_assets_asset_id ON user_owned_assets (asset_id);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_common_assets_identifier ON common_asset_details (identifier);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_price_history_identifier ON price_history (from_asset, to_asset);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_location_mappings_identifier ON location_asset_mappings (local_id);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_underlying_tokens_lists_identifier ON underlying_tokens_list (identifier, parent_token_entry);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_binance_pairs_identifier ON binance_pairs (base_asset, quote_asset);',  # noqa: E501
            'CREATE INDEX IF NOT EXISTS idx_multiasset_mappings_identifier ON multiasset_mappings (asset);',  # noqa: E501
        ):
            write_cursor.execute(query)

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=True,
    )
