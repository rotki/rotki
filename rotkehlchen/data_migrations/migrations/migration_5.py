import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _rename_icons(rotki: 'Rotkehlchen') -> None:
    """Change the prefix of icons files from _ceth_ to their CAIPS variant"""
    icon_path = rotki.icon_manager.icons_dir
    old_files = icon_path.glob(r'_ceth_0x*')
    # the urlencoded version of eip155:1/erc20:
    new_prefix = 'eip155%3A1%2Ferc20%3A'
    for file_path in old_files:
        old_name = file_path.stem
        new_name = old_name.replace('_ceth_', new_prefix)
        try:
            file_path.rename(Path(file_path.parent, f'{new_name}{file_path.suffix}'))
        except FileExistsError:
            file_path.unlink()
            log.debug(f'Skipping {old_name} because {new_name} already exists')


def data_migration_5(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:  # pylint: disable=unused-argument # noqa: E501
    """
    - Rename icons after modifying the identifiers in 1.26
    """
    _rename_icons(rotki=rotki)
