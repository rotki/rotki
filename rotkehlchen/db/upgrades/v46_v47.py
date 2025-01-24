import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v46->v47 upgrade')
def upgrade_v46_to_v47(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v46 to v47. This was in v1.38 release.

    - Add Binance Smart Chain location
    """
    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
            /* Binance Smart Chain */
            INSERT OR IGNORE INTO location(location, seq) VALUES ('v', 54);
            """)

    @progress_step(description='Remove extrainternaltx cache.')
    def _clean_cache(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("DELETE FROM key_value_cache WHERE name LIKE 'extrainternaltx_%'")

    @progress_step(description='Remove unneeded nft collection assets.')
    def _remove_nft_collection_assets(write_cursor: 'DBCursor') -> None:
        """Remove erc721 assets that have no collectible id, and also any erc20 assets
        with the same address that were incorrectly added.
        """
        identifiers_to_remove = []
        with GlobalDBHandler().conn.read_ctx() as global_db_cursor:
            cursor = global_db_cursor.execute("SELECT identifier FROM assets WHERE identifier LIKE '%erc721%'")  # noqa: E501
            for entry in cursor:
                identifiers_to_remove.extend([
                    entry[0],
                    entry[0].replace('erc721', 'erc20'),
                ])

        if len(identifiers_to_remove) == 0:
            return

        placeholders = ','.join(['?'] * len(identifiers_to_remove))
        with GlobalDBHandler().conn.write_ctx() as global_db_write_cursor:
            global_db_write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({placeholders})', identifiers_to_remove)  # noqa: E501

        # Delete from other tables where they might be referenced first to avoid FOREIGN KEY constraint errors when deleting from assets.  # noqa: E501
        write_cursor.execute(f'DELETE FROM history_events WHERE asset IN ({placeholders})', identifiers_to_remove)  # noqa: E501
        write_cursor.execute(f'DELETE FROM timed_balances WHERE currency IN ({placeholders})', identifiers_to_remove)  # noqa: E501
        write_cursor.execute(f'DELETE FROM evm_accounts_details WHERE value IN ({placeholders})', identifiers_to_remove)  # noqa: E501
        write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({placeholders})', identifiers_to_remove)  # noqa: E501

    # TODO: Reset events to trigger re-decoding so erc721 assets are added properly.

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
