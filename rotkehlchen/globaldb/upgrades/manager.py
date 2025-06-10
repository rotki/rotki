import logging
import shutil
import sqlite3
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.globaldb.migrations.manager import (
    LAST_DATA_MIGRATION,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.globaldb.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.globaldb.utils import (
    GLOBAL_DB_SCHEMA_BREAKING_CHANGES,
    GLOBAL_DB_VERSION,
    MIN_SUPPORTED_GLOBAL_DB_VERSION,
    globaldb_get_setting_value,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.upgrades import DBUpgradeProgressHandler, UpgradeRecord

from .v2_v3 import migrate_to_v3
from .v3_v4 import migrate_to_v4
from .v4_v5 import migrate_to_v5
from .v5_v6 import migrate_to_v6
from .v6_v7 import migrate_to_v7
from .v7_v8 import migrate_to_v8
from .v8_v9 import migrate_to_v9
from .v9_v10 import migrate_to_v10
from .v10_v11 import migrate_to_v11
from .v11_v12 import migrate_to_v12

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


UPGRADES_LIST = [
    UpgradeRecord(
        from_version=2,
        function=migrate_to_v3,
    ),
    UpgradeRecord(
        from_version=3,
        function=migrate_to_v4,
    ),
    UpgradeRecord(
        from_version=4,
        function=migrate_to_v5,
    ),
    UpgradeRecord(
        from_version=5,
        function=migrate_to_v6,
    ),
    UpgradeRecord(
        from_version=6,
        function=migrate_to_v7,
    ),
    UpgradeRecord(
        from_version=7,
        function=migrate_to_v8,
    ),
    UpgradeRecord(
        from_version=8,
        function=migrate_to_v9,
    ),
    UpgradeRecord(
        from_version=9,
        function=migrate_to_v10,
    ),
    UpgradeRecord(
        from_version=10,
        function=migrate_to_v11,
    ),
    UpgradeRecord(
        from_version=11,
        function=migrate_to_v12,
    ),
]


async def maybe_upgrade_globaldb(
        connection: 'DBConnection',
        global_dir: Path,
        db_filename: str,
        msg_aggregator: 'MessagesAggregator',
        globaldb: 'GlobalDBHandler | None' = None,
) -> bool:
    """Maybe upgrade the global DB.

    Returns True if this is a fresh DB. In that
    case the caller should make sure to input the latest version
    and also the latest migration in the settings. In all other cases returns False.

    The globaldb parameter is needed to handle schema-breaking changes that require
    updating assets data before the DB schema is modified.
    """
    try:
        async with connection.read_ctx() as cursor:
            db_version = globaldb_get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)
    except sqlite3.OperationalError:  # pylint: disable=no-member
        return True  # fresh DB -- nothing to upgrade

    if db_version < MIN_SUPPORTED_GLOBAL_DB_VERSION:
        raise ValueError(
            f'Your account was last opened by a very old version of rotki and its '
            f'globaldb version is {db_version}. To be able to use it you will need to '
            f'first use a previous version of rotki and then use this one. '
            f'Refer to the documentation for more information. '
            f'https://docs.rotki.com/usage-guides#upgrading-rotki-after-a-long-time',
        )
    if db_version > GLOBAL_DB_VERSION:
        raise ValueError(
            f'Tried to open a rotki version intended to work with GlobalDB v{GLOBAL_DB_VERSION} '
            f'but the GlobalDB found in the system is v{db_version}. Bailing ...',
        )
    elif db_version < GLOBAL_DB_VERSION:
        progress_handler = DBUpgradeProgressHandler(
            messages_aggregator=msg_aggregator,
            target_version=GLOBAL_DB_VERSION,
        )
        for upgrade in UPGRADES_LIST:
            if globaldb is not None and upgrade.from_version in GLOBAL_DB_SCHEMA_BREAKING_CHANGES:
                AssetsUpdater(
                    globaldb=globaldb,
                    msg_aggregator=msg_aggregator,
                ).apply_pending_compatible_updates()

            await _perform_single_upgrade(
                upgrade=upgrade,
                connection=connection,
                global_dir=global_dir,
                db_filename=db_filename,
                progress_handler=progress_handler,
            )

    # Finally make sure to always have latest version in the DB
    async with connection.write_ctx() as write_cursor:
        await write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('version', GLOBAL_DB_VERSION),
        )

    return False  # not fresh DB


async def _perform_single_upgrade(
        upgrade: UpgradeRecord,
        connection: 'DBConnection',
        global_dir: Path,
        db_filename: str,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    async with connection.read_ctx() as cursor:
        current_version = globaldb_get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)

    if current_version != upgrade.from_version:
        return
    to_version = upgrade.from_version + 1
    progress_handler.new_round(version=to_version)

    # WAL checkpoint at start to make sure everything is in the file we copy for backup. For more info check comment in the user DB upgrade.  # noqa: E501
    await connection.execute('PRAGMA wal_checkpoint(FULL);')
    # Create a backup
    tmp_db_filename = f'{ts_now()}_global_db_v{upgrade.from_version}.backup'
    tmp_db_path = global_dir / tmp_db_filename
    shutil.copyfile(global_dir / db_filename, tmp_db_path)

    async with connection.write_ctx() as cursor:
        await cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('ongoing_upgrade_from_version', str(upgrade.from_version)),
        )

    try:
        await upgrade.function(connection=connection, progress_handler=progress_handler)
    except BaseException as e:
        # Problem .. restore DB backup, log all info and bail out
        error_message = (
            f'Failed at global DB upgrade from version {upgrade.from_version} to '
            f'{to_version}: {e!s}'
        )
        stacktrace = traceback.format_exc()
        log.error(f'{error_message}\n{stacktrace}')
        shutil.copyfile(tmp_db_path, global_dir / db_filename)
        raise ValueError(error_message) from e

    # single upgrade successful
    async with connection.write_ctx() as write_cursor:
        await write_cursor.execute(
            'DELETE FROM settings WHERE name=?',
            ('ongoing_upgrade_from_version',),
        )
        await write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(to_version)),
        )


async def configure_globaldb(
        global_dir: Path,
        db_filename: str,
        connection: 'DBConnection',
        msg_aggregator: 'MessagesAggregator',
        globaldb: 'GlobalDBHandler | None' = None,
) -> None:
    """Configure the global database and handle schema upgrades.

    - global_dir: Directory containing the global database
    - db_filename: Name of the database file (typically global.db)
    - connection: The database connection object
    - msg_aggregator: Message aggregator for logging
    - globaldb: Optional handler instance - determines whether asset updates are attempted

    May raise:
        - DBSchemaError if the database schema is invalid.
    """
    is_fresh_db = await maybe_upgrade_globaldb(
        globaldb=globaldb,
        connection=connection,
        global_dir=global_dir,
        db_filename=db_filename,
        msg_aggregator=msg_aggregator,
    )

    # its not a fresh database and foreign keys are not turned on by default.
    await connection.executescript('PRAGMA foreign_keys=on;')
    await connection.execute('PRAGMA journal_mode=WAL;')
    if is_fresh_db is True:
        await connection.executescript(DB_SCRIPT_CREATE_TABLES)
        async with connection.write_ctx() as cursor:
            await cursor.executemany(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                [('version', str(GLOBAL_DB_VERSION)), ('last_data_migration', str(LAST_DATA_MIGRATION))],  # noqa: E501
            )
    else:
        await maybe_apply_globaldb_migrations(connection)
    await connection.schema_sanity_check()
