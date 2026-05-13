import logging
from typing import TYPE_CHECKING

from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.filetype import guess_icon_extension

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
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
            icon_extension = guess_icon_extension(icon_entry)
            if icon_extension is None or icon_extension not in ALLOWED_ICON_EXTENSIONS:
                icon_entry.unlink()


def data_migration_3(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """
    Migration created in 1.24
    - Delete malformed assets icons.
    """
    _validate_asset_icons(rotki.icon_manager)
