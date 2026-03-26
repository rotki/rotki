import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v15->v16 upgrade')
def migrate_to_v16(
        connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler',
) -> None:
    """This upgrade adds Hyperliquid L1 (chain 999) assets and contract data."""

    @progress_step('Adding WHYPE token to the global DB.')
    def _add_whype_token(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO assets(identifier, name, type) VALUES (?, ?, ?)',
            ('eip155:999/erc20:0x5555555555555555555555555555555555555555', 'Wrapped HYPE', 'C'),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO common_asset_details(identifier, symbol) VALUES (?, ?)',
            ('eip155:999/erc20:0x5555555555555555555555555555555555555555', 'WHYPE'),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO evm_tokens(identifier, token_kind, chain, address, decimals) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                'eip155:999/erc20:0x5555555555555555555555555555555555555555',
                'A',
                999,
                '0x5555555555555555555555555555555555555555',
                18,
            ),
        )

    @progress_step('Adding Hyperliquid contract data.')
    def _add_hyperliquid_contracts(write_cursor: 'DBCursor') -> None:
        abi_rows = write_cursor.execute(
            'SELECT name, id FROM contract_abi WHERE name IN (?, ?)',
            ('MULTICALL2', 'BALANCE_SCAN'),
        ).fetchall()
        abi_by_name = dict(abi_rows)
        if len(abi_by_name) != 2:
            log.error(
                'Missing required abi entries while upgrading globaldb to v16. '
                'Skipping Hyperliquid contract insertion.',
            )
            return

        # Multicall3 (uses MULTICALL2 ABI)
        write_cursor.execute(
            'INSERT OR IGNORE INTO contract_data(address, chain_id, abi, deployed_block) '
            'VALUES (?, ?, ?, ?)',
            ('0xcA11bde05977b3631167028862bE2a173976CA11', 999, abi_by_name['MULTICALL2'], 0),
        )
        # BalanceScanner (uses BALANCE_SCAN ABI)
        write_cursor.execute(
            'INSERT OR IGNORE INTO contract_data(address, chain_id, abi, deployed_block) '
            'VALUES (?, ?, ?, ?)',
            ('0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92', 999, abi_by_name['BALANCE_SCAN'], 0),
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
