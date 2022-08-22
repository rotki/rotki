import logging
import shutil
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.upgrades import UpgradeRecord

from ..utils import GLOBAL_DB_VERSION, MIN_SUPPORTED_GLOBAL_DB_VERSION, _get_setting_value
from .v2_v3 import migrate_to_v3

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


UPGRADES_LIST = [
    UpgradeRecord(
        from_version=2,
        function=migrate_to_v3,
    ),
]


def maybe_upgrade_globaldb(connection: 'DBConnection', dbpath: Path) -> bool:
    """Maybe upgrade the global DB. Returns True if this is a fresh DB. In that
    case the caller should make sure to input the latest version in the settings.
    In all other cases returns False"""

    try:
        with connection.read_ctx() as cursor:
            db_version = _get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)
    except sqlite3.OperationalError:  # pylint: disable=no-member
        return True  # fresh DB -- nothing to upgrade

    if db_version < MIN_SUPPORTED_GLOBAL_DB_VERSION:
        raise ValueError(
            f'Your account was last opened by a very old version of rotki and its '
            f'globaldb version is {db_version}. To be able to use it you will need to '
            f'first use a previous version of rotki and then use this one. '
            f'Refer to the documentation for more information. '
            f'https://rotki.readthedocs.io/en/latest/usage_guide.html#upgrading-rotki-after-a-very-long-time',  # noqa: E501
        )
    if db_version > GLOBAL_DB_VERSION:
        raise ValueError(
            f'Tried to open a rotki version intended to work with GlobalDB v{GLOBAL_DB_VERSION} '
            f'but the GlobalDB found in the system is v{db_version}. Bailing ...',
        )

    for upgrade in UPGRADES_LIST:
        if db_version != upgrade.from_version:
            continue

        # start the upgrade
        to_version = upgrade.from_version + 1
        # Create a backup
        tmp_db_filename = f'{ts_now()}_global_db_v{db_version}.backup'
        tmp_db_path = dbpath.parent / tmp_db_filename
        shutil.copyfile(dbpath, tmp_db_path)
        try:
            upgrade.function(connection)
        except BaseException as e:  # lgtm[py/catch-base-exception]
            # Problem .. restore DB backup and bail out
            error_message = (
                f'Failed at global DB upgrade from version {upgrade.from_version} to '
                f'{to_version}: {str(e)}'
            )
            log.error(error_message)
            shutil.copyfile(tmp_db_path, dbpath)
            raise ValueError(error_message) from e

        # single upgrade succesfull
        with connection.write_ctx() as cursor:
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(GLOBAL_DB_VERSION)),
            )

    return False  # not fresh DB
