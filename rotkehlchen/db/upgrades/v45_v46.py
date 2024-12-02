import json
import logging
import urllib.parse
from typing import TYPE_CHECKING

from rotkehlchen.constants import ALLASSETIMAGESDIR_NAME, ASSETIMAGESDIR_NAME, IMAGESDIR_NAME
from rotkehlchen.constants.assets import A_COW, A_GNOSIS_COW, A_LQTY
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v45->v46 upgrade')
def upgrade_v45_to_v46(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v45 to v46. This was in v1.37 release.

    - Remove balancer module from settings
    - Refresh icons
    """
    @progress_step(description='Removing balancer module from user settings.')
    def _remove_balancer_module(write_cursor: 'DBCursor') -> None:
        if (active_modules_result := write_cursor.execute("SELECT value FROM settings where name='active_modules'").fetchone()) is None:  # noqa: E501
            return None

        try:
            active_modules = json.loads(active_modules_result[0])
        except json.JSONDecodeError:
            log.error(f'During v45->v46 DB upgrade a non-json active_modules entry was found: {active_modules_result[0]}.')  # noqa: E501
            return None

        write_cursor.execute(
            "UPDATE OR IGNORE settings SET value=? WHERE name='active_modules'",
            (json.dumps([module for module in active_modules if module != 'balancer']),),
        )

    @progress_step(description='Refreshing icons.')
    def _refresh_icons(write_cursor: 'DBCursor') -> None:
        identifiers_to_delete = [
            A_COW.identifier,
            A_LQTY.identifier,
            A_GNOSIS_COW.identifier,
            'eip155:42161/erc20:0xcb8b5CD20BdCaea9a010aC1F8d835824F5C87A04',  # Cowswap on Arbitrum
        ]
        icons_dir = db.user_data_dir.parent.parent / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME / ALLASSETIMAGESDIR_NAME  # noqa: E501
        for identifier in identifiers_to_delete:
            icon_path = icons_dir / f'{urllib.parse.quote_plus(identifier)}_small.png'
            icon_path.unlink(missing_ok=True)

    @progress_step(description='Moving EVM event extra data to the history_events table.')
    def _move_extra_data(write_cursor: 'DBCursor') -> None:
        write_cursor.execute('ALTER TABLE history_events ADD COLUMN extra_data TEXT;')
        write_cursor.execute(
            'UPDATE history_events SET extra_data = '
            '(SELECT extra_data FROM evm_events_info '
            'WHERE evm_events_info.identifier = history_events.identifier);',
        )
        write_cursor.execute('ALTER TABLE evm_events_info DROP COLUMN extra_data;')

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
