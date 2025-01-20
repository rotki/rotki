import json
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

    @progress_step(description='Updating ERC721 token identifiers.')
    def _update_erc721_token_identifiers(write_cursor: 'DBCursor') -> None:
        """Update erc721 token identifiers to include the token id
        for all evm events that have the token id in extra_data.
        """
        write_cursor = write_cursor.execute("SELECT identifier, asset, extra_data FROM history_events WHERE entry_type = 2 AND extra_data != ''")  # noqa: E501
        assets_updates = []
        extra_data_updates = []
        for entry in write_cursor:
            asset_identifier = entry[1]
            try:
                extra_data: dict = json.loads(entry[2])
            except json.JSONDecodeError as e:
                log.error(f'Failed to parse {entry[2]} as JSON due to {e}')
                continue

            if (token_id := extra_data.get('token_id')) is not None:
                assets_updates.append((f'{asset_identifier}/{token_id}', asset_identifier))
                # remove the token id and name from extra_data to avoid storing redundant data,
                extra_data.pop('token_id', '')
                extra_data.pop('token_name', '')
                extra_data_updates.append((json.dumps(extra_data), entry[0]))

        if len(assets_updates) > 0:
            assets_query = 'UPDATE assets SET identifier=? WHERE identifier=?'
            with GlobalDBHandler().conn.write_ctx() as global_db_write_cursor:
                global_db_write_cursor.executemany(assets_query, assets_updates)

            write_cursor.executemany(assets_query, assets_updates)
            write_cursor.executemany('UPDATE history_events SET extra_data=? WHERE identifier=?', extra_data_updates)  # noqa: E501

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
