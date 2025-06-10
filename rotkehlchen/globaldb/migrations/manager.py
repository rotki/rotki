import logging
import sqlite3
import traceback
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, NamedTuple

from rotkehlchen.globaldb.migrations.migration2 import globaldb_data_migration_2
from rotkehlchen.logging import RotkehlchenLogsAdapter

from ..utils import globaldb_get_setting_value
from .migration1 import globaldb_data_migration_1

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection


class MigrationRecord(NamedTuple):
    version: int
    function: Callable[['DBConnection'], Awaitable[None]]


MIGRATIONS_LIST = [
    MigrationRecord(version=1, function=globaldb_data_migration_1),
    MigrationRecord(version=2, function=globaldb_data_migration_2),
]
LAST_DATA_MIGRATION = len(MIGRATIONS_LIST)


async def maybe_apply_globaldb_migrations(connection: 'DBConnection') -> None:
    """Maybe apply global DB data migrations"""
    try:
        async with connection.read_ctx() as cursor:
            last_migration = globaldb_get_setting_value(cursor, 'last_data_migration', 0)
    except sqlite3.OperationalError:  # pylint: disable=no-member
        log.error('Got an operational error at get_setting during maybe_apply_globaldb_migrations')
        return  # fresh DB? Should not happen here

    current_migration = last_migration
    for migration in MIGRATIONS_LIST:
        if current_migration < migration.version:
            try:
                await migration.function(connection)
            except BaseException as e:
                stacktrace = traceback.format_exc()
                error = f'Failed to run globaldb soft data migration to version {migration.version} due to {e!s}'  # noqa: E501
                log.error(f'{error}\n{stacktrace}')
                break

            current_migration += 1
            log.debug(f'Successfully applied global DB data migration {current_migration}')
            async with connection.write_ctx() as write_cursor:
                await write_cursor.execute(  # even if no migration happens we need to remember last one
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_data_migration', str(current_migration)),
                )
    else:  # no break -- all migrations completed okay, so remember last one
        async with connection.write_ctx() as write_cursor:
            await write_cursor.execute(  # even if no migration happens we need to remember last one
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('last_data_migration', str(LAST_DATA_MIGRATION)),
            )
