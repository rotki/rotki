import logging
from typing import TYPE_CHECKING

import filetype

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import IconManager, Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _validate_asset_icons(icon_manager: 'IconManager') -> None:
    """
    Loops through icons in the user's data directory and deletes those that are malformed.
    """
    icons_directory = icon_manager.icons_dir
    for icon_entry in icons_directory.iterdir():
        if icon_entry.is_file():
            icon_file_type = filetype.guess(icon_entry)
            if icon_file_type is None:
                icon_entry.unlink()
            elif icon_file_type.extension not in ALLOWED_ICON_EXTENSIONS:
                icon_entry.unlink()


def data_migration_3(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    Migration created in 1.24
    - Update the list of ignored assets with tokens from cryptoscamdb.
    - Delete malformed assets icons.
    """
    try:
        update_spam_assets(write_cursor=write_cursor, db=rotki.data.db, make_remote_query=True)
    except RemoteError as e:
        log.error(f'Failed to update the list of ignored assets during db migration. {str(e)}')

    _validate_asset_icons(rotki.icon_manager)
