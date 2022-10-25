import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Optional

from rotkehlchen.data_migrations.migrations.migration_1 import data_migration_1
from rotkehlchen.data_migrations.migrations.migration_2 import data_migration_2
from rotkehlchen.data_migrations.migrations.migration_3 import data_migration_3
from rotkehlchen.data_migrations.migrations.migration_4 import data_migration_4
from rotkehlchen.data_migrations.migrations.migration_5 import data_migration_5

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MigrationRecord(NamedTuple):
    version: int
    function: Callable[['DBCursor', 'Rotkehlchen'], None]
    kwargs: Optional[Dict[str, Any]] = None


MIGRATION_LIST = [
    MigrationRecord(version=1, function=data_migration_1),
    MigrationRecord(version=2, function=data_migration_2),
    MigrationRecord(version=3, function=data_migration_3),
    MigrationRecord(version=4, function=data_migration_4),
    MigrationRecord(version=5, function=data_migration_5),
]
LAST_DATA_MIGRATION = len(MIGRATION_LIST)


class DataMigrationManager:

    def __init__(self, rotki: 'Rotkehlchen'):
        self.rotki = rotki

    def maybe_migrate_data(self) -> None:
        with self.rotki.data.db.conn.read_ctx() as cursor:
            settings = self.rotki.data.db.get_settings(cursor)
        current_migration = settings.last_data_migration
        for migration in MIGRATION_LIST:
            if current_migration < migration.version:
                with self.rotki.data.db.user_write() as cursor:
                    if self._perform_migration(cursor, migration) is False:
                        break  # a migration failed -- no point continuing

                    current_migration += 1
                    log.debug(f'Successfuly applied migration {current_migration}')
                    cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_data_migration', current_migration),
                    )

    def _perform_migration(self, write_cursor: 'DBCursor', migration: MigrationRecord) -> bool:
        """Performs a single data migration and returns boolean for success/failure"""
        try:
            kwargs = migration.kwargs if migration.kwargs is not None else {}
            migration.function(write_cursor, self.rotki, **kwargs)
        except BaseException as e:  # lgtm[py/catch-base-exception]
            error = f'Failed to run soft data migration to version {migration.version} due to {str(e)}'  # noqa: E501
            self.rotki.msg_aggregator.add_error(error)
            return False

        return True
