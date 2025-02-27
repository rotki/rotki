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

    @progress_step('Remove avalanche and binance asset type')
    def remove_avalanche_binance_asset_type(write_cursor: 'DBCursor') -> None:
        """Update the assets we have in our global DB that are of avalanche and binance asset
        type to be EVM tokens with the proper identifier and chain id.

        For any other tokens the user may have added change the asset type to OTHER.

        Finally remove the asset types
        """
        changed_ids = (
            'BIDR', 'COS', 'PHB', 'BUX', 'LNCHX', 'POLX', 'ICA', 'TEDDY',
        )
        # We also do not change the following since they were never fused to BSC chain
        # 'BKRW', 'BVND', 'ERD', 'BOLT'

        for asset_id, asset_name, symbol, coingecko, cryptocompare, started, chain_id, address, decimals, swapped_for in (  # noqa: E501
                ('eip155:56/erc20:0x9A2f5556e9A637e8fBcE886d8e3cf8b316a1D8a2', 'BIDR BEP20', 'BIDR', None, 'BIDR', 1593475200, 56, '0x9A2f5556e9A637e8fBcE886d8e3cf8b316a1D8a2', 18, None),  # noqa: E501
                ('eip155:56/erc20:0x96Dd399F9c3AFda1F194182F71600F1B65946501', 'Contentos', 'COS', 'contentos', 'COS', 1561074552, 56, '0x96Dd399F9c3AFda1F194182F71600F1B65946501', 18, None),  # noqa: E501
                ('eip155:56/erc20:0x0409633A72D846fc5BBe2f98D88564D35987904D', 'Phoenix Global', 'PHB', 'phoenix-global', 'PHB', 1558497600, 56, '0x0409633A72D846fc5BBe2f98D88564D35987904D', 18, None),  # noqa: E501
                ('eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'BUX Token', 'BUX', None, None, 1643932800, 56, '0x211FfbE424b90e25a15531ca322adF1559779E45', 18, None),  # This already exists in the global DB but keeping it here for completion's sake# noqa: E501
                ('eip155:56/erc20:0xC43570263e924C8cF721F4b9c72eEd1AEC4Eb7DF', 'LaunchX', 'LNCHX', None, None, 1620720017, 56, '0xC43570263e924C8cF721F4b9c72eEd1AEC4Eb7DF', 18, None),  # noqa: E501
                ('eip155:56/erc20:0xbe510da084E084e3C27b20D79C135Dc841135c7F', 'Polylastic V2', 'POLX', 'polylastic', 'POLX', 1619730927, 56, '0xbe510da084E084e3C27b20D79C135Dc841135c7F', 18, 'eip155:137/erc20:0x187Ae45f2D361CbCE37c6A8622119c91148F261b'),  # noqa: E501
                ('eip155:56/erc20:0x0ca2f09eCa544b61b91d149dEA2580c455c564b2', 'Icarus', 'ICA', None, None, 1571364000, 56, '0x0ca2f09eCa544b61b91d149dEA2580c455c564b2', 18, None),  # noqa: E501
                ('eip155:43114/erc20:0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC', 'TEDDY ', 'TEDDY', None, None, 1629989893, 43114, '0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC', 18, None),  # noqa: E501
        ):
            write_cursor.execute(
                "INSERT OR IGNORE INTO assets(identifier, name, type) VALUES(?, ?, 'C')",
                (asset_id, asset_name),
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO common_asset_details(identifier, symbol, coingecko, '
                'cryptocompare, started, swapped_for) VALUES(?, ?, ?, ?, ?, ?)',
                (asset_id, symbol, coingecko, cryptocompare, started, swapped_for),
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO evm_tokens(identifier, token_kind, chain, address, decimals'
                ") VALUES(?, 'A', ?, ?, ?)",
                (asset_id, chain_id, address, decimals),
            )

        write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({",".join(["?"] * len(changed_ids))})', changed_ids)  # noqa: E501
        write_cursor.execute("UPDATE assets SET type='W' WHERE type IN ('S', 'X')")
        write_cursor.execute("DELETE FROM asset_types WHERE type IN ('S', 'X')")

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=True,
    )
