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
def migrate_to_v16(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This upgrade adds the WMON (Wrapped Monad) token to the global database."""

    @progress_step('Adding WMON token to the global database.')
    def _add_wmon_token(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO assets(identifier, name, type) "
            "VALUES('eip155:143/erc20:0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A', 'Wrapped Monad', 'C');",  # noqa: E501
        )
        write_cursor.execute(
            "INSERT OR IGNORE INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) "  # noqa: E501
            "VALUES('eip155:143/erc20:0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A', 'A', 143, '0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A', 18, NULL);",  # noqa: E501
        )
        write_cursor.execute(
            "INSERT OR IGNORE INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) "  # noqa: E501
            "VALUES('eip155:143/erc20:0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A', 'WMON', 'wrapped-monad', NULL, NULL, NULL, NULL);",  # noqa: E501
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
