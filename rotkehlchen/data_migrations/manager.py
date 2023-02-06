import logging
from typing import TYPE_CHECKING, Callable, NamedTuple

from rotkehlchen.data_migrations.migrations.migration_1 import data_migration_1
from rotkehlchen.data_migrations.migrations.migration_2 import data_migration_2
from rotkehlchen.data_migrations.migrations.migration_3 import data_migration_3
from rotkehlchen.data_migrations.migrations.migration_4 import data_migration_4
from rotkehlchen.data_migrations.migrations.migration_5 import data_migration_5
from rotkehlchen.data_migrations.migrations.migration_6 import data_migration_6
from rotkehlchen.data_migrations.migrations.migration_7 import data_migration_7
from rotkehlchen.data_migrations.migrations.migration_8 import data_migration_8
from rotkehlchen.data_migrations.migrations.migration_9 import data_migration_9
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .progress import MigrationProgressHandler

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MigrationRecord(NamedTuple):
    version: int
    function: Callable[['Rotkehlchen', MigrationProgressHandler], None]


MIGRATION_LIST = [
    MigrationRecord(version=1, function=data_migration_1),
    MigrationRecord(version=2, function=data_migration_2),
    MigrationRecord(version=3, function=data_migration_3),
    MigrationRecord(version=4, function=data_migration_4),
    MigrationRecord(version=5, function=data_migration_5),
    MigrationRecord(version=6, function=data_migration_6),
    MigrationRecord(version=7, function=data_migration_7),
    MigrationRecord(version=8, function=data_migration_8),
    MigrationRecord(version=9, function=data_migration_9),
]
LAST_DATA_MIGRATION = len(MIGRATION_LIST)


class DataMigrationManager:

    def __init__(self, rotki: 'Rotkehlchen'):
        self.rotki = rotki

    def maybe_migrate_data(self) -> None:
        with self.rotki.data.db.conn.read_ctx() as cursor:
            settings = self.rotki.data.db.get_settings(cursor)
        current_migration = settings.last_data_migration

        self.progress_handler = MigrationProgressHandler(
            messages_aggregator=self.rotki.msg_aggregator,
            target_version=LAST_DATA_MIGRATION,
        )
        for migration in MIGRATION_LIST:
            should_apply_migration_9 = False
            if migration.version == 9 and current_migration == LAST_DATA_MIGRATION:
                # there was a bug in 1.27.0 where new accounts were not writing last migration
                # in the DB so new migrations won't be applied. Check for that here
                with self.rotki.data.db.conn.read_ctx() as cursor:
                    cursor.execute('SELECT value FROM settings WHERE name="last_data_migration"')  # noqa: E501
                    if cursor.fetchone() is None:
                        should_apply_migration_9 = True
            if current_migration < migration.version or should_apply_migration_9:
                if self._perform_migration(migration) is False:
                    break  # a migration failed -- no point continuing

                current_migration += 1
                log.debug(f'Successfuly applied migration {current_migration}')
                with self.rotki.data.db.user_write() as write_cursor:
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_data_migration', current_migration),
                    )
        else:  # no break -- all migrations completed okay, so remember last one
            with self.rotki.data.db.user_write() as write_cursor:
                write_cursor.execute(  # even if no migration happens we need to remember last one
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_data_migration', LAST_DATA_MIGRATION),
                )

    def _perform_migration(self, migration: MigrationRecord) -> bool:
        """Performs a single data migration and returns boolean for success/failure"""
        self.progress_handler.new_round(version=migration.version)
        try:
            migration.function(self.rotki, self.progress_handler)
        except BaseException as e:
            error = f'Failed to run soft data migration to version {migration.version} due to {str(e)}'  # noqa: E501
            self.rotki.msg_aggregator.add_error(error)
            return False

        return True
